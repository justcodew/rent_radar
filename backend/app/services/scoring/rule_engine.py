"""规则版好房指数计算引擎

权重口径（与 PRD 一致）：
- 好房指数 = 发布者特征(30) + 房源特征(70)
- 发布者特征：发布频率(9) + 账号年龄(7.5) + 内容多样性(7.5) + 联系方式复用(6)
- 房源特征：图片真实性(17.5) + 描述详细度(21) + 价格合理性(14) + 信息完整度(17.5)

所有打分函数返回 (score, evidence_dict)，evidence 用于评分溯源。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from app.models.listing import Listing
from app.models.stat import AreaPriceStat


# ---------- 子项打分（满分制，已按权重换算好） ----------

def calc_frequency_score(count_30d: int) -> tuple[int, dict]:
    """发布频率：30天内发布套数，越少越可信。满分 9"""
    if count_30d <= 1:
        score = 9
        level = "个人房东（仅1套）"
    elif count_30d <= 3:
        score = 6
        level = "少量发布"
    elif count_30d <= 8:
        score = 3
        level = "较频繁"
    elif count_30d <= 20:
        score = 1
        level = "疑似中介"
    else:
        score = 0
        level = "高度疑似中介"
    return score, {"count_30d": count_30d, "level": level, "max": 9}


def calc_account_age_score(age_days: int) -> tuple[int, dict]:
    """账号年龄：注册/首次出现时间越长越可信。满分 7.5"""
    if age_days >= 365:
        score = 7.5
        level = "1年以上"
    elif age_days >= 180:
        score = 5
        level = "半年以上"
    elif age_days >= 60:
        score = 3
        level = "2个月以上"
    elif age_days >= 14:
        score = 1.5
        level = "新账号"
    else:
        score = 0
        level = "极新账号（高风险）"
    return score, {"age_days": age_days, "level": level, "max": 7.5}


def calc_content_diversity_score(titles: list[str]) -> tuple[int, dict]:
    """内容多样性：标题去重后数量越多越可信（中介账号标题高度雷同）。
    满分 7.5
    """
    if not titles:
        return 0, {"unique_ratio": 0, "level": "无历史数据", "max": 7.5}
    unique = len(set(titles))
    ratio = unique / len(titles)
    if ratio >= 0.8:
        score = 7.5
        level = "内容多样化"
    elif ratio >= 0.5:
        score = 5
        level = "内容较多样"
    elif ratio >= 0.3:
        score = 2.5
        level = "内容雷同"
    else:
        score = 0
        level = "高度模板化（疑似中介）"
    return score, {"unique_ratio": round(ratio, 2), "total": len(titles), "level": level, "max": 7.5}


def calc_contact_reuse_score(contact: dict, reuse_count: int) -> tuple[int, dict]:
    """联系方式复用：同一联系方式在多帖出现 -> 疑似中介。满分 6"""
    if reuse_count == 0:
        score = 6
        level = "未复用"
    elif reuse_count == 1:
        score = 4
        level = "复用1次"
    elif reuse_count <= 3:
        score = 2
        level = "复用较多"
    else:
        score = 0
        level = "高度复用（疑似中介）"
    return score, {"reuse_count": reuse_count, "level": level, "max": 6}


# 描述详细度关键词字典（命中加分）
DESC_KEYWORDS = [
    "电梯", "南向", "北向", "东向", "西向", "民水民电", "押一付一", "押一付三",
    "近地铁", "阳台", "独立卫生间", "飘窗", "采光", "空调", "洗衣机", "冰箱",
    "热水器", "宽带", "天然气", "集中供暖", "车位", "可养宠", "拎包入住",
    "精装", "简装", "毛坯", "整租", "合租", "主卧", "次卧",
]


def calc_description_score(title: str, content: str) -> tuple[int, dict]:
    """描述详细度：基于关键词命中 + 长度。满分 21"""
    text = f"{title or ''} {content or ''}"
    hits = [kw for kw in DESC_KEYWORDS if kw in text]
    content_len = len(content or "")

    # 长度评分（满分 8）
    if content_len >= 300:
        len_score = 8
    elif content_len >= 150:
        len_score = 6
    elif content_len >= 80:
        len_score = 4
    elif content_len >= 30:
        len_score = 2
    else:
        len_score = 0

    # 关键词评分（满分 13，命中越多越高）
    kw_score = min(13, len(hits) * 1.5)

    score = int(len_score + kw_score)
    return score, {
        "content_length": content_len,
        "hit_keywords": hits[:10],
        "hit_count": len(hits),
        "length_score": len_score,
        "keyword_score": int(kw_score),
        "max": 21,
    }


def calc_info_completeness_score(listing: Listing) -> tuple[int, dict]:
    """信息完整度：必填字段计数。满分 17.5"""
    fields = {
        "price": listing.price is not None and listing.price > 0,
        "area_name": bool(listing.area_name),
        "layout": bool(listing.layout),
        "size_sqm": listing.size_sqm is not None and listing.size_sqm > 0,
        "orientation": bool(listing.orientation),
        "floor_info": bool(listing.floor_info),
        "location_detail": bool(listing.location_detail),
        "images": bool(listing.image_urls),
        "contact": bool(listing.contact_info),
    }
    filled = sum(1 for v in fields.values() if v)
    ratio = filled / len(fields)
    score = round(17.5 * ratio, 1)
    missing = [k for k, v in fields.items() if not v]
    return score, {
        "filled_count": filled,
        "total_count": len(fields),
        "missing_fields": missing,
        "max": 17.5,
    }


async def calc_price_reasonableness_score(
    listing: Listing, db: AsyncSession
) -> tuple[int, dict]:
    """价格合理性：与同区域同户型均价对比。满分 14"""
    if not listing.price or not listing.area_name:
        return 7, {"reason": "缺少价格或区域，给中位数", "max": 14}

    # 查区域均价
    stmt = select(AreaPriceStat.avg_price, AreaPriceStat.sample_count).where(
        AreaPriceStat.city == "广州",
        AreaPriceStat.area_name == listing.area_name,
    )
    if listing.layout:
        stmt = stmt.where(AreaPriceStat.layout == listing.layout)
    result = await db.execute(stmt)
    row = result.first()

    if not row or row.sample_count < 5:
        return 7, {"reason": "无足够区域均价数据", "max": 14}

    avg = row.avg_price
    deviation = (listing.price - avg) / avg if avg else 0
    abs_dev = abs(deviation)

    if abs_dev <= 0.1:
        score = 14
        level = "价格合理"
    elif abs_dev <= 0.2:
        score = 11
        level = "略偏"
    elif abs_dev <= 0.35:
        score = 7
        level = "偏离较大"
    elif deviation < 0:
        score = 3
        level = "明显低于均价（疑似引流）"
    else:
        score = 3
        level = "明显高于均价（疑似虚高）"

    return score, {
        "area_avg": avg,
        "listing_price": listing.price,
        "deviation_pct": round(deviation * 100, 1),
        "level": level,
        "sample_count": row.sample_count,
        "max": 14,
    }


def calc_image_authenticity_score(listing: Listing, phash_duplicates: int = 0) -> tuple[int, dict]:
    """图片真实性：基于图片数量 + 水印/网图命中。满分 17.5
    MVP 阶段：纯规则，检查图片数量是否过少、是否出现明显重复 pHash
    深度图片识别留给 AI 增强版（按需触发）
    """
    img_count = len(listing.image_urls or [])
    evidence = {"image_count": img_count, "phash_duplicates": phash_duplicates, "max": 17.5}

    # 数量评分（满分 10）
    if img_count >= 6:
        cnt_score = 10
    elif img_count >= 4:
        cnt_score = 8
    elif img_count >= 2:
        cnt_score = 5
    elif img_count == 1:
        cnt_score = 2
    else:
        cnt_score = 0
    evidence["count_score"] = cnt_score

    # pHash 重复扣分（满分 7.5）
    dup_score = max(0, 7.5 - phash_duplicates * 3)
    evidence["dedup_score"] = dup_score

    # 内容识别（简易规则：title/content 出现"网图""效果图""样板间"等关键词扣分）
    text = f"{listing.title or ''} {listing.content or ''}"
    suspicious_keywords = ["网图", "效果图", "样板间", "仅供参考"]
    suspicious_hits = [k for k in suspicious_keywords if k in text]
    evidence["suspicious_hits"] = suspicious_hits
    penalty = len(suspicious_hits) * 3

    score = max(0, int(cnt_score + dup_score - penalty))
    if suspicious_hits:
        evidence["level"] = "疑似非实拍"
    elif img_count == 0:
        evidence["level"] = "无图片"
    else:
        evidence["level"] = "实拍风格"
    return score, evidence


# ---------- 主入口 ----------

@dataclass
class ScoreResult:
    general_score: int
    poster_score: float
    listing_score: float
    poster_frequency_score: float
    poster_age_score: float
    poster_diversity_score: float
    poster_contact_reuse_score: float
    image_authenticity_score: float
    description_score: int
    price_reasonable_score: int
    info_completeness_score: float
    risk_tags: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)


async def get_poster_stats(db: AsyncSession, poster_id: str, days: int = 30) -> dict:
    """统计发布者近 N 天的发布情况"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = select(
        func.count(Listing.id).label("count_30d"),
        func.min(Listing.created_at).label("first_seen"),
        func.max(Listing.created_at).label("last_seen"),
    ).where(
        Listing.poster_id == poster_id,
        Listing.created_at >= since,
    )
    result = await db.execute(stmt)
    row = result.first()

    # 该发布者全部历史标题（用于内容多样性）
    titles_stmt = select(Listing.title).where(
        Listing.poster_id == poster_id
    ).limit(50)
    titles = [r[0] for r in (await db.execute(titles_stmt)).all() if r[0]]

    first_seen_ever_stmt = select(func.min(Listing.created_at)).where(Listing.poster_id == poster_id)
    first_ever = (await db.execute(first_seen_ever_stmt)).scalar()

    age_days = 0
    if first_ever:
        age_days = max(0, (datetime.now(timezone.utc) - first_ever.replace(tzinfo=timezone.utc)).days)

    return {
        "count_30d": row.count_30d or 0,
        "titles": titles,
        "age_days": age_days,
    }


async def get_contact_reuse_count(db: AsyncSession, contact_info: dict) -> int:
    """统计联系方式在多少其他房源中出现"""
    if not contact_info:
        return 0
    # 简化：检查 wechat / phone 是否在其他房源的 contact_info 中出现
    wechat = contact_info.get("wechat")
    phone = contact_info.get("phone")
    conditions = []
    if wechat:
        conditions.append(Listing.contact_info["wechat"].astext == wechat)
    if phone:
        conditions.append(Listing.contact_info["phone"].astext == phone)
    if not conditions:
        return 0
    from sqlalchemy import or_
    stmt = select(func.count(func.distinct(Listing.id))).where(or_(*conditions))
    count = (await db.execute(stmt)).scalar() or 0
    return max(0, count - 1)  # 减去自己


async def calculate_listing_score(
    db: AsyncSession,
    listing: Listing,
    phash_duplicates: int = 0,
) -> ScoreResult:
    """计算单个房源的好房指数（规则版）"""
    # 发布者特征
    poster_stats = {"count_30d": 0, "titles": [], "age_days": 0}
    if listing.poster_id:
        poster_stats = await get_poster_stats(db, listing.poster_id)
    reuse_count = await get_contact_reuse_count(db, listing.contact_info or {})

    f_score, f_ev = calc_frequency_score(poster_stats["count_30d"])
    a_score, a_ev = calc_account_age_score(poster_stats["age_days"])
    d_score, d_ev = calc_content_diversity_score(poster_stats["titles"])
    c_score, c_ev = calc_contact_reuse_score(listing.contact_info or {}, reuse_count)

    poster_total = f_score + a_score + d_score + c_score

    # 房源特征
    img_score, img_ev = calc_image_authenticity_score(listing, phash_duplicates)
    desc_score, desc_ev = calc_description_score(listing.title or "", listing.content or "")
    price_score, price_ev = await calc_price_reasonableness_score(listing, db)
    info_score, info_ev = calc_info_completeness_score(listing)

    listing_total = img_score + desc_score + price_score + info_score

    general_score = round(poster_total + listing_total)

    # 风险标签
    risk_tags: list[str] = []
    if poster_stats["count_30d"] > 8:
        risk_tags.append("疑似中介")
    if reuse_count >= 2:
        risk_tags.append("联系方式复用")
    if price_ev.get("deviation_pct", 0) < -30:
        risk_tags.append("价格异常低")
    if img_ev.get("suspicious_hits"):
        risk_tags.append("图片存疑")
    if desc_ev.get("content_length", 0) < 30:
        risk_tags.append("描述过简")

    evidence = {
        "poster": {
            "frequency": f_ev, "age": a_ev,
            "diversity": d_ev, "contact_reuse": c_ev,
            "total": poster_total,
        },
        "image_authenticity": img_ev,
        "description_quality": desc_ev,
        "price_reasonableness": price_ev,
        "info_completeness": info_ev,
    }

    return ScoreResult(
        general_score=general_score,
        poster_score=poster_total,
        listing_score=listing_total,
        poster_frequency_score=f_score,
        poster_age_score=a_score,
        poster_diversity_score=d_score,
        poster_contact_reuse_score=c_score,
        image_authenticity_score=img_score,
        description_score=desc_score,
        price_reasonable_score=price_score,
        info_completeness_score=info_score,
        risk_tags=risk_tags,
        evidence=evidence,
    )


# 好房指数评级
def get_score_level(score: int) -> tuple[str, int]:
    """返回 (等级名, 星级)"""
    if score >= 90:
        return "精选好房", 5
    if score >= 75:
        return "优质好房", 4
    if score >= 60:
        return "一般", 3
    return "不推荐", 2

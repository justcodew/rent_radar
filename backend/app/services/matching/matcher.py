"""匹配度计算引擎

匹配度（满分 100）= 价格(20) + 通勤(20) + 区域(15) + 户型(15) + 环境(15) + 关键词(10)
个性化推荐分 = 好房指数 * 0.6 + 匹配度 * 0.4
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.listing import Listing
from app.models.profile import Profile
from app.models.score import ListingScore
from app.services.matching.commute import get_commute_minutes


def calc_price_match(price: int | None, budget_min: int, budget_max: int) -> tuple[int, dict]:
    """价格匹配，满分 20"""
    if price is None:
        return 5, {"reason": "无价格", "max": 20}
    if budget_min <= price <= budget_max:
        return 20, {"price": price, "in_budget": True, "max": 20}
    if price < budget_min * 0.8:
        return 10, {"price": price, "reason": "价格过低（疑似引流）", "max": 20}
    if price <= budget_max * 1.2:
        # 超出预算 20% 以内，线性衰减
        overflow = (price - budget_max) / budget_max
        score = max(0, int(20 - 20 * overflow))
        return score, {"price": price, "over_budget": True, "overflow_pct": round(overflow * 100, 1), "max": 20}
    return 0, {"price": price, "reason": "远超预算", "max": 20}


async def calc_commute_match(
    redis,
    listing: Listing,
    profile: Profile,
) -> tuple[int, dict]:
    """通勤匹配（支持多人）。满分 20"""
    commutes = profile.commute or []
    if not commutes:
        return 5, {"reason": "未设置通勤需求", "max": 20}
    if not listing.location_detail and not listing.area_name:
        return 0, {"reason": "房源位置不明", "max": 20}

    from_location = listing.location_detail or listing.area_name
    weighted_scores = []
    per_person = []

    for c in commutes:
        dest = c.get("location")
        max_time = c.get("max_time", 45)
        weight = c.get("weight", 1.0)
        mode = c.get("mode", "transit")
        if not dest:
            continue

        actual = await get_commute_minutes(redis, from_location, dest, mode)
        if actual is None:
            # 接口失败，给保守分
            score = 10
            per_person.append({"dest": dest, "actual": None, "score": score})
            weighted_scores.append(score * weight)
            continue

        if actual <= max_time:
            score = 20
        else:
            overflow = (actual - max_time) / max_time
            score = max(0, int(20 * (1 - overflow) ** 2))
        per_person.append({"dest": dest, "actual_min": actual, "max_min": max_time, "score": score})
        weighted_scores.append(score * weight)

    if not weighted_scores:
        return 0, {"reason": "通勤配置异常", "max": 20}

    total_weight = sum(c.get("weight", 1.0) for c in commutes)
    avg_score = sum(weighted_scores) / total_weight if total_weight else 0
    return int(avg_score), {"per_person": per_person, "average": int(avg_score), "max": 20}


def calc_area_match(listing_area: str | None, profile_areas: list[str]) -> tuple[int, dict]:
    """区域匹配，满分 15"""
    if not listing_area:
        return 0, {"reason": "无区域", "max": 15}
    if not profile_areas:
        return 8, {"reason": "未限制区域，给中位分", "max": 15}
    if listing_area in profile_areas:
        return 15, {"area": listing_area, "in_profile": True, "max": 15}
    # 邻近区域：去掉"区"后缀再查 _ADJACENT_MAP
    listing_base = listing_area.rstrip("区") if listing_area.endswith("区") else listing_area
    profile_bases = [a.rstrip("区") if a.endswith("区") else a for a in profile_areas]
    if any(_is_adjacent(listing_base, p) for p in profile_bases):
        return 8, {"area": listing_area, "is_adjacent": True, "max": 15}
    return 0, {"area": listing_area, "reason": "区域不匹配", "max": 15}


_ADJACENT_MAP = {
    # 广州相邻区域关系
    "天河": ["越秀", "海珠", "黄埔", "白云"],
    "越秀": ["天河", "海珠", "荔湾", "白云"],
    "海珠": ["天河", "越秀", "荔湾", "番禺"],
    "荔湾": ["越秀", "海珠", "白云"],
    "白云": ["天河", "越秀", "荔湾", "黄埔", "花都"],
    "黄埔": ["天河", "白云", "增城", "番禺"],
    "番禺": ["海珠", "黄埔", "南沙"],
    "花都": ["白云"],
    "南沙": ["番禺"],
    "增城": ["黄埔"],
    # 北京相邻区域关系（兼容旧数据/测试）
    "朝阳": ["东城", "西城", "海淀", "丰台", "通州", "顺义", "昌平"],
    "海淀": ["西城", "朝阳", "丰台", "石景山", "昌平"],
    "东城": ["西城", "朝阳", "丰台"],
    "西城": ["东城", "朝阳", "海淀", "丰台"],
    "丰台": ["西城", "东城", "朝阳", "海淀", "石景山", "大兴", "房山"],
    "石景山": ["海淀", "丰台"],
    "通州": ["朝阳", "顺义", "大兴"],
    "大兴": ["丰台", "通州", "房山"],
    "昌平": ["海淀", "朝阳", "顺义"],
    "顺义": ["朝阳", "通州", "昌平"],
    "房山": ["丰台", "大兴"],
}


def _is_adjacent(a: str, b: str) -> bool:
    return b in _ADJACENT_MAP.get(a, [])


def calc_layout_match(listing_layout: str | None, profile_layouts: list[str]) -> tuple[int, dict]:
    """户型匹配，满分 15"""
    if not listing_layout:
        return 3, {"reason": "无户型", "max": 15}
    if not profile_layouts:
        return 7, {"reason": "未限制户型", "max": 15}
    if listing_layout in profile_layouts:
        return 15, {"layout": listing_layout, "in_profile": True, "max": 15}
    # 简化：包含相同居室数
    if any(_same_rooms(listing_layout, p) for p in profile_layouts):
        return 8, {"layout": listing_layout, "similar": True, "max": 15}
    return 0, {"layout": listing_layout, "reason": "户型不匹配", "max": 15}


def _same_rooms(a: str, b: str) -> bool:
    import re
    def rooms(s):
        m = re.search(r"(\d+)室", s)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)居", s)
        if m:
            return int(m.group(1))
        return None
    ra, rb = rooms(a), rooms(b)
    return ra is not None and ra == rb


def calc_environment_match(listing: Listing, env: dict) -> tuple[int, dict]:
    """环境偏好匹配，满分 15"""
    if not env:
        return 5, {"reason": "无环境偏好", "max": 15}

    text = f"{listing.title or ''} {listing.content or ''}"
    score = 0
    hits = []

    if env.get("quiet_required"):
        quiet_keywords = ["安静", "不临街", "小区内部", "非临街"]
        if any(k in text for k in quiet_keywords):
            score += 5
            hits.append("quiet_hit")
        elif any(k in text for k in ["临街", "高架", "施工"]):
            score += 0
            hits.append("quiet_miss")
        else:
            score += 3

    if env.get("lighting_required"):
        light_keywords = ["南向", "朝南", "采光", "南北通透", "飘窗", "明卫"]
        if any(k in text for k in light_keywords):
            score += 5
            hits.append("light_hit")
        else:
            score += 2

    if env.get("no_handshake"):
        # 简化：默认非握手楼
        score += 5
        hits.append("handshake_default_pass")

    return min(15, score), {"hits": hits, "matched_score": score, "max": 15}


def calc_keyword_match(listing: Listing, keywords: dict) -> tuple[int, dict]:
    """关键词匹配（含 must_have / exclude）。满分 10"""
    if not keywords:
        return 5, {"reason": "无关键词配置", "max": 10}

    text = f"{listing.title or ''} {listing.content or ''}"
    must_have = keywords.get("must_have", [])
    exclude = keywords.get("exclude", [])

    score = 5  # 基础分
    hit_must = []
    hit_exclude = []

    for kw in must_have:
        if kw in text:
            score += 2
            hit_must.append(kw)

    for kw in exclude:
        if kw in text:
            score -= 5
            hit_exclude.append(kw)

    score = max(0, min(10, score))
    return score, {
        "must_have_hits": hit_must,
        "exclude_hits": hit_exclude,
        "score": score,
        "max": 10,
    }


@dataclass
class MatchResult:
    match_score: int
    personalized_score: int
    price_match: int
    commute_match: int
    area_match: int
    layout_match: int
    environment_match: int
    keyword_match: int
    evidence: dict = field(default_factory=dict)


async def calculate_match(
    db: AsyncSession,
    redis,
    listing: Listing,
    profile: Profile,
    general_score: int | None = None,
) -> MatchResult:
    """计算房源对画像的匹配度"""
    # 价格
    p_score, p_ev = calc_price_match(listing.price, profile.budget_min, profile.budget_max)
    # 通勤
    c_score, c_ev = await calc_commute_match(redis, listing, profile)
    # 区域
    a_score, a_ev = calc_area_match(listing.area_name, profile.areas or [])
    # 户型
    l_score, l_ev = calc_layout_match(listing.layout, profile.layouts or [])
    # 环境
    e_score, e_ev = calc_environment_match(listing, profile.environment or {})
    # 关键词
    k_score, k_ev = calc_keyword_match(listing, profile.keywords or {})

    match_score = p_score + c_score + a_score + l_score + e_score + k_score

    if general_score is None:
        # 从 listing_scores 表查
        from sqlalchemy import select
        stmt = select(ListingScore.general_score).where(ListingScore.listing_id == listing.id)
        general_score = (await db.execute(stmt)).scalar() or 50

    personalized_score = round(general_score * 0.6 + match_score * 0.4)

    return MatchResult(
        match_score=match_score,
        personalized_score=personalized_score,
        price_match=p_score,
        commute_match=c_score,
        area_match=a_score,
        layout_match=l_score,
        environment_match=e_score,
        keyword_match=k_score,
        evidence={
            "price": p_ev, "commute": c_ev, "area": a_ev,
            "layout": l_ev, "environment": e_ev, "keyword": k_ev,
        },
    )

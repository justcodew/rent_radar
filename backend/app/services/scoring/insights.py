"""LLM 深度房源洞察（"老广朋友"口吻）

区别于 ai_engine.py 的浅层分析（图片/描述/环境）：
- insights.py 把帖子全文 + 提取字段一起喂给 LLM
- 让 LLM 扮演"在该城市住了 10 年的懂行朋友"
- 输出结构化洞察：小区画像、优缺点、砍价建议、推荐结论

输出 schema（InsightsResult）：
{
  "community_profile": "小区画像",
  "pros": ["5 个真实优点"],
  "cons": ["5 个潜在缺陷"],
  "price_verdict": "价位评价",
  "tips": ["3 条砍价/避坑建议"],
  "recommendation": "值得看/谨慎看/别看",
  "summary": "一句话总结",
  "confidence": 0.0-1.0
}
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger
from app.models.listing import Listing
from app.models.score import ListingScore
from app.services.scoring.ai_engine import check_budget

logger = get_logger(__name__)

REDIS_INSIGHTS_CACHE_KEY = "ai:insights:{listing_id}"

# 缓存 30 天（洞察比浅层分析贵，缓存更久）
INSIGHTS_CACHE_TTL = 30 * 86400


class InsightsError(Exception):
    pass


CITY_PERSONA = {
    "广州": "老广",
    "北京": "北漂老炮儿",
    "上海": "上海老克勒",
    "深圳": "深圳土著",
    "杭州": "杭州老底子",
}


def _build_prompt(listing: Listing, area_avg_price: int | None) -> tuple[str, str]:
    """构造 system + user prompt，返回 (system, user)"""
    city = "广州"
    persona = CITY_PERSONA.get(city, "本地朋友")

    system = (
        f"你是一个在广州生活了 10 年的「{persona}」，对各小区、地铁、商圈、楼龄门儿清。"
        f"现在帮一个准备租房的朋友客观分析一套房源，用朋友聊天的口吻，"
        f"专业但接地气，不绕弯子。"
        f"严格按 JSON 格式输出，所有字段都要填，没有的也写「不确定」。"
    )

    fields_summary = []
    if listing.area_name: fields_summary.append(f"区域={listing.area_name}")
    if listing.layout: fields_summary.append(f"户型={listing.layout}")
    if listing.floor_info: fields_summary.append(f"楼层={listing.floor_info}")
    if listing.orientation: fields_summary.append(f"朝向={listing.orientation}")
    if listing.price: fields_summary.append(f"租金={listing.price}元/月")
    if listing.size_sqm: fields_summary.append(f"面积={listing.size_sqm}㎡")
    if area_avg_price:
        deviation = round((listing.price - area_avg_price) / area_avg_price * 100, 1) if listing.price and area_avg_price else None
        fields_summary.append(f"区域均价={area_avg_price}元（偏离 {deviation}%）" if deviation else f"区域均价={area_avg_price}元")

    fields_str = " · ".join(fields_summary) if fields_summary else "（帖子未提取到结构化字段）"
    title = (listing.title or "").strip() or "（无标题）"
    content = (listing.content or "").strip()[:2500] or "（无正文）"

    user = f"""帮我看看这套房子：

【标题】{title}
【关键字段】{fields_str}
【正文】
{content}

请用「{persona}」的口吻告诉我（一定要 JSON 格式）：
{{
  "community_profile": "如果你认识这小区/这片区域，说说它什么年代建的、什么类型（电梯房/步梯房/公寓/小区）、住什么人多、整体定位怎么样。不认识就说不熟悉。",
  "surroundings": {{
    "subway": [{{"name": "地铁站名+线路（如'3号线体育西路'）", "walk_min": 步行分钟数估算整数, "confidence": 0.0-1.0}}],
    "school": [{{"name": "学校名", "type": "小学/中学/大学", "walk_min": 估算步行分钟数}}],
    "hospital": [{{"name": "医院名", "level": "三甲/二甲/社区", "walk_min": 估算步行分钟数}}],
    "mall": [{{"name": "商场/超市/菜市场名", "type": "商场/超市/菜市场", "walk_min": 估算步行分钟数}}]
  }},
  "surroundings_confidence": 0.0-1.0,
  "pros": ["5 条真实优点，要具体（比如'5 分钟到 3 号线 X 站'而不是'交通便利'）。结合地段+帖子+你的常识推理。"],
  "cons": ["5 条潜在坑，帖子可能没明说的：噪音/采光/物业/楼龄/邻居/楼层/朝向/隐蔽费用等。站在租客角度提醒。"],
  "price_verdict": "这价位在这地段算贵/合理/便宜？给出依据。",
  "tips": ["3 条具体建议：砍价幅度、签合同注意事项、看房要重点检查什么。"],
  "recommendation": "值得看 / 谨慎看 / 别看（三选一）",
  "summary": "一句话总结，30 字以内，像朋友最后给的判断。",
  "confidence": 0.0-1.0  你对这套房源分析的把握度
}}

重要：surroundings 字段必须严格按上面结构输出，每类至少给 1 条（最多 3 条），不认识的写空数组 []。距离只能给粗估步行分钟数，不要假装精确。confidence 低的项你就在该项的 confidence 字段如实写低（如 0.3），整体把握度反映到 surroundings_confidence。

记住：用「{persona}」的口吻，专业、直接、接地气。不要客套话。"""
    return system, user


def _parse_insights(content: str) -> dict[str, Any]:
    """从 LLM 输出里解析 JSON，失败就提取子串"""
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
    return {"raw": content, "parse_error": True}


def _coerce_float(v: Any, default: float = 0.0) -> float:
    try:
        if v is None:
            return default
        return float(v)
    except (TypeError, ValueError):
        return default


def _coerce_int(v: Any, default: int = 0) -> int:
    try:
        if v is None:
            return default
        return int(float(v))
    except (TypeError, ValueError):
        return default


def _normalize_surroundings(raw: Any) -> dict[str, list[dict[str, Any]]]:
    """把 LLM 吐出来的 surroundings 字段规整成统一 schema"""
    if not isinstance(raw, dict):
        return {"subway": [], "school": [], "hospital": [], "mall": []}

    out: dict[str, list[dict[str, Any]]] = {"subway": [], "school": [], "hospital": [], "mall": []}
    for key in out:
        items = raw.get(key)
        if not isinstance(items, list):
            continue
        for it in items[:3]:
            if not isinstance(it, dict):
                continue
            name = (it.get("name") or "").strip()
            if not name:
                continue
            entry = {
                "name": name,
                "walk_min": _coerce_int(it.get("walk_min"), 0),
            }
            # 各类型特有字段
            for opt_field in ("type", "level", "line"):
                if opt_field in it and it[opt_field]:
                    entry[opt_field] = str(it[opt_field]).strip()
            if "confidence" in it:
                entry["confidence"] = _coerce_float(it["confidence"], 0.5)
            out[key].append(entry)
    return out


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
async def _call_llm_json(system: str, user: str, max_tokens: int = 2200) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.4,  # 稍高一点让"老广"口吻更自然
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return _parse_insights(content)


async def _get_area_avg_price(db: AsyncSession, area_name: str | None, layout: str | None) -> int | None:
    """查同区域均价（来自 listings 表的最近抓取）"""
    if not area_name:
        return None
    stmt = select(func.avg(Listing.price), func.count(Listing.id)).where(
        Listing.area_name == area_name,
        Listing.price.isnot(None),
        Listing.price > 0,
    )
    if layout:
        stmt = stmt.where(Listing.layout == layout)
    row = (await db.execute(stmt)).first()
    if row and row[1] >= 3:
        return int(row[0])
    return None


async def generate_insights(
    db: AsyncSession,
    redis,
    listing_id: UUID,
    force: bool = False,
) -> dict[str, Any]:
    """生成深度洞察"""
    cache_key = REDIS_INSIGHTS_CACHE_KEY.format(listing_id=listing_id)

    # 1. 缓存
    if not force:
        cached = await redis.get(cache_key)
        if cached:
            return {**json.loads(cached), "from_cache": True}

    # 2. 预算检查
    if not await check_budget(redis):
        return {"skipped": True, "reason": "AI 月度/日度预算超出"}

    # 3. LLM 配置检查
    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        return {"skipped": True, "reason": "LLM 未配置"}

    # 4. 加载房源
    listing = (await db.execute(select(Listing).where(Listing.id == listing_id))).scalar_one_or_none()
    if not listing:
        return {"skipped": True, "reason": "房源不存在"}

    # 5. 区域均价（用于 prompt 上下文 + 后续比价）
    area_avg = await _get_area_avg_price(db, listing.area_name, listing.layout)

    # 6. 调 LLM
    system, user = _build_prompt(listing, area_avg)
    try:
        result = await _call_llm_json(system, user)
    except Exception as e:
        logger.error("insights llm call failed", listing_id=str(listing_id), error=str(e))
        return {"skipped": True, "reason": f"LLM 调用失败：{e}"}

    # 7. 估算成本（深度分析比浅层贵：~¥0.15/次）
    estimated_cost = 0.15
    now = datetime.now(timezone.utc)
    monthly_key = "ai:cost:monthly:" + now.strftime("%Y%m")
    daily_key = "ai:cost:daily:" + now.strftime("%Y%m%d")
    await redis.incrbyfloat(monthly_key, estimated_cost)
    await redis.incrbyfloat(daily_key, estimated_cost)
    await redis.expire(monthly_key, 31 * 86400)
    await redis.expire(daily_key, 86400)

    insights = {
        "community_profile": result.get("community_profile", "不确定"),
        "surroundings": _normalize_surroundings(result.get("surroundings")),
        "surroundings_confidence": _coerce_float(result.get("surroundings_confidence"), 0.5),
        "pros": result.get("pros", [])[:5],
        "cons": result.get("cons", [])[:5],
        "price_verdict": result.get("price_verdict", "不确定"),
        "tips": result.get("tips", [])[:3],
        "recommendation": result.get("recommendation", "不确定"),
        "summary": result.get("summary", ""),
        "confidence": float(result.get("confidence", 0.6)),
        "area_avg_price": area_avg,
        "model": settings.LLM_MODEL,
        "analyzed_at": now.isoformat(),
        "estimated_cost_cny": estimated_cost,
    }

    # 8. 持久化到 ListingScore.ai_insights
    score_row = (await db.execute(select(ListingScore).where(ListingScore.listing_id == listing_id))).scalar_one_or_none()
    if score_row:
        score_row.ai_insights = insights
        await db.commit()

    # 9. 缓存 30 天
    await redis.set(cache_key, json.dumps(insights, ensure_ascii=False), ex=INSIGHTS_CACHE_TTL)

    return insights

"""LLM 自然语言选房（需求 → 推荐小区 + 匹配房源）

流程：
1. 用户给一段自由描述（"我在珠江新城上班，预算 4000，地铁通勤 30 分钟内"）
2. LLM 一次性输出：
   - 结构化提取（预算/区域/户型/面积/通勤/关键词/生活方式）
   - 3-5 个匹配小区（带估价区间、推荐理由、亮点、坑点）
3. 后端用提取出的参数查 listings 表，返回实际匹配的房源

成本：~¥0.15/次，描述 hash 缓存 1 天。
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, or_, desc
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger
from app.database import AsyncSession
from app.models.listing import Listing
from app.models.score import ListingScore
from app.schemas.listing import ListingOut
from app.services.scoring.ai_engine import check_budget
from app.services.scoring.insights import CITY_PERSONA, _parse_insights

logger = get_logger(__name__)

REDIS_NEED_MATCH_KEY = "ai:need_match:{sig}"
NEED_MATCH_CACHE_TTL = 1 * 86400  # 1 天


class NeedMatchError(Exception):
    pass


def _sig(description: str, city: str) -> str:
    norm = json.dumps({"d": description.strip(), "c": city}, ensure_ascii=True)
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


def _build_prompt(description: str, city: str, known_areas: list[str]) -> tuple[str, str]:
    persona = CITY_PERSONA.get(city, "本地朋友")
    areas_str = "、".join(known_areas[:20]) if known_areas else "（数据库无该城市区域信息）"

    system = (
        f"你是一个在{city}生活了 10 年的「{persona}」 + 资深租房顾问。"
        f"用户会用一句话描述自己的租房需求（可能很口语化、不完整）。"
        f"你的任务："
        f"1) 提取出结构化需求；"
        f"2) 基于你的{city}地段常识，推荐 3-5 个具体小区或片区。"
        f"严格按 JSON 输出。"
    )

    user = f"""【用户需求】
{description}

【{city} 数据库里已有的区域】
{areas_str}

请输出 JSON：
{{
  "extracted": {{
    "budget_min": int 或 null,
    "budget_max": int 或 null,
    "areas": ["区域名，必须从上面列表里选，没有就空数组"],
    "layouts": ["户型，如 一室一厅 / 两室一厅"],
    "size_min": int 或 null,
    "size_max": int 或 null,
    "commute_target": "上班/上学地点，可空",
    "commute_max_min": int 或 null,
    "commute_mode": "地铁/公交/骑行/步行",
    "must_have": ["硬性关键词，如 电梯/民水民电/押一付一/允许宠物"],
    "exclude": ["排除关键词，如 中介/隔断/合租"],
    "lifestyle": "一句话总结用户画像，如'珠江新城上班的单身白领，重通勤轻面积'"
  }},
  "communities": [
    {{
      "name": "小区或片区名",
      "area": "所在区域",
      "est_price_range": "如 '3000-4000元/一室一厅'",
      "reason": "为什么推荐给这位用户（具体到通勤/配套/价位）",
      "highlights": ["2-3 个亮点"],
      "watch_outs": ["1-2 个潜在坑"]
    }}
  ]
}}

要求：
- communities 必须 3-5 个，针对用户需求差异化（不要全是同地段）。
- 如果用户需求里有明确的上班地点+通勤时间，必须以通勤时间为主轴推荐。
- 如果预算明显不现实，第三个小区可以放一个"妥协方案"（如城中村 / 合租 / 远一点），reason 里说明。
- 不要瞎编地标，不确定的小区宁可少写。
- 输出纯 JSON，不要 markdown 代码块。
"""
    return system, user


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
async def _call_llm_json(system: str, user: str, max_tokens: int = 1800) -> dict:
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
        "temperature": 0.4,
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


async def _get_known_areas(db: AsyncSession, city: str) -> list[str]:
    """数据库里该城市已有的区域列表（用于让 LLM 选择真实区域）"""
    # 当前 schema 没有 city 字段，直接全部 distinct area_name（数据都是广州）
    stmt = select(Listing.area_name).where(
        Listing.area_name.isnot(None),
        Listing.status == "active",
    ).distinct()
    rows = (await db.execute(stmt)).scalars().all()
    return sorted([r for r in rows if r])


def _normalize_extracted(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for k in ("commute_target", "commute_mode", "lifestyle"):
        if isinstance(raw.get(k), str):
            out[k] = raw[k].strip()
    for k in ("budget_min", "budget_max", "size_min", "size_max", "commute_max_min"):
        v = raw.get(k)
        if v is None or v == "":
            continue
        try:
            out[k] = int(float(v))
        except (TypeError, ValueError):
            pass
    for k in ("areas", "layouts", "must_have", "exclude"):
        v = raw.get(k)
        if isinstance(v, list):
            out[k] = [str(x).strip() for x in v if str(x).strip()]
    return out


def _normalize_communities(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out = []
    for c in raw[:5]:
        if not isinstance(c, dict):
            continue
        name = (c.get("name") or "").strip()
        if not name:
            continue
        item = {
            "name": name,
            "area": (c.get("area") or "").strip(),
            "est_price_range": (c.get("est_price_range") or "").strip(),
            "reason": (c.get("reason") or "").strip(),
        }
        if isinstance(c.get("highlights"), list):
            item["highlights"] = [str(x).strip() for x in c["highlights"] if str(x).strip()][:3]
        if isinstance(c.get("watch_outs"), list):
            item["watch_outs"] = [str(x).strip() for x in c["watch_outs"] if str(x).strip()][:2]
        out.append(item)
    return out


async def _query_listings(
    db: AsyncSession, ext: dict[str, Any], limit: int = 12
) -> list[dict[str, Any]]:
    """根据 LLM 提取的参数查 listings 表"""
    stmt = (
        select(Listing, ListingScore.general_score, ListingScore.risk_tags)
        .outerjoin(ListingScore, ListingScore.listing_id == Listing.id)
        .where(Listing.status == "active")
    )

    bmin = ext.get("budget_min")
    bmax = ext.get("budget_max")
    if bmin is not None:
        stmt = stmt.where(Listing.price >= bmin)
    if bmax is not None:
        stmt = stmt.where(Listing.price <= bmax)

    areas = ext.get("areas") or []
    if areas:
        stmt = stmt.where(Listing.area_name.in_(areas))

    layouts = ext.get("layouts") or []
    if layouts:
        or_clauses = []
        for lay in layouts:
            or_clauses.append(Listing.layout.ilike(f"%{lay}%"))
        stmt = stmt.where(or_(*or_clauses))

    smin = ext.get("size_min")
    smax = ext.get("size_max")
    if smin is not None:
        stmt = stmt.where(Listing.size_sqm >= smin)
    if smax is not None:
        stmt = stmt.where(Listing.size_sqm <= smax)

    excludes = ext.get("exclude") or []
    for kw in excludes:
        stmt = stmt.where(~Listing.content.ilike(f"%{kw}%"))

    must_have = ext.get("must_have") or []
    if must_have:
        # 至少命中一个 must_have 关键词
        or_clauses = [Listing.content.ilike(f"%{kw}%") for kw in must_have]
        stmt = stmt.where(or_(*or_clauses))

    stmt = stmt.order_by(desc(ListingScore.general_score), desc(Listing.posted_at)).limit(limit)
    rows = (await db.execute(stmt)).all()

    out = []
    for listing, score, risk_tags in rows:
        item = ListingOut.model_validate(listing).model_dump(mode="json")
        item["general_score"] = score
        item["risk_tags"] = risk_tags or []
        out.append(item)
    return out


async def match_listings_by_need(
    db: AsyncSession,
    redis,
    description: str,
    city: str = "广州",
    limit: int = 12,
    force: bool = False,
) -> dict[str, Any]:
    sig = _sig(description, city)
    cache_key = REDIS_NEED_MATCH_KEY.format(sig=sig)

    if not force:
        cached = await redis.get(cache_key)
        if cached:
            cached_data = json.loads(cached)
            # 缓存里也要重新查 listings（数据可能更新）
            listings = await _query_listings(db, cached_data.get("extracted", {}), limit)
            return {**cached_data, "listings": listings, "from_cache": True}

    if not await check_budget(redis):
        return {"skipped": True, "reason": "AI 月度/日度预算超出"}

    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        return {"skipped": True, "reason": "LLM 未配置"}

    known_areas = await _get_known_areas(db, city)
    system, user = _build_prompt(description, city, known_areas)

    try:
        result = await _call_llm_json(system, user)
    except Exception as e:
        logger.error("need_match llm failed", sig=sig, error=str(e))
        return {"skipped": True, "reason": f"LLM 调用失败：{e}"}

    estimated_cost = 0.15
    now = datetime.now(timezone.utc)
    monthly_key = "ai:cost:monthly:" + now.strftime("%Y%m")
    daily_key = "ai:cost:daily:" + now.strftime("%Y%m%d")
    await redis.incrbyfloat(monthly_key, estimated_cost)
    await redis.incrbyfloat(daily_key, estimated_cost)
    await redis.expire(monthly_key, 31 * 86400)
    await redis.expire(daily_key, 86400)

    extracted = _normalize_extracted(result.get("extracted"))
    communities = _normalize_communities(result.get("communities"))
    listings = await _query_listings(db, extracted, limit)

    response = {
        "extracted": extracted,
        "communities": communities,
        "listings": listings,
        "city": city,
        "description": description.strip(),
        "model": settings.LLM_MODEL,
        "analyzed_at": now.isoformat(),
        "estimated_cost_cny": estimated_cost,
    }

    # 只缓存 LLM 输出部分，listings 实时查
    cache_payload = {
        "extracted": extracted,
        "communities": communities,
        "city": city,
        "description": description.strip(),
        "model": settings.LLM_MODEL,
        "analyzed_at": now.isoformat(),
        "estimated_cost_cny": estimated_cost,
    }
    await redis.set(cache_key, json.dumps(cache_payload, ensure_ascii=False), ex=NEED_MATCH_CACHE_TTL)

    return response

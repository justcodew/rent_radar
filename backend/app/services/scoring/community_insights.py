"""LLM 小区综合测评（用户输入驱动）

区别于 listing-based insights（基于一篇具体帖子）：
- community_insights 接受任意稀疏输入：哪怕只给个小区名也能输出
- 没有 listing 全文做上下文，LLM 完全靠"城市知识 + 区域知识 + 常识"
- confidence 通常会比 listing-based 低，需要在 prompt 里强制让模型自评
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import select, func
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger
from app.database import AsyncSession
from app.models.listing import Listing
from app.services.scoring.ai_engine import check_budget
from app.services.scoring.insights import (
    CITY_PERSONA,
    _coerce_float,
    _coerce_int,
    _normalize_surroundings,
    _parse_insights,
)

logger = get_logger(__name__)

REDIS_COMMUNITY_CACHE_KEY = "ai:community:{sig}"
COMMUNITY_CACHE_TTL = 7 * 86400  # 7 天


class CommunityInsightsError(Exception):
    pass


def _sig(payload: dict[str, Any]) -> str:
    """对输入做签名，作为缓存 key（顺序无关）"""
    norm = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(norm.encode()).hexdigest()[:16]


def _build_prompt(payload: dict[str, Any], area_avg_price: int | None) -> tuple[str, str]:
    city = payload.get("city") or "广州"
    persona = CITY_PERSONA.get(city, "本地朋友")

    system = (
        f"你是一个在{city}生活了 10 年的「{persona}」，对各小区、地铁、商圈、楼龄门儿清。"
        f"现在帮一个准备租房/买房的朋友客观分析一个小区或住处，用朋友聊天的口吻，"
        f"专业但接地气，不绕弯子。"
        f"注意：用户输入的信息可能很稀疏（甚至只给个名字），你需要靠你的城市常识和推理能力补全判断，"
        f"不确定的地方就用 confidence 字段如实反映，不要瞎编具体数据。"
        f"严格按 JSON 格式输出，所有字段都要填。"
    )

    # 拼接用户给的事实片段
    facts = []
    name = (payload.get("community_name") or "").strip()
    if name:
        facts.append(f"小区/地名 = {name}")
    if payload.get("area_name"):
        facts.append(f"区域 = {payload['area_name']}")
    if payload.get("layout"):
        facts.append(f"户型 = {payload['layout']}")
    if payload.get("price") is not None:
        facts.append(f"价格 = {payload['price']}元/月")
    if payload.get("size_sqm") is not None:
        facts.append(f"面积 = {payload['size_sqm']}㎡")
    if payload.get("floor_info"):
        facts.append(f"楼层 = {payload['floor_info']}")
    if payload.get("orientation"):
        facts.append(f"朝向 = {payload['orientation']}")
    if payload.get("extra_note"):
        facts.append(f"补充说明 = {payload['extra_note']}")

    facts_str = " · ".join(facts) if facts else "（用户只给了一个名字，可能不全）"

    price_hint = ""
    if area_avg_price:
        price_hint = f"\n【参考】{payload.get('area_name') or city} 同区域均价 ≈ {area_avg_price}元/月"

    user = f"""帮我看看这个地方：
【用户给的片段】{facts_str}{price_hint}

请用「{persona}」的口吻告诉我（一定要 JSON 格式）：
{{
  "community_profile": "如果你认识这小区/这片区域，说说它什么年代建的、什么类型（电梯房/步梯房/公寓/小区/城中村）、住什么人多、整体定位。完全不认识就如实说'对这小区没印象'，靠周边信息推断。",
  "surroundings": {{
    "subway": [{{"name": "地铁站名+线路", "walk_min": 估算步行分钟数整数, "confidence": 0.0-1.0}}],
    "school": [{{"name": "学校名", "type": "小学/中学/大学", "walk_min": 步行分钟}}],
    "hospital": [{{"name": "医院名", "level": "三甲/二甲/社区", "walk_min": 步行分钟}}],
    "mall": [{{"name": "商场/超市/菜场名", "type": "商场/超市/菜场", "walk_min": 步行分钟}}]
  }},
  "surroundings_confidence": 0.0-1.0,
  "pros": ["3-5 条优点（信息不全就少写，靠地段+常识推理）"],
  "cons": ["3-5 条潜在坑（楼龄/噪音/采光/物业/邻居/通勤等，站在租客角度）"],
  "price_verdict": "用户给了价格就评价贵/合理/便宜；没给就说'用户未提供价格，无法评价'",
  "tips": ["2-3 条看房/砍价/避坑建议"],
  "recommendation": "值得看 / 谨慎看 / 别看 / 不确定（四选一，信息严重不足就选不确定）",
  "summary": "一句话总结，30 字以内",
  "confidence": 0.0-1.0
}}

重要：
- surroundings 每类至少给 1 条（最多 3 条），完全不认识写 []，对应类别 confidence 写低。
- 不确定的距离只能给粗估步行分钟数。
- 信息严重不全（比如只有小区名还是冷门小区）就把整体 confidence 写 0.3-0.5，别装得很懂。"""

    return system, user


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


async def _get_area_avg_price(db: AsyncSession, area_name: str | None) -> int | None:
    if not area_name:
        return None
    stmt = select(func.avg(Listing.price), func.count(Listing.id)).where(
        Listing.area_name == area_name,
        Listing.price.isnot(None),
        Listing.price > 0,
    )
    row = (await db.execute(stmt)).first()
    if row and row[1] >= 3:
        return int(row[0])
    return None


async def generate_community_insights(
    db: AsyncSession,
    redis,
    payload: dict[str, Any],
    force: bool = False,
) -> dict[str, Any]:
    """生成小区测评"""
    sig = _sig(payload)
    cache_key = REDIS_COMMUNITY_CACHE_KEY.format(sig=sig)

    # Redis 不可用时跳过缓存 + 预算检查
    if redis and not force:
        try:
            cached = await redis.get(cache_key)
            if cached:
                return {**json.loads(cached), "from_cache": True}
        except Exception:
            pass

    if redis:
        try:
            if not await check_budget(redis):
                return {"skipped": True, "reason": "AI 月度/日度预算超出"}
        except Exception:
            pass

    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        return {"skipped": True, "reason": "LLM 未配置"}

    area_avg = await _get_area_avg_price(db, payload.get("area_name"))

    system, user = _build_prompt(payload, area_avg)
    try:
        result = await _call_llm_json(system, user)
    except Exception as e:
        logger.error("community insights llm failed", sig=sig, error=str(e))
        return {"skipped": True, "reason": f"LLM 调用失败：{e}"}

    estimated_cost = 0.15
    now = datetime.now(timezone.utc)
    if redis:
        try:
            monthly_key = "ai:cost:monthly:" + now.strftime("%Y%m")
            daily_key = "ai:cost:daily:" + now.strftime("%Y%m%d")
            await redis.incrbyfloat(monthly_key, estimated_cost)
            await redis.incrbyfloat(daily_key, estimated_cost)
            await redis.expire(monthly_key, 31 * 86400)
            await redis.expire(daily_key, 86400)
        except Exception:
            pass

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
        "confidence": _coerce_float(result.get("confidence"), 0.5),
        "area_avg_price": area_avg,
        "input": payload,
        "model": settings.LLM_MODEL,
        "analyzed_at": now.isoformat(),
        "estimated_cost_cny": estimated_cost,
    }

    if redis:
        try:
            await redis.set(cache_key, json.dumps(insights, ensure_ascii=False), ex=COMMUNITY_CACHE_TTL)
        except Exception:
            pass
    return insights

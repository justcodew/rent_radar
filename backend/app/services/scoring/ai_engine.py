"""AI 增强评分（按需触发）

设计原则：
1. 默认不触发，只在用户访问详情页或主动调用时跑
2. 结果缓存到 Redis（TTL 7 天）
3. 每月预算硬上限，超额降级到规则版
4. 单个房源每月最多触发 1 次

实现：
- 调用 OpenAI 兼容 API（OpenAI / Claude / 国产模型均可）
- 图片用 base64 编码走 vision 模型
- 文本用 chat completion
- 失败重试 2 次，预算计数只在成功时累加
"""
from __future__ import annotations

import base64
import json
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.core.logging import get_logger
from app.models.listing import Listing

logger = get_logger(__name__)

REDIS_AI_CACHE_KEY = "ai:score:{listing_id}"
REDIS_AI_MONTHLY_COUNTER = "ai:cost:monthly:{ym}"
REDIS_AI_DAILY_COUNTER = "ai:cost:daily:{ymd}"


class AIBudgetExceeded(Exception):
    """AI 预算超出"""


async def check_budget(redis) -> bool:
    """检查月度/日度预算是否超出"""
    now = datetime.now(timezone.utc)
    monthly_key = REDIS_AI_MONTHLY_COUNTER.format(ym=now.strftime("%Y%m"))
    daily_key = REDIS_AI_DAILY_COUNTER.format(ymd=now.strftime("%Y%m%d"))

    monthly = float(await redis.get(monthly_key) or 0)
    daily = float(await redis.get(daily_key) or 0)

    if monthly >= settings.LLM_MONTHLY_BUDGET_CNY:
        logger.warning("ai monthly budget exceeded", monthly=monthly)
        return False
    if daily >= settings.LLM_DAILY_BUDGET_CNY:
        logger.warning("ai daily budget exceeded", daily=daily)
        return False
    return True


async def get_cached(redis, listing_id: UUID) -> dict | None:
    raw = await redis.get(REDIS_AI_CACHE_KEY.format(listing_id=listing_id))
    if raw:
        return json.loads(raw)
    return None


async def analyze_listing_with_ai(
    db: AsyncSession,
    redis,
    listing_id: UUID,
    force: bool = False,
) -> dict[str, Any]:
    """对房源进行 AI 增强分析

    Returns:
        {
            "image_analysis": {...},
            "environment_analysis": {...},
            "description_analysis": {...},
            "estimated_cost_cny": 0.15,
            "model": "...",
        }
    """
    # 1. 检查缓存
    if not force:
        cached = await get_cached(redis, listing_id)
        if cached:
            logger.info("ai cache hit", listing_id=str(listing_id))
            return cached

    # 2. 检查预算
    if not await check_budget(redis):
        raise AIBudgetExceeded("AI 月度或日度预算超出")

    # 3. 检查 LLM 配置
    if not settings.LLM_API_KEY or not settings.LLM_BASE_URL:
        logger.warning("llm not configured, skip ai analysis")
        return {
            "skipped": True,
            "reason": "LLM 未配置（请在 .env 设置 LLM_API_KEY 和 LLM_BASE_URL）",
        }

    # 4. 加载房源
    from sqlalchemy import select
    listing = (await db.execute(select(Listing).where(Listing.id == listing_id))).scalar_one_or_none()
    if not listing:
        return {"skipped": True, "reason": "房源不存在"}

    # 5. 估算成本（粗算：每张图 ¥0.03 + 文本 ¥0.05）
    img_count = min(5, len(listing.image_urls or []))
    estimated_cost = round(0.05 + img_count * 0.03, 2)

    # 6. 调用 LLM（文本+视觉）
    try:
        image_analysis = await _analyze_images(listing)
        description_analysis = await _analyze_description(listing)
        environment_analysis = await _analyze_environment(listing, image_analysis)
    except Exception as e:
        logger.error("llm call failed", error=str(e))
        return {"skipped": True, "reason": f"LLM 调用失败：{e}"}

    # 7. 写入预算计数器（仅成功时）
    now = datetime.now(timezone.utc)
    monthly_key = REDIS_AI_MONTHLY_COUNTER.format(ym=now.strftime("%Y%m"))
    daily_key = REDIS_AI_DAILY_COUNTER.format(ymd=now.strftime("%Y%m%d"))
    await redis.incrbyfloat(monthly_key, estimated_cost)
    await redis.incrbyfloat(daily_key, estimated_cost)
    await redis.expire(monthly_key, 31 * 86400)
    await redis.expire(daily_key, 86400)

    result = {
        "image_analysis": image_analysis,
        "description_analysis": description_analysis,
        "environment_analysis": environment_analysis,
        "estimated_cost_cny": estimated_cost,
        "model": settings.LLM_MODEL,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
    }

    # 8. 持久化到 DB（让下次不调 LLM 也能展示）
    from app.models.score import ListingScore
    from sqlalchemy import select as sel
    score_row = (await db.execute(sel(ListingScore).where(ListingScore.listing_id == listing_id))).scalar_one_or_none()
    if score_row:
        score_row.ai_evidence = result
        await db.commit()

    # 9. 缓存 7 天
    await redis.set(
        REDIS_AI_CACHE_KEY.format(listing_id=listing_id),
        json.dumps(result, ensure_ascii=False),
        ex=7 * 86400,
    )

    return result


@retry(stop=stop_after_attempt(2), wait=wait_exponential(min=1, max=4), reraise=True)
async def _call_llm(messages: list[dict], max_tokens: int = 800) -> dict:
    """通用 LLM 调用（OpenAI 兼容）"""
    headers = {
        "Authorization": f"Bearer {settings.LLM_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.LLM_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.2,
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            f"{settings.LLM_BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        # 尝试解析 JSON（让 LLM 严格输出 JSON 格式）
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            # 提取 JSON 子串
            import re
            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                return json.loads(m.group(0))
            return {"raw": content}


async def _download_image_as_base64(url: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            return base64.b64encode(resp.content).decode()
    except Exception:
        return None


async def _analyze_images(listing: Listing) -> dict:
    """分析图片：实拍风格 / 装修新旧 / 是否网图"""
    urls = (listing.image_urls or [])[:3]  # 最多 3 张控制成本
    if not urls:
        return {"score": 12, "level": "无图片可分析", "details": "房源无图片"}

    # 文本+图片混合分析（OpenAI vision 风格）
    content_blocks = [
        {"type": "text", "text": (
            "请分析以下租房房源的图片，输出 JSON：\n"
            '{"is_real_photo": true/false, "is_showroom": true/false, '
            '"renovation_new": true/false, "has_watermark": true/false, '
            '"confidence": 0.0-1.0, "reason": "一句话说明"}\n'
            "实拍照片应有生活痕迹，样板间通常过于完美。"
        )},
    ]
    for url in urls:
        img_b64 = await _download_image_as_base64(url)
        if img_b64:
            content_blocks.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
            })

    messages = [{"role": "user", "content": content_blocks}]
    result = await _call_llm(messages, max_tokens=300)

    # 映射到分数
    is_real = result.get("is_real_photo", True)
    is_showroom = result.get("is_showroom", False)
    has_wm = result.get("has_watermark", False)
    confidence = result.get("confidence", 0.5)

    if is_real and not is_showroom and not has_wm:
        score = 16
        level = "实拍风格"
    elif is_showroom:
        score = 6
        level = "疑似样板间"
    elif has_wm:
        score = 8
        level = "图片有水印"
    else:
        score = 10
        level = "不确定"

    return {
        "score": score,
        "level": level,
        "confidence": confidence,
        "details": result.get("reason", ""),
        "analyzed_images": len(content_blocks) - 1,
    }


async def _analyze_description(listing: Listing) -> dict:
    """文本分析：是否模板话术 / 中介话术"""
    text = f"{listing.title or ''}\n{listing.content or ''}"[:1500]
    messages = [
        {"role": "system", "content": "你是租房信息分析助手，严格输出 JSON。"},
        {"role": "user", "content": (
            "判断以下租房帖子的描述，是否个人化（生活化、具体）还是模板/中介话术。\n"
            "输出 JSON：{\"is_personal\": true/false, \"is_template\": true/false, "
            "\"has_agent_signals\": true/false, \"quality_score\": 1-10, \"reason\": \"一句话\"}\n\n"
            f"帖子内容：\n{text}"
        )},
    ]
    result = await _call_llm(messages, max_tokens=200)

    quality = result.get("quality_score", 5)
    is_personal = result.get("is_personal", True)
    has_agent = result.get("has_agent_signals", False)

    if not is_personal or has_agent:
        score = max(2, quality // 2)
        level = "疑似模板/中介话术"
    else:
        score = quality + 5
        level = "个人化描述"

    return {
        "score": min(21, score),
        "level": level,
        "quality_score": quality,
        "details": result.get("reason", ""),
    }


async def _analyze_environment(listing: Listing, image_analysis: dict) -> dict:
    """环境推理：噪音/采光/楼间距（基于文本+图片分析结果）"""
    text = f"{listing.title or ''}\n{listing.content or ''}"[:1500]
    messages = [
        {"role": "system", "content": "你是租房环境分析助手，严格输出 JSON。"},
        {"role": "user", "content": (
            "根据帖子内容推断房源环境质量。输出 JSON：\n"
            '{"noise_level": "low/medium/high", "lighting": "good/medium/poor", '
            '"is_street_facing": true/false, "confidence": 0.0-1.0, '
            '"signals": ["命中的关键词"], "summary": "一句话"}\n\n'
            f"帖子内容：\n{text}"
        )},
    ]
    result = await _call_llm(messages, max_tokens=300)

    return {
        "noise_level": result.get("noise_level", "unknown"),
        "lighting": result.get("lighting", "unknown"),
        "is_street_facing": result.get("is_street_facing"),
        "signals": result.get("signals", []),
        "summary": result.get("summary", ""),
        "confidence": result.get("confidence", 0.5),
    }

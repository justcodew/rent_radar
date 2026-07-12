"""评分路由"""
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.response import ok
from app.database import get_db
from app.models.listing import Listing
from app.models.score import ListingScore
from app.services.scoring.rule_engine import calculate_listing_score, get_score_level
from app.services.scoring.ai_engine import analyze_listing_with_ai
from app.services.scoring.insights import generate_insights
from app.workers.celery_app import get_redis

router = APIRouter(prefix="/api/v1/scores", tags=["scores"])


@router.get("/{listing_id}")
async def get_score(listing_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ListingScore).where(ListingScore.listing_id == listing_id)
    )
    score = result.scalar_one_or_none()
    if not score:
        raise NotFoundError("该房源暂未评分")
    level, stars = get_score_level(score.general_score)
    return ok({
        "listing_id": str(score.listing_id),
        "general_score": score.general_score,
        "level": level,
        "stars": stars,
        "poster_score": score.poster_score,
        "listing_score": score.listing_score,
        "sub_scores": {
            "poster_frequency": score.poster_frequency_score,
            "poster_age": score.poster_age_score,
            "poster_diversity": score.poster_diversity_score,
            "poster_contact_reuse": score.poster_contact_reuse_score,
            "image_authenticity": score.image_authenticity_score,
            "description": score.description_score,
            "price_reasonable": score.price_reasonable_score,
            "info_completeness": score.info_completeness_score,
        },
        "risk_tags": score.risk_tags or [],
        "evidence": score.evidence or {},
        "ai_evidence": score.ai_evidence,
        "ai_insights": score.ai_insights,
        "score_version": score.score_version,
        "calculated_at": score.calculated_at.isoformat() if score.calculated_at else None,
    })


@router.post("/{listing_id}/recalculate")
async def recalculate_score(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """手动触发重新评分（开发/调试用）"""
    listing = (
        await db.execute(select(Listing).where(Listing.id == listing_id))
    ).scalar_one_or_none()
    if not listing:
        raise NotFoundError("房源不存在")

    result = await calculate_listing_score(db, listing)
    level, stars = get_score_level(result.general_score)
    return ok({
        "general_score": result.general_score,
        "level": level,
        "stars": stars,
        "sub_scores": {
            "poster_frequency": result.poster_frequency_score,
            "poster_age": result.poster_age_score,
            "poster_diversity": result.poster_diversity_score,
            "poster_contact_reuse": result.poster_contact_reuse_score,
            "image_authenticity": result.image_authenticity_score,
            "description": result.description_score,
            "price_reasonable": result.price_reasonable_score,
            "info_completeness": result.info_completeness_score,
        },
        "risk_tags": result.risk_tags,
        "evidence": result.evidence,
    })


@router.post("/{listing_id}/ai-analysis")
async def trigger_ai_analysis(
    listing_id: UUID,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """触发 AI 增强分析（按需，会消耗 LLM 预算）"""
    redis = await get_redis()
    result = await analyze_listing_with_ai(db, redis, listing_id, force=force)
    return ok(result)


@router.post("/{listing_id}/insights")
async def trigger_insights(
    listing_id: UUID,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """触发 LLM 深度洞察（懂行朋友口吻，~¥0.15/次）

    返回结构化洞察：小区画像、5 优 5 缺、价位评价、3 条建议、推荐结论。
    结果会缓存 30 天，并持久化到 listing_scores.ai_insights。
    """
    redis = await get_redis()
    result = await generate_insights(db, redis, listing_id, force=force)
    return ok(result)

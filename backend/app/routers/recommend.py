"""推荐路由"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import BadRequestError
from app.core.response import ok
from app.core.security import get_current_user
from app.database import get_db
from app.models.listing import Listing
from app.models.profile import Profile
from app.models.score import ListingScore, MatchScore as MS
from app.models.user import User
from app.schemas.listing import ListingOut
from app.services.matching.matcher import calculate_match
from app.workers.celery_app import get_redis

router = APIRouter(prefix="/api/v1/recommend", tags=["recommend"])


@router.get("")
async def recommend(
    profile_id: UUID = Query(..., description="基于哪个画像推荐"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """基于画像推荐房源

    策略：
    1. 先查 match_scores 表是否有预计算结果
    2. 没有的话，从 listing_scores 拉一批候选房源（general_score >= 60），实时算匹配度
    3. 按个性化推荐分排序返回
    """
    profile = (
        await db.execute(select(Profile).where(Profile.id == profile_id, Profile.user_id == user.id))
    ).scalar_one_or_none()
    if not profile:
        raise BadRequestError("画像不存在或不属于当前用户")

    redis = await get_redis()

    # 拉候选：评分 >= 60 的房源，最多 200 条
    candidate_stmt = (
        select(Listing, ListingScore)
        .join(ListingScore, ListingScore.listing_id == Listing.id)
        .where(Listing.status == "active", ListingScore.general_score >= 60)
        .order_by(desc(ListingScore.general_score))
        .limit(200)
    )
    candidates = (await db.execute(candidate_stmt)).all()

    # 计算匹配度（已缓存的从 DB 拿，未缓存的实时算）
    scored = []
    for listing, score in candidates:
        # 查 match_scores
        match_stmt = select(MS).where(MS.listing_id == listing.id, MS.profile_id == profile.id)
        cached = (await db.execute(match_stmt)).scalar_one_or_none()

        if cached:
            scored.append((listing, score, cached))
        else:
            result = await calculate_match(db, redis, listing, profile, score.general_score)
            # 入库缓存
            new_match = MS(
                listing_id=listing.id,
                profile_id=profile.id,
                match_score=result.match_score,
                personalized_score=result.personalized_score,
                price_match=result.price_match,
                commute_match=result.commute_match,
                area_match=result.area_match,
                layout_match=result.layout_match,
                environment_match=result.environment_match,
                keyword_match=result.keyword_match,
                evidence=result.evidence,
            )
            db.add(new_match)
            await db.flush()
            # 用一个临存对象保持接口一致
            scored.append((listing, score, new_match))

    await db.commit()

    # 排序
    scored.sort(key=lambda x: x[2].personalized_score, reverse=True)

    # 分页
    total = len(scored)
    page_items = scored[(page - 1) * page_size : page * page_size]

    items = []
    for listing, score, match in page_items:
        item = ListingOut.model_validate(listing).model_dump(mode="json")
        item["general_score"] = score.general_score
        item["risk_tags"] = score.risk_tags or []
        item["match_score"] = match.match_score
        item["personalized_score"] = match.personalized_score
        item["match_evidence"] = match.evidence
        items.append(item)

    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    })

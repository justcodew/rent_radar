"""收藏/忽略/标记路由"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.response import ok
from app.core.security import get_current_user
from app.database import get_db
from app.models.favorite import Favorite, Ignore, UserMark
from app.models.listing import Listing
from app.models.score import ListingScore
from app.models.user import User
from app.schemas.listing import ListingOut

router = APIRouter(prefix="/api/v1", tags=["favorites"])


class FavCreate(BaseModel):
    listing_id: str
    category: str = "待看"
    note: str | None = None


class IgnoreCreate(BaseModel):
    listing_id: str
    reason: str | None = None


class MarkCreate(BaseModel):
    listing_id: str
    mark_type: str   # agent / fake / noisy / quiet / lighting_good / lighting_bad / report
    note: str | None = None


@router.post("/favorites")
async def add_favorite(
    payload: FavCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fav = Favorite(
        user_id=user.id,
        listing_id=payload.listing_id,
        category=payload.category,
        note=payload.note,
    )
    db.add(fav)
    await db.flush()
    return ok({"id": str(fav.id)})


@router.get("/favorites")
async def list_favorites(
    category: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(Favorite, Listing, ListingScore)
        .join(Listing, Listing.id == Favorite.listing_id)
        .outerjoin(ListingScore, ListingScore.listing_id == Listing.id)
        .where(Favorite.user_id == user.id)
        .order_by(desc(Favorite.created_at))
    )
    if category:
        stmt = stmt.where(Favorite.category == category)
    rows = (await db.execute(stmt)).all()
    items = []
    for fav, listing, score in rows:
        item = ListingOut.model_validate(listing).model_dump(mode="json")
        item["general_score"] = score.general_score if score else None
        item["favorite_category"] = fav.category
        item["favorite_note"] = fav.note
        item["favorited_at"] = fav.created_at.isoformat() if fav.created_at else None
        items.append(item)
    return ok({"items": items, "total": len(items)})


@router.delete("/favorites/{listing_id}")
async def remove_favorite(
    listing_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Favorite).where(Favorite.user_id == user.id, Favorite.listing_id == listing_id)
    )
    fav = result.scalar_one_or_none()
    if fav:
        await db.delete(fav)
    return ok({"deleted": str(listing_id)})


@router.post("/ignores")
async def add_ignore(
    payload: IgnoreCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    ign = Ignore(user_id=user.id, listing_id=payload.listing_id, reason=payload.reason)
    db.add(ign)
    await db.flush()
    return ok({"id": str(ign.id)})


@router.post("/marks")
async def add_mark(
    payload: MarkCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """用户标记（中介/虚假/噪音/采光等）

    反馈闭环：同房源被 >=3 个不同用户标记为中介 -> 自动加 risk_tag
    """
    mark = UserMark(
        user_id=user.id,
        listing_id=payload.listing_id,
        mark_type=payload.mark_type,
        note=payload.note,
    )
    db.add(mark)
    await db.flush()

    # 检查是否达到自动标记阈值
    if payload.mark_type in ("agent", "fake"):
        count_stmt = select(UserMark).where(
            UserMark.listing_id == payload.listing_id,
            UserMark.mark_type == payload.mark_type,
        )
        all_marks = (await db.execute(count_stmt)).scalars().all()
        unique_users = {m.user_id for m in all_marks}
        if len(unique_users) >= 3:
            # 更新 listing_scores 的 risk_tags
            score_stmt = select(ListingScore).where(ListingScore.listing_id == payload.listing_id)
            score = (await db.execute(score_stmt)).scalar_one_or_none()
            if score:
                tags = list(score.risk_tags or [])
                auto_tag = "疑似中介" if payload.mark_type == "agent" else "用户标记虚假"
                if auto_tag not in tags:
                    tags.append(auto_tag)
                    score.risk_tags = tags

    return ok({"id": str(mark.id)})

"""房源路由"""
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.response import ok
from app.core.security import get_current_user
from app.database import get_db
from app.models.listing import Listing
from app.models.score import ListingScore, MatchScore
from app.models.user import User
from app.schemas.listing import ListingOut

router = APIRouter(prefix="/api/v1/listings", tags=["listings"])


@router.get("")
async def list_listings(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    area: str | None = None,
    min_price: int | None = None,
    max_price: int | None = None,
    min_score: int | None = None,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Listing, ListingScore.general_score, ListingScore.risk_tags).outerjoin(
        ListingScore, ListingScore.listing_id == Listing.id
    ).where(Listing.status == "active")

    if area:
        stmt = stmt.where(Listing.area_name == area)
    if min_price is not None:
        stmt = stmt.where(Listing.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Listing.price <= max_price)
    if min_score is not None:
        stmt = stmt.where(ListingScore.general_score >= min_score)

    # 总数
    count_stmt = select(func.count()).select_from(Listing).where(Listing.status == "active")
    if area:
        count_stmt = count_stmt.where(Listing.area_name == area)
    if min_price is not None:
        count_stmt = count_stmt.where(Listing.price >= min_price)
    if max_price is not None:
        count_stmt = count_stmt.where(Listing.price <= max_price)
    total = (await db.execute(count_stmt)).scalar() or 0

    # 排序：有评分的按评分降序，没评分的排后面
    stmt = stmt.order_by(desc(ListingScore.general_score), desc(Listing.posted_at))
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    data = []
    for listing, score, risk_tags in rows:
        item = ListingOut.model_validate(listing).model_dump(mode="json")
        item["general_score"] = score
        item["risk_tags"] = risk_tags or []
        data.append(item)

    return ok({
        "items": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    })


@router.get("/{listing_id}")
async def get_listing(
    listing_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Listing, ListingScore).outerjoin(
            ListingScore, ListingScore.listing_id == Listing.id
        ).where(Listing.id == listing_id)
    )
    row = result.first()
    if not row:
        raise NotFoundError("房源不存在")
    listing, score = row
    item = ListingOut.model_validate(listing).model_dump(mode="json")
    if score:
        item["general_score"] = score.general_score
        item["risk_tags"] = score.risk_tags or []
        item["evidence"] = score.evidence
    return ok(item)

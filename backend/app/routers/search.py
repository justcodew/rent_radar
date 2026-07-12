"""搜索路由（使用 PostgreSQL 全文检索）"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.database import get_db
from app.models.listing import Listing
from app.models.score import ListingScore
from app.schemas.listing import ListingOut

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
async def search(
    q: str = Query("", description="关键词"),
    area: list[str] | None = Query(None),
    price_min: int | None = None,
    price_max: int | None = None,
    layout: list[str] | None = Query(None),
    min_score: int | None = None,
    posted_within_days: int | None = None,
    sort: str = Query("default"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """混合搜索：全文检索 + 结构化筛选"""
    stmt = select(Listing, ListingScore.general_score, ListingScore.risk_tags).outerjoin(
        ListingScore, ListingScore.listing_id == Listing.id
    ).where(Listing.status == "active")

    # 全文检索
    # 注：PG 'simple' tsvector 对中文分词效果差（"望京" 不会成为独立 token）
    # 改用 ILIKE 模糊匹配（中文场景），同时保留 tsquery 给英文/数字（兼顾未来 zhparser）
    if q.strip():
        like_pattern = f"%{q.strip()}%"
        stmt = stmt.where(
            Listing.title.ilike(like_pattern) | Listing.content.ilike(like_pattern)
        )

    # 区域筛选
    if area:
        stmt = stmt.where(Listing.area_name.in_(area))
    if price_min is not None:
        stmt = stmt.where(Listing.price >= price_min)
    if price_max is not None:
        stmt = stmt.where(Listing.price <= price_max)
    if layout:
        stmt = stmt.where(Listing.layout.in_(layout))
    if min_score is not None:
        stmt = stmt.where(ListingScore.general_score >= min_score)
    if posted_within_days is not None:
        from datetime import datetime, timedelta, timezone
        cutoff = datetime.now(timezone.utc) - timedelta(days=posted_within_days)
        stmt = stmt.where(Listing.posted_at >= cutoff)

    # 排序
    if sort == "price_asc":
        stmt = stmt.order_by(Listing.price.asc())
    elif sort == "price_desc":
        stmt = stmt.order_by(Listing.price.desc())
    elif sort == "newest":
        stmt = stmt.order_by(desc(Listing.posted_at))
    elif sort == "score":
        stmt = stmt.order_by(desc(ListingScore.general_score))
    else:
        # 默认综合排序：评分*0.7 + 时间衰减*0.3
        stmt = stmt.order_by(desc(ListingScore.general_score), desc(Listing.posted_at))

    # count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # 分页
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).all()

    items = []
    for listing, score, risk_tags in rows:
        item = ListingOut.model_validate(listing).model_dump(mode="json")
        item["general_score"] = score
        item["risk_tags"] = risk_tags or []
        items.append(item)

    return ok({
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
        "has_more": page * page_size < total,
    })

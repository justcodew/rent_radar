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

# 平台 → 本地图片目录映射
_PLATFORM_IMG_DIR = {"xiaohongshu": "xhs", "douban": "douban", "weibo": "weibo"}


def _rewrite_images(item: dict) -> dict:
    """把 image_urls 转为可访问的路径。

    优先策略:
    1. 如果本地已下载(data/<platform>/images/<source_id>/),返回本地 API 路径
    2. 否则返回代理路径(后端带 Referer 转发,但如果 URL 过期仍会失败)
    """
    import os
    from pathlib import Path

    urls = item.get("image_urls") or []
    source = item.get("source", "")
    source_id = item.get("source_id", "")
    platform_dir = _PLATFORM_IMG_DIR.get(source, source)
    local_dir = Path("data") / platform_dir / "images" / source_id

    result = []
    for url in urls:
        if not url or not url.startswith(("http://", "https://")):
            continue
        # 尝试从 URL 提取文件名
        filename = url.split("/")[-1].split("?")[0]
        local_path = local_dir / filename
        if local_path.exists():
            # 本地已下载
            result.append(f"/api/v1/images/{platform_dir}/{source_id}/{filename}")
        else:
            # 远程代理
            result.append(f"/api/v1/images/proxy?url={url}")
    item["image_urls"] = result
    return item

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
        item = _rewrite_images(item)
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
    listing_id: str,
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
    item = _rewrite_images(item)
    return ok(item)

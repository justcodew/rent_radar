"""采集控制路由

触发采集任务(小红书/豆瓣/微博),采集结果可查/可转 Listing 入库。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.database import get_db

router = APIRouter(prefix="/api/v1/crawl", tags=["crawl"])

SUPPORTED_PLATFORMS = {"xhs", "douban", "wb"}


@router.get("/platforms")
async def list_platforms():
    """列出支持的采集平台"""
    return ok({"platforms": sorted(SUPPORTED_PLATFORMS)})


@router.post("/trigger")
async def trigger_crawl(
    platform: str = Query("xhs"),
    keywords: str = Query(""),
    max_count: int = Query(20, ge=1, le=100),
    login_type: str = Query("qrcode"),
    cookies: str = Query(""),
):
    """触发采集任务。

    通过 subprocess 调用平台采集脚本(需 Chrome CDP 环境)。
    采集是异步的,本接口返回后采集在后台进行。
    """
    from app.services.crawler.runner import run_crawl

    result = await run_crawl(
        platform=platform,
        keywords=keywords,
        max_count=max_count,
        login_type=login_type,
        cookies=cookies,
    )
    return ok(result)


@router.get("/listings")
async def get_crawled_listings(
    platform: str = Query("xhs"),
    limit: int = Query(50, ge=1, le=500),
    only_with_price: bool = Query(False),
):
    """获取已采集数据,返回 house_pro Listing 格式。

    读取 data/<platform>/jsonl/ 下已采集数据,用 extractor 提取结构化字段。
    """
    from app.services.crawler.runner import get_crawled_listings as _get

    listings = await _get(platform, limit=limit * 2)
    if only_with_price:
        listings = [l for l in listings if l.get("price")]
    listings = listings[:limit]

    return ok({
        "platform": platform,
        "total": len(listings),
        "listings": listings,
    })


@router.post("/ingest")
async def ingest_to_db(
    platform: str = Query("xhs"),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """把已采集数据入库 Listing 表(并触发评分)。

    读取已采集数据 → 转换 → 去重 → 入库 → 返回统计。
    """
    from sqlalchemy import select
    from app.models.listing import Listing
    from app.services.crawler.runner import get_crawled_listings as _get

    listings = await _get(platform, limit=limit)
    if not listings:
        return ok({"platform": platform, "ingested": 0, "message": "无已采集数据"})

    stats = {"fetched": len(listings), "ingested": 0, "skipped": 0}
    for item in listings:
        source = item.get("source", platform)
        source_id = item.get("source_id", "")
        if not source_id:
            stats["skipped"] += 1
            continue

        # 去重
        exists = await db.execute(
            select(Listing.id).where(
                Listing.source == source,
                Listing.source_id == source_id,
            )
        )
        if exists.scalar_one_or_none():
            stats["skipped"] += 1
            continue

        listing = Listing(
            source=source,
            source_id=source_id,
            source_url=item.get("source_url"),
            poster_id=item.get("poster_id"),
            poster_name=item.get("poster_name"),
            title=item.get("title"),
            content=item.get("content", ""),
            price=item.get("price"),
            layout=item.get("layout"),
            area_name=item.get("area_name"),
            size_sqm=item.get("size_sqm"),
            floor_info=item.get("floor_info"),
            orientation=item.get("orientation"),
            contact_info=item.get("contact_info", {}),
            raw_data=item.get("raw_data", {}),
        )
        db.add(listing)
        stats["ingested"] += 1

    await db.commit()
    return ok({"platform": platform, **stats})

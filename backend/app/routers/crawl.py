"""采集控制路由

触发采集任务(小红书/豆瓣/微博),采集结果可查/可转 Listing 入库。

采集流程改为真正异步:
- POST /trigger → 立即返回 task_id,后台 asyncio.create_task 执行采集
- GET /status/{task_id} → 查采集进度
- GET /listings → 查已采集数据
- POST /ingest → 入库 + 评分
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.database import get_db

router = APIRouter(prefix="/api/v1/crawl", tags=["crawl"])

SUPPORTED_PLATFORMS = {"xhs", "douban", "wb"}

#: 内存中的采集任务状态(进程重启后丢失,开发阶段足够)
_tasks: dict[str, dict] = {}


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
    """触发采集任务(异步,立即返回 task_id)。

    采集在后台进行,通过 GET /status/{task_id} 查进度。
    """
    task_id = uuid.uuid4().hex[:12]
    _tasks[task_id] = {
        "task_id": task_id,
        "platform": platform,
        "keywords": keywords,
        "status": "running",
        "result": None,
        "error": None,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "finished_at": None,
    }

    # 后台执行采集(不阻塞 HTTP 响应)
    asyncio.create_task(_run_crawl_task(task_id, platform, keywords, max_count, login_type, cookies))

    return ok({
        "task_id": task_id,
        "status": "running",
        "message": "采集已启动,请通过 /status 查进度。小红书需在 Chrome 窗口扫码登录。",
    })


async def _run_crawl_task(
    task_id: str, platform: str, keywords: str, max_count: int, login_type: str, cookies: str
):
    """后台采集任务"""
    from app.services.crawler.runner import run_crawl

    try:
        result = await run_crawl(
            platform=platform,
            keywords=keywords,
            max_count=max_count,
            login_type=login_type,
            cookies=cookies,
        )
        _tasks[task_id]["status"] = result.get("status", "success")
        _tasks[task_id]["result"] = result
    except Exception as e:
        _tasks[task_id]["status"] = "failed"
        _tasks[task_id]["error"] = str(e)
    finally:
        _tasks[task_id]["finished_at"] = datetime.now(timezone.utc).isoformat()


@router.get("/status/{task_id}")
async def crawl_status(task_id: str):
    """查采集任务状态"""
    task = _tasks.get(task_id)
    if not task:
        return ok({"task_id": task_id, "status": "not_found"})
    return ok(task)


@router.get("/listings")
async def get_crawled_listings(
    platform: str = Query("xhs"),
    limit: int = Query(50, ge=1, le=500),
    only_with_price: bool = Query(False),
):
    """获取已采集数据,返回 house_pro Listing 格式。"""
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
    """把已采集数据入库 Listing 表(并触发评分)。"""
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

        exists = await db.execute(
            select(Listing.id).where(Listing.source == source, Listing.source_id == source_id)
        )
        if exists.scalar_one_or_none():
            stats["skipped"] += 1
            continue

        db.add(Listing(
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
            contact_info=item.get("contact_info", {}),
            raw_data=item.get("raw_data", {}),
        ))
        stats["ingested"] += 1

    await db.commit()

    # 触发评分
    if stats["ingested"] > 0:
        try:
            await _trigger_scoring_for_new(db)
        except Exception:
            pass

    return ok({"platform": platform, **stats})


async def _trigger_scoring_for_new(db) -> int:
    """对新入库的房源触发评分"""
    from app.models.listing import Listing
    from app.models.score import ListingScore
    from app.services.scoring.rule_engine import calculate_listing_score
    from app.config import settings

    stmt = (
        select(Listing)
        .outerjoin(ListingScore, ListingScore.listing_id == Listing.id)
        .where(ListingScore.id.is_(None), Listing.status == "active")
        .limit(500)
    )
    listings = (await db.execute(stmt)).scalars().all()

    count = 0
    for listing in listings:
        result = await calculate_listing_score(db, listing)
        db.add(ListingScore(
            listing_id=listing.id,
            general_score=result.general_score,
            poster_score=result.poster_score,
            listing_score=result.listing_score,
            poster_frequency_score=result.poster_frequency_score,
            poster_age_score=result.poster_age_score,
            poster_diversity_score=result.poster_diversity_score,
            poster_contact_reuse_score=result.poster_contact_reuse_score,
            image_authenticity_score=result.image_authenticity_score,
            description_score=result.description_score,
            price_reasonable_score=result.price_reasonable_score,
            info_completeness_score=result.info_completeness_score,
            risk_tags=result.risk_tags,
            evidence=result.evidence,
            score_version=settings.SCORE_RULE_VERSION,
        ))
        count += 1
        if count % 10 == 0:
            await db.commit()
    await db.commit()
    return count

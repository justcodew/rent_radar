"""Celery 应用与任务定义"""
from __future__ import annotations

import asyncio
from typing import Any

import redis.asyncio as aioredis
from celery import Celery

from app.config import settings

celery_app = Celery(
    "haofang",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        # 每 6 小时抓一次豆瓣
        "crawl-douban-every-6h": {
            "task": "app.workers.celery_app.crawl_douban",
            "schedule": settings.CRAWLER_INTERVAL_SECONDS,
        },
        # 每 30 分钟扫描 MediaCrawler 落地的小红书 JSON
        "crawl-xiaohongshu-every-30m": {
            "task": "app.workers.celery_app.crawl_xiaohongshu",
            "schedule": 1800,
        },
        # 每天 03:00 重新计算高分房源的评分
        "recalc-top-scores-daily": {
            "task": "app.workers.celery_app.recalc_top_scores",
            "schedule": 86400,
        },
        # 每周一 04:00 更新区域均价
        "update-area-price-stats": {
            "task": "app.workers.celery_app.update_area_price_stats",
            "schedule": 7 * 86400,
        },
    },
)

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    """获取全局 Redis 客户端（async）"""
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis_pool


def _run_async(coro):
    """在 Celery 同步任务中跑 async 函数"""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.celery_app.crawl_douban")
def crawl_douban():
    """采集豆瓣租房信息 → 入库 → 触发评分。

    使用 rent_radar 的统一采集入口(runner.py)。
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _run():
        from app.services.crawler.runner import run_crawl, get_crawled_listings
        # 1. 采集(需 Chrome CDP 环境,无环境时返回 pending)
        crawl_result = await run_crawl(
            platform="douban",
            keywords=getattr(settings, "CRAWL_KEYWORDS", "广州租房"),
            max_count=20,
        )
        # 2. 入库
        async with SessionLocal() as db:
            from sqlalchemy import select
            from app.models.listing import Listing
            listings_data = await get_crawled_listings("douban", limit=50)
            stats = {"fetched": len(listings_data), "ingested": 0, "skipped": 0}
            for item in listings_data:
                exists = await db.execute(
                    select(Listing.id).where(
                        Listing.source == item.get("source", "douban"),
                        Listing.source_id == item.get("source_id", ""),
                    )
                )
                if exists.scalar_one_or_none():
                    stats["skipped"] += 1
                    continue
                db.add(Listing(
                    source=item.get("source", "douban"),
                    source_id=item["source_id"],
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
            if stats["ingested"] > 0:
                await _trigger_scoring_for_new(db)
            return {**crawl_result, **stats}

    return _run_async(_run())


@celery_app.task(name="app.workers.celery_app.crawl_xiaohongshu")
def crawl_xiaohongshu():
    """采集小红书租房信息 → 入库 → 触发评分。

    使用 rent_radar 的统一采集入口(runner.py)。
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _run():
        from app.services.crawler.runner import run_crawl, get_crawled_listings
        crawl_result = await run_crawl(
            platform="xhs",
            keywords=getattr(settings, "CRAWL_KEYWORDS", "广州租房"),
            max_count=20,
        )
        async with SessionLocal() as db:
            from sqlalchemy import select
            from app.models.listing import Listing
            listings_data = await get_crawled_listings("xhs", limit=50)
            stats = {"fetched": len(listings_data), "ingested": 0, "skipped": 0}
            for item in listings_data:
                exists = await db.execute(
                    select(Listing.id).where(
                        Listing.source == item.get("source", "xiaohongshu"),
                        Listing.source_id == item.get("source_id", ""),
                    )
                )
                if exists.scalar_one_or_none():
                    stats["skipped"] += 1
                    continue
                db.add(Listing(
                    source=item.get("source", "xiaohongshu"),
                    source_id=item["source_id"],
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
            if stats["ingested"] > 0:
                await _trigger_scoring_for_new(db)
            return {**crawl_result, **stats}

    return _run_async(_run())


async def _trigger_scoring_for_new(db) -> int:
    """对新入库（没有 listing_scores 记录）的房源触发评分"""
    from sqlalchemy import select
    from app.models.listing import Listing
    from app.models.score import ListingScore
    from app.services.scoring.rule_engine import calculate_listing_score

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
        score = ListingScore(
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
        )
        db.add(score)
        count += 1
        if count % 50 == 0:
            await db.commit()
    await db.commit()
    return count


@celery_app.task(name="app.workers.celery_app.calc_score_for_listing")
def calc_score_for_listing(listing_id: str):
    """对单个房源触发评分计算"""
    from uuid import UUID
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.models.listing import Listing
    from app.models.score import ListingScore
    from app.services.scoring.rule_engine import calculate_listing_score

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _run():
        async with SessionLocal() as db:
            listing = (
                await db.execute(select(Listing).where(Listing.id == UUID(listing_id)))
            ).scalar_one_or_none()
            if not listing:
                return None
            result = await calculate_listing_score(db, listing)
            # upsert
            existing = (
                await db.execute(
                    select(ListingScore).where(ListingScore.listing_id == listing.id)
                )
            ).scalar_one_or_none()
            if existing:
                for k, v in {
                    "general_score": result.general_score,
                    "poster_score": result.poster_score,
                    "listing_score": result.listing_score,
                    "risk_tags": result.risk_tags,
                    "evidence": result.evidence,
                    "score_version": settings.SCORE_RULE_VERSION,
                }.items():
                    setattr(existing, k, v)
            else:
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
            await db.commit()
            return result.general_score

    return _run_async(_run())


@celery_app.task(name="app.workers.celery_app.recalc_top_scores")
def recalc_top_scores():
    """重新计算高分房源的评分（每天一次，确保模型迭代后分数更新）"""
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select
    from app.models.listing import Listing
    from app.models.score import ListingScore
    from app.services.scoring.rule_engine import calculate_listing_score

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _run():
        async with SessionLocal() as db:
            stmt = (
                select(Listing)
                .join(ListingScore, ListingScore.listing_id == Listing.id)
                .where(ListingScore.general_score >= 75)
                .order_by(ListingScore.general_score.desc())
                .limit(500)
            )
            listings = (await db.execute(stmt)).scalars().all()
            count = 0
            for listing in listings:
                result = await calculate_listing_score(db, listing)
                score = (
                    await db.execute(
                        select(ListingScore).where(ListingScore.listing_id == listing.id)
                    )
                ).scalar_one()
                score.general_score = result.general_score
                score.risk_tags = result.risk_tags
                score.evidence = result.evidence
                count += 1
            await db.commit()
            return count

    return _run_async(_run())


@celery_app.task(name="app.workers.celery_app.update_area_price_stats")
def update_area_price_stats():
    """更新区域均价统计（每周一次）

    从 listings 表按 area_name + layout 聚合
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from sqlalchemy import select, func, delete
    from app.models.listing import Listing
    from app.models.stat import AreaPriceStat

    engine = create_async_engine(settings.DATABASE_URL)
    SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

    async def _run():
        async with SessionLocal() as db:
            stmt = (
                select(
                    Listing.area_name,
                    Listing.layout,
                    func.avg(Listing.price).label("avg_price"),
                    func.count(Listing.id).label("sample_count"),
                )
                .where(
                    Listing.status == "active",
                    Listing.price.isnot(None),
                    Listing.price > 0,
                    Listing.area_name.isnot(None),
                    Listing.layout.isnot(None),
                )
                .group_by(Listing.area_name, Listing.layout)
            )
            rows = (await db.execute(stmt)).all()

            # 简化：清空后重写
            await db.execute(delete(AreaPriceStat))
            for r in rows:
                if r.sample_count >= 3:
                    db.add(AreaPriceStat(
                        city="广州",
                        area_name=r.area_name,
                        layout=r.layout,
                        avg_price=int(r.avg_price),
                        sample_count=r.sample_count,
                    ))
            await db.commit()
            return len(rows)

    return _run_async(_run())

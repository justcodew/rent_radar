"""MediaCrawler HTTP 客户端

直接调用 MediaCrawler 的 /api/house/* 接口,实时获取结构化 Listing 数据。
作为文件落盘模式的实时替代方案。

用法:
    client = MediaCrawlerClient(base_url="http://localhost:8080")
    listings = await client.get_listings(platform="xhs", limit=20, only_with_price=True)
    # listings 是 house_pro Listing 格式的 list,可直接入库

    # 或触发 MediaCrawler 把数据导出到指定目录
    await client.export(platform="xhs", output_dir=settings.XHS_RAW_DIR)
"""
from __future__ import annotations

import httpx

from app.core.logging import get_logger

logger = get_logger(__name__)

DEFAULT_BASE_URL = "http://localhost:8080"
DEFAULT_TIMEOUT = 30.0


class MediaCrawlerClient:
    """MediaCrawler API 客户端"""

    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = DEFAULT_TIMEOUT) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    async def get_platforms(self) -> list[dict]:
        """获取有数据的平台列表"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/api/house/platforms")
            resp.raise_for_status()
            return resp.json().get("platforms", [])

    async def get_listings(
        self,
        platform: str = "xhs",
        limit: int = 100,
        only_with_price: bool = False,
    ) -> list[dict]:
        """实时获取已采集数据,返回 house_pro Listing 格式。

        Args:
            platform: MediaCrawler 平台标识(xhs/douban/...)
            limit: 最多返回条数
            only_with_price: 只返回提取到价格的房源

        Returns:
            Listing 格式的 dict 列表(含 source/source_id/price/layout/area_name 等)
        """
        params = {"platform": platform, "limit": limit, "only_with_price": only_with_price}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.get(f"{self.base_url}/api/house/listings", params=params)
            if resp.status_code == 404:
                logger.info("mediacrawler no data", platform=platform)
                return []
            resp.raise_for_status()
            return resp.json().get("listings", [])

    async def export(self, platform: str, output_dir: str, limit: int = 100) -> dict:
        """触发 MediaCrawler 把数据导出到指定目录(文件落盘模式)。

        house_pro 的 Celery 定时扫该目录做 ETL 入库。
        """
        payload = {"platform": platform, "output_dir": output_dir, "limit": limit}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/house/export", json=payload)
            resp.raise_for_status()
            return resp.json()


async def fetch_and_ingest(
    db,
    platform: str = "xhs",
    base_url: str = DEFAULT_BASE_URL,
    limit: int = 100,
) -> dict:
    """从 MediaCrawler 实时拉取数据并入库(house_pro Listing 表)。

    替代文件落盘模式,实时性更好。
    """
    from sqlalchemy import select
    from app.models.listing import Listing

    client = MediaCrawlerClient(base_url)
    stats = {"fetched": 0, "ingested": 0, "skipped": 0, "errors": 0}

    try:
        listings = await client.get_listings(platform=platform, limit=limit)
    except Exception as e:
        logger.warning("mediacrawler fetch failed", platform=platform, error=str(e))
        stats["errors"] = len(listings) if 'listings' in dir() else 0
        return stats

    stats["fetched"] = len(listings)

    for item in listings:
        try:
            source = item.get("source", platform)
            source_id = item.get("source_id", "")
            if not source_id:
                stats["skipped"] += 1
                continue

            # 预查去重
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
                image_urls=item.get("image_urls", []),
                price=item.get("price"),
                price_unit=item.get("price_unit", "元/月"),
                size_sqm=item.get("size_sqm"),
                layout=item.get("layout"),
                area_name=item.get("area_name"),
                floor_info=item.get("floor_info"),
                orientation=item.get("orientation"),
                contact_info=item.get("contact_info", {}),
                raw_data=item.get("raw_data", {}),
            )
            db.add(listing)
            await db.flush()
            stats["ingested"] += 1
        except Exception as e:
            logger.warning("ingest listing failed", error=str(e))
            stats["errors"] += 1

    await db.commit()
    logger.info("mediacrawler fetch_and_ingest done", **stats)
    return stats

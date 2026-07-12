"""通勤时间计算（高德 API + Redis 缓存）"""
from __future__ import annotations

import json
from typing import Optional

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

CACHE_TTL = 7 * 86400  # 通勤时间缓存 7 天（同地点不变）


async def get_commute_minutes(
    redis,
    from_location: str,
    to_location: str,
    mode: str = "transit",
) -> Optional[int]:
    """获取两地之间通勤时间（分钟）

    Args:
        redis: Redis 客户端
        from_location: 起点地址或坐标 "lng,lat"
        to_location: 终点地址或坐标
        mode: transit（公交）/ driving / walking / riding
    """
    cache_key = f"commute:{from_location}->{to_location}:{mode}"
    cached = await redis.get(cache_key)
    if cached:
        try:
            return int(cached)
        except (TypeError, ValueError):
            pass

    if not settings.AMAP_API_KEY:
        logger.warning("amap api key not configured")
        return None

    # 1. 地理编码：地址 -> 坐标
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            # 起点坐标
            origin = await _geocode(client, from_location)
            dest = await _geocode(client, to_location)
            if not origin or not dest:
                return None

            # 2. 路径规划
            url = f"{settings.AMAP_BASE_URL}/direction/{mode}"
            params = {
                "key": settings.AMAP_API_KEY,
                "origin": origin,
                "destination": dest,
                "city": "广州",
            }
            resp = await client.get(url, params=params)
            data = resp.json()

            if data.get("status") != "1":
                logger.warning("amap route failed", err=data.get("info"))
                return None

            # transit 返回结构
            transit = data.get("route", {}).get("transits", [])
            if not transit:
                return None
            duration = int(transit[0].get("duration", 0)) // 60
            await redis.set(cache_key, duration, ex=CACHE_TTL)
            return duration
        except Exception as e:
            logger.error("amap api error", error=str(e))
            return None


async def _geocode(client: httpx.AsyncClient, address: str) -> Optional[str]:
    """地址 -> 经纬度字符串"""
    # 如果已经是坐标格式（lng,lat），直接返回
    if "," in address and all(p.replace(".", "").isdigit() for p in address.split(",")):
        return address

    url = f"{settings.AMAP_BASE_URL}/geocode/geo"
    params = {"key": settings.AMAP_API_KEY, "address": address, "city": "广州"}
    resp = await client.get(url, params=params)
    data = resp.json()
    if data.get("status") != "1":
        return None
    locations = data.get("geocodes", [])
    if not locations:
        return None
    return locations[0].get("location")

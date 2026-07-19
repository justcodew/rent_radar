"""OpenStreetMap Overpass API 客户端。

用于查地铁站附近的住宅小区,完全免费,无需 API key。
数据来源:OpenStreetMap(ODbL 协议),中国大城市覆盖较好。

参考:
- API 文档:https://wiki.openstreetmap.org/wiki/Overpass_API
- 标签:landuse=residential(住宅用地)、place=neighbourhood(邻里)
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from app.core.geo import bearing_deg, haversine_km
from app.core.logging import get_logger

logger = get_logger(__name__)

# Overpass 公共镜像,主服务器常 504,失败时按顺序尝试其它
_OVERPASS_URLS = [
    "https://overpass.kumi.systems/api/interpreter",  # 较稳定的镜像
    "https://overpass-api.de/api/interpreter",         # 官方主站
    "https://overpass.openstreetmap.fr/api/interpreter",
]
_USER_AGENT = "rent-radar/1.0 (educational project)"
_TIMEOUT = 60.0

# 5 分钟内存缓存:(lat, lng, radius_m) -> (timestamp, result)
_cache: dict[tuple[float, float, int], tuple[float, list[dict]]] = {}
_CACHE_TTL = 300  # 5 min

# Overpass QL:查指定中心点 R 米内的住宅小区
# 标签组合说明(从窄到宽):
# - landuse=residential:成片住宅用地,通常是小区
# - place=neighbourhood|quarter|suburb:邻里/街区/分区,有 name 的居住片区
# - building=residential|apartments|dormitory|terrace:带 name 的住宅楼/大楼
#   (中国老城区大量单体住宅楼只有 building 标签,但带 name,是关键补充)
# 都要求有 name,过滤掉匿名建筑
_QUERY_TEMPLATE = """
[out:json][timeout:35];
(
  way["landuse"="residential"]["name"](around:{radius},{lat},{lng});
  way["building"~"residential|apartments|dormitory|terrace"]["name"](around:{radius},{lat},{lng});
  node["building"~"residential|apartments|dormitory"]["name"](around:{radius},{lat},{lng});
  node["place"~"neighbourhood|quarter|suburb"](around:{radius},{lat},{lng});
);
out center 400;
"""


async def find_nearby_communities(
    lat: float, lng: float, radius_m: int = 2000
) -> list[dict]:
    """查中心点 radius_m 米内的住宅小区列表。

    返回:`[{name, lat, lng, osm_type, osm_id}]`
    结果按距中心点距离升序。
    """
    cache_key = (round(lat, 4), round(lng, 4), radius_m)
    now = time.time()
    cached = _cache.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    query = _QUERY_TEMPLATE.format(lat=lat, lng=lng, radius=radius_m)

    try:
        resp = None
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            for url in _OVERPASS_URLS:
                try:
                    resp = await client.post(
                        url,
                        data={"data": query},
                        headers={"User-Agent": _USER_AGENT},
                    )
                    if resp.status_code == 200:
                        break
                    logger.warning("overpass endpoint returned non-200", url=url, status=resp.status_code)
                except httpx.HTTPError as e:
                    logger.warning("overpass endpoint failed", url=url, error=str(e))
                    continue
            else:
                return []

        if resp is None or resp.status_code != 200:
            return []

        data: dict[str, Any] = resp.json()
        elements = data.get("elements", [])

        # 去重 + 抽字段
        seen_names: set[str] = set()
        communities: list[dict] = []
        for el in elements:
            tags = el.get("tags") or {}
            name = tags.get("name", "").strip()
            if not name or name in seen_names:
                continue
            seen_names.add(name)
            center = el.get("center") or el
            lat_c = center.get("lat")
            lng_c = center.get("lon")
            if lat_c is None or lng_c is None:
                continue
            communities.append({
                "name": name,
                "lat": float(lat_c),
                "lng": float(lng_c),
                "osm_type": el.get("type", ""),
                "osm_id": el.get("id"),
            })

        # 算距离/方位,按距离升序
        for c in communities:
            c["distance_km"] = round(haversine_km(lat, lng, c["lat"], c["lng"]), 2)
            c["bearing_deg"] = round(bearing_deg(lat, lng, c["lat"], c["lng"]), 1)
        communities.sort(key=lambda x: x["distance_km"])

        _cache[cache_key] = (now, communities)
        logger.info("overpass fetched communities", center=(lat, lng), radius_m=radius_m, count=len(communities))
        return communities

    except Exception as e:
        logger.error("overpass query failed", error=str(e))
        return []

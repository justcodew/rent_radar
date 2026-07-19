"""地铁站附近小区探索路由。

输入地铁站 + 半径 → 返回半径内的真实小区(来自 OSM Overpass)
+ 每个小区的房源匹配数 + 抽样房源。
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import NotFoundError
from app.core.geo import bearing_deg, haversine_km
from app.core.response import ok
from app.database import get_db
from app.models.listing import Listing
from app.models.score import ListingScore
from app.schemas.listing import ListingOut
from app.services.geo.poi import find_nearby_communities

router = APIRouter(prefix="/api/v1/subway", tags=["subway"])

_DATA_DIR = Path(__file__).resolve().parent.parent / "data"


@lru_cache(maxsize=1)
def _load_stations() -> list[dict]:
    with open(_DATA_DIR / "guangzhou_subway.json", encoding="utf-8") as f:
        return json.load(f)


@lru_cache(maxsize=1)
def _load_districts() -> list[dict]:
    with open(_DATA_DIR / "guangzhou_districts.json", encoding="utf-8") as f:
        return json.load(f)


def _find_station(name: str) -> dict | None:
    for s in _load_stations():
        if s["name"] == name:
            return s
    return None


@router.get("/stations")
async def list_stations(q: str = Query("", description="站名模糊匹配"), limit: int = Query(10, ge=1, le=50)):
    """地铁站自动补全。"""
    q = q.strip()
    stations = _load_stations()
    if q:
        matched = [s for s in stations if q in s["name"]]
    else:
        matched = stations
    return ok({"stations": matched[:limit], "total": len(matched)})


@router.get("/explore")
async def explore(
    station: str = Query(..., description="地铁站名(精确)"),
    radius_km: float = Query(2.0, ge=0.3, le=5.0),
    db: AsyncSession = Depends(get_db),
):
    """查指定地铁站半径内的真实小区(OSM 数据)+ 每个小区的房源匹配。

    小区数据来自 OpenStreetMap Overpass API,有真实经纬度。
    房源匹配:listing.title + content 包含小区名时算命中。
    没有房源的小区也返回(listings_count=0)。
    """
    st = _find_station(station)
    if not st:
        raise NotFoundError(f"未找到地铁站: {station}")

    radius_m = int(radius_km * 1000)

    # 拉地铁站附近的小区(Overpass,5min 缓存)
    all_communities = await find_nearby_communities(st["lat"], st["lng"], radius_m=radius_m)

    # 加载所有 active listings,匹配小区名(数据量小,直接内存扫描)
    listing_rows = (
        await db.execute(
            select(Listing, ListingScore.general_score)
            .outerjoin(ListingScore, ListingScore.listing_id == Listing.id)
            .where(Listing.status == "active")
            .order_by(ListingScore.general_score.desc().nullslast())
        )
    ).all()

    # 预处理 listing 文本,做小区名匹配
    listing_data = []
    for listing, score in listing_rows:
        text = f"{listing.title or ''} {listing.content or ''}"
        listing_data.append({
            "listing": listing,
            "score": score,
            "text": text,
        })

    for c in all_communities:
        name = c["name"]
        matched = [ld for ld in listing_data if name in ld["text"]]
        c["listings_count"] = len(matched)
        c["sample_listings"] = []
        for ld in matched[:6]:
            item = ListingOut.model_validate(ld["listing"]).model_dump(mode="json")
            item["general_score"] = ld["score"]
            c["sample_listings"].append(item)

    return ok({
        "station": st,
        "radius_km": radius_km,
        "communities": all_communities,  # 已按距离升序
    })

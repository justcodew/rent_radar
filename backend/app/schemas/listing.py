"""房源 schema"""
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel


class ListingOut(BaseModel):
    id: UUID
    source: str
    source_url: str | None
    poster_id: str | None
    poster_name: str | None
    title: str | None
    content: str
    price: int | None
    area_name: str | None
    location_detail: str | None
    layout: str | None
    size_sqm: int | None
    floor_info: str | None
    orientation: str | None
    contact_info: dict[str, Any]
    image_urls: list[str]
    posted_at: datetime | None
    created_at: datetime

    # 评分（可选，从 join 出来）
    general_score: int | None = None
    risk_tags: list[str] = []
    match_score: int | None = None
    personalized_score: int | None = None

    class Config:
        from_attributes = True


class ScoreOut(BaseModel):
    listing_id: UUID
    general_score: int
    level: str
    stars: int
    poster_score: float
    listing_score: float
    sub_scores: dict[str, float]
    risk_tags: list[str]
    evidence: dict[str, Any]
    score_version: str
    calculated_at: datetime


class SearchParams(BaseModel):
    keyword: str | None = None
    area: list[str] | None = None
    price_min: int | None = None
    price_max: int | None = None
    layout: list[str] | None = None
    size_min: int | None = None
    size_max: int | None = None
    rent_type: str | None = None
    min_score: int | None = None
    posted_within_days: int | None = None
    sort: str = "default"  # default / score / price_asc / price_desc / newest
    page: int = 1
    page_size: int = 20

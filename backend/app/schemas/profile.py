"""画像 schema"""
from datetime import datetime
from typing import Any
from uuid import UUID
from pydantic import BaseModel, Field


class CommuteItem(BaseModel):
    location: str
    mode: str = "transit"   # transit / driving / walking / riding
    max_time: int = Field(default=45, ge=5, le=180)
    weight: float = Field(default=1.0, gt=0, le=5)


class ProfileBase(BaseModel):
    name: str = Field(max_length=100)
    city: str = "广州"
    budget_min: int = Field(default=0, ge=0)
    budget_max: int = Field(default=10000, ge=0)
    occupants: int = Field(default=1, ge=1, le=10)
    move_in: str | None = None
    areas: list[str] = []
    layouts: list[str] = []
    rent_type: str | None = None
    size_range: list[int] = [0, 100]
    commute: list[CommuteItem] = []
    environment: dict[str, Any] = {}
    keywords: dict[str, list[str]] = {}
    preferences: dict[str, Any] = {}


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    name: str | None = None


class ProfileOut(ProfileBase):
    id: UUID
    user_id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

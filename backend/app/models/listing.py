"""房源模型（含全文检索字段）"""
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import JSON, String, Integer, Text, DateTime, ForeignKey, Index, func, Computed
import uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Listing(Base):
    __tablename__ = "listings"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))

    # 来源
    source: Mapped[str] = mapped_column(String(20), index=True)            # douban / xiaohongshu
    source_id: Mapped[str] = mapped_column(String(100))                    # 平台原始 ID
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_id: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    poster_name: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 提取的结构化信息
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    content: Mapped[str] = mapped_column(Text, default="")
    price: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    price_unit: Mapped[str] = mapped_column(String(20), default="元/月")
    area_name: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    location_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    layout: Mapped[str | None] = mapped_column(String(50), nullable=True)
    size_sqm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    floor_info: Mapped[str | None] = mapped_column(String(50), nullable=True)
    orientation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contact_info: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)

    # 原始数据
    raw_data: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    image_urls: Mapped[list[str]] = mapped_column(JSON, default=list)

    # 状态
    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        # 唯一约束：同一平台同一原始 ID 不重复
        # 全文检索 GIN 索引（在 init.sql 或 alembic 中创建 tsvector 列）
        Index("idx_listings_unique_source", "source", "source_id", unique=True),
        Index("idx_listings_poster", "poster_id"),
    )


class ListingImage(Base):
    """房源图片表（用于 pHash 去重和图片分析）"""
    __tablename__ = "listing_images"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    listing_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    url: Mapped[str] = mapped_column(Text)
    phash: Mapped[str | None] = mapped_column(String(32), index=True, nullable=True)
    # 后续以房找房预留：embedding vector(512) 列，由 alembic 后续迁移添加
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

"""评分模型

关键设计：listing_scores.evidence 字段记录每个子项的打分依据（命中关键词、对比数据等），
支撑 PRD 4.7「评分解释与信息来源」功能。
"""
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import JSON, String, Integer, DateTime, ForeignKey, func
import uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ListingScore(Base):
    __tablename__ = "listing_scores"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    listing_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("listings.id", ondelete="CASCADE"), unique=True
    )

    # 总分
    general_score: Mapped[int] = mapped_column(Integer, index=True)

    # 发布者特征（30 分制）
    poster_score: Mapped[int] = mapped_column(Integer, default=0)
    poster_frequency_score: Mapped[int] = mapped_column(Integer, default=0)
    poster_age_score: Mapped[int] = mapped_column(Integer, default=0)
    poster_diversity_score: Mapped[int] = mapped_column(Integer, default=0)
    poster_contact_reuse_score: Mapped[int] = mapped_column(Integer, default=0)

    # 房源特征（70 分制）
    listing_score: Mapped[int] = mapped_column(Integer, default=0)
    image_authenticity_score: Mapped[int] = mapped_column(Integer, default=0)
    description_score: Mapped[int] = mapped_column(Integer, default=0)
    price_reasonable_score: Mapped[int] = mapped_column(Integer, default=0)
    info_completeness_score: Mapped[int] = mapped_column(Integer, default=0)

    # 风险标签 & 评分依据
    risk_tags: Mapped[list[str]] = mapped_column(JSON, default=list)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    ai_evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    ai_insights: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)

    score_version: Mapped[str] = mapped_column(String(20), default="rule-v1")
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class MatchScore(Base):
    __tablename__ = "match_scores"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    listing_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("profiles.id", ondelete="CASCADE"), index=True
    )

    match_score: Mapped[int] = mapped_column(Integer)
    personalized_score: Mapped[int] = mapped_column(Integer, index=True)

    # 各维度（满分均为对应权重）
    price_match: Mapped[int] = mapped_column(Integer, default=0)
    commute_match: Mapped[int] = mapped_column(Integer, default=0)
    area_match: Mapped[int] = mapped_column(Integer, default=0)
    layout_match: Mapped[int] = mapped_column(Integer, default=0)
    environment_match: Mapped[int] = mapped_column(Integer, default=0)
    keyword_match: Mapped[int] = mapped_column(Integer, default=0)

    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        # 一个房源对一个画像只算一次
        # 通过 partial unique index 实现（避免改 schema 太多）
    )

"""需求画像模型"""
from datetime import datetime
from uuid import UUID, uuid4
from typing import Any

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Profile(Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(50), default="广州")

    # 基础约束
    budget_min: Mapped[int] = mapped_column(Integer, default=0)
    budget_max: Mapped[int] = mapped_column(Integer, default=10000)
    occupants: Mapped[int] = mapped_column(Integer, default=1)
    move_in: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 房源需求
    areas: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)        # ["朝阳","海淀"]
    layouts: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)      # ["一室一厅"]
    rent_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 整租/合租
    size_range: Mapped[dict[str, Any]] = mapped_column(JSONB, default=[0, 100])

    # 通勤（支持多人）：[{location, mode, max_time, weight}]
    commute: Mapped[dict[str, Any]] = mapped_column(JSONB, default=list)

    # 环境偏好
    environment: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    # 关键词
    keywords: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)  # {must_have:[], exclude:[]}

    # 软偏好
    preferences: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    status: Mapped[str] = mapped_column(String(20), default="active")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

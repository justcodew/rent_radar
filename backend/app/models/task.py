"""找房任务与通知"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
import uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    profile_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("profiles.id", ondelete="CASCADE")
    )
    name: Mapped[str] = mapped_column(String(100))

    push_threshold: Mapped[int] = mapped_column(Integer, default=75)
    push_frequency: Mapped[str] = mapped_column(String(20), default="realtime")
    push_method: Mapped[str] = mapped_column(String(20), default="webpush")

    status: Mapped[str] = mapped_column(String(20), default="active", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[UUID] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    task_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True
    )
    listing_id: Mapped[UUID | None] = mapped_column(
        String(36), ForeignKey("listings.id", ondelete="CASCADE"), nullable=True
    )

    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

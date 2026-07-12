"""收藏 / 忽略 / 用户标记"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Favorite(Base):
    __tablename__ = "favorites"
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_favorite"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    category: Mapped[str] = mapped_column(String(20), default="待看")  # 待看/看过/不考虑/已租
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Ignore(Base):
    __tablename__ = "ignores"
    __table_args__ = (UniqueConstraint("user_id", "listing_id", name="uq_ignore"),)

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    reason: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class UserMark(Base):
    """用户对房源的标记（中介/虚假/噪音/采光等），反馈闭环"""
    __tablename__ = "user_marks"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    listing_id: Mapped[UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True
    )
    mark_type: Mapped[str] = mapped_column(String(50), index=True)
    # agent/fake/noisy/quiet/lighting_good/lighting_bad/report
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    extra: Mapped[dict] = mapped_column(JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

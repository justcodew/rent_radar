"""用户模型

注意：与 PRD「不留存用户隐私」一致，phone/email 都设为可选，
支持匿名使用（仅 user_id 维度）。
"""
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PgUUID(as_uuid=True), primary_key=True, default=uuid4)
    phone: Mapped[str | None] = mapped_column(String(20), unique=True, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(100), unique=True, index=True, nullable=True)
    nickname: Mapped[str | None] = mapped_column(String(50), nullable=True)
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

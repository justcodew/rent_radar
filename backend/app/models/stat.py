"""区域均价统计（替代时序数据库）

每日 Cron 更新，作为价格合理性评分的基线数据。
"""
from datetime import datetime
from uuid import uuid4, UUID

from sqlalchemy import String, Integer, DateTime, func
import uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AreaPriceStat(Base):
    __tablename__ = "area_price_stats"

    id: Mapped[UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    city: Mapped[str] = mapped_column(String(50), index=True)
    area_name: Mapped[str] = mapped_column(String(100), index=True)
    layout: Mapped[str] = mapped_column(String(50))          # 户型
    avg_price: Mapped[int] = mapped_column(Integer)          # 元/月
    sample_count: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

"""独立小区测评路由

用户输入小区名 + 可选片段，LLM 综合评价。
"""
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.database import get_db
from app.services.scoring.community_insights import generate_community_insights
from app.services.scoring.need_match import match_listings_by_need
from app.workers.celery_app import get_redis

router = APIRouter(prefix="/api/v1/insights", tags=["insights"])


class CommunityInsightsRequest(BaseModel):
    community_name: str = Field(..., min_length=1, max_length=100, description="小区名/地名（必填）")
    city: Optional[str] = Field(default="广州", max_length=20)
    area_name: Optional[str] = Field(default=None, max_length=50, description="区域，如天河区")
    layout: Optional[str] = Field(default=None, max_length=50, description="户型，如一室一厅")
    price: Optional[int] = Field(default=None, ge=0, description="月租金")
    size_sqm: Optional[float] = Field(default=None, ge=0)
    floor_info: Optional[str] = Field(default=None, max_length=50)
    orientation: Optional[str] = Field(default=None, max_length=20)
    extra_note: Optional[str] = Field(default=None, max_length=500, description="其他补充")
    force: bool = False


@router.post("/community")
async def community_insights(
    req: CommunityInsightsRequest,
    db: AsyncSession = Depends(get_db),
):
    """小区综合测评（稀疏输入也能用）"""
    try:
        redis = await get_redis()
    except Exception:
        redis = None
    payload = req.model_dump(exclude={"force"})
    result = await generate_community_insights(db, redis, payload, force=req.force)
    return ok(result)


class NeedMatchRequest(BaseModel):
    description: str = Field(..., min_length=2, max_length=1000, description="自然语言需求描述")
    city: Optional[str] = Field(default="广州", max_length=20)
    limit: int = Field(default=12, ge=1, le=50)
    force: bool = False


@router.post("/match")
async def match_by_need(
    req: NeedMatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """自然语言选房：LLM 提取需求 + 推荐小区 + 数据库匹配房源"""
    try:
        redis = await get_redis()
    except Exception:
        redis = None
    result = await match_listings_by_need(
        db, redis, req.description, req.city or "广州", req.limit, force=req.force
    )
    return ok(result)


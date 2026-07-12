"""采集控制路由

触发采集任务(小红书/豆瓣/微博),采集结果自动入库 Listing 表。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.database import get_db

router = APIRouter(prefix="/api/v1/crawl", tags=["crawl"])

#: 支持的采集平台
SUPPORTED_PLATFORMS = {"xhs", "douban", "wb"}


@router.get("/platforms")
async def list_platforms():
    """列出支持的采集平台"""
    return ok({"platforms": list(SUPPORTED_PLATFORMS)})


@router.post("/trigger")
async def trigger_crawl(
    platform: str = Query("xhs", description="平台: xhs/douban/wb"),
    keywords: str = Query("", description="搜索关键词(逗号分隔)"),
    max_count: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """触发采集任务。

    阶段一:返回任务状态(采集引擎在阶段二接入)。
    阶段二:调用 services/crawler/runner.py 执行真实采集。
    """
    if platform not in SUPPORTED_PLATFORMS:
        from app.core.errors import AppException
        raise AppException(f"不支持的平台: {platform}, 支持: {SUPPORTED_PLATFORMS}")

    # 阶段一:返回占位响应(采集引擎待接入)
    return ok({
        "status": "pending",
        "platform": platform,
        "keywords": keywords,
        "max_count": max_count,
        "message": "采集引擎将在阶段二接入,届时自动执行采集+入库+评分",
    })


@router.get("/status/{task_id}")
async def crawl_status(task_id: str):
    """查采集任务状态(阶段二实现)"""
    return ok({
        "task_id": task_id,
        "status": "not_implemented",
        "message": "任务状态追踪将在阶段二实现",
    })

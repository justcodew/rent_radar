"""统一采集入口(阶段二实现)

从 MediaCrawler 迁移 xhs/douban/wb 三平台的采集逻辑,统一入口。

阶段一:空壳,只定义接口。
阶段二:实现 run_crawl(),调用各平台 crawler 执行采集 → extractor 提取 → 入库。
"""
from __future__ import annotations

from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

#: 支持的平台(从 MediaCrawler 精简)
PLATFORMS = ["xhs", "douban", "wb"]


async def run_crawl(
    platform: str,
    keywords: str = "",
    max_count: int = 20,
    **kwargs: Any,
) -> dict:
    """执行采集任务。

    Args:
        platform: 平台(xhs/douban/wb)
        keywords: 搜索关键词(逗号分隔)
        max_count: 最大采集条数

    Returns:
        {"platform": ..., "crawled": N, "ingested": N, "errors": N}

    阶段二实现:
        1. 初始化 crawler(xhs/douban/wb 对应的 core.py)
        2. 执行 search/detail 采集
        3. 用 extractor.py 提取结构化字段
        4. 入库 Listing 表
        5. 触发评分引擎
    """
    logger.info("crawl requested (stage 2 not yet implemented)", platform=platform, keywords=keywords)
    return {
        "platform": platform,
        "status": "not_implemented",
        "message": "采集引擎将在阶段二从 MediaCrawler 迁移接入",
    }

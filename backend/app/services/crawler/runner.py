"""统一采集入口

直接在当前进程内调各平台 crawler(不再走 subprocess,避免进程管理复杂度)。
采集 → extractor 提取 → 入库 Listing 表。
"""
from __future__ import annotations

import json
import os
import asyncio
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = _BACKEND_ROOT / "data"


async def run_crawl(
    platform: str,
    keywords: str = "",
    max_count: int = 20,
    login_type: str = "qrcode",
    cookies: str = "",
    enable_anti_detect: bool = True,
    enable_resume: bool = False,
    **kwargs: Any,
) -> dict:
    """执行采集任务(直接调 crawler core.py,不走 subprocess)。

    采集需要 Chrome CDP 环境(端口 9222)。如果 Chrome 没开,会返回提示。
    采集结果落到 data/<platform>/jsonl/,然后可以用 get_crawled_listings 读取。
    """
    logger.info("crawl started", platform=platform, keywords=keywords)

    # 设置采集配置(通过环境变量传给 crawler 的 config 模块)
    os.environ.setdefault("CRAWLER_TYPE", "search")
    os.environ.setdefault("LOGIN_TYPE", login_type)
    if keywords:
        os.environ["KEYWORDS"] = keywords
    if cookies:
        os.environ["COOKIES"] = cookies

    try:
        if platform == "xhs":
            return await _crawl_xhs(keywords, max_count, login_type, cookies)
        elif platform == "douban":
            return await _crawl_douban(keywords, max_count, login_type, cookies)
        elif platform == "wb":
            return await _crawl_weibo(keywords, max_count, login_type, cookies)
        else:
            raise ValueError(f"不支持的平台: {platform}")
    except Exception as e:
        logger.error("crawl failed", platform=platform, error=str(e))
        raise


async def _crawl_xhs(keywords: str, max_count: int, login_type: str, cookies: str) -> dict:
    """采集小红书"""
    # 动态加载 crawler 配置 + core
    from app.services.crawler.config import base_config as crawl_config
    crawl_config.PLATFORM = "xhs"
    crawl_config.KEYWORDS = keywords or crawl_config.KEYWORDS
    crawl_config.LOGIN_TYPE = login_type
    crawl_config.CRAWLER_TYPE = "search"
    crawl_config.CRAWLER_MAX_NOTES_COUNT = max_count
    crawl_config.SAVE_DATA_OPTION = "jsonl"
    crawl_config.ENABLE_CDP_MODE = True
    crawl_config.ENABLE_ANTI_DETECT = True
    crawl_config.ENABLE_GET_MEIDAS = True      # 下载图片到本地(解决 CDN 过期)
    crawl_config.ENABLE_GET_COMMENTS = True
    if cookies:
        crawl_config.COOKIES = cookies

    from app.services.crawler.platforms.xhs.core import XiaoHongShuCrawler
    crawler = XiaoHongShuCrawler()
    crawler.anti_detect.enabled = True
    await crawler.start()

    # 采集完成,扫描数据文件
    data_files = sorted(str(f) for f in (DATA_DIR / "xhs" / "jsonl").glob("*.jsonl")) if (DATA_DIR / "xhs" / "jsonl").exists() else []
    crawled = 0
    for fpath in data_files:
        if "contents" in fpath:
            with open(fpath, encoding="utf-8") as f:
                crawled += sum(1 for line in f if line.strip())

    return {"platform": "xhs", "status": "success", "crawled": crawled, "data_files": data_files}


async def _crawl_douban(keywords: str, max_count: int, login_type: str, cookies: str) -> dict:
    """采集豆瓣"""
    from app.services.crawler.config import base_config as crawl_config
    crawl_config.PLATFORM = "douban"
    crawl_config.KEYWORDS = keywords or crawl_config.KEYWORDS
    crawl_config.LOGIN_TYPE = login_type
    crawl_config.CRAWLER_TYPE = "search"
    crawl_config.CRAWLER_MAX_NOTES_COUNT = max_count
    crawl_config.SAVE_DATA_OPTION = "jsonl"
    if cookies:
        crawl_config.COOKIES = cookies

    from app.services.crawler.platforms.douban.core import DoubanCrawler
    crawler = DoubanCrawler()
    await crawler.start()

    data_files = sorted(str(f) for f in (DATA_DIR / "douban" / "jsonl").glob("*.jsonl")) if (DATA_DIR / "douban" / "jsonl").exists() else []
    crawled = 0
    for fpath in data_files:
        if "contents" in fpath:
            with open(fpath, encoding="utf-8") as f:
                crawled += sum(1 for line in f if line.strip())

    return {"platform": "douban", "status": "success", "crawled": crawled, "data_files": data_files}


async def _crawl_weibo(keywords: str, max_count: int, login_type: str, cookies: str) -> dict:
    """采集微博"""
    from app.services.crawler.config import base_config as crawl_config
    crawl_config.PLATFORM = "wb"
    crawl_config.KEYWORDS = keywords or crawl_config.KEYWORDS
    crawl_config.LOGIN_TYPE = login_type
    crawl_config.CRAWLER_TYPE = "search"
    crawl_config.CRAWLER_MAX_NOTES_COUNT = max_count
    crawl_config.SAVE_DATA_OPTION = "jsonl"
    if cookies:
        crawl_config.COOKIES = cookies

    from app.services.crawler.platforms.weibo.core import WeiboCrawler
    crawler = WeiboCrawler()
    await crawler.start()

    data_files = sorted(str(f) for f in (DATA_DIR / "weibo" / "jsonl").glob("*.jsonl")) if (DATA_DIR / "weibo" / "jsonl").exists() else []
    crawled = 0
    for fpath in data_files:
        if "contents" in fpath:
            with open(fpath, encoding="utf-8") as f:
                crawled += sum(1 for line in f if line.strip())

    return {"platform": "wb", "status": "success", "crawled": crawled, "data_files": data_files}


async def get_crawled_listings(platform: str, limit: int = 100) -> list[dict]:
    """读取已采集数据,转成 house_pro Listing 格式。"""
    from app.services.crawler.extractor import extract_listing_fields

    # 映射 platform → 数据目录名
    platform_dir_map = {"xhs": "xhs", "douban": "douban", "wb": "weibo"}
    dir_name = platform_dir_map.get(platform, platform)

    platform_dir = DATA_DIR / dir_name / "jsonl"
    if not platform_dir.exists():
        return []

    # 按 note_id 去重,保留最后一条(最新采集的数据,可能补了图片等字段)
    notes_by_id: dict[str, dict] = {}
    for fpath in sorted(platform_dir.glob("*contents*.jsonl")):
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    note = json.loads(line)
                except json.JSONDecodeError:
                    continue
                nid = note.get("note_id") or note.get("topic_id") or note.get("mblog_id") or ""
                if not nid:
                    continue
                notes_by_id[str(nid)] = note  # 后写入覆盖前一条
    notes = list(notes_by_id.values())

    source_map = {"xhs": "xiaohongshu", "douban": "douban", "wb": "weibo"}
    source = source_map.get(platform, platform)
    listings = []
    for note in notes[:limit]:
        note_id = note.get("note_id") or note.get("topic_id") or note.get("mblog_id") or ""
        if not note_id:
            continue
        title = note.get("title", "") or ""
        content = note.get("desc", "") or note.get("content", "") or ""
        fields = extract_listing_fields(content, title)

        listings.append({
            "source": source,
            "source_id": str(note_id),
            "source_url": note.get("note_url", ""),
            "poster_id": note.get("creator_hash", "") or note.get("user_id", ""),
            "poster_name": note.get("nickname", "") or note.get("user_nickname", ""),
            "title": title,
            "content": content,
            "price": fields["price"],
            "layout": fields["layout"],
            "area_name": fields["area_name"],
            "size_sqm": fields["size_sqm"],
            "floor_info": fields["floor_info"],
            "orientation": fields["orientation"],
            "contact_info": fields["contact_info"],
            "image_urls": (
                note.get("image_urls")
                if isinstance(note.get("image_urls"), list)
                else [u.strip() for u in str(note.get("image_urls", "")).split(",") if u.strip()]
            ),
            "raw_data": {**note, "fields_pre_extracted": True},
        })

    return listings

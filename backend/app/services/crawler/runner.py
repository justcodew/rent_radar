"""统一采集入口

通过 subprocess 调用采集脚本(各平台 crawler 独立运行,需 Chrome/Playwright 环境)。
采集完成后,数据通过 house_adapter 转换 → 入库 Listing 表。

支持的平台:xhs(小红书) / douban(豆瓣) / wb(微博)
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

#: 项目根(backend/)
_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent

#: 支持的平台 → 采集脚本路径映射
PLATFORM_SCRIPTS = {
    "xhs": "app/services/crawler/platforms/xhs/run_crawl.py",
    "douban": "app/services/crawler/platforms/douban/run_crawl.py",
    "wb": "app/services/crawler/platforms/weibo/run_crawl.py",
}

#: 采集数据输出目录
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
    """执行采集任务。

    流程:
        1. subprocess 调用平台采集脚本(需 Chrome CDP 环境)
        2. 采集数据落 data/<platform>/jsonl/
        3. 用 house_adapter 转换成 Listing 格式
        4. 返回结果(入库由调用方/Celery 处理)

    Args:
        platform: 平台(xhs/douban/wb)
        keywords: 搜索关键词(逗号分隔)
        max_count: 最大采集条数
        login_type: 登录方式(qrcode/cookie)
        cookies: cookie 字符串(cookie 登录时用)
        enable_anti_detect: 是否启用反检测
        enable_resume: 是否启用断点续爬

    Returns:
        {"platform":..., "status":..., "crawled":N, "data_files":[...]}
    """
    if platform not in PLATFORM_SCRIPTS:
        return {"platform": platform, "status": "error", "message": f"不支持的平台: {platform}"}

    logger.info("crawl started", platform=platform, keywords=keywords, max_count=max_count)

    # 构造采集命令
    cmd = [
        "python3", "-u",
        str(_BACKEND_ROOT / PLATFORM_SCRIPTS[platform]),
        "--keywords", keywords or "",
        "--max-count", str(max_count),
        "--login-type", login_type,
        "--save-option", "jsonl",
    ]
    if cookies:
        cmd.extend(["--cookies", cookies])
    if enable_anti_detect:
        cmd.append("--anti-detect")
    if enable_resume:
        cmd.append("--resume")

    # 执行采集(subprocess,异步)
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(_BACKEND_ROOT),
        )
        stdout, _ = await proc.communicate()
        output = stdout.decode("utf-8", errors="replace") if stdout else ""

        if proc.returncode != 0:
            logger.warning("crawl failed", platform=platform, returncode=proc.returncode)
            return {
                "platform": platform,
                "status": "failed",
                "message": f"采集进程退出码 {proc.returncode}",
                "output": output[-500:],
            }
    except FileNotFoundError:
        # 采集脚本不存在(阶段二尚未写 run_crawl.py),返回占位
        logger.info("crawl script not found, returning placeholder", platform=platform)
        return {
            "platform": platform,
            "status": "pending",
            "message": f"采集脚本 {PLATFORM_SCRIPTS[platform]} 尚未实现,阶段二完成",
        }

    # 采集成功,扫描数据文件
    platform_dir = DATA_DIR / platform / "jsonl"
    data_files = []
    if platform_dir.exists():
        data_files = sorted(str(f) for f in platform_dir.glob("*.jsonl"))

    crawled = 0
    for fpath in data_files:
        with open(fpath, encoding="utf-8") as f:
            crawled += sum(1 for line in f if line.strip())

    logger.info("crawl done", platform=platform, crawled=crawled, files=len(data_files))
    return {
        "platform": platform,
        "status": "success",
        "crawled": crawled,
        "data_files": data_files,
    }


async def get_crawled_listings(platform: str, limit: int = 100) -> list[dict]:
    """读取已采集数据,转成 house_pro Listing 格式。

    复用 house_adapter/extractor + converter 的字段提取逻辑。
    """
    from app.services.crawler.extractor import extract_listing_fields

    platform_dir = DATA_DIR / platform / "jsonl"
    if not platform_dir.exists():
        return []

    notes = []
    for fpath in sorted(platform_dir.glob("*contents*.jsonl")):
        with open(fpath, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        notes.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        if len(notes) >= limit:
            break

    # 转成 Listing 格式
    source_map = {"xhs": "xiaohongshu", "douban": "douban", "wb": "weibo"}
    source = source_map.get(platform, platform)
    listings = []
    for note in notes[:limit]:
        note_id = note.get("note_id") or note.get("topic_id") or ""
        if not note_id:
            continue
        title = note.get("title", "") or ""
        content = note.get("desc", "") or note.get("content", "") or ""
        fields = extract_listing_fields(content, title)

        listings.append({
            "source": source,
            "source_id": str(note_id),
            "source_url": note.get("note_url", ""),
            "poster_id": note.get("creator_hash", ""),
            "poster_name": note.get("nickname", ""),
            "title": title,
            "content": content,
            "price": fields["price"],
            "layout": fields["layout"],
            "area_name": fields["area_name"],
            "size_sqm": fields["size_sqm"],
            "floor_info": fields["floor_info"],
            "orientation": fields["orientation"],
            "contact_info": fields["contact_info"],
            "raw_data": {**note, "fields_pre_extracted": True},
        })

    return listings

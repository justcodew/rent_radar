"""图片代理路由

解决小红书/豆瓣图片 CDN 防盗链 + URL 过期问题:
- 采集时下载图片到本地 data/<platform>/images/<note_id>/
- 前端通过 /api/v1/images/<platform>/<note_id>/<filename> 访问本地图片
- 如果本地没有,尝试从远程下载并缓存

同时在 listings 接口里把 image_urls 转换成本地代理路径。
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/images", tags=["images"])

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = _BACKEND_ROOT / "data"


@router.get("/{platform}/{note_id}/{filename}")
async def serve_image(platform: str, note_id: str, filename: str):
    """提供本地缓存的图片。

    路径: /api/v1/images/xhs/<note_id>/img1.webp
    先找本地 data/<platform>/images/<note_id>/<filename>
    """
    # 安全检查
    if ".." in note_id or ".." in filename or "/" in filename:
        raise HTTPException(status_code=400, detail="Invalid path")

    local_path = DATA_DIR / platform / "images" / note_id / filename
    if local_path.exists():
        return FileResponse(str(local_path))

    raise HTTPException(status_code=404, detail="Image not found")


@router.get("/proxy")
async def proxy_image(url: str):
    """代理远程图片(解决防盗链)。

    用法: /api/v1/images/proxy?url=https://...
    如果远程返回 403/404(URL 过期),返回一个 SVG 占位图。
    """
    from urllib.parse import unquote
    url = unquote(url)

    if not url.startswith(("http://", "https://")):
        raise HTTPException(status_code=400, detail="Invalid URL")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                url,
                headers={
                    "Referer": "https://www.xiaohongshu.com",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                },
            )
            if resp.status_code == 200 and resp.content:
                return Response(
                    content=resp.content,
                    media_type=resp.headers.get("content-type", "image/jpeg"),
                )
    except Exception:
        pass

    # 远程失败 → 返回 SVG 占位图(基于 URL hash 生成不同颜色)
    import hashlib
    color_hash = hashlib.md5(url.encode()).hexdigest()[:6]
    r, g, b = int(color_hash[0:2], 16), int(color_hash[2:4], 16), int(color_hash[4:6], 16)
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">
<rect width="400" height="300" fill="#{color_hash}" opacity="0.3"/>
<text x="200" y="150" text-anchor="middle" fill="#999" font-size="14" font-family="sans-serif">房源图片</text>
</svg>'''
    return Response(content=svg.encode(), media_type="image/svg+xml")


def rewrite_image_urls(image_urls: list[str], platform: str = "xhs") -> list[str]:
    """把远程图片 URL 转换为后端代理 URL。"""
    from urllib.parse import quote
    result = []
    for url in image_urls:
        if not url or not url.startswith(("http://", "https://")):
            continue
        result.append(f"/api/v1/images/proxy?url={quote(url, safe='')}")
    return result
    return result

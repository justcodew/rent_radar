"""HTTP 中间件：注入 request_id、记录访问日志、上报异常"""
from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import bind_request_context, get_logger

logger = get_logger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """每个请求注入 X-Request-ID；上游带过来就用，没带就生成。
    所有日志会自动带上这个 request_id（通过 structlog contextvar）。"""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        bind_request_context(
            request_id=request_id,
            method=request.method,
            path=request.url.path,
        )

        start = time.perf_counter()
        response: Response | None = None
        try:
            response = await call_next(request)
            return response
        except Exception as exc:
            logger.error(
                "request_crashed",
                error=str(exc),
                error_type=type(exc).__name__,
            )
            raise
        finally:
            duration_ms = int((time.perf_counter() - start) * 1000)
            status = response.status_code if response else 500
            # 静态/健康检查不打 access 日志，避免噪音
            if request.url.path not in ("/health", "/", "/docs", "/openapi.json", "/redoc"):
                logger.info(
                    "request_completed",
                    status=status,
                    duration_ms=duration_ms,
                )
            if response is not None:
                response.headers["X-Request-ID"] = request_id

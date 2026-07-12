"""结构化日志（structlog）+ Sentry 集成

策略：
- 开发环境 (DEBUG=true)：彩色 ConsoleRenderer，方便人读
- 生产环境：JSONRenderer，方便 ELK/Loki 采集
- 启用 Sentry（SENTRY_DSN 非空时）：所有 WARNING+ 自动上报，trace 与 structlog 互通
- request_id 注入：每个 HTTP 请求由中间件 bind 一份 contextvar，所有日志带上
"""
import logging
import sys

import structlog

from app.config import settings


_sentry_initialized = False


def _setup_sentry_if_configured():
    """如果配置了 SENTRY_DSN 就初始化 sentry-sdk"""
    global _sentry_initialized
    dsn = getattr(settings, "SENTRY_DSN", "") or ""
    if not dsn:
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.redis import RedisIntegration
        sentry_sdk.init(
            dsn=dsn,
            environment=settings.APP_ENV,
            traces_sample_rate=getattr(settings, "SENTRY_TRACES_RATE", 0.1),
            send_default_pii=False,
            integrations=[
                FastApiIntegration(),
                RedisIntegration(),
            ],
        )
        _sentry_initialized = True
    except ImportError:
        # 没装 sentry-sdk 就跳过
        pass


def setup_logging():
    """配置 structlog + stdlib logging，幂等可重复调用"""
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    is_dev = settings.DEBUG or settings.APP_ENV == "development"

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=level,
        force=True,
    )

    if is_dev:
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        renderer = structlog.processors.JSONRenderer()

    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        _redact_processor,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    if _sentry_initialized:
        processors.append(_sentry_processor)
    processors.append(renderer)

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(level),
        cache_logger_on_first_use=True,
        logger_factory=structlog.PrintLoggerFactory(),
    )

    # uvicorn / sqlalchemy / celery 的 logger 走 structlog 处理
    for name in ("uvicorn", "uvicorn.access", "sqlalchemy.engine", "celery"):
        std_logger = logging.getLogger(name)
        std_logger.handlers = []
        std_logger.propagate = True

    _setup_sentry_if_configured()


def get_logger(name: str = __name__):
    return structlog.get_logger(name)


# ===== helpers =====

_SENSITIVE_KEYS = {"password", "password_hash", "token", "access_token", "refresh_token",
                   "authorization", "cookie", "secret", "api_key"}


def _redact_processor(logger, method_name, event_dict):
    """敏感字段打码"""
    for k in list(event_dict.keys()):
        if k.lower() in _SENSITIVE_KEYS:
            event_dict[k] = "***"
    return event_dict


def _sentry_processor(logger, method_name, event_dict):
    """把 structlog 的 WARNING+ 推到 sentry breadcrumb"""
    try:
        import sentry_sdk
        level = event_dict.get("level", "info").lower()
        if level in ("warning", "error", "critical"):
            sentry_sdk.add_breadcrumb(
                data=event_dict,
                category=event_dict.get("event", "log"),
                level=level,
            )
        if level in ("error", "critical"):
            msg = event_dict.get("event") or event_dict.get("message") or "error"
            sentry_sdk.capture_message(msg, level=level)
    except Exception:
        pass
    return event_dict


def bind_request_context(request_id: str, **extras):
    """每个请求开始时调用，把 request_id 等信息绑到 contextvar"""
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id, **extras)

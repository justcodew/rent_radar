"""FastAPI 应用入口"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.core.errors import AppException
from app.core.logging import setup_logging, get_logger
from app.core.middleware import RequestIdMiddleware
from app.routers import auth, profiles, listings, scores, search, recommend, favorites, insights, crawl
from app.routers import images as images_router
from app.routers import prompts as prompts_router
from app.routers import cases as cases_router
from app.routers import subway as subway_router

setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("app starting", env=settings.APP_ENV, debug=settings.DEBUG)
    yield
    logger.info("app stopping")


app = FastAPI(
    title="好房雷达 API",
    description="智能租房分析与推荐工具",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS（开发环境）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.DEBUG else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID + 访问日志（最外层，最先入最晚出）
app.add_middleware(RequestIdMiddleware)


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=200,
        content={"code": int(exc.code), "message": exc.message, "data": exc.data},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
    )
    # 上报到 Sentry（如启用）；FastApiIntegration 会自动捕获，
    # 但显式 capture 确保被 @app.exception_handler 吃掉的也能上去
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except Exception:
        pass
    return JSONResponse(
        status_code=500,
        content={"code": 500, "message": "服务器内部错误", "data": None},
    )


@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.APP_ENV}


@app.get("/")
async def root():
    return {
        "name": "好房雷达 API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# 注册路由
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(listings.router)
app.include_router(scores.router)
app.include_router(search.router)
app.include_router(recommend.router)
app.include_router(favorites.router)
app.include_router(insights.router)
app.include_router(crawl.router)
app.include_router(images_router.router)
app.include_router(prompts_router.router)
app.include_router(cases_router.router)
app.include_router(subway_router.router)

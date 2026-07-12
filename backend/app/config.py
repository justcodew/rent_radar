"""应用配置（pydantic-settings 自动从环境变量加载）"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # 基础
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://haofang:haofang@localhost:5432/haofang"
    DATABASE_SYNC_URL: str = "postgresql+psycopg2://haofang:haofang@localhost:5432/haofang"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # JWT
    JWT_SECRET: str = "dev-only-change-in-production-please"
    JWT_ACCESS_TTL_MINUTES: int = 60
    JWT_REFRESH_TTL_DAYS: int = 7

    # 外部服务
    AMAP_API_KEY: str = ""
    AMAP_BASE_URL: str = "https://restapi.amap.com/v3"

    # LLM（按需）
    LLM_API_KEY: str = ""
    LLM_BASE_URL: str = ""
    LLM_MODEL: str = ""
    LLM_DAILY_BUDGET_CNY: float = 50.0
    LLM_MONTHLY_BUDGET_CNY: float = 1500.0

    # 爬虫
    DOUBAN_COOKIE: str = ""
    CRAWLER_INTERVAL_SECONDS: int = 21600

    # 小红书（MediaCrawler 输出目录）
    # MediaCrawler 以独立进程运行（CDP 模式 + Playwright），把搜索结果的 JSON 落到这个目录，
    # 我们定时扫描、解析、入库，然后归档到 processed/
    XHS_RAW_DIR: str = "data/xhs_raw"

    # 评分
    SCORE_RULE_VERSION: str = "rule-v1"

    # 观测
    SENTRY_DSN: str = ""
    SENTRY_TRACES_RATE: float = 0.1


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

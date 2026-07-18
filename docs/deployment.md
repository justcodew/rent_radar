# 部署指南

本文档面向部署人员，说明如何运行、部署和维护租房雷达。

## 一、环境要求

| 依赖 | 版本 | 说明 |
|------|------|------|
| Python | >= 3.11 | 后端 |
| Node.js | >= 16 | 前端构建 |
| PostgreSQL | 15+(推荐) / SQLite(开发) | 数据库 |
| Redis | 7+(可选) | 缓存/Celery |
| Chrome | 最新版 | 采集需要(CDP 模式) |

## 二、Docker 部署(推荐)

### 2.1 配置

```bash
cp .env.example .env
```

编辑 `.env`，至少修改：

```bash
# 必改
JWT_SECRET=你的随机密钥          # openssl rand -hex 32

# AI 功能(不配则小区测评/AI选房/深度洞察不可用)
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://apihub.agnes-ai.com/v1
LLM_MODEL=agnes-1.5-flash

# 可选(通勤计算)
AMAP_API_KEY=高德地图API密钥
```

### 2.2 启动

```bash
docker-compose up -d
```

启动后：
- 前端: http://localhost:5174
- API 文档: http://localhost:8000/docs
- PostgreSQL: localhost:5433
- Redis: localhost:6380

### 2.3 停止

```bash
docker-compose down          # 停止(保留数据)
docker-compose down -v       # 停止+删除数据卷
```

## 三、本地开发部署(无 Docker)

### 3.1 后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置
cp ../.env.example .env
# 编辑 .env，DATABASE_URL 改为 SQLite:
# DATABASE_URL=sqlite+aiosqlite:///./rent_radar.db

# 建表(自动)
python -c "
import asyncio
from app.database import engine, Base
from app.models import user, listing, score, profile, favorite, task, stat
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
"

# 启动 API
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3.2 前端

```bash
cd frontend
npm install --registry=https://registry.npmmirror.com  # 国内加速
npm run dev    # 开发模式 http://localhost:5173
# 或
npm run build  # 生产构建 → dist/
```

### 3.3 采集环境(可选)

采集需要 Chrome CDP：

```bash
# 启动带远程调试的 Chrome
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome_rent_radar \
  --no-first-run

# 在 Chrome 窗口里手动登录小红书/豆瓣/微博
# 然后通过 WebUI「采集」页触发采集
```

## 四、数据库说明

### 4.1 PostgreSQL vs SQLite

| | PostgreSQL | SQLite |
|---|---|---|
| 生产环境 | ✅ 推荐 | ❌ |
| 开发调试 | ✅ | ✅ 更简单 |
| JSONB 支持 | 原生 | 兼容(JSON) |
| 全文检索 | GIN 索引 | ILIKE |
| 迁移 | alembic | 自动建表 |

切换方式：修改 `.env` 的 `DATABASE_URL`。

### 4.2 主要表

| 表名 | 说明 |
|------|------|
| `listings` | 房源(含 price/area_name/layout/image_urls/raw_data) |
| `listing_scores` | 评分(好房指数 100 分制 + 8 维度子分) |
| `profiles` | 租房画像(预算/区域/户型/通勤需求) |
| `match_scores` | 匹配度(个性化推荐) |
| `favorites` | 收藏 |
| `area_price_stats` | 区域均价统计(评分引擎用) |

### 4.3 初始化

```bash
# Docker 模式:自动执行 infrastructure/postgres/init.sql
# 本地 SQLite:首次启动自动建表
# 手动重新建表:
python -c "
import asyncio
from app.database import engine, Base
from app.models import *
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
"
```

## 五、Celery 定时任务(可选)

定时采集 + 评分。需要 Redis。

```bash
# 启动 Worker
celery -A app.workers.celery_app worker --loglevel=info

# 启动 Beat(定时调度)
celery -A app.workers.celery_app beat --loglevel=info
```

定时任务配置(`app/workers/celery_app.py`):

| 任务 | 频率 | 说明 |
|------|------|------|
| crawl_xiaohongshu | 每 30 分钟 | 采集小红书 |
| crawl_douban | 每 6 小时 | 采集豆瓣 |
| recalc_top_scores | 每天 03:00 | 重算高分房源评分 |
| update_area_price_stats | 每周一 04:00 | 更新区域均价 |

## 六、常见问题

### Q: 图片不显示?

A: 小红书图片 CDN 有时效性。解决方案：
1. 采集时确保 `ENABLE_GET_MEIDAS=True`(图片下载到本地)
2. 后端图片代理 `/api/v1/images/proxy` 自动兜底

### Q: AI 功能报错?

A: 检查 `.env` 的 `LLM_API_KEY` 和 `LLM_BASE_URL`。支持的 LLM：
- Agnes AI (推荐,免费): `https://apihub.agnes-ai.com/v1` + `agnes-1.5-flash`
- OpenAI: `https://api.openai.com/v1` + `gpt-4o-mini`
- DeepSeek / 智谱 / 通义千问等 OpenAI 兼容接口

### Q: 采集失败?

A: 常见原因：
1. Chrome CDP 端口(9222)未开启
2. 小红书/豆瓣未登录(需在 Chrome 窗口手动扫码)
3. 反检测触发风控(查看 `data/risk_screenshots/` 截图)

### Q: PostgreSQL 连不上?

A: 开发时可临时用 SQLite：
```bash
# .env
DATABASE_URL=sqlite+aiosqlite:///./rent_radar.db
```

## 七、日志

```bash
# Docker
docker-compose logs -f api
docker-compose logs -f worker

# 本地
tail -f /tmp/rent_radar_be.log
```

## 八、备份

```bash
# PostgreSQL
docker exec rent_radar_pg pg_dump -U radar rent_radar > backup.sql

# SQLite
cp backend/rent_radar.db backup.db
```

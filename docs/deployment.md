# 部署指南

本文档面向部署人员，说明如何运行、部署和维护租房雷达。

提供 **3 种部署方式**，从简单到完整，按需选择：

| 方式 | 适合场景 | 需要 | 耗时 |
|------|---------|------|------|
| [方式一：纯本地](#方式一纯本地开发最简单) | 开发调试、快速体验 | Python + Node.js | 5 分钟 |
| [方式二：Docker 一键](#方式二docker-一键部署推荐生产) | 生产部署 | Docker | 3 分钟 |
| [方式三：混合部署](#方式三混合部署本地代码--docker-数据库) | 开发但需要 PG/Redis | Python + Node.js + Docker | 8 分钟 |

---

## 前置准备

### 必须安装

| 依赖 | 版本要求 | 安装方式 | 验证 |
|------|---------|---------|------|
| Python | >= 3.11 | [python.org](https://www.python.org/downloads/) | `python3 --version` |
| Node.js | >= 16 | [nodejs.org](https://nodejs.org/) | `node --version` |

### 可选安装（按方式不同）

| 依赖 | 何时需要 |
|------|---------|
| Docker Desktop | 方式二、方式三 |
| PostgreSQL 15 | 方式二(Docker自带)、方式三(可手动装) |
| Redis 7 | 方式二(Docker自带)、定时采集(可选) |
| Google Chrome | 采集功能（任何方式都需要） |

### 获取代码

```bash
git clone https://github.com/justcodew/rent_radar.git
cd rent_radar
```

---

## 方式一：纯本地开发（最简单）

**不需要 Docker、PostgreSQL、Redis。** 用 SQLite 做数据库，Redis 不可用时自动跳过。

### 步骤 1：配置

```bash
cp .env.example backend/.env
```

编辑 `backend/.env`，修改以下项（其他保持默认即可）：

```bash
# 数据库：用 SQLite（不需要安装 PostgreSQL）
DATABASE_URL=sqlite+aiosqlite:///./rent_radar.db
DATABASE_SYNC_URL=sqlite:///./rent_radar.db

# 必改：JWT 密钥（随便填一串字符）
JWT_SECRET=rent-radar-my-secret-key-123456

# AI 功能（不配则 AI 功能不可用，其他功能正常）
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://apihub.agnes-ai.com/v1
LLM_MODEL=agnes-1.5-flash

# Redis（本地没装的话留空即可，系统会自动跳过缓存）
REDIS_URL=redis://localhost:6379/0
```

### 步骤 2：启动后端

```bash
cd backend

# 创建虚拟环境（推荐但非必须）
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
# 国内加速: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 首次运行：自动建表（SQLite）
python3 -c "
import asyncio
from app.database import engine, Base
from app.models import user, listing, score, profile, favorite, task, stat
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✓ 数据库建表完成')
asyncio.run(init())
"

# 启动 API 服务（开发模式，改代码自动重载）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

看到以下输出说明成功：
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

验证：浏览器打开 http://localhost:8000/docs 看到 API 文档。

### 步骤 3：启动前端

**另开一个终端**（后端保持运行）：

```bash
cd rent_radar/frontend

# 安装依赖
npm install
# 国内加速: npm install --registry=https://registry.npmmirror.com

# 启动开发服务器
npm run dev
```

看到以下输出说明成功：
```
VITE v5.x  ready in xxx ms
➜  Local:   http://localhost:5173/
```

### 步骤 4：访问

浏览器打开 http://localhost:5173

### 步骤 5：初始化数据（可选）

刚启动时数据库是空的，你可以：
- 通过「采集」页采集房源数据（需要 Chrome）
- 或导入已有数据：

```bash
cd backend
python3 -c "
import asyncio, json
from app.database import AsyncSessionLocal
from app.models.listing import Listing
from app.services.crawler.extractor import extract_listing_fields

async def seed():
    # 从已有 jsonl 导入
    import glob
    files = glob.glob('data/xhs/jsonl/*contents*.jsonl')
    if not files:
        print('无数据文件，请先采集')
        return
    async with AsyncSessionLocal() as db:
        count = 0
        for f in files:
            with open(f) as fh:
                for line in fh:
                    if not line.strip(): continue
                    note = json.loads(line)
                    nid = note.get('note_id','')
                    if not nid: continue
                    title = note.get('title','')
                    content = note.get('desc','')
                    fields = extract_listing_fields(content, title)
                    db.add(Listing(
                        source='xiaohongshu', source_id=nid,
                        source_url=note.get('note_url',''),
                        poster_name=note.get('nickname',''),
                        title=title, content=content[:5000],
                        price=fields['price'], area_name=fields['area_name'],
                        layout=fields['layout'], raw_data=note))
                    count += 1
        await db.commit()
        print(f'✓ 导入 {count} 条房源')

asyncio.run(seed())
"
```

### 方式一优缺点

| ✅ 优点 | ❌ 限制 |
|--------|--------|
| 无需 Docker/PG/Redis | SQLite 不支持并发写入 |
| 5 分钟启动 | 无定时采集（需手动触发） |
| 改代码自动重载 | 无全文索引（用 ILIKE 替代） |
| 适合开发调试 | 生产环境不建议 |

---

## 方式二：Docker 一键部署（推荐生产）

**最省心。** 一个命令启动全部 4 个容器（PostgreSQL + Redis + API + 前端）。

### 步骤 1：配置

```bash
cp .env.example .env
```

编辑 `.env`：

```bash
# 数据库（Docker 内 PostgreSQL，不用改）
DATABASE_URL=postgresql+asyncpg://radar:radar_secret_2026@postgres:5432/rent_radar

# 必改
JWT_SECRET=$(openssl rand -hex 32)  # 生成随机密钥

# AI
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://apihub.agnes-ai.com/v1
LLM_MODEL=agnes-1.5-flash

# Redis（Docker 内自带）
REDIS_URL=redis://redis:6379/0
```

### 步骤 2：启动

```bash
docker-compose up -d
```

等待 30 秒让数据库初始化完成。

### 步骤 3：访问

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5174 |
| API 文档 | http://localhost:8000/docs |
| PostgreSQL | localhost:5433 |
| Redis | localhost:6380 |

### 步骤 4：初始化数据库

Docker 首次启动会自动执行 `infrastructure/postgres/init.sql`（pgvector 扩展）。
如需手动建表：

```bash
docker exec rent_radar_api python -c "
import asyncio
from app.database import engine, Base
from app.models import *
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
"
```

### 步骤 5：停止/重启

```bash
docker-compose stop           # 暂停
docker-compose start          # 恢复
docker-compose down           # 停止并删除容器（数据保留）
docker-compose down -v        # 停止并删除数据（慎重！）
docker-compose logs -f api    # 查看后端日志
docker-compose logs -f web    # 查看前端日志
```

### 方式二优缺点

| ✅ 优点 | ❌ 限制 |
|--------|--------|
| 一键启动全部服务 | 需要 Docker |
| PostgreSQL + Redis 完整 | 改代码需重新 build |
| 支持定时采集(Celery) | 首次拉取镜像较慢 |
| 生产级部署 | |

---

## 方式三：混合部署（本地代码 + Docker 数据库）

**适合开发调试但需要 PostgreSQL 的场景。** 数据库用 Docker，代码本地跑（改代码即时生效）。

### 步骤 1：用 Docker 启动数据库

```bash
# 只启动 PostgreSQL + Redis
docker-compose up -d postgres redis

# 等待 10 秒
sleep 10

# 验证
docker exec rent_radar_pg pg_isready -U radar
# 输出: accepting connections
```

### 步骤 2：配置

```bash
cp .env.example backend/.env
```

编辑 `backend/.env`：

```bash
# 连接 Docker 里的 PostgreSQL（注意端口映射 5433）
DATABASE_URL=postgresql+asyncpg://radar:radar_secret_2026@localhost:5433/rent_radar

# Redis
REDIS_URL=redis://localhost:6380/0

# 其他同方式一
JWT_SECRET=你的密钥
LLM_API_KEY=你的API密钥
LLM_BASE_URL=https://apihub.agnes-ai.com/v1
LLM_MODEL=agnes-1.5-flash
```

### 步骤 3：启动后端

```bash
cd backend
pip install -r requirements.txt

# 建表
python3 -c "
import asyncio
from app.database import engine, Base
from app.models import *
async def init():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
asyncio.run(init())
"

# 启动
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 步骤 4：启动前端

```bash
cd frontend
npm install
npm run dev
```

### 方式三优缺点

| ✅ 优点 | ❌ 限制 |
|--------|--------|
| 代码改了即时生效 | 需要管理 3 个进程 |
| 完整 PG + Redis 功能 | 配置稍复杂 |
| 适合开发 + 测试 | |

---

## 采集环境配置（三种方式通用）

采集功能需要 Chrome 浏览器配合，与部署方式无关。

### 启动 Chrome（CDP 模式）

**另开一个终端**，保持运行：

```bash
# macOS
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome_rent_radar \
  --no-first-run

# Windows
"C:\Program Files\Google\Chrome\Application\chrome.exe" \
  --remote-debugging-port=9222 \
  --user-data-dir=C:\temp\chrome_rent_radar

# Linux
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome_rent_radar
```

### 登录目标平台

在弹出的 Chrome 窗口里，手动登录：
- 小红书：https://www.xiaohongshu.com
- 豆瓣：https://www.douban.com
- 微博：https://weibo.com

### 触发采集

在 WebUI「采集」页面操作，或通过 API：

```bash
# 触发小红书采集
curl -X POST "http://localhost:8000/api/v1/crawl/trigger?platform=xhs&keywords=广州越秀两房出租&max_count=20"

# 查采集进度
curl "http://localhost:8000/api/v1/crawl/status/{task_id}"

# 入库 + 评分
curl -X POST "http://localhost:8000/api/v1/crawl/ingest?platform=xhs"
```

---

## 数据库说明

### 主要表结构

| 表名 | 说明 | 关键字段 |
|------|------|---------|
| `listings` | 房源 | source, source_id, title, content, price, area_name, image_urls, raw_data |
| `listing_scores` | 评分 | general_score(100分制), poster_score, listing_score, risk_tags |
| `profiles` | 租房画像 | budget_min/max, areas, layouts, commute |
| `match_scores` | 匹配度 | match_score, personalized_score |
| `favorites` | 收藏 | category(待看/看过/不考虑/已租) |
| `area_price_stats` | 区域均价 | avg_price, sample_count |

### PostgreSQL vs SQLite 选择

| 场景 | 推荐 | 原因 |
|------|------|------|
| 开发调试 | SQLite | 零安装，开箱即用 |
| 单人使用 | SQLite | 数据量小，够用 |
| 多人/生产 | PostgreSQL | 并发写入 + 全文检索 + JSONB |
| 需要定时采集 | PostgreSQL + Redis | Celery 需要 Redis |

### 切换数据库

只需改 `.env` 的 `DATABASE_URL`：

```bash
# SQLite
DATABASE_URL=sqlite+aiosqlite:///./rent_radar.db

# PostgreSQL (Docker)
DATABASE_URL=postgresql+asyncpg://radar:radar_secret_2026@localhost:5433/rent_radar

# PostgreSQL (本地安装)
DATABASE_URL=postgresql+asyncpg://用户名:密码@localhost:5432/rent_radar
```

改完重启后端即可，首次启动自动建表。

---

## Celery 定时任务（可选）

> 仅 PostgreSQL + Redis 环境可用

### 启动

```bash
cd backend

# Worker（执行任务）
celery -A app.workers.celery_app worker --loglevel=info

# Beat（定时调度，另开终端）
celery -A app.workers.celery_app beat --loglevel=info
```

### 定时任务配置

| 任务 | 频率 | 说明 |
|------|------|------|
| crawl_xiaohongshu | 每 30 分钟 | 自动采集小红书 |
| crawl_douban | 每 6 小时 | 自动采集豆瓣 |
| recalc_top_scores | 每天 03:00 | 重算高分房源评分 |
| update_area_price_stats | 每周一 04:00 | 更新区域均价统计 |

### 修改频率

编辑 `app/workers/celery_app.py` 的 `beat_schedule`：

```python
"crawl-xiaohongshu-every-30m": {
    "task": "app.workers.celery_app.crawl_xiaohongshu",
    "schedule": 1800,  # 秒，改为 3600 = 1小时
},
```

---

## 常见问题

### Q: 启动后端报 ModuleNotFoundError？

```bash
# 确保在 backend/ 目录下，且依赖已装
cd backend
pip install -r requirements.txt
```

### Q: 图片不显示？

小红书图片 CDN 有时效性（URL 里的签名会过期）。解决方案：
1. 采集时确保 `ENABLE_GET_MEIDAS=True`（图片下载到本地）
2. 后端图片代理 `/api/v1/images/proxy` 会自动兜底（返回占位图）
3. 重新采集一次，新图片会下载到本地永久保存

### Q: AI 功能报错？

检查 `.env`：
```bash
LLM_API_KEY=是否填写
LLM_BASE_URL=是否正确
LLM_MODEL=模型名是否支持
```

测试 LLM 连通性：
```bash
curl -X POST "http://localhost:8000/api/v1/insights/community" \
  -H "Content-Type: application/json" \
  -d '{"community_name":"公园前","city":"广州"}'
```

### Q: 采集失败（Timeout）？

1. Chrome CDP 端口是否开启：`curl http://localhost:9222/json/version`
2. Chrome 窗口里是否已登录目标平台
3. 是否触发风控：查看 `data/risk_screenshots/` 目录有没有截图
4. 采集需要时间（20条约 2-3 分钟），确保前端超时设置为 300 秒

### Q: PostgreSQL 连不上？

临时切 SQLite 开发：
```bash
# backend/.env
DATABASE_URL=sqlite+aiosqlite:///./rent_radar.db
```

### Q: 前端页面空白？

```bash
# 检查前端是否在运行
curl http://localhost:5173

# 检查后端是否可达
curl http://localhost:8000/health

# 检查 vite proxy 配置（frontend/vite.config.ts）
# 确保 /api 代理到 http://localhost:8000
```

---

## 日志查看

```bash
# Docker 模式
docker-compose logs -f api       # 后端
docker-compose logs -f web       # 前端
docker-compose logs -f postgres  # 数据库

# 本地模式
tail -f /tmp/rent_radar_be.log   # 后端（如果用 nohup 启动）
# 或直接看 uvicorn 终端输出

# 采集日志
ls data/risk_screenshots/        # 风控截图（如触发）
```

---

## 数据备份与恢复

### PostgreSQL

```bash
# 备份
docker exec rent_radar_pg pg_dump -U radar rent_radar > backup_$(date +%Y%m%d).sql

# 恢复
cat backup_20260719.sql | docker exec -i rent_radar_pg psql -U radar rent_radar
```

### SQLite

```bash
# 备份（就是复制文件）
cp backend/rent_radar.db backup_$(date +%Y%m%d).db

# 恢复
cp backup_20260719.db backend/rent_radar.db
```

### 采集数据

```bash
# data/ 目录包含了所有采集的原始数据
tar czf crawl_data_backup.tar.gz data/
```

---

## 维护与优化建议

### 定期维护

| 任务 | 频率 | 命令 |
|------|------|------|
| 备份数据库 | 每天 | 见上方备份命令 |
| 清理旧风控截图 | 每周 | `rm data/risk_screenshots/risk_*.png` |
| 重算评分 | 每周 | Celery 自动 / API 手动触发 |
| 更新区域均价 | 每周 | Celery 自动 |

### 性能优化

1. **数据库索引**：确保 listings 表的 source, source_id, price, area_name 有索引
2. **图片存储**：大量图片时考虑用 CDN 或对象存储替代本地路径
3. **采集频率**：避免过于频繁（建议 30 分钟以上间隔）
4. **前端构建**：生产环境用 `npm run build` 替代 `npm run dev`

### 功能扩展方向

1. 新增采集平台：在 `services/crawler/platforms/` 下新增平台目录
2. 新增评分维度：在 `services/scoring/rule_engine.py` 添加 `calc_xxx_score` 函数
3. 新增标签类型：在 `services/crawler/extractor.py` 的 `extract_tags()` 添加提取规则
4. 自定义 AI 提示词：通过 `/api/v1/prompts/community` 接口或前端编辑器
5. 新增需求案例：在 `routers/cases.py` 的 `CASES` 列表添加新案例

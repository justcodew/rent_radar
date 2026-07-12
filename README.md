# 租房雷达(rent_radar)

> 多平台租房信息采集 + 智能评分 + 推荐系统

整合 MediaCrawler(采集引擎)与好房雷达(house_pro,评分/推荐/前端)的专注租房的单体应用。

## 功能

- **采集**:小红书 + 豆瓣 + 微博租房信息(CDP 登录 + 反检测 + 断点续爬)
- **评分**:好房指数(100分制),发布者特征 + 房源特征 + AI 增强
- **推荐**:基于租房画像的个性化匹配(价格/通勤/区域/户型)
- **展示**:React 前端(房源列表/详情/搜索/收藏/小区测评)

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy(async) + Celery |
| 数据库 | PostgreSQL 15(pgvector) |
| 缓存 | Redis 7 |
| 前端 | React 18 + TypeScript + Vite + TailwindCSS |
| 采集 | Playwright + httpx + parsel |
| AI | OpenAI 兼容 LLM(评分增强/深度洞察/自然语言选房) |

## 快速开始

```bash
# 1. 配置
cp .env.example .env
# 按需修改(至少改 JWT_SECRET / LLM_API_KEY)

# 2. 启动(需要 Docker)
docker-compose up -d

# 3. 访问
# API: http://localhost:8000/docs
# 前端: http://localhost:5174
```

## 项目结构

```
rent_radar/
├── docker-compose.yml          # postgres + redis + api + web
├── backend/
│   ├── app/
│   │   ├── main.py             # FastAPI 入口
│   │   ├── config.py           # 统一配置
│   │   ├── database.py         # SQLAlchemy 引擎
│   │   ├── models/             # 7 个 ORM 模型
│   │   ├── schemas/            # Pydantic DTO
│   │   ├── routers/            # 9 个路由(含采集控制)
│   │   ├── services/
│   │   │   ├── scoring/        # 评分引擎(规则+AI+洞察+选房)
│   │   │   ├── matching/       # 匹配引擎(匹配度+通勤)
│   │   │   └── crawler/        # ★采集引擎(xhs/douban/wb + 反检测 + 断点续爬)
│   │   └── workers/            # Celery(定时采集→入库→评分)
│   └── requirements.txt
├── frontend/                   # React SPA(13页面+8组件,含采集控制台)
└── infrastructure/
    └── postgres/init.sql       # pgvector 初始化
```

## 开发路线

- ✅ **阶段一**:骨架搭建(目录/配置/docker-compose/路由/前端)
- ✅ **阶段二**:采集引擎迁移(MediaCrawler xhs/douban/wb → services/crawler/)
- ✅ **阶段三**:评分/推荐引擎接入(scoring + matching + Celery 定时任务)
- ✅ **前端**:采集控制台页面 + crawlApi 封装

## 来源

- 采集能力来自 [MediaCrawler](../agent_pro/MediaCrawler)(精简为 xhs/douban/wb)
- 评分/推荐/前端来自 [house_pro](../house_pro)(好房雷达)

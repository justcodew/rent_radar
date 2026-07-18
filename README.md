# 租房雷达(rent_radar)

> 多平台租房信息采集 + 智能评分 + AI 分析 + 推荐系统

从小红书/豆瓣/微博采集真实租房信息，自动提取价格/户型/楼层/电梯/朝向/地铁站等关键标签，AI 中介识别 + 好房指数评分 + 深度洞察 + 自然语言选房。

## 功能一览

| 功能 | 说明 |
|------|------|
| 🔍 搜索 | 按区域/价格/户型/评分筛选房源 |
| 📋 案例 | 预设需求案例(如"越秀4K电梯阳台两房"),含AI推荐片区+匹配房源+现实分析 |
| 🕷️ 采集 | 小红书/豆瓣/微博三平台采集,带反检测+断点续爬 |
| 🤖 AI选房 | 自然语言描述需求,AI提取结构化需求+推荐小区+匹配房源 |
| 🏘️ 小区测评 | 输入小区名,AI"老广"帮你分析优缺点+周边配套 |
| 📊 推荐 | 基于租房画像的个性化匹配(价格/通勤/区域/户型) |
| 🏷️ 标签 | 自动提取:房型/面积/楼层(步梯几楼)/电梯(原生/加装)/阳台/朝向/地铁站/已租出 |
| 🔍 中介识别 | 7维度判断发帖人是否中介 |

## 快速开始

```bash
# 1. 配置
cp .env.example .env
# 编辑 .env:改 JWT_SECRET / LLM_API_KEY / 可选 AMAP_API_KEY

# 2. Docker 启动(推荐)
docker-compose up -d

# 3. 访问
# 前端: http://localhost:5174
# API 文档: http://localhost:8000/docs
```

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | FastAPI + SQLAlchemy(async) + Celery |
| 数据库 | PostgreSQL 15(pgvector) / SQLite(开发) |
| 前端 | React 18 + TypeScript + Vite + TailwindCSS |
| 采集 | Playwright + httpx + parsel + CDP |
| AI | OpenAI 兼容 LLM(评分增强/深度洞察/选房/小区测评) |

## 项目结构

```
rent_radar/
├── docker-compose.yml
├── backend/
│   ├── app/
│   │   ├── main.py              # 入口
│   │   ├── config.py            # 配置
│   │   ├── models/              # 7 个 ORM 模型
│   │   ├── routers/             # 12 个路由
│   │   │   ├── listings.py      # 房源列表/详情(+标签+中介识别)
│   │   │   ├── search.py        # 搜索
│   │   │   ├── scores.py        # 评分/洞察/中介识别
│   │   │   ├── crawl.py         # 采集控制(异步)
│   │   │   ├── cases.py         # 需求案例
│   │   │   ├── insights.py      # 小区测评/AI选房
│   │   │   ├── images.py        # 图片代理
│   │   │   └── prompts.py       # 提示词管理
│   │   ├── services/
│   │   │   ├── scoring/         # 评分引擎(规则+AI+洞察+选房+中介识别)
│   │   │   ├── matching/        # 推荐引擎(匹配度+通勤)
│   │   │   └── crawler/         # 采集引擎(xhs/douban/wb)
│   │   └── workers/             # Celery 定时任务
│   └── requirements.txt
├── frontend/                    # React SPA
│   └── src/pages/               # 15 个页面
└── infrastructure/
    └── postgres/init.sql
```

详细文档:
- [部署指南](docs/deployment.md)
- [使用手册](docs/user-guide.md)

## 来源

采集能力来自 [MediaCrawler](https://github.com/NanmiCoder/MediaCrawler)
评分/推荐/前端来自好房雷达(house_pro)

## License

NON-COMMERCIAL LEARNING LICENSE 1.1

"""需求案例路由

展示典型租房需求案例 + 系统匹配结果,让用户直观感受系统价值。
每个案例包含:需求清单、AI 推荐片区、数据库匹配房源、现实分析。
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import ok
from app.database import get_db
from app.models.listing import Listing

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])

#: 预设需求案例
CASES = [
    {
        "id": "yuexiu-4k-elevator-balcony",
        "title": "越秀地铁站附近 4K 能租到带电梯阳台的方正两房吗?",
        "subtitle": "预算 4000 内 · 农讲所/纪念堂/公园前/动物园 · 800m 内",
        "persona": "在越秀上班的年轻白领,追求通勤便利和居住品质",
        "budget": "3500-4000 元/月",
        "requirements": [
            {"label": "预算", "value": "4000 内", "icon": "💰"},
            {"label": "地铁站", "value": "农讲所、纪念堂、公园前、动物园", "icon": "🚇"},
            {"label": "距离", "value": "地铁站 800 米内", "icon": "📍"},
            {"label": "小区环境", "value": "安静小区房或大院管理", "icon": "🏘️"},
            {"label": "房间布局", "value": "方正两房一厅、厅出阳台、电梯", "icon": "🏠"},
            {"label": "采光朝向", "value": "东南、南、北、东北", "icon": "☀️"},
            {"label": "周边环境", "value": "有公园或江边", "icon": "🌳"},
        ],
        "ai_communities": [
            {
                "name": "农林上路大院/省公安厅宿舍片区",
                "reason": "农讲所与东山口之间,步行500-700m到地铁。多为80-90年代单位大院,部分加装电梯。环境极其安静,绿化好,符合大院管理和安静需求。4000以内有机会谈到老电梯房。",
                "match_tags": ["大院管理", "安静", "近地铁"],
            },
            {
                "name": "小北路/环市中路电梯公寓",
                "reason": "靠近纪念堂/越秀公园站,均在800m内。有早期商务公寓或高层电梯楼,周边有越秀公园,满足电梯+阳台+地铁+公园。",
                "match_tags": ["电梯", "近公园", "近地铁"],
            },
            {
                "name": "淘金路/建设六马路片区",
                "reason": "5号线淘金站附近,涉外公寓和老式电梯大院,社区氛围好。可能略超4000,需捡漏或接受60平左右面积。",
                "match_tags": ["电梯", "大院", "品质社区"],
            },
            {
                "name": "西华路/人民北路",
                "reason": "备选方案。加装电梯老楼,更容易4000以内找到带阳台两房。靠近西门口站,美食多,但小区环境稍逊。",
                "match_tags": ["加装电梯", "性价比", "美食"],
            },
        ],
        "reality_analysis": {
            "verdict": "有难度但不是不可能",
            "detail": "4000在越秀核心区(农讲所/纪念堂/公园前)租到原生电梯+阳台+方正两房较紧张。建议放宽到加装电梯,或看越秀边缘(动物园/小北)。步梯5楼以下也是务实选择。",
            "tips": [
                "优先找'加装电梯'的老大院,价格更低且电梯已在用",
                "公园前/农讲所是1号线核心换乘,选择最多但竞争激烈",
                "越秀公园/流花湖周边更安静,且满足'近公园'需求",
                "看房重点确认电梯是否已验收使用(不是'正在安装')",
            ],
        },
        "match_filters": {
            "price_max": 4000,
            "keywords_any": ["电梯", "阳台"],
            "metro_any": ["农讲所", "纪念堂", "公园前", "动物园", "越秀公园", "淘金"],
        },
    },
]


@router.get("")
async def list_cases():
    """列出所有需求案例"""
    return ok({"cases": [{"id": c["id"], "title": c["title"], "subtitle": c["subtitle"]} for c in CASES]})


@router.get("/{case_id}")
async def get_case(
    case_id: str,
    refresh: bool = False,
    db: AsyncSession = Depends(get_db),
):
    """获取案例详情 + 数据库匹配的房源。

    refresh=true 时:
    1. 重新从数据库匹配最新房源(而非缓存)
    2. 重新调 AI 生成推荐片区和现实分析
    3. 更新中介识别和标签
    """
    case = next((c for c in CASES if c["id"] == case_id), None)
    if not case:
        return ok({"error": "案例不存在"})

    # 从数据库匹配最新房源
    filters = case.get("match_filters", {})
    stmt = select(Listing).where(Listing.status == "active")

    if filters.get("price_max"):
        stmt = stmt.where(Listing.price <= filters["price_max"])

    rows = (await db.execute(stmt.order_by(Listing.price))).scalars().all()

    # 关键词过滤 + 标签提取
    from app.services.crawler.extractor import extract_tags
    from app.services.scoring.agent_detector import detect_agent
    from urllib.parse import quote

    keywords_any = filters.get("keywords_any", [])
    metro_any = filters.get("metro_any", [])
    matched = []
    for listing in rows:
        text = f"{listing.title or ''} {listing.content or ''}"
        kw_hits = sum(1 for kw in keywords_any if kw in text)
        metro_hits = [m for m in metro_any if m in text]
        if kw_hits > 0 or metro_hits:
            # 提取标签
            tags = extract_tags(text)
            # 中介识别
            agent = detect_agent(
                poster_name=listing.poster_name or "",
                title=listing.title or "",
                content=listing.content or "",
            )
            # 图片代理
            image_urls = []
            for u in (listing.image_urls or []):
                if u and u.startswith(("http://", "https://")):
                    from urllib.parse import quote
                    image_urls.append(f"/api/v1/images/proxy?url={quote(u, safe='')}")

            match_tags = [kw for kw in keywords_any if kw in text] + [f"🚇{m}" for m in metro_hits]
            # 补充标签信息
            if tags.get("elevator"):
                match_tags.append(tags["elevator"])
            if tags.get("has_balcony"):
                match_tags.append("阳台")
            if tags.get("floor_note"):
                match_tags.append(tags["floor_note"])
            if tags.get("is_rented"):
                match_tags.append("已租出")

            matched.append({
                "id": listing.id,
                "title": listing.title,
                "price": listing.price,
                "area_name": listing.area_name,
                "source": listing.source,
                "source_url": listing.source_url,
                "poster_name": listing.poster_name,
                "content_preview": (listing.content or "")[:120],
                "image_urls": image_urls[:3],
                "match_tags": match_tags,
                "match_score": kw_hits + len(metro_hits),
                "tags": tags,
                "is_agent": agent["is_agent"],
                "agent_level": agent["agent_level"],
            })

    matched.sort(key=lambda x: -x["match_score"])

    # refresh 时重新调 AI 生成片区推荐
    ai_communities = case.get("ai_communities", [])
    reality_analysis = case.get("reality_analysis", {})

    if refresh:
        try:
            ai_result = await _refresh_ai_analysis(case, matched)
            if ai_result.get("communities"):
                ai_communities = ai_result["communities"]
            if ai_result.get("reality_analysis"):
                reality_analysis = ai_result["reality_analysis"]
        except Exception:
            pass  # AI 失败时用默认

    return ok({
        **{k: v for k, v in case.items() if k != "match_filters"},
        "ai_communities": ai_communities,
        "reality_analysis": reality_analysis,
        "matched_listings": matched[:10],
        "total_matched": len(matched),
        "refreshed": refresh,
    })


async def _refresh_ai_analysis(case: dict, matched: list) -> dict:
    """重新调 AI 分析:基于最新匹配房源重新推荐片区和分析"""
    from app.config import settings
    import httpx

    if not settings.LLM_API_KEY:
        return {}

    # 构造 prompt
    req_summary = "\n".join(f"- {r['label']}: {r['value']}" for r in case.get("requirements", []))
    listings_summary = "\n".join(
        f"  {m['price'] or '?'}元 | {m['title'][:30]} | 标签:{','.join(m.get('match_tags', [])[:4])}"
        for m in matched[:6]
    ) or "(暂无匹配房源)"

    system = "你是广州租房市场分析专家,根据最新数据动态分析。用 JSON 输出。"
    user = f"""用户需求:
{req_summary}

数据库最新匹配的房源:
{listings_summary}

请基于最新数据重新分析(用 JSON):
{{
  "communities": [
    {{"name": "片区名", "reason": "推荐理由(结合最新房源)", "match_tags": ["标签"]}}
  ],
  "reality_analysis": {{
    "verdict": "一句话结论",
    "detail": "详细分析(结合最新数据中的价格/电梯/楼层情况)",
    "tips": ["建议1", "建议2", "建议3"]
  }}
}}

要求:基于实际匹配到的房源数据分析,如果匹配到好房源就说有戏,匹配不到就如实说难。"""

    payload = {
        "model": settings.LLM_MODEL,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0.4,
        "max_tokens": 2000,
    }
    headers = {"Authorization": f"Bearer {settings.LLM_API_KEY}", "Content-Type": "application/json"}

    import json as _json
    import re as _re
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(f"{settings.LLM_BASE_URL}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]

    # 解析 JSON
    try:
        return _json.loads(content)
    except _json.JSONDecodeError:
        m = _re.search(r"\{[\s\S]*\}", content)
        if m:
            try:
                return _json.loads(m.group(0))
            except _json.JSONDecodeError:
                pass
    return {}

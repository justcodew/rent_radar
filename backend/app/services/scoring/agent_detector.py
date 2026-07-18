"""中介识别引擎

多维度特征判断发帖人是否为中介/职业二房东:

1. 关键词命中:帖子里出现中介信号词(专业租房/多家房源/随时看房...)
2. 昵称特征:名字含"中介/房产/置业/公寓/优选好房/租房..."等
3. 发布频率:同一 poster_id 短时间内发多条(>3条疑似)
4. 内容模板化:标题结构高度雷同(emoji堆砌/格式化标题)
5. 联系方式复用:微信/手机在多条帖出现
6. 昵称含营销词:"优选/好房/直租/免中介费/房东直租..."

每条命中算一个信号分,综合判定:
- 0 个信号 → 个人房东
- 1 个信号 → 可能是个人(轻度营销)
- 2 个信号 → 疑似中介
- 3+ 个信号 → 高度疑似中介
"""
from __future__ import annotations

import re
from typing import Any

# ===== 关键词字典 =====

# 帖子内容里的中介信号(命中 >=2 个强信号)
AGENT_CONTENT_KEYWORDS = [
    "专业租房", "多家房源", "诚信中介", "免费看房", "大量房源",
    "随时看房", "全广州", "各种户型", "中介费", "房源编号",
    "联系电话同微信", "多套房源", "一手房源", "房源充足",
    "看房热线", "诚招", "长期有效", "朋友圈", "加我微信看更多",
    "更多房源", "每日更新", "找我租房", "包租", "代租",
]

# 昵称里的中介特征词
AGENT_NICKNAME_KEYWORDS = [
    "中介", "房产", "置业", "公寓", "优选", "好房", "直租", "免中介费",
    "房东直租", "租房", "管家", "物业", "经纪", "地产", "找房",
    "安居", "链家", "贝壳", "自如", "蛋壳", "相寓", "包租婆",
    "番薯",  # 小红书常见中介号后缀
]

# 模板化标题特征(emoji + 模板格式)
TEMPLATE_TITLE_PATTERNS = [
    r"🚇.*?💰",       # 地铁emoji + 价格emoji
    r"🏠.*?🔑",       # 房子 + 钥匙
    r".*?直租！.*?只要",  # "直租！...只要" 固定格式
    r".*?精装.*?拎包入住",  # 高频模板组合
]

# 昵称里的营销后缀/前缀模式
MARKETING_PATTERNS = [
    r".*\d+$",               # 昵称以数字结尾(常见营销号)
    r".*[A-Z]{2,}.*",        # 含大写英文缩写
    r".*（.*看.*）",          # 括号含"看评论区"等引导
    r".*优选.*", r".*好房.*", r".*直租.*",
]


def detect_agent(
    poster_name: str = "",
    poster_id: str = "",
    title: str = "",
    content: str = "",
    post_count: int = 0,
    contact_reuse: int = 0,
    titles_history: list[str] | None = None,
) -> dict[str, Any]:
    """多维度中介识别

    Args:
        poster_name: 发帖人昵称
        poster_id: 发帖人 ID
        title: 帖子标题
        content: 帖子正文
        post_count: 同一 poster_id 的发帖总数
        contact_reuse: 联系方式复用次数
        titles_history: 同一 poster_id 的历史标题列表

    Returns:
        {
            "is_agent": bool,           # 是否判定为中介
            "agent_level": str,         # "个人房东" / "疑似中介" / "高度疑似中介"
            "confidence": float,        # 0.0-1.0
            "signals": [str],           # 命中的信号列表
            "signal_count": int,        # 信号数
            "details": {...},           # 各维度详情
        }
    """
    signals: list[str] = []
    details: dict[str, Any] = {}

    # --- 维度1: 内容关键词 ---
    text = f"{title}\n{content}"
    content_hits = [kw for kw in AGENT_CONTENT_KEYWORDS if kw in text]
    if len(content_hits) >= 2:
        signals.append("内容含多个中介信号词")
    elif len(content_hits) == 1:
        signals.append("内容含1个中介信号词")
    details["content_keywords"] = content_hits

    # --- 维度2: 昵称特征 ---
    nick_lower = (poster_name or "").lower()
    nick_hits = [kw for kw in AGENT_NICKNAME_KEYWORDS if kw.lower() in nick_lower]
    if nick_hits:
        signals.append(f"昵称含中介特征词: {','.join(nick_hits)}")
    details["nickname_keywords"] = nick_hits

    # --- 维度3: 发布频率 ---
    if post_count >= 5:
        signals.append(f"高频发帖({post_count}条)")
    elif post_count >= 3:
        signals.append(f"较频繁发帖({post_count}条)")
    details["post_count"] = post_count

    # --- 维度4: 联系方式复用 ---
    if contact_reuse >= 3:
        signals.append(f"联系方式复用{contact_reuse}次")
    elif contact_reuse >= 1:
        signals.append(f"联系方式复用{contact_reuse}次")
    details["contact_reuse"] = contact_reuse

    # --- 维度5: 模板化标题 ---
    template_hits = []
    for pattern in TEMPLATE_TITLE_PATTERNS:
        if re.search(pattern, title or ""):
            template_hits.append(pattern)
    if template_hits:
        signals.append("标题模板化(格式固定)")
    details["template_patterns"] = template_hits

    # --- 维度6: 营销昵称模式 ---
    marketing_hits = []
    for pattern in MARKETING_PATTERNS:
        if re.match(pattern, poster_name or ""):
            marketing_hits.append(pattern)
    if marketing_hits:
        signals.append("昵称含营销模式")
    details["marketing_patterns"] = marketing_hits

    # --- 维度7: 内容多样性(标题雷同) ---
    if titles_history and len(titles_history) >= 2:
        unique_ratio = len(set(titles_history)) / len(titles_history)
        if unique_ratio < 0.3:
            signals.append(f"标题高度雷同(去重率{unique_ratio:.0%})")
        details["title_diversity"] = round(unique_ratio, 2)

    # --- 综合判定 ---
    signal_count = len(signals)
    if signal_count >= 3:
        agent_level = "高度疑似中介"
        is_agent = True
        confidence = min(0.95, 0.5 + signal_count * 0.12)
    elif signal_count == 2:
        agent_level = "疑似中介"
        is_agent = True
        confidence = 0.6 + 0.1 * (len(content_hits) + len(nick_hits))
    elif signal_count == 1:
        agent_level = "可能个人(轻度营销)"
        is_agent = False
        confidence = 0.3
    else:
        agent_level = "个人房东"
        is_agent = False
        confidence = 0.1

    return {
        "is_agent": is_agent,
        "agent_level": agent_level,
        "confidence": round(confidence, 2),
        "signals": signals,
        "signal_count": signal_count,
        "details": details,
    }

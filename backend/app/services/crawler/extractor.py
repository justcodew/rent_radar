"""房源信息提取器（正则 + 关键词字典）"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


# 价格：3000元/月 / 3000/月 / 3000 元
PRICE_PATTERNS = [
    r"(\d{3,5})\s*[元块]?\s*/\s*月",
    r"(\d{3,5})\s*[元块]/?\s*月",
    r"月租\s*[:：]?\s*(\d{3,5})",
    r"租金\s*[:：]?\s*(\d{3,5})",
    r"(?:^|\s)(\d{3,5})\s*元",
]

# 面积：15平 / 15平米 / 15 ㎡
AREA_PATTERNS = [
    r"(\d{1,3}(?:\.\d)?)\s*(?:平(?:方)?(?:米)?|㎡|sqm)",
]

# 户型：一室一厅 / 1室1厅 / 一居 / 两居
LAYOUT_PATTERNS = [
    r"([一二三四五六]?[室居])\s*([一二三四五六]?[厅])",
    r"(\d室)\s*(\d厅)",
    r"([1-4])\s*室\s*([0-4])\s*厅",
    r"([1-4])\s*居",
]

LAYOUT_NORMALIZE = {
    "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6",
}

# 区域（广州所有区）
GUANGZHOU_AREAS = [
    "天河", "海珠", "越秀", "荔湾", "白云", "黄埔",
    "番禺", "花都", "南沙", "增城", "从化",
]

# 子区域 / 商圈 → 主区域映射（广州）
GUANGZHOU_SUBAREA_MAP = {
    # 天河
    "珠江新城": "天河", "体育中心": "天河", "天河北": "天河", "岗顶": "天河",
    "石牌": "天河", "五山": "天河", "车陂": "天河", "棠下": "天河", "棠东": "天河",
    "员村": "天河", "沙河": "天河", "龙洞": "天河", "天河公园": "天河", "华师": "天河",
    "林和": "天河", "冼村": "天河", "猎德": "天河",
    # 海珠
    "客村": "海珠", "江南西": "海珠", "赤岗": "海珠", "新港西": "海珠", "琶洲": "海珠",
    "工业大道": "海珠", "滨江": "海珠", "宝岗": "海珠", "昌岗": "海珠", "中大": "海珠",
    # 越秀
    "北京路": "越秀", "东山口": "越秀", "淘金": "越秀", "五羊新城": "越秀",
    "环市东": "越秀", "烈士陵园": "越秀", "公园前": "越秀",
    # 荔湾
    "西关": "荔湾", "上下九": "荔湾", "芳村": "荔湾", "滘口": "荔湾",
    "中山八": "荔湾", "陈家祠": "荔湾",
    # 白云
    "机场路": "白云", "三元里": "白云", "同和": "白云", "京溪": "白云",
    "白云大道": "白云", "黄石": "白云", "嘉禾": "白云", "永泰": "白云",
    # 黄埔
    "科学城": "黄埔", "大沙地": "黄埔", "萝岗": "黄埔", "文冲": "黄埔",
    "鱼珠": "黄埔", "黄埔东": "黄埔",
    # 番禺
    "市桥": "番禺", "大石": "番禺", "洛溪": "番禺", "南村": "番禺",
    "钟村": "番禺", "汉溪": "番禺", "万博": "番禺", "大学城": "番禺",
    # 增城
    "新塘": "增城", "增城广场": "增城",
}

# 北京区域（保留供测试/旧数据使用）
BEIJING_AREAS = [
    "朝阳", "海淀", "东城", "西城", "丰台", "石景山",
    "通州", "大兴", "昌平", "顺义", "房山", "门头沟",
    "平谷", "怀柔", "密云", "延庆",
]

BEIJING_SUBAREA_MAP = {
    "望京": "朝阳", "国贸": "朝阳", "CBD": "朝阳", "三里屯": "朝阳", "大望路": "朝阳",
    "中关村": "海淀", "五道口": "海淀", "西二旗": "海淀", "上地": "海淀",
    "东直门": "东城", "朝阳门": "东城", "崇文门": "东城", "王府井": "东城",
    "金融街": "西城", "西直门": "西城", "宣武门": "西城",
    "回龙观": "昌平", "天通苑": "昌平",
    "黄村": "大兴", "亦庄": "大兴",
}

# 楼层：6/12层 / 中楼层 / 高楼层 / 顶层 / 底层
FLOOR_PATTERNS = [
    r"(\d{1,2})\s*/\s*(\d{1,2})\s*层",
    r"(高楼层|中楼层|低楼层|顶层|底层|一楼|二楼|三楼|四楼|五楼|六楼)",
]

# 朝向
ORIENTATION_PATTERNS = [
    r"(南向|北向|东向|西向|南北通透|东南|西南|东北|西北|朝南|朝北|朝东|朝西)",
]

# 联系方式
WECHAT_PATTERN = r"(?:微信|wechat|wx|v(?:x)?)(?:[:：\s]+)?([a-zA-Z][a-zA-Z0-9_-]{5,19})"
PHONE_PATTERN = r"(?<!\d)(1[3-9]\d{9})(?!\d)"


def extract_price(text: str) -> int | None:
    for p in PRICE_PATTERNS:
        m = re.search(p, text, re.MULTILINE)
        if m:
            try:
                val = int(m.group(1))
                if 500 <= val <= 30000:  # 合理范围
                    return val
            except (ValueError, IndexError):
                continue
    return None


def extract_area_size(text: str) -> int | None:
    for p in AREA_PATTERNS:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                val = float(m.group(1))
                if 5 <= val <= 300:
                    return int(val)
            except (ValueError, IndexError):
                continue
    return None


def extract_layout(text: str) -> str | None:
    for p in LAYOUT_PATTERNS:
        m = re.search(p, text)
        if m:
            raw = m.group(0)
            # 标准化为 "X室Y厅"
            normalized = raw
            for cn, num in LAYOUT_NORMALIZE.items():
                normalized = normalized.replace(cn, num)
            normalized = normalized.replace("居", "室")
            return normalized
    return None


def extract_area_name(text: str) -> str | None:
    # 先扫广州（当前主城市），再扫北京（兼容旧数据）
    for areas, sub_map in ((GUANGZHOU_AREAS, GUANGZHOU_SUBAREA_MAP),
                            (BEIJING_AREAS, BEIJING_SUBAREA_MAP)):
        for area in areas:
            if area + "区" in text:
                return area + "区"
        for area in areas:
            if area in text:
                return area + "区"
        for sub, main in sub_map.items():
            if sub in text:
                return main + "区"
    return None


def extract_floor(text: str) -> str | None:
    for p in FLOOR_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def extract_orientation(text: str) -> str | None:
    for p in ORIENTATION_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return None


def extract_contact(text: str) -> dict:
    contact = {}
    m = re.search(WECHAT_PATTERN, text, re.IGNORECASE)
    if m:
        contact["wechat"] = m.group(1)
    m = re.search(PHONE_PATTERN, text)
    if m:
        contact["phone"] = m.group(1)
    return contact


def extract_listing_fields(raw_text: str, title: str = "") -> dict[str, Any]:
    """从帖子原文提取结构化字段"""
    text = f"{title}\n{raw_text}"
    return {
        "price": extract_price(text),
        "size_sqm": extract_area_size(text),
        "layout": extract_layout(text),
        "area_name": extract_area_name(text),
        "floor_info": extract_floor(text),
        "orientation": extract_orientation(text),
        "contact_info": extract_contact(text),
    }


def is_probably_agent(content: str, title: str = "") -> bool:
    """简易中介识别（爬虫阶段初筛，真正评分在 rule_engine）"""
    text = f"{title}\n{content}"
    agent_signals = [
        "专业租房", "多家房源", "诚信中介", "免费看房",
        "大量房源", "随时看房", "全广州", "各种户型",
        "中介费", "房源编号", "联系电话同微信",
    ]
    hits = sum(1 for s in agent_signals if s in text)
    return hits >= 2


def extract_image_urls(html: str, base_url: str = "") -> list[str]:
    """从帖子 HTML 提取图片 URL"""
    urls = re.findall(r'<img[^>]+src=["\'](https?://[^"\']+)["\']', html)
    # 过滤掉头像、表情等小图
    filtered = [u for u in urls if "doubanio.com" in u and "large" in u]
    if not filtered:
        filtered = [u for u in urls if "doubanio.com" in u]
    if base_url and not filtered:
        # 兜底
        filtered = urls[:10]
    return list(dict.fromkeys(filtered))  # 去重保序

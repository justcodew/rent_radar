# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 房源结构化字段提取器
# 复用 house_pro(好房雷达)的 extractor.py 正则逻辑,保证两端提取结果一致。
# 从帖子 title + desc 提取:价格/面积/户型/区域/楼层/朝向/联系方式。

from __future__ import annotations

import re
from typing import Any

# ===== 正则模式(与 house_pro/extractor.py 完全一致)=====

PRICE_PATTERNS = [
    r"(\d{3,5})\s*[元块]?\s*/\s*月",
    r"(\d{3,5})\s*[元块]/?\s*月",
    r"月租\s*[:：]?\s*(\d{3,5})",
    r"租金\s*[:：]?\s*(\d{3,5})",
    r"(?:^|\s)(\d{3,5})\s*元",
]

AREA_PATTERNS = [
    r"(\d{1,3}(?:\.\d)?)\s*(?:平(?:方)?(?:米)?|㎡|sqm)",
]

LAYOUT_PATTERNS = [
    r"([一二三四五六]?[室居])\s*([一二三四五六]?[厅])",
    r"(\d室)\s*(\d厅)",
    r"([1-4])\s*室\s*([0-4])\s*厅",
    r"([1-4])\s*居",
]

LAYOUT_NORMALIZE = {
    "一": "1", "二": "2", "三": "3", "四": "4", "五": "5", "六": "6",
}

# 广州区域
GUANGZHOU_AREAS = [
    "天河", "海珠", "越秀", "荔湾", "白云", "黄埔",
    "番禺", "花都", "南沙", "增城", "从化",
]

GUANGZHOU_SUBAREA_MAP = {
    "珠江新城": "天河", "体育中心": "天河", "天河北": "天河", "岗顶": "天河",
    "石牌": "天河", "五山": "天河", "车陂": "天河", "棠下": "天河", "棠东": "天河",
    "员村": "天河", "沙河": "天河", "龙洞": "天河", "天河公园": "天河", "华师": "天河",
    "林和": "天河", "冼村": "天河", "猎德": "天河",
    "客村": "海珠", "江南西": "海珠", "赤岗": "海珠", "新港西": "海珠", "琶洲": "海珠",
    "工业大道": "海珠", "滨江": "海珠", "宝岗": "海珠", "昌岗": "海珠", "中大": "海珠",
    "北京路": "越秀", "东山口": "越秀", "淘金": "越秀", "五羊新城": "越秀",
    "环市东": "越秀", "烈士陵园": "越秀", "公园前": "越秀",
    "西关": "荔湾", "上下九": "荔湾", "芳村": "荔湾", "滘口": "荔湾",
    "中山八": "荔湾", "陈家祠": "荔湾",
    "机场路": "白云", "三元里": "白云", "同和": "白云", "京溪": "白云",
    "白云大道": "白云", "黄石": "白云", "嘉禾": "白云", "永泰": "白云",
    "科学城": "黄埔", "大沙地": "黄埔", "萝岗": "黄埔", "文冲": "黄埔",
    "鱼珠": "黄埔", "黄埔东": "黄埔",
    "市桥": "番禺", "大石": "番禺", "洛溪": "番禺", "南村": "番禺",
    "钟村": "番禺", "汉溪": "番禺", "万博": "番禺", "大学城": "番禺",
    "新塘": "增城", "增城广场": "增城",
    # 补充越秀子区域(广州租房高频)
    "农讲所": "越秀", "建设大马路": "越秀", "建设二马路": "越秀", "建设六马路": "越秀",
    "西门口": "越秀", "小北": "越秀", "纪念堂": "越秀", "动物园": "越秀",
    "越秀公园": "越秀", "北京路": "越秀",
}

FLOOR_PATTERNS = [
    r"(\d{1,2})\s*/\s*(\d{1,2})\s*层",
    r"(高楼层|中楼层|低楼层|顶层|底层|一楼|二楼|三楼|四楼|五楼|六楼)",
]

ORIENTATION_PATTERNS = [
    r"(南向|北向|东向|西向|南北通透|东南|西南|东北|西北|朝南|朝北|朝东|朝西)",
]

WECHAT_PATTERN = r"(?:微信|wechat|wx|v(?:x)?)(?:[:：\s]+)?([a-zA-Z][a-zA-Z0-9_-]{5,19})"
PHONE_PATTERN = r"(?<!\d)(1[3-9]\d{9})(?!\d)"

# 支持的 k 计价(如 3.6k = 3600,2.5k = 2500)
PRICE_K_PATTERN = r"(\d+(?:\.\d+)?)\s*[kK千](?:\+|\s|$|元)"


# ===== 提取函数 =====

def extract_price(text: str) -> int | None:
    """提取月租价格"""
    # 先匹配带 k 的
    m = re.search(PRICE_K_PATTERN, text)
    if m:
        try:
            val = int(float(m.group(1)) * 1000)
            if 500 <= val <= 30000:
                return val
        except (ValueError, IndexError):
            pass
    for p in PRICE_PATTERNS:
        m = re.search(p, text, re.MULTILINE)
        if m:
            try:
                val = int(m.group(1))
                if 500 <= val <= 30000:
                    return val
            except (ValueError, IndexError):
                continue
    return None


def extract_area_size(text: str) -> int | None:
    """提取面积(平方米)"""
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
    """提取户型(如 两房一厅 / 2室1厅 / 单间)"""
    # 先用已有 patterns
    for p in LAYOUT_PATTERNS:
        m = re.search(p, text)
        if m:
            raw = m.group(0)
            normalized = raw
            for cn, num in LAYOUT_NORMALIZE.items():
                normalized = normalized.replace(cn, num)
            normalized = normalized.replace("居", "室")
            return normalized

    # 补充中文写法:两房一厅 / 三房两厅 / 一房一厅 / 两房 / 单间
    cn_patterns = [
        (r"两房\s*(一厅|1厅)", "两房一厅"),
        (r"三房\s*(一厅|两厅|2厅)", "三房一厅"),
        (r"一房\s*(一厅|1厅)", "一房一厅"),
        (r"四房\s*(一厅|两厅)", "四房一厅"),
        (r"两房两厅", "两房两厅"),
        (r"两房一卫", "两房"),
        (r"三房一卫", "三房"),
        (r"(两房|2房)(?![一两三四一二三四厅])", "两房"),
        (r"(三房|3房)(?![一两三四厅])", "三房"),
        (r"(一房|1房)(?![一两三四厅])", "一房"),
        (r"单间", "单间"),
        (r"开间", "开间"),
        (r"一居室", "一房"),
        (r"两居室", "两房"),
        (r"三居室", "三房"),
    ]
    for pattern, display in cn_patterns:
        if re.search(pattern, text):
            return display
    return None


def extract_area_name(text: str) -> str | None:
    """提取区域(广州/北京)"""
    for areas, sub_map in ((GUANGZHOU_AREAS, GUANGZHOU_SUBAREA_MAP),):
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
    """提取楼层信息"""
    for p in FLOOR_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group(0)
    return None


def extract_orientation(text: str) -> str | None:
    """提取朝向"""
    for p in ORIENTATION_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group(1)
    return None


def extract_contact(text: str) -> dict:
    """提取联系方式(微信/手机)"""
    contact = {}
    m = re.search(WECHAT_PATTERN, text, re.IGNORECASE)
    if m:
        contact["wechat"] = m.group(1)
    m = re.search(PHONE_PATTERN, text)
    if m:
        contact["phone"] = m.group(1)
    return contact


def extract_listing_fields(raw_text: str, title: str = "") -> dict[str, Any]:
    """从帖子原文提取全部结构化字段。"""
    text = f"{title}\n{raw_text}"
    return {
        "price": extract_price(text),
        "size_sqm": extract_area_size(text),
        "layout": extract_layout(text),
        "area_name": extract_area_name(text),
        "floor_info": extract_floor(text),
        "orientation": extract_orientation(text),
        "contact_info": extract_contact(text),
        "tags": extract_tags(text),
    }


# ===== 关键标签提取 =====

# 广州地铁站(用于标签提取)
GUANGZHOU_METRO_STATIONS = [
    "公园前", "农讲所", "烈士陵园", "东山口", "杨箕", "五羊邨", "珠江新城",
    "体育西路", "体育中心", "岗顶", "石牌桥", "天河客运站", "广州东站",
    "越秀公园", "纪念堂", "西门口", "海珠广场", "北京路", "团一大广场",
    "淘金", "小北", "白云文化广场", "白云公园", "萧岗", "江夏",
    "陈家祠", "长寿路", "黄沙", "芳村", "花地湾", "滘口",
    "客村", "鹭江", "中大", "晓港", "江南西", "市二宫",
    "三元里", "飞翔公园", "白云大道北", "永泰", "同和", "京溪南方医院",
    "车陂南", "车陂", "东圃", "黄村", "珠村", "三溪",
    "琶洲", "万胜围", "官洲", "大学城北", "大学城南",
    "天河智慧城", "神舟路", "科学城", "苏元", "萝岗",
    "汉溪长隆", "市桥", "番禺广场", "大石", "厦滘", "沥滘",
    "嘉禾望岗", "白云东平", "燕塘", "天河公园", "棠东",
    "流花", "彩虹桥", "华林寺", "同福西", "一德路",
]

# 已租出关键词
RENTED_KEYWORDS = [
    "已租", "已出", "已找到", "已成交", "租出去了", "已出租",
    "已定", "定出去了", "已签约", "合同已签", "找到租客",
    "已没", "已空", "rented", "已结束", "更新：已租",
    "已议定", "租掉了", "租出去了", "不再更新",
]

# 阳台关键词
BALCONY_KEYWORDS = ["阳台", "露台", "大阳台", "南向阳台"]

# 电梯/步梯关键词
ELEVATOR_KEYWORDS = ["电梯", "有电梯", "带电梯", "电梯房", "电梯楼", "有电梯的"]
STAIRS_KEYWORDS = ["步梯", "楼梯", "楼梯房", "无电梯", "没电梯", "不带电梯", "步行梯"]

# 原生电梯关键词(区分加装电梯 vs 原生电梯)
ORIGINAL_ELEVATOR_KEYWORDS = [
    "原生电梯", "原装电梯", "电梯洋房", "电梯高层", "电梯公寓",
    "带电梯的", "电梯直搂", "电梯入户", "电梯小高层", "电梯高层",
]
ADDED_ELEVATOR_KEYWORDS = [
    "加装电梯", "电梯已安装", "电梯已加装", "加装了电梯", "电梯正在安装",
    "电梯已通", "电梯已验收", "后装电梯", "已加装",
]

# 楼层数字提取模式
FLOOR_LEVEL_PATTERNS = [
    r"步梯\s*(\d{1,2})\s*楼",
    r"(\d{1,2})\s*楼.*?步梯",
    r"(\d{1,2})\s*/\s*\d{1,2}\s*层",
    r"(\d{1,2})\s*楼",
    r"低楼层|中楼层|高楼层|顶层|底层",
    r"一楼|二楼|三楼|四楼|五楼|六楼|七楼|八楼|九楼",
]

FLOOR_CN_TO_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9}


def _extract_floor_level(text: str) -> tuple[str | None, int | None]:
    """提取楼层信息:返回 (楼层描述, 楼层数字)

    如 "步梯5楼" → ("步梯5楼", 5)
    "6/9层" → ("6/9层", 6)
    "三楼" → ("三楼", 3)
    """
    for p in FLOOR_LEVEL_PATTERNS:
        m = re.search(p, text)
        if m:
            raw = m.group(0)
            # 尝试提取数字
            num = None
            num_m = re.search(r"(\d{1,2})", raw)
            if num_m:
                num = int(num_m.group(1))
            else:
                # 中文数字
                for cn, n in FLOOR_CN_TO_NUM.items():
                    if cn in raw:
                        num = n
                        break
            return raw, num
    return None, None


def _detect_elevator_type(text: str, has_stairs: bool) -> str | None:
    """判断电梯类型:原生电梯 / 加装电梯 / 步梯"""
    # 先查加装关键词
    is_added = any(kw in text for kw in ADDED_ELEVATOR_KEYWORDS)
    if is_added:
        return "加装电梯"
    # 再查原生电梯
    is_original = any(kw in text for kw in ORIGINAL_ELEVATOR_KEYWORDS)
    has_elevator = any(kw in text for kw in ELEVATOR_KEYWORDS)

    if is_original:
        return "原生电梯"
    if has_elevator and has_stairs:
        return "加装电梯"  # 同时提到步梯+电梯,大概率加装
    if has_elevator:
        return "电梯"  # 有电梯但无法判断原生还是加装
    if has_stairs:
        return "步梯"
    return None


def extract_tags(text: str) -> dict[str, Any]:
    """提取关键标签:房型/阳台/电梯步梯(含具体楼层)/朝向/地铁站/面积/已租出"""
    tags: dict[str, Any] = {}

    # 0. 房型(放在最前面,面积后面)
    layout = extract_layout(text)
    if layout:
        # 标准化显示:1室1厅 → 一房一厅
        layout_display = layout
        num_map = {"1": "一", "2": "两", "3": "三", "4": "四"}
        room_num = layout[0] if layout[0].isdigit() else ""
        if room_num and room_num in num_map:
            # 1室1厅 → 一房一厅
            parts = layout.replace("室", "房").replace("厅", "厅")
            layout_display = num_map.get(parts[0], parts[0]) + parts[1:]
        tags["layout"] = layout_display

    # 1. 阳台
    has_balcony = any(kw in text for kw in BALCONY_KEYWORDS)
    tags["has_balcony"] = has_balcony
    if has_balcony:
        tags["balcony"] = "有阳台"

    # 2. 电梯/步梯类型 + 具体楼层(合并为一个标签,避免重合)
    has_stairs = any(kw in text for kw in STAIRS_KEYWORDS)
    elevator_type = _detect_elevator_type(text, has_stairs)

    floor_desc, floor_num = _extract_floor_level(text)

    # 合并显示:电梯类型 + 楼层 → 一个标签
    if elevator_type and floor_num:
        is_stairs = "步梯" in (elevator_type or "") or has_stairs
        if is_stairs:
            if floor_num <= 3:
                tags["floor_note"] = f"步梯{floor_num}楼，低层"
            elif floor_num <= 5:
                tags["floor_note"] = f"步梯{floor_num}楼，中层"
            elif floor_num <= 7:
                tags["floor_note"] = f"步梯{floor_num}楼，高层"
            else:
                tags["floor_note"] = f"步梯{floor_num}楼，超高层⚠️"
        else:
            tags["floor_note"] = f"{elevator_type}{floor_num}楼"
    elif elevator_type and floor_desc:
        # 有电梯类型 + 楼层描述(但没提取到数字,如"中楼层")
        tags["floor_note"] = f"{elevator_type}·{floor_desc}"
    elif elevator_type:
        tags["floor_note"] = elevator_type
    elif floor_num:
        tags["floor_note"] = f"{floor_num}楼"
    elif floor_desc:
        tags["floor_note"] = floor_desc

    # 楼层数字(单独存,供前端评级用)
    if floor_num:
        tags["floor_num"] = floor_num

    # 3. 朝向(复用已有函数)
    orientation = extract_orientation(text)
    if orientation:
        tags["orientation"] = orientation

    # 4. 地铁站
    metro_hits = [s for s in GUANGZHOU_METRO_STATIONS if s in text]
    if metro_hits:
        tags["metro_stations"] = metro_hits[:3]  # 最多3个
    # 也匹配 🚇 + 地名模式
    metro_emoji = re.findall(r"🚇\s*(\S{2,6})", text)
    for m in metro_emoji:
        clean = m.strip("🚇📍✨🍃💰🏠")
        if clean and clean not in metro_hits and len(clean) >= 2:
            tags.setdefault("metro_stations", []).append(clean)
            if len(tags.get("metro_stations", [])) > 3:
                tags["metro_stations"] = tags["metro_stations"][:3]

    # 5. 面积(复用已有函数)
    size = extract_area_size(text)
    if size:
        tags["size_sqm"] = size

    # 6. 已租出
    is_rented = any(kw in text for kw in RENTED_KEYWORDS)
    tags["is_rented"] = is_rented
    if is_rented:
        tags["rented"] = "已租出"

    return tags


def is_probably_agent(content: str, title: str = "") -> bool:
    """简易中介识别"""
    text = f"{title}\n{content}"
    agent_signals = [
        "专业租房", "多家房源", "诚信中介", "免费看房",
        "大量房源", "随时看房", "全广州", "各种户型",
        "中介费", "房源编号", "联系电话同微信",
    ]
    hits = sum(1 for s in agent_signals if s in text)
    return hits >= 2

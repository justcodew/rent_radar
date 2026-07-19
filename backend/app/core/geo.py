"""地理计算工具:直线距离 + 方位角。

供地铁找房功能使用,精度对 MVP 足够(误差 < 0.5%)。
"""
from __future__ import annotations

import math

# 地球半径(km)
_EARTH_RADIUS_KM = 6371.0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """两经纬度点之间的直线距离(km),haversine 公式。"""
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlng / 2) ** 2
    )
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def bearing_deg(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """从点 1 到点 2 的方位角(0-360,正北=0,顺时针)。

    用于在 SVG 示意图上把区点按真实方位散布在地铁站周围。
    """
    rlat1, rlat2 = math.radians(lat1), math.radians(lat2)
    dlng = math.radians(lng2 - lng1)
    x = math.sin(dlng) * math.cos(rlat2)
    y = math.cos(rlat1) * math.sin(rlat2) - math.sin(rlat1) * math.cos(rlat2) * math.cos(dlng)
    brng = math.degrees(math.atan2(x, y))
    return (brng + 360) % 360

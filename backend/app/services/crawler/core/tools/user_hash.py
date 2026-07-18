# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# rent_radar 保留原始用户信息(不做脱敏),方便用户直接联系房东/中介。
# 原始 MediaCrawler 教学版的脱敏逻辑已移除。


def anonymize_user_id(user_id) -> str:
    """保留原始用户 ID(不脱敏)"""
    if user_id is None:
        return ""
    return str(user_id).strip()


def mask_nickname(name) -> str:
    """保留原始昵称(不脱敏)"""
    if name is None:
        return ""
    return str(name)

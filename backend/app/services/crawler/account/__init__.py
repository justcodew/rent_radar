# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 多账号模块
# 用法:
#   from account import AccountPool, AccountInfo
#   from account import store, manager

from app.services.crawler.account.pool import AccountPool
from app.services.crawler.account.types import AccountInfo
from app.services.crawler.account import manager, store

__all__ = ["AccountPool", "AccountInfo", "store", "manager"]

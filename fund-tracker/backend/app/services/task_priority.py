# -*- coding: utf-8 -*-
"""
任务优先级定义 - 避免循环导入
"""
from enum import Enum


class TaskPriority(Enum):
    """任务优先级"""
    P0 = 0  # 最高 - 用户持仓基金
    P1 = 1  # 高 - 默认基金列表
    P2 = 2  # 中 - 最近访问基金
    P3 = 3  # 低 - 其他基金

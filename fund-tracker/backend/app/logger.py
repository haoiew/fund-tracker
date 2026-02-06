# -*- coding: utf-8 -*-
"""
日志配置模块
统一配置项目日志输出
"""
import logging
import sys
from pathlib import Path


def setup_logging(
    level: int = logging.INFO,
    log_file: str = None,
    format_string: str = None
) -> logging.Logger:
    """
    配置日志系统

    Args:
        level: 日志级别，默认为 INFO
        log_file: 日志文件路径，默认为 None（不写入文件）
        format_string: 自定义日志格式

    Returns:
        配置好的 logger 实例
    """
    if format_string is None:
        format_string = (
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )

    # 创建 formatter
    formatter = logging.Formatter(
        format_string,
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 配置根日志器
    logger = logging.getLogger("fund_tracker")
    logger.setLevel(level)

    # 清除已有处理器
    logger.handlers = []

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# 创建默认日志器
logger = setup_logging()


def get_logger(name: str) -> logging.Logger:
    """
    获取指定名称的日志器

    Args:
        name: 日志器名称

    Returns:
        日志器实例
    """
    return logging.getLogger(f"fund_tracker.{name}")

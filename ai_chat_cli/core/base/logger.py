# -*- coding: utf-8 -*-

"""
日志模块
提供统一的日志输出，支持日志级别标识
- 所有级别日志均写入文件（方便调试排查）
- 终端不输出日志（避免干扰 Display 的用户交互）
"""

import atexit
import os
from datetime import datetime
from enum import Enum


class LogLevel(Enum):
    """日志级别标识"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARN"
    ERROR = "ERROR"


class Logger:
    """
    日志器
    - 所有级别日志均写入文件，不做级别过滤
    - 终端留给 Display，Logger 不往终端输出
    """

    def __init__(self, show_timestamp=True, log_file="logs/app.log"):
        """
        初始化日志器

        Args:
            show_timestamp: 是否在日志中显示时间戳
            log_file: 日志文件路径，为 None 或空字符串则不写文件
        """
        self.show_timestamp = show_timestamp
        self._file = None

        if log_file:
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            self._file = open(log_file, "a", encoding="utf-8")
            atexit.register(self.close)

    def _log(self, level: LogLevel, message):
        """写入一条日志到文件"""
        timestamp = ""
        if self.show_timestamp:
            timestamp = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} "

        line = f"{timestamp}[{level.value}] {message}"

        if self._file:
            self._file.write(line + "\n")
            self._file.flush()

    def debug(self, message):
        self._log(LogLevel.DEBUG, message)

    def info(self, message):
        self._log(LogLevel.INFO, message)

    def warning(self, message):
        self._log(LogLevel.WARNING, message)

    def error(self, message):
        self._log(LogLevel.ERROR, message)

    def close(self):
        """关闭日志文件"""
        if self._file:
            self._file.close()
            self._file = None

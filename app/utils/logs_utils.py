"""
@Project ：Contract_Review_backend-Py
@File    ：logs_utils.py
@IDE     ：PyCharm 
@Author  ：潘尚国
@Date    ：2025/10/23 11:52
"""
import json
import logging
import os
from logging.handlers import TimedRotatingFileHandler

from app.config.config import settings


class LoggingModule:
    def __init__(
            self,
            logger_name: str = "app_logger",
            log_dir: str = "logs",
            log_file: str = "app.log",
            log_level: int = logging.INFO,
            backup_days: int = 30,
            encoding: str = "utf-8"
    ):
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(log_level)
        self.logger.propagate = False
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, log_file)
        self.formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(module)s:%(funcName)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        self._add_console_handler()
        self._add_timed_rotating_file_handler(backup_days, encoding)

    def _add_console_handler(self):
        """添加控制台输出处理器"""
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(self.formatter)
        self.logger.addHandler(console_handler)

    def _add_timed_rotating_file_handler(self, backup_days: int, encoding: str):
        """添加按时间轮转的文件处理器"""
        file_handler = TimedRotatingFileHandler(
            filename=self.log_file,
            when="midnight", # 每天凌晨切割
            interval=1,  # 每天凌晨切割一次
            backupCount=backup_days,  # 保留backup_days个文件
            encoding=encoding,
            delay=False,
            utc=False
        )

        file_handler.suffix = "%Y-%m-%d"
        file_handler.setFormatter(self.formatter)
        self.logger.addHandler(file_handler)

    def info(self, message: str):
        self.logger.info(message)

    def warning(self, message: str):
        self.logger.warning(message)

    def error(self, message: str, exc_info: bool = False):
        self.logger.error(message, exc_info=exc_info)

    def get_logger(self) -> logging.Logger:
        return self.logger


log_module = LoggingModule(
    logger_name=settings.logging_config.logger_name,
    log_dir=settings.logging_config.log_dir,
    log_file=settings.logging_config.log_file,
    log_level=settings.logging_config.log_level,
    backup_days=settings.logging_config.backup_days,
    encoding=settings.logging_config.encoding
)

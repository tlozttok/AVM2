import logging

import os
from typing import Dict

class LoggerFactory:
    """日志工厂类，为每个类名创建独立的日志文件"""
    _loggers: Dict[str, logging.Logger] = {}
    _handlers: Dict[str, logging.Handler] = {}
    
    @classmethod
    def get_logger(cls, class_name: str, log_dir: str = "logs") -> logging.Logger:
        """
        获取指定类名的 logger
        
        Args:
            class_name: 类名
            log_dir: 日志目录路径
            
        Returns:
            配置好的 logger 实例
        """
        if class_name in cls._loggers:
            return cls._loggers[class_name]
        
        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)
        
        # 创建 logger
        logger = logging.getLogger(class_name)
        logger.setLevel(logging.DEBUG)
        
        # 避免重复添加 handler
        if not logger.handlers:
            # 创建文件 handler
            log_file = os.path.join(log_dir, f"{class_name}.log")
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.DEBUG)
            
            # 设置统一的格式
            formatter = logging.Formatter(
                '[%(asctime)s] %(name)s.%(funcName)s(%(lineno)d)[%(levelname)s]:%(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            # 添加 handler 到 logger
            logger.addHandler(file_handler)
            logger.propagate = False  # 避免日志传播到 root logger
        
        cls._loggers[class_name] = logger
        
        logger.info("===============================")
        logger.info(f"{class_name} 日志初始化。")
        
        return logger

# 基础类，提供日志功能
class Loggable:
    """可继承的日志基类"""
    
    def __init__(self):
        # 获取类名（支持继承）
        class_name = self.__class__.__name__
        self.logger = LoggerFactory.get_logger(class_name)
        
        
basic_logger = LoggerFactory.get_logger("basic")
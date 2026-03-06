import logging
import os
import time
from enum import Enum, auto
from typing import Dict, Optional, Any
from utils.detail_logger import DetailLogger


class LogMode(Enum):
    """日志模式枚举

    CONTENT: 运行内容模式 - 保持现有日志行为，记录业务逻辑
    DETAIL:  程序细节模式 - 额外记录精确时间、对象引用、运行时结构
    ARCH:    架构还原模式 - 在DETAIL基础上监控异步框架活动
    """
    CONTENT = auto()
    DETAIL = auto()
    ARCH = auto()


class LoggerFactory:
    """日志工厂类，为每个类名创建独立的日志文件"""
    _loggers: Dict[str, 'StructuredLogger'] = {}
    _handlers: Dict[str, logging.Handler] = {}
    _global_mode: LogMode = LogMode.CONTENT
    _class_modes: Dict[str, LogMode] = {}
    _detail_logger: Optional[DetailLogger] = None

    @classmethod
    def _init_detail_logger(cls):
        """初始化结构化日志记录器（延迟初始化）"""
        if cls._detail_logger is None:
            cls._detail_logger = DetailLogger()

    @classmethod
    def set_mode(cls, mode: LogMode):
        """设置全局日志模式

        Args:
            mode: 日志模式 (LogMode.CONTENT / DETAIL / ARCH)
        """
        cls._global_mode = mode
        # 更新所有已创建的logger的模式
        for logger in cls._loggers.values():
            logger.set_mode(mode)

    @classmethod
    def set_mode_for_class(cls, class_name: str, mode: LogMode):
        """为特定类设置日志模式

        Args:
            class_name: 类名
            mode: 日志模式
        """
        cls._class_modes[class_name] = mode
        # 如果logger已存在，更新其模式
        if class_name in cls._loggers:
            cls._loggers[class_name].set_mode(mode)

    @classmethod
    def _get_mode_for_class(cls, class_name: str) -> LogMode:
        """获取指定类的日志模式"""
        # 首先检查是否有类特定的设置
        if class_name in cls._class_modes:
            return cls._class_modes[class_name]
        # 否则返回全局模式
        return cls._global_mode

    @classmethod
    def get_logger(cls, class_name: str, log_dir: str = "logs") -> 'StructuredLogger':
        """
        获取指定类名的 logger

        Args:
            class_name: 类名
            log_dir: 日志目录路径

        Returns:
            配置好的 StructuredLogger 实例
        """
        if class_name in cls._loggers:
            return cls._loggers[class_name]

        # 初始化结构化日志记录器
        cls._init_detail_logger()

        # 创建日志目录
        os.makedirs(log_dir, exist_ok=True)

        # 创建底层 logging.Logger
        raw_logger = logging.getLogger(f"avm2.{class_name}")
        raw_logger.setLevel(logging.DEBUG)

        # 避免重复添加 handler
        if not raw_logger.handlers:
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
            raw_logger.addHandler(file_handler)
            raw_logger.propagate = False  # 避免日志传播到 root logger

        # 确定该logger的模式
        mode = cls._get_mode_for_class(class_name)

        # 创建结构化logger
        logger = StructuredLogger(class_name, raw_logger, cls._detail_logger, mode)
        cls._loggers[class_name] = logger

        # 记录初始化信息
        logger.info(f"==============================={class_name} 日志初始化。")

        return logger

    @classmethod
    def get_mode(cls) -> LogMode:
        """获取当前全局日志模式"""
        return cls._global_mode


class StructuredLogger:
    """结构化日志记录器，支持三种日志模式

    该类包装了标准的 logging.Logger，并添加了 DETAIL 和 ARCH 模式的支持。
    保持与原有代码的向后兼容性。
    """

    def __init__(self, class_name: str, raw_logger: logging.Logger,
                 detail_logger: Optional[DetailLogger], mode: LogMode):
        self.class_name = class_name
        self.raw_logger = raw_logger
        self.detail_logger = detail_logger
        self._mode = mode
        self._agent_id: Optional[str] = None  # 如果设置了Agent ID

    def set_mode(self, mode: LogMode):
        """设置当前logger的模式"""
        self._mode = mode

    def get_mode(self) -> LogMode:
        """获取当前logger的模式"""
        return self._mode

    def set_agent_id(self, agent_id: str):
        """设置Agent ID（用于Agent日志）"""
        self._agent_id = agent_id

    # ========== CONTENT 模式方法（标准日志） ==========

    def debug(self, msg: str):
        """记录DEBUG级别日志（运行内容模式）"""
        prefix = f"[Agent:{self._agent_id}] " if self._agent_id else ""
        self.raw_logger.debug(f"{prefix}{msg}")

    def info(self, msg: str):
        """记录INFO级别日志（运行内容模式）"""
        prefix = f"[Agent:{self._agent_id}] " if self._agent_id else ""
        self.raw_logger.info(f"{prefix}{msg}")

    def warning(self, msg: str):
        """记录WARNING级别日志（运行内容模式）"""
        prefix = f"[Agent:{self._agent_id}] " if self._agent_id else ""
        self.raw_logger.warning(f"{prefix}{msg}")

    def error(self, msg: str):
        """记录ERROR级别日志（运行内容模式）"""
        prefix = f"[Agent:{self._agent_id}] " if self._agent_id else ""
        self.raw_logger.error(f"{prefix}{msg}")

    def exception(self, msg: str):
        """记录EXCEPTION级别日志（运行内容模式）"""
        prefix = f"[Agent:{self._agent_id}] " if self._agent_id else ""
        self.raw_logger.exception(f"{prefix}{msg}")

    def critical(self, msg: str):
        """记录CRITICAL级别日志（运行内容模式）"""
        prefix = f"[Agent:{self._agent_id}] " if self._agent_id else ""
        self.raw_logger.critical(f"{prefix}{msg}")

    # ========== DETAIL 模式方法（程序细节） ==========

    def detail(self, event_type: str, data: Dict[str, Any]):
        """记录程序细节日志

        仅在 DETAIL 或 ARCH 模式下生效。
        自动添加微秒级时间戳、对象引用等信息。

        Args:
            event_type: 事件类型，如 "message_received", "agent_created" 等
            data: 事件相关数据字典
        """
        if self._mode == LogMode.CONTENT:
            return

        if self.detail_logger:
            source = f"{self.class_name}.{self._agent_id}" if self._agent_id else self.class_name
            self.detail_logger.log_detail(source, event_type, data)

    # ========== ARCH 模式方法（架构还原） ==========

    def arch(self, event_type: str, data: Dict[str, Any]):
        """记录架构还原日志

        仅在 ARCH 模式下生效。
        在 DETAIL 基础上额外记录异步框架活动信息。

        Args:
            event_type: 事件类型
            data: 事件相关数据字典
        """
        if self._mode != LogMode.ARCH:
            return

        if self.detail_logger:
            source = f"{self.class_name}.{self._agent_id}" if self._agent_id else self.class_name
            self.detail_logger.log_arch(source, event_type, data)


class AgentLogger:
    """Agent专用的日志包装器，自动包含Agent ID

    保持与原有代码的向后兼容性，同时支持新的日志模式。
    """

    def __init__(self, agent_id, logger: StructuredLogger):
        self.agent_id = agent_id
        self.raw_logger = logger
        # 设置Agent ID以便logger使用
        logger.set_agent_id(str(agent_id))

    def _get_prefix(self) -> str:
        return f"[Agent:{self.agent_id}] "

    def debug(self, msg: str):
        self.raw_logger.debug(msg)

    def info(self, msg: str):
        self.raw_logger.info(msg)

    def warning(self, msg: str):
        self.raw_logger.warning(msg)

    def error(self, msg: str):
        self.raw_logger.error(msg)

    def exception(self, msg: str):
        self.raw_logger.exception(msg)

    def critical(self, msg: str):
        self.raw_logger.critical(msg)

    # 添加对新日志模式的支持
    def detail(self, event_type: str, data: Dict[str, Any]):
        """记录程序细节日志"""
        self.raw_logger.detail(event_type, data)

    def arch(self, event_type: str, data: Dict[str, Any]):
        """记录架构还原日志"""
        self.raw_logger.arch(event_type, data)


# 基础类，提供日志功能
class Loggable:
    """可继承的日志基类"""

    def __init__(self):
        # 获取类名（支持继承）
        class_name = self.__class__.__name__
        self.logger: StructuredLogger = LoggerFactory.get_logger(class_name)

    def set_log_name(self, name: str):
        """设置日志名称（通常用于设置Agent ID）"""
        self.logger.set_agent_id(name)


# 从环境变量读取默认日志模式
def _init_log_mode_from_env():
    """根据环境变量初始化日志模式"""
    mode_str = os.environ.get('AVM2_LOG_MODE', 'CONTENT').upper()
    mode_map = {
        'CONTENT': LogMode.CONTENT,
        'DETAIL': LogMode.DETAIL,
        'ARCH': LogMode.ARCH
    }
    if mode_str in mode_map:
        LoggerFactory.set_mode(mode_map[mode_str])
        basic_logger = LoggerFactory.get_logger("basic")
        basic_logger.info(f"日志模式设置为: {mode_str}")


# 初始化基本logger
basic_logger = LoggerFactory.get_logger("basic")

# 在模块加载时从环境变量初始化
_init_log_mode_from_env()

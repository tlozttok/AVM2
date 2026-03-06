#!/usr/bin/env python3
"""
统一日志记录器
所有日志都输出为 JSONL 格式
便于 Web 可视化监控快速解析
"""

import json
import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional
from pathlib import Path
from enum import Enum, auto


class LogMode(Enum):
    """日志模式枚举"""
    CONTENT = auto()
    DETAIL = auto()
    ARCH = auto()


class UnifiedLogger:
    """
    统一日志记录器
    所有日志都输出为 JSONL 格式到 logs/system.jsonl
    根据模式不同，输出不同详细程度的数据
    """

    _instance = None
    _fh = None
    _mode = LogMode.CONTENT

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = "logs"):
        if hasattr(self, '_initialized') and self._initialized:
            return

        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 统一日志文件
        self.log_file = self.log_dir / "system.jsonl"
        self._fh = open(self.log_file, 'a', encoding='utf-8')

        self._initialized = True

    @classmethod
    def set_mode(cls, mode: LogMode):
        cls._mode = mode

    @classmethod
    def get_mode(cls) -> LogMode:
        return cls._mode

    def _get_timestamp_us(self) -> int:
        return time.time_ns() // 1000

    def _get_object_refs(self, obj: Any = None) -> Dict[str, Any]:
        """获取对象引用信息"""
        refs = {}
        if obj:
            refs['object_addr'] = hex(id(obj))
        return refs

    def _collect_async_context(self) -> Dict[str, Any]:
        """收集异步框架上下文信息"""
        context = {
            "current_task": None,
            "all_tasks": [],
            "event_loop": None
        }

        try:
            try:
                current_task = asyncio.current_task()
                if current_task:
                    coro = current_task.get_coro()
                    context["current_task"] = {
                        "task_id": id(current_task),
                        "task_name": current_task.get_name(),
                        "coro_name": getattr(coro, '__qualname__', str(coro)),
                        "stack_depth": len(current_task.get_stack()) if hasattr(current_task, 'get_stack') else 0
                    }
            except RuntimeError:
                pass

            try:
                all_tasks = asyncio.all_tasks()
                context["all_tasks"] = [
                    {
                        "task_id": id(t),
                        "task_name": t.get_name(),
                        "coro_name": getattr(t.get_coro(), '__qualname__', str(t.get_coro()))
                    }
                    for t in all_tasks
                ]
            except RuntimeError:
                pass

            try:
                loop = asyncio.get_event_loop()
                context["event_loop"] = {
                    "loop_id": id(loop),
                    "is_running": loop.is_running(),
                    "is_closed": loop.is_closed(),
                    "default_executor": loop._default_executor is not None if hasattr(loop, '_default_executor') else None
                }
            except RuntimeError:
                pass
        except Exception as e:
            context["error"] = str(e)

        return context

    def log(self, level: str, source: str, event_type: str, data: Dict[str, Any],
            object_refs: Optional[Dict[str, Any]] = None, include_async: bool = False):
        """
        记录日志

        Args:
            level: 日志级别 (info, debug, warning, error)
            source: 日志来源
            event_type: 事件类型
            data: 事件数据
            object_refs: 对象引用信息
            include_async: 是否包含异步上下文
        """
        entry = {
            "timestamp_us": self._get_timestamp_us(),
            "level": level,
            "source": source,
            "event_type": event_type,
            "data": data,
        }

        # 根据模式添加不同详细程度的信息
        if self._mode.value >= LogMode.DETAIL.value:
            entry["object_refs"] = object_refs or {}

        if self._mode.value >= LogMode.ARCH.value or include_async:
            entry["async_context"] = self._collect_async_context()

        try:
            self._fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            self._fh.flush()
        except Exception as e:
            print(f"UnifiedLogger write error: {e}")

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None

    def __del__(self):
        self.close()


# 全局统一日志实例
unified_logger = UnifiedLogger()


class Loggable:
    """可继承的日志基类（使用统一 JSONL 格式）"""

    def __init__(self):
        class_name = self.__class__.__name__
        self._source = class_name
        self._agent_id: Optional[str] = None

    def set_log_name(self, name: str):
        """设置 Agent ID"""
        self._agent_id = name
        self._source = f"{self.__class__.__name__}.{name}"

    def _log(self, level: str, event_type: str, data: Dict[str, Any],
             object_refs: Optional[Dict[str, Any]] = None, include_async: bool = False):
        """内部日志方法"""
        source = f"{self._source}" if self._agent_id else self._source
        unified_logger.log(level, source, event_type, data, object_refs, include_async)

    def info(self, event_type: str, data: Dict[str, Any]):
        self._log("info", event_type, data)

    def debug(self, event_type: str, data: Dict[str, Any]):
        self._log("debug", event_type, data)

    def warning(self, event_type: str, data: Dict[str, Any]):
        self._log("warning", event_type, data)

    def error(self, event_type: str, data: Dict[str, Any]):
        self._log("error", event_type, data)

    def exception(self, event_type: str, data: Dict[str, Any], exc: Exception = None):
        entry = dict(data)
        if exc:
            entry["exception"] = str(exc)
        self._log("error", event_type, entry, include_async=True)

    def detail(self, event_type: str, data: Dict[str, Any], object_refs: Optional[Dict[str, Any]] = None):
        """记录程序细节日志（DETAIL 模式）"""
        self._log("detail", event_type, data, object_refs)

    def arch(self, event_type: str, data: Dict[str, Any]):
        """记录架构还原日志（ARCH 模式）"""
        self._log("arch", event_type, data, include_async=True)


# 从环境变量读取日志模式
def _init_from_env():
    mode_str = os.environ.get('AVM2_LOG_MODE', 'CONTENT').upper()
    mode_map = {
        'CONTENT': LogMode.CONTENT,
        'DETAIL': LogMode.DETAIL,
        'ARCH': LogMode.ARCH
    }
    if mode_str in mode_map:
        UnifiedLogger.set_mode(mode_map[mode_str])
        print(f"UnifiedLogger mode: {mode_str}")


_init_from_env()

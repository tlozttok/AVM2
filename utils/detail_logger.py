#!/usr/bin/env python3
"""
结构化细节日志记录器
专门处理 DETAIL 和 ARCH 级别的结构化日志输出
输出 JSONL 格式便于后续分析和可视化
"""

import json
import os
import time
import asyncio
from typing import Dict, Any, Optional
from pathlib import Path


class DetailLogger:
    """
    程序细节日志专用记录器

    处理两种级别的结构化日志：
    - DETAIL: 程序运行时细节（时间戳、对象引用、队列状态等）
    - ARCH: 架构还原（在 DETAIL 基础上添加异步框架活动信息）

    输出格式：JSON Lines (.jsonl)，每行一个JSON对象
    """

    _instance = None

    def __new__(cls, *args, **kwargs):
        """单例模式确保只有一个DetailLogger实例"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, log_dir: str = "logs"):
        if self._initialized:
            return

        self.log_dir = Path(log_dir)
        self.detail_dir = self.log_dir / "detail"
        self.arch_dir = self.log_dir / "arch"

        # 创建目录
        self.detail_dir.mkdir(parents=True, exist_ok=True)
        self.arch_dir.mkdir(parents=True, exist_ok=True)

        # 日志文件路径
        self.detail_file = self.detail_dir / "system.detail.jsonl"
        self.arch_file = self.arch_dir / "system.arch.jsonl"

        # 缓存文件句柄
        self._detail_fh = None
        self._arch_fh = None

        self._initialized = True

    def _get_detail_fh(self):
        """获取 detail 日志文件句柄（延迟打开）"""
        if self._detail_fh is None:
            self._detail_fh = open(self.detail_file, 'a', encoding='utf-8')
        return self._detail_fh

    def _get_arch_fh(self):
        """获取 arch 日志文件句柄（延迟打开）"""
        if self._arch_fh is None:
            self._arch_fh = open(self.arch_file, 'a', encoding='utf-8')
        return self._arch_fh

    def _get_timestamp_us(self) -> int:
        """获取微秒级时间戳"""
        return time.time_ns() // 1000

    def _collect_async_context(self) -> Dict[str, Any]:
        """
        收集异步框架上下文信息

        包括：
        - 当前 Task 信息
        - 所有活跃 Task 列表
        - 事件循环状态
        """
        context = {
            "current_task": None,
            "all_tasks": [],
            "event_loop": None
        }

        try:
            # 获取当前任务
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
                # 当前没有正在运行的任务
                pass

            # 获取所有任务
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

            # 获取事件循环信息
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

    def log_detail(self, source: str, event_type: str, data: Dict[str, Any],
                   object_refs: Optional[Dict[str, Any]] = None):
        """
        记录程序细节日志

        Args:
            source: 日志来源（如 "Agent.550e8400"）
            event_type: 事件类型（如 "message_received", "loop_iteration"）
            data: 事件相关数据
            object_refs: 对象引用信息（内存地址、连接关系等）

        输出格式示例：
        {
            "timestamp_us": 1709701234567890,
            "source": "Agent.550e8400",
            "event_type": "message_received",
            "data": {...},
            "object_refs": {...}
        }
        """
        entry = {
            "timestamp_us": self._get_timestamp_us(),
            "source": source,
            "event_type": event_type,
            "data": data,
            "object_refs": object_refs or {}
        }

        try:
            fh = self._get_detail_fh()
            fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            fh.flush()
        except Exception:
            # 日志失败不应该影响主程序
            pass

    def log_arch(self, source: str, event_type: str, data: Dict[str, Any],
                 object_refs: Optional[Dict[str, Any]] = None):
        """
        记录架构还原日志

        在 DETAIL 基础上添加异步框架上下文信息

        Args:
            source: 日志来源
            event_type: 事件类型
            data: 事件相关数据
            object_refs: 对象引用信息

        输出格式示例：
        {
            "timestamp_us": 1709701234567890,
            "source": "Agent.550e8400",
            "event_type": "processing_loop_iteration",
            "data": {...},
            "object_refs": {...},
            "async_context": {
                "current_task": {...},
                "all_tasks": [...],
                "event_loop": {...}
            }
        }
        """
        entry = {
            "timestamp_us": self._get_timestamp_us(),
            "source": source,
            "event_type": event_type,
            "data": data,
            "object_refs": object_refs or {},
            "async_context": self._collect_async_context()
        }

        try:
            fh = self._get_arch_fh()
            fh.write(json.dumps(entry, ensure_ascii=False, default=str) + "\n")
            fh.flush()
        except Exception:
            pass

    def close(self):
        """关闭日志文件句柄"""
        if self._detail_fh:
            self._detail_fh.close()
            self._detail_fh = None
        if self._arch_fh:
            self._arch_fh.close()
            self._arch_fh = None

    def __del__(self):
        """析构时确保文件句柄关闭"""
        self.close()


# 全局 DetailLogger 实例
detail_logger = DetailLogger()

"""
异步框架活动监控模块
用于捕获 Python asyncio 框架的运行时信息
支持架构还原模式(ARCH)的日志记录需求
"""

import asyncio
import time
import inspect
from typing import Dict, List, Optional, Any


class AsyncMonitor:
    """
    异步框架活动监控器
    捕获 Task、事件循环、协程等异步运行时信息
    """

    @staticmethod
    def get_current_task_info() -> Optional[Dict[str, Any]]:
        """
        获取当前 Task 的详细信息

        Returns:
            dict: 包含 task_id, task_name, coro_name, stack_depth 等
            None: 如果没有当前任务（在主线程调用时）
        """
        try:
            task = asyncio.current_task()
            if task is None:
                return None

            coro = task.get_coro()
            coro_name = coro.__qualname__ if coro else "unknown"

            # 获取栈深度（小心处理，避免阻塞）
            try:
                stack = task.get_stack()
                stack_depth = len(stack)
                # 获取顶层帧的函数名
                top_frame_func = stack[0].f_code.co_name if stack else None
            except Exception:
                stack_depth = 0
                top_frame_func = None

            return {
                "task_id": id(task),
                "task_name": task.get_name(),
                "coro_name": coro_name,
                "coro_addr": hex(id(coro)) if coro else None,
                "stack_depth": stack_depth,
                "top_frame_func": top_frame_func,
                "done": task.done(),
                "cancelled": task.cancelled() if task.done() else False
            }
        except RuntimeError:
            # 不在事件循环中
            return None

    @staticmethod
    def get_all_tasks_info() -> List[Dict[str, Any]]:
        """
        获取所有活跃 Task 的信息列表

        Returns:
            list: 所有任务的简要信息列表
        """
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                return []

            tasks = asyncio.all_tasks(loop)
            result = []
            for task in tasks:
                coro = task.get_coro()
                result.append({
                    "task_id": id(task),
                    "task_name": task.get_name(),
                    "coro_name": coro.__qualname__ if coro else "unknown",
                    "done": task.done(),
                    "cancelled": task.cancelled() if task.done() else False
                })
            return result
        except RuntimeError:
            return []

    @staticmethod
    def get_event_loop_info() -> Optional[Dict[str, Any]]:
        """
        获取当前事件循环的状态信息

        Returns:
            dict: 事件循环状态
            None: 如果没有事件循环
        """
        try:
            loop = asyncio.get_event_loop()

            # 获取队列中的回调数量（近似值）
            ready_callbacks = len(loop._ready) if hasattr(loop, '_ready') else 0

            # 获取计划中的定时器句柄数量
            scheduled = len(loop._scheduled) if hasattr(loop, '_scheduled') else 0

            return {
                "loop_id": id(loop),
                "loop_addr": hex(id(loop)),
                "running": loop.is_running(),
                "closed": loop.is_closed(),
                "debug": loop.get_debug(),
                "default_executor": loop._default_executor is not None,
                "ready_callbacks": ready_callbacks,
                "scheduled_timers": scheduled,
                "thread_id": getattr(loop, '_thread_id', None)
            }
        except RuntimeError:
            return None

    @staticmethod
    def get_queue_info(queue: asyncio.Queue) -> Dict[str, Any]:
        """
        获取 asyncio.Queue 的状态信息

        Args:
            queue: 要监控的队列

        Returns:
            dict: 队列状态信息
        """
        return {
            "queue_id": id(queue),
            "queue_addr": hex(id(queue)),
            "size": queue.qsize(),
            "maxsize": queue.maxsize,
            "full": queue.full(),
            "empty": queue.empty(),
            "capacity_used": queue.qsize() / queue.maxsize if queue.maxsize > 0 else 0
        }

    @staticmethod
    def capture_full_context() -> Dict[str, Any]:
        """
        捕获完整的异步上下文信息
        用于 ARCH 模式日志记录

        Returns:
            dict: 包含所有异步运行时信息的字典
        """
        return {
            "timestamp_us": time.time_ns() // 1000,
            "current_task": AsyncMonitor.get_current_task_info(),
            "all_tasks": AsyncMonitor.get_all_tasks_info(),
            "event_loop": AsyncMonitor.get_event_loop_info()
        }

    @staticmethod
    def get_caller_info(skip: int = 2) -> Dict[str, Any]:
        """
        获取调用者的信息

        Args:
            skip: 跳过多少层栈帧（默认2：跳过本函数和直接调用者）

        Returns:
            dict: 调用者信息
        """
        try:
            frame = inspect.currentframe()
            for _ in range(skip):
                if frame is None:
                    break
                frame = frame.f_back

            if frame is None:
                return {"error": "frame not available"}

            code = frame.f_code
            return {
                "filename": code.co_filename,
                "function": code.co_name,
                "lineno": frame.f_lineno,
                "module": code.co_filename.split('/')[-1].replace('.py', '')
            }
        except Exception as e:
            return {"error": str(e)}


class TaskContext:
    """
    任务上下文管理器
    用于在代码块中捕获异步上下文
    """

    def __init__(self, name: str = None):
        self.name = name or "unnamed"
        self.start_time = None
        self.start_context = None

    def __enter__(self):
        self.start_time = time.time_ns() // 1000
        self.start_context = AsyncMonitor.capture_full_context()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        end_time = time.time_ns() // 1000
        self.duration_us = end_time - self.start_time
        self.exc_type = exc_type.__name__ if exc_type else None
        return False  # 不抑制异常

    def get_summary(self) -> Dict[str, Any]:
        """获取任务执行摘要"""
        return {
            "name": self.name,
            "start_time_us": self.start_time,
            "duration_us": getattr(self, 'duration_us', None),
            "exception": getattr(self, 'exc_type', None),
            "start_context": self.start_context
        }


def monitor_task(coro_func):
    """
    装饰器：监控协程函数的执行
    用于 ARCH 模式记录协程生命周期
    """
    async def wrapper(*args, **kwargs):
        task = asyncio.current_task()
        task_name = task.get_name() if task else "unknown"

        # 记录开始
        start_context = AsyncMonitor.capture_full_context()
        start_time = time.time_ns() // 1000

        try:
            result = await coro_func(*args, **kwargs)
            return result
        finally:
            # 记录结束
            end_time = time.time_ns() // 1000
            duration_us = end_time - start_time

    return wrapper

#!/usr/bin/env python3
"""
AVM2 输入输出 Agent 模块
包含 InputAgent 和 OutputAgent 抽象基类
使用统一日志记录器 (unified_logger) 输出 JSONL 格式
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from typing import List

from utils.visual_monitor.unified_logger import Loggable
from utils.llm_logger import llm_logger


class InputOutputAgent(Loggable):
    """I/O Agent 基类 - 不可直接实例化"""

    def __init__(self):
        super().__init__()
        self.id: str = str(uuid.uuid4())
        self.message_bus = None
        self.system = None
        self._running = False

        self.set_log_name(str(self.id))


class OutputAgent(InputOutputAgent, ABC):
    """
    输出 Agent 抽象基类

    用于将 Agent 系统的消息输出到外部世界
    必须实现 explore() 和 execute_data() 方法
    """

    def __init__(self):
        super().__init__()
        self.input_connections: List[str] = []
        self.input_queue = asyncio.Queue()
        self._processing_task = None
        self._processing_interval = 0.1

        self.info("output_agent_created", {
            "agent_id": self.id,
            "agent_type": "OutputAgent"
        })

    @abstractmethod
    def explore(self, message: str):
        """探索消息内容"""
        pass

    @abstractmethod
    async def execute_data(self, data: str):
        """执行数据输出"""
        pass

    def receive_message(self, message: str, sender: str):
        """接收消息"""
        if sender in self.input_connections:
            llm_logger.log_output_agent_message(
                agent_id=self.id,
                message=message,
                sender_id=sender
            )

            queue_size_before = self.input_queue.qsize()
            self.input_queue.put_nowait((sender, message))
            queue_size_after = self.input_queue.qsize()

            self.info("message_received", {
                "sender": sender,
                "message_length": len(message),
                "queue_size_before": queue_size_before,
                "queue_size_after": queue_size_after
            })
        else:
            self.warning("message_from_unknown_sender", {
                "sender": sender
            })

    async def start_processing(self):
        """开始处理循环"""
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        self.info("processing_started", {})

    async def stop_processing(self):
        """停止处理循环"""
        if not self._running:
            return

        self._running = False

        try:
            self.input_queue.put_nowait(("__STOP__", ""))
        except:
            pass

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        self.info("processing_stopped", {})

    async def _processing_loop(self):
        """主处理循环"""
        loop_count = 0

        while self._running:
            loop_count += 1

            try:
                try:
                    message = await asyncio.wait_for(
                        self.input_queue.get(),
                        timeout=self._processing_interval
                    )

                    if message[0] == "__STOP__":
                        break

                    messages = [message]
                    while not self.input_queue.empty():
                        try:
                            additional = self.input_queue.get_nowait()
                            if additional[0] == "__STOP__":
                                break
                            messages.append(additional)
                        except asyncio.QueueEmpty:
                            break

                    await self._process_messages_batch(messages)

                except asyncio.TimeoutError:
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error("processing_loop_error", {"error": str(e)})
                await asyncio.sleep(1)

        self.info("processing_loop_ended", {"total_iterations": loop_count})

    async def _process_messages_batch(self, messages):
        """处理一批消息"""
        for sender, message in messages:
            self.explore(message)
            await self.execute_data(message)


class InputAgent(InputOutputAgent, ABC):
    """
    输入 Agent 抽象基类

    用于从外部世界收集数据并输入到 Agent 系统
    必须实现 has_data_to_send() 和 collect_data() 方法
    """

    def __init__(self):
        super().__init__()
        self.output_connections: List[str] = []
        self._task = None

        self.info("input_agent_created", {
            "agent_id": self.id,
            "agent_type": "InputAgent"
        })

    @abstractmethod
    def seek_signal(self, message: str):
        """发送搜索信号"""
        pass

    async def start_processing(self):
        """启动输入 Agent 处理循环"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self.info("input_agent_started", {})

    async def stop_processing(self):
        """停止输入 Agent"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.info("input_agent_stopped", {})

    async def _run_loop(self):
        """主运行循环"""
        loop_count = 0

        while self._running:
            loop_count += 1

            try:
                if self.should_send_data():
                    await self.send_collected_data()

                interval = self.get_check_interval()
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error("run_loop_error", {"error": str(e)})
                await asyncio.sleep(1)

        self.info("run_loop_ended", {"total_iterations": loop_count})

    def should_send_data(self) -> bool:
        """检查是否应该发送数据"""
        return self.has_data_to_send()

    @abstractmethod
    def has_data_to_send(self) -> bool:
        """检查是否有数据要发送"""
        pass

    def get_check_interval(self) -> float:
        """获取检查间隔（秒）"""
        return 0.1

    async def send_collected_data(self):
        """发送收集的数据"""
        data = self.collect_data()
        self.seek_signal(data)

        if not self.output_connections:
            self.warning("no_output_connections", {})
            return

        llm_logger.log_input_agent_message(
            agent_id=self.id,
            message=data,
            receiver_ids=self.output_connections
        )

        for receiver_id in self.output_connections:
            await self.message_bus.send_message(data, receiver_id, self.id)

        self.info("data_sent", {
            "data_length": len(data),
            "receivers_count": len(self.output_connections)
        })

    @abstractmethod
    def collect_data(self) -> str:
        """收集数据"""
        pass

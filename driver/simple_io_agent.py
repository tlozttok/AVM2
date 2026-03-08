#!/usr/bin/env python3
"""
简单的输入输出代理实现
- UserInputAgent: 接受用户输入的 InputAgent
- ConsoleOutputAgent: 将信息输出到控制台的 OutputAgent
"""

import asyncio
import uuid
from typing import List
from abc import ABC, abstractmethod
from .i_o_agent import InputAgent, OutputAgent


class UserInputAgent(InputAgent):
    """
    用户输入代理
    从控制台接受用户输入并发送给连接的代理
    """

    def __init__(self, prompt: str = "请输入消息: "):
        super().__init__()
        self.prompt = prompt
        self._input_queue = asyncio.Queue()
        self._reader_task = None

        self.info("agent_initialized", {
            "agent_type": "UserInputAgent",
            "prompt": self.prompt
        })
        
    def seek_signal(self, message: str):
        """根据message决定是否进行seek - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    def has_data_to_send(self) -> bool:
        """检查是否有用户输入需要发送"""
        has_data = not self._input_queue.empty()
        if has_data:
            self.debug("data_available", {"queue_empty": False})
        return has_data
        
    def collect_data(self) -> str:
        """从输入队列中获取数据"""
        if not self._input_queue.empty():
            data = self._input_queue.get_nowait()
            self.debug("data_collected", {"data_length": len(data)})
            return data
        self.warning("empty_queue_access", {"message": "尝试从空队列中获取数据"})
        return ""
        
    async def start(self):
        """启动输入监听和运行循环"""
        self.info("agent_starting", {"agent_type": "UserInputAgent"})
        # 启动输入监听
        self._reader_task = asyncio.create_task(self._read_user_input())
        self.debug("input_listener_created", {})
        # 启动父类的运行循环
        await super().start()
        self.info("agent_started", {"agent_type": "UserInputAgent"})
        
    async def stop(self):
        """停止输入监听和运行循环"""
        self.info("agent_stopping", {"agent_type": "UserInputAgent"})
        if self._reader_task:
            self.debug("cancelling_input_listener", {})
            self._reader_task.cancel()
            try:
                await self._reader_task
                self.debug("input_listener_stopped", {})
            except asyncio.CancelledError:
                self.debug("input_listener_cancelled", {})
                pass
        await super().stop()
        self.info("agent_stopped", {"agent_type": "UserInputAgent"})
        
    async def _read_user_input(self):
        """异步读取用户输入"""
        self.debug("input_reader_started", {})
        loop = asyncio.get_event_loop()
        input_count = 0
        while True:
            try:
                # 使用异步方式读取用户输入
                user_input = await loop.run_in_executor(None, input, self.prompt)
                if user_input.strip():
                    input_count += 1
                    await self._input_queue.put(user_input.strip())
                    self.info("user_input_received", {
                        "input_number": input_count,
                        "input": user_input
                    })
                    print(f"[UserInputAgent] 已接收输入: {user_input}")
                else:
                    self.debug("empty_input_ignored", {})
            except (EOFError, KeyboardInterrupt):
                self.info("input_reader_ended", {"reason": "EOF或中断"})
                break
            except Exception as e:
                self.error("input_reader_error", {"error": str(e)})
                print(f"[UserInputAgent] 输入读取错误: {e}")
                await asyncio.sleep(0.1)

        self.info("input_reader_finished", {"total_inputs": input_count})
                
    def get_check_interval(self) -> float:
        """获取检查间隔 - 用户输入需要快速响应"""
        return 0.05  # 50毫秒


class ConsoleOutputAgent(OutputAgent):
    """
    控制台输出代理
    将接收到的消息输出到控制台
    """

    def __init__(self, prefix: str = "[输出]"):
        super().__init__()
        self.prefix = prefix
        self.message_count = 0

        self.info("agent_initialized", {
            "agent_type": "ConsoleOutputAgent",
            "prefix": self.prefix
        })
        
    def explore(self, message: str):
        """根据message决定是否探索 - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    async def execute_data(self, data: str):
        """执行数据输出到控制台"""
        self.message_count += 1
        self.info("message_output", {
            "message_number": self.message_count,
            "data_length": len(data),
            "data_preview": data[:100]
        })
        print(f"{self.prefix} ({self.message_count}) {data}")
        self.debug("message_printed", {})
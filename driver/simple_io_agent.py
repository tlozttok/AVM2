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
from .driver import InputAgent, OutputAgent


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
        
    def seek_signal(self, message: str):
        """根据message决定是否进行seek - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    def has_data_to_send(self) -> bool:
        """检查是否有用户输入需要发送"""
        return not self._input_queue.empty()
        
    def collect_data(self) -> str:
        """从输入队列中获取数据"""
        if not self._input_queue.empty():
            return self._input_queue.get_nowait()
        return ""
        
    async def start(self):
        """启动输入监听和运行循环"""
        # 启动输入监听
        self._reader_task = asyncio.create_task(self._read_user_input())
        # 启动父类的运行循环
        await super().start()
        
    async def stop(self):
        """停止输入监听和运行循环"""
        if self._reader_task:
            self._reader_task.cancel()
            try:
                await self._reader_task
            except asyncio.CancelledError:
                pass
        await super().stop()
        
    async def _read_user_input(self):
        """异步读取用户输入"""
        loop = asyncio.get_event_loop()
        while True:
            try:
                # 使用异步方式读取用户输入
                user_input = await loop.run_in_executor(None, input, self.prompt)
                if user_input.strip():
                    await self._input_queue.put(user_input.strip())
                    print(f"[UserInputAgent] 已接收输入: {user_input}")
            except (EOFError, KeyboardInterrupt):
                break
            except Exception as e:
                print(f"[UserInputAgent] 输入读取错误: {e}")
                await asyncio.sleep(0.1)
                
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
        
    def explore(self, message: str):
        """根据message决定是否探索 - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    async def execute_data(self, data: str):
        """执行数据输出到控制台"""
        self.message_count += 1
        print(f"{self.prefix} ({self.message_count}) {data}")
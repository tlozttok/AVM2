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
        
        self.logger.info(f"UserInputAgent实例已创建，提示符: '{self.prompt}'")
        
    def seek_signal(self, message: str):
        """根据message决定是否进行seek - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    def has_data_to_send(self) -> bool:
        """检查是否有用户输入需要发送"""
        has_data = not self._input_queue.empty()
        if has_data:
            self.logger.debug("检测到用户输入队列中有数据需要发送")
        return has_data
        
    def collect_data(self) -> str:
        """从输入队列中获取数据"""
        if not self._input_queue.empty():
            data = self._input_queue.get_nowait()
            self.logger.debug(f"从输入队列获取数据，长度: {len(data)} 字符")
            return data
        self.logger.warning("尝试从空队列中获取数据")
        return ""
        
    async def start(self):
        """启动输入监听和运行循环"""
        self.logger.info("启动UserInputAgent")
        # 启动输入监听
        self._reader_task = asyncio.create_task(self._read_user_input())
        self.logger.debug("用户输入监听任务已创建")
        # 启动父类的运行循环
        await super().start()
        self.logger.info("UserInputAgent已完全启动")
        
    async def stop(self):
        """停止输入监听和运行循环"""
        self.logger.info("停止UserInputAgent")
        if self._reader_task:
            self.logger.debug("取消用户输入监听任务")
            self._reader_task.cancel()
            try:
                await self._reader_task
                self.logger.debug("用户输入监听任务已停止")
            except asyncio.CancelledError:
                self.logger.debug("用户输入监听任务被取消")
                pass
        await super().stop()
        self.logger.info("UserInputAgent已完全停止")
        
    async def _read_user_input(self):
        """异步读取用户输入"""
        self.logger.debug("开始读取用户输入")
        loop = asyncio.get_event_loop()
        input_count = 0
        while True:
            try:
                # 使用异步方式读取用户输入
                user_input = await loop.run_in_executor(None, input, self.prompt)
                if user_input.strip():
                    input_count += 1
                    await self._input_queue.put(user_input.strip())
                    self.logger.info(f"接收到用户输入 #{input_count}: '{user_input}'")
                    print(f"[UserInputAgent] 已接收输入: {user_input}")
                else:
                    self.logger.debug("接收到空输入，忽略")
            except (EOFError, KeyboardInterrupt):
                self.logger.info("用户输入读取结束 (EOF或中断)")
                break
            except Exception as e:
                self.logger.error(f"用户输入读取错误: {e}")
                self.logger.exception("输入读取异常详情:")
                print(f"[UserInputAgent] 输入读取错误: {e}")
                await asyncio.sleep(0.1)
        
        self.logger.info(f"用户输入读取结束，共接收 {input_count} 条输入")
                
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
        
        self.logger.info(f"ConsoleOutputAgent实例已创建，前缀: '{self.prefix}'")
        
    def explore(self, message: str):
        """根据message决定是否探索 - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    async def execute_data(self, data: str):
        """执行数据输出到控制台"""
        self.message_count += 1
        self.logger.info(f"输出消息 #{self.message_count}，长度: {len(data)} 字符")
        self.logger.debug(f"输出消息内容: {data[:100]}...")
        print(f"{self.prefix} ({self.message_count}) {data}")
        self.logger.debug("消息已输出到控制台")
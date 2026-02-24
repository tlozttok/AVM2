#!/usr/bin/env python3
"""
终端 Agent 适配器模块
将 TerminalManager 包装为 InputAgent 和 OutputAgent 子类，用于接入 Agent 网络
"""

import asyncio
from typing import List, Optional
from driver.driver import InputAgent, OutputAgent


class TerminalInputAgent(InputAgent):
    """
    终端输入 Agent
    将终端渲染输出作为数据源，发送给连接的 Agent
    """

    def __init__(self, terminal_manager):
        super().__init__()
        self.terminal = terminal_manager
        self._last_render: str = ""
        self._render_dirty: bool = False

        # 设置终端的渲染回调，当渲染更新时标记 dirty
        self.terminal.set_render_callback(self._on_render_update)

    def _on_render_update(self, render_text: str):
        """终端渲染更新回调"""
        self._last_render = render_text
        self._render_dirty = True

    def seek_signal(self, message: str):
        """根据 message 决定是否进行 seek - 终端被动输出，不主动 seek"""
        pass

    def has_data_to_send(self) -> bool:
        """检查是否有新的渲染数据需要发送"""
        return self._render_dirty and bool(self._last_render)

    def collect_data(self) -> str:
        """收集渲染数据并重置 dirty 标志"""
        if self._render_dirty:
            self._render_dirty = False
            return self._last_render
        return ""

    def get_check_interval(self) -> float:
        """获取检查间隔 - 与终端帧率同步"""
        return 1.0 / self.terminal.fps


class TerminalOutputAgent(OutputAgent):
    """
    终端输出 Agent
    接收来自其他 Agent 的命令并输入到终端
    """

    def __init__(self, terminal_manager):
        super().__init__()
        self.terminal = terminal_manager
        self._input_queue: asyncio.Queue = asyncio.Queue()

    def explore(self, message: str):
        """根据 message 决定是否探索 - 终端不主动探索"""
        pass

    async def execute_data(self, data: str):
        """
        执行接收到的数据
        data 包含来自其他 Agent 的输入字符和控制命令
        """
        await self.terminal.feed_input(data)

    async def send_message(self, message: str):
        """
        便捷方法：直接发送命令到终端
        等效于 execute_data，但由外部直接调用
        """
        await self.terminal.feed_input(message)


class TerminalPair:
    """
    终端 Agent 对
    封装 TerminalManager 和对应的 Input/Output Agent，提供便捷的访问接口
    """

    def __init__(self, fps: int = 10, default_rows: int = 20, default_cols: int = 80):
        from AVBash.terminal import TerminalManager

        self.terminal = TerminalManager(fps, default_rows, default_cols)
        self.input_agent: Optional[TerminalInputAgent] = None
        self.output_agent: Optional[TerminalOutputAgent] = None

    def create_agents(self) -> tuple:
        """创建并返回 InputAgent 和 OutputAgent"""
        self.input_agent = TerminalInputAgent(self.terminal)
        self.output_agent = TerminalOutputAgent(self.terminal)
        return self.input_agent, self.output_agent

    async def start(self):
        """启动终端管理器"""
        await self.terminal.start()

    async def stop(self):
        """停止终端管理器"""
        await self.terminal.stop()

    async def send_command(self, command: str):
        """便捷方法：直接发送命令到终端"""
        await self.terminal.feed_input(command)

    def set_render_callback(self, callback):
        """设置额外的渲染回调（除了 InputAgent 之外）"""
        self.terminal.set_render_callback(callback)

    def set_message_callback(self, callback):
        """设置消息回调（用于 info/error 消息）"""
        self.terminal.set_message_callback(callback)


# ==================== 使用示例 ====================

async def main():
    """示例：如何将终端接入 Agent 网络"""
    from driver.driver import AgentSystem

    # 创建终端对
    terminal_pair = TerminalPair(fps=10)

    # 创建 Agent 系统
    system = AgentSystem()

    # 创建终端 Agent
    input_agent, output_agent = terminal_pair.create_agents()

    # 添加到系统
    system.add_agent(input_agent)
    system.add_agent(output_agent)

    # 启动终端
    await terminal_pair.start()

    try:
        # 现在可以通过发送消息到 output_agent 来控制终端
        # 例如：output_agent.receive_message("/list", some_agent_id)

        # 模拟运行
        await asyncio.sleep(5)

    finally:
        await terminal_pair.stop()


if __name__ == "__main__":
    asyncio.run(main())

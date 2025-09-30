"""
异步Agent系统管理器
"""

import asyncio
from typing import Dict
from .driver import Agent, MessageBus


class AgentSystem:
    """异步Agent系统管理器"""
    
    def __init__(self):
        self.message_bus = MessageBus()
        self.agents: Dict[str, Agent] = {}
    
    def register_agent(self, agent: Agent):
        """注册Agent到系统"""
        self.agents[agent.id] = agent
        agent.message_bus = self.message_bus
        self.message_bus.register_agent(agent)
    
    async def start(self):
        """启动整个系统"""
        await self.message_bus.start()
        print(f"Agent系统已启动，包含 {len(self.agents)} 个Agent")
    
    async def stop(self):
        """停止系统"""
        await self.message_bus.stop()
        print("Agent系统已停止")
    
    async def send_initial_message(self, sender_id: str, content: str, receiver_id: str):
        """发送初始消息启动系统"""
        from .driver import AgentMessage
        message = AgentMessage(
            sender_keyword="init",
            content=content,
            receiver_keyword=None
        )
        await self.message_bus.send_message(sender_id, message, receiver_id)
        print(f"发送初始消息: {sender_id} -> {receiver_id}")


async def demo_system():
    """演示异步系统运行"""
    system = AgentSystem()
    
    # 创建示例Agent
    agent1 = Agent("agent1", "你是一个问题分析Agent，负责分析用户问题")
    agent2 = Agent("agent2", "你是一个回答生成Agent，负责生成回答")
    
    # 设置连接关系
    agent1.output_connections.connections = {
        "analysis": ["agent2"]
    }
    agent2.input_connections.connections = {
        "agent1": "analysis"
    }
    agent2.input_message_keyword = ["analysis"]
    
    # 注册Agent
    system.register_agent(agent1)
    system.register_agent(agent2)
    
    # 启动系统
    await system.start()
    
    # 发送初始消息
    await system.send_initial_message("user", "请分析一下Python的异步编程", "agent1")
    
    # 等待一段时间让系统运行
    await asyncio.sleep(10)
    
    # 停止系统
    await system.stop()


if __name__ == "__main__":
    asyncio.run(demo_system())
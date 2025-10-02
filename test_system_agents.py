#!/usr/bin/env python3
"""
测试系统接口Agent
"""

import asyncio
import os
from driver.async_system import AgentSystem
from system_interface_agents.system_agent_examples import AgentCreatorOutputAgent, SystemMonitorInputAgent
from driver.driver import AgentMessage

async def test_system_agents():
    """测试系统接口Agent功能"""
    
    # 创建系统
    system = AgentSystem()
    
    # 创建系统接口Agent
    agent_creator = AgentCreatorOutputAgent("agent_creator", system, system.message_bus)
    system_monitor = SystemMonitorInputAgent("system_monitor", system, 3.0, system.message_bus)  # 每3秒报告一次
    
    # 注册系统Agent
    system.register_agent(agent_creator)
    system.register_agent(system_monitor)
    
    # 启动系统
    await system.start()
    await system_monitor.start_input()
    
    print("🚀 系统已启动")
    print("等待3秒查看初始系统状态...")
    await asyncio.sleep(3)
    
    # 通过agent_creator创建一些普通Agent
    print("\n📝 创建普通Agent...")
    
    # 创建分析Agent
    await agent_creator.execute_action(
        AgentMessage("user", "create_agent analyzer 你是一个分析Agent，负责分析用户输入并生成分析结果", "agent_creator")
    )
    
    # 创建响应Agent
    await agent_creator.execute_action(
        AgentMessage("user", "create_agent responder 你是一个响应Agent，负责根据分析结果生成最终回答", "agent_creator")
    )
    
    await asyncio.sleep(2)
    
    # 建立连接
    print("\n🔗 建立Agent间连接...")
    
    # 连接analyzer到responder
    await agent_creator.execute_action(
        AgentMessage("user", "connect analyzer analysis responder analysis", "agent_creator")
    )
    
    # 设置responder的激活通道
    await agent_creator.execute_action(
        AgentMessage("user", "set_activation responder analysis", "agent_creator")
    )
    
    await asyncio.sleep(2)
    
    # 等待系统监控报告更新后的状态
    print("\n📊 等待系统监控报告更新后的状态...")
    await asyncio.sleep(5)
    
    # 停止系统
    print("\n🛑 停止系统...")
    await system_monitor.stop_input()
    await system.stop()
    
    print("✅ 测试完成")

if __name__ == "__main__":
    asyncio.run(test_system_agents())
#!/usr/bin/env python3
"""
测试异步Agent系统
"""

import asyncio
import os
from driver.driver import Agent
from driver.async_system import AgentSystem

# 设置环境变量（请替换为您的实际API密钥）
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"

async def test_async_system():
    """测试异步系统"""
    
    # 创建系统
    system = AgentSystem()
    
    # 创建两个测试Agent
    agent1 = Agent("analyzer", "你是一个分析Agent，负责分析用户输入并生成分析结果")
    agent2 = Agent("responder", "你是一个响应Agent，负责根据分析结果生成最终回答")
    
    # 设置连接关系
    agent1.output_connections.connections = {
        "analysis": ["responder"]
    }
    agent2.input_connections.connections = {
        "analyzer": "analysis"
    }
    agent2.input_message_keyword = ["analysis"]
    
    # 注册Agent
    system.register_agent(agent1)
    system.register_agent(agent2)
    
    # 启动系统
    await system.start()
    print("系统已启动，等待5秒...")
    
    # 发送测试消息
    await system.send_initial_message("user", "请帮我分析一下Python的异步编程特点", "analyzer")
    
    # 等待系统处理
    await asyncio.sleep(5)
    
    # 停止系统
    await system.stop()
    print("测试完成")

if __name__ == "__main__":
    # 如果没有设置API密钥，只测试架构
    if not os.environ.get("OPENAI_API_KEY"):
        print("警告: 未设置OPENAI_API_KEY环境变量，将只测试系统架构")
        print("要测试完整功能，请设置: export OPENAI_API_KEY=your-key")
    
    asyncio.run(test_async_system())
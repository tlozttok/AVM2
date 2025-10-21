#!/usr/bin/env python3
"""
主程序文件
连接模式: Input-AgentA-AgentB-Output
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
from driver.driver import AgentSystem, Agent
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent


# AgentA和AgentB现在直接使用Agent实例
# 它们的行为完全由输入和LLM决定，不通过继承扩展


async def main():
    """主异步函数"""
    print("启动 AVM2 系统...")
    print("连接模式: Input-AgentA-AgentB-Output")
    
    # 创建系统
    system = AgentSystem()
    
    # 创建代理
    user_input = UserInputAgent("用户输入: ")
    agent_a = Agent()  # 直接使用Agent实例
    agent_b = Agent()  # 直接使用Agent实例
    console_output = ConsoleOutputAgent("[系统输出]")
    
    # 添加代理到系统
    system.add_io_agent(user_input)
    system.add_agent(agent_a)
    system.add_agent(agent_b)
    system.add_io_agent(console_output)
    
    # 建立连接: Input -> AgentA -> AgentB -> Output
    user_input.output_connections.append(agent_a.id)
    agent_a.output_connection.append(("output", agent_b.id))
    agent_b.output_connection.append(("output", console_output.id))
    
    # 启动系统
    await system.start_all_input_agents()
    
    try:
        print("系统已启动，等待用户输入...")
        print("输入 'quit' 退出程序")
        print("=" * 50)
        
        # 持续运行
        await asyncio.sleep(3600)  # 运行1小时
        
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        # 停止系统
        await system.stop_all_input_agents()
        print("系统已停止")


if __name__ == "__main__":
    asyncio.run(main())
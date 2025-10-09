"""
AVM2 系统主程序 - 使用eval动态创建Agent
"""

import asyncio
import os

import glob
import yaml
from driver.driver import Agent
from driver.async_system import AgentSystem
from system_interface_agents.agent_creator_output_agent import AgentCreatorOutputAgent
from system_interface_agents.system_monitor_input_agent import SystemMonitorInputAgent
from driver import async_system

from utils.logger import basic_logger

# 调试模式设置 - 修改这个变量来控制是否启用调试模式
DEBUG_MODE = True  # 设置为True时禁用自动文件同步

async def main():
    """主程序入口"""
    
    basic_logger.info("进入主函数")
    system = AgentSystem()
    async_system.SYMBOLIC_REAL=system
    
    basic_logger.info("开始加载普通Agent")
    
    # 遍历Agents文件夹中的普通Agent
    agent_files = glob.glob("Agents/*.yaml")
    for agent_file in agent_files:
        agent = Agent("")
        agent.sync_from_file(agent_file)
        
        # 设置自动同步状态
        agent.auto_sync_enabled = not DEBUG_MODE
        
        system.register_agent(agent)
        basic_logger.info(f"加载普通Agent: {agent.id}")
        
    basic_logger.info("加载普通Agent完成")
    basic_logger.info("开始加载系统Agent")

    # 遍历系统Agent
    system_agent_files = glob.glob("Agents/SystemAgents/*.yaml")
    for system_agent_file in system_agent_files:
        with open(system_agent_file, 'r', encoding='utf-8') as f:
            agent_data = yaml.safe_load(f)
        
        class_name = agent_data["metadata"]["class_name"]
        
        # 根据字符串创建对应类型Agent
        agent = eval(class_name)(agent_data["id"])
        agent.sync_from_file(system_agent_file)
        
        # 设置自动同步状态
        agent.auto_sync_enabled = not DEBUG_MODE
        
        system.register_agent(agent)
        
        basic_logger.info(f"加载系统Agent:{agent.id}")
    
    basic_logger.info("加载系统Agent完成")
    
    await system.start()
    
    basic_logger.info("系统加载完成")
    
    try:
        
        # 保持程序运行，等待消息
        print("📡 系统正在运行")
        print("按 Ctrl+C 停止系统")
        basic_logger.info("开始运行系统")
        
        # 创建一个永久等待的future
        await asyncio.Future()
        
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号，正在关闭系统...")
        basic_logger.info("收到停止信号，正在关闭系统")
    finally:
        await system.stop()
        basic_logger.info("系统已关闭")


if __name__ == "__main__":
    asyncio.run(main())
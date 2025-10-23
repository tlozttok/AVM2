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
from utils.logger import LoggerFactory


# AgentA和AgentB现在直接使用Agent实例
# 它们的行为完全由输入和LLM决定，不通过继承扩展


async def main():
    """主异步函数"""
    # 获取主程序日志器
    logger = LoggerFactory.get_logger("main")
    
    logger.info("启动 AVM2 系统...")
    logger.info("连接模式: Input-AgentA-AgentB-Output")
    
    # 创建系统
    logger.debug("创建 AgentSystem 实例")
    system = AgentSystem()
    logger.info("AgentSystem 实例已创建")
    
    # 创建代理
    logger.debug("创建 UserInputAgent 实例")
    user_input = UserInputAgent("用户输入: ")
    logger.debug("创建 AgentA 实例")
    agent_a = Agent()  # 直接使用Agent实例
    logger.debug("创建 AgentB 实例")
    agent_b = Agent()  # 直接使用Agent实例
    logger.debug("创建 ConsoleOutputAgent 实例")
    console_output = ConsoleOutputAgent("[系统输出]")
    logger.info(f"代理创建完成: UserInputAgent({user_input.id}), AgentA({agent_a.id}), AgentB({agent_b.id}), ConsoleOutputAgent({console_output.id})")
    
    # 添加代理到系统
    logger.debug("开始添加代理到系统")
    system.add_io_agent(user_input)
    system.add_agent(agent_a)
    system.add_agent(agent_b)
    system.add_io_agent(console_output)
    logger.info("所有代理已添加到系统")
    
    # 建立连接: Input -> AgentA -> AgentB -> Output
    logger.debug("建立代理连接关系")
    user_input.output_connections.append(agent_a.id)
    logger.debug(f"UserInputAgent -> AgentA ({agent_a.id})")
    agent_a.output_connection.append(("output", agent_b.id))
    logger.debug(f"AgentA -> AgentB ({agent_b.id})")
    agent_b.output_connection.append(("output_to_console", console_output.id))
    logger.debug(f"AgentB -> ConsoleOutputAgent ({console_output.id})")
    agent_b.output_connection.append(("reflected_to_input", agent_a.id))
    logger.debug(f"AgentB -> AgentA ({agent_a.id})")
    console_output.input_connections.append(agent_b.id)
    logger.info("代理连接已建立: Input -> AgentA -> AgentB -> Output")
    
    # 启动系统
    logger.info("启动所有输入代理")
    await system.start_all_input_agents()
    logger.info("所有输入代理已启动")
    
    try:
        logger.info("系统已启动，等待用户输入...")
        print("系统已启动，等待用户输入...")
        print("输入 'quit' 退出程序")
        print("=" * 50)
        
        # 持续运行
        logger.debug("进入主运行循环 (1小时)")
        await asyncio.sleep(3600)  # 运行1小时
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
        print("\n收到中断信号...")
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        logger.exception("详细异常信息:")
        raise
    finally:
        # 停止系统
        logger.info("开始停止系统...")
        await system.stop_all_input_agents()
        logger.info("所有输入代理已停止")
        logger.info("系统已完全停止")
        print("系统已停止")


if __name__ == "__main__":
    logger = LoggerFactory.get_logger("main")
    logger.info("AVM2 系统启动")
    try:
        asyncio.run(main())
        logger.info("AVM2 系统正常退出")
    except Exception as e:
        logger.critical(f"AVM2 系统异常退出: {e}")
        logger.exception("系统崩溃详情:")
        raise
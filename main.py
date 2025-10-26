#!/usr/bin/env python3
"""
主程序文件
连接模式: UserInput -> Agent -> DfrotzOutput -> DfrotzInput -> ConsoleOutput
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
from driver.driver import AgentSystem, Agent
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent
from game_env.environment import DfrotzInputAgent, DfrotzOutputAgent
from utils.logger import LoggerFactory


async def main():
    """主异步函数"""
    # 获取主程序日志器
    logger = LoggerFactory.get_logger("main")
    
    logger.info("启动 AVM2 系统...")
    logger.info("连接模式: UserInput -> Agent -> DfrotzOutput -> DfrotzInput -> ConsoleOutput")
    
    # 创建系统
    logger.debug("创建 AgentSystem 实例")
    system = AgentSystem()
    logger.info("AgentSystem 实例已创建")
    
    
    logger.debug("创建 Agent 实例")
    agent = Agent()  # 只创建一个Agent
    
    
    # 创建dfrotz代理
    logger.debug("创建 DfrotzOutputAgent 实例")
    game_file = "game_env/dfrotz/905.z5"
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    dfrotz_output = DfrotzOutputAgent(game_file, dfrotz_path)
    
    logger.debug("创建 DfrotzInputAgent 实例")
    # DfrotzInputAgent需要共享同一个dfrotz管理器
    from game_env.environment import DfrotzManager
    #dfrotz_manager = DfrotzManager(game_file, dfrotz_path)
    dfrotz_input = DfrotzInputAgent(dfrotz_output.dfrotz_manager)
    
    logger.info(f"代理创建完成: Agent({agent.id}), DfrotzOutputAgent({dfrotz_output.id}), DfrotzInputAgent({dfrotz_input.id})")
    
    # 添加代理到系统
    logger.debug("开始添加代理到系统")
    system.add_agent(agent)
    system.add_io_agent(dfrotz_output)
    system.add_io_agent(dfrotz_input)
    logger.info("所有代理已添加到系统")
    
    logger.debug("建立代理连接关系")
    
    
    # Agent -> DfrotzOutput
    agent.output_connection.append(("dfrotz_command", dfrotz_output.id))
    logger.debug(f"Agent -> DfrotzOutputAgent ({dfrotz_output.id})")
    
    dfrotz_output.input_connections.append(agent.id)
    
    # DfrotzInput -> Agent (将游戏输出反馈给Agent)
    dfrotz_input.output_connections.append(agent.id)
    logger.debug(f"DfrotzInputAgent -> Agent ({agent.id})")
    agent.input_connection.append(("dfrotz_output", dfrotz_input.id))
    
    logger.info("代理连接已建立")
    
    # 启动系统
    logger.info("启动所有输入代理")
    await system.start_all_input_agents()
    
    # 启动dfrotz输出代理（它不是InputAgent，需要手动启动）
    logger.info("启动DfrotzOutputAgent")
    await dfrotz_output.start()
    
    logger.info("所有代理已启动")
    
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
        
        # 停止dfrotz输出代理
        logger.info("停止DfrotzOutputAgent")
        await dfrotz_output.stop()
        
        logger.info("所有代理已停止")
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
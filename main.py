#!/usr/bin/env python3
"""
主程序文件 - ETF集成版本
集成所有ETF模块的输入输出代理
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
from driver.driver import AgentSystem, Agent
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent
from game_env.environment import DfrotzInputAgent, DfrotzOutputAgent
from ETF.io_agent import TimingPromptAgent, FeedbackListenerAgent, DualOutputAgent, UserInputAgent as ETFUserInputAgent
from utils.logger import LoggerFactory


async def main():
    """主异步函数"""
    # 获取主程序日志器
    logger = LoggerFactory.get_logger("main")
    
    logger.info("启动 AVM2 ETF 集成系统...")
    logger.info("集成模式: 所有ETF代理 + 基础代理")
    
    # 创建系统
    logger.debug("创建 AgentSystem 实例")
    system = AgentSystem()
    logger.info("AgentSystem 实例已创建")
    
    # 创建主Agent
    logger.debug("创建主 Agent 实例")
    main_agent = Agent()
    
    # 创建ETF代理
    logger.debug("创建ETF代理实例")
    
    # 1. 定时提示代理
    timing_agent = TimingPromptAgent()
    
    # 2. 用户输入代理
    user_input_agent = ETFUserInputAgent()
    
    # 3. 反馈监听代理
    feedback_listener = FeedbackListenerAgent()
    
    # 4. 双重输出代理（绑定反馈监听代理）
    dual_output = DualOutputAgent(
        log_file="user_output.log",
        feedback_listener=feedback_listener
    )
    
    logger.info("所有ETF代理创建完成")
    
    # 添加代理到系统
    logger.debug("开始添加代理到系统")
    
    # 添加主Agent
    system.add_agent(main_agent)
    
    # 添加ETF代理
    system.add_io_agent(timing_agent)
    system.add_io_agent(user_input_agent)
    system.add_io_agent(feedback_listener)
    system.add_io_agent(dual_output)
    
    logger.info("所有代理已添加到系统")
    
    # 建立代理连接关系
    logger.debug("建立代理连接关系")
    
    # ETF输入代理 -> 主Agent
    # 定时提示代理连接到主Agent
    timing_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((timing_agent.id, "timing_prompt"))
    logger.debug(f"TimingPromptAgent -> 主Agent ({main_agent.id})")

    # 用户输入代理连接到主Agent
    user_input_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((user_input_agent.id, "user_input"))
    logger.debug(f"UserInputAgent -> 主Agent ({main_agent.id})")

    # 反馈监听代理连接到主Agent
    feedback_listener.output_connections.append(main_agent.id)
    main_agent.input_connection.append((feedback_listener.id, "system_feedback"))
    logger.debug(f"FeedbackListenerAgent -> 主Agent ({main_agent.id})")
    
    # 主Agent -> 双重输出代理
    main_agent.output_connection.append(("user_output", dual_output.id))
    dual_output.input_connections.append(main_agent.id)
    logger.debug(f"主Agent -> DualOutputAgent ({dual_output.id})")
    
    logger.info("代理连接已建立")
    
    # 启动系统
    logger.info("启动所有输入代理")
    await system.start_all_input_agents()
    
    logger.info("所有代理已启动")
    
    try:
        logger.info("ETF集成系统已启动")
        print("ETF集成系统已启动")
        print("当前运行的代理:")
        print(f"  - 主Agent: {main_agent.id}")
        print(f"  - 定时提示代理: {timing_agent.id}")
        print(f"  - 用户输入代理: {user_input_agent.id}")
        print(f"  - 反馈监听代理: {feedback_listener.id}")
        print(f"  - 双重输出代理: {dual_output.id}")
        print("\n系统功能:")
        print("  - 定时提示: 根据timing.yaml配置定时发送提示")
        print("  - 用户输入: 从控制台读取用户输入并发送给系统")
        print("  - 系统反馈: 系统输出会反馈回系统作为输入")
        print("  - 双重输出: 输出到日志文件和系统反馈")
        print("\n输入 Ctrl+C 退出程序")
        print("=" * 50)
        
        # 持续运行
        logger.debug("进入主运行循环")
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
        
        logger.info("所有代理已停止")
        logger.info("系统已完全停止")
        print("系统已停止")


if __name__ == "__main__":
    logger = LoggerFactory.get_logger("main")
    logger.info("AVM2 ETF 集成系统启动")
    try:
        asyncio.run(main())
        logger.info("AVM2 ETF 集成系统正常退出")
    except Exception as e:
        logger.critical(f"AVM2 ETF 集成系统异常退出: {e}")
        logger.exception("系统崩溃详情:")
        raise
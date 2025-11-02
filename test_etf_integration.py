#!/usr/bin/env python3
"""
ETF集成测试脚本
测试所有ETF代理的集成功能
"""

import asyncio
import time
import os
import sys

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from driver.driver import AgentSystem, Agent
from etf.io_agent import TimingPromptAgent, ImageDetectionAgent, FeedbackListenerAgent, DualOutputAgent
from utils.logger import LoggerFactory


async def test_etf_integration():
    """测试ETF代理集成"""
    logger = LoggerFactory.get_logger("test_etf")
    
    logger.info("开始ETF集成测试...")
    
    # 创建系统
    system = AgentSystem()
    
    # 创建代理
    main_agent = Agent()
    timing_agent = TimingPromptAgent()
    image_agent = ImageDetectionAgent()
    feedback_listener = FeedbackListenerAgent()
    dual_output = DualOutputAgent(
        log_file="test_output.log",
        feedback_listener=feedback_listener
    )
    
    # 添加到系统
    system.add_agent(main_agent)
    system.add_io_agent(timing_agent)
    system.add_io_agent(image_agent)
    system.add_io_agent(feedback_listener)
    system.add_io_agent(dual_output)
    
    # 建立连接
    timing_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((timing_agent.id, "timing_prompt"))
    
    image_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((image_agent.id, "image_detection"))
    
    feedback_listener.output_connections.append(main_agent.id)
    main_agent.input_connection.append((feedback_listener.id, "system_feedback"))
    
    main_agent.output_connection.append(("user_output", dual_output.id))
    dual_output.input_connections.append(main_agent.id)
    
    # 启动系统
    await system.start_all_input_agents()
    
    print("ETF集成测试已启动")
    print("测试将运行30秒...")
    print("检查以下功能:")
    print("1. 定时提示代理是否工作")
    print("2. 图像检测代理是否工作")
    print("3. 反馈系统是否工作")
    print("4. 双重输出是否工作")
    
    # 运行测试
    await asyncio.sleep(30)
    
    # 停止系统
    await system.stop_all_input_agents()
    
    print("ETF集成测试完成")
    print("请检查以下文件:")
    print("- test_output.log: 双重输出日志")
    print("- input_img/: 测试图片文件夹")
    print("- used_img/: 已处理图片文件夹")


if __name__ == "__main__":
    asyncio.run(test_etf_integration())
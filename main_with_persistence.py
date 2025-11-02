#!/usr/bin/env python3
"""
主程序文件 - ETF集成版本（带持久化功能）
集成所有ETF模块的输入输出代理，支持系统状态持久化
"""

import asyncio
import sys
import os
import signal

# 添加当前目录到 Python 路径
from driver.driver import AgentSystem, Agent
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent
from game_env.environment import DfrotzInputAgent, DfrotzOutputAgent
from ETF.io_agent import TimingPromptAgent, ImageDetectionAgent, FeedbackListenerAgent, DualOutputAgent, UserInputAgent as ETFUserInputAgent
from utils.logger import LoggerFactory
from utils.persistence import PersistenceUtils


async def main():
    """主异步函数"""
    # 获取主程序日志器
    logger = LoggerFactory.get_logger("main")
    
    logger.info("启动 AVM2 ETF 集成系统（带持久化功能）...")
    logger.info("集成模式: 所有ETF代理 + 基础代理 + 持久化")
    
    # 创建持久化工具
    persistence_utils = PersistenceUtils("system_checkpoints")
    
    # 检查是否有可用的检查点
    latest_checkpoint = persistence_utils.get_latest_checkpoint()
    
    system = None
    if latest_checkpoint:
        print(f"发现最新检查点: {latest_checkpoint}")
        response = input("是否从检查点恢复系统？(y/N): ").strip().lower()
        if response in ['y', 'yes']:
            try:
                system = await persistence_utils.load_system_checkpoint(latest_checkpoint)
                logger.info(f"系统已从检查点恢复: {latest_checkpoint}")
                print(f"系统已从检查点恢复，包含 {len(system.agents)} 个Agent")
            except Exception as e:
                logger.error(f"从检查点恢复失败: {e}")
                print(f"从检查点恢复失败: {e}")
                print("创建新系统...")
                system = create_new_system()
        else:
            system = create_new_system()
    else:
        system = create_new_system()
    
    # 启动自动保存任务
    auto_save_task = await persistence_utils.auto_save(system, interval=600)  # 每10分钟自动保存
    
    try:
        logger.info("ETF集成系统已启动")
        print("ETF集成系统已启动")
        print("当前运行的代理:")
        for agent_id, agent in system.agents.items():
            print(f"  - {agent.__class__.__name__}: {agent_id}")
        print("\n系统功能:")
        print("  - 定时提示: 根据timing.yaml配置定时发送提示")
        print("  - 图像识别: 自动检测input_img文件夹中的图片并识别")
        print("  - 系统反馈: 系统输出会反馈回系统作为输入")
        print("  - 双重输出: 输出到日志文件和系统反馈")
        print("  - 持久化: 自动保存系统状态，支持从检查点恢复")
        print("\n命令:")
        print("  - Ctrl+C: 优雅退出系统")
        print("  - save: 手动保存检查点")
        print("  - list: 列出所有检查点")
        print("  - quit: 退出程序")
        print("=" * 50)
        
        # 启动所有输入代理
        await system.start_all_input_agents()
        
        # 命令行交互循环
        await command_loop(system, persistence_utils)
        
    except KeyboardInterrupt:
        logger.info("收到键盘中断信号")
        print("\n收到中断信号...")
    except Exception as e:
        logger.error(f"系统运行异常: {e}")
        logger.exception("详细异常信息:")
        raise
    finally:
        # 取消自动保存任务
        auto_save_task.cancel()
        try:
            await auto_save_task
        except asyncio.CancelledError:
            pass
        
        # 停止系统
        logger.info("开始停止系统...")
        await system.stop_all_input_agents()
        
        # 保存最终检查点
        try:
            final_checkpoint = await persistence_utils.save_system_checkpoint(system, "final_checkpoint")
            logger.info(f"最终检查点已保存: {final_checkpoint}")
            print(f"最终检查点已保存: {final_checkpoint}")
        except Exception as e:
            logger.error(f"保存最终检查点失败: {e}")
        
        logger.info("所有代理已停止")
        logger.info("系统已完全停止")
        print("系统已停止")


def create_new_system() -> AgentSystem:
    """
    创建新的AgentSystem
    
    Returns:
        AgentSystem实例
    """
    logger = LoggerFactory.get_logger("main")
    
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
    
    # 2. 图像检测代理
    image_agent = ImageDetectionAgent()
    
    # 3. 反馈监听代理
    feedback_listener = FeedbackListenerAgent()
    
    # 4. 双重输出代理（绑定反馈监听代理）
    dual_output = DualOutputAgent(
        log_file="user_output.log",
        feedback_listener=feedback_listener
    )
    
    # 5. 用户输入代理（ETF版本）
    user_input_agent = ETFUserInputAgent()
    
    logger.info("所有ETF代理创建完成")
    
    # 添加代理到系统
    logger.debug("开始添加代理到系统")
    
    # 添加主Agent
    system.add_agent(main_agent)
    
    # 添加ETF代理
    system.add_io_agent(timing_agent)
    system.add_io_agent(image_agent)
    system.add_io_agent(feedback_listener)
    system.add_io_agent(dual_output)
    system.add_io_agent(user_input_agent)
    
    logger.info("所有代理已添加到系统")
    
    # 建立代理连接关系
    logger.debug("建立代理连接关系")
    
    # ETF输入代理 -> 主Agent
    # 定时提示代理连接到主Agent
    timing_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((timing_agent.id, "timing_prompt"))
    logger.debug(f"TimingPromptAgent -> 主Agent ({main_agent.id})")
    
    # 图像检测代理连接到主Agent
    image_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((image_agent.id, "image_detection"))
    logger.debug(f"ImageDetectionAgent -> 主Agent ({main_agent.id})")
    
    # 反馈监听代理连接到主Agent
    feedback_listener.output_connections.append(main_agent.id)
    main_agent.input_connection.append((feedback_listener.id, "system_feedback"))
    logger.debug(f"FeedbackListenerAgent -> 主Agent ({main_agent.id})")
    
    # 用户输入代理连接到主Agent
    user_input_agent.output_connections.append(main_agent.id)
    main_agent.input_connection.append((user_input_agent.id, "user_input"))
    logger.debug(f"UserInputAgent -> 主Agent ({main_agent.id})")
    
    # 主Agent -> 双重输出代理
    main_agent.output_connection.append(("user_output", dual_output.id))
    dual_output.input_connections.append(main_agent.id)
    logger.debug(f"主Agent -> DualOutputAgent ({dual_output.id})")
    
    logger.info("代理连接已建立")
    
    return system


async def command_loop(system: AgentSystem, persistence_utils: PersistenceUtils):
    """
    命令行交互循环
    
    Args:
        system: AgentSystem实例
        persistence_utils: 持久化工具
    """
    logger = LoggerFactory.get_logger("main")
    
    while True:
        try:
            # 使用asyncio创建异步输入读取
            loop = asyncio.get_event_loop()
            user_input = await loop.run_in_executor(None, input, "\n命令> ")
            
            command = user_input.strip().lower()
            
            if command in ['quit', 'exit', 'q']:
                logger.info("用户请求退出")
                print("正在退出系统...")
                break
            
            elif command == 'save':
                logger.info("用户请求手动保存检查点")
                try:
                    checkpoint_file = await persistence_utils.save_system_checkpoint(system, "manual_save")
                    print(f"检查点已保存: {checkpoint_file}")
                except Exception as e:
                    print(f"保存检查点失败: {e}")
            
            elif command == 'list':
                logger.info("用户请求列出检查点")
                checkpoints = persistence_utils.list_available_checkpoints()
                if checkpoints:
                    print("可用检查点:")
                    for cp in checkpoints[:5]:  # 只显示最新的5个
                        print(f"  - {cp['name']}: {cp['agent_count']} 个Agent, 时间: {cp['timestamp']}")
                else:
                    print("没有可用的检查点")
            
            elif command == 'status':
                logger.info("用户请求系统状态")
                print(f"系统状态:")
                print(f"  Agent数量: {len(system.agents)}")
                print(f"  探索Agent: {len(system.explore_agent)}")
                print(f"  IO代理: {len(system.io_agents)}")
            
            elif command == 'help':
                print("可用命令:")
                print("  save    - 手动保存检查点")
                print("  list    - 列出所有检查点")
                print("  status  - 显示系统状态")
                print("  quit    - 退出程序")
                print("  help    - 显示帮助")
            
            elif command:
                print(f"未知命令: {command}")
                print("输入 'help' 查看可用命令")
            
        except EOFError:
            logger.info("检测到输入结束(EOF)")
            break
        except KeyboardInterrupt:
            logger.info("命令行循环收到中断信号")
            break
        except Exception as e:
            logger.error(f"命令行循环异常: {e}")
            print(f"命令处理错误: {e}")


if __name__ == "__main__":
    logger = LoggerFactory.get_logger("main")
    logger.info("AVM2 ETF 集成系统（带持久化功能）启动")
    try:
        asyncio.run(main())
        logger.info("AVM2 ETF 集成系统正常退出")
    except Exception as e:
        logger.critical(f"AVM2 ETF 集成系统异常退出: {e}")
        logger.exception("系统崩溃详情:")
        raise
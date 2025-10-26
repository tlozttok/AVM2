#!/usr/bin/env python3
"""
dfrotz系统演示
展示完整的dfrotz集成系统
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from driver.driver import AgentSystem, Agent
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent
from game_env.environment import DfrotzInputAgent, DfrotzOutputAgent, DfrotzManager


async def demo_simple_interaction():
    """演示简单交互"""
    print("=== dfrotz系统演示 - 简单交互 ===")
    
    # 创建系统
    system = AgentSystem()
    
    # 创建代理
    user_input = UserInputAgent("输入游戏命令: ")
    agent = Agent()
    console_output = ConsoleOutputAgent("[游戏输出]")
    
    # 创建dfrotz代理
    game_file = "game_env/dfrotz/905.z5"
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    dfrotz_output = DfrotzOutputAgent(game_file, dfrotz_path)
    
    # DfrotzInputAgent需要共享同一个dfrotz管理器
    dfrotz_manager = DfrotzManager(game_file, dfrotz_path)
    dfrotz_input = DfrotzInputAgent(dfrotz_manager)
    
    # 添加到系统
    system.add_io_agent(user_input)
    system.add_agent(agent)
    system.add_io_agent(console_output)
    system.add_io_agent(dfrotz_output)
    system.add_io_agent(dfrotz_input)
    
    # 建立连接
    user_input.output_connections.append(agent.id)
    agent.output_connection.append(("dfrotz_command", dfrotz_output.id))
    dfrotz_input.output_connections.append(console_output.id)
    dfrotz_input.output_connections.append(agent.id)
    agent.output_connection.append(("console_output", console_output.id))
    
    print("系统配置完成，启动中...")
    
    # 启动系统
    await system.start_all_input_agents()
    await dfrotz_output.start()
    
    print("系统已启动!")
    print("您可以输入游戏命令如: look, inventory, n, s, e, w, examine 物品名等")
    print("输入 'quit' 退出演示")
    print("=" * 50)
    
    try:
        # 运行演示
        await asyncio.sleep(30)  # 运行30秒
        
    except KeyboardInterrupt:
        print("\n收到中断信号...")
    finally:
        # 停止系统
        await system.stop_all_input_agents()
        await dfrotz_output.stop()
        print("系统已停止")


async def demo_automatic_play():
    """演示自动游戏"""
    print("\n=== dfrotz系统演示 - 自动游戏 ===")
    
    # 创建dfrotz管理器
    game_file = "game_env/dfrotz/905.z5"
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    
    manager = DfrotzManager(game_file, dfrotz_path)
    
    try:
        await manager.start()
        print("dfrotz启动成功，开始自动游戏演示...")
        
        # 自动执行一系列命令
        commands = [
            "look",
            "inventory", 
            "n",
            "look",
            "s",
            "look"
        ]
        
        for i, cmd in enumerate(commands):
            print(f"\n--- 执行命令 {i+1}: {cmd} ---")
            await manager.send_text(cmd)
            await asyncio.sleep(2)
            
            output = await manager.get_output()
            if output:
                print(f"输出:\n{output}")
        
        print("\n自动游戏演示完成!")
        
        await manager.stop()
        
    except Exception as e:
        print(f"自动游戏演示失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主演示函数"""
    print("开始dfrotz系统演示...")
    
    # 演示自动游戏
    await demo_automatic_play()
    
    # 演示交互式游戏
    await demo_simple_interaction()
    
    print("\n所有演示完成!")


if __name__ == "__main__":
    asyncio.run(main())
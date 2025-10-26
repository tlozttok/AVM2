#!/usr/bin/env python3
"""
测试异步dfrotz功能
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_env.environment import DfrotzManager


async def test_async_dfrotz():
    """测试异步dfrotz功能"""
    print("=== 测试异步dfrotz功能 ===")
    
    # 使用项目中的游戏文件
    game_file = "game_env/dfrotz/905.z5"
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    
    manager = DfrotzManager(game_file, dfrotz_path)
    
    try:
        # 启动dfrotz
        print("启动dfrotz...")
        await manager.start()
        print("dfrotz启动成功")
        
        # 测试基本命令
        print("\n测试 'look' 命令...")
        await manager.send_text("look")
        await asyncio.sleep(2)
        
        output = await manager.get_output()
        print(f"look命令输出:\n{output}")
        
        # 测试分页功能
        print("\n测试分页功能...")
        await manager.send_text("inventory")
        await asyncio.sleep(2)
        
        output = await manager.get_output()
        print(f"inventory命令输出:\n{output}")
        
        # 测试移动命令
        print("\n测试移动命令...")
        await manager.send_text("n")
        await asyncio.sleep(1)
        
        output = await manager.get_output()
        print(f"移动命令输出:\n{output}")
        
        # 停止
        print("\n停止dfrotz...")
        await manager.stop()
        print("dfrotz停止成功")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


async def test_concurrent_commands():
    """测试并发命令"""
    print("\n=== 测试并发命令 ===")
    
    game_file = "game_env/dfrotz/905.z5"
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    
    manager = DfrotzManager(game_file, dfrotz_path)
    
    try:
        await manager.start()
        print("dfrotz启动成功")
        
        # 并发发送多个命令
        commands = ["look", "inventory", "n", "look"]
        
        for i, cmd in enumerate(commands):
            print(f"\n发送命令 {i+1}: {cmd}")
            await manager.send_text(cmd)
            await asyncio.sleep(1)
            
            output = await manager.get_output()
            if output:
                print(f"命令 {cmd} 输出 (前100字符): {output[:100]}...")
        
        await manager.stop()
        print("并发测试完成")
        
    except Exception as e:
        print(f"并发测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试异步dfrotz功能...")
    
    await test_async_dfrotz()
    await test_concurrent_commands()
    
    print("\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
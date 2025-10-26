#!/usr/bin/env python3
"""
测试字节流dfrotz功能
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_env.environment import DfrotzManager


async def test_bytes_dfrotz():
    """测试字节流dfrotz功能"""
    print("=== 测试字节流dfrotz功能 ===")
    
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
        
        # 测试中文支持
        print("\n测试 'inventory' 命令...")
        await manager.send_text("inventory")
        await asyncio.sleep(2)
        
        output = await manager.get_output()
        print(f"inventory命令输出:\n{output}")
        
        # 测试特殊字符
        print("\n测试特殊字符命令...")
        await manager.send_text("examine everything")
        await asyncio.sleep(2)
        
        output = await manager.get_output()
        print(f"特殊字符命令输出:\n{output}")
        
        # 停止
        print("\n停止dfrotz...")
        await manager.stop()
        print("dfrotz停止成功")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试字节流dfrotz功能...")
    
    await test_bytes_dfrotz()
    
    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
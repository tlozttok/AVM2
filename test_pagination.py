#!/usr/bin/env python3
"""
测试dfrotz分页功能
"""

import asyncio
import sys
import os

# 添加当前目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from game_env.environment import DfrotzManager


async def test_pagination():
    """测试分页功能"""
    print("=== 测试dfrotz分页功能 ===")
    
    # 使用项目中的游戏文件
    game_file = "game_env/dfrotz/905.z5"
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    
    manager = DfrotzManager(game_file, dfrotz_path)
    
    try:
        # 启动dfrotz
        await manager.start()
        print("dfrotz启动成功")
        
        # 发送一些可能产生分页的命令
        print("发送 'look' 命令...")
        await manager.send_text("look")
        
        # 等待一段时间让分页处理
        print("等待分页处理...")
        await asyncio.sleep(3)
        
        # 获取输出
        output = await manager.get_output()
        print(f"dfrotz输出:\n{output}")
        
        # 测试其他可能产生分页的命令
        print("\n发送 'inventory' 命令...")
        await manager.send_text("inventory")
        await asyncio.sleep(2)
        
        output = await manager.get_output()
        print(f"dfrotz输出:\n{output}")
        
        # 停止
        await manager.stop()
        print("dfrotz停止成功")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主测试函数"""
    print("开始测试dfrotz分页功能...")
    
    await test_pagination()
    
    print("\n测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
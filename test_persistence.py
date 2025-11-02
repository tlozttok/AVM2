#!/usr/bin/env python3
"""
测试持久化功能
"""

import asyncio
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from driver.driver import AgentSystem, Agent
from utils.persistence import CheckpointManager, PersistenceUtils


async def test_persistence():
    """测试持久化功能"""
    print("=== 测试持久化功能 ===")
    
    # 创建系统
    system = AgentSystem()
    
    # 创建几个测试Agent
    agent1 = Agent()
    agent1.state = "这是Agent1的状态，包含一些重要的记忆信息"
    agent1.input_cache = [("test_keyword", "测试消息1"), ("another_keyword", "测试消息2")]
    
    agent2 = Agent()
    agent2.state = "Agent2的状态，包含不同的记忆内容"
    agent2.input_cache = [("input_keyword", "输入消息")]
    
    # 建立连接
    agent1.output_connection = [("output_to_agent2", agent2.id)]
    agent2.input_connection = [(agent1.id, "output_to_agent2")]
    
    # 添加到系统
    system.add_agent(agent1)
    system.add_agent(agent2)
    
    # 添加到探索列表
    system.add_explore_agent(agent1.id)
    
    print(f"原始系统状态:")
    print(f"  Agent数量: {len(system.agents)}")
    print(f"  探索Agent: {system.explore_agent}")
    print(f"  Agent1状态长度: {len(agent1.state)}")
    print(f"  Agent1输入缓存: {len(agent1.input_cache)} 条消息")
    print(f"  Agent2状态长度: {len(agent2.state)}")
    print(f"  Agent2输入缓存: {len(agent2.input_cache)} 条消息")
    
    # 测试检查点管理器
    print("\n--- 测试检查点管理器 ---")
    checkpoint_manager = CheckpointManager("test_checkpoints")
    
    # 保存检查点
    checkpoint_file = checkpoint_manager.save_checkpoint(system, "test_checkpoint")
    print(f"检查点已保存: {checkpoint_file}")
    
    # 列出检查点
    checkpoints = checkpoint_manager.list_checkpoints()
    print(f"可用检查点数量: {len(checkpoints)}")
    for cp in checkpoints:
        print(f"  - {cp['name']}: {cp['agent_count']} 个Agent, 时间: {cp['timestamp']}")
    
    # 加载检查点
    print("\n--- 测试检查点加载 ---")
    restored_system = checkpoint_manager.load_checkpoint(checkpoint_file)
    
    print(f"恢复的系统状态:")
    print(f"  Agent数量: {len(restored_system.agents)}")
    print(f"  探索Agent: {restored_system.explore_agent}")
    
    # 检查恢复的Agent状态
    for agent_id, agent in restored_system.agents.items():
        print(f"  Agent {agent_id}:")
        print(f"    状态长度: {len(agent.state)}")
        print(f"    输入缓存: {len(agent.input_cache)} 条消息")
        print(f"    输入连接: {len(agent.input_connection)} 个")
        print(f"    输出连接: {len(agent.output_connection)} 个")
    
    # 测试持久化工具
    print("\n--- 测试持久化工具 ---")
    persistence_utils = PersistenceUtils("test_checkpoints")
    
    # 异步保存
    async_checkpoint_file = await persistence_utils.save_system_checkpoint(system, "async_test")
    print(f"异步保存完成: {async_checkpoint_file}")
    
    # 异步加载
    async_restored_system = await persistence_utils.load_system_checkpoint(async_checkpoint_file)
    print(f"异步加载完成，Agent数量: {len(async_restored_system.agents)}")
    
    # 清理测试文件
    print("\n--- 清理测试文件 ---")
    checkpoint_manager.delete_checkpoint(checkpoint_file)
    checkpoint_manager.delete_checkpoint(async_checkpoint_file)
    print("测试文件已清理")
    
    print("\n=== 持久化功能测试完成 ===")


if __name__ == "__main__":
    asyncio.run(test_persistence())
#!/usr/bin/env python3
"""
测试Agent内部的激活频率计算器
"""

import asyncio
import time
from driver.driver import Agent, AgentSystem


async def test_agent_frequency():
    """测试Agent内部的频率计算器"""
    print("测试Agent内部的激活频率计算器...")
    
    # 创建系统和Agent
    system = AgentSystem()
    agent = Agent()
    system.add_agent(agent)
    
    print(f"创建Agent: {agent.id}")
    
    # 模拟多次激活
    print("模拟Agent激活...")
    
    # 快速激活
    for i in range(5):
        # 模拟接收消息触发激活
        agent.input_cache.append((f"test_keyword_{i}", f"test_message_{i}"))
        await agent.activate()
        await asyncio.sleep(0.1)  # 100ms间隔
    
    # 获取频率统计
    stats = agent.get_frequency_stats()
    print(f"快速激活后频率统计:")
    print(f"  瞬时频率: {stats['instant_frequency_hz']:.3f} Hz")
    print(f"  移动平均: {stats['moving_average_frequency_hz']:.3f} Hz")
    print(f"  总激活数: {stats['total_activations']}")
    
    # 慢速激活
    for i in range(3):
        agent.input_cache.append((f"slow_keyword_{i}", f"slow_message_{i}"))
        await agent.activate()
        await asyncio.sleep(1.0)  # 1秒间隔
    
    # 获取更新后的频率统计
    stats = agent.get_frequency_stats()
    print(f"混合激活后频率统计:")
    print(f"  瞬时频率: {stats['instant_frequency_hz']:.3f} Hz")
    print(f"  移动平均: {stats['moving_average_frequency_hz']:.3f} Hz")
    print(f"  总激活数: {stats['total_activations']}")
    
    # 测试系统级别的频率统计
    system_stats = system.get_frequency_stats()
    print(f"\n系统级别频率统计:")
    for agent_id, agent_stats in system_stats.items():
        print(f"  Agent {agent_id}:")
        print(f"    瞬时频率: {agent_stats['instant_frequency_hz']:.3f} Hz")
        print(f"    移动平均: {agent_stats['moving_average_frequency_hz']:.3f} Hz")
        print(f"    总激活数: {agent_stats['total_activations']}")
    
    print("\nAgent内部频率计算器测试完成!")


async def main():
    """主测试函数"""
    print("开始测试Agent内部激活频率计算器...")
    
    await test_agent_frequency()
    
    print("\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
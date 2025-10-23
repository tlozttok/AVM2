#!/usr/bin/env python3
"""
测试激活频率计算器
"""

import asyncio
import time
from utils.frequency_calculator import ActivationFrequencyCalculator, FrequencyMonitor


async def test_activation_frequency_calculator():
    """测试单个频率计算器"""
    print("测试单个激活频率计算器...")
    
    # 创建频率计算器
    calculator = ActivationFrequencyCalculator(
        window_size=5,
        time_window_seconds=10.0,
        agent_id="test_agent"
    )
    
    # 模拟快速激活
    print("模拟快速激活...")
    for i in range(5):
        calculator.record_activation()
        await asyncio.sleep(0.1)  # 100ms间隔
    
    # 获取统计信息
    stats = calculator.get_frequency_stats()
    print(f"快速激活后统计: {stats}")
    
    # 模拟慢速激活
    print("模拟慢速激活...")
    for i in range(3):
        calculator.record_activation()
        await asyncio.sleep(1.0)  # 1秒间隔
    
    # 获取统计信息
    stats = calculator.get_frequency_stats()
    print(f"混合激活后统计: {stats}")
    
    print("单个频率计算器测试完成!")


async def test_frequency_monitor():
    """测试频率监控器"""
    print("\n测试频率监控器...")
    
    # 创建频率监控器
    monitor = FrequencyMonitor()
    
    # 注册多个Agent
    agent_ids = ["agent_a", "agent_b", "agent_c"]
    for agent_id in agent_ids:
        monitor.register_agent(agent_id)
    
    # 模拟不同频率的激活
    print("模拟不同频率的激活...")
    
    # Agent A: 高频激活
    for i in range(10):
        monitor.record_activation("agent_a")
        await asyncio.sleep(0.05)  # 50ms间隔
    
    # Agent B: 中频激活
    for i in range(5):
        monitor.record_activation("agent_b")
        await asyncio.sleep(0.2)  # 200ms间隔
    
    # Agent C: 低频激活
    for i in range(3):
        monitor.record_activation("agent_c")
        await asyncio.sleep(0.5)  # 500ms间隔
    
    # 获取所有统计信息
    all_stats = monitor.get_all_frequency_stats()
    print("所有Agent频率统计:")
    for agent_id, stats in all_stats.items():
        print(f"  {agent_id}:")
        print(f"    瞬时频率: {stats['instant_frequency_hz']:.3f} Hz")
        print(f"    移动平均: {stats['moving_average_frequency_hz']:.3f} Hz")
        print(f"    总激活数: {stats['total_activations']}")
        print(f"    窗口内激活: {stats['activations_in_window']}")
    
    print("频率监控器测试完成!")


async def main():
    """主测试函数"""
    print("开始测试激活频率计算器...")
    
    await test_activation_frequency_calculator()
    await test_frequency_monitor()
    
    print("\n所有测试完成!")


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
系统集成测试 - 验证所有组件能否协同工作
"""

import asyncio
import sys
import os

# 添加driver目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'driver'))

try:
    from driver.driver import Agent, AgentMessage, MessageBus
    from driver.async_system import AgentSystem
    from driver.system_agents import InputAgent, OutputAgent
    from system_interface_agents.system_agent_examples import AgentCreatorOutputAgent, SystemMonitorInputAgent
    print("✅ 所有模块导入成功")
except ImportError as e:
    print(f"❌ 模块导入失败: {e}")
    sys.exit(1)


async def test_basic_components():
    """测试基础组件"""
    print("\n=== 测试基础组件 ===")
    
    try:
        # 1. 测试MessageBus
        message_bus = MessageBus()
        print("✅ MessageBus创建成功")
        
        # 2. 测试Agent创建
        agent = Agent("test_agent", "测试提示词", message_bus)
        print("✅ Agent创建成功")
        
        # 3. 测试AgentMessage
        message = AgentMessage("sender", "测试消息", "receiver")
        print("✅ AgentMessage创建成功")
        
        # 4. 测试AgentSystem
        system = AgentSystem()
        print("✅ AgentSystem创建成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 基础组件测试失败: {e}")
        return False


async def test_message_flow():
    """测试消息流"""
    print("\n=== 测试消息流 ===")
    
    try:
        system = AgentSystem()
        
        # 创建两个测试Agent
        agent1 = Agent("agent1", "第一个测试Agent", system.message_bus)
        agent2 = Agent("agent2", "第二个测试Agent", system.message_bus)
        
        # 设置连接
        agent1.output_connections.connections = {"output": ["agent2"]}
        agent2.input_connections.connections = {"agent1": "input"}
        agent2.input_message_keyword = ["input"]
        
        # 注册Agent
        system.register_agent(agent1)
        system.register_agent(agent2)
        
        # 启动系统
        await system.start()
        print("✅ 系统启动成功")
        
        # 发送测试消息
        test_message = AgentMessage("test", "集成测试消息", None)
        await system.message_bus.send_message("user", test_message, "agent1")
        print("✅ 消息发送成功")
        
        # 等待消息处理
        await asyncio.sleep(2)
        
        # 停止系统
        await system.stop()
        print("✅ 系统停止成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 消息流测试失败: {e}")
        return False


async def test_system_agents():
    """测试系统接口Agent"""
    print("\n=== 测试系统接口Agent ===")
    
    try:
        system = AgentSystem()
        
        # 创建系统接口Agent
        agent_creator = AgentCreatorOutputAgent("creator", system, system.message_bus)
        system_monitor = SystemMonitorInputAgent("monitor", system, 2.0, system.message_bus)
        
        # 注册系统Agent
        system.register_agent(agent_creator)
        system.register_agent(system_monitor)
        
        # 启动系统
        await system.start()
        await system_monitor.start_input()
        print("✅ 系统接口Agent启动成功")
        
        # 测试Agent创建功能
        create_message = AgentMessage("user", "create_agent test_new 新创建的测试Agent", "creator")
        await agent_creator.execute_action(create_message)
        print("✅ Agent创建功能测试成功")
        
        # 等待系统监控报告
        await asyncio.sleep(3)
        
        # 停止系统
        await system_monitor.stop_input()
        await system.stop()
        print("✅ 系统接口Agent停止成功")
        
        return True
        
    except Exception as e:
        print(f"❌ 系统接口Agent测试失败: {e}")
        return False


async def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试错误处理 ===")
    
    try:
        system = AgentSystem()
        
        # 测试向不存在的Agent发送消息
        message = AgentMessage("sender", "测试消息", "nonexistent")
        await system.message_bus.send_message("user", message, "nonexistent")
        print("✅ 不存在的Agent消息处理正常")
        
        # 测试空消息
        empty_message = AgentMessage("", "", "")
        await system.message_bus.send_message("", empty_message, "")
        print("✅ 空消息处理正常")
        
        await system.stop()
        return True
        
    except Exception as e:
        print(f"❌ 错误处理测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("🚀 开始系统集成测试")
    
    tests = [
        test_basic_components,
        test_message_flow,
        test_system_agents,
        test_error_handling
    ]
    
    results = []
    for test in tests:
        result = await test()
        results.append(result)
        await asyncio.sleep(1)  # 测试间间隔
    
    # 总结测试结果
    print("\n" + "="*50)
    print("📊 测试结果总结:")
    
    passed = sum(results)
    total = len(results)
    
    for i, result in enumerate(results):
        status = "✅ 通过" if result else "❌ 失败"
        print(f"测试 {i+1}: {status}")
    
    print(f"\n总成绩: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统可以正常运行")
    else:
        print("⚠️  部分测试失败，需要修复问题")
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
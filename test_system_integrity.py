#!/usr/bin/env python3
"""
测试系统完整性，确保没有破坏原有逻辑
"""

from driver.driver import AgentSystem, Agent, MessageBus
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent
import inspect

def test_system_integrity():
    print("测试系统完整性...")
    
    # 测试类型
    system = AgentSystem()
    agent = Agent()
    message_bus = MessageBus()
    user_input = UserInputAgent()
    console_output = ConsoleOutputAgent()
    
    print("✓ 所有类实例化成功")
    
    # 测试方法签名
    methods_to_check = [
        (MessageBus, 'send_message', ['message', 'receiver_id', 'sender_id']),
        (Agent, 'receive_message', ['message', 'sender']),
        (Agent, 'send_message', ['message', 'keyword']),
        (Agent, 'process_signal', ['signals']),
        (Agent, 'process_response', ['response']),
    ]
    
    for cls, method_name, expected_params in methods_to_check:
        method = getattr(cls, method_name, None)
        if method:
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            if params[1:] == expected_params:  # 跳过self参数
                print(f"✓ {cls.__name__}.{method_name} 方法签名正确")
            else:
                print(f"✗ {cls.__name__}.{method_name} 方法签名错误: {params[1:]} != {expected_params}")
        else:
            print(f"✗ {cls.__name__}.{method_name} 方法不存在")
    
    # 测试异步方法
    async_methods = [
        (MessageBus, 'send_message'),
        (Agent, 'receive_message'), 
        (Agent, 'send_message'),
        (Agent, 'process_signal'),
        (Agent, 'process_response'),
        (Agent, 'activate'),
    ]
    
    for cls, method_name in async_methods:
        method = getattr(cls, method_name, None)
        if method and inspect.iscoroutinefunction(method):
            print(f"✓ {cls.__name__}.{method_name} 是异步方法")
        else:
            print(f"✗ {cls.__name__}.{method_name} 不是异步方法")
    
    print("\n系统完整性测试完成！")

if __name__ == "__main__":
    test_system_integrity()
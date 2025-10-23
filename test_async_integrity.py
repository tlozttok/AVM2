#!/usr/bin/env python3
"""
测试异步优化完整性，确保LLM日志记录没有破坏原有逻辑
"""

from driver.driver import AgentSystem, Agent, MessageBus
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent
import inspect

def test_async_optimizations():
    print("测试异步优化完整性...")
    
    # 测试实例化
    system = AgentSystem()
    agent = Agent()
    message_bus = MessageBus()
    user_input = UserInputAgent()
    console_output = ConsoleOutputAgent()
    
    print("✓ 所有类实例化成功")
    
    # 测试异步优化方法签名
    methods_to_check = [
        (MessageBus, 'send_message', ['message', 'receiver_id', 'sender_id'], 'Optional[asyncio.Task]'),
        (Agent, 'receive_message', ['message', 'sender'], 'Optional[asyncio.Task]'),
        (Agent, 'send_message', ['message', 'keyword'], None),
        (Agent, 'process_signal', ['signals'], None),
        (Agent, 'process_response', ['response'], None),
    ]
    
    for cls, method_name, expected_params, return_type in methods_to_check:
        method = getattr(cls, method_name, None)
        if method:
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            # 检查参数
            if params[1:] == expected_params:  # 跳过self参数
                print(f"✓ {cls.__name__}.{method_name} 参数正确: {params[1:]}")
            else:
                print(f"✗ {cls.__name__}.{method_name} 参数错误: {params[1:]} != {expected_params}")
            
            # 检查返回类型注解
            if return_type and sig.return_annotation != inspect.Signature.empty:
                if str(sig.return_annotation) == return_type:
                    print(f"✓ {cls.__name__}.{method_name} 返回类型正确: {sig.return_annotation}")
                else:
                    print(f"✗ {cls.__name__}.{method_name} 返回类型错误: {sig.return_annotation} != {return_type}")
            elif return_type:
                print(f"✗ {cls.__name__}.{method_name} 缺少返回类型注解")
            else:
                print(f"✓ {cls.__name__}.{method_name} 返回类型正确")
        else:
            print(f"✗ {cls.__name__}.{method_name} 方法不存在")
    
    # 测试异步方法
    async_methods = [
        (Agent, 'send_message'),
        (Agent, 'process_signal'),
        (Agent, 'process_response'),
        (Agent, 'activate'),
        (InputAgent, 'send_collected_data'),
        (OutputAgent, 'receive_message'),
    ]
    
    for cls, method_name in async_methods:
        method = getattr(cls, method_name, None)
        if method and inspect.iscoroutinefunction(method):
            print(f"✓ {cls.__name__}.{method_name} 是异步方法")
        else:
            print(f"✗ {cls.__name__}.{method_name} 不是异步方法")
    
    print("\n异步优化完整性测试完成！")

if __name__ == "__main__":
    test_async_optimizations()
#!/usr/bin/env python3
"""
测试类型修改是否正确
"""

from driver.driver import AgentSystem, Agent, MessageBus
from driver.simple_io_agent import UserInputAgent, ConsoleOutputAgent

def test_types():
    print("测试类型修改...")
    
    # 测试AgentSystem
    system = AgentSystem()
    print(f"AgentSystem agents 类型: {type(system.agents)}")
    
    # 测试Agent
    agent = Agent()
    print(f"Agent id 类型: {type(agent.id)}")
    print(f"Agent input_connection 类型: {type(agent.input_connection)}")
    print(f"Agent output_connection 类型: {type(agent.output_connection)}")
    
    # 测试MessageBus
    message_bus = MessageBus()
    print(f"MessageBus agents 类型: {type(message_bus.agents)}")
    
    # 测试UserInputAgent
    user_input = UserInputAgent()
    print(f"UserInputAgent id 类型: {type(user_input.id)}")
    print(f"UserInputAgent output_connections 类型: {type(user_input.output_connections)}")
    
    # 测试ConsoleOutputAgent
    console_output = ConsoleOutputAgent()
    print(f"ConsoleOutputAgent id 类型: {type(console_output.id)}")
    print(f"ConsoleOutputAgent input_connections 类型: {type(console_output.input_connections)}")
    
    print("\n所有类型测试完成！")

if __name__ == "__main__":
    test_types()
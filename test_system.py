#!/usr/bin/env python3
"""
测试SystemMessage的新集成模式
"""

from driver.driver import SystemMessage, Context, AgentMessage, Agent

def test_system_message():
    """测试SystemMessage的新功能"""
    
    # 测试SystemMessage
    system_msg = SystemMessage()
    print("初始SystemMessage内容:")
    print(system_msg.content)
    print("-" * 50)
    
    # 测试集成关键词
    keywords = ["response", "analysis", "decision"]
    system_msg.integrate_keywords(keywords)
    print("集成关键词后的SystemMessage:")
    print(system_msg.content)
    print("-" * 50)
    
    # 测试集成系统提示词
    system_prompt = "你负责处理用户请求并生成合适的响应。"
    system_msg.integrate_system_prompt(system_prompt)
    print("集成系统提示词后的SystemMessage:")
    print(system_msg.content)
    print("-" * 50)
    
    # 测试集成Agent消息
    agent_messages = [
        AgentMessage("agent1", "用户需要帮助", "current_agent"),
        AgentMessage("agent2", "分析完成", "current_agent")
    ]
    system_msg.integrate(agent_messages)
    print("集成Agent消息后的SystemMessage:")
    print(system_msg.content)

def test_context_integration():
    """测试Context集成"""
    
    # 创建测试数据
    system_prompt = "测试系统提示词"
    bg_messages = [
        AgentMessage("background", "背景信息1", "current"),
        AgentMessage("background", "背景信息2", "current")
    ]
    input_messages = [
        AgentMessage("user", "用户输入1", "current"),
        AgentMessage("user", "用户输入2", "current")
    ]
    output_keywords = ["output1", "output2"]
    
    # 测试Context集成
    context = Context().integrate(
        system_prompt, 
        bg_messages, 
        input_messages,
        output_keywords
    )
    
    print("\nContext集成结果:")
    print("SystemMessage内容:")
    print(context.content[0].content)
    print("\nUserMessage内容:")
    print(context.content[1].content)
    
    # 测试消息转换
    messages = context.to_messages()
    print("\n转换为API消息格式:")
    for msg in messages:
        print(f"{msg['role']}: {msg['content'][:100]}...")

if __name__ == "__main__":
    test_system_message()
    test_context_integration()
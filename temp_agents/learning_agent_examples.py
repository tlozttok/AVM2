"""
学习使用系统接口Agent的示例
演示想象界Agent如何学会与实在界系统Agent交互
"""

import asyncio
from typing import Dict, Any
from driver.driver import Agent, AgentMessage
from driver.system_agents import IOAgent
from system_interface_agents.system_agent_examples import AgentCreatorOutputAgent, SystemMonitorInputAgent


class SystemInterfaceLearnerAgent(Agent):
    """
    学习使用系统接口Agent的示例Agent
    通过语义学习如何与系统Agent交互
    """
    
    def __init__(self, id: str, prompt: str = "", message_bus=None):
        # 基础提示词，包含系统接口的使用知识
        system_interface_prompt = """
你是一个学习使用系统接口的Agent。你需要学会如何与系统接口Agent交互来查询系统状态和创建新的Agent。

系统接口Agent包括：
1. IOAgent - 用于系统查询（agent_io）
2. AgentCreatorOutputAgent - 用于创建新Agent（agent_creator）
3. SystemMonitorInputAgent - 用于系统监控（system_monitor）

查询系统状态的格式：
<system_metadata></system_metadata> - 获取系统元信息
<agent_list></agent_list> - 获取Agent列表
<keyword_subgraph>keyword=关键词</keyword_subgraph> - 获取关键词子图
<agent_details>agent_ids=agent1,agent2</agent_details> - 获取Agent详情
<connection_stats></connection_stats> - 获取连接统计

创建新Agent的JSON格式：
{
  "operation": "create_agent",
  "id": "新AgentID",
  "prompt": "新Agent的提示词",
  "input_connections": {"发送者ID": "输入通道"},
  "output_connections": {"输出通道": ["接收者ID列表"]},
  "activation_channels": ["激活通道列表"]
}

请根据你的任务需求，选择合适的系统接口进行操作。
"""
        
        full_prompt = system_interface_prompt + (prompt if prompt else "")
        super().__init__(id, full_prompt, message_bus)
        
        # 记录学习到的系统接口知识
        self.learned_interfaces = {
            "system_query": False,
            "agent_creation": False,
            "system_monitoring": False
        }
    
    async def demonstrate_system_learning(self):
        """演示系统接口学习过程"""
        print(f"🎓 {self.id} 开始学习系统接口使用...")
        
        # 学习阶段1: 系统查询
        await self._learn_system_query()
        
        # 学习阶段2: Agent创建
        await self._learn_agent_creation()
        
        # 学习阶段3: 系统监控
        await self._learn_system_monitoring()
        
        print(f"✅ {self.id} 系统接口学习完成!")
        self._print_learning_summary()
    
    async def _learn_system_query(self):
        """学习系统查询接口"""
        print("\\n📊 学习阶段1: 系统查询接口")
        
        # 模拟发送系统查询消息
        query_examples = [
            "<system_metadata></system_metadata>",
            "<agent_list></agent_list>",
            "<connection_stats></connection_stats>"
        ]
        
        for query in query_examples:
            print(f"  发送查询: {query}")
            # 在实际系统中，这里会通过消息总线发送到IOAgent
            # await self.send_message_async(query)
        
        self.learned_interfaces["system_query"] = True
        print("  ✅ 系统查询接口学习完成")
    
    async def _learn_agent_creation(self):
        """学习Agent创建接口"""
        print("\\n🛠️ 学习阶段2: Agent创建接口")
        
        # Agent创建语义示例
        creation_semantic = '''
{
  "operation": "create_agent",
  "id": "learned_agent",
  "prompt": "这是一个通过学习创建的Agent，具备系统接口使用能力",
  "input_connections": {
    "system_interface_learner": "learning_input"
  },
  "output_connections": {
    "analysis": ["system_monitor"],
    "learning_output": ["system_interface_learner"]
  },
  "activation_channels": ["learning_input"]
}
'''
        
        print(f"  学习Agent创建语义:")
        print(f"  {creation_semantic.strip()}")
        
        # 在实际系统中，这里会通过消息总线发送到AgentCreatorOutputAgent
        # await self.send_message_async(creation_semantic)
        
        self.learned_interfaces["agent_creation"] = True
        print("  ✅ Agent创建接口学习完成")
    
    async def _learn_system_monitoring(self):
        """学习系统监控接口"""
        print("\\n📈 学习阶段3: 系统监控接口")
        
        # 系统监控语义示例
        monitoring_concepts = [
            "系统元信息包含Agent数量、消息统计、运行时间",
            "连接拓扑显示Agent间的通信关系",
            "关键词分布反映系统的语义结构",
            "性能指标帮助评估系统健康度"
        ]
        
        for concept in monitoring_concepts:
            print(f"  理解概念: {concept}")
        
        self.learned_interfaces["system_monitoring"] = True
        print("  ✅ 系统监控接口学习完成")
    
    def _print_learning_summary(self):
        """打印学习总结"""
        print(f"\\n📋 {self.id} 学习总结:")
        for interface, learned in self.learned_interfaces.items():
            status = "✅ 已掌握" if learned else "❌ 未掌握"
            print(f"  {interface}: {status}")
    
    def generate_system_interface_guide(self) -> str:
        """生成系统接口使用指南"""
        guide = """
# 系统接口使用指南

## 可用接口
1. **IOAgent (agent_io)** - 系统查询
2. **AgentCreatorOutputAgent (agent_creator)** - Agent创建
3. **SystemMonitorInputAgent (system_monitor)** - 系统监控

## 查询格式
- 系统元信息: <system_metadata></system_metadata>
- Agent列表: <agent_list></agent_list>
- 关键词子图: <keyword_subgraph>keyword=关键词</keyword_subgraph>
- Agent详情: <agent_details>agent_ids=id1,id2</agent_details>
- 连接统计: <connection_stats></connection_stats>

## 创建Agent格式
使用JSON格式发送到agent_creator:
```json
{
  "operation": "create_agent",
  "id": "新AgentID",
  "prompt": "提示词",
  "input_connections": {},
  "output_connections": {},
  "activation_channels": []
}
```
"""
        return guide


async def demo_system_interface_learning():
    """演示系统接口学习过程"""
    from .async_system import AgentSystem
    
    # 创建系统
    system = AgentSystem()
    
    # 创建学习Agent
    learner = SystemInterfaceLearnerAgent(
        "system_learner",
        "你是一个专门学习系统接口使用的Agent，目标是掌握所有系统交互方法。"
    )
    
    # 创建系统接口Agent
    from .system_agent_examples import AgentCreatorOutputAgent, SystemMonitorInputAgent
    from .system_agents import IOAgent
    
    agent_creator = AgentCreatorOutputAgent("agent_creator", system, system.message_bus)
    system_monitor = SystemMonitorInputAgent("system_monitor", system, 10.0, system.message_bus)
    io_agent = IOAgent("agent_io", system, "", system.message_bus)
    
    # 注册所有Agent
    system.register_agent(learner)
    system.register_agent(agent_creator)
    system.register_agent(system_monitor)
    system.register_agent(io_agent)
    
    # 设置连接关系
    learner.output_connections.connections = {
        "system_queries": ["agent_io"],
        "creation_requests": ["agent_creator"],
        "monitoring_feedback": ["system_monitor"]
    }
    
    io_agent.input_connections.connections = {
        "system_learner": "system_queries"
    }
    agent_creator.input_connections.connections = {
        "system_learner": "creation_requests"
    }
    
    # 启动系统
    await system.start()
    await system_monitor.start_input()
    
    print("🚀 系统接口学习演示开始")
    print("=" * 50)
    
    # 执行学习过程
    await learner.demonstrate_system_learning()
    
    print("\\n" + "=" * 50)
    print("📚 生成的系统接口指南:")
    print(learner.generate_system_interface_guide())
    
    # 停止系统
    await system_monitor.stop_input()
    await system.stop()
    
    print("✅ 系统接口学习演示完成")


if __name__ == "__main__":
    asyncio.run(demo_system_interface_learning())
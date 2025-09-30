"""
系统接口Agent的实用实现
"""

import asyncio
import time
from typing import Optional, Dict, Any
from .system_agents import InputAgent, OutputAgent
from .driver import Agent, AgentMessage, MessageBus


class AgentCreatorOutputAgent(OutputAgent):
    """
    创建普通Agent的系统输出Agent
    根据接收到的JSON消息创建新的普通Agent
    """
    
    def __init__(self, id: str, agent_system, message_bus=None):
        super().__init__(id, message_bus)
        self.agent_system = agent_system  # 需要访问系统来注册新Agent
    
    async def execute_action(self, message: AgentMessage) -> bool:
        """解析JSON消息并创建新的普通Agent"""
        try:
            content = message.content.strip()
            
            # 尝试解析JSON格式
            if content.startswith('{') and content.endswith('}'):
                import json
                operation_data = json.loads(content)
                
                operation_type = operation_data.get("operation")
                
                if operation_type == "create_agent":
                    return await self._create_agent_from_json(operation_data)
                elif operation_type == "connect_agents":
                    return await self._connect_agents_from_json(operation_data)
                elif operation_type == "set_activation":
                    return await self._set_activation_from_json(operation_data)
                else:
                    print(f"❓ 未知JSON操作类型: {operation_type}")
                    return False
            
            # 向后兼容：支持旧的简单字符串格式
            elif content.startswith("create_agent "):
                return await self._create_agent_from_string(content)
            elif content.startswith("connect "):
                return await self._connect_agents_from_string(content)
            elif content.startswith("set_activation "):
                return await self._set_activation_from_string(content)
            
            else:
                print(f"❓ 未知指令格式: {content}")
                return False
                
        except Exception as e:
            print(f"❌ Agent创建/配置失败: {e}")
            return False
    
    async def _create_agent_from_json(self, data: dict) -> bool:
        """从JSON数据创建Agent"""
        agent_id = data.get("id")
        prompt = data.get("prompt", "")
        
        if not agent_id:
            print("❌ JSON格式错误: 缺少id字段")
            return False
        
        # 创建新的普通Agent
        new_agent = Agent(agent_id, prompt, self.message_bus)
        
        # 设置连接关系
        input_connections = data.get("input_connections", {})
        output_connections = data.get("output_connections", {})
        activation_channels = data.get("activation_channels", [])
        
        new_agent.input_connections.connections = input_connections
        new_agent.output_connections.connections = output_connections
        new_agent.input_message_keyword = activation_channels
        
        # 注册到系统
        self.agent_system.register_agent(new_agent)
        
        print(f"✅ 成功创建Agent: {agent_id}")
        print(f"   提示词: {prompt[:50]}..." if len(prompt) > 50 else f"   提示词: {prompt}")
        return True
    
    async def _connect_agents_from_json(self, data: dict) -> bool:
        """从JSON数据连接Agent"""
        connections = data.get("connections", [])
        
        for conn in connections:
            from_id = conn.get("from_id")
            output_channel = conn.get("output_channel")
            to_id = conn.get("to_id")
            input_channel = conn.get("input_channel")
            
            if not all([from_id, output_channel, to_id, input_channel]):
                print(f"❌ 连接数据不完整: {conn}")
                continue
            
            # 获取源Agent和目标Agent
            from_agent = self.agent_system.agents.get(from_id)
            to_agent = self.agent_system.agents.get(to_id)
            
            if from_agent and to_agent:
                # 设置输出连接
                if output_channel not in from_agent.output_connections.connections:
                    from_agent.output_connections.connections[output_channel] = []
                from_agent.output_connections.connections[output_channel].append(to_id)
                
                # 设置输入连接
                to_agent.input_connections.connections[from_id] = input_channel
                
                print(f"✅ 成功建立连接: {from_id}.{output_channel} -> {to_id}.{input_channel}")
            else:
                print(f"❌ 连接失败: 未找到Agent ({from_id} 或 {to_id})")
        
        return True
    
    async def _set_activation_from_json(self, data: dict) -> bool:
        """从JSON数据设置激活通道"""
        agent_id = data.get("agent_id")
        activation_channels = data.get("activation_channels", [])
        
        if not agent_id:
            print("❌ JSON格式错误: 缺少agent_id字段")
            return False
        
        agent = self.agent_system.agents.get(agent_id)
        if agent:
            agent.input_message_keyword = activation_channels
            print(f"✅ 设置Agent {agent_id} 的激活通道: {activation_channels}")
            return True
        else:
            print(f"❌ 设置激活通道失败: 未找到Agent {agent_id}")
            return False
    
    # 向后兼容的字符串处理方法
    async def _create_agent_from_string(self, content: str) -> bool:
        parts = content.split(" ", 2)
        if len(parts) >= 3:
            agent_id = parts[1]
            prompt = parts[2]
            
            new_agent = Agent(agent_id, prompt, self.message_bus)
            self.agent_system.register_agent(new_agent)
            
            print(f"✅ 成功创建Agent: {agent_id}")
            return True
        return False
    
    async def _connect_agents_from_string(self, content: str) -> bool:
        parts = content.split(" ")
        if len(parts) == 5:
            from_id, output_channel, to_id, input_channel = parts[1:]
            
            from_agent = self.agent_system.agents.get(from_id)
            to_agent = self.agent_system.agents.get(to_id)
            
            if from_agent and to_agent:
                if output_channel not in from_agent.output_connections.connections:
                    from_agent.output_connections.connections[output_channel] = []
                from_agent.output_connections.connections[output_channel].append(to_id)
                
                to_agent.input_connections.connections[from_id] = input_channel
                
                print(f"✅ 成功建立连接: {from_id}.{output_channel} -> {to_id}.{input_channel}")
                return True
        return False
    
    async def _set_activation_from_string(self, content: str) -> bool:
        parts = content.split(" ")
        if len(parts) >= 2:
            agent_id = parts[1]
            activation_channels = parts[2:]
            
            agent = self.agent_system.agents.get(agent_id)
            if agent:
                agent.input_message_keyword = activation_channels
                print(f"✅ 设置Agent {agent_id} 的激活通道: {activation_channels}")
                return True
        return False


class SystemMonitorInputAgent(InputAgent):
    """
    系统监控输入Agent
    记录程序系统内各个Agent的信息并定期报告
    提供实在界→想象界的转换
    """
    
    def __init__(self, id: str, agent_system, report_interval: float = 10.0, message_bus=None):
        super().__init__(id, message_bus)
        self.agent_system = agent_system
        self.report_interval = report_interval  # 报告间隔（秒）
        self.last_report_time = 0
    
    async def collect_input(self) -> Optional[str]:
        """收集系统状态信息"""
        current_time = time.time()
        
        # 检查是否到达报告间隔
        if current_time - self.last_report_time >= self.report_interval:
            self.last_report_time = current_time
            
            # 收集系统信息
            system_info = self._collect_system_info()
            return system_info
        
        return None
    
    def should_activate(self, input_data: str) -> bool:
        """只要有系统信息就激活"""
        return input_data is not None
    
    def format_message(self, input_data: str) -> str:
        """格式化系统报告消息"""
        return f"系统状态报告:\n{input_data}"
    
    def _collect_system_info(self) -> str:
        """收集详细的系统信息"""
        import json
        
        # 构建JSON格式的系统描述（实在界→想象界转换）
        system_description = {
            "operation": "system_report",
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "total_agents": len(self.agent_system.agents),
            "agents": []
        }
        
        for agent_id, agent in self.agent_system.agents.items():
            # 实在界Agent对象转换为想象界JSON描述
            agent_description = {
                "id": agent_id,
                "type": "普通Agent" if isinstance(agent, Agent) and agent.prompt else "系统Agent",
                "prompt": agent.prompt or "",
                "input_connections": dict(agent.input_connections.connections),
                "output_connections": dict(agent.output_connections.connections),
                "activation_channels": agent.input_message_keyword if hasattr(agent, 'input_message_keyword') else []
            }
            system_description["agents"].append(agent_description)
        
        # 返回JSON格式的系统描述
        return json.dumps(system_description, ensure_ascii=False, indent=2)


# 演示如何使用这些系统Agent
async def demo_system_agents():
    """演示系统接口Agent的使用"""
    from .driver import AgentSystem, AgentMessage
    
    # 创建系统
    system = AgentSystem()
    
    # 创建系统接口Agent
    agent_creator = AgentCreatorOutputAgent("agent_creator", system, system.message_bus)
    system_monitor = SystemMonitorInputAgent("system_monitor", system, 5.0, system.message_bus)  # 每5秒报告一次
    
    # 注册系统Agent
    system.register_agent(agent_creator)
    system.register_agent(system_monitor)
    
    # 启动系统
    await system.start()
    await system_monitor.start_input()
    
    print("系统已启动，等待系统监控报告...")
    
    # 测试JSON格式创建Agent
    print("\\n=== 测试JSON格式创建Agent ===")
    json_create_command = '''
{
  "operation": "create_agent",
  "id": "json_created_agent",
  "prompt": "这是一个通过JSON创建的Agent",
  "input_connections": {
    "agent_creator": "system_commands"
  },
  "output_connections": {
    "analysis": ["system_monitor"]
  },
  "activation_channels": ["system_commands"]
}
'''
    
    # 模拟发送JSON创建命令
    test_message = AgentMessage("test", json_create_command)
    await agent_creator.receive_message_async(test_message, "test_sender")
    
    # 等待一段时间查看系统监控
    await asyncio.sleep(10)
    
    # 停止系统
    await system_monitor.stop_input()
    await system.stop()


if __name__ == "__main__":
    asyncio.run(demo_system_agents())
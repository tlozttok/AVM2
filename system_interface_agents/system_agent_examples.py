"""
系统接口Agent的实用实现
"""

import asyncio
import time
from typing import Optional, Dict, Any
from driver.system_agents import InputAgent, OutputAgent
from driver.driver import Agent, AgentMessage, MessageBus


class AgentCreatorOutputAgent(OutputAgent):
    """
    创建普通Agent的系统输出Agent
    实现语义字符串与Agent对象的严格转换机制
    根据接收到的语义描述创建新的普通Agent
    """
    
    def __init__(self, id: str, agent_system, message_bus=None):
        super().__init__(id, message_bus)
        self.agent_system = agent_system  # 需要访问系统来注册新Agent
        
        # 语义转换验证器
        self.semantic_validators = {
            "agent_creation": self._validate_agent_creation_semantics,
            "connection_setup": self._validate_connection_semantics,
            "activation_setup": self._validate_activation_semantics
        }
    
    async def execute_action(self, message: AgentMessage) -> bool:
        """
        严格的语义转换：将语义字符串转换为Agent对象
        实现实在界与想象界的精确映射
        """
        try:
            content = message.content.strip()
            
            # 语义验证阶段
            validation_result = await self._validate_semantic_structure(content)
            if not validation_result["valid"]:
                print(f"❌ 语义验证失败: {validation_result['error']}")
                return False
            
            # 语义解析阶段
            semantic_data = validation_result["data"]
            
            # 执行语义转换
            operation_type = semantic_data.get("operation")
            
            if operation_type == "create_agent":
                return await self._strict_create_agent(semantic_data)
            elif operation_type == "connect_agents":
                return await self._strict_connect_agents(semantic_data)
            elif operation_type == "set_activation":
                return await self._strict_set_activation(semantic_data)
            # 系统Agent创建应该由专门的系统Agent创建器处理
            else:
                print(f"❓ 未知语义操作类型: {operation_type}")
                return False
                
        except Exception as e:
            print(f"❌ 语义转换失败: {e}")
            return False
    
    async def _validate_semantic_structure(self, content: str) -> dict:
        """验证语义字符串的结构完整性"""
        try:
            # 支持多种语义格式
            if content.startswith('{') and content.endswith('}'):
                import json
                data = json.loads(content)
                
                # 验证必需字段
                required_fields = ["operation"]
                for field in required_fields:
                    if field not in data:
                        return {"valid": False, "error": f"缺少必需字段: {field}"}
                
                # 验证操作类型特定的字段
                operation = data["operation"]
                if operation == "create_agent":
                    if "id" not in data:
                        return {"valid": False, "error": "创建Agent需要id字段"}
                elif operation == "connect_agents":
                    if "connections" not in data:
                        return {"valid": False, "error": "连接Agent需要connections字段"}
                elif operation == "set_activation":
                    if "agent_id" not in data:
                        return {"valid": False, "error": "设置激活需要agent_id字段"}
                
                return {"valid": True, "data": data}
            
            else:
                return {"valid": False, "error": "不支持的语义格式，请使用JSON格式"}
                
        except json.JSONDecodeError as e:
            return {"valid": False, "error": f"JSON解析错误: {e}"}
        except Exception as e:
            return {"valid": False, "error": f"语义验证错误: {e}"}
    
    async def _strict_create_agent(self, data: dict) -> bool:
        """
        严格的Agent创建：语义字符串→Agent对象转换
        确保想象界描述与实在界对象的一致性
        """
        agent_id = data.get("id")
        prompt = data.get("prompt", "")
        
        # 语义验证：确保Agent ID唯一
        if agent_id in self.agent_system.agents:
            print(f"❌ 语义冲突: Agent ID '{agent_id}' 已存在")
            return False
        
        # 创建实在界Agent对象
        new_agent = Agent(agent_id, prompt, self.message_bus)
        
        # 严格设置连接关系
        input_connections = data.get("input_connections", {})
        output_connections = data.get("output_connections", {})
        activation_channels = data.get("activation_channels", [])
        
        # 验证连接语义的实在界对应性
        for sender_id in input_connections.keys():
            if sender_id not in self.agent_system.agents and sender_id != "system_input":
                print(f"❌ 语义错误: 输入连接指向不存在的Agent '{sender_id}'")
                return False
        
        for output_channel, receiver_ids in output_connections.items():
            for receiver_id in receiver_ids:
                if receiver_id not in self.agent_system.agents and receiver_id != "system_output":
                    print(f"❌ 语义错误: 输出连接指向不存在的Agent '{receiver_id}'")
                    return False
        
        # 应用语义到实在界
        new_agent.input_connections.connections = input_connections
        new_agent.output_connections.connections = output_connections
        new_agent.input_message_keyword = activation_channels
        
        # 注册到系统（实在界操作）
        self.agent_system.register_agent(new_agent)
        
        # 验证转换正确性
        if agent_id in self.agent_system.agents:
            print(f"✅ 语义转换成功: 想象界描述 → 实在界Agent '{agent_id}'")
            print(f"   语义提示词: {prompt[:50]}..." if len(prompt) > 50 else f"   语义提示词: {prompt}")
            print(f"   输入连接: {len(input_connections)} 个")
            print(f"   输出连接: {len(output_connections)} 个")
            print(f"   激活通道: {activation_channels}")
            return True
        else:
            print(f"❌ 语义转换失败: Agent '{agent_id}' 未正确创建")
            return False
    

    
    async def _strict_connect_agents(self, data: dict) -> bool:
        """
        严格的Agent连接：语义描述→实在界连接转换
        确保连接语义的实在界正确性
        """
        connections = data.get("connections", [])
        successful_connections = 0
        
        for conn in connections:
            from_id = conn.get("from_id")
            output_channel = conn.get("output_channel")
            to_id = conn.get("to_id")
            input_channel = conn.get("input_channel")
            
            # 语义完整性验证
            if not all([from_id, output_channel, to_id, input_channel]):
                print(f"❌ 连接语义不完整: {conn}")
                continue
            
            # 实在界存在性验证
            from_agent = self.agent_system.agents.get(from_id)
            to_agent = self.agent_system.agents.get(to_id)
            
            if not from_agent:
                print(f"❌ 语义错误: 源Agent '{from_id}' 不存在")
                continue
            if not to_agent:
                print(f"❌ 语义错误: 目标Agent '{to_id}' 不存在")
                continue
            
            # 执行实在界连接操作
            try:
                # 设置输出连接
                if output_channel not in from_agent.output_connections.connections:
                    from_agent.output_connections.connections[output_channel] = []
                
                # 避免重复连接
                if to_id not in from_agent.output_connections.connections[output_channel]:
                    from_agent.output_connections.connections[output_channel].append(to_id)
                
                # 设置输入连接
                to_agent.input_connections.connections[from_id] = input_channel
                
                successful_connections += 1
                print(f"✅ 语义连接成功: {from_id}.{output_channel} → {to_id}.{input_channel}")
                
            except Exception as e:
                print(f"❌ 连接操作失败: {e}")
        
        print(f"📊 连接统计: {successful_connections}/{len(connections)} 个连接成功建立")
        return successful_connections > 0
    
    async def _strict_set_activation(self, data: dict) -> bool:
        """
        严格的激活设置：语义描述→实在界激活机制转换
        确保激活语义的实在界有效性
        """
        agent_id = data.get("agent_id")
        activation_channels = data.get("activation_channels", [])
        
        # 语义验证
        if not agent_id:
            print("❌ 语义错误: 缺少agent_id字段")
            return False
        
        # 实在界存在性验证
        agent = self.agent_system.agents.get(agent_id)
        if not agent:
            print(f"❌ 语义错误: Agent '{agent_id}' 不存在")
            return False
        
        # 激活通道语义验证
        if not isinstance(activation_channels, list):
            print(f"❌ 语义错误: activation_channels 必须是列表")
            return False
        
        # 执行实在界激活设置
        try:
            agent.input_message_keyword = activation_channels
            
            # 验证设置正确性
            if hasattr(agent, 'input_message_keyword') and agent.input_message_keyword == activation_channels:
                print(f"✅ 激活语义转换成功: Agent '{agent_id}' 激活通道设置为 {activation_channels}")
                return True
            else:
                print(f"❌ 激活语义转换失败: 设置未生效")
                return False
                
        except Exception as e:
            print(f"❌ 激活设置操作失败: {e}")
            return False
    
    # 语义验证器方法
    def _validate_agent_creation_semantics(self, data: dict) -> bool:
        """验证Agent创建语义的完整性"""
        required_fields = ["id", "prompt"]
        for field in required_fields:
            if field not in data:
                print(f"❌ Agent创建语义不完整: 缺少 {field}")
                return False
        return True
    
    def _validate_connection_semantics(self, data: dict) -> bool:
        """验证连接语义的完整性"""
        if "connections" not in data:
            print("❌ 连接语义不完整: 缺少 connections 字段")
            return False
        
        connections = data["connections"]
        if not isinstance(connections, list):
            print("❌ 连接语义错误: connections 必须是列表")
            return False
        
        for conn in connections:
            required = ["from_id", "output_channel", "to_id", "input_channel"]
            for field in required:
                if field not in conn:
                    print(f"❌ 连接语义不完整: 缺少 {field}")
                    return False
        
        return True
    
    def _validate_activation_semantics(self, data: dict) -> bool:
        """验证激活语义的完整性"""
        required_fields = ["agent_id", "activation_channels"]
        for field in required_fields:
            if field not in data:
                print(f"❌ 激活语义不完整: 缺少 {field}")
                return False
        
        if not isinstance(data["activation_channels"], list):
            print("❌ 激活语义错误: activation_channels 必须是列表")
            return False
        
        return True
    
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
        
        # 收集分层系统信息
        system_info = {}
        
        # 1. 系统元信息
        system_info["metadata"] = self.agent_system.get_system_metadata()
        
        # 2. Agent基本信息
        system_info["agents"] = {
            "total_count": len(self.agent_system.agents),
            "agent_ids": self.agent_system.get_agent_ids(),
            "active_agents": len([a for a in self.agent_system.agents.values() 
                                if hasattr(a, 'is_activating') and a.is_activating])
        }
        
        # 3. 关键词统计
        all_keywords = self.agent_system.get_all_keywords()
        system_info["keywords"] = {
            "total_count": len(all_keywords),
            "keyword_list": list(all_keywords)
        }
        
        # 4. 连接拓扑信息
        conn_stats = self.agent_system.get_connection_types()
        system_info["connections"] = {
            "input_connections": len(conn_stats["input_connections"]),
            "output_connections": len(conn_stats["output_connections"]),
            "bidirectional_pairs": len(conn_stats["bidirectional_pairs"]),
            "total_connections": (len(conn_stats["input_connections"]) + 
                                 len(conn_stats["output_connections"]))
        }
        
        # 5. 系统健康度
        uptime = time.time() - self.agent_system.start_time
        system_info["health"] = {
            "uptime_hours": round(uptime / 3600, 2),
            "messages_per_minute": round(self.agent_system.message_count / (uptime / 60), 2) if uptime > 0 else 0,
            "activations_per_minute": round(self.agent_system.activation_count / (uptime / 60), 2) if uptime > 0 else 0,
            "system_status": "running" if self.agent_system.message_bus.is_running else "stopped"
        }
        
        # 6. 最近活动（示例数据）
        system_info["recent_activity"] = {
            "last_5_minutes": {
                "messages": self.agent_system.message_count,  # 简化处理
                "activations": self.agent_system.activation_count
            }
        }
        
        return json.dumps(system_info, ensure_ascii=False, indent=2)


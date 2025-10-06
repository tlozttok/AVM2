"""
Agent创建器系统输出Agent
实现语义字符串与Agent对象的严格转换机制
根据接收到的语义描述创建新的普通Agent
"""

import asyncio
from typing import Optional, Dict, Any
from driver.system_agents import OutputAgent
from driver.driver import Agent, AgentMessage
from driver import async_system

# 日志系统导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import LogLevel, logger


class AgentCreatorOutputAgent(OutputAgent):
    """
    创建普通Agent的系统输出Agent
    实现语义字符串与Agent对象的严格转换机制
    根据接收到的语义描述创建新的普通Agent
    """
    
    def __init__(self, id: str, message_bus=None):
        super().__init__(id, message_bus)
        self.agent_system = async_system.SYMBOLIC_REAL  # 需要访问系统来注册新Agent
        
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
                logger.log_system_agent_operation(
                    "AgentCreatorOutputAgent", 
                    "语义验证失败", 
                    {"error": validation_result['error']}, 
                    LogLevel.ERROR
                )
                return False
            
            # 语义解析阶段
            semantic_data = validation_result["data"]
            
            # 记录Agent创建器操作详情（DEBUG模式）
            operation_type = semantic_data.get("operation")
            # 系统Agent本身的激活记录到核心细节日志
            logger.log_activation_details(
                self.id, 
                f"执行操作: {operation_type}, 数据: {semantic_data}", 
                [{"操作类型": operation_type, "数据": semantic_data}],
                is_system_agent=True
            )
            
            # 执行语义转换
            if operation_type == "create_agent":
                return await self._strict_create_agent(semantic_data)
            elif operation_type == "connect_agents":
                return await self._strict_connect_agents(semantic_data)
            elif operation_type == "set_activation":
                return await self._strict_set_activation(semantic_data)
            elif operation_type == "delete_connection":
                return await self._strict_delete_connection(semantic_data)
            elif operation_type == "change_prompt":
                return await self._strict_change_prompt(semantic_data)
            elif operation_type == "delete_agent":
                return await self._strict_delete_agent(semantic_data)
            # 系统Agent创建应该由专门的系统Agent创建器处理
            else:
                logger.log_system_agent_operation(
                    "AgentCreatorOutputAgent", 
                    "未知操作类型", 
                    {"operation_type": operation_type}, 
                    LogLevel.WARNING
                )
                return False
                
        except Exception as e:
            logger.log_system_agent_operation(
                "AgentCreatorOutputAgent", 
                "语义转换失败", 
                {"error": str(e)}, 
                LogLevel.ERROR
            )
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
                elif operation == "delete_connection":
                    if "connection" not in data:
                        return {"valid": False, "error": "删除连接需要connection字段"}
                elif operation == "change_prompt":
                    if "agent_id" not in data or "new_prompt" not in data:
                        return {"valid": False, "error": "更改提示词需要agent_id和new_prompt字段"}
                elif operation == "delete_agent":
                    if "agent_id" not in data:
                        return {"valid": False, "error": "删除Agent需要agent_id字段"}
                
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
            # 系统Agent的特定操作记录到Agent日志
            logger.log_system_agent_operation(
                "AgentCreatorOutputAgent", 
                "Agent创建", 
                {"agent_id": agent_id, "prompt_length": len(prompt), "connections": len(input_connections) + len(output_connections)}
            )
            # Agent创建记录到核心细节日志
            logger.log_agent_creation(agent_id, data, "AgentCreatorOutputAgent")
            return True
        else:
            logger.log_system_agent_operation(
                "AgentCreatorOutputAgent", 
                "Agent创建失败", 
                {"agent_id": agent_id, "error": "Agent未正确创建"}, 
                LogLevel.ERROR
            )
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
    
    async def _strict_delete_connection(self, data: dict) -> bool:
        """
        严格的连接删除：语义描述→实在界连接删除转换
        确保连接删除语义的实在界正确性
        """
        connection_data = data.get("connection", {})
        
        # 语义完整性验证
        required_fields = ["from_id", "output_channel", "to_id"]
        for field in required_fields:
            if field not in connection_data:
                print(f"❌ 删除连接语义不完整: 缺少 {field}")
                return False
        
        from_id = connection_data["from_id"]
        output_channel = connection_data["output_channel"]
        to_id = connection_data["to_id"]
        
        # 实在界存在性验证
        from_agent = self.agent_system.agents.get(from_id)
        to_agent = self.agent_system.agents.get(to_id)
        
        if not from_agent:
            print(f"❌ 语义错误: 源Agent '{from_id}' 不存在")
            return False
        if not to_agent:
            print(f"❌ 语义错误: 目标Agent '{to_id}' 不存在")
            return False
        
        # 执行实在界连接删除操作
        try:
            # 从源Agent的输出连接中删除
            if output_channel in from_agent.output_connections.connections:
                if to_id in from_agent.output_connections.connections[output_channel]:
                    from_agent.output_connections.connections[output_channel].remove(to_id)
                    print(f"✅ 删除输出连接: {from_id}.{output_channel} → {to_id}")
                    
                    # 如果输出通道为空，删除整个通道
                    if not from_agent.output_connections.connections[output_channel]:
                        del from_agent.output_connections.connections[output_channel]
                else:
                    print(f"⚠️ 连接不存在: {from_id}.{output_channel} → {to_id}")
            else:
                print(f"⚠️ 输出通道不存在: {from_id}.{output_channel}")
            
            # 从目标Agent的输入连接中删除
            if from_id in to_agent.input_connections.connections:
                del to_agent.input_connections.connections[from_id]
                print(f"✅ 删除输入连接: {from_id} → {to_id}")
            else:
                print(f"⚠️ 输入连接不存在: {from_id} → {to_id}")
            
            return True
            
        except Exception as e:
            print(f"❌ 连接删除操作失败: {e}")
            return False
    
    async def _strict_change_prompt(self, data: dict) -> bool:
        """
        严格的提示词更改：语义描述→实在界提示词更新转换
        确保提示词语义的实在界正确性
        """
        agent_id = data.get("agent_id")
        new_prompt = data.get("new_prompt", "")
        
        # 语义验证
        if not agent_id:
            print("❌ 语义错误: 缺少agent_id字段")
            return False
        
        if not new_prompt:
            print("⚠️ 警告: 新提示词为空")
        
        # 实在界存在性验证
        agent = self.agent_system.agents.get(agent_id)
        if not agent:
            print(f"❌ 语义错误: Agent '{agent_id}' 不存在")
            return False
        
        # 执行实在界提示词更新
        try:
            old_prompt = agent.prompt
            agent.prompt = new_prompt
            
            print(f"✅ 提示词语义转换成功: Agent '{agent_id}'")
            print(f"   旧提示词: {old_prompt[:50]}..." if len(old_prompt) > 50 else f"   旧提示词: {old_prompt}")
            print(f"   新提示词: {new_prompt[:50]}..." if len(new_prompt) > 50 else f"   新提示词: {new_prompt}")
            
            return True
            
        except Exception as e:
            print(f"❌ 提示词更改操作失败: {e}")
            return False
    
    async def _strict_delete_agent(self, data: dict) -> bool:
        """
        严格的Agent删除：语义描述→实在界Agent删除转换
        包含回收站机制，将被删除的Agent移动到回收站文件夹
        """
        agent_id = data.get("agent_id")
        
        # 语义验证
        if not agent_id:
            print("❌ 语义错误: 缺少agent_id字段")
            return False
        
        # 实在界存在性验证
        agent = self.agent_system.agents.get(agent_id)
        if not agent:
            print(f"❌ 语义错误: Agent '{agent_id}' 不存在")
            return False
        
        # 检查是否为系统Agent（系统Agent不应被删除）
        if hasattr(agent, 'metadata') and agent.metadata.get('type') in ['InputAgent', 'OutputAgent', 'SystemAgent']:
            print(f"❌ 语义错误: 系统Agent '{agent_id}' 不能被删除")
            return False
        
        # 执行实在界Agent删除操作
        try:
            # 1. 先保存Agent到回收站
            recycle_bin_path = await self._move_agent_to_recycle_bin(agent)
            
            # 2. 从系统中注销Agent
            self.agent_system.unregister_agent(agent_id)
            
            # 3. 清理所有相关的连接
            await self._cleanup_agent_connections(agent_id)
            
            print(f"✅ Agent删除语义转换成功: Agent '{agent_id}' 已删除")
            print(f"   回收站位置: {recycle_bin_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Agent删除操作失败: {e}")
            return False
    
    async def _move_agent_to_recycle_bin(self, agent) -> str:
        """
        将Agent移动到回收站文件夹
        文件名标注删除时间
        """
        import os
        import datetime
        
        # 创建回收站文件夹
        recycle_bin_dir = "Agents/RecycleBin"
        os.makedirs(recycle_bin_dir, exist_ok=True)
        
        # 生成带时间戳的文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{agent.id}_deleted_{timestamp}.yaml"
        recycle_bin_path = os.path.join(recycle_bin_dir, filename)
        
        # 保存Agent到回收站
        agent.sync_to_file(recycle_bin_path)
        
        return recycle_bin_path
    
    async def _cleanup_agent_connections(self, agent_id: str):
        """
        清理与被删除Agent相关的所有连接
        """
        # 清理其他Agent指向该Agent的输出连接
        for other_agent_id, other_agent in self.agent_system.agents.items():
            if other_agent_id == agent_id:
                continue
                
            # 清理输出连接
            for output_channel, receiver_ids in list(other_agent.output_connections.connections.items()):
                if agent_id in receiver_ids:
                    other_agent.output_connections.connections[output_channel].remove(agent_id)
                    print(f"   清理输出连接: {other_agent_id}.{output_channel} → {agent_id}")
                    
                    # 如果输出通道为空，删除整个通道
                    if not other_agent.output_connections.connections[output_channel]:
                        del other_agent.output_connections.connections[output_channel]
            
            # 清理输入连接
            if agent_id in other_agent.input_connections.connections:
                del other_agent.input_connections.connections[agent_id]
                print(f"   清理输入连接: {agent_id} → {other_agent_id}")
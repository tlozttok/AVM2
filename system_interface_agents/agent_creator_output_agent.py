"""
Agent创建器系统输出Agent
实现语义字符串与Agent对象的严格转换机制
根据接收到的语义描述创建新的普通Agent
"""

import asyncio
import json
import os
from typing import Optional, Dict, Any
from driver.system_agents import OutputAgent
from driver.driver import Agent, AgentMessage
from driver import async_system



class AgentCreatorOutputAgent(OutputAgent):
    """
    创建普通Agent的系统输出Agent
    实现语义字符串与Agent对象的严格转换机制
    根据接收到的语义描述创建新的普通Agent
    """
    
    def __init__(self, id: str, message_bus=None):
        super().__init__(id, message_bus)
        self.agent_system = async_system.SYMBOLIC_REAL  # 需要访问系统来注册新Agent
        
    def _check_arg(self, op_type: str, op_arg: Dict[str, Any]) -> bool:
        """检查操作参数是否完整"""
        check_all = lambda keys, dict: all(key in dict for key in keys)
        match op_type:
            case "create_agent":
                return check_all(["agent_id", "system_prompt"], op_arg)
            case "add_connection":
                return check_all(["from_agent_id", "from_keyword", "to_agent_id", "to_keyword"], op_arg)
            case "set_activate":
                return check_all(["agent_id", "activate_keyword"], op_arg)
            case "change_system_prompt":
                return check_all(["agent_id", "system_prompt"], op_arg)
            case "delete_out_connection":
                return check_all(["from_agent_id", "from_keyword", "to_agent_id"], op_arg)
            case "delete_int_connection":
                return check_all(["to_agent_id", "from_agent_id"], op_arg)
            case "delete_agent":
                return check_all(["agent_id"], op_arg)
            case _:
                return False
    
    def _execute(self, op_name: str, op_arg: Dict[str, Any]) -> bool:
        """执行具体的操作"""
        try:
            match op_name:
                case "create_agent":
                    return self._execute_create_agent(op_arg)
                case "add_connection":
                    return self._execute_add_connection(op_arg)
                case "set_activate":
                    return self._execute_set_activate(op_arg)
                case "change_system_prompt":
                    return self._execute_change_system_prompt(op_arg)
                case "delete_out_connection":
                    return self._execute_delete_out_connection(op_arg)
                case "delete_int_connection":
                    return self._execute_delete_int_connection(op_arg)
                case "delete_agent":
                    return self._execute_delete_agent(op_arg)
                case _:
                    self.logger.error(f"未知操作类型: {op_name}")
                    return False
        except Exception as e:
            self.logger.error(f"执行操作 {op_name} 时发生错误: {e}")
            return False
    
    def _execute_create_agent(self, op_arg: Dict[str, Any]) -> bool:
        """执行创建Agent操作"""
        agent_id = op_arg["agent_id"]
        system_prompt = op_arg["system_prompt"]
        
        # 检查Agent是否已存在
        if agent_id in self.agent_system.agents:
            self.logger.warning(f"Agent {agent_id} 已存在，跳过创建")
            return False
        
        # 创建新Agent
        new_agent = Agent(agent_id, system_prompt, self.agent_system.message_bus)
        self.agent_system.register_agent(new_agent)
        
        # 同步到文件
        new_agent.sync_to_file()
        
        self.logger.info(f"成功创建Agent: {agent_id}")
        return True
    
    def _execute_add_connection(self, op_arg: Dict[str, Any]) -> bool:
        """执行添加连接操作"""
        from_agent_id = op_arg["from_agent_id"]
        from_keyword = op_arg["from_keyword"]
        to_agent_id = op_arg["to_agent_id"]
        to_keyword = op_arg["to_keyword"]
        
        # 检查Agent是否存在
        from_agent = self.agent_system.get(from_agent_id)
        to_agent = self.agent_system.get(to_agent_id)
        
        if not from_agent:
            self.logger.error(f"发送者Agent不存在: {from_agent_id}")
            return False
        if not to_agent:
            self.logger.error(f"接收者Agent不存在: {to_agent_id}")
            return False
        
        # 使用新的连接管理方法
        from_agent.add_output_connection(from_keyword, to_agent_id)
        to_agent.add_input_connection(from_agent_id, to_keyword)
        
        self.logger.info(f"成功添加连接: {from_agent_id}.{from_keyword} -> {to_agent_id}.{to_keyword}")
        return True
    
    def _execute_set_activate(self, op_arg: Dict[str, Any]) -> bool:
        """执行设置激活关键词操作"""
        agent_id = op_arg["agent_id"]
        activate_keyword = op_arg["activate_keyword"]
        
        agent = self.agent_system.get(agent_id)
        if not agent:
            self.logger.error(f"Agent不存在: {agent_id}")
            return False
        
        # 使用新的激活关键词管理方法
        agent.set_activation_keywords([activate_keyword])
        
        self.logger.info(f"成功设置Agent {agent_id} 的激活关键词: {activate_keyword}")
        return True
    
    def _execute_change_system_prompt(self, op_arg: Dict[str, Any]) -> bool:
        """执行修改系统提示词操作"""
        agent_id = op_arg["agent_id"]
        system_prompt = op_arg["system_prompt"]
        
        agent = self.agent_system.get(agent_id)
        if not agent:
            self.logger.error(f"Agent不存在: {agent_id}")
            return False
        
        # 使用新的提示词更新方法
        agent.update_prompt(system_prompt)
        
        self.logger.info(f"成功修改Agent {agent_id} 的系统提示词")
        return True
    
    def _execute_delete_out_connection(self, op_arg: Dict[str, Any]) -> bool:
        """执行删除输出连接操作"""
        from_agent_id = op_arg["from_agent_id"]
        from_keyword = op_arg["from_keyword"]
        to_agent_id = op_arg["to_agent_id"]
        
        from_agent = self.agent_system.get(from_agent_id)
        if not from_agent:
            self.logger.error(f"发送者Agent不存在: {from_agent_id}")
            return False
        
        # 使用新的连接管理方法
        success = from_agent.remove_output_connection(from_keyword, to_agent_id)
        
        if success:
            self.logger.info(f"成功删除输出连接: {from_agent_id}.{from_keyword} -> {to_agent_id}")
        else:
            self.logger.warning(f"输出连接不存在: {from_agent_id}.{from_keyword} -> {to_agent_id}")
        
        return success
    
    def _execute_delete_int_connection(self, op_arg: Dict[str, Any]) -> bool:
        """执行删除输入连接操作"""
        to_agent_id = op_arg["to_agent_id"]
        from_agent_id = op_arg["from_agent_id"]
        
        to_agent = self.agent_system.get(to_agent_id)
        if not to_agent:
            self.logger.error(f"接收者Agent不存在: {to_agent_id}")
            return False
        
        # 使用新的连接管理方法
        success = to_agent.remove_input_connection(from_agent_id)
        
        if success:
            self.logger.info(f"成功删除输入连接: {from_agent_id} -> {to_agent_id}")
        else:
            self.logger.warning(f"输入连接不存在: {from_agent_id} -> {to_agent_id}")
        
        return success
    
    def _execute_delete_agent(self, op_arg: Dict[str, Any]) -> bool:
        """执行删除Agent操作"""
        agent_id = op_arg["agent_id"]
        
        if agent_id not in self.agent_system.agents:
            self.logger.warning(f"Agent不存在: {agent_id}")
            return False
        
        # 删除Agent文件
        agent = self.agent_system.agents[agent_id]
        file_path = agent._get_agent_file_path()
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                self.logger.info(f"删除Agent文件: {file_path}")
        except Exception as e:
            self.logger.warning(f"删除Agent文件失败: {e}")
        
        # 从系统中移除Agent
        del self.agent_system.agents[agent_id]
        
        self.logger.info(f"成功删除Agent: {agent_id}")
        return True
    
    async def execute_action(self, message: AgentMessage) -> bool:
        """执行操作的主方法"""
        try:
            # 解析消息内容
            message_content = message.content
            operation_data = json.loads(message_content)
            
            operation_type = operation_data["operation"]
            operation_arg = operation_data["arg"]
            
            # 检查参数
            if not self._check_arg(operation_type, operation_arg):
                self.logger.error(f"参数错误: {operation_data}")
                return False
            
            self.logger.info(f"执行操作: {operation_type}")
            
            # 执行操作
            success = self._execute(operation_type, operation_arg)
            
            if success:
                self.logger.info(f"操作 {operation_type} 执行成功")
                self.agent_system.set_event("SystemChanged")
            else:
                self.logger.error(f"操作 {operation_type} 执行失败")
            
            return success
            
        except json.JSONDecodeError as e:
            self.logger.error(f"消息格式错误: {e}")
            return False
        except KeyError as e:
            self.logger.error(f"消息缺少必要字段: {e}")
            return False
        except Exception as e:
            self.logger.error(f"执行操作时发生未知错误: {e}")
            return False
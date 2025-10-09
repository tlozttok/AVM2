"""
系统接口Agent
- InputAgent: 系统输入Agent，将现实世界转化为字符串消息
- OutputAgent: 系统输出Agent，将字符串消息转化为实际行动
两者都不使用LLM，依赖程序代码实现
"""

from typing import List, Optional, Callable
import asyncio
import json
import yaml
import os
from abc import ABC, abstractmethod
from .driver import Agent, AgentMessage, MessageBus



class InputAgent(Agent):
    """
    系统输入Agent基类
    - 不接受其他Agent的信息
    - 拥有程序化的输入机制和激活机制
    - 将现实世界转化为字符串消息发送到其他Agent
    - 不使用LLM
    """
    
    def __init__(self, id: str, message_bus: MessageBus = None):
        # 不设置prompt，因为不使用LLM
        super().__init__(id, "", message_bus)
        self.is_running = False
        self.input_task = None
        self.logger.info(f"InputAgent {self.id} 初始化完成")
    
    async def receive_message(self, message: AgentMessage, sender_id: str) -> None:
        """异步版本 - 同样忽略消息"""
        self.logger.warning(f"InputAgent {self.id} 收到消息: {message.content}！发送者{sender_id}，发送关键词{message.sender_keyword}，不应该如此。")
    
    @abstractmethod
    async def collect_input(self) -> Optional[str]:
        """
        抽象方法：收集现实世界输入
        子类必须实现此方法来获取输入数据
        返回: 输入数据的字符串表示，如果无输入则返回None
        """
        pass
    
    @abstractmethod
    def should_activate(self, input_data: str) -> bool:
        """
        抽象方法：判断是否应该激活
        子类必须实现此方法来决定何时发送消息
        返回: 是否应该发送消息
        """
        pass
    
    @abstractmethod
    def format_message(self, input_data: str) -> str:
        """
        抽象方法：格式化消息
        子类必须实现此方法来将输入数据格式化为消息
        返回: 格式化后的消息字符串
        """
        pass
    
    async def input_loop(self):
        """输入循环 - 持续收集和处理输入"""
        self.is_running = True
        self.logger.info("启动输入循环")
        while self.is_running:
            # 收集输入
            input_data = await self.collect_input()
            self.logger.debug(f"收到输入: {input_data}")
                
            if input_data and self.should_activate(input_data):
                # 格式化消息
                message_content = self.format_message(input_data)
                
                self.logger.debug(f"发送消息: {message_content}")    
                # 发送消息到所有输出连接
                await self.send_message(message_content)
                    
            # 短暂休眠避免过度占用CPU
            await asyncio.sleep(0.1)    
                
    
    async def start_input(self):
        """启动输入收集"""
        self.input_task = asyncio.create_task(self.input_loop())
        self.logger.info(f"InputAgent {self.id} 已启动")
    
    async def stop_input(self):
        """停止输入收集"""
        self.is_running = False
        if self.input_task:
            self.input_task.cancel()
            try:
                await self.input_task
            except asyncio.CancelledError:
                pass
        self.logger.info(f"InputAgent {self.id} 已停止")
    
    # 重写LLM相关方法为空实现
    
    async def _activate(self):
        """输入Agent不使用LLM激活"""
        pass
    
    def sync_to_file(self, file_path: str = None) -> None:
        """
        系统输入Agent的持久化
        包含输入Agent特有的属性
        """
        self.logger.info(f"正在将InputAgent '{self.id}' 保存到文件: {file_path}")
        if file_path is None:
            file_path = f"{self.id}.{format}"
        
        # 构建输入Agent数据
        agent_data = {
            "id": self.id,
            "input_connections": self.input_connections.connections,
            "output_connections": self.output_connections.connections,
            "input_message_keyword": self.input_message_keyword,
            "metadata": {
                "type": "InputAgent",
            }
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(agent_data, f, allow_unicode=True, indent=2, sort_keys=False)
            
            self.logger.info(f"InputAgent '{self.id}' 已保存到文件: {file_path}")
            
        except Exception as e:
            self.logger.warning(f"保存InputAgent '{self.id}' 到文件失败: {e}")
            pass
            
    def sync_from_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        从文件加载系统输入Agent状态
        支持YAML和JSON格式
        """
        if file_path is None:
            file_path = f"{self.id}.{format}"
        
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}。忘记创建该InputAgent的文件了吗？")
            return
        
        try:
            # 根据文件扩展名确定格式
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    agent_data = yaml.safe_load(f)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
            else:
                # 默认尝试YAML，然后JSON
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        agent_data = yaml.safe_load(f)
                except:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        agent_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(agent_data, dict) or "id" not in agent_data:
                self.logger.error(f"无效的InputAgent数据格式: {file_path}")
                raise ValueError("无效的InputAgent数据格式")
            
            # 更新InputAgent状态
            self.id = agent_data.get("id", self.id)
            
            # 更新连接
            input_connections = agent_data.get("input_connections", None)
            if isinstance(input_connections, dict):
                self.input_connections.connections = input_connections
            
            output_connections = agent_data.get("output_connections", None)
            if isinstance(output_connections, dict):
                self.output_connections.connections = output_connections
            
            # 更新激活关键词
            input_message_keyword = agent_data.get("input_message_keyword", None)
            if isinstance(input_message_keyword, list):
                self.input_message_keyword = input_message_keyword
            
            self.logger.info(f"InputAgent '{self.id}' 已从文件加载: {file_path}")
            
        except Exception as e:
            if file_path or self.id!="":
                self.logger.warning(f"InputAgent {self.id} 从文件加载Agent失败: {e}")
            else:
                self.logger.error(f"InputAgent无法从文件中初始化！")


class OutputAgent(Agent):
    """
    系统输出Agent基类
    - 接受其他Agent的消息
    - 通过程序处理消息，将其转化为实际行动
    - 不使用LLM
    """
    
    def __init__(self, id: str, message_bus: MessageBus = None):
        # 不设置prompt，因为不使用LLM
        super().__init__(id, "", message_bus)
        self.logger.info(f"OutputAgent {self.id} 初始化完成")
    
    @abstractmethod
    async def execute_action(self, message: AgentMessage) -> bool:
        """
        抽象方法：执行实际行动
        子类必须实现此方法来将消息转化为实际行动
        返回: 执行是否成功
        """
        pass
    
    
    async def receive_message(self, message: AgentMessage, sender_id: str) -> None:
        """异步接收消息并执行实际行动"""
        self.logger.info(f"{self.id} 接收到来自{sender_id} 的消息")
        input_channel = self.input_connections.get_keyword(sender_id)
        if input_channel:
            message.receiver_keyword = input_channel
            self.logger.debug(f"设置接收者关键词: {input_channel}")

        # 执行实际行动
        self.logger.debug(f"开始执行行动，消息内容: {message.content}")
        success = await self.execute_action(message)
        
        if success:
            self.logger.info(f"OutputAgent {self.id} 成功执行行动")
        else:
            self.logger.warning(f"OutputAgent {self.id} 执行行动失败")

    
    async def _activate(self):
        """输出Agent不使用LLM激活"""
        pass
    
    async def send_message(self, raw_content: str):
        """输出Agent通常不发送消息，但可以用于调试"""
        #用日志
        pass
    
    def sync_to_file(self, file_path: str = None) -> None:
        """
        系统输出Agent的持久化
        包含输出Agent特有的属性
        """
        self.logger.info(f"正在将OutputAgent '{self.id}' 保存到文件: {file_path}")
        if file_path is None:
            file_path = f"{self.id}.{format}"
        
        # 构建输出Agent数据
        agent_data = {
            "id": self.id,
            "input_connections": self.input_connections.connections,
            "output_connections": self.output_connections.connections,
            "input_message_keyword": self.input_message_keyword,
            "metadata": {
                "type": "OutputAgent",
            }
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(agent_data, f, allow_unicode=True, indent=2, sort_keys=False)
            
            self.logger.info(f"OutputAgent '{self.id}' 已保存到文件: {file_path}")
            
        except Exception as e:
            self.logger.warning(f"保存OutputAgent '{self.id}' 到文件失败: {e}")
    
    def sync_from_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        从文件加载系统输出Agent状态
        支持YAML和JSON格式
        """
        if file_path is None:
            file_path = f"{self.id}.{format}"
        
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}。忘记创建该OutputAgent的文件了吗？")
            return
        
        try:
            # 根据文件扩展名确定格式
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    agent_data = yaml.safe_load(f)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
            else:
                # 默认尝试YAML，然后JSON
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        agent_data = yaml.safe_load(f)
                except:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        agent_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(agent_data, dict) or "id" not in agent_data:
                self.logger.error(f"无效的OutputAgent数据格式: {file_path}")
                raise ValueError("无效的OutputAgent数据格式")
            
            # 更新OutputAgent状态
            self.id = agent_data.get("id", self.id)
            
            # 更新连接
            input_connections = agent_data.get("input_connections", None)
            if isinstance(input_connections, dict):
                self.input_connections.connections = input_connections
            
            output_connections = agent_data.get("output_connections", None)
            if isinstance(output_connections, dict):
                self.output_connections.connections = output_connections
            
            # 更新激活关键词
            input_message_keyword = agent_data.get("input_message_keyword", None)
            if isinstance(input_message_keyword, list):
                self.input_message_keyword = input_message_keyword
            
            self.logger.info(f"OutputAgent '{self.id}' 已从文件加载: {file_path}")
            
        except Exception as e:
            if file_path or self.id!="":
                self.logger.warning(f"OutputAgent {self.id} 从文件加载Agent失败: {e}")
            else:
                self.logger.error(f"OutputAgent无法从文件中初始化！")
        
        
class IOAgent(Agent):
    """
    InputAgent和OutputAgent的结合版本（抽象基类）
    提供受控输入功能：接收特定格式的消息，进行查询或操作，然后返回结果
    子类必须实现具体的查询处理方法
    """
    
    def __init__(self, id: str, agent_system, prompt: str = "", message_bus: MessageBus = None):
        super().__init__(id, prompt, message_bus)
        self.agent_system = agent_system
        self.query_handlers = {}
        self.logger.info(f"IOAgent {self.id} 初始化完成")
    
    @abstractmethod
    def _process_query(self, query_content: AgentMessage) -> str:
        """
        抽象方法：处理查询内容并返回响应
        子类必须实现此方法来处理具体的查询逻辑
        """
        pass
    
    async def receive_message(self, message: AgentMessage, sender_id: str) -> None:
        """异步接收消息并处理查询"""
        self.logger.info(f"{self.id} 接收到来自{sender_id} 的消息")
        input_channel = self.input_connections.get_keyword(sender_id)
        if input_channel:
            message.receiver_keyword = input_channel
            self.logger.debug(f"设置接收者关键词: {input_channel}")
        
        # 处理查询并生成响应
        self.logger.debug(f"开始处理查询，消息内容: {message.content}")
        response = await self._process_query(message)
        
        # 发送响应
        if response:
            self.logger.debug(f"发送响应: {response}")
            await self.send_message(response)
        else:
            self.logger.warning(f"IOAgent {self.id} 处理查询后未生成响应")
    
    # 重写激活方法，使用查询处理逻辑
    async def _activate(self):
        pass
    
    def sync_to_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        IOAgent的持久化
        包含IOAgent特有的属性
        """
        self.logger.info(f"正在将IOAgent '{self.id}' 保存到文件: {file_path}")
        if file_path is None:
            file_path = f"{self.id}.{format}"
        
        # 构建IOAgent数据
        agent_data = {
            "id": self.id,
            "prompt": self.prompt,
            "input_connections": self.input_connections.connections,
            "output_connections": self.output_connections.connections,
            "input_message_keyword": self.input_message_keyword,
            "metadata": {
                "type": "IOAgent",
            }
        }
        
        try:
            if format.lower() == "yaml":
                with open(file_path, 'w', encoding='utf-8') as f:
                    yaml.dump(agent_data, f, allow_unicode=True, indent=2, sort_keys=False)
            elif format.lower() == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(agent_data, f, ensure_ascii=False, indent=2)
            else:
                raise ValueError(f"不支持的格式: {format}")
            
            self.logger.info(f"IOAgent '{self.id}' 已保存到文件: {file_path}")
            
        except Exception as e:
            self.logger.warning(f"保存IOAgent '{self.id}' 到文件失败: {e}")
    
    def sync_from_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        从文件加载IOAgent状态
        支持YAML和JSON格式
        """
        if file_path is None:
            file_path = f"{self.id}.{format}"
        
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}。忘记创建该IOAgent的文件了吗？")
            return
        
        try:
            # 根据文件扩展名确定格式
            if file_path.endswith('.yaml') or file_path.endswith('.yml'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    agent_data = yaml.safe_load(f)
            elif file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    agent_data = json.load(f)
            else:
                # 默认尝试YAML，然后JSON
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        agent_data = yaml.safe_load(f)
                except:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        agent_data = json.load(f)
            
            # 验证数据格式
            if not isinstance(agent_data, dict) or "id" not in agent_data:
                self.logger.error(f"无效的IOAgent数据格式: {file_path}")
                raise ValueError("无效的IOAgent数据格式")
            
            # 更新IOAgent状态
            self.id = agent_data.get("id", self.id)
            self.prompt = agent_data.get("prompt", self.prompt)
            
            # 更新连接
            input_connections = agent_data.get("input_connections", None)
            if isinstance(input_connections, dict):
                self.input_connections.connections = input_connections
            
            output_connections = agent_data.get("output_connections", None)
            if isinstance(output_connections, dict):
                self.output_connections.connections = output_connections
            
            # 更新激活关键词
            input_message_keyword = agent_data.get("input_message_keyword", None)
            if isinstance(input_message_keyword, list):
                self.input_message_keyword = input_message_keyword
            
            self.logger.info(f"IOAgent '{self.id}' 已从文件加载: {file_path}")
            
        except Exception as e:
            if file_path or self.id!="":
                self.logger.warning(f"IOAgent {self.id} 从文件加载Agent失败: {e}")
            else:
                self.logger.error(f"IOAgent无法从文件中初始化！")

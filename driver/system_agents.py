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
    
    def receive_message(self, message: AgentMessage, sender_id: str) -> None:
        """输入Agent不接受其他Agent的消息"""
        # 可以记录日志，但不处理消息
        print(f"InputAgent {self.id} 收到消息但忽略: {message.content}")
    
    async def receive_message_async(self, message: AgentMessage, sender_id: str) -> None:
        """异步版本 - 同样忽略消息"""
        print(f"InputAgent {self.id} 收到消息但忽略: {message.content}")
    
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
        while self.is_running:
            try:
                # 收集输入
                input_data = await self.collect_input()
                
                if input_data and self.should_activate(input_data):
                    # 格式化消息
                    message_content = self.format_message(input_data)
                    
                    # 发送消息到所有输出连接
                    await self.send_message_async(message_content)
                    
                # 短暂休眠避免过度占用CPU
                await asyncio.sleep(0.1)
                
            except Exception as e:
                print(f"InputAgent {self.id} 输入循环错误: {e}")
                await asyncio.sleep(1)  # 错误后等待更长时间
    
    async def start_input(self):
        """启动输入收集"""
        self.input_task = asyncio.create_task(self.input_loop())
        print(f"InputAgent {self.id} 已启动")
    
    async def stop_input(self):
        """停止输入收集"""
        self.is_running = False
        if self.input_task:
            self.input_task.cancel()
            try:
                await self.input_task
            except asyncio.CancelledError:
                pass
        print(f"InputAgent {self.id} 已停止")
    
    # 重写LLM相关方法为空实现
    def activate(self):
        """输入Agent不使用LLM激活"""
        pass
    
    async def activate_async(self):
        """输入Agent不使用LLM激活"""
        pass
    
    def sync_to_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        系统输入Agent的持久化
        包含输入Agent特有的属性
        """
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
                "version": "1.0",
                "is_running": self.is_running
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
            
            print(f"✅ InputAgent '{self.id}' 已保存到文件: {file_path}")
            
        except Exception as e:
            print(f"❌ 保存InputAgent '{self.id}' 到文件失败: {e}")


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
    
    @abstractmethod
    async def execute_action(self, message: AgentMessage) -> bool:
        """
        抽象方法：执行实际行动
        子类必须实现此方法来将消息转化为实际行动
        返回: 执行是否成功
        """
        pass
    
    def receive_message(self, message: AgentMessage, sender_id: str) -> None:
        """同步接收消息 - 转发到异步处理"""
        asyncio.create_task(self.receive_message_async(message, sender_id))
    
    async def receive_message_async(self, message: AgentMessage, sender_id: str) -> None:
        """异步接收消息并执行实际行动"""
        input_channel = self.input_connections.get(sender_id)
        if input_channel:
            message.receiver_keyword = input_channel
        
        # 执行实际行动
        success = await self.execute_action(message)
        
        if success:
            print(f"OutputAgent {self.id} 成功执行动作: {message.content}")
        else:
            print(f"OutputAgent {self.id} 执行动作失败: {message.content}")
    
    # 重写LLM相关方法为空实现
    def activate(self):
        """输出Agent不使用LLM激活"""
        pass
    
    async def activate_async(self):
        """输出Agent不使用LLM激活"""
        pass
    
    async def send_message_async(self, raw_content: str):
        """输出Agent通常不发送消息，但可以用于调试"""
        print(f"OutputAgent {self.id} 发送调试消息: {raw_content}")
    
    def send_message(self, raw_content: str):
        """同步版本"""
        asyncio.create_task(self.send_message_async(raw_content))
    
    def sync_to_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        系统输出Agent的持久化
        包含输出Agent特有的属性
        """
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
                "version": "1.0"
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
            
            print(f"✅ OutputAgent '{self.id}' 已保存到文件: {file_path}")
            
        except Exception as e:
            print(f"❌ 保存OutputAgent '{self.id}' 到文件失败: {e}")
        
        
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
    
    @abstractmethod
    def _process_query(self, query_content: str) -> str:
        """
        抽象方法：处理查询内容并返回响应
        子类必须实现此方法来处理具体的查询逻辑
        """
        pass
    
    async def receive_message_async(self, message: AgentMessage, sender_id: str) -> None:
        """异步接收消息并处理查询"""
        input_channel = self.input_connections.get(sender_id)
        if input_channel:
            message.receiver_keyword = input_channel
        
        # 处理查询并生成响应
        response = await self._process_query(message.content)
        
        # 发送响应
        if response:
            await self.send_message_async(response)
    
    # 重写激活方法，使用查询处理逻辑
    async def activate_async(self):
        """IOAgent的激活逻辑 - 处理输入消息并返回查询结果"""
        if not self.input_message_cache:
            return
        
        # 处理所有输入消息
        for message in self.input_message_cache:
            response = await self._process_query(message.content)
            if response:
                await self.send_message_async(response)
        
        # 清空输入缓存
        self.input_message_cache = []

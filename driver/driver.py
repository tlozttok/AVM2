




import json
import random
import re
import os
import asyncio
from typing import List, Tuple, Dict
import uuid
from uuid import UUID
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from dotenv import load_dotenv
from utils.logger import Loggable


# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = AsyncOpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL')
)

MODEL_NAME = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')


class MessageBus:
    
    
    def __init__(self):
        self.agents: Dict[UUID, Agent] = {}
        
        
    def register_agent(self, agent):
        self.agents[agent.id] = agent
        
    def unregister_agent(self, agent_id: UUID):
        if agent_id in self.agents:
            del self.agents[agent_id]
            
    async def send_message(self, message: str, receiver_id: UUID, sender_id: UUID):
        if receiver_id in self.agents:
            await self.agents[receiver_id].receive_message(message, sender_id)


class AgentSystem:
    
    
    def __init__(self):
        self.agents: Dict[UUID, Agent] = {}
        self.message_bus = MessageBus()
        self.explore_agent=[]
        self.io_agents=[]
        
        
    def add_agent(self, agent):
        self.agents[agent.id] = agent
        self.message_bus.register_agent(agent)
        agent.message_bus = self.message_bus
        agent.system = self
    
    def add_io_agent(self, agent):
        self.add_agent(agent)
        self.io_agents.append(agent)
        
    async def start_all_input_agents(self):
        """启动所有 InputAgent"""
        for agent in self.io_agents:
            if isinstance(agent, InputAgent):
                await agent.start()
                
    async def stop_all_input_agents(self):
        """停止所有 InputAgent"""
        for agent in self.io_agents:
            if isinstance(agent, InputAgent):
                await agent.stop()
        
    def remove_agent(self, agent_id: UUID):
        if agent_id in self.agents:
            self.message_bus.unregister_agent(agent_id)
            del self.agents[agent_id]
        if agent_id in self.io_agents:
            self.io_agents.remove(agent_id)
            
    def get_agent(self, agent_id: UUID):
        return self.agents.get(agent_id)
    
    def add_explore_agent(self, agent:UUID):
        self.explore_agent.append(agent)

    def stop_explore_agent(self, agent:UUID):
        self.explore_agent.remove(agent)
    
    def seek_agent(self, keyword:str):
        return random.choice(self.explore_agent)


class Agent(Loggable):
    """
    Agent类 - 不可继承的代理实例
    所有Agent行为由输入和LLM决定，不应通过继承扩展
    """
    
    def __init__(self):
        super().__init__()
        # 防止继承的机制
        if type(self) != Agent:
            raise TypeError("Agent类不可继承，请通过输入和LLM配置Agent行为")
            
        self.id:UUID=uuid.uuid4()
        self.state:str=""
        self.input_connection:List[Tuple[UUID, str]]=[]
        self.output_connection:List[Tuple[str, UUID]]=[]
        self.input_cache:List[Tuple[str,str]]=[]
        self.message_bus=None
        self.system=None
        self.pre_prompt=""
        
        self.set_log_name(str(self.id))
        
        self.logger.info(f"Agent实例已创建，ID: {self.id}")
        
        
    async def receive_message(self, message:str, sender:UUID):
        self.logger.debug(f"收到来自 {sender} 的消息: {message}")
        keyword=list(filter(lambda x:x[0]==sender, self.input_connection))
        if keyword:
            keyword=keyword[0][1]
        else:
            keyword=str(sender)
        self.input_cache.append((keyword, message))
        self.logger.debug(f"输入缓存大小: {len(self.input_cache)}")
        if self.should_activate():
            await self.activate()
            
    def should_activate(self):
        return len(self.input_cache)>0
        
    async def send_message(self, message:str, keyword:str):
        self.logger.debug(f"发送消息到关键字 '{keyword}': {message}")
        uids=list(filter(lambda x:x[0]==keyword, self.output_connection))
        if uids:
            uids=list(map(lambda x:x[1], uids))
        
        self.logger.debug(f"找到 {len(uids)} 个接收者")
        for uid in uids:
            await self.message_bus.send_message(message, uid, self.id)
            
    def delete_input_connection(self, keyword:str):
        deleted_connections=list(filter(lambda x:x[1]==keyword, self.input_connection))
        self.input_connection=list(filter(lambda x:x[1]!=keyword, self.input_connection))
        for id, _ in deleted_connections:
            self.system.get_agent(id).delete_output_connection(self.id)
        
    def delete_output_connection(self, id:UUID):
        self.output_connection=list(filter(lambda x:x[1]!=id, self.output_connection))
        
    def set_input_connection(self, id:UUID, keyword:str):
        self.input_connection.append((id, keyword))
    
    def explore(self):
        self.logger.info(f"开始探索模式，允许其他Agent发现")
        self.system.add_explore_agent(self.id)
        
    def stop_explore(self):
        self.logger.info(f"停止探索模式")
        self.system.stop_explore_agent(self.id)
    
    def seek(self,keyword):
        self.logger.info(f"寻找关键字 '{keyword}' 的Agent")
        agent=self.system.seek_agent(keyword)
        self.output_connection.append((keyword,agent))
        self.logger.info(f"已建立输出连接到 {agent}")
        
    async def activate(self):
        self.logger.info(f"激活Agent，处理输入缓存")
        system_prompt=self.pre_prompt+\
            "\n<self_state>"+self.state+"</self_state>"+\
            "\n<output_keywords>"+" ".join([x[0] for x in self.output_connection])+"</output_keywords>"
        
        user_prompt="\n".join([f"{input[0]} : {input[1]}" for input in self.input_cache])
        
        self.logger.debug(f"系统提示词长度: {len(system_prompt)}")
        self.logger.debug(f"用户提示词长度: {len(user_prompt)}")
        
        message=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}]
        
        try:
            self.logger.info(f"调用LLM API，模型: {MODEL_NAME}")
            response = await openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=message,
                temperature=0.7
            )
            response_content = response.choices[0].message.content
            
            self.logger.info(f"LLM响应长度: {len(response_content)}")
            
            #如果成功
            self.input_cache=[]
            
            await self.process_response(response_content)
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            # 保留输入缓存以便重试
        
    async def process_response(self, response):
        self.logger.info(f"处理LLM响应")
        pattern = re.compile(r"<(\w+)>(.*?)</\1>")
        matches = pattern.findall(response)
        self.logger.debug(f"找到 {len(matches)} 个标签匹配")
        for keyword, content in matches:
            self.logger.debug(f"处理标签 '{keyword}': {content[:50]}...")
            if keyword == "self_state":
                self.state=content
                self.logger.info(f"更新状态，新状态长度: {len(content)}")
            if  keyword == "signal":
                await self.process_signal(content)
            else:
                await self.send_message(content,keyword)
                
    async def process_signal(self, signals):
        self.logger.info(f"处理信号: {signals}")
        signals=json.loads(signals)
        self.logger.debug(f"解析到 {len(signals)} 个信号")
        for signal in signals:
            signal_type=signal["type"]
            self.logger.info(f"执行信号: {signal_type}")
            if signal_type=="EXPLORE":
                self.explore()
            if signal_type=="STOP_EXPLORE":
                self.stop_explore()
            if signal_type=="SEEK":
                self.seek(signal["keyword"])
            if signal_type=="REJECT_INPUT":
                self.delete_input_connection(signal["keyword"])
            if signal_type=="ACCEPT_INPUT":
                self.set_input_connection(signal["id"],signal["keyword"])


class OutputAgent(Loggable, ABC):
    
    
    def __init__(self):
        super().__init__()
        self.id: UUID = uuid.uuid4()
        self.input_connections:List[UUID]=[]
        self.message_bus = None
        self.system = None
        
        self.logger.info(f"OutputAgent实例已创建，ID: {self.id}")
        
    @abstractmethod
    def explore(self,message:str):
        """
        根据message决定是否探索
        """
        
        pass
    
    async def receive_message(self, message: str, sender: UUID):
        self.logger.debug(f"收到来自 {sender} 的消息: {message}")
        # 执行其他Agent送来的数据
        if sender in  self.input_connections:
            self.logger.debug(f"执行探索和数据输出")
            self.explore(message)
            await self.execute_data(message)
        else:
            self.logger.warning(f"未知发送者 {sender}，忽略消息")
        
    @abstractmethod
    async def execute_data(self, data: str):
        """执行其他Agent送来的数据"""
        pass


class InputAgent(ABC):
    
    
    def __init__(self):
        self.id: UUID = uuid.uuid4()
        self.message_bus = None
        self.output_connections:List[UUID] = []
        self.system = None
        self._running = False
        self._task = None
        
    @abstractmethod
    def seek_signal(self, message: str):
        """根据message决定是否进行seek"""
        pass
        
    async def start(self):
        """启动持续运行的循环"""
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        
    async def stop(self):
        """停止运行循环"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
    async def _run_loop(self):
        """持续运行的循环，收集信息并检测发送时机"""
        while self._running:
            try:
                # 检查是否有数据需要发送
                if self.should_send_data():
                    await self.send_collected_data()
                
                # 等待一段时间再检查
                await asyncio.sleep(self.get_check_interval())
                
            except asyncio.CancelledError:
                break

            
        
    def should_send_data(self) -> bool:
        """检测是否应该发送数据"""
        return self.has_data_to_send()
        
    @abstractmethod
    def has_data_to_send(self) -> bool:
        """检查是否有数据需要发送"""
        pass
        
    def get_check_interval(self) -> float:
        """获取检查间隔（秒）"""
        return 0.1  # 默认100毫秒
        
    async def send_collected_data(self):
        """向所有输出连接发送收集到的字符串化的数据"""
        data = self.collect_data()
        self.seek_signal(data)
        for receiver_id in self.output_connections:
            await self.message_bus.send_message(data, receiver_id, self.id)
            
    @abstractmethod
    def collect_data(self) -> str:
        """收集并字符串化数据"""
        pass
                
                
                

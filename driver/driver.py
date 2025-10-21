




import json
import random
import re
import os
from typing import List, Tuple, Dict
import uuid
from uuid import UUID
from abc import ABC, abstractmethod
from openai import OpenAI
from dotenv import load_dotenv


# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(
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
            
    def send_message(self, message: str, receiver_id: UUID, sender_id: UUID):
        if receiver_id in self.agents:
            self.agents[receiver_id].receive_message(message, sender_id)


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


class Agent:
    
    
    def __init__(self):
        self.id:UUID=uuid.uuid4()
        self.state:str=""
        self.input_connection:List[Tuple[UUID, str]]=[]
        self.output_connection:List[Tuple[str, UUID]]=[]
        self.input_cache:List[Tuple[str,str]]=[]
        self.message_bus=None
        self.system=None
        self.pre_prompt=""
        
        
    def receive_message(self, message:str, sender:UUID):
        keyword=list(filter(lambda x:x[0]==sender, self.input_connection))
        if keyword:
            keyword=keyword[0][1]
        else:
            keyword=str(sender)
        self.input_cache.append((keyword, message))
        if self.should_activate():
            self.activate()
            
    def should_activate(self):
        return len(self.input_cache)>0
        
    def send_message(self, message:str, keyword:str):
        uids=list(filter(lambda x:x[0]==keyword, self.output_connection))
        if uids:
            uids=list(map(lambda x:x[1], uids))
        
        for uid in uids:
            self.message_bus.send_message(message, uid, self.id)
            
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
        self.system.add_explore_agent(self.id)
        
    def stop_explore(self):
        self.system.stop_explore_agent(self.id)
    
    def seek(self,keyword):
        agent=self.system.seek_agent(keyword)
        self.output_connection.append((keyword,agent))
        
    def activate(self):
        system_prompt=self.pre_prompt+\
            "\n<self_state>"+self.state+"</self_state>"+\
            "\n<output_keywords>"+" ".join([x[1] for x in self.output_connection])+"</output_keywords>"
        
        user_prompt="\n".join([f"{input[0]} : {input[1]}" for input in self.input_cache])
        
        
        message=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}]
        
        try:
            response = openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=message,
                temperature=0.7
            )
            response_content = response.choices[0].message.content
            
            #如果成功
            self.input_cache=[]
            
            self.process_response(response_content)
        except Exception as e:
            print(f"LLM调用失败: {e}")
            # 保留输入缓存以便重试
        
    def process_response(self, response):
        pattern = re.compile(r"<(\w+)>(.*?)</\1>")
        matches = pattern.findall(response)
        for keyword, content in matches:
            if keyword == "self_state":
                self.state=content
            if  keyword == "signal":
                self.process_signal(content)
            else:
                self.send_message(content,keyword)
                
    def process_signal(self, signals):
        signals=json.loads(signals)
        for signal in signals:
            signal_type=signal["type"]
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


class OutputAgent(ABC):
    
    
    def __init__(self):
        self.id: UUID = uuid.uuid4()
        self.input_connections:List[UUID]=[]
        self.message_bus = None
        self.system = None
        
    @abstractmethod
    def seek_signal(self,message:str):
        pass
    
    def receive_message(self, message: str, sender: UUID):
        # 执行其他Agent送来的数据
        if sender in  self.input_connections:
            self.seek_signal(message)
            self.execute_data(message)
        
    @abstractmethod
    def execute_data(self, data: str):
        """执行其他Agent送来的数据"""
        pass


class IutputAgent(ABC):
    
    
    def __init__(self):
        self.id: UUID = uuid.uuid4()
        self.message_bus = None
        self.output_connections:List[id] = []
        self.system = None
        
    @abstractmethod
    def explore(self,message: str):
        pass
        
    def send_collected_data(self):
        """在某个时候向所有输出连接发送收集到的字符串化的数据"""
        data = self.collect_data()
        self.explore(data)
        for receiver_id in self.output_connections:
            self.message_bus.send_message(data, receiver_id, self.id)
            
    @abstractmethod
    def collect_data(self) -> str:
        """收集并字符串化数据"""
        pass
                
                
                

from collections import namedtuple
from dataclasses import dataclass
from typing import Callable, Dict, List, Literal, Tuple, Optional
import uuid
from uuid import UUID
from openai import AsyncOpenAI
import asyncio
import os
import json
import yaml
from pathlib import Path

# 日志系统导入
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import Loggable


type Keyword = str



class Context:
        
    class SystemMessage:
        content:str
        
        def __init__(self,state,connect_state):
            self.content = ""
            self.content+="\n"+state
            for connect,state_for_connect in connect_state.items():
                self.content+="\n"+connect+" : "+state_for_connect
            
        
        def __repr__(self):
            return self.content

    
    @classmethod
    def integrate(cls,state:str,connect_state:Dict[str,str],input_messages:List['AgentMessage'])-> List[Dict[str, str]] :
        """集成上下文信息"""
        system_msg = Context.SystemMessage(state,connect_state)
        
        
        
        user_msg = "\n\n".join(input_messages)
        
        #将上下文转换为OpenAI API格式的消息列表
        messages = []
        if system_msg and system_msg.content:
            messages.append({"role": "system", "content": system_msg.content})
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        return messages
        


class AgentMessage:
    """
    Agent间传递的消息
    """
    sender_name: str
    content: str
    
    def __init__(self, sender_name:str, content:str):
        self.sender_keyword = sender_name
        self.content = content
        
    def to_str(self)->str:
        return f"{self.sender_keyword} : {self.content}"
    
    def __repr__(self):
        return f"{self.sender_keyword} : {self.content}"

AgentMessageData=namedtuple("AgentMessageData", ["sender_name", "content"])

@dataclass
class AgentData():
    id: str
    type: str
    input_connections: Dict[str, Keyword]
    output_connections: Dict[Keyword, List[str]]
    input_message_keyword: List[str]
    bg_message_cache: List[Tuple[AgentMessageData,bool]]
    input_message_cache: List[AgentMessageData]
    meta_data: Dict
    
    @property
    def keywords(self) -> Dict[Literal["input_keywords","output_keywords"], List[str]]:
        input_keywords = self.input_connections.values()
        output_keywords = self.output_connections.keys()
        return {"input_keywords": input_keywords, "output_keywords": output_keywords}
    
    

class Agent(Loggable):
    """
    微Agent实体
    """
    
    # TODO:信号机制（将系统的操作能力下放给每个Agent，但是外部输入输出还是使用IO机制
    # 建立输出连接信号、建立输入连接信号检测是否有配对的信号，然后一回合更改一次连接
    # 删除连接信号一回合删除一次连接
    # 更改id信号更改id
    
    def __init__(self, name: str, message_bus: 'MessageBus' = None):
        super().__init__()
        self.uuid=uuid.uuid4()
        self.name = name
        self.state="新建立……无信息"
        self.connect_state:  Dict[UUID, Tuple[str,str]] = {}
        self.input_message_cache: List[AgentMessage] = []
        self.input_check_function:Callable[[List[AgentMessage]],bool] = \
            self.default_input_check_function
        self.output_connection:List[UUID]=[]#这个也要放到上下文里
        self.message_bus = message_bus
        self._env_config = None  # 缓存.env配置
        self._file_path = None  # 缓存文件路径
        self.auto_sync_enabled = True  # 默认启用自动同步
        
    @property
    def data(self) -> AgentData:
        pass
        
    def default_input_check_function(self,inputs:List[AgentMessage])->bool:
        return len(inputs)>0
    
    def sync_to_file(self, file_path: str = None) -> None:
        """
        将Agent状态同步到文件
        使用人类可编辑的格式（YAML或JSON）
        """
        #需要修改
        self.logger.info(f"正在将Agent {self.name}状态同步到文件")
        if file_path is None:
            file_path = self._get_agent_file_path()
        
        # 构建Agent数据
        agent_data = {
            "id": self.name,
            "input_connections": self.input_connections.connections,
            "output_connections": self.output_connections.connections,
            "input_message_keyword": self.input_message_keyword,
            "bg_message_cache": [
                {
                    "sender_keyword": msg.sender_keyword,
                    "content": msg.content,
                    "receiver_keyword": msg.receiver_keyword,
                    "is_unused": is_unused
                }
                for msg, is_unused in self.bg_message_cache
            ],
            "input_message_cache": [
                {
                    "sender_keyword": msg.sender_keyword,
                    "content": msg.content,
                    "receiver_keyword": msg.receiver_keyword
                }
                for msg in self.input_message_cache
            ],
            "metadata": self.meta_data
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                yaml.dump(agent_data, f, allow_unicode=True, indent=2, sort_keys=False)
            self.logger.info(f"Agent '{self.name}' 已保存到文件: {file_path}")
                
            
        except Exception as e:
            self.logger.warning(f"保存Agent '{self.name}' 到文件失败: {e}")
            pass
    
    def _get_agent_file_path(self) -> str:
        """
        计算Agent的存储文件路径
        根据当前项目结构：
        - 普通Agent: Agents/{id}.yaml
        - 系统Agent: Agents/SystemAgents/{id}.yaml
        """
        if self._file_path:
            return self._file_path
            
        # 检查是否是系统Agent
        project_root = Path(__file__).parent.parent
        system_agents_dir = project_root / "Agents" / "SystemAgents"
        
        # 检查SystemAgents目录中是否有该Agent的文件
        system_agent_file = system_agents_dir / f"{self.name}.yaml"
        if system_agent_file.exists():
            self._file_path = str(system_agent_file)
            return self._file_path
        
        # 检查普通Agent目录
        agents_dir = project_root / "Agents"
        agent_file = agents_dir / f"{self.name}.yaml"
        if agent_file.exists():
            self._file_path = str(agent_file)
            return self._file_path
        
        # 如果都不存在，默认使用普通Agent路径
        self._file_path = str(agents_dir / f"{self.name}.yaml")
        return self._file_path
    
    def sync_from_file(self, file_path: str = None) -> None:
        """
        从文件加载Agent状态
        支持YAML和JSON格式
        """
        #需要修改
        
        if file_path is None:
            file_path = self._get_agent_file_path()
        
        if not os.path.exists(file_path):
            self.logger.error(f"文件不存在: {file_path}。忘记创建该Agent的文件了吗？")
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
                self.logger.error(f"无效的Agent数据格式: {file_path}")
                raise ValueError("无效的Agent数据格式")
            
            # 更新Agent状态
            self.name = agent_data.get("id", self.name)
            
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
            
            # 更新消息缓存
            bg_message_cache = agent_data.get("bg_message_cache", None)
            if isinstance(bg_message_cache, list):
                self.bg_message_cache = [
                    (
                        AgentMessage(
                            sender_keyword=msg.get("sender_keyword", "unknow"),
                            content=msg.get("content", "unknow"),
                            receiver_keyword=msg.get("receiver_keyword", "unknow")
                        ),
                        msg.get("is_unused", True)  # 默认为未使用
                    )
                    for msg in bg_message_cache
                ]
            
            input_message_cache = agent_data.get("input_message_cache", None)
            if isinstance(input_message_cache, list):
                self.input_message_cache = [
                    AgentMessage(
                        sender_keyword=msg.get("sender_keyword", "unknow"),
                        content=msg.get("content", "unknow"),
                        receiver_keyword=msg.get("receiver_keyword", "unknow")
                    )
                    for msg in input_message_cache
                ]
            
            # 更新元数据
            metadata = agent_data.get("metadata", None)
            if isinstance(metadata, dict):
                self.meta_data=metadata
            
            # 缓存文件路径
            self._file_path = file_path
            
            self.logger.info(f"Agent '{self.name}' 已从文件加载: {file_path}")
            
        except Exception as e:
            if file_path or self.name!="":
                self.logger.warning(f"Agent {self.name} 从文件加载Agent失败: {e}")
            else:
                self.logger.error(f"Agent无法从文件中初始化！")
    
    def _load_env_config(self) -> dict:
        """从项目根目录的.env文件加载配置"""
        if self._env_config is not None:
            return self._env_config
            
        # 查找项目根目录的.env文件
        project_root = Path(__file__).parent.parent
        env_file = project_root / ".env"
        
        config = {}
        
        if env_file.exists():
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            except Exception as e:
                print(f"❌ 读取.env文件失败: {e}")
        else:
            print(f"⚠️ 未找到.env文件: {env_file}")
        
        self._env_config = config
        return config
    
    def _get_env_value(self, key: str, default: str = None) -> str:
        """获取环境变量值，优先从.env文件读取，其次从系统环境变量读取"""
        config = self._load_env_config()
        
        # 优先从.env文件读取
        if key in config:
            return config[key]
        
        # 其次从系统环境变量读取
        return os.environ.get(key, default)
    
    # Connection Management Methods
    def change_name(self, new_name: str):
        self.name = new_name
    
    def delete_output
    
    
    async def receive_message(self, message: AgentMessage, sender_name:str) -> None:
        """异步接收消息"""
        self.logger.info(f"Agent {self.name} 接受到来自{sender_name}的消息")
        self.logger.debug(f"消息内容：{message}")
        self.input_message_cache.append(message)
        self.logger.debug(f"Agent {self.name}检查是否激活")
        if self.input_check_function(self.input_message_cache):
            self.logger.debug(f"Agent {self.name}激活")
            await self._activate()
            
        
    async def _process_response(self, response: str):
        content=self._prase_content(response)
        
        new_state=content.get("state")
        output=content.get("output")
        connection_state_change=content.get("connection_state_change")
        signals=content.get("signals")
        
        
        self.state=new_state
        for connection_name,connection_state in connection_state_change.items():
            self.connect_state[connection_name]=connection_state
            
        for signal in signals:
            
        for agent in self.output_connection:
            await self.message_bus.send_message(self.name,AgentMessage(self.name,output),agent)
        
    
             
    
    async def _activate(self):
        """异步激活Agent，调用大模型API"""
        self.logger.info(f"Agent {self.name} 正在激活...")
        
        # 在激活前自动同步状态到文件（如果启用）
        if self.auto_sync_enabled:
            self.debug(f"Agent {self.name} 正在自动同步状态到文件...")
            self.sync_to_file()
        
        self.logger.debug(f"Agent {self.name} 构建上下文")
        # 构建上下文
        messages = Context.integrate(
            self.state,
            self.connect_state,
            self.input_message_cache
        )
        
        self.logger.debug(f"Agent {self.name}激活，上下文为：{messages}")
        
        # 清空输入消息缓存
        self.input_message_cache = []
        
            
        try:
            # 初始化异步OpenAI客户端
            
            client = AsyncOpenAI(
                api_key=self._get_env_value("OPENAI_API_KEY"),
                base_url=self._get_env_value("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
            
            # 异步调用大模型API
            response = await client.chat.completions.create(
                model=self._get_env_value("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=messages,
                max_tokens=2048,
                temperature=0.7
            )
            
            # 获取模型响应
            content = response.choices[0].message.content
            
            # 异步发送响应消息
            await self._process_response(content)
            
        except Exception as e:
            print(f"API调用失败: {e}")
            self.logger.critical(f"API调用失败: {e}")
        
        
        
        
        
        
class MessageBus(Loggable):
    """异步消息总线，管理Agent间的消息传递"""
    
    def __init__(self):
        super().__init__()
        self.agents: Dict[str, Agent] = {}
        self.message_queue = asyncio.Queue()
        self.is_running = False
        self.processing_task = None
    
    def register_agent(self, agent: 'Agent'):
        self.logger.info(f"注册Agent: {agent.name}")
        """注册Agent到消息总线"""
        self.agents[agent.name] = agent
    
    async def send_message(self, sender_id: str, message: AgentMessage, receiver_id: str):
        """异步发送消息到目标Agent"""
        self.logger.info(f"{sender_id} 发送消息给 {receiver_id}")
        await self.message_queue.put((sender_id, message, receiver_id))
    
    async def process_messages(self):
        """异步处理消息队列"""
        self.is_running = True
        self.logger.info("开始处理消息队列")
        while self.is_running:
            try:
                sender_id, message, receiver_id = await self.message_queue.get()
                self.logger.debug(f"处理消息: {message}，从{sender_id}发送到{receiver_id}")
                receiver = self.agents.get(receiver_id)
                if receiver:
                    # 异步处理消息接收
                    await receiver.receive_message(message, sender_id)
                else:
                    self.logger.warning(f"未找到接收者: {receiver_id}")
            except asyncio.CancelledError:
                # 任务被取消，正常退出
                print("🔌 消息总线处理循环被取消")
                self.logger.info("消息总线处理循环被取消")
                self.is_running = False
                break        
    
    async def start(self):
        """启动消息总线"""
        self.processing_task = asyncio.create_task(self.process_messages())
        print("消息总线已启动")
        self.logger.info("消息总线已启动")
    
    async def stop(self):
        """停止消息总线"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
        print("🔌 消息总线已停止")
        self.logger.info("消息总线已停止")
        
    
    
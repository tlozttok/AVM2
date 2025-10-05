


from typing import Callable, Dict, List, Tuple, Optional
from openai import AsyncOpenAI
import asyncio
import os
import json
import yaml
from pathlib import Path


type Keyword = str

class UserMessage:
    content:str
    
    def __init__(self):
        self.content = ""
    
    def integrate(self, agent_message:List['AgentMessage']):
        self.content += "\n".join([message.to_str() for message in agent_message])
        

class SystemMessage:
    content:str
    
    def __init__(self):
        self.content = "你是一个Agent系统中的Agent，基本行为是接受其他Agent的信息，根据后面的提示，进行信息处理，输出一个信息。其他Agent的信息会以'{发送端关键词} - {接收端关键词}:{内容}'的格式输入。你的输出会被处理并发送到和你连接的其他Agent，其他Agent也和你一样，不过连接不同。每个连接有两个关键词，发送端的关键词（输出关键词）和接收端的关键词（输入关键词）。你的输出格式应该是“<think>思考过程</think><keyword1>关键词一的输出</keyword1><keyword2>关键词二的输出</keyword>...”。以下是你的输出关键词列表：\n"
        
    def integrate_keywords(self, keywords:List[Keyword]):
        """集成输出关键词列表"""
        if keywords:
            self.content += "\n".join([f"- {keyword}" for keyword in keywords]) + "\n"
    
    def integrate_system_prompt(self, system_prompt:str):
        """集成系统提示词"""
        if system_prompt:
            self.content += f"\n\n以下是你的具体任务和背景信息：\n{system_prompt}"
    
    def integrate(self, agent_message:List['AgentMessage']):
        """集成其他Agent的实时信息"""
        if agent_message:
            self.content += "\n\n以下是其他Agent的实时信息：\n" + "\n".join([message.to_str() for message in agent_message])

class Context:
    content:Tuple[SystemMessage, UserMessage]
    
    def __init__(self, system_message:SystemMessage=None, user_message:UserMessage=None):
        self.content = (system_message, user_message)
        
    def integrate(self, system_prompt:str, bg_messages:List['AgentMessage'], input_messages:List['AgentMessage'], output_keywords:List[Keyword]=None):
        """集成上下文信息"""
        system_msg = SystemMessage()
        
        # 集成输出关键词
        if output_keywords:
            system_msg.integrate_keywords(output_keywords)
        
        # 集成系统提示词
        system_msg.integrate_system_prompt(system_prompt)
        
        # 集成背景消息
        system_msg.integrate(bg_messages)
        
        user_msg = UserMessage()
        user_msg.integrate(input_messages)
        
        self.content = (system_msg, user_msg)
        return self
        
    def to_messages(self) -> List[Dict[str, str]]:
        """将上下文转换为OpenAI API格式的消息列表"""
        messages = []
        if self.content[0] and self.content[0].content:
            messages.append({"role": "system", "content": self.content[0].content})
        if self.content[1] and self.content[1].content:
            messages.append({"role": "user", "content": self.content[1].content})
        return messages
        


class InputConnections:
    """
    输入连接映射：{发送者Agent ID -> 本Agent的输入通道}
    用于通过发送者ID找到对应的输入通道
    """
    connections:Dict[str, str]
    
    def __init__(self):
        self.connections = {}
    
    def get(self, sender_id:str)->Keyword:
        """通过发送者ID获取对应的输入通道"""
        return self.connections.get(sender_id)
    
    @property
    def get_id(self)->List[str]:
        """获取所有连接的发送者ID列表"""
        return list(self.connections.keys())
    
    @property
    def get_keyword(self)->List[Keyword]:
        """获取所有输入通道列表"""
        return list(self.connections.values())
    
class OutputConnections:
    """
    输出连接映射：{输出通道 -> [接收者Agent ID列表]}
    用于通过输出通道找到对应的接收者ID列表
    """
    connections:Dict[str, List[str]]
    
    def __init__(self):
        self.connections = {}
    
    def get(self, output_channel:Keyword)->List[str]:
        """通过输出通道获取对应的接收者ID列表"""
        return self.connections.get(output_channel, [])
    
    @property
    def get_keyword(self)->List[Keyword]:
        """获取所有输出通道列表"""
        return list(self.connections.keys())
    
    @property
    def get_id(self)->List[List[str]]:
        """获取所有接收者ID列表的列表"""
        return list(self.connections.values())

class AgentMessage:
    """
    Agent间传递的消息
    - sender_keyword: 发送者使用的输出通道
    - receiver_keyword: 接收者使用的输入通道
    - content: 消息内容
    """
    sender_keyword: Keyword
    content: str
    receiver_keyword: Keyword
    
    def __init__(self, sender_keyword:Keyword, content:str, receiver_keyword:Keyword=None):
        self.sender_keyword = sender_keyword
        self.content = content
        self.receiver_keyword = receiver_keyword
        
    def to_str(self)->str:
        return f"{self.sender_keyword} - {self.receiver_keyword}: {self.content}"

class Agent:
    """
    微Agent实体
    - input_connections: 输入连接映射（发送者ID -> 输入通道）
    - output_connections: 输出连接映射（输出通道 -> 接收者ID列表）
    - bg_message_cache: 背景消息缓存（非激活通道的消息）
    - input_message_cache: 输入消息缓存（激活通道的消息）
    - input_message_keyword: 激活通道列表（触发Agent激活的通道）
    """
    
    def __init__(self, id: str, prompt: str = "", message_bus: 'MessageBus' = None):
        self.id = id
        self.prompt = prompt
        self.input_connections = InputConnections()
        self.output_connections = OutputConnections()
        self.bg_message_cache:  list[AgentMessage] = []
        self.input_message_cache: list[AgentMessage] = []
        self.input_message_keyword = []
        self.input_check_function:Callable[[List[Tuple[Keyword,Keyword]]],bool] = \
            self.default_input_check_function
        self.message_bus = message_bus
        self.is_activating = False  # 防止重复激活
        self._env_config = None  # 缓存.env配置
        self._file_path = None  # 缓存文件路径
        self.auto_sync_enabled = True  # 默认启用自动同步
    def default_input_check_function(self,keywords:List[Tuple[Keyword,Keyword]])->bool:
        received_keywords = [k[1] for k in keywords]
        return all([k in received_keywords for k in self.input_message_keyword])
    
    def sync_to_file(self, file_path: str = None, format: str = "yaml") -> None:
        """
        将Agent状态同步到文件
        使用人类可编辑的格式（YAML或JSON）
        """
        if file_path is None:
            file_path = self._get_agent_file_path()
        
        # 构建Agent数据
        agent_data = {
            "id": self.id,
            "prompt": self.prompt,
            "input_connections": self.input_connections.connections,
            "output_connections": self.output_connections.connections,
            "input_message_keyword": self.input_message_keyword,
            "bg_message_cache": [
                {
                    "sender_keyword": msg.sender_keyword,
                    "content": msg.content,
                    "receiver_keyword": msg.receiver_keyword
                }
                for msg in self.bg_message_cache
            ],
            "input_message_cache": [
                {
                    "sender_keyword": msg.sender_keyword,
                    "content": msg.content,
                    "receiver_keyword": msg.receiver_keyword
                }
                for msg in self.input_message_cache
            ],
            "metadata": {
                "type": "Agent",
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
            
            print(f"✅ Agent '{self.id}' 已保存到文件: {file_path}")
            
        except Exception as e:
            print(f"❌ 保存Agent '{self.id}' 到文件失败: {e}")
    
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
        system_agent_file = system_agents_dir / f"{self.id}.yaml"
        if system_agent_file.exists():
            self._file_path = str(system_agent_file)
            return self._file_path
        
        # 检查普通Agent目录
        agents_dir = project_root / "Agents"
        agent_file = agents_dir / f"{self.id}.yaml"
        if agent_file.exists():
            self._file_path = str(agent_file)
            return self._file_path
        
        # 如果都不存在，默认使用普通Agent路径
        self._file_path = str(agents_dir / f"{self.id}.yaml")
        return self._file_path
    
    def sync_from_file(self, file_path: str) -> None:
        """
        从文件加载Agent状态
        支持YAML和JSON格式
        """
        if not os.path.exists(file_path):
            print(f"❌ 文件不存在: {file_path}")
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
                raise ValueError("无效的Agent数据格式")
            
            # 更新Agent状态
            self.id = agent_data.get("id", self.id)
            self.prompt = agent_data.get("prompt", self.prompt)
            
            # 更新连接
            input_connections = agent_data.get("input_connections", {})
            if isinstance(input_connections, dict):
                self.input_connections.connections = input_connections
            
            output_connections = agent_data.get("output_connections", {})
            if isinstance(output_connections, dict):
                self.output_connections.connections = output_connections
            
            # 更新激活关键词
            input_message_keyword = agent_data.get("input_message_keyword", [])
            if isinstance(input_message_keyword, list):
                self.input_message_keyword = input_message_keyword
            
            # 更新消息缓存
            bg_message_cache = agent_data.get("bg_message_cache", [])
            if isinstance(bg_message_cache, list):
                self.bg_message_cache = [
                    AgentMessage(
                        sender_keyword=msg.get("sender_keyword", ""),
                        content=msg.get("content", ""),
                        receiver_keyword=msg.get("receiver_keyword")
                    )
                    for msg in bg_message_cache
                ]
            
            input_message_cache = agent_data.get("input_message_cache", [])
            if isinstance(input_message_cache, list):
                self.input_message_cache = [
                    AgentMessage(
                        sender_keyword=msg.get("sender_keyword", ""),
                        content=msg.get("content", ""),
                        receiver_keyword=msg.get("receiver_keyword")
                    )
                    for msg in input_message_cache
                ]
            
            # 缓存文件路径
            self._file_path = file_path
            
            print(f"✅ Agent '{self.id}' 已从文件加载: {file_path}")
            
        except Exception as e:
            print(f"❌ 从文件加载Agent失败: {e}")
    
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
                print(f"✅ 从文件加载环境配置: {env_file}")
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
    

    
    def receive_message(self, message: AgentMessage, sender_id:str) -> None:
        """同步接收消息（用于向后兼容）"""
        # 在异步环境中，应该使用receive_message_async
        asyncio.create_task(self.receive_message_async(message, sender_id))
    
    async def receive_message_async(self, message: AgentMessage, sender_id:str) -> None:
        """异步接收消息"""
        input_channel = self.input_connections.get(sender_id)
        if input_channel:
            message.receiver_keyword = input_channel
        if input_channel in self.input_message_keyword:
            self.input_message_cache.append(message)
        else:
            self.bg_message_cache.append(message)
            
        # 检查是否应该激活
        if self.input_check_function([(msg.sender_keyword, msg.receiver_keyword) for msg in self.input_message_cache]):
            if not self.is_activating:
                self.is_activating = True
                await self.activate_async()
                self.is_activating = False
        
            
    async def send_message_async(self, raw_content: str):
        """
        异步发送消息：
        1. 从原始内容中提取不同输出通道对应的消息
        2. 通过output_connections获取对应的接收者ID列表
        3. 通过MessageBus异步发送消息
        """
        # 解析原始内容，提取输出通道对应的消息
        channel_messages = self._parse_keyword_messages(raw_content)
        
        # 为每个输出通道消息创建AgentMessage并发送
        for output_channel, content in channel_messages.items():
            # 获取该输出通道对应的所有接收者ID
            receiver_ids = self.output_connections.get(output_channel)
            
            if receiver_ids:
                for receiver_id in receiver_ids:
                    # 创建消息
                    message = AgentMessage(
                        sender_keyword=output_channel,
                        content=content,
                        receiver_keyword=None  # 接收者会在receive_message中设置
                    )
                    
                    # 通过MessageBus异步发送消息
                    if self.message_bus:
                        await self.message_bus.send_message(self.id, message, receiver_id)
                    else:
                        print(f"警告: Agent {self.id} 未连接到消息总线，无法发送消息")
    
    def send_message(self, raw_content: str):
        """同步发送消息（用于向后兼容）"""
        # 在异步环境中，应该使用send_message_async
        asyncio.create_task(self.send_message_async(raw_content))
    
    def _parse_keyword_messages(self, raw_content: str) -> Dict[Keyword, str]:
        """
        解析原始内容，提取格式为：
        <think>思考过程</think><keyword1>内容1</keyword1><keyword2>内容2</keyword2>
        """
        keyword_messages = {}
        
        # 首先提取think部分（如果有）
        think_start = raw_content.find("<think>")
        think_end = raw_content.find("</think>")
        
        if think_start != -1 and think_end != -1:
            # 移除think部分，只处理关键词部分
            content_after_think = raw_content[think_end + 8:]  # 8是</think>的长度
        else:
            content_after_think = raw_content
        
        # 解析所有关键词标签
        import re
        pattern = r'<([\w\u4e00-\u9fff]+)>(.*?)</\1>'
        matches = re.findall(pattern, content_after_think, re.DOTALL)
        
        for keyword, content in matches:
            # 检查该关键词是否在output_connections中
            if keyword in self.output_connections.get_keyword:
                keyword_messages[keyword] = content.strip()
        
        return keyword_messages
            
    
    def reduce(self):
        deduplicated_messages = {}
        for message in self.bg_message_cache:
            deduplicated_messages[(message.sender_keyword,message.receiver_keyword)] = message
        self.bg_message_cache = list(deduplicated_messages.values())
    
    async def activate_async(self):
        """异步激活Agent，调用大模型API"""
        
        self.reduce()
        
        # 在激活前自动同步状态到文件（如果启用）
        if self.auto_sync_enabled:
            try:
                self.sync_to_file()
                print(f"📝 Agent '{self.id}' 状态已实时同步到文件")
            except Exception as e:
                print(f"⚠️ Agent '{self.id}' 文件同步失败: {e}")
        
        # 构建上下文
        output_keywords = self.output_connections.get_keyword if hasattr(self.output_connections, 'get_keyword') else []
        context = Context().integrate(
            self.prompt, 
            self.bg_message_cache, 
            self.input_message_cache,
            output_keywords
        )
        messages = context.to_messages()
        
        self.input_message_cache=[]
        
        if not messages:
            return
            
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
            await self.send_message_async(content)
            
        except Exception as e:
            print(f"API调用失败: {e}")
    
    def activate(self):
        """同步激活Agent（用于向后兼容）"""
        # 在异步环境中，应该使用activate_async
        asyncio.create_task(self.activate_async())
        
        
        
        
        
        
class MessageBus:
    """异步消息总线，管理Agent间的消息传递"""
    
    def __init__(self):
        self.agents: Dict[str, Agent] = {}
        self.message_queue = asyncio.Queue()
        self.is_running = False
        self.processing_task = None
    
    def register_agent(self, agent: 'Agent'):
        """注册Agent到消息总线"""
        self.agents[agent.id] = agent
    
    async def send_message(self, sender_id: str, message: AgentMessage, receiver_id: str):
        """异步发送消息到目标Agent"""
        await self.message_queue.put((sender_id, message, receiver_id))
    
    async def process_messages(self):
        """异步处理消息队列"""
        self.is_running = True
        while self.is_running:
            try:
                sender_id, message, receiver_id = await self.message_queue.get()
                
                receiver = self.agents.get(receiver_id)
                if receiver:
                    # 异步处理消息接收
                    await receiver.receive_message_async(message, sender_id)
                else:
                    print(f"警告: 未找到接收者Agent: {receiver_id}")
            except asyncio.CancelledError:
                # 任务被取消，正常退出
                print("🔌 消息总线处理循环被取消")
                break        
            except Exception as e:
                print(f"处理消息时出错: {e}")
    
    async def start(self):
        """启动消息总线"""
        self.processing_task = asyncio.create_task(self.process_messages())
        print("消息总线已启动")
    
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
        
    
    
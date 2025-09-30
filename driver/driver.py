


from typing import Callable, Dict, List, Tuple, Optional
from openai import AsyncOpenAI
import asyncio
import os


type Keyword = str

class UserMessage:
    content:str
    
    def __init__(self):
        self.content = ""
    
    def integrate(self, agent_message:List['AgentMessage']):
        self.content += " ".join([message.content for message in agent_message])
        

class SystemMessage:
    content:str
    
    def __init__(self):
        self.content = "你是一个Agent系统中的Agent，基本行为是接受其他Agent的信息，根据后面的提示，进行信息处理，输出一个信息。你的输出会被处理并发送到和你连接的其他Agent，其他Agent也和你一样，不过连接不同。每个连接有两个关键词，发送端的关键词（输出关键词）和接收端的关键词（输入关键词）。你的输出格式应该是“<think>思考过程</think><keyword1>关键词一的输出</keyword1><keyword2>关键词二的输出</keyword>...”。以下是你的输出关键词列表：\n"
        
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
            self.content += "\n\n以下是其他Agent的实时信息：\n" + "\n".join([message.content for message in agent_message])

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
        return f"{self.sender_keyword} -> {self.receiver_keyword}: {self.content}"

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
    def default_input_check_function(self,keywords:List[Tuple[Keyword,Keyword]])->bool:
        received_keywords = [k[1] for k in keywords]
        return all([k in received_keywords for k in self.input_message_keyword])
    
    def sync_to_file(self)->None:
        #  TODO: Implement
        pass
    
    def sync_from_file(self)->None:
        #  TODO: Implement
        pass
    
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
        pattern = r'<(\w+)>(.*?)</\1>'
        matches = re.findall(pattern, content_after_think)
        
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
                api_key=os.environ.get("OPENAI_API_KEY"),
                base_url=os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
            )
            
            # 异步调用大模型API
            response = await client.chat.completions.create(
                model=os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo"),
                messages=messages,
                max_tokens=1000,
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
                # 等待消息，设置超时避免无限阻塞
                sender_id, message, receiver_id = await asyncio.wait_for(
                    self.message_queue.get(), timeout=1.0
                )
                
                receiver = self.agents.get(receiver_id)
                if receiver:
                    # 异步处理消息接收
                    await receiver.receive_message_async(message, sender_id)
                else:
                    print(f"警告: 未找到接收者Agent: {receiver_id}")
                    
            except asyncio.TimeoutError:
                # 超时，继续循环
                continue
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
        print("消息总线已停止")
        
        
        
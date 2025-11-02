

from collections import Counter
import json
import random
import re
import os
import asyncio
import time
from typing import List, Optional, Tuple, Dict
import uuid
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from dotenv import load_dotenv
from utils.logger import Loggable
from utils.llm_logger import llm_logger
from utils.frequency_calculator import ActivationFrequencyCalculator, FrequencyMonitor


# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = AsyncOpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL')
)

MODEL_NAME = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

with open("driver/pre_prompt.md", "r") as f:
    pre_prompt = f.read()


class MessageBus(Loggable):
    
    
    def __init__(self):
        super().__init__()
        self.agents: Dict[str, Agent] = {}
        self.logger.info("MessageBus 实例已创建")
        
        
    def register_agent(self, agent):
        self.logger.debug(f"注册代理到消息总线: {agent.id}")
        self.agents[agent.id] = agent
        self.logger.info(f"代理 {agent.id} 已注册到消息总线，当前注册代理数: {len(self.agents)}")
        
    def unregister_agent(self, agent_id: str):
        self.logger.debug(f"从消息总线注销代理: {agent_id}")
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.logger.info(f"代理 {agent_id} 已从消息总线注销，当前注册代理数: {len(self.agents)}")
        else:
            self.logger.warning(f"尝试注销不存在的代理: {agent_id}")
            
    def send_message(self, message: str, receiver_id: str, sender_id: str)->Optional[asyncio.Task]:
        self.logger.debug(f"发送消息: {sender_id} -> {receiver_id}, 长度: {len(message)} 字符")
        if receiver_id in self.agents:
            self.logger.debug(f"找到接收者 {receiver_id}，转发消息")
            task=self.agents[receiver_id].receive_message(message, sender_id)
            self.logger.info(f"消息已成功发送到 {receiver_id}")
        else:
            self.logger.error(f"接收者 {receiver_id} 未在消息总线中注册，消息发送失败")
            task=None
        return task


class AgentSystem(Loggable):
    
    
    def __init__(self):
        super().__init__()
        self.agents: Dict[str, Agent] = {}
        self.message_bus = MessageBus()
        self.explore_agent=[]
        self.io_agents=[]
        self.frequency_monitor = FrequencyMonitor()
        self.logger.debug("频率监控器已创建")
        
        self.logger.info("AgentSystem 实例已创建")
        
        
    def add_agent(self, agent):
        self.logger.debug(f"添加代理到系统: {agent.id} ({agent.__class__.__name__})")
        self.agents[agent.id] = agent
        self.message_bus.register_agent(agent)
        agent.message_bus = self.message_bus
        agent.system = self
        
        # 在频率监控器中注册Agent
        self.frequency_monitor.register_agent(agent.id)
        # 减少日志记录，只在调试模式下记录详细频率信息
        
        self.logger.info(f"代理 {agent.id} 已添加到系统")
    
    def add_io_agent(self, agent):
        self.logger.debug(f"添加IO代理: {agent.id}")
        self.add_agent(agent)
        self.io_agents.append(agent)
        self.logger.info(f"IO代理 {agent.id} 已添加到系统")
        
    async def start_all_input_agents(self):
        """启动所有 InputAgent"""
        self.logger.info("开始启动所有输入代理")
        input_agents = [agent for agent in self.io_agents if isinstance(agent, InputAgent)]
        self.logger.debug(f"找到 {len(input_agents)} 个输入代理")
        for agent in input_agents:
            self.logger.debug(f"启动输入代理: {agent.id}")
            await agent.start()
        self.logger.info("所有输入代理已启动")
                
    async def stop_all_input_agents(self):
        """停止所有 InputAgent"""
        self.logger.info("开始停止所有输入代理")
        input_agents = [agent for agent in self.io_agents if isinstance(agent, InputAgent)]
        self.logger.debug(f"找到 {len(input_agents)} 个输入代理需要停止")
        for agent in input_agents:
            self.logger.debug(f"停止输入代理: {agent.id}")
            await agent.stop()
        self.logger.info("所有输入代理已停止")
        
    def remove_agent(self, agent_id: str):
        self.logger.debug(f"尝试移除代理: {agent_id}")
        if agent_id in self.agents:
            self.message_bus.unregister_agent(agent_id)
            del self.agents[agent_id]
            
            # 清理频率监控器中的记录
            self.frequency_monitor.unregister_agent(agent_id)
            # 减少日志记录，只在调试模式下记录详细频率信息
            
            self.logger.info(f"代理 {agent_id} 已从系统中移除")
        else:
            self.logger.warning(f"尝试移除不存在的代理: {agent_id}")
            
        if agent_id in self.io_agents:
            self.io_agents.remove(agent_id)
            self.logger.debug(f"代理 {agent_id} 已从IO代理列表中移除")
            
    def get_agent(self, agent_id: str):
        agent = self.agents.get(agent_id)
        if agent:
            self.logger.debug(f"获取代理 {agent_id} 成功")
        else:
            self.logger.warning(f"获取代理 {agent_id} 失败，代理不存在")
        return agent
    
    def add_explore_agent(self, agent:str):
        self.logger.debug(f"添加探索代理: {agent}")
        self.explore_agent.append(agent)
        self.logger.info(f"代理 {agent} 已添加到探索列表，当前探索代理数: {len(self.explore_agent)}")

    def stop_explore_agent(self, agent:str):
        self.logger.debug(f"停止探索代理: {agent}")
        if agent in self.explore_agent:
            self.explore_agent.remove(agent)
            self.logger.info(f"代理 {agent} 已从探索列表移除，当前探索代理数: {len(self.explore_agent)}")
        else:
            self.logger.warning(f"尝试停止不在探索列表中的代理: {agent}")
    
    def seek_agent(self, keyword:str):
        self.logger.debug(f"寻找关键字 '{keyword}' 的探索代理")
        if not self.explore_agent:
            self.logger.warning("探索代理列表为空，无法寻找代理")
            return None
        agent = random.choice(self.explore_agent)
        self.logger.info(f"为关键字 '{keyword}' 找到探索代理: {agent}")
        return agent
    
    def split_agent(self, state, connection):
        self.logger.info(f"系统级别Agent分裂，状态: {state}, 连接数: {len(connection)}")
        new_agent=Agent()
        new_agent.state=state
        new_agent.input_connection=connection
        self.add_agent(new_agent)
        self.logger.info(f"新Agent {new_agent.id} 已创建并添加到系统")
    
    def get_frequency_stats(self, agent_id: str = None) -> dict:
        """
        获取频率统计信息
        
        Args:
            agent_id: 指定Agent ID，如果为None则返回所有Agent的统计
            
        Returns:
            dict: 频率统计信息
        """
        if agent_id:
            self.logger.debug(f"获取Agent {agent_id} 的频率统计")
            agent = self.get_agent(agent_id)
            if agent:
                stats = agent.get_frequency_stats()
                self.logger.debug(f"Agent {agent_id} 频率统计获取完成")
            else:
                self.logger.warning(f"Agent {agent_id} 不存在，无法获取频率统计")
                stats = None
        else:
            self.logger.debug("获取所有Agent的频率统计")
            stats = {}
            for agent_id, agent in self.agents.items():
                stats[agent_id] = agent.get_frequency_stats()
            self.logger.debug(f"所有 {len(stats)} 个Agent的频率统计获取完成")
        
        return stats


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
            
        self.id:str=str(uuid.uuid4())
        self.state:str=""
        self.input_connection:List[Tuple[str, str]]=[]
        self.output_connection:List[Tuple[str, str]]=[]
        self.input_cache:List[Tuple[str,str]]=[]
        self.message_bus=None
        self.system=None
        self.pre_prompt=pre_prompt
        
        # 激活频率计算器
        self.frequency_calculator = ActivationFrequencyCalculator(
            window_size=10,
            time_window_seconds=60.0,
            agent_id=self.id
        )
        self.logger.debug(f"激活频率计算器已创建 - 窗口大小: 10, 时间窗口: 60.0秒")
        
        # keyword消息接收频率跟踪器
        self.keyword_frequency_trackers: Dict[str, ActivationFrequencyCalculator] = {}
        self.logger.debug("keyword消息接收频率跟踪器已初始化")
        
        self.set_log_name(str(self.id))
        
        self.logger.info(f"Agent实例已创建，ID: {self.id}")
        
        
    def receive_message(self, message:str, sender:str)->Optional[asyncio.Task]:
        self.logger.debug(f"收到来自 {sender} 的消息: {message}")
        keyword=list(filter(lambda x:x[0]==sender, self.input_connection))
        if keyword:
            keyword=keyword[0][1]
            self.logger.debug(f"找到对应关键字: '{keyword}'")
            
            # 记录keyword消息接收频率
            if keyword not in self.keyword_frequency_trackers:
                self.keyword_frequency_trackers[keyword] = ActivationFrequencyCalculator(
                    window_size=10,
                    time_window_seconds=60.0,
                    agent_id=f"{self.id}.keyword.{keyword}"
                )
                self.logger.debug(f"为关键字 '{keyword}' 创建消息接收频率跟踪器")
            
            self.keyword_frequency_trackers[keyword].record_activation()
            # 减少日志记录，只在调试模式下记录详细频率信息
            
        else:
            keyword=sender
            self.logger.warning(f"未找到发送者 {sender} 的输入连接，使用发送者ID作为关键字")
        self.input_cache.append((keyword, message))
        self.logger.debug(f"输入缓存大小: {len(self.input_cache)}")
        if self.should_activate():
            self.logger.debug("满足激活条件，开始激活")
            task=asyncio.create_task(self.activate())
            return task
        else:
            self.logger.debug("不满足激活条件，等待更多输入")
            return None
            
    def should_activate(self):
        should_activate = len(self.input_cache) > 0
        if should_activate:
            self.logger.debug(f"激活检查: 输入缓存有 {len(self.input_cache)} 条消息，需要激活")
        else:
            self.logger.debug("激活检查: 输入缓存为空，不需要激活")
        return should_activate
        
    async def send_message(self, message:str, keyword:str):
        self.logger.debug(f"发送消息到关键字 '{keyword}': {message}")
        uids=list(filter(lambda x:x[0]==keyword, self.output_connection))
        if uids:
            uids=list(map(lambda x:x[1], uids))
            self.logger.debug(f"找到 {len(uids)} 个接收者: {uids}")
        else:
            self.logger.warning(f"未找到关键字 '{keyword}' 的输出连接")
            return
        
        for uid in uids:
            self.logger.debug(f"发送消息到接收者 {uid}")
            await self.message_bus.send_message(message, uid, self.id)
        self.logger.info(f"消息已发送到 {len(uids)} 个接收者")
            
    def delete_input_connection(self, keyword:str):
        self.logger.debug(f"删除输入连接: 关键字 '{keyword}'")
        deleted_connections=list(filter(lambda x:x[1]==keyword, self.input_connection))
        self.input_connection=list(filter(lambda x:x[1]!=keyword, self.input_connection))
        self.logger.info(f"删除了 {len(deleted_connections)} 个输入连接")
        for id, _ in deleted_connections:
            self.logger.debug(f"通知发送者 {id} 删除输出连接")
            self.system.get_agent(id).delete_output_connection(self.id)
        
    def delete_output_connection(self, id:str):
        self.logger.debug(f"删除输出连接: 接收者 {id}")
        before_count = len(self.output_connection)
        self.output_connection=list(filter(lambda x:x[1]!=id, self.output_connection))
        after_count = len(self.output_connection)
        self.logger.info(f"输出连接已删除，连接数: {before_count} -> {after_count}")
        
    def set_input_connection(self, id:str, keyword:str):
        self.logger.debug(f"设置输入连接: 发送者 {id}, 关键字 '{keyword}'")
        self.input_connection.append((id, keyword))
        self.logger.info(f"输入连接已添加，当前输入连接数: {len(self.input_connection)}")
    
    def explore(self):
        self.logger.info(f"开始探索模式，允许其他Agent发现")
        self.system.add_explore_agent(self.id)
        
    def stop_explore(self):
        self.logger.info(f"停止探索模式")
        self.system.stop_explore_agent(self.id)
    
    def seek(self,keyword):
        self.logger.info(f"寻找关键字 '{keyword}' 的Agent")
        agent=self.system.seek_agent(keyword)
        if agent is None:
            self.logger.error(f"未找到关键字 '{keyword}' 的Agent")
            return
        if not (agent,keyword) in self.output_connection:
            self.output_connection.append((keyword,agent))
            self.logger.info(f"已建立输出连接到 {agent}")
            
    def split(self,state,keyword):
        self.logger.info(f"执行Agent分裂，状态: {state}, 关键字: {keyword}")
        splited_connection=list(filter(lambda x:x[1] == keyword,self.input_connection))
        self.logger.debug(f"找到 {len(splited_connection)} 个需要分裂的连接")
        self.input_connection=list(filter(lambda x:x[1] not in keyword,self.input_connection))
        self.logger.debug(f"分裂后剩余 {len(self.input_connection)} 个输入连接")
        self.system.split_agent(state,splited_connection)
        self.logger.info("Agent分裂操作完成")
    
    def get_frequency_stats(self) -> dict:
        """
        获取Agent的频率统计信息
        
        Returns:
            dict: 频率统计信息
        """
        self.logger.debug("获取Agent频率统计信息")
        stats = self.frequency_calculator.get_frequency_stats()
        # 减少日志记录，只在调试模式下记录详细频率信息
        return stats
    
    
    def get_keyword_message_frequencies(self) -> dict:
        """
        获取各个keyword消息接收频率
        
        Returns:
            dict: {keyword: frequency_stats} 的字典
        """
        # 减少日志记录，只在调试模式下记录详细频率信息
        keyword_frequencies = {}
        
        for keyword, tracker in self.keyword_frequency_trackers.items():
            frequency_stats = tracker.get_frequency_stats()
            keyword_frequencies[keyword] = {
                'instant_frequency_hz': frequency_stats['instant_frequency_hz'],
                'moving_average_frequency_hz': frequency_stats['moving_average_frequency_hz'],
                'total_messages': frequency_stats['total_activations']
            }
            # 减少日志记录，只在调试模式下记录详细频率信息
        
        self.logger.debug(f"获取到 {len(keyword_frequencies)} 个keyword的消息接收频率信息")
        return keyword_frequencies
        
    async def activate(self):
        self.logger.info(f"激活Agent，处理 {len(self.input_cache)} 条输入缓存")
        
        # 记录激活频率
        self.frequency_calculator.record_activation()
        # 减少日志记录，只在调试模式下记录详细频率信息
        
        # 获取频率统计信息
        frequency_stats = self.frequency_calculator.get_frequency_stats()
        # 减少日志记录，只在调试模式下记录详细频率信息
        
        # 获取keyword消息接收频率
        keyword_frequencies = self.get_keyword_message_frequencies()
        
        output_count=Counter([x[0] for x in self.output_connection])
        # 构建系统提示词（包含频率信息）
        system_prompt=self.pre_prompt+\
            "这是上一次激活后你传来的状态。留下里面的记忆！必须传递下去！要不然你就会变成只能记住一次对话的痴呆症！\n<self_state>"+self.state+"</self_state>"+\
            "\n<output_keywords>"+str(output_count)+"</output_keywords>"+\
            "\n<input_keywords>"+str([x[1] for x in self.input_connection])+"</input_keywords>"+\
            "\n<your_id>"+self.id+"</your_id>"+\
            "\n<activation_frequency>"+\
            f"瞬时频率: {frequency_stats['instant_frequency_hz']:.3f} Hz, "+\
            f"移动平均: {frequency_stats['moving_average_frequency_hz']:.3f} Hz"+\
            "</activation_frequency>"+\
            "\n<keyword_message_frequencies>"+\
            str(keyword_frequencies)+\
            "</keyword_message_frequencies>"
        
        self.logger.info("系统提示词已构建，包含激活频率信息")
        
        # 构建用户提示词
        user_prompt="\n".join([f"{input[0]} : {input[1]}" for input in self.input_cache])
        
        self.logger.debug(f"系统提示词长度: {len(system_prompt)} 字符")
        self.logger.debug(f"用户提示词长度: {len(user_prompt)} 字符")
        self.logger.debug(f"输出关键字: {[x[0] for x in self.output_connection]}")
        
        message=[{"role": "system", "content": system_prompt},{"role": "user", "content": user_prompt}]
        
        try:
            self.logger.info(f"调用LLM API，模型: {MODEL_NAME}")
            start_time = time.time()
            response = await openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=message,
                temperature=0.7
            )
            response_time = time.time() - start_time
            response_content = response.choices[0].message.content
            
            # 记录LLM调用到专用日志
            tokens_used = response.usage.total_tokens if hasattr(response, 'usage') and response.usage else None
            llm_logger.log_llm_call(
                agent_id=self.id,
                model=MODEL_NAME,
                system_prompt=system_prompt.replace(pre_prompt,"[PRE_PROMPT]"),
                user_prompt=user_prompt,
                output=response_content,
                response_time=response_time,
                tokens_used=tokens_used
            )
            
            self.logger.info(f"LLM响应长度: {len(response_content)} 字符，响应时间: {response_time:.2f}秒")
            self.logger.debug(f"LLM响应内容: {response_content}")
            
            self.input_cache=[]
            self.logger.debug("输入缓存已清空")
            
            await self.process_response(response_content)
        except Exception as e:
            self.logger.error(f"LLM调用失败: {e}")
            self.logger.exception("LLM调用异常详情:")
            # 保留输入缓存以便重试
            self.logger.warning(f"保留 {len(self.input_cache)} 条输入缓存以便重试")
        
    async def process_response(self, response):
        self.logger.info(f"处理LLM响应")
        pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
        matches = pattern.findall(response)
        self.logger.info(f"找到 {len(matches)} 个标签匹配")
        
        state_updates = 0
        signal_processing = 0
        message_sending = 0
        
        task_list=[]
        
        for keyword, content in matches:
            self.logger.debug(f"处理标签 '{keyword}': {content[:50]}...")
            if keyword == "self_state":
                self.state=content
                state_updates += 1
                self.logger.info(f"更新状态，新状态长度: {len(content)} 字符")
            elif keyword == "signal":
                signal_processing += 1
                self.logger.debug(f"处理信号: {content}")
                await self.process_signal(content)
            else:
                message_sending += 1
                self.logger.debug(f"发送消息到关键字 '{keyword}'，内容长度: {len(content)} 字符")
                task=self.send_message(content,keyword)
                if task:
                    task_list.append(task)
                
        for  task in task_list:
            asyncio.ensure_future(task)
        
        self.logger.info(f"响应处理完成: 状态更新 {state_updates} 次，处理信号 {signal_processing} 个，发送消息 {message_sending} 条")
                
    async def process_signal(self, signals):
        self.logger.info(f"处理信号: {signals}")
        try:
            signals_data = json.loads(signals)
            self.logger.debug(f"解析到 {len(signals_data)} 个信号")
            signals_data=signals_data["content"]
            for signal in signals_data:
                signal_type=signal["type"]
                self.logger.info(f"执行信号: {signal_type}")
                if signal_type=="EXPLORE":
                    self.explore()
                if signal_type=="STOP_EXPLORE":
                    self.stop_explore()
                if signal_type=="SEEK":
                    self.seek(signal["keyword"])
                if signal_type=="REJECT_INPUT":
                    if signal.get("keyword"):
                        self.delete_input_connection(signal["keyword"])
                    if signal.get("id"):
                        self.logger.debug(f"通知发送者 {signal['id']} 删除输出连接")
                        self.system.get_agent(signal["id"]).delete_output_connection(self.id)
                if signal_type=="ACCEPT_INPUT":
                    self.set_input_connection(signal["id"],signal["keyword"])
                if signal_type=="SPLIT":
                    self.logger.info(f"执行SPLIT信号，状态: {signal['state']}, 关键字: {signal['keyword']}")
                    self.split(signal["state"],signal["keyword"])
        except Exception as e:
            self.logger.error(f"信号处理失败: {e}")
            self.logger.exception("信号处理异常详情:")


class OutputAgent(Loggable, ABC):
    
    
    def __init__(self):
        super().__init__()
        self.id: str = str(uuid.uuid4())
        self.input_connections:List[str]=[]
        self.message_bus = None
        self.system = None
        
        self.logger.info(f"OutputAgent实例已创建，ID: {self.id}")
        
    @abstractmethod
    def explore(self,message:str):
        """
        根据message决定是否探索
        """
        
        pass
    
    async def receive_message(self, message: str, sender: str):
        self.logger.debug(f"收到来自 {sender} 的消息: {message}")
        # 执行其他Agent送来的数据
        if sender in  self.input_connections:
            # 记录OutputAgent消息到专用日志
            llm_logger.log_output_agent_message(
                agent_id=self.id,
                message=message,
                sender_id=sender
            )
            
            self.logger.debug(f"发送者 {sender} 在输入连接列表中，执行探索和数据输出")
            self.explore(message)
            await self.execute_data(message)
            self.logger.info(f"消息已成功处理并输出")
        else:
            self.logger.warning(f"未知发送者 {sender}，忽略消息。当前输入连接: {self.input_connections}")
        
    @abstractmethod
    async def execute_data(self, data: str):
        """执行其他Agent送来的数据"""
        pass


class InputAgent(Loggable, ABC):
    
    
    def __init__(self):
        super().__init__()
        self.id: str = str(uuid.uuid4())
        self.message_bus = None
        self.output_connections:List[str] = []
        self.system = None
        self._running = False
        self._task = None
        
        self.logger.info(f"InputAgent实例已创建，ID: {self.id}")
        
    @abstractmethod
    def seek_signal(self, message: str):
        """根据message决定是否进行seek"""
        pass
        
    async def start(self):
        """启动持续运行的循环"""
        self.logger.info("启动InputAgent运行循环")
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self.logger.info("InputAgent运行循环已启动")
        
    async def stop(self):
        """停止运行循环"""
        self.logger.info("停止InputAgent运行循环")
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
                self.logger.info("InputAgent运行循环已停止")
            except asyncio.CancelledError:
                self.logger.debug("InputAgent运行循环被取消")
                pass
        
    async def _run_loop(self):
        """持续运行的循环，收集信息并检测发送时机"""
        self.logger.debug("InputAgent运行循环开始")
        loop_count = 0
        while self._running:
            loop_count += 1
            try:
                # 检查是否有数据需要发送
                if self.should_send_data():
                    self.logger.debug(f"第 {loop_count} 次循环: 有数据需要发送")
                    await self.send_collected_data()
                else:
                    #self.logger.debug(f"第 {loop_count} 次循环: 无数据需要发送")
                    ...
                
                # 等待一段时间再检查
                interval = self.get_check_interval()
                #self.logger.debug(f"等待 {interval} 秒后再次检查")
                await asyncio.sleep(interval)
                
            except asyncio.CancelledError:
                self.logger.debug("InputAgent运行循环被取消")
                break
            except Exception as e:
                self.logger.error(f"InputAgent运行循环异常: {e}")
                self.logger.exception("运行循环异常详情:")
                await asyncio.sleep(1)  # 异常后等待1秒再继续
        
        self.logger.info(f"InputAgent运行循环结束，共执行 {loop_count} 次循环")

            
        
    def should_send_data(self) -> bool:
        """检测是否应该发送数据"""
        should_send = self.has_data_to_send()
        #if should_send:
            #self.logger.debug("检测到有数据需要发送")
        #else:
            #self.logger.debug("检测到无数据需要发送")
        return should_send
        
    @abstractmethod
    def has_data_to_send(self) -> bool:
        """检查是否有数据需要发送"""
        pass
        
    def get_check_interval(self) -> float:
        """获取检查间隔（秒）"""
        return 0.1  # 默认100毫秒
        
    async def send_collected_data(self):
        """向所有输出连接发送收集到的字符串化的数据"""
        self.logger.debug("开始发送收集的数据")
        data = self.collect_data()
        self.logger.debug(f"收集到数据，长度: {len(data)} 字符")
        self.seek_signal(data)
        
        if not self.output_connections:
            self.logger.warning("无输出连接，数据无法发送")
            return
            
        # 记录InputAgent消息到专用日志
        llm_logger.log_input_agent_message(
            agent_id=self.id,
            message=data,
            receiver_ids=self.output_connections
        )
            
        self.logger.info(f"向 {len(self.output_connections)} 个输出连接发送数据")
        for receiver_id in self.output_connections:
            self.logger.debug(f"发送数据到接收者: {receiver_id}")
            await self.message_bus.send_message(data, receiver_id, self.id)
        
        self.logger.info("数据发送完成")
            
    @abstractmethod
    def collect_data(self) -> str:
        """收集并字符串化数据"""
        pass
                
                
                

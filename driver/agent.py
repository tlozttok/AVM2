#!/usr/bin/env python3
"""
AVM2 Agent 类模块
包含核心的 Agent 类
使用统一日志记录器 (unified_logger) 输出 JSONL 格式
"""

from collections import Counter
import json
import os
import re
import asyncio
import time
from typing import List, Tuple, Dict
import uuid

from openai import AsyncOpenAI
from dotenv import load_dotenv

from utils.visual_monitor.unified_logger import Loggable
from utils.llm_logger import llm_logger
from utils.frequency_calculator import ActivationFrequencyCalculator, FrequencyMonitor
from utils.agent_message_logger import agent_message_logger

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = AsyncOpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    base_url=os.getenv('OPENAI_BASE_URL')
)

MODEL_NAME = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')

# 读取预提示
with open("driver/pre_prompt.md", "r") as f:
    pre_prompt = f.read()


class Agent(Loggable):
    """
    Agent 类 - 核心处理单元

    注意：此类不可被继承
    """

    def __init__(self):
        super().__init__()

        # 防止继承
        if type(self) != Agent:
            raise TypeError("Agent 类不可继承")

        self.id: str = str(uuid.uuid4())
        self.state: str = ""
        self.input_connection: List[Tuple[str, str]] = []  # [(sender_id, keyword), ...]
        self.output_connection: List[Tuple[str, str]] = []  # [(keyword, receiver_id), ...]
        self.input_queue = asyncio.Queue()
        self.message_bus = None
        self.system = None
        self.pre_prompt = pre_prompt

        self._running = False
        self._processing_task = None
        self._processing_interval = 0.1

        # 频率监控
        self.frequency_calculator = ActivationFrequencyCalculator(
            window_size=10,
            time_window_seconds=60.0,
            agent_id=self.id
        )
        self.keyword_frequency_trackers: Dict[str, ActivationFrequencyCalculator] = {}

        # 设置日志名称
        self.set_log_name(str(self.id))

        # 记录 Agent 创建
        self.info("agent_created", {
            "agent_id": self.id,
            "agent_type": "Agent",
            "object_addr": hex(id(self)),
            "queue_addr": hex(id(self.input_queue))
        })

    def receive_message(self, message: str, sender: str):
        """接收消息并加入输入队列"""
        queue_size_before = self.input_queue.qsize()

        # 查找关键字
        keyword_list = [x for x in self.input_connection if x[0] == sender]
        if keyword_list:
            keyword = keyword_list[0][1]

            # 为关键字创建频率追踪器
            if keyword not in self.keyword_frequency_trackers:
                self.keyword_frequency_trackers[keyword] = ActivationFrequencyCalculator(
                    window_size=10,
                    time_window_seconds=60.0,
                    agent_id=f"{self.id}.keyword.{keyword}"
                )

            self.keyword_frequency_trackers[keyword].record_activation()
        else:
            keyword = sender

        self.input_queue.put_nowait((keyword, message))
        queue_size_after = self.input_queue.qsize()

        # 记录消息接收
        self.info("message_received", {
            "sender": sender,
            "keyword": keyword,
            "message_length": len(message),
            "queue_size_before": queue_size_before,
            "queue_size_after": queue_size_after
        })

    def should_activate(self) -> bool:
        """检查是否应该激活"""
        return not self.input_queue.empty()

    async def send_message(self, message: str, keyword: str):
        """通过关键字发送消息（支持全局控制）"""
        uids = [x[1] for x in self.output_connection if x[0] == keyword]

        if not uids:
            self.warning("output_connection_not_found", {
                "keyword": keyword
            })
            return

        # 等待系统恢复（如果暂停）
        while self.system and self.system.is_paused():
            await asyncio.sleep(0.1)

        for uid in uids:
            await self.message_bus.send_message(message, uid, self.id)

            # 记录消息流 (DETAIL/ARCH 日志)
            self.detail("message_flow", {
                "source_agent": self.id,
                "target_agent": uid,
                "keyword": keyword,
                "message_type": "standard",
                "message_length": len(message)
            })

            # 记录架构日志 (ARCH 模式)
            self.arch("message_flow_arch", {
                "source_agent": self.id,
                "target_agent": uid,
                "keyword": keyword,
                "bus_addr": hex(id(self.message_bus)) if self.message_bus else None
            })

        self.info("message_sent", {
            "keyword": keyword,
            "receivers_count": len(uids)
        })

    def delete_input_connection(self, keyword: str):
        """删除指定关键字的输入连接"""
        deleted = [x for x in self.input_connection if x[1] == keyword]
        self.input_connection = [x for x in self.input_connection if x[1] != keyword]

        for sender_id, _ in deleted:
            agent = self.system.get_agent(sender_id)
            if agent:
                agent.delete_output_connection(self.id)

        self.info("input_connection_deleted", {
            "keyword": keyword,
            "deleted_count": len(deleted)
        })

    def delete_output_connection(self, agent_id: str):
        """删除指定 Agent 的输出连接"""
        before = len(self.output_connection)
        self.output_connection = [x for x in self.output_connection if x[1] != agent_id]
        after = len(self.output_connection)

        self.info("output_connection_deleted", {
            "receiver_id": agent_id,
            "connections_before": before,
            "connections_after": after
        })

    def set_input_connection(self, agent_id: str, keyword: str, protected: bool = False):
        """设置输入连接，支持受保护连接"""
        # 如果 protected=True，在 keyword 中加入保护标记
        if protected:
            keyword = f"[受保护]{keyword}"

        before = len(self.input_connection)
        self.input_connection.append((agent_id, keyword))
        after = len(self.input_connection)

        self.info("input_connection_set", {
            "sender_id": agent_id,
            "keyword": keyword,
            "protected": protected,
            "connections_before": before,
            "connections_after": after
        })

    def set_output_connection(self, agent_id: str, keyword: str, protected: bool = False):
        """设置输出连接，支持受保护连接"""
        # 如果 protected=True，在 keyword 中加入保护标记
        if protected:
            keyword = f"[受保护]{keyword}"

        before = len(self.output_connection)
        self.output_connection.append((keyword, agent_id))
        after = len(self.output_connection)

        self.info("output_connection_set", {
            "receiver_id": agent_id,
            "keyword": keyword,
            "protected": protected,
            "connections_before": before,
            "connections_after": after
        })

    def delete_output_connection_by_keyword(self, keyword: str):
        """通过关键字删除输出连接"""
        deleted = [x for x in self.output_connection if x[0] == keyword]
        before = len(self.output_connection)
        self.output_connection = [x for x in self.output_connection if x[0] != keyword]
        after = len(self.output_connection)

        self.info("output_connection_deleted_by_keyword", {
            "keyword": keyword,
            "deleted_count": len(deleted),
            "connections_before": before,
            "connections_after": after
        })

        for receiver_id, _ in deleted:
            agent = self.system.get_agent(receiver_id)
            if agent:
                agent.delete_input_connection_by_id(self.id)

    def delete_input_connection_by_id(self, sender_id: str):
        """通过发送者 ID 删除输入连接"""
        before = len(self.input_connection)
        self.input_connection = [x for x in self.input_connection if x[0] != sender_id]
        after = len(self.input_connection)

        self.info("input_connection_deleted_by_id", {
            "sender_id": sender_id,
            "connections_before": before,
            "connections_after": after
        })

    def _is_connection_protected(self, keyword: str) -> bool:
        """检查连接是否受保护（通过keyword前缀）"""
        return keyword.startswith("[受保护]")

    def can_delete_connection(self, target_agent_id: str, connection_type: str) -> bool:
        """
        询问对方 Agent 是否允许删除连接
        - 如果对方是 InputAgent/OutputAgent，返回对方的决定
        - 普通 Agent 返回 True（允许删除）
        """
        from driver.i_o_agent import InputAgent, OutputAgent

        if self.system is None:
            return True  # 无系统引用，允许删除

        target = self.system.get_agent(target_agent_id)
        if target is None:
            return True  # Agent 不存在，允许删除

        # 检查对方是否是 I/O Agent
        if isinstance(target, (InputAgent, OutputAgent)):
            return target.on_connection_delete_request(self.id, connection_type)

        # 普通 Agent 不能拒绝
        return True

    def delete_input_connection_with_check(self, keyword: str):
        """带权限检查的输入连接删除"""
        deleted = []
        remaining = []

        for sender_id, kw in self.input_connection:
            if kw == keyword:
                # 检查是否受保护
                if self._is_connection_protected(kw):
                    remaining.append((sender_id, kw))
                    self.logger.info(f"Protected input connection '{kw}' from {sender_id} cannot be deleted")
                    continue

                # 询问对方是否允许删除
                if self.can_delete_connection(sender_id, "input"):
                    deleted.append((sender_id, kw))
                else:
                    # 对方拒绝，保留连接
                    remaining.append((sender_id, kw))
                    self.logger.info(f"Agent {sender_id} rejected input connection deletion")
            else:
                remaining.append((sender_id, kw))

        self.input_connection = remaining

        # 通知允许删除的对应对应删除他们的输出连接
        for sender_id, _ in deleted:
            agent = self.system.get_agent(sender_id) if self.system else None
            if agent:
                agent.delete_output_connection(self.id)

        self.info("input_connection_deleted_with_check", {
            "keyword": keyword,
            "deleted_count": len(deleted),
            "remaining_count": len(remaining)
        })

    def delete_output_connection_with_check(self, keyword: str):
        """带权限检查的输出连接删除"""
        deleted = []
        remaining = []

        for kw, receiver_id in self.output_connection:
            if kw == keyword:
                # 检查是否受保护
                if self._is_connection_protected(kw):
                    remaining.append((kw, receiver_id))
                    self.logger.info(f"Protected output connection '{kw}' to {receiver_id} cannot be deleted")
                    continue

                # 询问对方是否允许删除
                if self.can_delete_connection(receiver_id, "output"):
                    deleted.append((kw, receiver_id))
                else:
                    # 对方拒绝，保留连接
                    remaining.append((kw, receiver_id))
                    self.logger.info(f"Agent {receiver_id} rejected output connection deletion")
            else:
                remaining.append((kw, receiver_id))

        self.output_connection = remaining

        # 通知允许删除的对应对应删除他们的输入连接
        for _, receiver_id in deleted:
            agent = self.system.get_agent(receiver_id) if self.system else None
            if agent:
                agent.delete_input_connection_by_id(self.id)

        self.info("output_connection_deleted_with_check", {
            "keyword": keyword,
            "deleted_count": len(deleted),
            "remaining_count": len(remaining)
        })

    def update_input_connection_keyword(self, old_keyword: str, new_keyword: str):
        """更新输入连接的关键词"""
        updated = False
        new_connections = []

        for sender_id, keyword in self.input_connection:
            if keyword == old_keyword:
                new_connections.append((sender_id, new_keyword))
                updated = True
                # 只修改自己的词典，不通知发送方
            else:
                new_connections.append((sender_id, keyword))

        self.input_connection = new_connections

        if updated:
            self.info("input_connection_keyword_updated", {
                "old_keyword": old_keyword,
                "new_keyword": new_keyword
            })

    def update_output_connection_keyword(self, old_keyword: str, new_keyword: str):
        """更新输出连接的关键词"""
        updated = False
        new_connections = []

        for keyword, receiver_id in self.output_connection:
            if keyword == old_keyword:
                new_connections.append((new_keyword, receiver_id))
                updated = True
                # 只修改自己的词典，不通知接收方
            else:
                new_connections.append((keyword, receiver_id))

        self.output_connection = new_connections

        if updated:
            self.info("output_connection_keyword_updated", {
                "old_keyword": old_keyword,
                "new_keyword": new_keyword
            })

    def update_input_connection_keyword_for_sender(self, sender_id: str, old_keyword: str, new_keyword: str):
        """由对方调用，更新指定发送者的输入连接关键词"""
        new_connections = []
        for sid, keyword in self.input_connection:
            if sid == sender_id and keyword == old_keyword:
                new_connections.append((sender_id, new_keyword))
            else:
                new_connections.append((sid, keyword))
        self.input_connection = new_connections

    def update_output_connection_keyword_for_receiver(self, receiver_id: str, old_keyword: str, new_keyword: str):
        """由对方调用，更新指定接收者的输出连接关键词"""
        new_connections = []
        for keyword, rid in self.output_connection:
            if rid == receiver_id and keyword == old_keyword:
                new_connections.append((new_keyword, receiver_id))
            else:
                new_connections.append((keyword, rid))
        self.output_connection = new_connections

    def get_frequency_stats(self) -> dict:
        """获取激活频率统计"""
        return self.frequency_calculator.get_frequency_stats()

    def get_keyword_message_frequencies(self) -> dict:
        """获取关键字消息频率"""
        result = {}
        for keyword, tracker in self.keyword_frequency_trackers.items():
            stats = tracker.get_frequency_stats()
            result[keyword] = {
                'instant_frequency_hz': stats['instant_frequency_hz'],
                'moving_average_frequency_hz': stats['moving_average_frequency_hz'],
                'total_messages': stats['total_activations']
            }
        return result

    async def process_response(self, response):
        """解析并处理 LLM 响应"""
        pattern = re.compile(r"<(.+?)>(.*?)</\1>", re.DOTALL)
        matches = pattern.findall(response)

        state_updates = 0
        signal_processing = 0
        message_sending = 0

        for keyword, content in matches:
            if keyword == "self_state":
                self.state = content
                state_updates += 1
            elif keyword == "signal":
                signal_processing += 1
                await self.process_signal(content)
            else:
                message_sending += 1
                await self.send_message(content, keyword)

        self.info("response_processed", {
            "state_updates": state_updates,
            "signal_processing": signal_processing,
            "message_sending": message_sending
        })

    async def process_signal(self, signals):
        """处理信号"""
        try:
            signals_data = json.loads(signals)
            signals_data = signals_data.get("content", [])

            for signal in signals_data:
                signal_type = signal.get("type")

                if signal_type == "REJECT_INPUT":
                    # 只通过keyword删除，使用带保护的删除方法
                    if signal.get("keyword"):
                        self.delete_input_connection_with_check(signal["keyword"])

                elif signal_type == "ACCEPT_INPUT":
                    # 通过old_keyword和new_keyword修改已有连接的keyword
                    old_keyword = signal.get("old_keyword")
                    new_keyword = signal.get("new_keyword")
                    if old_keyword and new_keyword:
                        self.update_input_connection_keyword(old_keyword, new_keyword)

                elif signal_type == "SET_OUTPUT":
                    # 通过old_keyword和new_keyword修改已有连接的keyword
                    old_keyword = signal.get("old_keyword")
                    new_keyword = signal.get("new_keyword")
                    if old_keyword and new_keyword:
                        self.update_output_connection_keyword(old_keyword, new_keyword)

                elif signal_type == "REJECT_OUTPUT":
                    # 只通过keyword删除，使用带保护的删除方法
                    if signal.get("keyword"):
                        self.delete_output_connection_with_check(signal["keyword"])

        except Exception as e:
            self.error("signal_processing_failed", {
                "error": str(e)
            })

    async def start_processing(self):
        """开始处理循环"""
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())

        self.info("processing_started", {
            "task_id": id(self._processing_task)
        })

    async def stop_processing(self):
        """停止处理循环"""
        if not self._running:
            return

        self._running = False

        try:
            self.input_queue.put_nowait(("__STOP__", ""))
        except:
            pass

        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass

        self.info("processing_stopped", {})

    async def _processing_loop(self):
        """主处理循环"""
        loop_count = 0

        while self._running:
            loop_count += 1

            try:
                try:
                    message = await asyncio.wait_for(
                        self.input_queue.get(),
                        timeout=self._processing_interval
                    )

                    if message[0] == "__STOP__":
                        break

                    messages = [message]
                    while not self.input_queue.empty():
                        try:
                            additional = self.input_queue.get_nowait()
                            if additional[0] == "__STOP__":
                                break
                            messages.append(additional)
                        except asyncio.QueueEmpty:
                            break

                    await self._process_messages_batch(messages)

                except asyncio.TimeoutError:
                    pass

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error("processing_loop_error", {
                    "error": str(e)
                })
                await asyncio.sleep(1)

        self.info("processing_loop_ended", {
            "total_iterations": loop_count
        })

    async def _process_messages_batch(self, messages):
        """处理一批消息"""
        self.frequency_calculator.record_activation()
        frequency_stats = self.frequency_calculator.get_frequency_stats()
        keyword_frequencies = self.get_keyword_message_frequencies()

        # 记录 Agent 激活 (DETAIL 日志)
        self.detail("agent_activated", {
            "agent_id": self.id,
            "activation_count": frequency_stats['total_activations'],
            "queue_size": self.input_queue.qsize(),
            "messages_in_batch": len(messages),
            "instant_frequency_hz": frequency_stats['instant_frequency_hz']
        })

        # 记录架构日志 (ARCH 模式)
        self.arch("agent_processing_arch", {
            "agent_id": self.id,
            "messages_count": len(messages),
            "state_length": len(self.state),
            "keywords": list(keyword_frequencies.keys())
        })

        output_count = Counter([x[0] for x in self.output_connection])

        # 构建系统提示
        USE_FREQUENCY_STATS=False
        if USE_FREQUENCY_STATS:
            system_prompt = (
                self.pre_prompt +
                "\n<self_state>" + self.state + "</self_state>" +
                "\n<output_keywords>" + str(output_count) + "</output_keywords>" +
                "\n<input_keywords>" + str([x[1] for x in self.input_connection]) + "</input_keywords>" +
                "\n<your_id>" + self.id + "</your_id>" +
                "\n<activation_frequency>瞬时：" + f"{frequency_stats['instant_frequency_hz']:.3f}" +
                "Hz, 移动平均：" + f"{frequency_stats['moving_average_frequency_hz']:.3f}Hz</activation_frequency>" +
                "\n<keyword_message_frequencies>" + str(keyword_frequencies) + "</keyword_message_frequencies>"
            )
        else:
            system_prompt = (
                self.pre_prompt +
                "\n<self_state>" + self.state + "</self_state>" +
                "\n<output_keywords>" + str(output_count) + "</output_keywords>" +
                "\n<input_keywords>" + str([x[1] for x in self.input_connection]) + "</input_keywords>" +
                "\n<your_id>" + self.id + "</your_id>"
            )

        user_prompt = "\n".join([f"{m[0]} : {m[1]}" for m in messages])

        # 记录 Agent 消息到专门日志（调用 LLM 前）
        agent_message_logger.log_message(
            agent_id=self.id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            input_messages=messages,
            state=self.state
        )

        try:
            start_time = time.time()
            response = await openai_client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7
            )
            response_time = time.time() - start_time
            response_content = response.choices[0].message.content
            tokens_used = getattr(getattr(response, 'usage', None), 'total_tokens', None)

            llm_logger.log_llm_call(
                agent_id=self.id,
                model=MODEL_NAME,
                system_prompt=system_prompt.replace(pre_prompt, "[PRE_PROMPT]"),
                user_prompt=user_prompt,
                output=response_content,
                response_time=response_time,
                tokens_used=tokens_used
            )

            self.info("llm_response_received", {
                "response_time_ms": response_time * 1000,
                "response_length": len(response_content),
                "tokens_used": tokens_used
            })

            await self.process_response(response_content)

        except Exception as e:
            self.error("llm_call_failed", {
                "error": str(e)
            })
            for msg in messages:
                self.input_queue.put_nowait(msg)

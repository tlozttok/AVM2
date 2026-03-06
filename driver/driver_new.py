#!/usr/bin/env python3
"""
AVM2 核心驱动模块
使用统一日志记录器 (unified_logger) 输出 JSONL 格式
"""


from collections import Counter
import json
import re
import os
import asyncio
import time
from typing import List, Optional, Tuple, Dict
import uuid
from abc import ABC, abstractmethod
from openai import AsyncOpenAI
from dotenv import load_dotenv

# 使用统一日志记录器
from utils.visual_monitor.unified_logger import Loggable

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
        self.agents: Dict[str, 'Agent'] = {}
        self.info("message_bus_created", {
            "initial_agents_count": 0
        })

    def register_agent(self, agent):
        before_count = len(self.agents)
        self.agents[agent.id] = agent
        after_count = len(self.agents)
        self.info("agent_registered", {
            "agent_id": agent.id,
            "agents_count_before": before_count,
            "agents_count_after": after_count
        })

    def unregister_agent(self, agent_id: str):
        before_count = len(self.agents)
        if agent_id in self.agents:
            del self.agents[agent_id]
            after_count = len(self.agents)
            self.info("agent_unregistered", {
                "agent_id": agent_id,
                "agents_count_before": before_count,
                "agents_count_after": after_count
            })
        else:
            self.warning("agent_not_found_for_unregister", {
                "agent_id": agent_id
            })

    def send_message(self, message: str, receiver_id: str, sender_id: str):
        self.debug("message_routing", {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message_length": len(message)
        })

        if receiver_id in self.agents:
            self.agents[receiver_id].receive_message(message, sender_id)
            self.info("message_delivered", {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "success": True
            })
        else:
            self.error("message_delivery_failed", {
                "sender_id": sender_id,
                "receiver_id": receiver_id,
                "reason": "receiver_not_registered"
            })


class AgentSystem(Loggable):

    def __init__(self):
        super().__init__()
        self.agents: Dict[str, 'Agent'] = {}
        self.message_bus = MessageBus()
        self.io_agents = []
        self.frequency_monitor = FrequencyMonitor()

        self._system_running = False

        self.info("agent_system_created", {
            "initial_agents_count": 0
        })

    def add_agent(self, agent):
        before_count = len(self.agents)
        self.agents[agent.id] = agent
        self.message_bus.register_agent(agent)
        agent.message_bus = self.message_bus
        agent.system = self

        self.frequency_monitor.register_agent(agent.id)

        after_count = len(self.agents)

        if self._system_running and hasattr(agent, 'start_processing'):
            asyncio.ensure_future(agent.start_processing())

        self.info("agent_added", {
            "agent_id": agent.id,
            "agent_type": agent.__class__.__name__,
            "agents_count_before": before_count,
            "agents_count_after": after_count
        })

    def add_io_agent(self, agent):
        self.info("io_agent_added", {
            "agent_id": agent.id
        })
        self.add_agent(agent)
        self.io_agents.append(agent)

    async def start_all_input_agents(self):
        self.info("starting_input_agents", {})
        input_agents = [a for a in self.io_agents if isinstance(a, InputAgent)]
        for agent in input_agents:
            await agent.start()
        self.info("input_agents_started", {})

    async def stop_all_input_agents(self):
        self.info("stopping_input_agents", {})
        input_agents = [a for a in self.io_agents if isinstance(a, InputAgent)]
        for agent in input_agents:
            await agent.stop()
        self.info("input_agents_stopped", {})

    async def start_all_agents(self):
        self.info("starting_all_agents", {
            "agents_count": len(self.agents)
        })
        self._system_running = True
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'start_processing'):
                await agent.start_processing()
        self.info("all_agents_started", {})

    async def stop_all_agents(self):
        self.info("stopping_all_agents", {})
        self._system_running = False
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'stop_processing'):
                await agent.stop_processing()
        self.info("all_agents_stopped", {})

    def remove_agent(self, agent_id: str):
        if agent_id in self.agents:
            before_count = len(self.agents)
            self.message_bus.unregister_agent(agent_id)
            del self.agents[agent_id]
            after_count = len(self.agents)

            self.frequency_monitor.unregister_agent(agent_id)

            self.info("agent_removed", {
                "agent_id": agent_id,
                "agents_count_before": before_count,
                "agents_count_after": after_count
            })
        else:
            self.warning("agent_not_found_for_remove", {
                "agent_id": agent_id
            })

    def get_agent(self, agent_id: str):
        agent = self.agents.get(agent_id)
        return agent

    def get_frequency_stats(self, agent_id: str = None) -> dict:
        if agent_id:
            agent = self.get_agent(agent_id)
            if agent:
                return agent.get_frequency_stats()
            return None
        else:
            return {aid: a.get_frequency_stats() for aid, a in self.agents.items()}


class Agent(Loggable):
    """Agent 类 - 不可继承"""

    def __init__(self):
        super().__init__()
        if type(self) != Agent:
            raise TypeError("Agent 类不可继承")

        self.id: str = str(uuid.uuid4())
        self.state: str = ""
        self.input_connection: List[Tuple[str, str]] = []
        self.output_connection: List[Tuple[str, str]] = []
        self.input_queue = asyncio.Queue()
        self.message_bus = None
        self.system = None
        self.pre_prompt = pre_prompt

        self._running = False
        self._processing_task = None
        self._processing_interval = 0.1

        self.frequency_calculator = ActivationFrequencyCalculator(
            window_size=10,
            time_window_seconds=60.0,
            agent_id=self.id
        )
        self.keyword_frequency_trackers: Dict[str, ActivationFrequencyCalculator] = {}

        self.set_log_name(str(self.id))

        # 记录 Agent 创建 - 用于拓扑图构建
        self.info("agent_created", {
            "agent_id": self.id,
            "agent_type": "Agent",
            "object_addr": hex(id(self)),
            "queue_addr": hex(id(self.input_queue))
        })

    def receive_message(self, message: str, sender: str):
        queue_size_before = self.input_queue.qsize()

        keyword_list = [x for x in self.input_connection if x[0] == sender]
        if keyword_list:
            keyword = keyword_list[0][1]

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

        # 记录消息接收 - 用于激活监控
        self.info("message_received", {
            "sender": sender,
            "keyword": keyword,
            "message_length": len(message),
            "queue_size_before": queue_size_before,
            "queue_size_after": queue_size_after
        })

    def should_activate(self):
        return not self.input_queue.empty()

    async def send_message(self, message: str, keyword: str):
        uids = [x[1] for x in self.output_connection if x[0] == keyword]

        if not uids:
            self.warning("output_connection_not_found", {
                "keyword": keyword
            })
            return

        for uid in uids:
            self.message_bus.send_message(message, uid, self.id)

        self.info("message_sent", {
            "keyword": keyword,
            "receivers_count": len(uids)
        })

    def delete_input_connection(self, keyword: str):
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
        before = len(self.output_connection)
        self.output_connection = [x for x in self.output_connection if x[1] != agent_id]
        after = len(self.output_connection)

        self.info("output_connection_deleted", {
            "receiver_id": agent_id,
            "connections_before": before,
            "connections_after": after
        })

    def set_input_connection(self, agent_id: str, keyword: str):
        before = len(self.input_connection)
        self.input_connection.append((agent_id, keyword))
        after = len(self.input_connection)

        self.info("input_connection_set", {
            "sender_id": agent_id,
            "keyword": keyword,
            "connections_before": before,
            "connections_after": after
        })

    def set_output_connection(self, agent_id: str, keyword: str):
        before = len(self.output_connection)
        self.output_connection.append((keyword, agent_id))
        after = len(self.output_connection)

        self.info("output_connection_set", {
            "receiver_id": agent_id,
            "keyword": keyword,
            "connections_before": before,
            "connections_after": after
        })

    def delete_output_connection_by_keyword(self, keyword: str):
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
        before = len(self.input_connection)
        self.input_connection = [x for x in self.input_connection if x[0] != sender_id]
        after = len(self.input_connection)

        self.info("input_connection_deleted_by_id", {
            "sender_id": sender_id,
            "connections_before": before,
            "connections_after": after
        })

    def get_frequency_stats(self) -> dict:
        return self.frequency_calculator.get_frequency_stats()

    def get_keyword_message_frequencies(self) -> dict:
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
        pattern = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)
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
        try:
            signals_data = json.loads(signals)
            signals_data = signals_data.get("content", [])

            for signal in signals_data:
                signal_type = signal.get("type")

                if signal_type == "REJECT_INPUT":
                    if signal.get("keyword"):
                        self.delete_input_connection(signal["keyword"])
                    if signal.get("id"):
                        agent = self.system.get_agent(signal["id"])
                        if agent:
                            agent.delete_output_connection(self.id)

                elif signal_type == "ACCEPT_INPUT":
                    self.set_input_connection(signal["id"], signal["keyword"])

                elif signal_type == "SET_OUTPUT":
                    self.set_output_connection(signal["id"], signal["keyword"])

                elif signal_type == "REJECT_OUTPUT":
                    if signal.get("keyword"):
                        self.delete_output_connection_by_keyword(signal["keyword"])
                    if signal.get("id"):
                        agent = self.system.get_agent(signal["id"])
                        if agent:
                            agent.delete_input_connection_by_id(self.id)

        except Exception as e:
            self.error("signal_processing_failed", {
                "error": str(e)
            })

    async def start_processing(self):
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())

        self.info("processing_started", {
            "task_id": id(self._processing_task)
        })

    async def stop_processing(self):
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
        self.frequency_calculator.record_activation()
        frequency_stats = self.frequency_calculator.get_frequency_stats()
        keyword_frequencies = self.get_keyword_message_frequencies()

        output_count = Counter([x[0] for x in self.output_connection])

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

        user_prompt = "\n".join([f"{m[0]} : {m[1]}" for m in messages])

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


class OutputAgent(Loggable, ABC):

    def __init__(self):
        super().__init__()
        self.id: str = str(uuid.uuid4())
        self.input_connections: List[str] = []
        self.input_queue = asyncio.Queue()
        self.message_bus = None
        self.system = None

        self._running = False
        self._processing_task = None
        self._processing_interval = 0.1

        self.set_log_name(str(self.id))

        self.info("output_agent_created", {
            "agent_id": self.id,
            "agent_type": "OutputAgent"
        })

    @abstractmethod
    def explore(self, message: str):
        pass

    def receive_message(self, message: str, sender: str):
        if sender in self.input_connections:
            llm_logger.log_output_agent_message(
                agent_id=self.id,
                message=message,
                sender_id=sender
            )

            queue_size_before = self.input_queue.qsize()
            self.input_queue.put_nowait((sender, message))
            queue_size_after = self.input_queue.qsize()

            self.info("message_received", {
                "sender": sender,
                "message_length": len(message),
                "queue_size_before": queue_size_before,
                "queue_size_after": queue_size_after
            })
        else:
            self.warning("message_from_unknown_sender", {
                "sender": sender
            })

    async def start_processing(self):
        if self._running:
            return

        self._running = True
        self._processing_task = asyncio.create_task(self._processing_loop())
        self.info("processing_started", {})

    async def stop_processing(self):
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
                self.error("processing_loop_error", {"error": str(e)})
                await asyncio.sleep(1)

        self.info("processing_loop_ended", {"total_iterations": loop_count})

    async def _process_messages_batch(self, messages):
        for sender, message in messages:
            self.explore(message)
            await self.execute_data(message)

    @abstractmethod
    async def execute_data(self, data: str):
        pass


class InputAgent(Loggable, ABC):

    def __init__(self):
        super().__init__()
        self.id: str = str(uuid.uuid4())
        self.message_bus = None
        self.output_connections: List[str] = []
        self.system = None
        self._running = False
        self._task = None

        self.set_log_name(str(self.id))

        self.info("input_agent_created", {
            "agent_id": self.id,
            "agent_type": "InputAgent"
        })

    @abstractmethod
    def seek_signal(self, message: str):
        pass

    async def start(self):
        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        self.info("input_agent_started", {})

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self.info("input_agent_stopped", {})

    async def _run_loop(self):
        loop_count = 0

        while self._running:
            loop_count += 1

            try:
                if self.should_send_data():
                    await self.send_collected_data()

                interval = self.get_check_interval()
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error("run_loop_error", {"error": str(e)})
                await asyncio.sleep(1)

        self.info("run_loop_ended", {"total_iterations": loop_count})

    def should_send_data(self) -> bool:
        return self.has_data_to_send()

    @abstractmethod
    def has_data_to_send(self) -> bool:
        pass

    def get_check_interval(self) -> float:
        return 0.1

    async def send_collected_data(self):
        data = self.collect_data()
        self.seek_signal(data)

        if not self.output_connections:
            self.warning("no_output_connections", {})
            return

        llm_logger.log_input_agent_message(
            agent_id=self.id,
            message=data,
            receiver_ids=self.output_connections
        )

        for receiver_id in self.output_connections:
            self.message_bus.send_message(data, receiver_id, self.id)

        self.info("data_sent", {
            "data_length": len(data),
            "receivers_count": len(self.output_connections)
        })

    @abstractmethod
    def collect_data(self) -> str:
        pass

#!/usr/bin/env python3
"""
AVM2 Agent 系统模块
包含 MessageBus 和 AgentSystem 类
使用统一日志记录器 (unified_logger) 输出 JSONL 格式
"""

import asyncio
from typing import Dict, List
from utils.visual_monitor.unified_logger import Loggable


class MessageBus(Loggable):
    """消息总线 - 负责在 Agent 之间路由消息"""

    def __init__(self):
        super().__init__()
        self.agents: Dict[str, 'Agent'] = {}
        self.info("message_bus_created", {
            "initial_agents_count": 0
        })

    def register_agent(self, agent):
        """注册 Agent 到消息总线"""
        before_count = len(self.agents)
        self.agents[agent.id] = agent
        after_count = len(self.agents)
        self.info("agent_registered", {
            "agent_id": agent.id,
            "agents_count_before": before_count,
            "agents_count_after": after_count
        })

    def unregister_agent(self, agent_id: str):
        """从消息总线注销 Agent"""
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
        """发送消息到指定 Agent"""
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
    """Agent 系统 - 管理所有 Agent 和消息总线"""

    def __init__(self):
        super().__init__()
        self.agents: Dict[str, 'Agent'] = {}
        self.message_bus = MessageBus()
        self.io_agents: List['InputOutputAgent'] = []
        self._system_running = False

        self.info("agent_system_created", {
            "initial_agents_count": 0
        })

    def add_agent(self, agent):
        """添加 Agent 到系统"""
        before_count = len(self.agents)
        self.agents[agent.id] = agent
        self.message_bus.register_agent(agent)
        agent.message_bus = self.message_bus
        agent.system = self

        if hasattr(self, 'frequency_monitor'):
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
        """添加 I/O Agent 到系统"""
        self.info("io_agent_added", {
            "agent_id": agent.id
        })
        self.add_agent(agent)
        self.io_agents.append(agent)

    async def start_all_input_agents(self):
        """启动所有输入 Agent"""
        self.info("starting_input_agents", {})
        input_agents = [a for a in self.io_agents if isinstance(a, InputAgent)]
        for agent in input_agents:
            await agent.start()
        self.info("input_agents_started", {})

    async def stop_all_input_agents(self):
        """停止所有输入 Agent"""
        self.info("stopping_input_agents", {})
        input_agents = [a for a in self.io_agents if isinstance(a, InputAgent)]
        for agent in input_agents:
            await agent.stop()
        self.info("input_agents_stopped", {})

    async def start_all_agents(self):
        """启动所有 Agent"""
        self.info("starting_all_agents", {
            "agents_count": len(self.agents)
        })
        self._system_running = True
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'start_processing'):
                await agent.start_processing()
        self.info("all_agents_started", {})

    async def stop_all_agents(self):
        """停止所有 Agent"""
        self.info("stopping_all_agents", {})
        self._system_running = False
        for agent_id, agent in self.agents.items():
            if hasattr(agent, 'stop_processing'):
                await agent.stop_processing()
        self.info("all_agents_stopped", {})

    def remove_agent(self, agent_id: str):
        """从系统移除 Agent"""
        if agent_id in self.agents:
            before_count = len(self.agents)
            self.message_bus.unregister_agent(agent_id)
            del self.agents[agent_id]
            after_count = len(self.agents)

            if hasattr(self, 'frequency_monitor'):
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
        """获取指定 Agent"""
        agent = self.agents.get(agent_id)
        return agent

    def get_frequency_stats(self, agent_id: str = None) -> dict:
        """获取激活频率统计"""
        if agent_id:
            agent = self.get_agent(agent_id)
            if agent:
                return agent.get_frequency_stats()
            return None
        else:
            return {aid: a.get_frequency_stats() for aid, a in self.agents.items()}


# 延迟导入避免循环依赖
from .agent import Agent
from .i_o_agent import InputAgent, InputOutputAgent

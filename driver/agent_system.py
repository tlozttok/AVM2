#!/usr/bin/env python3
"""
AVM2 Agent 系统模块
包含 MessageBus 和 AgentSystem 类
使用统一日志记录器 (unified_logger) 输出 JSONL 格式
"""

import asyncio
from typing import Dict, List, Optional
from utils.visual_monitor.unified_logger import Loggable


class MessageBus(Loggable):
    """消息总线 - 负责在 Agent 之间路由消息"""

    def __init__(self):
        super().__init__()
        self.agents: Dict[str, 'Agent'] = {}

        # 全局控制
        self._message_paused = False      # 消息暂停标志
        self._message_delay = 0.0         # 消息延迟（秒）
        self._control_lock = asyncio.Lock()  # 控制锁

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

    async def send_message(self, message: str, receiver_id: str, sender_id: str):
        """
        发送消息到指定 Agent（支持全局控制）

        - 如果网络暂停，会阻塞等待恢复
        - 如果设置了延迟，会等待指定时间
        """
        # 检查是否暂停 - 等待恢复
        while self._message_paused:
            await asyncio.sleep(0.1)

        # 应用延迟
        if self._message_delay > 0:
            await asyncio.sleep(self._message_delay)

        self.debug("message_routing", {
            "sender_id": sender_id,
            "receiver_id": receiver_id,
            "message_length": len(message)
        })

        # 记录异步快照 (ARCH 日志)
        self.arch("async_snapshot", {
            "operation": "message_routing",
            "sender_id": sender_id,
            "receiver_id": receiver_id
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

    # ==================== 全局控制方法 ====================

    def pause_messages(self):
        """暂停消息传递"""
        self._message_paused = True
        self.info("messages_paused", {})

    def resume_messages(self):
        """恢复消息传递"""
        self._message_paused = False
        self.info("messages_resumed", {})

    def set_message_delay(self, seconds: float):
        """
        设置消息延迟（秒）

        Args:
            seconds: 延迟秒数，0 表示无延迟
        """
        self._message_delay = max(0.0, seconds)
        self.info("message_delay_set", {
            "delay_seconds": seconds
        })

    def is_message_paused(self) -> bool:
        """检查消息是否暂停"""
        return self._message_paused

    def get_message_delay(self) -> float:
        """获取当前消息延迟"""
        return self._message_delay

    def set_speed_factor(self, factor: float):
        """
        设置速度因子

        Args:
            factor: 速度因子 (1.0=正常，0.5=半速，0.1=慢速)
        """
        factor = max(0.0, min(1.0, factor))  # 限制在 0-1 范围
        # 速度因子与延迟成反比：factor=0.1 时 delay=0.9
        self._message_delay = (1.0 - factor) * 1.0
        self.info("speed_factor_set", {
            "factor": factor,
            "delay": self._message_delay
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
                # 记录任务创建 (ARCH 日志)
                self.arch("task_created", {
                    "task_name": f"agent_processor_{agent_id}",
                    "coro_name": "Agent._processing_loop",
                    "agent_id": agent_id
                })
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

    # ==================== 全局控制便捷方法 ====================

    def pause(self):
        """暂停网络活动"""
        self.message_bus.pause_messages()
        self.info("system_paused", {})

    def resume(self):
        """恢复网络活动"""
        self.message_bus.resume_messages()
        self.info("system_resumed", {})

    def set_speed(self, factor: float):
        """
        设置网络速度因子

        Args:
            factor: 速度因子 (1.0=正常，0.5=半速，0.1=慢速，0.0=完全暂停)
        """
        if factor <= 0:
            self.pause()
        else:
            if self.message_bus.is_message_paused():
                self.resume()
            self.message_bus.set_speed_factor(factor)
        self.info("system_speed_set", {
            "factor": factor
        })

    def set_message_delay(self, seconds: float):
        """
        设置消息延迟（秒）

        Args:
            seconds: 延迟秒数，0 表示无延迟
        """
        self.message_bus.set_message_delay(seconds)
        self.info("system_message_delay_set", {
            "delay_seconds": seconds
        })

    def is_paused(self) -> bool:
        """检查系统是否暂停"""
        return self.message_bus.is_message_paused()

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            'paused': self.message_bus.is_message_paused(),
            'delay': self.message_bus.get_message_delay(),
            'agent_count': len(self.agents),
            'io_agent_count': len(self.io_agents),
            'running': self._system_running
        }


# 延迟导入避免循环依赖
from .agent import Agent
from .i_o_agent import InputAgent, InputOutputAgent

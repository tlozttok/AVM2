"""
Agent 网络管理类

用于创建和管理 Agent 之间的连接网络，提供与 I/O Agent 的集成接口
"""

import random
from typing import List, Dict, Optional, Tuple

from driver.agent import Agent
from utils.logger import LoggerFactory
from driver.agent_system import AgentSystem, MessageBus
from driver.i_o_agent import InputAgent, OutputAgent


class AgentNetwork:
    """
    Agent 网络管理类

    负责创建 Agent 实例、管理其连接拓扑、以及与 I/O Agent 集成
    """

    def __init__(self, system: AgentSystem):
        """
        初始化 Agent 网络

        Args:
            system: AgentSystem 实例，用于添加和管理 Agent
        """
        self.logger = LoggerFactory.get_logger("AgentNetwork")
        self.logger.info("AgentNetwork 初始化")

        self.system = system
        self.agents: List[Agent] = []
        self.input_agents: List[InputAgent] = []
        self.output_agents: List[OutputAgent] = []

        # Agent 连接关系记录：{agent_id: [(sender_id, keyword), ...]}
        self.input_connections: Dict[str, List[Tuple[str, str]]] = {}
        # Agent 输出连接关系记录：{agent_id: [(keyword, receiver_id), ...]}
        self.output_connections: Dict[str, List[Tuple[str, str]]] = {}

    def create_network(self, num_agents: int) -> List[Agent]:
        """
        创建指定数量的 Agent 并初始化其连接

        当前为随机初始化占位实现，后续可替换为更复杂的连接算法

        Args:
            num_agents: 要创建的 Agent 数量

        Returns:
            创建的所有 Agent 列表
        """
        self.logger.info(f"创建网络，Agent 数量: {num_agents}")
        self.agents = []

        # 创建 Agent 实例
        for i in range(num_agents):
            agent = Agent()
            self.agents.append(agent)
            self.system.add_agent(agent)

            # 初始化连接记录
            self.input_connections[agent.id] = []
            self.output_connections[agent.id] = []

        # 随机初始化连接（占位实现）
        self._random_initialize_connections()

        self.logger.info(f"网络创建完成，共 {len(self.agents)} 个 Agent")
        return self.agents

    def _random_initialize_connections(self) -> None:
        """
        随机初始化 Agent 之间的连接（占位实现）

        此方法为临时实现，后续将被更智能的连接算法替代
        """
        if len(self.agents) < 2:
            self.logger.debug("Agent 数量少于 2，跳过连接初始化")
            return

        # 每个 Agent 随机连接到其他 1-3 个 Agent
        connection_count = 0
        for agent in self.agents:
            # 随机选择目标 Agent（排除自己）
            possible_targets = [a for a in self.agents if a.id != agent.id]
            num_connections = random.randint(1, min(3, len(possible_targets)))
            targets = random.sample(possible_targets, num_connections)

            for target in targets:
                # 生成随机关键字
                keyword = self._generate_random_keyword()

                # 设置输出连接
                agent.set_output_connection(target.id, keyword)

                # 设置对应的输入连接
                target.set_input_connection(agent.id, keyword)

                # 记录连接关系
                self.output_connections[agent.id].append((keyword, target.id))
                self.input_connections[target.id].append((agent.id, keyword))
                connection_count += 1
                self.logger.debug(f"连接: {agent.id[:8]} -> {target.id[:8]} (关键字: {keyword})")

        self.logger.info(f"随机初始化连接完成，共 {connection_count} 个连接")

    def _generate_random_keyword(self) -> str:
        """
        生成随机关键字

        Returns:
            随机生成的关键字字符串
        """
        # 临时实现：使用简单的前缀 + 随机数
        prefixes = ['message']
        return f"{random.choice(prefixes)}_{random.randint(1000, 9999)}"

    def connect_io_agent(self, io_agent: InputAgent | OutputAgent) -> Optional[Agent]:
        """
        将 I/O Agent 连接到网络中的一个 Agent

        当前为随机选择 Agent，后续可替换为更智能的选择算法

        Args:
            io_agent: 要连接的 I/O Agent（InputAgent 或 OutputAgent）

        Returns:
            连接到的 Agent，如果连接失败则返回 None
        """
        if not self.agents:
            self.logger.warning("尝试连接 I/O Agent 但网络中没有 Agent")
            return None

        # 随机选择一个 Agent
        target_agent = random.choice(self.agents)
        agent_type = type(io_agent).__name__

        if isinstance(io_agent, InputAgent):
            # InputAgent 向网络发送数据，需要设置输出连接到目标 Agent
            io_agent.output_connections.append(target_agent.id)
            target_agent.set_input_connection(
                io_agent.id,
                "系统感知输入（无法删除）",
                protected=True
            )
            self.input_agents.append(io_agent)
            self.logger.info(f"InputAgent {io_agent.id[:8]} 连接到 Agent {target_agent.id[:8]} (受保护)")

        elif isinstance(io_agent, OutputAgent):
            # OutputAgent 接收网络数据，需要设置输入连接从目标 Agent 接收
            keyword = "系统操作输出（无法删除）（向该连接发送数据以进行操作）"
            target_agent.set_output_connection(io_agent.id, keyword, protected=True)
            io_agent.input_connections.append(target_agent.id)
            self.output_agents.append(io_agent)
            self.logger.info(f"OutputAgent {io_agent.id[:8]} 连接到 Agent {target_agent.id[:8]} (受保护)")

        return target_agent

    def connect_io_agents(
        self,
        input_agents: List[InputAgent] = None,
        output_agents: List[OutputAgent] = None
    ) -> Dict[str, List[Agent]]:
        """
        批量连接 I/O Agent 到网络

        Args:
            input_agents: 要连接的 InputAgent 列表
            output_agents: 要连接的 OutputAgent 列表

        Returns:
            连接结果：{'input': [连接的 Agent], 'output': [连接的 Agent]}
        """
        result = {'input': [], 'output': []}

        if input_agents:
            self.logger.info(f"批量连接 {len(input_agents)} 个 InputAgent...")
            for io_agent in input_agents:
                agent = self.connect_io_agent(io_agent)
                if agent:
                    result['input'].append(agent)

        if output_agents:
            self.logger.info(f"批量连接 {len(output_agents)} 个 OutputAgent...")
            for io_agent in output_agents:
                agent = self.connect_io_agent(io_agent)
                if agent:
                    result['output'].append(agent)

        self.logger.info(f"批量连接完成: Input={len(result['input'])}, Output={len(result['output'])}")
        return result

    def get_agent(self, agent_id: str) -> Optional[Agent]:
        """
        根据 ID 获取 Agent

        Args:
            agent_id: Agent ID

        Returns:
            对应的 Agent，如果不存在则返回 None
        """
        for agent in self.agents:
            if agent.id == agent_id:
                return agent
        return None

    def get_all_agents(self) -> List[Agent]:
        """
        获取所有 Agent

        Returns:
            所有 Agent 的列表
        """
        return self.agents.copy()

    def get_connection_stats(self) -> Dict:
        """
        获取网络连接统计信息

        Returns:
            包含连接统计的字典
        """
        total_input_connections = sum(len(conns) for conns in self.input_connections.values())
        total_output_connections = sum(len(conns) for conns in self.output_connections.values())

        return {
            'total_agents': len(self.agents),
            'total_input_connections': total_input_connections,
            'total_output_connections': total_output_connections,
            'input_agents_count': len(self.input_agents),
            'output_agents_count': len(self.output_agents),
        }

    def clear(self) -> None:
        """
        清空网络，移除所有 Agent 引用

        注意：此方法只清空网络类的引用，不会从 AgentSystem 中移除 Agent
        """
        self.logger.info("清空 AgentNetwork 连接")
        self.agents.clear()
        self.input_agents.clear()
        self.output_agents.clear()
        self.input_connections.clear()
        self.output_connections.clear()
        self.logger.info("AgentNetwork 已清空")

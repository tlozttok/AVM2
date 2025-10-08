"""
异步Agent系统管理器
"""

import asyncio
import time
import json
import yaml
import os
from typing import Dict, List, Set, Any

from utils.logger import Loggable
from .driver import Agent, MessageBus
from .system_agents import InputAgent, OutputAgent, IOAgent

SYMBOLIC_REAL = None

class AgentSystem(Loggable):
    """异步Agent系统管理器"""
    
    def __init__(self):
        self.message_bus = MessageBus()
        self.agents: Dict[str, Agent] = {}
        
        self.start_time = time.time()
        self.message_count = 0
        self.activation_count = 0
    
    def register_agent(self, agent: Agent):
        """注册Agent到系统"""
        self.agents[agent.id] = agent
        agent.message_bus = self.message_bus
        self.message_bus.register_agent(agent)
    
    async def start(self):
        """启动整个系统"""
        await self.message_bus.start()
        
        # 筛选InputAgent启动它们的输入循环
        input_agents = []
        for agent in self.agents.values():
            # 检查是否是InputAgent类型（通过检查是否有start_input方法）
            if isinstance(agent,InputAgent):
                input_agents.append(agent)
        
        # 启动所有InputAgent的输入循环
        for input_agent in input_agents:
            await input_agent.start_input()
            
        print("Agent系统已启动")
        
    
    async def stop(self):
        """停止系统"""
        await self.message_bus.stop()
        print("Agent系统已停止")
    
    #TODO: 我需要更深思熟虑的考虑状态信息的数据结构
    
    def get_system_metadata(self) -> Dict[str, Any]:
        """获取系统元信息（轻量级）"""
        uptime = time.time() - self.start_time
        active_agents = len([a for a in self.agents.values() if hasattr(a, 'is_activating') and a.is_activating])
        
        return {
            "agent_count": len(self.agents),
            "message_count": self.message_count,
            "activation_count": self.activation_count,
            "uptime_seconds": int(uptime),
            "active_agents": active_agents,
            "system_status": "running" if self.message_bus.is_running else "stopped"
        }
    
    def get_agent_ids(self) -> List[str]:
        """获取所有Agent ID列表"""
        return list(self.agents.keys())
    
    def get_all_keywords(self) -> Set[str]:
        """获取系统中使用的所有关键词"""
        keywords = set()
        for agent in self.agents.values():
            # 输入关键词
            if hasattr(agent, 'input_connections') and agent.input_connections:
                for keyword in agent.input_connections.get_keywords:
                    keywords.add(keyword)
            # 输出关键词
            if hasattr(agent, 'output_connections') and agent.output_connections:
                for keyword in agent.output_connections.get_keywords:
                    keywords.add(keyword)
            # 激活关键词
            if hasattr(agent, 'input_message_keyword'):
                for keyword in agent.input_message_keyword:
                    keywords.add(keyword)
        return keywords
    
    def get_subgraph_by_keyword(self, keyword: str) -> Dict[str, Any]:
        """获取与特定关键词相关的子图"""
        related_agents = set()
        connections = []
        
        for agent_id, agent in self.agents.items():
            # 检查输入连接
            if hasattr(agent, 'input_connections') and agent.input_connections:
                for sender_id, input_keyword in agent.input_connections.connections.items():
                    if input_keyword == keyword:
                        related_agents.add(agent_id)
                        related_agents.add(sender_id)
                        connections.append(f"{sender_id} -> {agent_id} ({keyword})")
            
            # 检查输出连接
            if hasattr(agent, 'output_connections') and agent.output_connections:
                for output_keyword, receiver_ids in agent.output_connections.connections.items():
                    if output_keyword == keyword:
                        related_agents.add(agent_id)
                        for receiver_id in receiver_ids:
                            related_agents.add(receiver_id)
                            connections.append(f"{agent_id} -> {receiver_id} ({keyword})")
        
        return {
            "keyword": keyword,
            "agents": list(related_agents),
            "connections": connections,
            "agent_count": len(related_agents),
            "connection_count": len(connections)
        }
    
    def get_agent_neighbors(self, agent_id: str, depth: int = 1) -> Dict[str, Any]:
        """获取Agent的邻居拓扑"""
        if agent_id not in self.agents:
            return {"error": f"Agent {agent_id} not found"}
        
        visited = set()
        neighbors = {}
        
        def explore(current_id: str, current_depth: int):
            if current_id in visited or current_depth > depth:
                return
            visited.add(current_id)
            
            if current_id not in neighbors:
                neighbors[current_id] = {"depth": current_depth, "connections": []}
            
            agent = self.agents[current_id]
            
            # 查找输出连接（当前Agent发送给谁）
            if hasattr(agent, 'output_connections') and agent.output_connections:
                for keyword, receiver_ids in agent.output_connections.connections.items():
                    for receiver_id in receiver_ids:
                        if receiver_id in self.agents:
                            neighbors[current_id]["connections"].append({
                                "type": "output",
                                "target": receiver_id,
                                "keyword": keyword
                            })
                            explore(receiver_id, current_depth + 1)
            
            # 查找输入连接（谁发送给当前Agent）
            if hasattr(agent, 'input_connections') and agent.input_connections:
                for sender_id, keyword in agent.input_connections.connections.items():
                    if sender_id in self.agents:
                        neighbors[current_id]["connections"].append({
                            "type": "input", 
                            "source": sender_id,
                            "keyword": keyword
                        })
                        explore(sender_id, current_depth + 1)
        
        explore(agent_id, 0)
        
        return {
            "center_agent": agent_id,
            "search_depth": depth,
            "neighbors": neighbors,
            "total_agents_found": len(neighbors)
        }
    
    def get_agent_details(self, agent_ids: List[str]) -> Dict[str, Any]:
        """获取特定Agent的详细信息"""
        details = {}
        
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                details[agent_id] = {"error": "Agent not found"}
                continue
            
            agent = self.agents[agent_id]
            agent_info = {
                "id": agent.id,
                "has_prompt": bool(agent.prompt),
                "prompt_length": len(agent.prompt) if agent.prompt else 0
            }
            
            # 输入连接信息
            if hasattr(agent, 'input_connections') and agent.input_connections:
                agent_info["input_connections"] = agent.input_connections.connections
                agent_info["input_keywords"] = agent.input_connections.get_keywords
            
            # 输出连接信息
            if hasattr(agent, 'output_connections') and agent.output_connections:
                agent_info["output_connections"] = agent.output_connections.connections
                agent_info["output_keywords"] = agent.output_connections.get_keywords
            
            # 激活关键词
            if hasattr(agent, 'input_message_keyword'):
                agent_info["activation_keywords"] = agent.input_message_keyword
            
            # 缓存状态
            if hasattr(agent, 'bg_message_cache'):
                agent_info["background_cache_size"] = len(agent.bg_message_cache)
            if hasattr(agent, 'input_message_cache'):
                agent_info["input_cache_size"] = len(agent.input_message_cache)
            
            details[agent_id] = agent_info
        
        return {
            "requested_agents": agent_ids,
            "found_agents": len([a for a in details.values() if "error" not in a]),
            "details": details
        }
    
    def get_connection_types(self) -> Dict[str, List[str]]:
        """获取系统中使用的连接类型统计"""
        connection_types = {
            "input_connections": [],
            "output_connections": [],
            "bidirectional_pairs": []
        }
        
        # 收集所有连接
        all_connections = set()
        
        for agent_id, agent in self.agents.items():
            # 输入连接
            if hasattr(agent, 'input_connections') and agent.input_connections:
                for sender_id, keyword in agent.input_connections.connections.items():
                    conn = f"{sender_id}->{agent_id}:{keyword}"
                    connection_types["input_connections"].append(conn)
                    all_connections.add((sender_id, agent_id, keyword))
            
            # 输出连接
            if hasattr(agent, 'output_connections') and agent.output_connections:
                for keyword, receiver_ids in agent.output_connections.connections.items():
                    for receiver_id in receiver_ids:
                        conn = f"{agent_id}->{receiver_id}:{keyword}"
                        connection_types["output_connections"].append(conn)
                        all_connections.add((agent_id, receiver_id, keyword))
        
        # 查找双向连接
        for sender, receiver, keyword in all_connections:
            if (receiver, sender, keyword) in all_connections:
                bidirectional = f"{sender}<->{receiver}:{keyword}"
                if bidirectional not in connection_types["bidirectional_pairs"]:
                    connection_types["bidirectional_pairs"].append(bidirectional)
        
        # 添加统计信息
        connection_types["stats"] = {
            "total_input_connections": len(connection_types["input_connections"]),
            "total_output_connections": len(connection_types["output_connections"]),
            "bidirectional_pairs_count": len(connection_types["bidirectional_pairs"])
        }
        
        return connection_types
    
    def get_general_infor(self):
        '''
        为SystemMonitorInputAgent准备的综合信息收集
        包含所有连接信息和元信息，结果可能很大，主要用于前期系统监控
        '''
        general_info = {}
        
        # 1. 系统元信息
        general_info["system_metadata"] = self.get_system_metadata()
        
        # 2. 所有Agent的详细信息
        general_info["all_agents"] = {}
        for agent_id in self.get_agent_ids():
            agent_details = self.get_agent_details([agent_id])
            if agent_id in agent_details["details"]:
                general_info["all_agents"][agent_id] = agent_details["details"][agent_id]
        
        # 3. 完整的连接拓扑
        general_info["connection_topology"] = {}
        for agent_id in self.get_agent_ids():
            # 获取每个Agent的邻居拓扑（深度2，显示更完整的连接关系）
            neighbors = self.get_agent_neighbors(agent_id, depth=2)
            general_info["connection_topology"][agent_id] = neighbors
        
        # 4. 关键词分布统计
        all_keywords = self.get_all_keywords()
        keyword_usage = {}
        for keyword in all_keywords:
            subgraph = self.get_subgraph_by_keyword(keyword)
            keyword_usage[keyword] = {
                "agent_count": subgraph["agent_count"],
                "connection_count": subgraph["connection_count"],
                "related_agents": subgraph["agents"]
            }
        general_info["keyword_distribution"] = keyword_usage
        
        # 5. 连接类型详细统计
        conn_types = self.get_connection_types()
        general_info["connection_statistics"] = {
            "detailed_stats": conn_types["stats"],
            "input_connections_sample": conn_types["input_connections"][:10],  # 限制样本大小
            "output_connections_sample": conn_types["output_connections"][:10],
            "bidirectional_pairs": conn_types["bidirectional_pairs"]
        }
        
        # 6. 系统性能指标
        uptime = time.time() - self.start_time
        general_info["performance_metrics"] = {
            "uptime_seconds": int(uptime),
            "uptime_human_readable": self._format_uptime(uptime),
            "message_rate": round(self.message_count / uptime, 2) if uptime > 0 else 0,
            "activation_rate": round(self.activation_count / uptime, 2) if uptime > 0 else 0,
            "average_agents_per_keyword": round(len(all_keywords) / len(self.agents), 2) if self.agents else 0,
            "connection_density": round((len(conn_types["input_connections"]) + len(conn_types["output_connections"])) / len(self.agents), 2) if self.agents else 0
        }
        
        # 7. 系统健康评估
        general_info["health_assessment"] = {
            "agent_count_health": "good" if len(self.agents) > 0 else "poor",
            "connection_density_health": "good" if general_info["performance_metrics"]["connection_density"] > 0.5 else "moderate",
            "activity_level": "active" if self.message_count > 0 else "idle",
            "system_stability": "stable" if uptime > 60 else "initializing"  # 运行超过1分钟认为稳定
        }
        
        return general_info
    
    def _format_uptime(self, seconds: float) -> str:
        """格式化运行时间为可读格式"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs}s"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"
    
    def load_agent_from_file(self, file_path: str) -> Agent:
        """
        从文件加载Agent并注册到系统
        支持YAML和JSON格式
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
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
            
            # 检查Agent类型
            agent_type = agent_data.get("metadata", {}).get("type", "Agent")
            
            # 创建Agent实例
            agent_id = agent_data["id"]
            prompt = agent_data.get("prompt", "")
            
            if agent_type == "Agent":
                # 创建普通Agent
                agent = Agent(agent_id, prompt, self.message_bus)
            else:
                # 对于系统接口Agent，需要专门的创建逻辑
                # 这里可以扩展支持具体的系统接口Agent类型
                agent = Agent(agent_id, prompt, self.message_bus)
            
            # 设置连接
            input_connections = agent_data.get("input_connections", {})
            if isinstance(input_connections, dict):
                agent.input_connections.connections = input_connections
            
            output_connections = agent_data.get("output_connections", {})
            if isinstance(output_connections, dict):
                agent.output_connections.connections = output_connections
            
            # 设置激活关键词
            input_message_keyword = agent_data.get("input_message_keyword", [])
            if isinstance(input_message_keyword, list):
                agent.input_message_keyword = input_message_keyword
            
            # 注册到系统
            self.register_agent(agent)
            
            print(f"✅ 从文件加载并注册Agent: {agent_id}")
            return agent
            
        except Exception as e:
            print(f"❌ 从文件加载Agent失败: {e}")
            raise
    
    def load_system_from_directory(self, directory_path: str) -> None:
        """
        从目录加载整个系统
        加载目录中的所有Agent文件
        """
        if not os.path.exists(directory_path):
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        # 查找所有Agent文件
        agent_files = []
        for file_name in os.listdir(directory_path):
            if file_name.endswith(('.yaml', '.yml', '.json')):
                agent_files.append(os.path.join(directory_path, file_name))
        
        if not agent_files:
            print(f"⚠️ 目录中没有找到Agent文件: {directory_path}")
            return
        
        loaded_count = 0
        for file_path in agent_files:
            try:
                self.load_agent_from_file(file_path)
                loaded_count += 1
            except Exception as e:
                print(f"❌ 加载文件失败 {file_path}: {e}")
        
        print(f"✅ 从目录加载完成: {loaded_count}/{len(agent_files)} 个Agent成功加载")



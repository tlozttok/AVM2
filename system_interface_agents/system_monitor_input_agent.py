"""
系统监控输入Agent
记录程序系统内各个Agent的信息并定期报告
提供实在界→想象界的转换
"""

import asyncio
import time
from typing import Optional, Dict, Any
from driver.system_agents import InputAgent
from driver.driver import Agent, AgentMessage
from driver import async_system


class SystemMonitorInputAgent(InputAgent):
    """
    系统监控输入Agent
    记录程序系统内各个Agent的信息并定期报告
    提供实在界→想象界的转换
    """
    
    def __init__(self, id: str, report_interval: float = 30.0, message_bus=None):
        super().__init__(id, message_bus)
        self.agent_system = async_system.SYMBOLIC_REAL
        self.report_interval = report_interval  # 报告间隔（秒）
        self.last_report_time = 0
        self.first_activate = True
    
    async def collect_input(self) -> Optional[str]:
        """收集系统状态信息"""
        current_time = time.time()
        
        # 检查是否到达报告间隔
        if self.first_activate or current_time - self.last_report_time >= self.report_interval and self.report_interval > 0:
            self.last_report_time = current_time
            
            # 收集系统信息
            system_info = self._collect_system_info()
            self.first_activate  = False
            return system_info
        
        return None
    
    def should_activate(self, input_data: str) -> bool:
        """只要有系统信息就激活"""
        return input_data is not None
    
    def format_message(self, input_data: str) -> str:
        """格式化系统报告消息为Agent消息格式"""
        # 使用标准的Agent消息格式：<keyword>content</keyword>
        return f"<system_report>{input_data}</system_report>"
    
    def _collect_system_info(self) -> str:
        """
        为初始Agent生成可读的系统状态描述
        使用自然语言描述系统状态，便于LLM理解
        """
        import json
        
        # 收集系统状态
        agents = self.agent_system.agents
        keywords = self.agent_system.get_all_keywords()
        conn_stats = self.agent_system.get_connection_types()
        
        # 构建语义化的系统描述
        system_description = {
            "系统概述": {
                "描述": f"当前系统包含 {len(agents)} 个Agent，使用 {len(keywords)} 个通信关键词，建立了 {len(conn_stats['input_connections']) + len(conn_stats['output_connections'])} 个连接关系",
                "运行状态": "正在运行" if self.agent_system.message_bus.is_running else "已停止"
            },
            "Agent清单": {
                "总数": len(agents),
                "详细信息": {}
            },
            "通信网络": {
                "关键词列表": list(keywords),
                "连接统计": {
                    "输入连接数": len(conn_stats["input_connections"]),
                    "输出连接数": len(conn_stats["output_connections"]),
                    "双向连接对": len(conn_stats["bidirectional_pairs"])
                }
            }
        }
        
        # 为每个Agent生成描述
        for agent_id, agent in agents.items():
            agent_type = self._get_agent_type(agent)
            
            # 构建Agent描述
            agent_desc = {
                "类型": agent_type,
                "提示词状态": "有提示词" if agent.prompt else "无提示词",
                "提示词长度": len(agent.prompt) if agent.prompt else 0
            }
            
            # 输入连接描述
            if hasattr(agent, 'input_connections') and agent.input_connections:
                agent_desc["输入来源"] = list(agent.input_connections.connections.keys())
                agent_desc["输入关键词"] = list(agent.input_connections.get_keyword)
            
            # 输出连接描述
            if hasattr(agent, 'output_connections') and agent.output_connections:
                agent_desc["输出目标"] = {}
                for keyword, receivers in agent.output_connections.connections.items():
                    agent_desc["输出目标"][keyword] = receivers
            
            # 激活关键词
            if hasattr(agent, 'input_message_keyword'):
                agent_desc["激活关键词"] = agent.input_message_keyword
            
            system_description["Agent清单"]["详细信息"][agent_id] = agent_desc
        
        # 关键词使用情况描述
        keyword_analysis = {}
        for keyword in keywords:
            subgraph = self.agent_system.get_subgraph_by_keyword(keyword)
            keyword_analysis[keyword] = {
                "使用该关键词的Agent数量": subgraph["agent_count"],
                "基于该关键词的连接数": subgraph["connection_count"],
                "相关Agent": subgraph["agents"]
            }
        
        system_description["通信网络"]["关键词分析"] = keyword_analysis
        
        # 连接样本
        system_description["通信网络"]["连接样本"] = {
            "输入连接示例": conn_stats["input_connections"][:5],
            "输出连接示例": conn_stats["output_connections"][:5],
            "双向连接示例": conn_stats["bidirectional_pairs"][:3] if conn_stats["bidirectional_pairs"] else []
        }
        
        return json.dumps(system_description, ensure_ascii=False, indent=2)
    
    def _get_agent_type(self, agent) -> str:
        """客观判断Agent类型，不包含任何价值判断"""
        if hasattr(agent, 'start_input') and callable(agent.start_input):
            return "InputAgent"
        elif hasattr(agent, 'execute_action') and callable(agent.execute_action):
            return "OutputAgent"
        elif hasattr(agent, 'prompt') and agent.prompt:
            return "LLMAgent"
        else:
            return "Unknown"
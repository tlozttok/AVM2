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
        self.system_changed = False
        self.agent_system.register_event("SystemChanged", self.on_system_changed, self.id)
    
    def on_system_changed(self):   
        self.logger.debug("系统改变事件被触发了")
        self.system_changed = True 
    
    async def collect_input(self) -> Optional[str]:
        """收集系统状态信息"""
        current_time = time.time()
        
        # 检查是否到达报告间隔
        if current_time - self.last_report_time >= self.report_interval:
            self.last_report_time = current_time
            
            # 收集系统信息
            system_info = self._collect_system_info()
            self.first_activate  = False
            return system_info
        
        return None
    
    def should_activate(self, input_data: str) -> bool:
        """只要有系统信息就激活"""
        return self.first_activate or self.system_changed
    
    def format_message(self, input_data: str) -> str:
        """格式化系统报告消息为Agent消息格式"""
        # 使用标准的Agent消息格式：<keyword>content</keyword>
        return f"<system_report>{input_data}</system_report>"
    
    def _collect_system_info(self) -> str:
        """
        为初始Agent生成可读的系统状态描述
        使用自然语言描述系统状态，便于LLM理解
        """
        self.logger.info("获取系统信息...")
        agent_ids=self.agent_system.get_agent_ids()
        agent_data=[self.agent_system.get(id).data for id in agent_ids]
        #不知道写什么好
        agent_keys=[data.keywords for data in agent_data]
        agent_input_connections=[data.input_connections for data in agent_data]
        agent_output_connections=[data.output_connections for data in agent_data]
        agent_input_keywords=[data.input_message_keyword for data in agent_data]
        agent_data=[
            {"id":agent_ids[i],
             "keywords":agent_keys[i],
             "input_connections":agent_input_connections[i],
             "output_connections":agent_output_connections[i],
             "input_message_keyword":agent_input_keywords[i]
             }
            for i in  range(len(agent_ids))
        ]
        
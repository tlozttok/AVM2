"""
检查点管理器
负责保存和加载AgentSystem的完整状态
"""

import json
import pickle
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional
from driver.driver import AgentSystem, Agent, InputAgent, OutputAgent
from utils.logger import LoggerFactory


class CheckpointManager:
    """
    检查点管理器
    管理AgentSystem的持久化检查点
    """
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        初始化检查点管理器
        
        Args:
            checkpoint_dir: 检查点保存目录
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.logger = LoggerFactory.get_logger("CheckpointManager")
        
        self.logger.info(f"检查点管理器已初始化，检查点目录: {self.checkpoint_dir.absolute()}")
    
    def save_checkpoint(self, system: AgentSystem, checkpoint_name: Optional[str] = None) -> str:
        """
        保存系统检查点
        
        Args:
            system: 要保存的AgentSystem实例
            checkpoint_name: 检查点名称，如果为None则自动生成
            
        Returns:
            保存的检查点文件路径
        """
        if checkpoint_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            checkpoint_name = f"checkpoint_{timestamp}"
        
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_name}.json"
        
        self.logger.info(f"开始保存检查点: {checkpoint_file}")
        
        try:
            # 构建检查点数据
            checkpoint_data = self._build_checkpoint_data(system)
            
            # 保存为JSON文件
            with open(checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
            
            self.logger.info(f"检查点保存成功: {checkpoint_file}")
            self.logger.info(f"保存了 {len(checkpoint_data['agents'])} 个Agent的状态")
            
            return str(checkpoint_file)
            
        except Exception as e:
            self.logger.error(f"保存检查点失败: {e}")
            raise
    
    def load_checkpoint(self, checkpoint_file: str) -> AgentSystem:
        """
        从检查点加载系统
        
        Args:
            checkpoint_file: 检查点文件路径
            
        Returns:
            恢复的AgentSystem实例
        """
        checkpoint_path = Path(checkpoint_file)
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"检查点文件不存在: {checkpoint_file}")
        
        self.logger.info(f"开始加载检查点: {checkpoint_path}")
        
        try:
            # 加载检查点数据
            with open(checkpoint_path, 'r', encoding='utf-8') as f:
                checkpoint_data = json.load(f)
            
            # 重建系统
            system = self._rebuild_system(checkpoint_data)
            
            self.logger.info(f"检查点加载成功: {checkpoint_path}")
            self.logger.info(f"恢复了 {len(system.agents)} 个Agent")
            
            return system
            
        except Exception as e:
            self.logger.error(f"加载检查点失败: {e}")
            raise
    
    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """
        列出所有可用的检查点
        
        Returns:
            检查点信息列表
        """
        checkpoints = []
        
        for checkpoint_file in self.checkpoint_dir.glob("*.json"):
            try:
                with open(checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint_data = json.load(f)
                
                checkpoints.append({
                    'file': str(checkpoint_file),
                    'name': checkpoint_file.stem,
                    'timestamp': checkpoint_data.get('metadata', {}).get('timestamp', ''),
                    'agent_count': len(checkpoint_data.get('agents', {})),
                    'system_info': checkpoint_data.get('metadata', {}).get('system_info', {})
                })
            except Exception as e:
                self.logger.warning(f"无法读取检查点文件 {checkpoint_file}: {e}")
        
        # 按时间戳排序
        checkpoints.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return checkpoints
    
    def _build_checkpoint_data(self, system: AgentSystem) -> Dict[str, Any]:
        """
        构建检查点数据
        
        Args:
            system: AgentSystem实例
            
        Returns:
            检查点数据字典
        """
        checkpoint_data = {
            'metadata': {
                'timestamp': datetime.now().isoformat(),
                'system_info': {
                    'total_agents': len(system.agents),
                    'explore_agents': len(system.explore_agent),
                    'io_agents': len(system.io_agents)
                }
            },
            'agents': {},
            'system_state': {
                'explore_agent': system.explore_agent.copy(),
                'io_agents': system.io_agents.copy()
            }
        }
        
        # 保存所有Agent的状态
        for agent_id, agent in system.agents.items():
            # 跳过IOAgent（瞬态信息不需要保存）
            if isinstance(agent, (InputAgent, OutputAgent)):
                self.logger.debug(f"跳过IOAgent: {agent_id}")
                continue
                
            agent_data = self._serialize_agent(agent)
            checkpoint_data['agents'][agent_id] = agent_data
        
        return checkpoint_data
    
    def _serialize_agent(self, agent: Agent) -> Dict[str, Any]:
        """
        序列化Agent状态
        
        Args:
            agent: Agent实例
            
        Returns:
            序列化的Agent数据
        """
        agent_data = {
            'id': agent.id,
            'state': agent.state,
            'input_connection': agent.input_connection.copy(),
            'output_connection': agent.output_connection.copy(),
            'input_cache': agent.input_cache.copy(),
            'pre_prompt': agent.pre_prompt,
            'class_name': agent.__class__.__name__
        }
        
        # 保存频率统计信息
        frequency_stats = agent.get_frequency_stats()
        keyword_frequencies = agent.get_keyword_message_frequencies()
        
        agent_data['frequency_stats'] = frequency_stats
        agent_data['keyword_frequencies'] = keyword_frequencies
        
        return agent_data
    
    def _rebuild_system(self, checkpoint_data: Dict[str, Any]) -> AgentSystem:
        """
        从检查点数据重建系统
        
        Args:
            checkpoint_data: 检查点数据
            
        Returns:
            重建的AgentSystem实例
        """
        system = AgentSystem()
        
        # 重建所有Agent
        for agent_id, agent_data in checkpoint_data['agents'].items():
            agent = self._deserialize_agent(agent_data)
            system.add_agent(agent)
        
        # 恢复系统状态
        system_state = checkpoint_data.get('system_state', {})
        system.explore_agent = system_state.get('explore_agent', [])
        system.io_agents = system_state.get('io_agents', [])
        
        # 重建消息总线连接
        self._rebuild_message_bus_connections(system)
        
        return system
    
    def _deserialize_agent(self, agent_data: Dict[str, Any]) -> Agent:
        """
        从序列化数据重建Agent
        
        Args:
            agent_data: 序列化的Agent数据
            
        Returns:
            重建的Agent实例
        """
        # 创建新的Agent实例
        agent = Agent()
        
        # 恢复Agent状态
        agent.id = agent_data['id']
        agent.state = agent_data['state']
        agent.input_connection = agent_data['input_connection']
        agent.output_connection = agent_data['output_connection']
        agent.input_cache = agent_data['input_cache']
        agent.pre_prompt = agent_data['pre_prompt']
        
        # 恢复频率统计信息（这里只记录，不恢复完整的计算器状态）
        # 频率计算器会在后续运行中重新计算
        
        self.logger.debug(f"重建Agent: {agent.id}, 状态长度: {len(agent.state)}, 输入缓存: {len(agent.input_cache)}")
        
        return agent
    
    def _rebuild_message_bus_connections(self, system: AgentSystem):
        """
        重建消息总线连接
        
        Args:
            system: AgentSystem实例
        """
        # 确保所有Agent都正确连接到消息总线
        for agent_id, agent in system.agents.items():
            if agent.message_bus is None:
                agent.message_bus = system.message_bus
            if agent.system is None:
                agent.system = system
        
        # 重新注册所有Agent到消息总线
        for agent_id, agent in system.agents.items():
            system.message_bus.register_agent(agent)
    
    def delete_checkpoint(self, checkpoint_file: str) -> bool:
        """
        删除检查点
        
        Args:
            checkpoint_file: 检查点文件路径
            
        Returns:
            是否删除成功
        """
        checkpoint_path = Path(checkpoint_file)
        
        if not checkpoint_path.exists():
            self.logger.warning(f"检查点文件不存在: {checkpoint_file}")
            return False
        
        try:
            checkpoint_path.unlink()
            self.logger.info(f"检查点已删除: {checkpoint_file}")
            return True
        except Exception as e:
            self.logger.error(f"删除检查点失败: {e}")
            return False
    
    def get_latest_checkpoint(self) -> Optional[str]:
        """
        获取最新的检查点文件路径
        
        Returns:
            最新的检查点文件路径，如果没有则返回None
        """
        checkpoints = self.list_checkpoints()
        if not checkpoints:
            return None
        
        return checkpoints[0]['file']
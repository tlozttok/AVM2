#!/usr/bin/env python3
"""
激活频率计算器
计算Agent的激活频率，包括瞬时频率和基于时间的移动平均
"""

import time
from collections import deque
from typing import Optional, List
from utils.logger import LoggerFactory


class ActivationFrequencyCalculator:
    """
    激活频率计算器
    
    功能:
    - 计算瞬时频率（通过时间间隔）
    - 基于时间的移动平均计算
    - 记录激活历史
    """
    
    def __init__(self, 
                 window_size: int = 10, 
                 time_window_seconds: float = 60.0,
                 agent_id: Optional[str] = None):
        """
        初始化频率计算器
        
        Args:
            window_size: 移动平均窗口大小（基于激活次数）
            time_window_seconds: 时间窗口大小（秒）
            agent_id: 关联的Agent ID，用于日志记录
        """
        self.window_size = window_size
        self.time_window_seconds = time_window_seconds
        self.agent_id = agent_id
        
        # 激活时间记录
        self.activation_times: deque = deque()
        
        # 频率统计
        self.instant_frequency: float = 0.0  # 瞬时频率（Hz）
        self.moving_average_frequency: float = 0.0  # 移动平均频率（Hz）
        self.total_activations: int = 0  # 总激活次数
        
        # 日志器
        self.logger = LoggerFactory.get_logger(
            f"frequency_calculator.{agent_id if agent_id else 'global'}"
        )
        
        self.logger.info(
            f"激活频率计算器已创建 - 窗口大小: {window_size}, "
            f"时间窗口: {time_window_seconds}秒"
        )
    
    def record_activation(self) -> None:
        """
        记录一次激活事件并重新计算频率
        """
        current_time = time.time()
        self.activation_times.append(current_time)
        self.total_activations += 1
        
        # 清理过期的时间记录
        self._clean_old_activations(current_time)
        
        # 计算频率
        self._calculate_instant_frequency()
        self._calculate_moving_average_frequency()
        
        self.logger.debug(
            f"激活记录 - 瞬时频率: {self.instant_frequency:.3f} Hz, "
            f"移动平均: {self.moving_average_frequency:.3f} Hz, "
            f"总激活: {self.total_activations}"
        )
    
    def _clean_old_activations(self, current_time: float) -> None:
        """
        清理超出时间窗口的激活记录
        """
        cutoff_time = current_time - self.time_window_seconds
        
        # 移除超出时间窗口的记录
        while (self.activation_times and 
               self.activation_times[0] < cutoff_time):
            self.activation_times.popleft()
    
    def _calculate_instant_frequency(self) -> None:
        """
        计算瞬时频率（基于最近两次激活的时间间隔）
        """
        if len(self.activation_times) < 2:
            # 如果激活次数不足，无法计算瞬时频率
            self.instant_frequency = 0.0
            return
        
        # 计算最近两次激活的时间间隔
        recent_times = list(self.activation_times)[-2:]
        time_interval = recent_times[1] - recent_times[0]
        
        if time_interval > 0:
            self.instant_frequency = 1.0 / time_interval
        else:
            self.instant_frequency = float('inf')
    
    def _calculate_moving_average_frequency(self) -> None:
        """
        计算基于时间的移动平均频率
        """
        if len(self.activation_times) < 2:
            # 如果激活次数不足，无法计算移动平均
            self.moving_average_frequency = 0.0
            return
        
        # 计算时间窗口内的激活次数
        current_time = time.time()
        window_start = current_time - self.time_window_seconds
        
        # 统计时间窗口内的激活次数
        activations_in_window = sum(
            1 for t in self.activation_times 
            if t >= window_start
        )
        
        if self.time_window_seconds > 0:
            self.moving_average_frequency = activations_in_window / self.time_window_seconds
        else:
            self.moving_average_frequency = 0.0
    
    def get_frequency_stats(self) -> dict:
        """
        获取频率统计信息
        
        Returns:
            dict: 包含各种频率统计信息的字典
        """
        return {
            'instant_frequency_hz': self.instant_frequency,
            'moving_average_frequency_hz': self.moving_average_frequency,
            'total_activations': self.total_activations,
            'activations_in_window': len(self.activation_times),
            'window_size': self.window_size,
            'time_window_seconds': self.time_window_seconds
        }
    
    def get_instant_frequency(self) -> float:
        """获取瞬时频率（Hz）"""
        return self.instant_frequency
    
    def get_moving_average_frequency(self) -> float:
        """获取移动平均频率（Hz）"""
        return self.moving_average_frequency
    
    def get_total_activations(self) -> int:
        """获取总激活次数"""
        return self.total_activations
    
    def reset(self) -> None:
        """重置频率计算器"""
        self.activation_times.clear()
        self.instant_frequency = 0.0
        self.moving_average_frequency = 0.0
        self.total_activations = 0
        
        self.logger.info("频率计算器已重置")
    
    def __str__(self) -> str:
        """字符串表示"""
        return (
            f"ActivationFrequencyCalculator(agent={self.agent_id}, "
            f"instant={self.instant_frequency:.3f} Hz, "
            f"moving_avg={self.moving_average_frequency:.3f} Hz, "
            f"total={self.total_activations})"
        )


class FrequencyMonitor:
    """
    频率监控器 - 管理多个Agent的频率计算器
    """
    
    def __init__(self):
        """初始化频率监控器"""
        self.frequency_calculators: dict = {}
        self.logger = LoggerFactory.get_logger("frequency_monitor")
        
        self.logger.info("频率监控器已创建")
    
    def register_agent(self, 
                      agent_id: str, 
                      window_size: int = 10,
                      time_window_seconds: float = 60.0) -> ActivationFrequencyCalculator:
        """
        为Agent注册频率计算器
        
        Args:
            agent_id: Agent ID
            window_size: 窗口大小
            time_window_seconds: 时间窗口大小
            
        Returns:
            ActivationFrequencyCalculator: 创建的频率计算器
        """
        if agent_id in self.frequency_calculators:
            self.logger.warning(f"Agent {agent_id} 已注册频率计算器")
            return self.frequency_calculators[agent_id]
        
        calculator = ActivationFrequencyCalculator(
            window_size=window_size,
            time_window_seconds=time_window_seconds,
            agent_id=agent_id
        )
        self.frequency_calculators[agent_id] = calculator
        
        self.logger.info(f"Agent {agent_id} 已注册频率计算器")
        return calculator
    
    def record_activation(self, agent_id: str) -> None:
        """
        记录Agent的激活事件
        
        Args:
            agent_id: Agent ID
        """
        if agent_id not in self.frequency_calculators:
            self.logger.warning(
                f"Agent {agent_id} 未注册频率计算器，自动注册默认配置"
            )
            self.register_agent(agent_id)
        
        self.frequency_calculators[agent_id].record_activation()
    
    def get_agent_frequency_stats(self, agent_id: str) -> Optional[dict]:
        """
        获取Agent的频率统计信息
        
        Args:
            agent_id: Agent ID
            
        Returns:
            Optional[dict]: 频率统计信息，如果Agent未注册则返回None
        """
        if agent_id in self.frequency_calculators:
            return self.frequency_calculators[agent_id].get_frequency_stats()
        else:
            self.logger.warning(f"Agent {agent_id} 未注册频率计算器")
            return None
    
    def get_all_frequency_stats(self) -> dict:
        """
        获取所有注册Agent的频率统计信息
        
        Returns:
            dict: 所有Agent的频率统计信息
        """
        return {
            agent_id: calculator.get_frequency_stats()
            for agent_id, calculator in self.frequency_calculators.items()
        }
    
    def unregister_agent(self, agent_id: str) -> None:
        """
        注销Agent的频率计算器
        
        Args:
            agent_id: Agent ID
        """
        if agent_id in self.frequency_calculators:
            del self.frequency_calculators[agent_id]
            self.logger.info(f"Agent {agent_id} 的频率计算器已注销")
        else:
            self.logger.warning(f"尝试注销未注册的Agent: {agent_id}")
    
    def reset_all(self) -> None:
        """重置所有频率计算器"""
        for calculator in self.frequency_calculators.values():
            calculator.reset()
        self.logger.info("所有频率计算器已重置")
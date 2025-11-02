"""
系统持久化模块
提供AgentSystem的检查点保存和加载功能
"""

from .checkpoint_manager import CheckpointManager

__all__ = ['CheckpointManager']
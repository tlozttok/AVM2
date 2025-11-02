"""
持久化工具函数
提供便捷的检查点操作接口
"""

import asyncio
from typing import Optional
from .checkpoint_manager import CheckpointManager
from driver.driver import AgentSystem
from utils.logger import LoggerFactory


class PersistenceUtils:
    """
    持久化工具类
    """
    
    def __init__(self, checkpoint_dir: str = "checkpoints"):
        """
        初始化持久化工具
        
        Args:
            checkpoint_dir: 检查点保存目录
        """
        self.checkpoint_manager = CheckpointManager(checkpoint_dir)
        self.logger = LoggerFactory.get_logger("PersistenceUtils")
    
    async def save_system_checkpoint(self, system: AgentSystem, checkpoint_name: Optional[str] = None) -> str:
        """
        保存系统检查点（异步版本）
        
        Args:
            system: AgentSystem实例
            checkpoint_name: 检查点名称
            
        Returns:
            保存的检查点文件路径
        """
        # 在后台线程中执行保存操作以避免阻塞事件循环
        loop = asyncio.get_event_loop()
        checkpoint_file = await loop.run_in_executor(
            None, 
            self.checkpoint_manager.save_checkpoint, 
            system, 
            checkpoint_name
        )
        
        self.logger.info(f"异步保存检查点完成: {checkpoint_file}")
        return checkpoint_file
    
    async def load_system_checkpoint(self, checkpoint_file: str) -> AgentSystem:
        """
        从检查点加载系统（异步版本）
        
        Args:
            checkpoint_file: 检查点文件路径
            
        Returns:
            恢复的AgentSystem实例
        """
        # 在后台线程中执行加载操作
        loop = asyncio.get_event_loop()
        system = await loop.run_in_executor(
            None,
            self.checkpoint_manager.load_checkpoint,
            checkpoint_file
        )
        
        self.logger.info(f"异步加载检查点完成: {checkpoint_file}")
        return system
    
    def list_available_checkpoints(self) -> list:
        """
        列出所有可用的检查点
        
        Returns:
            检查点信息列表
        """
        return self.checkpoint_manager.list_checkpoints()
    
    def get_latest_checkpoint(self) -> Optional[str]:
        """
        获取最新的检查点文件路径
        
        Returns:
            最新的检查点文件路径
        """
        return self.checkpoint_manager.get_latest_checkpoint()
    
    async def auto_save(self, system: AgentSystem, interval: int = 300) -> asyncio.Task:
        """
        自动定期保存检查点
        
        Args:
            system: AgentSystem实例
            interval: 保存间隔（秒）
            
        Returns:
            自动保存任务
        """
        async def auto_save_loop():
            save_count = 0
            while True:
                try:
                    await asyncio.sleep(interval)
                    checkpoint_file = await self.save_system_checkpoint(
                        system, 
                        f"auto_save_{save_count:04d}"
                    )
                    save_count += 1
                    self.logger.info(f"自动保存完成: {checkpoint_file}")
                except asyncio.CancelledError:
                    self.logger.info("自动保存任务被取消")
                    break
                except Exception as e:
                    self.logger.error(f"自动保存失败: {e}")
        
        task = asyncio.create_task(auto_save_loop())
        self.logger.info(f"自动保存任务已启动，间隔: {interval}秒")
        return task


def create_checkpoint_manager(checkpoint_dir: str = "checkpoints") -> CheckpointManager:
    """
    创建检查点管理器
    
    Args:
        checkpoint_dir: 检查点保存目录
        
    Returns:
        CheckpointManager实例
    """
    return CheckpointManager(checkpoint_dir)


def create_persistence_utils(checkpoint_dir: str = "checkpoints") -> PersistenceUtils:
    """
    创建持久化工具
    
    Args:
        checkpoint_dir: 检查点保存目录
        
    Returns:
        PersistenceUtils实例
    """
    return PersistenceUtils(checkpoint_dir)
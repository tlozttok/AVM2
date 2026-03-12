#!/usr/bin/env python3
"""
Agent 消息日志记录器
在 Agent 调用 LLM 前记录消息到专门的日志文件
"""

import os
import gzip
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional


class AgentMessageLogger:
    """Agent 消息日志记录器 - 每个 Agent 一个文件"""

    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, log_dir: str = "logs/Agent_log"):
        if self._initialized:
            return

        self.log_dir = Path(log_dir)
        self.archive_dir = Path("logs/Agent_log_old")
        self._file_handles: dict = {}
        self._initialized = True

        # 创建目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def archive_old_logs(self):
        """归档旧日志文件"""
        if not self.log_dir.exists():
            return

        # 检查是否有旧日志文件
        log_files = list(self.log_dir.glob("*.log"))
        if not log_files:
            return

        # 生成时间戳
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_path = self.archive_dir / f"{timestamp}.zip"

        # 压缩旧日志
        import zipfile
        try:
            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for log_file in log_files:
                    zf.write(log_file, log_file.name)
                    # 清空原文件
                    log_file.unlink()
            print(f"AgentMessageLogger: Archived {len(log_files)} logs to {archive_path}")
        except Exception as e:
            print(f"AgentMessageLogger: Failed to archive logs: {e}")

    def _get_file_handle(self, agent_id: str):
        """获取或创建文件句柄"""
        if agent_id not in self._file_handles:
            log_file = self.log_dir / f"{agent_id}.log"
            self._file_handles[agent_id] = open(log_file, 'a', encoding='utf-8')
        return self._file_handles[agent_id]

    def log_message(self, agent_id: str, system_prompt: str, user_prompt: str,
                    input_messages: list, state: str):
        """
        记录 Agent 消息

        Args:
            agent_id: Agent ID
            system_prompt: 系统提示词（会被简化）
            user_prompt: 用户提示词
            input_messages: 输入消息列表
            state: Agent 状态
        """
        try:
            fh = self._get_file_handle(agent_id)

            # 简化系统提示词：用 [PRE_PROMPT] 代替实际的预提示词
            from driver.agent import pre_prompt
            simplified_system = system_prompt.replace(pre_prompt, "[PRE_PROMPT]")

            # 构建日志条目
            timestamp = datetime.now().isoformat()
            log_entry = f"""
{'='*80}
[{timestamp}] Agent: {agent_id}
{'-'*80}
System Prompt:
{simplified_system}
{'-'*80}
User Prompt:
{user_prompt}
{'-'*80}
Input Messages ({len(input_messages)}):
"""
            for msg in input_messages:
                log_entry += f"  - {msg}\n"

            log_entry += f"""{'-'*80}
State:
{state[:500]}...
{'='*80}

"""
            fh.write(log_entry)
            fh.flush()

        except Exception as e:
            print(f"AgentMessageLogger: Failed to log message for {agent_id}: {e}")

    def close(self):
        """关闭所有文件句柄"""
        for agent_id, fh in self._file_handles.items():
            try:
                fh.close()
            except:
                pass
        self._file_handles.clear()

    def __del__(self):
        self.close()


# 全局实例
agent_message_logger = AgentMessageLogger()


def archive_agent_logs():
    """归档旧日志的便捷函数"""
    agent_message_logger.archive_old_logs()

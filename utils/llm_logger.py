#!/usr/bin/env python3
"""
LLM调用专用日志记录器
专门记录每次LLM调用的输入和输出，包括时间戳、Agent ID、输入和输出内容
"""

import json
import os
import time
from datetime import datetime
from typing import Dict, Any


class LLMLogger:
    """
    LLM调用专用日志记录器
    记录格式：
    {
        "timestamp": "2024-01-01 12:00:00",
        "agent_id": "agent-123",
        "model": "gpt-3.5-turbo",
        "input": {
            "system_prompt": "...",
            "user_prompt": "..."
        },
        "output": "...",
        "response_time": 2.5,
        "tokens_used": 100
    }
    """
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self.log_file = os.path.join(log_dir, "llm_calls.jsonl")
        
    def log_llm_call(
        self, 
        agent_id: str, 
        model: str, 
        system_prompt: str, 
        user_prompt: str, 
        output: str,
        response_time: float = None,
        tokens_used: int = None
    ):
        """
        记录LLM调用
        
        Args:
            agent_id: 调用LLM的Agent ID
            model: 使用的模型名称
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            output: LLM输出内容
            response_time: 响应时间（秒）
            tokens_used: 使用的token数量
        """
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "agent_id": agent_id,
            "model": model,
            "input": {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt
            },
            "output": output,
            "response_time": response_time,
            "tokens_used": tokens_used
        }
        
        # 写入JSONL格式文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def log_input_agent_message(self, agent_id: str, message: str, receiver_ids: list):
        """
        记录InputAgent发送的消息
        
        Args:
            agent_id: 发送消息的Agent ID
            message: 消息内容
            receiver_ids: 接收者ID列表
        """
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "input_agent_message",
            "agent_id": agent_id,
            "message": message,
            "receivers": receiver_ids
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def log_output_agent_message(self, agent_id: str, message: str, sender_id: str):
        """
        记录OutputAgent接收的消息
        
        Args:
            agent_id: 接收消息的Agent ID
            message: 消息内容
            sender_id: 发送者ID
        """
        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "type": "output_agent_message", 
            "agent_id": agent_id,
            "message": message,
            "sender": sender_id
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# 全局LLM日志记录器实例
llm_logger = LLMLogger()
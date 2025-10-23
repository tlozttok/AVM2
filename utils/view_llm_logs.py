#!/usr/bin/env python3
"""
查看LLM日志的工具
"""

import json
import os
from datetime import datetime

def view_llm_logs(log_file: str = "logs/llm_calls.jsonl"):
    """
    查看LLM日志
    
    Args:
        log_file: 日志文件路径
    """
    if not os.path.exists(log_file):
        print(f"日志文件不存在: {log_file}")
        return
    
    print(f"=== LLM调用日志 ({log_file}) ===\n")
    
    with open(log_file, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            if line.strip():
                try:
                    log_entry = json.loads(line.strip())
                    
                    # 根据类型显示不同的信息
                    log_type = log_entry.get("type", "llm_call")
                    
                    if log_type == "llm_call":
                        print(f"[{line_num}] LLM调用 - {log_entry['timestamp']}")
                        print(f"    Agent: {log_entry['agent_id']}")
                        print(f"    模型: {log_entry['model']}")
                        print(f"    系统提示词: {log_entry['input']['system_prompt'][:100]}...")
                        print(f"    用户提示词: {log_entry['input']['user_prompt'][:100]}...")
                        print(f"    LLM输出: {log_entry['output'][:100]}...")
                        if log_entry.get('response_time'):
                            print(f"    响应时间: {log_entry['response_time']:.2f}秒")
                        if log_entry.get('tokens_used'):
                            print(f"    Token使用: {log_entry['tokens_used']}")
                    
                    elif log_type == "input_agent_message":
                        print(f"[{line_num}] InputAgent消息 - {log_entry['timestamp']}")
                        print(f"    Agent: {log_entry['agent_id']}")
                        print(f"    消息: {log_entry['message'][:100]}...")
                        print(f"    接收者: {log_entry['receivers']}")
                    
                    elif log_type == "output_agent_message":
                        print(f"[{line_num}] OutputAgent消息 - {log_entry['timestamp']}")
                        print(f"    Agent: {log_entry['agent_id']}")
                        print(f"    消息: {log_entry['message'][:100]}...")
                        print(f"    发送者: {log_entry['sender']}")
                    
                    print()  # 空行分隔
                    
                except json.JSONDecodeError as e:
                    print(f"[{line_num}] 解析错误: {e}")
                    print(f"    原始行: {line.strip()}")
                    print()

def count_llm_calls(log_file: str = "logs/llm_calls.jsonl"):
    """
    统计LLM调用次数
    
    Args:
        log_file: 日志文件路径
    """
    if not os.path.exists(log_file):
        print(f"日志文件不存在: {log_file}")
        return
    
    llm_calls = 0
    input_messages = 0
    output_messages = 0
    
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    log_entry = json.loads(line.strip())
                    log_type = log_entry.get("type", "llm_call")
                    
                    if log_type == "llm_call":
                        llm_calls += 1
                    elif log_type == "input_agent_message":
                        input_messages += 1
                    elif log_type == "output_agent_message":
                        output_messages += 1
                        
                except json.JSONDecodeError:
                    continue
    
    print(f"=== 统计信息 ===")
    print(f"LLM调用次数: {llm_calls}")
    print(f"InputAgent消息数: {input_messages}")
    print(f"OutputAgent消息数: {output_messages}")
    print(f"总计: {llm_calls + input_messages + output_messages}")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "count":
        count_llm_calls()
    else:
        view_llm_logs()
#!/usr/bin/env python3
"""
测试可视化监控
生成一些测试日志数据来验证监控系统工作正常
"""

import sys
import os
import time
import json
import random

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.visual_monitor.unified_logger import unified_logger, Loggable, LogMode

# 设置模式
LogMode.DETAIL
unified_logger.set_mode(LogMode.DETAIL)

print("生成测试日志...")

# 模拟 Agent 创建
for i in range(5):
    agent_id = f"agent-{random.randint(1000, 9999)}"
    unified_logger.log("info", f"Agent.{agent_id}", "agent_created", {
        "agent_id": agent_id,
        "agent_type": random.choice(["Agent", "InputAgent", "OutputAgent"]),
        "object_addr": hex(random.randint(0x10000000, 0xFFFFFFFF)),
        "queue_addr": hex(random.randint(0x10000000, 0xFFFFFFFF))
    })
    print(f"  创建 Agent: {agent_id}")
    time.sleep(0.1)

# 模拟连接建立
agents = []
for entry in open("logs/system.jsonl", "r").readlines()[-5:]:
    data = json.loads(entry)
    if data.get("event_type") == "agent_created":
        agents.append(data["data"]["agent_id"])

print(f"找到 Agent: {agents}")

# 创建一些连接
for i in range(len(agents) - 1):
    unified_logger.log("info", f"Agent.{agents[i]}", "output_connection_set", {
        "receiver_id": agents[i + 1],
        "keyword": f"keyword_{i}"
    })
    unified_logger.log("info", f"Agent.{agents[i + 1]}", "input_connection_set", {
        "sender_id": agents[i],
        "keyword": f"keyword_{i}"
    })
    print(f"  创建连接：{agents[i]} -> {agents[i + 1]}")
    time.sleep(0.1)

# 模拟消息传递
for i in range(10):
    if agents:
        src = random.choice(agents)
        dst = random.choice(agents)
        unified_logger.log("info", f"Agent.{dst}", "message_received", {
            "sender": src,
            "keyword": f"keyword_{random.randint(0, 3)}",
            "message_length": random.randint(50, 500),
            "queue_size_before": random.randint(0, 5),
            "queue_size_after": random.randint(1, 6)
        })
        time.sleep(0.2)

print("测试日志生成完成!")
print(f"日志文件：logs/system.jsonl")
print(f"日志行数：{len(open('logs/system.jsonl', 'r').readlines())}")

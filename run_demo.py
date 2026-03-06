#!/usr/bin/env python3
"""
AVM2 可视化监控演示
启动监控服务器并生成测试数据
"""

import sys
import os
import asyncio
import time
import random
import threading

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.visual_monitor.unified_logger import unified_logger, LogMode, Loggable
from utils.visual_monitor.server import run_async_server


class TestAgent(Loggable):
    """测试 Agent 类"""

    def __init__(self, agent_id: str, agent_type: str = "Agent"):
        super().__init__()
        self.id = agent_id
        self.type = agent_type
        self.set_log_name(agent_id)

        # 记录创建事件
        self.info("agent_created", {
            "agent_id": self.id,
            "agent_type": self.type,
            "object_addr": hex(id(self)),
            "queue_addr": hex(id(self))
        })

    def connect_to(self, target: 'TestAgent', keyword: str):
        """建立连接到目标 Agent"""
        # 输出连接
        self.info("output_connection_set", {
            "receiver_id": target.id,
            "keyword": keyword
        })
        # 输入连接
        target.info("input_connection_set", {
            "sender_id": self.id,
            "keyword": keyword
        })

    def send_message(self, target: 'TestAgent', message: str, keyword: str):
        """发送消息到目标 Agent"""
        target.info("message_received", {
            "sender": self.id,
            "keyword": keyword,
            "message_length": len(message),
            "queue_size_before": random.randint(0, 5),
            "queue_size_after": random.randint(1, 6)
        })


async def generate_test_data():
    """生成测试数据"""
    print("开始生成测试数据...")

    # 等待服务器启动
    await asyncio.sleep(2)

    # 创建 Agent
    agents = []
    for i in range(5):
        agent_type = random.choice(["Agent", "InputAgent", "OutputAgent"])
        agent = TestAgent(f"agent-{1000+i}", agent_type)
        agents.append(agent)
        print(f"  创建 {agent_type}: agent-{1000+i}")
        await asyncio.sleep(0.5)

    # 建立连接（链式）
    print("建立连接...")
    for i in range(len(agents) - 1):
        agents[i].connect_to(agents[i + 1], f"channel_{i}")
        print(f"  连接：{agents[i].id} -> {agents[i + 1].id}")
        await asyncio.sleep(0.3)

    # 随机消息传递
    print("开始消息传递...")
    for i in range(20):
        src = random.choice(agents)
        dst = random.choice(agents)
        if src != dst:
            src.send_message(dst, f"Message {i}", f"channel_{random.randint(0, 3)}")
            print(f"  消息：{src.id} -> {dst.id}")
        await asyncio.sleep(0.5)

    print("测试数据生成完成!")


async def main():
    """主函数"""
    print("=" * 50)
    print("AVM2 可视化监控演示")
    print("=" * 50)
    print()
    print("访问地址：http://localhost:8765")
    print()

    # 设置日志模式
    LogMode.DETAIL
    unified_logger.set_mode(LogMode.DETAIL)

    # 启动测试数据生成任务
    test_task = asyncio.create_task(generate_test_data())

    # 启动监控服务器
    try:
        await run_async_server(host="localhost", port=8765, log_dir="logs")
    except KeyboardInterrupt:
        print("\n正在关闭...")
        test_task.cancel()


if __name__ == '__main__':
    asyncio.run(main())

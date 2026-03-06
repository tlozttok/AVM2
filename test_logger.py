#!/usr/bin/env python3
"""
日志系统测试脚本
测试三层日志模式：CONTENT / DETAIL / ARCH
"""

import os
import sys
import asyncio
import time

# 设置日志模式
os.environ['AVM2_LOG_MODE'] = 'ARCH'  # 可以改为 CONTENT 或 DETAIL

print("=" * 60)
print("AVM2 三层日志系统测试")
print("=" * 60)
print(f"当前日志模式：{os.environ['AVM2_LOG_MODE']}")
print()

# 导入模块
from utils.logger import LoggerFactory, LogMode, Loggable, StructuredLogger
from utils.detail_logger import DetailLogger, detail_logger

# 测试 1: LoggerFactory
print("测试 1: LoggerFactory")
print("-" * 40)

logger1 = LoggerFactory.get_logger("TestModule1")
print(f"日志模式：{LoggerFactory.get_mode()}")
print(f"logger1 类型：{type(logger1).__name__}")
print(f"logger1 模式：{logger1.get_mode()}")

logger1.info("这是一条 INFO 日志")
logger1.debug("这是一条 DEBUG 日志")
logger1.warning("这是一条 WARNING 日志")

# 测试 2: StructuredLogger 的 detail 和 arch 方法
print()
print("测试 2: StructuredLogger 扩展方法")
print("-" * 40)

logger1.detail("test_event", {
    "test_key": "test_value",
    "number": 42,
    "list": [1, 2, 3]
})
print("已调用 detail() 方法")

logger1.arch("arch_event", {
    "async_operation": "test",
    "task_info": "test_task"
})
print("已调用 arch() 方法")

# 测试 3: Loggable 基类
print()
print("测试 3: Loggable 基类")
print("-" * 40)

class TestClass(Loggable):
    def __init__(self):
        super().__init__()
        self.logger.info("TestClass 初始化")

    def do_something(self):
        self.logger.debug("正在执行某个操作")
        self.logger.detail("operation_detail", {
            "step": 1,
            "description": "执行第一步"
        })
        self.logger.arch("operation_arch", {
            "async_context": "test"
        })

obj = TestClass()
obj.do_something()

# 测试 4: AgentLogger 包装器
print()
print("测试 4: AgentLogger 包装器")
print("-" * 40)

logger2 = LoggerFactory.get_logger("TestAgent")
logger2.set_agent_id("agent-12345")
logger2.info("Agent 已初始化")
logger2.detail("agent_event", {
    "agent_id": "agent-12345",
    "event": "test"
})

# 测试 5: DetailLogger 直接使用
print()
print("测试 5: DetailLogger 直接使用")
print("-" * 40)

detail_logger.log_detail("DirectTest", "direct_event", {
    "message": "直接调用 detail_logger",
    "timestamp": time.time()
})

detail_logger.log_arch("DirectTest", "direct_arch_event", {
    "message": "直接调用 arch_logger",
    "async_info": "test"
})

print("已直接调用 detail_logger 方法")

# 等待一下让异步日志写入
time.sleep(0.5)

# 测试 6: 检查日志文件
print()
print("测试 6: 检查日志文件")
print("-" * 40)

log_files = [
    "logs/TestModule1.log",
    "logs/TestClass.log",
    "logs/TestAgent.log",
    "logs/detail/system.detail.jsonl",
    "logs/arch/system.arch.jsonl"
]

for f in log_files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"✓ {f} 存在 (大小：{size} 字节)")

        # 显示最后几行
        with open(f, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            print(f"  最后 2 行内容:")
            for line in lines[-2:]:
                print(f"    {line.strip()[:100]}...")
    else:
        print(f"✗ {f} 不存在")

print()
print("=" * 60)
print("测试完成!")
print("=" * 60)
print()
print("提示:")
print("- 修改 AVM2_LOG_MODE 环境变量切换模式:")
print("  CONTENT: 仅基础日志")
print("  DETAIL:  基础日志 + 程序细节")
print("  ARCH:    基础日志 + 程序细节 + 架构还原")
print()
print("日志文件位置:")
print("- 基础日志：logs/<模块名>.log")
print("- 细节日志：logs/detail/system.detail.jsonl")
print("- 架构日志：logs/arch/system.arch.jsonl")

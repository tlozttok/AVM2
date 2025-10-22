#!/usr/bin/env python3
"""
测试日志系统，验证函数名显示是否正确
"""

from utils.logger import LoggerFactory, AgentLogger

# 测试普通日志器
logger = LoggerFactory.get_logger("test")

def test_function():
    logger.info("这是来自 test_function 的日志")
    logger.debug("这是调试信息")

# 测试Agent日志器
class TestAgent:
    def __init__(self):
        self.id = "test-agent-123"
        self.logger = AgentLogger(self.id, LoggerFactory.get_logger("TestAgent"))
    
    def process_message(self):
        self.logger.info("这是来自 process_message 的日志")
        self.logger.debug("这是调试信息")

if __name__ == "__main__":
    print("测试普通日志器...")
    test_function()
    
    print("\n测试Agent日志器...")
    agent = TestAgent()
    agent.process_message()
    
    print("\n测试完成，请查看 logs/test.log 和 logs/TestAgent.log 文件")
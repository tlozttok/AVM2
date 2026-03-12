#!/usr/bin/env python3
"""
AVM2 主程序
- 启动可视化监控服务
- 启动终端
- 使用 AgentNetwork 初始化 Agent 网络
- 连接终端 I/O Agent 到网络
"""

import asyncio
import signal
import sys

from driver import AgentSystem
from utils.logger import LoggerFactory
from driver.net import AgentNetwork
from AVBash.terminal_agents import TerminalPair
from utils.visual_monitor.server import run_async_server
from utils.visual_monitor.unified_logger import unified_logger, LogMode
from utils.agent_message_logger import archive_agent_logs


class MainApplication:
    """主应用程序类"""

    def __init__(self):
        self.logger = LoggerFactory.get_logger("MainApplication")
        self.logger.info("MainApplication 初始化")

        self.system: AgentSystem = None
        self.network: AgentNetwork = None
        self.terminal_pair: TerminalPair = None
        self.monitor_task: asyncio.Task = None
        self._shutdown = False

    async def start(self):
        """启动应用程序"""
        self.logger.info("=" * 50)
        self.logger.info("AVM2 Agent 系统启动")
        self.logger.info("=" * 50)
        print("=" * 50)
        print("AVM2 Agent 系统")
        print("=" * 50)
        print()

        # 归档旧 Agent 消息日志
        archive_agent_logs()

        # 1. 启动监控服务器（后台任务）
        self.logger.info("启动监控服务器...")
        print("启动监控服务器...")
        self.monitor_task = asyncio.create_task(
            run_async_server(host="localhost", port=8765, log_dir="logs")
        )
        print("  监控服务器运行于：http://localhost:8765")

        # 2. 创建并启动终端（10秒渲染一次）
        self.logger.info("启动终端...")
        print("启动终端...")
        self.terminal_pair = TerminalPair(fps=0.1, default_rows=20, default_cols=80)
        await self.terminal_pair.start()

        # 3. 检查终端是否正常运行
        if not self.terminal_pair.terminal.windows:
            self.logger.error("终端启动失败：没有创建窗口")
            raise RuntimeError("终端启动失败：没有创建窗口")
        self.logger.info(f"终端已启动，窗口 ID: {list(self.terminal_pair.terminal.windows.keys())}")
        print(f"  终端已启动，窗口 ID: {list(self.terminal_pair.terminal.windows.keys())}")

        # 4. 创建 Agent 系统
        self.logger.info("初始化 Agent 系统...")
        print("初始化 Agent 系统...")
        self.system = AgentSystem()

        # 设置系统运行频率：10秒一次调用
        self.system.set_message_delay(10.0)
        print("  系统消息延迟: 10s")

        # 5. 创建 Agent 网络
        self.logger.info("创建 Agent 网络...")
        print("创建 Agent 网络...")
        self.network = AgentNetwork(self.system)

        # 6. 创建终端 Agent
        input_agent, output_agent = self.terminal_pair.create_agents()
        self.logger.info(f"创建终端 Agent: Input={input_agent.id}, Output={output_agent.id}")
        print(f"  终端 InputAgent: {input_agent.id}")
        print(f"  终端 OutputAgent: {output_agent.id}")

        # 7. 创建内部 Agent 网络
        agents = self.network.create_network(num_agents=10)
        self.logger.info(f"创建内部 Agent 网络，共 {len(agents)} 个 Agent")
        print(f"  创建了 {len(agents)} 个内部 Agent")

        # 8. 将终端 I/O Agent 连接到网络
        self.logger.info("连接终端 I/O Agent 到网络...")
        print("连接终端 I/O Agent 到网络...")
        self.system.add_io_agent(input_agent)
        self.system.add_io_agent(output_agent)

        connected = self.network.connect_io_agents(
            input_agents=[input_agent],
            output_agents=[output_agent]
        )
        self.logger.info(f"I/O Agent 连接完成: Input={len(connected['input'])}, Output={len(connected['output'])}")
        print(f"  InputAgent 连接到: {len(connected['input'])} 个 Agent")
        print(f"  OutputAgent 连接到: {len(connected['output'])} 个 Agent")

        # 9. 启动所有 Agent
        self.logger.info("启动所有 Agent...")
        print("启动所有 Agent...")

        # 设置日志级别为 ARCH（用于异步活动监控）
        unified_logger.set_mode(LogMode.ARCH)
        print("  日志模式: ARCH (架构级)")

        await self.system.start_all_agents()
        self.logger.info("所有 Agent 已启动")
        print("  所有 Agent 已启动")

        # 10. 打印网络统计
        stats = self.network.get_connection_stats()
        self.logger.info(f"网络统计: {stats}")
        print(f"  网络统计: {stats}")

        self.logger.info("系统运行中...")
        print()
        print("=" * 50)
        print("系统运行中... 按 Ctrl+C 停止")
        print("=" * 50)
        print()
        print("提示:")
        print("  - 在终端中输入 /help 查看命令")
        print("  - 访问 http://localhost:8765 查看监控界面")
        print("  - 使用 system.pause() / system.resume() 控制网络")
        print()

        # 11. 运行直到用户中断
        await self.run_until_shutdown()

    async def run_until_shutdown(self):
        """运行直到关闭"""
        try:
            # 等待事件（实际上会一直等待）
            await asyncio.Event().wait()
        except asyncio.CancelledError:
            pass

    async def stop(self):
        """停止应用程序"""
        self.logger.info("正在关闭系统...")
        print("\n正在关闭系统...")

        # 停止所有 Agent
        if self.system:
            await self.system.stop_all_agents()
            self.logger.info("Agent 系统已停止")
            print("  Agent 系统已停止")

        # 停止终端
        if self.terminal_pair:
            await self.terminal_pair.stop()
            self.logger.info("终端已停止")
            print("  终端已停止")

        # 停止监控服务器
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
            self.logger.info("监控服务器已停止")
            print("  监控服务器已停止")

        self.logger.info("系统已完全关闭")
        print("系统已完全关闭")


async def main():
    """主函数"""
    app = MainApplication()

    # 设置信号处理
    loop = asyncio.get_event_loop()

    def signal_handler():
        app.logger.info("收到中断信号，开始关闭...")
        print("\n收到中断信号...")
        app._shutdown = True
        # 取消主任务
        for task in asyncio.all_tasks(loop):
            task.cancel()

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, signal_handler)

    try:
        await app.start()
    except Exception as e:
        app.logger.error(f"运行错误: {e}")
        print(f"运行错误：{e}")
        import traceback
        traceback.print_exc()
    finally:
        await app.stop()


if __name__ == "__main__":
    asyncio.run(main())

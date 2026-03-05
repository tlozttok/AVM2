#!/usr/bin/env python3
"""
Agent 网络 + AVBash 终端 测试程序

网络规模：10 个 Agent（不包括输入输出 Agent）
每个 Agent 的输入连接数和输出连接数都是 1

TEST 标签用于阻断 AVBash 输出，防止网络激活
"""

import asyncio
from driver.driver import AgentSystem
from driver.net import AgentNetwork
from AVBash.terminal_agents import TerminalPair


# ==================== TEST 标签控制 ====================
# 设置为 True 时，会阻断 AVBash 的输出，防止网络被激活
# 设置为 False 时，AVBash 正常输出，网络会正常激活
TEST = True
# =====================================================


async def main():
    # 创建 Agent 系统
    system = AgentSystem()

    # 创建 Agent 网络（10 个 Agent）
    network = AgentNetwork(system)
    agents = network.create_network(num_agents=10)

    print(f"已创建 {len(agents)} 个 Agent")

    # 创建终端对（AVBash）
    terminal_pair = TerminalPair(fps=10)
    input_agent, output_agent = terminal_pair.create_agents()

    # 将终端 Agent 添加到系统
    system.add_agent(input_agent)
    system.add_agent(output_agent)

    # 将终端连接到网络
    network.connect_io_agent(input_agent)
    network.connect_io_agent(output_agent)

    # 打印连接统计
    stats = network.get_connection_stats()
    print("\n网络连接统计:")
    print(f"  - Agent 总数：{stats['total_agents']}")
    print(f"  - 输入连接总数：{stats['total_input_connections']}")
    print(f"  - 输出连接总数：{stats['total_output_connections']}")
    print(f"  - InputAgent 数量：{stats['input_agents_count']}")
    print(f"  - OutputAgent 数量：{stats['output_agents_count']}")

    # 打印每个 Agent 的连接信息
    print("\nAgent 连接详情:")
    for i, agent in enumerate(agents):
        print(f"  Agent {i+1}:")
        print(f"    ID: {agent.id[:8]}...")
        print(f"    输入连接：{len(agent.input_connection)} 个")
        for sender_id, keyword in agent.input_connection:
            print(f"      <- {sender_id[:8]}... (keyword: {keyword})")
        print(f"    输出连接：{len(agent.output_connection)} 个")
        for keyword, receiver_id in agent.output_connection:
            print(f"      -> {receiver_id[:8]}... (keyword: {keyword})")

    # 启动终端
    await terminal_pair.start()

    # 设置消息回调
    def on_message(msg):
        if TEST:
            # TEST 模式下，不显示消息
            return
        print(f"[终端消息] {msg}")

    terminal_pair.set_message_callback(on_message)

    # 设置渲染回调
    def on_render(render_text):
        if TEST:
            # TEST 模式下，不显示渲染输出
            return
        # 清屏并渲染
        print("\033[2J\033[H", end="")
        print(render_text)

    terminal_pair.set_render_callback(on_render)

    print("\n" + "=" * 60)
    if TEST:
        print("TEST 模式：AVBash 输出已阻断，网络不会被激活")
        print("如需启用网络，请将 TEST 标签设置为 False")
    else:
        print("正常运行模式：AVBash 正常输出")
    print("=" * 60)

    # 启动所有 Agent 处理循环
    await system.start_all_agents()

    # 启动所有输入 Agent
    await system.start_all_input_agents()

    print("\n系统已启动，按 Ctrl+C 退出...")

    try:
        # 保持运行
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        print("\n正在停止系统...")
    finally:
        # 清理资源
        await system.stop_all_input_agents()
        await system.stop_all_agents()
        await terminal_pair.stop()
        print("系统已停止")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已中断")

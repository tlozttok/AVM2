#!/usr/bin/env python3
"""
终端命令行程序
直接在命令行中运行多窗口终端
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from AVBash.terminal import TerminalManager


async def main():
    """主函数"""
    print("=" * 60)
    print("AVM2 多窗口终端")
    print("=" * 60)
    print()
    print("使用说明：")
    print("  - 普通文本直接输入到焦点窗口")
    print("  - 以 / 开头的为控制命令（如 /help 查看帮助）")
    print("  - 输入 // 表示字面的 / 字符")
    print("  - 按 Ctrl+C 退出")
    print()

    # 创建终端管理器
    term = TerminalManager(fps=10)

    # 当前输入行
    input_buffer = []

    def on_render(text):
        """渲染回调"""
        # 清屏并显示渲染结果
        os.system('clear' if os.name != 'nt' else 'cls')
        print(text)
        print()
        # 显示输入提示
        if term.focused_window_id and term.focused_window_id in term.windows:
            window = term.windows[term.focused_window_id]
            prompt = f"[窗口{window.id}] 输入：{window.input_buffer}"
        else:
            prompt = "[无焦点窗口]"
        print(prompt, end='', flush=True)
        # 重新输出用户已输入的字符
        for ch in ''.join(input_buffer):
            print(ch, end='', flush=True)

    def on_message(msg):
        """消息回调"""
        print(f"\n{msg}\n", end='', flush=True)

    term.set_render_callback(on_render)
    term.set_message_callback(on_message)

    # 启动终端
    await term.start()

    # 异步读取用户输入
    loop = asyncio.get_event_loop()

    try:
        while term._running:
            # 使用线程池运行阻塞的 input()
            try:
                user_input = await loop.run_in_executor(None, input)
            except (EOFError, KeyboardInterrupt):
                break

            if user_input == 'quit' or user_input == '/quit':
                break

            # 发送输入到终端
            await term.feed_input(user_input + '\n')

    except KeyboardInterrupt:
        pass
    finally:
        await term.stop()
        print("\n终端已退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n终端已退出")

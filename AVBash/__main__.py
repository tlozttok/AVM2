#!/usr/bin/env python3
"""
终端命令行程序
直接在命令行中运行多窗口终端
支持逐字符输入显示
"""

import asyncio
import sys
import os
import tty
import termios

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
    print("  - Ctrl+C 退出")
    print()

    # 创建终端管理器（不指定 cols，使用终端实际宽度）
    term = TerminalManager(fps=10)

    def on_render(text):
        """渲染回调"""
        # 清屏并移动光标到左上角
        sys.stdout.write('\x1b[2J\x1b[H\x1b[3J')
        # 将 \n 替换为 \r\n 确保回车换行
        sys.stdout.write(text.replace('\n', '\r\n'))
        sys.stdout.write('\r\n')
        sys.stdout.flush()

    def on_message(msg):
        """消息回调"""
        pass  # 消息已经在渲染中显示

    def on_message(msg):
        """消息回调"""
        pass  # 消息已经在渲染中显示

    term.set_render_callback(on_render)
    term.set_message_callback(on_message)

    # 启动终端
    await term.start()

    # 保存原始终端设置
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)

    try:
        # 设置为原始模式
        tty.setraw(fd)

        # 异步读取用户输入（逐字符）
        loop = asyncio.get_event_loop()

        async def read_char():
            """异步读取单个字符"""
            return await loop.run_in_executor(None, lambda: sys.stdin.read(1))

        while term._running:
            try:
                ch = await read_char()

                if not ch:
                    break

                # Ctrl+C 退出
                if ch == '\x03':
                    break

                # Enter 提交
                if ch == '\r' or ch == '\n':
                    # 手动打印回车换行
                    sys.stdout.write('\r\n')
                    sys.stdout.flush()
                    await term.feed_input('\n')
                else:
                    # 逐字符发送到终端
                    await term.feed_input(ch)
                    # 手动回显字符（原始模式下不会自动显示）
                    sys.stdout.write(ch)
                    sys.stdout.flush()

            except (EOFError, KeyboardInterrupt):
                break

    except KeyboardInterrupt:
        pass
    finally:
        # 恢复终端设置
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        await term.stop()
        os.system('clear' if os.name != 'nt' else 'cls')
        print("\n终端已退出")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n终端已退出")

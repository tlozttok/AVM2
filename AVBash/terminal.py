#!/usr/bin/env python3
"""
多窗口终端模块
实现异步流式输入输出的多窗口终端，每个窗口运行独立的 Shell
"""

import asyncio
import os
import pty
import re
import time
from typing import Optional, Callable, Dict, List


# ANSI 转义码正则表达式
ANSI_ESCAPE_PATTERN = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')


def strip_ansi(text: str) -> str:
    """去除 ANSI 转义码"""
    return ANSI_ESCAPE_PATTERN.sub('', text)


class Window:
    """
    单个终端窗口
    管理一个 Shell 子进程及其相关的输入输出缓冲
    """

    def __init__(self, window_id: int, title: str = None, rows: int = 24, cols: int = 80):
        self.id = window_id
        self.title = title or f"Shell {window_id}"
        self.rows = rows
        self.cols = cols

        # Shell 进程相关
        self.shell_process: Optional[asyncio.subprocess.Process] = None
        self.shell_reader: Optional[asyncio.StreamReader] = None
        self.shell_writer: Optional[asyncio.StreamWriter] = None
        self._read_task: Optional[asyncio.Task] = None
        self._process_running = False

        # 缓冲区
        self.screen_buffer: List[str] = []      # 历史输出行
        self.input_buffer: str = ""             # 当前未提交的输入行
        self.scroll_offset: int = 0             # 向上滚动的行数偏移
        self.visible_rows: int = 20             # 可视区域行数

        # 状态
        self.shell_exited: bool = False
        self.last_command: str = ""             # 最后一次提交的命令
        self.last_command_status: str = ""      # 最后命令的执行状态

        self._output_callbacks: List[Callable[[str], None]] = []

    def add_output_callback(self, callback: Callable[[str], None]):
        """添加输出回调 - 当有新输出时通知"""
        self._output_callbacks.append(callback)

    async def start_shell(self, shell_cmd: str = "/bin/bash"):
        """启动 Shell 子进程"""
        try:
            # 创建伪终端
            master_fd, slave_fd = pty.openpty()

            # 启动子进程
            self.shell_process = await asyncio.create_subprocess_exec(
                shell_cmd,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env={**os.environ, 'TERM': 'xterm-256color'},
                close_fds=True
            )

            # 关闭子进程端的文件描述符
            os.close(slave_fd)

            # 设置主进程端的非阻塞读取
            self._master_fd = master_fd

            # 创建 StreamReader 来读取输出
            self.shell_reader = asyncio.StreamReader()
            protocol = asyncio.StreamReaderProtocol(self.shell_reader)

            # 将文件描述符包装为 asyncio 可读的
            loop = asyncio.get_event_loop()
            self._read_transport, _ = await loop.connect_read_pipe(
                lambda: asyncio.streams.FlowControlMixin(protocol, loop),
                os.fdopen(master_fd, 'rb', 0)
            )

            # 创建 StreamWriter 来写入输入
            write_transport = await loop.connect_write_pipe(
                asyncio.streams.FlowControlMixin,
                os.fdopen(master_fd, 'wb', 0)
            )
            self.shell_writer = asyncio.StreamWriter(write_transport, protocol, self.shell_reader, loop)

            self._process_running = True

            # 启动读取任务
            self._read_task = asyncio.create_task(self._read_shell_output())

        except Exception as e:
            raise RuntimeError(f"启动 Shell 失败：{e}")

    async def _read_shell_output(self):
        """异步读取 Shell 输出"""
        buffer = ""
        try:
            while self._process_running:
                try:
                    # 读取数据
                    data = await asyncio.wait_for(
                        self.shell_reader.read(4096),
                        timeout=0.1
                    )
                    if not data:
                        # Shell 退出
                        self.shell_exited = True
                        break

                    # 解码并添加到缓冲区
                    text = data.decode('utf-8', errors='replace')
                    buffer += text

                    # 按行分割处理
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        if line:
                            # 去除 ANSI 码后存储
                            clean_line = strip_ansi(line)
                            self.screen_buffer.append(clean_line)

                    # 通知有新的输出
                    for callback in self._output_callbacks:
                        try:
                            callback(f"[Window {self.id}] 新输出")
                        except:
                            pass

                except asyncio.TimeoutError:
                    await asyncio.sleep(0.01)
                except asyncio.IncompleteReadError as e:
                    if e.partial:
                        text = e.partial.decode('utf-8', errors='replace')
                        buffer += text
                    self.shell_exited = True
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.shell_exited = True

    async def write_input(self, text: str):
        """向 Shell 写入输入"""
        if self.shell_writer and not self.shell_exited:
            try:
                self.shell_writer.write(text.encode('utf-8'))
                await self.shell_writer.drain()
            except Exception as e:
                self.shell_exited = True

    async def submit_input(self):
        """提交输入缓冲区内容给 Shell"""
        if self.input_buffer:
            self.last_command = self.input_buffer
            command = self.input_buffer + "\n"
            self.input_buffer = ""
            await self.write_input(command)

    def get_visible_content(self) -> List[str]:
        """获取当前可见的历史行（考虑滚动偏移）"""
        total_lines = len(self.screen_buffer)
        start_idx = max(0, total_lines - self.visible_rows - self.scroll_offset)
        end_idx = max(0, total_lines - self.scroll_offset)
        return self.screen_buffer[start_idx:end_idx]

    def scroll_up(self, lines: int = 10):
        """向上滚动"""
        max_scroll = max(0, len(self.screen_buffer) - self.visible_rows)
        self.scroll_offset = min(max_scroll, self.scroll_offset + lines)

    def scroll_down(self, lines: int = 10):
        """向下滚动"""
        self.scroll_offset = max(0, self.scroll_offset - lines)

    def search(self, pattern: str) -> List[tuple]:
        """在历史中搜索，返回匹配的行号和内容"""
        results = []
        try:
            regex = re.compile(pattern, re.IGNORECASE)
            for i, line in enumerate(self.screen_buffer):
                if regex.search(line):
                    results.append((i, line))
        except re.error:
            # 正则表达式错误，使用简单匹配
            for i, line in enumerate(self.screen_buffer):
                if pattern.lower() in line.lower():
                    results.append((i, line))
        return results

    async def cleanup(self):
        """清理资源"""
        self._process_running = False

        if self._read_task:
            self._read_task.cancel()
            try:
                await self._read_task
            except asyncio.CancelledError:
                pass

        if self.shell_writer:
            self.shell_writer.close()

        if self.shell_process:
            try:
                self.shell_process.terminate()
                await asyncio.wait_for(self.shell_process.wait(), timeout=2.0)
            except Exception:
                try:
                    self.shell_process.kill()
                except:
                    pass


class TerminalManager:
    """
    多窗口终端管理器
    独立的终端核心，不依赖 Agent 基类
    通过 create_agents() 方法创建 InputAgent 和 OutputAgent 子类来接入网络
    """

    def __init__(self, fps: int = 10, default_rows: int = 20, default_cols: int = 80):
        self.fps = fps
        self.default_rows = default_rows
        self.default_cols = default_cols

        # 窗口管理
        self.windows: Dict[int, Window] = {}
        self.next_window_id: int = 1
        self.focused_window_id: Optional[int] = None

        # 渲染回调
        self.render_callback: Optional[Callable[[str], None]] = None

        # 异步任务
        self._render_task: Optional[asyncio.Task] = None
        self._running = False

        # 命令帮助
        self.commands_help = {
            "enter": "提交当前输入",
            "new [title]": "创建新窗口",
            "kill [id]": "关闭窗口",
            "focus <id>": "切换焦点",
            "list": "列出所有窗口",
            "scroll up|down [lines]": "滚动窗口",
            "search <pattern>": "搜索历史",
            "title [new_title]": "设置/查看标题",
            "resize <rows> <cols>": "调整窗口大小",
            "help": "显示帮助",
        }

        # 消息输出回调（用于发送 info/error 消息）
        self.message_callback: Optional[Callable[[str], None]] = None

    def create_agents(self):
        """创建用于接入 Agent 网络的 InputAgent 和 OutputAgent 子类"""
        from .terminal_agents import TerminalInputAgent, TerminalOutputAgent

        input_agent = TerminalInputAgent(self)
        output_agent = TerminalOutputAgent(self)
        return input_agent, output_agent

    def set_render_callback(self, callback: Callable[[str], None]):
        """设置渲染输出回调"""
        self.render_callback = callback

    def set_message_callback(self, callback: Callable[[str], None]):
        """设置消息输出回调（用于 info/error 消息）"""
        self.message_callback = callback

    async def start(self):
        """启动终端管理器"""
        self._running = True

        # 创建第一个默认窗口
        await self._create_window("Main Shell")

        # 启动渲染任务
        self._render_task = asyncio.create_task(self._render_loop())

    async def stop(self):
        """停止终端管理器，清理所有资源"""
        self._running = False

        if self._render_task:
            self._render_task.cancel()
            try:
                await self._render_task
            except asyncio.CancelledError:
                pass

        # 清理所有窗口
        for window in list(self.windows.values()):
            await window.cleanup()

        self.windows.clear()
        self.focused_window_id = None

    async def _render_loop(self):
        """定时渲染循环"""
        frame_interval = 1.0 / self.fps
        while self._running:
            try:
                start_time = time.time()

                # 生成渲染文本
                rendered = self.render_windows()

                # 调用回调
                if self.render_callback and rendered:
                    try:
                        self.render_callback(rendered)
                    except Exception as e:
                        pass

                # 控制帧率
                elapsed = time.time() - start_time
                sleep_time = max(0, frame_interval - elapsed)
                await asyncio.sleep(sleep_time)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await asyncio.sleep(frame_interval)

    # ==================== 核心输入处理 ====================

    async def feed_input(self, text: str):
        """
        接收输入文本，解析并处理
        支持控制命令（以 / 开头）和普通字符输入
        // 表示字面的 / 字符
        """
        # 处理转义：// → 特殊标记
        text = text.replace("//", "\x00ESCAPED_SLASH\x00")

        # 按行分割处理
        lines = text.split('\n')

        for line in lines:
            # 恢复转义的 /
            line = line.replace("\x00ESCAPED_SLASH\x00", "/")

            if line.startswith('/'):
                # 解析命令
                await self._execute_command(line[1:])
            elif self.focused_window_id and self.focused_window_id in self.windows:
                # 普通字符输入到焦点窗口
                window = self.windows[self.focused_window_id]
                window.input_buffer += line
                if text.endswith('\n'):
                    window.input_buffer += '\n'

    async def _execute_command(self, command_str: str):
        """执行控制命令"""
        parts = command_str.strip().split(maxsplit=1)
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        handlers = {
            "enter": lambda: self._cmd_enter(),
            "new": lambda: self._cmd_new(args),
            "kill": lambda: self._cmd_kill(args),
            "focus": lambda: self._cmd_focus(args),
            "list": lambda: self._cmd_list(),
            "scroll": lambda: self._cmd_scroll(args),
            "search": lambda: self._cmd_search(args),
            "title": lambda: self._cmd_title(args),
            "resize": lambda: self._cmd_resize(args),
            "help": lambda: self._cmd_help(),
        }

        handler = handlers.get(cmd)
        if handler:
            try:
                await handler()
            except Exception as e:
                await self._send_error(f"命令 '{cmd}' 执行失败：{e}")
        else:
            await self._send_error(f"未知命令：{cmd}")

    # ==================== 命令实现 ====================

    async def _cmd_enter(self):
        """提交输入"""
        window = self._get_focused_window()
        if window:
            await window.submit_input()

    async def _cmd_new(self, args: str):
        """创建新窗口"""
        title = args.strip() if args.strip() else None
        await self._create_window(title)

    async def _cmd_kill(self, args: str):
        """关闭窗口"""
        if args.strip():
            try:
                window_id = int(args.strip())
                await self._close_window(window_id)
            except ValueError:
                await self._send_error(f"无效的窗口 ID: {args}")
        else:
            # 关闭当前焦点窗口
            if self.focused_window_id:
                await self._close_window(self.focused_window_id)

    async def _cmd_focus(self, args: str):
        """切换焦点"""
        try:
            window_id = int(args.strip())
            if window_id in self.windows:
                self.focused_window_id = window_id
                self.windows[window_id].scroll_offset = 0
            else:
                await self._send_error(f"窗口 {window_id} 不存在")
        except ValueError:
            await self._send_error(f"无效的窗口 ID: {args}")

    async def _cmd_list(self):
        """列出所有窗口"""
        if not self.windows:
            await self._send_info("当前没有窗口")
            return

        result = ["窗口列表:"]
        for wid, window in sorted(self.windows.items()):
            marker = "►" if wid == self.focused_window_id else " "
            last_line = window.screen_buffer[-1][:50] if window.screen_buffer else "(空)"
            result.append(f"  {marker} [{wid}] {window.title}: {last_line}")

        await self._send_info('\n'.join(result))

    async def _cmd_scroll(self, args: str):
        """滚动窗口"""
        window = self._get_focused_window()
        if not window:
            return

        parts = args.strip().split()
        if not parts:
            await self._send_error("用法：/scroll up|down [lines]")
            return

        direction = parts[0].lower()
        lines = int(parts[1]) if len(parts) > 1 else 10

        if direction == "up":
            window.scroll_up(lines)
        elif direction == "down":
            window.scroll_down(lines)
        else:
            await self._send_error(f"未知滚动方向：{direction} (使用 up 或 down)")

    async def _cmd_search(self, args: str):
        """搜索历史"""
        window = self._get_focused_window()
        if not window:
            return

        if not args.strip():
            await self._send_error("用法：/search <pattern>")
            return

        results = window.search(args.strip())
        if results:
            lines = [f"找到 {len(results)} 条匹配:"]
            for line_num, content in results[:10]:  # 限制显示 10 条
                lines.append(f"  [{line_num}] {content[:60]}")
            if len(results) > 10:
                lines.append(f"  ... 还有 {len(results) - 10} 条")
            await self._send_info('\n'.join(lines))
        else:
            await self._send_info(f"未找到匹配 '{args.strip()}' 的行")

    async def _cmd_title(self, args: str):
        """设置/查看标题"""
        window = self._get_focused_window()
        if not window:
            return

        if args.strip():
            window.title = args.strip()
        else:
            await self._send_info(f"当前窗口标题：{window.title}")

    async def _cmd_resize(self, args: str):
        """调整窗口大小"""
        window = self._get_focused_window()
        if not window:
            return

        parts = args.strip().split()
        if len(parts) < 2:
            await self._send_error("用法：/resize <rows> <cols>")
            return

        try:
            rows = int(parts[0])
            cols = int(parts[1])
            window.visible_rows = rows
            window.cols = cols
        except ValueError:
            await self._send_error("无效的行数/列数")

    async def _cmd_help(self):
        """显示帮助"""
        lines = ["可用命令:"]
        for cmd, desc in sorted(self.commands_help.items()):
            lines.append(f"  /{cmd:<15} {desc}")
        await self._send_info('\n'.join(lines))

    # ==================== 窗口管理 ====================

    async def _create_window(self, title: str = None) -> Optional[Window]:
        """创建新窗口"""
        window_id = self.next_window_id
        self.next_window_id += 1

        window = Window(window_id, title, self.default_rows, self.default_cols)

        try:
            await window.start_shell()
            self.windows[window_id] = window
            self.focused_window_id = window_id
            return window
        except Exception as e:
            await self._send_error(f"创建窗口失败：{e}")
            self.next_window_id -= 1
            return None

    async def _close_window(self, window_id: int):
        """关闭窗口"""
        if window_id not in self.windows:
            await self._send_error(f"窗口 {window_id} 不存在")
            return

        window = self.windows[window_id]
        await window.cleanup()
        del self.windows[window_id]

        # 如果关闭的是焦点窗口，切换到另一个窗口
        if self.focused_window_id == window_id:
            if self.windows:
                self.focused_window_id = next(iter(self.windows.keys()))
            else:
                self.focused_window_id = None

    def _get_focused_window(self) -> Optional[Window]:
        """获取焦点窗口"""
        if self.focused_window_id and self.focused_window_id in self.windows:
            return self.windows[self.focused_window_id]
        return None

    # ==================== 渲染 ====================

    def render_windows(self) -> str:
        """
        渲染所有窗口为纯文本
        焦点窗口显示完整内容，非焦点窗口显示摘要
        """
        if not self.windows:
            return "[终端] 没有活动窗口 - 使用 /new 创建窗口"

        result = []

        for window_id, window in sorted(self.windows.items()):
            if window_id == self.focused_window_id:
                # 焦点窗口 - 完整渲染
                rendered = self._render_focused_window(window)
            else:
                # 非焦点窗口 - 摘要渲染
                rendered = self._render_unfocused_window(window)
            result.append(rendered)

        return '\n'.join(result)

    def _render_focused_window(self, window: Window) -> str:
        """渲染焦点窗口"""
        lines = []
        lines.append("╔" + "═" * (window.cols - 2) + "╗")

        # 标题栏
        title = f"► {window.title} [ID:{window.id}] "
        title_len = len(title) + 10  # 加上 ANSI 码长度估算
        lines.append("║" + title + " " * (window.cols - title_len - 2) + "║")
        lines.append("╠" + "═" * (window.cols - 2) + "╣")

        # 历史内容
        visible = window.get_visible_content()
        for _ in range(window.visible_rows - len(visible)):
            visible.append("")

        for line in visible[:window.visible_rows]:
            display_line = line[:window.cols - 2] if len(line) < window.cols - 2 else line[:window.cols - 2]
            lines.append("║" + display_line + " " * (window.cols - len(display_line) - 2) + "║")

        # 输入行
        lines.append("╠" + "═" * (window.cols - 2) + "╣")
        input_line = f"$ {window.input_buffer}"[:window.cols - 2]
        lines.append("║" + input_line + " " * (window.cols - len(input_line) - 2) + "║")
        lines.append("╚" + "═" * (window.cols - 2) + "╝")

        # 滚动指示
        if window.scroll_offset > 0:
            lines.append(f"(已向上滚动 {window.scroll_offset} 行)")

        return '\n'.join(lines)

    def _render_unfocused_window(self, window: Window) -> str:
        """渲染非焦点窗口（摘要模式）"""
        last_line = window.screen_buffer[-1][:50] if window.screen_buffer else "(无输出)"
        status = "运行中" if not window.shell_exited else "已退出"

        lines = [
            f"[窗口 {window.id}] {window.title} - {status}",
            f"  最后输出：{last_line}",
        ]
        return '\n'.join(lines)

    # ==================== 辅助方法 ====================

    async def _send_info(self, message: str):
        """发送信息消息"""
        if self.message_callback:
            self.message_callback(f"[INFO] {message}")

    async def _send_error(self, message: str):
        """发送错误消息"""
        if self.message_callback:
            self.message_callback(f"[ERROR] {message}")


# ==================== 使用示例 ====================

async def main():
    """示例使用"""
    term = TerminalManager(fps=10)

    # 设置渲染回调（这里打印到控制台）
    term.set_render_callback(lambda text: print(text + "\n" + "-" * 40))

    await term.start()

    try:
        # 模拟输入
        await term.feed_input("echo Hello World")
        await asyncio.sleep(0.5)
        await term.feed_input("/enter")
        await asyncio.sleep(1)

        # 创建新窗口
        await term.feed_input("/new Second Shell")
        await asyncio.sleep(0.5)

        # 列出窗口
        await term.feed_input("/list")
        await asyncio.sleep(1)

    finally:
        await term.stop()


if __name__ == "__main__":
    asyncio.run(main())

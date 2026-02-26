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


def display_width(text: str) -> int:
    """计算字符串的显示宽度"""
    # 使用 wcwidth 库或简单计算：中文字符宽度为 2，其他为 1
    width = 0
    for char in text:
        # CJK 字符宽度为 2
        if '\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f':
            width += 2
        else:
            width += 1
    return width


def truncate_to_width(text: str, max_width: int) -> str:
    """截断字符串到指定显示宽度"""
    result = ""
    current_width = 0
    for char in text:
        char_width = 2 if ('\u4e00' <= char <= '\u9fff' or '\u3000' <= char <= '\u303f') else 1
        if current_width + char_width > max_width:
            break
        result += char
        current_width += char_width
    return result


class Window:
    """
    单个终端窗口
    管理一个 Shell 子进程及其相关的输入输出缓冲
    """

    def __init__(self, window_id: int, title: str = None, rows: int = 24, cols: int = None):
        self.id = window_id
        self.title = title or f"Shell {window_id}"
        self.rows = rows
        # 如果没有指定 cols，使用默认值 60（保守值，适配大多数终端）
        self.cols = cols if cols is not None else 60

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
        self.visible_rows: int = rows - 4       # 可视区域行数（减去标题和边框）

        # 状态
        self.shell_exited: bool = False
        self.last_command: str = ""             # 最后一次提交的命令
        self.last_command_status: str = ""      # 最后命令的执行状态

        self._output_callbacks: List[Callable[[str], None]] = []

    def add_output_callback(self, callback: Callable[[str], None]):
        """添加输出回调 - 当有新输出时通知"""
        self._output_callbacks.append(callback)

    async def start_shell(self, shell_cmd: str = None):
        """启动 Shell 子进程"""
        try:
            # 创建伪终端
            master_fd, slave_fd = pty.openpty()

            # 启动子进程 - 使用 bash 的交互模式
            if shell_cmd is None:
                shell_cmd = "/bin/bash"

            # 使用 preexec_fn 来创建新会话，避免进程组警告
            import subprocess

            self.shell_process = await asyncio.create_subprocess_exec(
                shell_cmd,
                "--norc", "--noprofile",  # 不加载配置文件
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                env={**os.environ, 'TERM': 'xterm-256color'},
                close_fds=True,
                start_new_session=True  # 创建新会话，避免进程组警告
            )

            # 关闭子进程端的文件描述符
            os.close(slave_fd)

            # 设置为非阻塞模式
            import fcntl
            flags = fcntl.fcntl(master_fd, fcntl.F_GETFL)
            fcntl.fcntl(master_fd, fcntl.F_SETFL, flags | os.O_NONBLOCK)

            self._master_fd = master_fd
            self._process_running = True

            # 启动读取任务
            loop = asyncio.get_event_loop()
            self._read_task = asyncio.create_task(self._read_shell_output())

        except Exception as e:
            os.close(master_fd)
            raise RuntimeError(f"启动 Shell 失败：{e}")

    async def _read_shell_output(self):
        """异步读取 Shell 输出"""
        buffer = ""
        loop = asyncio.get_event_loop()

        try:
            while self._process_running:
                try:
                    # 使用线程池读取数据（避免阻塞事件循环）
                    data = await loop.run_in_executor(
                        None,
                        lambda: os.read(self._master_fd, 4096)
                    )

                    if not data:
                        # Shell 退出（EOF）
                        self.shell_exited = True
                        break

                    # 解码并添加到缓冲区
                    text = data.decode('utf-8', errors='replace')
                    buffer += text

                    # 按行分割处理
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        # 检测是否包含 bash 提示符（表示命令已完成）
                        clean_line = strip_ansi(line).strip()
                        # 提示符格式通常是 "bash-X.Y$ " 或 "user@host:~$ "
                        if clean_line.endswith('$') or (clean_line.startswith('bash') and '$' in clean_line):
                            # 命令完成
                            if self.last_command_status == "running":
                                self.last_command_status = "success"
                        # 检测错误消息
                        elif 'error' in clean_line.lower() or 'command not found' in clean_line.lower() or 'no such file' in clean_line.lower():
                            self.last_command_status = "error"

                        # 直接存储原始行
                        self.screen_buffer.append(line)

                    # 通知有新的输出
                    for callback in self._output_callbacks:
                        try:
                            callback(f"[Window {self.id}] 新输出")
                        except:
                            pass

                except BlockingIOError:
                    # 没有数据，等待一下
                    await asyncio.sleep(0.05)
                except OSError:
                    self.shell_exited = True
                    break

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.shell_exited = True

    async def write_input(self, text: str):
        """向 Shell 写入输入"""
        if self._process_running and not self.shell_exited and hasattr(self, '_master_fd'):
            try:
                # 直接写入文件描述符
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    None,
                    lambda: os.write(self._master_fd, text.encode('utf-8'))
                )
            except Exception as e:
                self.shell_exited = True

    async def submit_input(self):
        """提交输入缓冲区内容给 Shell"""
        if self.input_buffer:
            self.last_command = self.input_buffer
            self.last_command_status = "running"  # 假设命令开始执行
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

        # 关闭 master fd
        if hasattr(self, '_master_fd'):
            try:
                os.close(self._master_fd)
            except:
                pass

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

    def __init__(self, fps: int = 10, default_rows: int = 20, default_cols: int = None):
        self.fps = fps
        self.default_rows = default_rows
        # 如果没有指定 cols，则使用当前终端宽度
        if default_cols is None:
            try:
                self.default_cols = os.get_terminal_size().columns
            except OSError:
                self.default_cols = 60  # 默认值
        else:
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

        # 全局输入缓冲区 - 用户在 AVBash 层面的输入
        self.global_input_buffer: str = ""

        # 消息缓冲区 - 存储最近的控制命令反馈消息
        self.message_buffer: List[str] = []
        self.max_message_lines: int = 5  # 最多显示的消息行数

    def create_agents(self):
        """创建用于接入 Agent 网络的 InputAgent 和 OutputAgent 子类"""
        from AVBash.terminal_agents import TerminalInputAgent, TerminalOutputAgent

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

        注意：逐字符输入时，每个字符单独调用此方法
        命令检查只在回车时进行
        """
        # 处理转义：// → 特殊标记（用于字面的 /）
        text = text.replace("//", "\x00ESCAPED_SLASH\x00")

        # 检查是否以换行符结尾（表示需要提交）
        should_submit = text.endswith('\n')

        # 按行分割处理
        lines = text.split('\n')

        for i, line in enumerate(lines):
            # 恢复转义的 /
            line = line.replace("\x00ESCAPED_SLASH\x00", "/")

            # 跳过空行（通常是换行符分割产生的）
            if not line:
                continue

            # 逐字符输入时，直接添加到缓冲区（不检查是否为命令）
            self.global_input_buffer += line

        # 回车时检查和执行命令
        if should_submit:
            await self._handle_submit()

    def _submit_global_input(self):
        """提交全局输入缓冲区内容到焦点窗口"""
        if self.global_input_buffer and self.focused_window_id:
            window = self.windows.get(self.focused_window_id)
            if window:
                window.input_buffer = self.global_input_buffer
        self.global_input_buffer = ""

    async def _handle_submit(self):
        """处理回车提交：检查是否为命令或输入到 shell"""
        if not self.global_input_buffer:
            return

        if self.global_input_buffer.startswith('/'):
            # 控制命令：执行命令
            command_str = self.global_input_buffer[1:]  # 去掉开头的 /
            self.global_input_buffer = ""  # 清空缓冲区
            await self._execute_command(command_str)
        else:
            # 普通输入：提交到焦点窗口的 shell
            self._submit_global_input()
            # 同时提交到 shell（添加换行符）
            window = self._get_focused_window()
            if window:
                await window.submit_input()

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
        """提交输入 - 等同于回车"""
        await self._handle_submit()

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

        await self._send_info("窗口列表:")
        for wid, window in sorted(self.windows.items()):
            marker = "►" if wid == self.focused_window_id else " "
            last_line = window.screen_buffer[-1][:50] if window.screen_buffer else "(空)"
            await self._send_info(f"  {marker} [{wid}] {window.title}: {last_line}")

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
            await self._send_info(f"找到 {len(results)} 条匹配:")
            for line_num, content in results[:10]:  # 限制显示 10 条
                await self._send_info(f"  [{line_num}] {content[:60]}")
            if len(results) > 10:
                await self._send_info(f"  ... 还有 {len(results) - 10} 条")
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
        await self._send_info("命令列表:")
        for cmd, desc in sorted(self.commands_help.items()):
            # 缩短每行长度
            await self._send_info(f"  /{cmd}: {desc}")

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
        布局顺序（从上到下）：
        1. 其他非焦点窗口（摘要渲染）
        2. 焦点窗口（完整渲染）
        3. 消息显示区
        4. 输入显示区（最底部）
        """
        result = []

        # 1. 渲染非焦点窗口（顶部）
        for window_id, window in sorted(self.windows.items()):
            if window_id != self.focused_window_id:
                rendered = self._render_unfocused_window(window)
                result.append(rendered)

        # 2. 渲染焦点窗口（完整）
        if self.focused_window_id and self.focused_window_id in self.windows:
            focused_window = self.windows[self.focused_window_id]
            rendered = self._render_focused_window(focused_window)
            result.append(rendered)
        elif not self.windows:
            result.append("[终端] 没有活动窗口 - 使用 /new 创建窗口")

        # 3. 消息显示区 - 直接逐行添加
        result.append("-- 消息 --")
        if self.message_buffer:
            for msg in self.message_buffer[-self.max_message_lines:]:
                result.append(f"  {msg}")
        else:
            result.append("  (无消息)")

        # 4. 输入显示区（最底部）
        result.append(self._render_input_area())

        return '\n'.join(result)

    def _render_focused_window(self, window: Window) -> str:
        """渲染焦点窗口"""
        lines = []
        inner_width = window.cols - 2  # 减去左右边框

        lines.append("╔" + "═" * inner_width + "╗")

        # 标题栏
        title = f"► {window.title} [ID:{window.id}] "
        title_padded = truncate_to_width(title, inner_width)
        title_padded = title_padded + " " * (inner_width - display_width(title_padded))
        lines.append("║" + title_padded + "║")

        lines.append("╠" + "═" * inner_width + "╣")

        # 历史内容
        visible = window.get_visible_content()
        # 只填充到 visible_rows 行，但不超过必要
        while len(visible) < window.visible_rows:
            visible.append("")

        for line in visible[:window.visible_rows]:
            # 先去除 ANSI 码
            clean_line = strip_ansi(line)
            # 将 tab 替换为 4 个空格
            clean_line = clean_line.replace('\t', '    ')
            # 处理 \r：按 \r 分割，处理覆盖逻辑
            # 如果 \r 在中间，后面的内容覆盖前面；如果 \r 在末尾，忽略
            parts = clean_line.split('\r')
            # 过滤掉空字符串（\r 在末尾产生的）
            non_empty_parts = [p for p in parts if p]
            # 如果有多个非空部分，最后一个覆盖了前面的
            clean_line = non_empty_parts[-1] if non_empty_parts else ""
            # 截断到窗口宽度
            display_line = truncate_to_width(clean_line, inner_width)
            # 用空格填充到宽度
            display_width_filled = display_width(display_line)
            display_line = display_line + " " * (inner_width - display_width_filled)
            lines.append("║" + display_line + "║")

        # 输入行
        lines.append("╠" + "═" * inner_width + "╣")
        input_line = truncate_to_width(f"$ {window.input_buffer}", inner_width)
        input_line = input_line + " " * (inner_width - display_width(input_line))
        lines.append("║" + input_line + "║")

        lines.append("╚" + "═" * inner_width + "╝")

        # 滚动指示
        if window.scroll_offset > 0:
            lines.append(f"(已向上滚动 {window.scroll_offset} 行)")

        return '\n'.join(lines)

        return '\n'.join(lines)

    def _render_unfocused_window(self, window: Window) -> str:
        """渲染非焦点窗口（摘要模式）"""
        # 获取最后一行非提示符的输出
        last_output = "(无输出)"
        for line in reversed(window.screen_buffer):
            clean = strip_ansi(line).strip()
            # 跳过提示符行
            if clean.endswith('$') or clean.startswith('bash'):
                continue
            if clean:
                # 处理 tab 和 \r
                clean = clean.replace('\t', '    ')
                if clean.endswith('\r'):
                    clean = clean[:-1]
                else:
                    clean = clean.split('\r')[-1]
                last_output = clean.strip()[:50]
                break

        # 最后命令
        last_command = window.last_command if window.last_command else "(无命令)"

        # 执行状态
        if window.shell_exited:
            status = "已退出"
        elif window.last_command_status == "error":
            status = "报错"
        elif window.last_command_status == "success":
            status = "成功"
        elif window.last_command_status == "running":
            status = "运行中"
        else:
            status = "空闲"

        lines = [
            f"[窗口 {window.id}] {window.title}",
            f"  状态：{status}",
            f"  最后命令：{last_command}",
            f"  最后输出：{last_output}",
        ]
        return '\n'.join(lines)

    def _render_input_area(self) -> str:
        """渲染输入显示区 - 显示用户当前输入"""
        prompt = "AVBash$ "
        input_text = self.global_input_buffer if self.global_input_buffer else "(等待输入...)"
        return f"{prompt}{input_text}"

    # ==================== 辅助方法 ====================

    def _add_message(self, message: str):
        """添加消息到缓冲区"""
        self.message_buffer.append(message)
        # 限制消息数量
        if len(self.message_buffer) > self.max_message_lines:
            self.message_buffer.pop(0)

    async def _send_info(self, message: str):
        """发送信息消息"""
        self._add_message(f"[INFO] {message}")
        if self.message_callback:
            self.message_callback(f"[INFO] {message}")

    async def _send_error(self, message: str):
        """发送错误消息"""
        self._add_message(f"[ERROR] {message}")
        if self.message_callback:
            self.message_callback(f"[ERROR] {message}")


# ==================== 使用示例 ====================

async def main():
    """示例使用"""
    from .terminal_agents import TerminalPair

    # 创建终端对
    pair = TerminalPair(fps=10)

    # 设置渲染回调（直接打印到控制台）
    pair.set_render_callback(lambda text: print(text + "\n" + "-" * 40))

    await pair.start()

    try:
        # 模拟输入
        await pair.send_command("echo Hello World")
        await asyncio.sleep(0.5)
        await pair.send_command("/enter")
        await asyncio.sleep(1)

        # 创建新窗口
        await pair.send_command("/new Second Shell")
        await asyncio.sleep(0.5)

        # 列出窗口
        await pair.send_command("/list")
        await asyncio.sleep(1)

    finally:
        await pair.stop()


if __name__ == "__main__":
    asyncio.run(main())

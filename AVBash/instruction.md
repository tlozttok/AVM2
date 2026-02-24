请编写一个Python终端模块，满足以下要求：

### 总体目标
实现一个**异步流式输入输出的多窗口终端**，每个窗口运行一个独立的Shell（如bash），能够接受外部字符输入（来自AI Agent）并实时更新内部状态，同时以固定帧率输出当前所有窗口的纯文本渲染结果。终端应支持窗口创建、删除、焦点切换、滚动、搜索等控制命令。

### 核心特性
1. **多窗口多Shell**  
   - 每个窗口关联一个独立的Shell子进程（通过伪终端pty）。  
   - 每个窗口拥有独立的输入缓冲区（未提交行）、屏幕历史行列表、滚动偏移量。  
   - 支持动态创建和销毁窗口。

2. **焦点窗口**  
   - 同时只有一个窗口处于活动状态（焦点窗口），接收外部输入字符。  
   - 非焦点窗口的Shell继续运行，渲染时只显示摘要或指定展开。

3. **输入处理**  
   - 外部输入的普通字符追加到焦点窗口的输入缓冲区，不立即发送给Shell。  
   - 输入中的控制命令（以`/`开头）用于操作终端本身（如`/enter`提交输入、`/new`创建窗口等）。  
   - 支持转义：连续两个`//`表示一个字面`/`字符。

4. **异步机制**  
   - 所有与Shell子进程的读写操作必须是非阻塞的（使用`asyncio`）。  
   - 终端内部维护每个窗口的读事件（捕获Shell输出），将输出行添加到屏幕历史。  
   - 外部输入通过队列或方法调用传入，终端内部异步处理。

5. **帧率控制渲染输出**  
   - 终端不立即返回每次输入后的结果，而是以固定帧率（例如每秒10次）生成当前所有窗口的渲染文本，并通过回调或事件发送给外部。  
   - 渲染文本采用纯文本格式，清晰描述每个窗口的内容（例如窗口标题、历史行、当前输入行等，非焦点窗口只显示标题、上次的命令和执行状态）。  
   - 渲染函数应支持滚动偏移，仅显示窗口可视区域的行数（可配置行数，如20行）。

6. **控制命令支持**  
   至少实现以下命令（通过输入中的`/cmd`形式触发）：
   - `/enter`：提交焦点窗口的输入缓冲区内容给Shell，清空缓冲区。
   - `/new [title]`：创建新窗口，标题可选，自动设为焦点。
   - `/kill [id]`：关闭指定窗口（默认当前），若焦点窗口被关闭则切换到另一个窗口。
   - `/focus <id>`：切换焦点到指定窗口。
   - `/list`：列出所有窗口ID、标题、最后一行摘要。
   - `/scroll up|down [lines]`：在当前窗口中向上/下滚动指定行数（默认10）。
   - `/search <pattern>`：在当前窗口历史中搜索，返回匹配行。
   - `/title [new_title]`：设置或查看当前窗口标题。
   - `/resize <rows> <cols>`：调整窗口的显示尺寸（影响渲染行数）。
   - `/help`：显示命令帮助。

### 数据结构建议
```python
class Window:
    id: int
    title: str
    shell_process: asyncio.subprocess.Process  # 通过pty运行
    shell_reader: asyncio.StreamReader          # 读取shell输出
    shell_writer: asyncio.StreamWriter          # 写入shell输入
    screen_buffer: list[str]                     # 历史行（包含输出和已提交输入行）
    input_buffer: str                             # 当前未提交输入行
    scroll_offset: int                             # 向上滚动的行数偏移
    visible_rows: int = 20                         # 可视区域行数
    # 其他状态
```

### 外部接口（供AI Agent调用）
建议设计一个`Terminal`类，提供以下异步方法：
- `async def feed_input(self, text: str)`: 接收来自AI的输入（可能包含多个字符或命令）。该方法解析输入，更新内部状态，但不立即输出。
- `def set_render_callback(self, callback: Callable[[str], None])`: 设置渲染输出回调函数，终端将定期（固定帧率）调用该回调，传入当前所有窗口的渲染文本。
- `async def start(self)`: 启动终端内部循环（监听shell输出、定时渲染等）。
- `async def stop(self)`: 停止所有子进程，清理资源。

### 实现要点
1. **伪终端（pty）**：使用`asyncio`的`create_subprocess_exec`结合`pty`选项，或者使用`pexpect`的异步版本（但需轻量）。推荐标准库`asyncio.subprocess`配合`pty`参数。
2. **异步读写**：为每个窗口创建`asyncio.create_task`循环读取`shell_reader`，将输出行添加到`screen_buffer`（考虑行缓冲，按行分割）。
3. **输入命令解析**：`feed_input`中检测以`/`开头的令牌，若是命令则执行相应操作，否则将字符追加到焦点窗口的`input_buffer`。
4. **渲染帧率**：终端启动一个异步任务，每`1/fps`秒收集所有窗口的渲染文本，调用回调。
5. **渲染函数**：`def render_windows(self) -> str`：遍历所有窗口，为每个窗口生成文本块。焦点窗口完整显示历史行（考虑滚动）和当前输入行；非焦点窗口可显示摘要（如最后一行）。用简单ASCII边框或分隔线区分窗口。

### 示例使用流程
```python
async def main():
    term = Terminal(fps=10)
    term.set_render_callback(lambda text: print(text))  # 实际应发给AI
    await term.start()
    
    # 模拟AI输入字符
    await term.feed_input("git st")          # 字符追加到输入缓冲区
    await asyncio.sleep(0.1)
    await term.feed_input("/enter")          # 提交命令
    await asyncio.sleep(2)
    
    await term.stop()
```

### 注意事项
- 控制命令的解析需要处理转义（`//`）。
- Shell输出可能包含ANSI转义码，为简化可先去除或保留（但渲染时可能需要处理），目前可简单按原始文本存储。
- 滚动操作只影响渲染视图，不改变历史。
- 窗口销毁时应正确终止子进程。

请根据以上要求生成完整的Python代码，包括必要的注释和错误处理。代码应模块化、易于集成到现有AI Agent框架中。
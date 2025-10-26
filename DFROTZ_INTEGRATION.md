# dfrotz 集成文档

## 重构改进

### 1. 使用 asyncio.create_subprocess_exec

**之前**: 使用 `subprocess.Popen`
```python
self.process = subprocess.Popen(
    [self.dfrotz_path, self.game_file],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1,
    universal_newlines=True
)
```

**现在**: 使用 `asyncio.create_subprocess_exec`
```python
self.process = await asyncio.create_subprocess_exec(
    self.dfrotz_path,
    self.game_file,
    stdin=asyncio.subprocess.PIPE,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
    bufsize=0  # 无缓冲，立即输出
)
```

### 2. 异步字节流操作

**输入输出操作**:
- 使用 `await self.process.stdout.readline()` 异步读取字节数据
- 使用 `.decode('utf-8', errors='replace')` 解码字节为字符串
- 使用 `.encode('utf-8')` 编码字符串为字节数据
- 使用 `self.process.stdin.write()` + `await self.process.stdin.drain()` 异步写入
- 使用 `await self.process.wait()` 异步等待进程结束

### 3. 改进的分页处理

**分页检测**:
- `***MORE***` - 标准分页提示
- `[MORE]` - 方括号格式
- `(MORE)` - 圆括号格式  
- `--more--` - 破折号格式
- `-- More --` - 带空格的格式

**自动处理**:
- 检测到分页提示时自动发送回车键
- 过滤分页提示，不包含在最终输出中
- 添加适当等待让dfrotz处理分页

### 4. 贪婪读取优化

**读取策略**:
- 一次性读取所有可用的输出行
- 合并为完整输出块放入队列
- 减少频繁的队列操作

**获取策略**:
- 一次性获取队列中所有输出块
- 合并为完整输出字符串
- 提高输出完整性

## 系统架构

```
UserInputAgent -> Agent -> DfrotzOutputAgent -> dfrotz进程 -> DfrotzInputAgent -> ConsoleOutputAgent
                                     ↑
                                     ↓
                               自动分页处理
```

## 核心类

### DfrotzManager
- 管理dfrotz进程生命周期
- 处理异步输入输出
- 自动分页处理
- 完整的日志记录

### DfrotzOutputAgent
- 接收系统消息
- 发送给dfrotz作为输入
- 管理dfrotz进程启动/停止

### DfrotzInputAgent
- 监控dfrotz输出
- 发送给连接的Agent
- 自动处理分页

## 使用示例

### 基本使用
```python
from game_env.environment import DfrotzManager

manager = DfrotzManager("game.z5", "dfrotz.exe")
await manager.start()
await manager.send_text("look")
output = await manager.get_output()
await manager.stop()
```

### 系统集成
```python
from game_env.environment import DfrotzInputAgent, DfrotzOutputAgent

# 创建代理
dfrotz_output = DfrotzOutputAgent("game.z5", "dfrotz.exe")
dfrotz_input = DfrotzInputAgent(dfrotz_manager)

# 添加到系统
system.add_io_agent(dfrotz_output)
system.add_io_agent(dfrotz_input)

# 建立连接
agent.output_connection.append(("dfrotz_command", dfrotz_output.id))
dfrotz_input.output_connections.append(console_output.id)
```

## 测试脚本

- `test_async_dfrotz.py` - 测试异步功能
- `test_pagination.py` - 测试分页功能  
- `demo_dfrotz_system.py` - 完整系统演示

## 优势

1. **真正的异步**: 使用asyncio原生子进程管理
2. **字节流处理**: 正确处理字节数据，避免编码问题
3. **更好的性能**: 无阻塞的输入输出操作
4. **自动分页**: 无需手动处理分页
5. **完整日志**: 详细的运行状态监控
6. **健壮性**: 改进的错误处理和进程管理
7. **编码安全**: 使用UTF-8解码，处理编码错误

## 注意事项

- 确保dfrotz可执行文件路径正确
- 游戏文件需要存在且可访问
- 系统需要适当的权限运行外部进程
- 异步操作需要正确处理异常
# AVM2 可视化监控工具

## 概述

基于 Web 的实时监控系统，用于可视化 AVM2 Agent 网络的运行状态。

## 架构

```
核心程序 (driver.py)
    ↓ (写入 JSONL 日志)
logs/system.jsonl
    ↓ (文件监控)
log_monitor.py
    ↓ (WebSocket 推送)
server.py → 前端页面
```

## 使用方式

### 1. 启动监控服务器

```bash
# 在项目根目录执行
python -m utils.visual_monitor --port 8765
```

### 2. 访问 Web 界面

在浏览器打开：`http://localhost:8765`

### 3. 启动核心程序

在另一个终端运行你的 AVM2 程序：

```bash
python main.py
```

## 日志格式

所有日志都输出为 JSONL 格式到 `logs/system.jsonl`：

```json
{
  "timestamp_us": 1709701234567890,
  "level": "info",
  "source": "Agent.xxx",
  "event_type": "agent_created",
  "data": {
    "agent_id": "xxx",
    "agent_type": "Agent",
    "object_addr": "0x...",
    "queue_addr": "0x..."
  }
}
```

## 关键事件类型

| 事件类型 | 说明 | 数据字段 |
|---------|------|---------|
| `agent_created` | Agent 创建 | agent_id, agent_type, object_addr, queue_addr |
| `input_connection_set` | 输入连接建立 | sender_id, keyword |
| `output_connection_set` | 输出连接建立 | receiver_id, keyword |
| `message_received` | 消息接收 | sender, keyword, message_length, queue_size_* |

## 三层监控模式

通过环境变量 `AVM2_LOG_MODE` 控制：

- **CONTENT** (默认): 基础拓扑图 + 日志流
- **DETAIL**: + 对象引用、队列状态
- **ARCH**: + 异步任务、事件循环信息

```bash
export AVM2_LOG_MODE=DETAIL
python -m utils.visual_monitor
```

## 文件结构

```
utils/visual_monitor/
├── __init__.py          # 模块入口
├── __main__.py          # 命令行入口
├── server.py            # WebSocket/HTTP服务器
├── log_monitor.py       # 日志文件监控器
├── unified_logger.py    # 统一 JSONL 日志记录器
├── templates/
│   └── index.html       # Web 界面
└── static/
    ├── app.js           # Vue 3 前端应用
    └── styles.css       # 样式
```

## 功能

### 当前实现
- 实时日志流显示
- 网络拓扑图可视化
- Agent 列表和详情
- 连接关系显示
- WebSocket 实时推送

### 计划实现
- 实时激活热力图（DETAIL 模式）
- 异步任务监控面板（ARCH 模式）
- 事件循环状态可视化
- 日志过滤和搜索

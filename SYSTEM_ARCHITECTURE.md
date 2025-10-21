# AVM2 系统架构说明

## 系统概述

AVM2 是一个基于 Agent 的异步消息传递系统，采用 Input-Agent-Output 的连接模式。系统严格区分系统内连接和系统-外界交互。

## 核心组件

### 1. AgentSystem
- 管理所有 Agent 和 IOAgent
- 提供消息总线 (MessageBus)
- 处理 Agent 的注册和注销

### 2. MessageBus
- 负责 Agent 之间的消息传递
- 维护 Agent 注册表
- 异步消息路由

## Agent 类型

### 1. Agent (核心代理)
**系统内组件**，具有 LLM 能力

**关键属性:**
- `id`: 唯一标识符
- `state`: 内部状态
- `input_connection`: 输入连接列表 [(sender_id, keyword)]
- `output_connection`: 输出连接列表 [(keyword, receiver_id)]
- `input_cache`: 输入消息缓存
- `pre_prompt`: 系统级提示词

**核心方法:**
- `explore()`: **系统内** - 将自己标记为可被发现
- `seek(keyword)`: **系统内** - 主动寻找输出连接
- `activate()`: 触发 LLM 处理
- `process_response()`: 解析 LLM 响应

### 2. InputAgent (输入代理)
**边界组件**，连接系统与外界输入

**关键属性:**
- `output_connections`: 输出连接列表
- `_running`: 运行状态
- `_task`: 异步任务

**核心方法:**
- `seek_signal(message)`: **系统内** - 根据消息决定是否寻找输出连接
- `collect_data()`: **系统-外界** - 从外界收集数据
- `start()`/`stop()`: 控制运行循环

### 3. OutputAgent (输出代理)
**边界组件**，连接系统与外界输出

**关键属性:**
- `input_connections`: 输入连接列表

**核心方法:**
- `explore(message)`: **系统内** - 根据消息决定是否探索输入连接
- `execute_data(data)`: **系统-外界** - 向外界执行输出

## 连接管理

### 系统内连接
- **Agent ↔ Agent**: 通过 MessageBus 传递消息
- **连接建立**: 通过 explore/seek 机制动态建立
- **连接类型**: 输入连接和输出连接

### 系统-外界交互
- **InputAgent ← 外界**: 收集外部数据
- **OutputAgent → 外界**: 执行外部输出

## 消息流

```
外界 → InputAgent → Agent → Agent → OutputAgent → 外界
     (collect_data)  (MessageBus)  (MessageBus)  (execute_data)
```

## 关键概念澄清

### seek 和 explore 的准确含义

**seek (寻找)**
- **范围**: 系统内
- **方向**: 输出方向
- **行为**: 主动寻找接收者
- **示例**: Agent.seek() 寻找输出连接

**explore (探索)**
- **范围**: 系统内  
- **方向**: 输入方向
- **行为**: 被动允许被发现
- **示例**: Agent.explore() 允许被其他 Agent 发现

**IOAgent 的特殊性**
- InputAgent.seek_signal: 系统内 - 决定是否寻找输出
- OutputAgent.explore: 系统内 - 决定是否探索输入
- InputAgent.collect_data: 系统-外界 - 获取外部数据
- OutputAgent.execute_data: 系统-外界 - 执行外部输出

## 设计原则

1. **Agent 不可继承**: Agent 行为完全由输入和 LLM 决定
2. **严格边界**: 清晰区分系统内和系统-外界交互
3. **动态连接**: 通过 explore/seek 机制实现自组织
4. **异步处理**: 所有消息传递都是异步的
5. **状态驱动**: Agent 状态影响 LLM 响应处理

## 典型工作流程

1. InputAgent 从外界收集数据
2. 通过 MessageBus 发送给连接的 Agent
3. Agent 处理消息，可能触发 LLM
4. LLM 响应被解析，可能包含连接指令
5. Agent 根据指令建立/断开连接
6. 最终结果通过 OutputAgent 输出到外界
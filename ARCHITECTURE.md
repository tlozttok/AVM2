# AVM2 系统架构设计

基于拉康三界理论和语义自举范式的AI系统架构。

## 1. 核心架构设计

### 三界分离架构

#### 象征界（Symbolic Register）
- **功能**: 知识库和配置存储，存储所有Agent配置和语义信息
- **实现**: YAML配置文件系统
- **包含**: 
  - Agent配置（Agents/目录）
  - 系统配置（config.json）
  - 消息缓存和连接关系

#### 想象界（Imaginary Register）
- **功能**: 运行时上下文和语义处理层
- **实现**: Agent运行时状态和消息处理
- **包含**:
  - Agent激活上下文
  - 消息缓存（bg_message_cache, input_message_cache）
  - LLM语义处理

#### 实在界（Real Register）
- **功能**: 物理世界反馈和执行层
- **实现**: 系统Agent和实际执行
- **包含**:
  - 系统Agent（InputAgent/OutputAgent/IOAgent）
  - 用户交互（GUI窗口）
  - 系统监控和执行反馈

## 2. 核心组件

### Agent 系统

#### Agent 基类
```python
class Agent(Loggable):
    """微Agent实体基类"""
    - id: Agent唯一标识
    - prompt: LLM提示词
    - input_connections: 输入连接映射
    - output_connections: 输出连接映射
    - message_caches: 消息缓存
    - sync_to_file() / sync_from_file(): 文件同步
```

#### 系统Agent抽象类
- **InputAgent**: 系统输入Agent，将现实世界转化为字符串消息
- **OutputAgent**: 系统输出Agent，将字符串消息转化为实际行动
- **IOAgent**: InputAgent和OutputAgent的结合版本

#### 消息系统
- **MessageBus**: 异步消息总线，管理Agent间通信
- **AgentMessage**: 标准消息格式
- **异步处理**: 使用asyncio实现非阻塞消息传递

### 系统Agent实现

#### UserInputAgent
- **类型**: InputAgent
- **功能**: 通过GUI窗口收集用户输入
- **特性**: 
  - Tkinter GUI界面
  - 多线程支持
  - 实时输入队列

#### AgentCreatorOutputAgent
- **类型**: OutputAgent
- **功能**: 创建普通Agent的系统输出Agent

#### SystemMonitorInputAgent
- **类型**: InputAgent
- **功能**: 系统监控输入Agent，定期报告系统状态

## 3. 数据流设计

### Agent激活流程
```
触发激活 → 上下文构建 → 消息处理 → LLM处理 → 输出解析 → 消息发送
```

### 文件同步流程
```
Agent状态变化 → 自动同步 → YAML文件更新 → 系统重启恢复
```

### 消息传递流程
```
发送Agent → MessageBus → 接收Agent → 消息处理 → 响应生成
```

## 4. 文件结构设计

### 核心模块
```
driver/
├── driver.py             # Agent基类、消息总线、文件同步
├── system_agents.py      # 系统Agent抽象类
└── async_system.py       # 异步系统
```

### 系统Agent实现
```
system_interface_agents/
├── user_input_agent.py              # 用户输入Agent
├── agent_creator_output_agent.py    # Agent创建器
└── system_monitor_input_agent.py    # 系统监控器
```

### 配置管理
```
Agents/
├── genesis_agent.yaml               # 初始Agent
└── SystemAgents/
    ├── user_input_agent.yaml        # 用户输入Agent配置
    ├── agent_creator_agent.yaml     # Agent创建器配置
    └── system_monitor_agent.yaml    # 系统监控器配置
```

### 工具模块
```
utils/
└── logger.py             # 日志系统
```

## 5. 配置系统

### Agent配置格式
```yaml
id: agent_id
prompt: |
  多行提示词内容
input_connections:
  sender_id: input_channel
output_connections:
  output_channel: [receiver_ids]
input_message_keyword:
  - activation_keywords
metadata:
  type: Agent/InputAgent/OutputAgent
  class_name: ClassName  # 系统Agent专用
```

### 系统配置
```json
{
  "system": {
    "architecture": "Three-layer architecture",
    "context_management": {
      "default_stateless": true,
      "message_driven": true
    },
    "agent_activation_modes": [
      "subject_activation",
      "passive_activation", 
      "trigger_activation"
    ]
  }
}
```

## 6. 异步设计

### 异步消息总线
- 使用asyncio.Queue实现消息队列
- 支持并发消息处理
- 避免阻塞系统运行

### Agent异步方法
- `async def receive_message()`: 异步接收消息
- `async def send_message()`: 异步发送消息
- `async def _activate()`: 异步激活处理

## 7. 日志系统

### 日志格式
```
[时间] 类名.方法名(行号)[级别]:消息内容
```

### 日志级别
- **DEBUG**: 详细调试信息
- **INFO**: 常规操作信息
- **WARNING**: 警告信息
- **ERROR**: 错误信息

### 日志文件
- 每个类有独立的日志文件
- 存储在logs/目录
- 支持UTF-8编码

## 8. 系统启动流程

1. **配置扫描**: 递归扫描Agents文件夹下的YAML文件
2. **动态创建**: 使用eval(class_name)根据配置创建Agent实例
3. **状态同步**: 调用sync_from_file加载Agent状态
4. **系统注册**: 将Agent注册到AgentSystem
5. **启动运行**: 启动消息总线，运行系统
6. **GUI启动**: 启动用户输入GUI窗口

## 9. 设计原则

### 语义自举原则
- 表达能力等价性
- 语义体系与编程体系分离
- 文件同步机制

### 工程实践原则
- 类型注解
- 异步编程
- 模块化设计
- 错误处理
- 日志记录

## 10. 扩展性设计

### 系统Agent扩展
- 继承InputAgent/OutputAgent/IOAgent基类
- 实现抽象方法
- 创建对应的YAML配置文件

### 配置驱动
- 所有行为通过配置定义
- 支持运行时配置修改
- 无硬编码逻辑

### 插件化架构
- 系统Agent作为插件
- 动态加载和卸载
- 独立开发和测试
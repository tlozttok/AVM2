# AVM2 - 语义自举系统

基于拉康三界理论的实验性AI系统，通过语义自举范式实现智能的涌现。

## 当前开发状态

**开发阶段**: 基础框架实现完成，系统Agent已重构  
**当前焦点**: 系统运行和调试  
**技术栈**: Python + OpenAI API + Tkinter GUI  
**架构**: 三界分离架构（实在界、想象界、象征界）

## 项目结构

```
AVM2/
├── driver/                    # 核心驱动模块
│   ├── driver.py             # Agent基类、消息总线、文件同步
│   ├── system_agents.py      # 系统Agent抽象类（InputAgent/OutputAgent/IOAgent）
│   └── async_system.py       # 异步系统
├── system_interface_agents/  # 系统Agent具体实现
│   ├── agent_creator_output_agent.py    # Agent创建器
│   ├── system_monitor_input_agent.py    # 系统监控器
│   └── user_input_agent.py              # 用户输入Agent（带GUI）
├── Agents/                   # Agent配置
│   ├── genesis_agent.yaml    # 初始Agent
│   └── SystemAgents/         # 系统Agent配置
│       ├── agent_creator_agent.yaml     # Agent创建器配置
│       ├── system_monitor_agent.yaml    # 系统监控器配置
│       └── user_input_agent.yaml        # 用户输入Agent配置
├── utils/                    # 工具模块
│   └── logger.py             # 日志系统
├── logs/                     # 日志文件目录
├── main.py                   # 系统入口（支持调试模式）
├── config.json               # 系统配置
├── example_agent.yaml        # 普通Agent配置示例
├── example_input_agent.yaml  # 输入Agent配置示例
├── TODO.md                   # 开发计划
├── QWEN.md                   # 项目知识库
├── ARCHITECTURE.md           # 系统架构设计
├── Start.md                  # 项目理念和理论基础
└── README.md                 # 项目说明
```

## 核心特性

### 🚀 语义自举机制
- **三界分离**: 实在界（物理世界反馈）、想象界（语义处理）、象征界（知识库）
- **微Agent架构**: RNA式原初实体，主体性极弱，不决策不规划
- **语义-实在转换**: 系统Agent是实在界与想象界的交界点

### 🔄 实时文件同步
- **自动状态持久化**: Agent激活时自动同步状态到YAML文件
- **消息缓存持久化**: `bg_message_cache`和`input_message_cache`完整保存
- **调试模式**: 可禁用自动同步，便于调试

### 🏗️ 模块化系统Agent
- **独立文件结构**: 每个系统Agent在独立文件中实现
- **动态类型创建**: 使用`eval(class_name)`根据YAML配置动态创建实例
- **抽象接口**: InputAgent/OutputAgent/IOAgent抽象基类

### 📡 异步消息系统
- **异步消息总线**: 管理Agent间的消息传递
- **消息队列**: 异步处理消息，避免阻塞
- **连接管理**: 输入/输出连接映射

### 🖥️ 用户交互界面
- **GUI输入**: 通过Tkinter窗口收集用户输入
- **实时反馈**: 输入状态实时显示
- **多线程支持**: GUI与系统运行分离

## 快速开始

### 环境配置
1. 创建`.env`文件：
```bash
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
```

### 运行系统
```bash
python main.py
```

### 调试模式
编辑`main.py`中的`DEBUG_MODE = True`可禁用自动文件同步。

## 系统Agent

### 已实现
- **AgentCreatorOutputAgent**: 创建普通Agent的系统输出Agent
- **SystemMonitorInputAgent**: 系统监控输入Agent，定期报告系统状态
- **UserInputAgent**: 用户输入Agent，通过GUI窗口收集用户输入

### 计划中（见TODO.md）
- **系统Agent探查Agent**: 查询系统内可用的系统Agent及其使用方法

## 开发理念

### 第一性原理
- **表达能力等价性**: 新Agent表达能力 ≥ 原Agent表达能力
- **语义体系与编程体系分离**: YAML配置描述语义，Python类实现逻辑
- **文件同步机制**: 所有Agent类必须实现`sync_to_file`和`sync_from_file`方法

### 工程实践
- **类型注解**: 所有方法参数和返回值使用类型注解
- **异步编程**: 统一使用`async/await`处理异步操作
- **模块化设计**: driver/包含核心组件，system_interface_agents/包含具体实现
- **日志系统**: 统一的日志记录和文件输出

## 核心洞察

- **伪代码理解**: 伪代码是示意，不能运行，需要实现为可执行代码
- **简单性原则**: 避免过度设计，直接实现需求
- **动态类型使用**: Python的`eval()`可以简化动态对象创建
- **不要硬编码**: 使用配置驱动而非硬编码逻辑

## 贡献指南

1. 遵循现有的代码风格和项目结构
2. 所有Agent类必须实现文件同步方法
3. 系统Agent需要独立的YAML配置文件
4. 使用异步编程模式
5. 添加适当的日志记录

## 许可证

MIT License
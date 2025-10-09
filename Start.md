# AVM2 语义自举系统 - 实践指南

## 项目概述

AVM2是一个基于拉康三界理论和语义自举范式的实验性AI系统。系统通过构造一个场域，让智能有机会从符号与实在的耦合中涌现。

## 快速开始

### 环境要求
- Python 3.8+
- 依赖包：`pip install -r requirements.txt`
- OpenAI API密钥

### 系统配置

1. **环境变量配置**
创建 `.env` 文件：
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-3.5-turbo
```

2. **系统运行**
```bash
python main.py
```

3. **调试模式**
编辑 `main.py` 中的 `DEBUG_MODE` 变量：
```python
DEBUG_MODE = True  # 禁用自动文件同步，便于调试
```

## 系统架构

### 三界分离

#### 象征界（Symbolic Register）
- **位置**: `Agents/` 目录下的YAML配置文件
- **内容**: Agent配置、连接关系、消息缓存
- **特点**: 人类可编辑的语义配置

#### 想象界（Imaginary Register）
- **位置**: Agent运行时状态
- **内容**: 激活上下文、消息处理、LLM交互
- **特点**: 动态构建的语义处理层

#### 实在界（Real Register）
- **位置**: 系统Agent实现
- **内容**: 用户交互、系统监控、实际执行
- **特点**: 物理世界反馈和执行

### 核心组件

#### Agent 系统
- **Agent基类**: 提供基础Agent功能
- **消息总线**: 异步消息传递
- **文件同步**: 状态持久化

#### 系统Agent类型
- **InputAgent**: 将现实世界转化为字符串消息
- **OutputAgent**: 将字符串消息转化为实际行动
- **IOAgent**: 结合输入输出功能

## 系统Agent使用

### 用户输入Agent
- **功能**: 通过GUI窗口收集用户输入
- **启动**: 系统启动时自动创建GUI窗口
- **使用**: 在窗口中输入文本，点击"发送"按钮

### Agent创建器
- **功能**: 创建普通Agent的系统输出Agent
- **配置**: 通过YAML文件定义创建规则

### 系统监控器
- **功能**: 定期报告系统状态
- **输出**: 系统运行状态和性能指标

## 开发指南

### 创建新系统Agent

1. **创建Python类**
```python
from driver.system_agents import InputAgent

class MyInputAgent(InputAgent):
    def __init__(self, id: str, message_bus = None):
        super().__init__(id, message_bus)
        self.logger.info(f"MyInputAgent {self.id} 初始化完成")
    
    async def collect_input(self) -> Optional[str]:
        # 实现输入收集逻辑
        pass
    
    def should_activate(self, input_data: str) -> bool:
        # 实现激活判断逻辑
        pass
    
    def format_message(self, input_data: str) -> str:
        # 实现消息格式化逻辑
        pass
```

2. **创建YAML配置**
```yaml
id: my_input_agent
class_name: MyInputAgent
input_connections: {}
output_connections:
  my_output: ["target_agent"]
input_message_keyword: []
metadata:
  type: InputAgent
  version: "1.0"
  description: "我的输入Agent描述"
```

3. **放置文件**
- Python类: `system_interface_agents/my_input_agent.py`
- YAML配置: `Agents/SystemAgents/my_input_agent.yaml`

### 配置Agent连接

在YAML文件中定义连接关系：
```yaml
input_connections:
  sender_agent: input_channel

output_connections:
  output_channel: ["receiver_agent1", "receiver_agent2"]

input_message_keyword:
  - activation_keyword1
  - activation_keyword2
```

### 日志系统使用

系统使用统一的日志系统：
```python
self.logger.info("操作信息")
self.logger.debug("调试信息")
self.logger.warning("警告信息")
self.logger.error("错误信息")
```

日志文件保存在 `logs/` 目录，每个类有独立的日志文件。

## 调试技巧

### 调试模式
设置 `DEBUG_MODE = True` 可以：
- 禁用自动文件同步
- 避免状态文件被意外修改
- 便于测试和调试

### 日志查看
- 查看 `logs/` 目录下的日志文件
- 日志格式: `[时间] 类名.方法名(行号)[级别]:消息内容`

### 消息追踪
- 通过日志追踪消息传递路径
- 查看Agent激活状态
- 监控系统运行状态

## 常见问题

### GUI窗口不显示
- 确保系统有图形界面支持
- 检查Tkinter是否正确安装
- 查看日志文件中的错误信息

### Agent无法激活
- 检查input_message_keyword配置
- 验证连接关系是否正确
- 查看消息缓存状态

### 文件同步失败
- 检查文件权限
- 验证YAML格式是否正确
- 查看日志中的错误信息

## 设计理念

### 语义自举
智能从符号与实在的耦合中涌现，而不是通过预设规则设计。

### 微Agent架构
弱主体性的原初实体，通过组合实现复杂行为。

### 演化机制
通过淘汰和奖励机制实现系统自我优化。

## 扩展开发

### 添加新功能
1. 遵循现有代码风格
2. 实现必要的抽象方法
3. 添加适当的日志记录
4. 创建对应的配置文件

### 系统集成
- 支持新的输入输出方式
- 扩展系统Agent类型
- 集成外部服务和API

## 贡献指南

1. 遵循项目代码风格
2. 添加适当的类型注解
3. 使用异步编程模式
4. 实现文件同步方法
5. 添加详细的日志记录

---

**核心原则**: 智能不再是设计的结果，而是淘汰的残余。语义自举通过构造一个场域，让智能有机会从符号与实在的耦合中涌现。
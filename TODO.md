# AVM2 系统开发 TODO

## 已完成
- ✅ 重构系统Agent类到独立文件
  - `agent_creator_output_agent.py` - Agent创建器
  - `system_monitor_input_agent.py` - 系统监控器

## 待实现需求

### 1. 用户输入Agent
- **功能**: 提供用户与系统的交互接口
- **类型**: InputAgent
- **描述**: 接收用户输入，转换为系统内部消息格式
- **实现要点**:
  - 支持多种输入方式（命令行、文件、API等）
  - 消息格式标准化
  - 错误处理和用户反馈

### 2. 系统Agent探查Agent
- **功能**: 向系统发送"有什么系统Agent可用，怎么用"查询
- **类型**: IOAgent（需要消息输入才会输出）
- **描述**: 查询系统内可用的系统Agent及其使用方法
- **实现要点**:
  - 动态发现系统Agent
  - 生成使用说明文档
  - 支持语义查询

### 3. 自动创建系统Agent YAML文件
- **功能**: 在创建系统Agent类时自动生成对应的YAML配置文件
- **描述**: 确保每个系统Agent都有对应的配置文件，便于系统加载
- **实现要点**:
  - 类装饰器或基类自动生成
  - 配置模板管理
  - 文件路径自动计算

## 设计原则
1. **语义自举**: 保持语义体系与编程体系的分离
2. **三界分离**: 实在界（物理世界反馈）、想象界（语义处理）、象征界（知识库）
3. **微Agent架构**: RNA式原初实体，主体性极弱
4. **表达能力等价性**: 新Agent表达能力 ≥ 原Agent表达能力

## 技术规范
- 所有Agent类必须实现 `sync_to_file` 和 `sync_from_file` 方法
- 系统Agent YAML文件必须包含 `class_name` 字段
- 使用动态类型创建：`eval(class_name)`
- 统一异步编程模式：`async/await`

## 文件结构
```
system_interface_agents/
├── agent_creator_output_agent.py    # Agent创建器
├── system_monitor_input_agent.py    # 系统监控器
├── user_input_agent.py              # [TODO] 用户输入Agent
└── system_explorer_agent.py         # [TODO] 系统探查Agent
```

## 优先级
1. 用户输入Agent - 提供基础交互能力
2. 系统Agent探查Agent - 增强系统自描述性  
3. 自动YAML创建 - 简化系统Agent部署
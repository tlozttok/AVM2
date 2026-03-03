# 提示词迁移计划 - pre_prompt 0228 到新版

## 概述

本文档记录了从旧提示词 `utils/resources/pre_prompt 0228.md` 迁移到新提示词 `driver/pre_prompt.md` 所需的代码变更。

## 提示词差异对比

### 信号系统变更

| 信号类型 | 旧版 (0228.md) | 新版 (pre_prompt.md) | 操作 |
|---------|---------------|---------------------|------|
| EXPLORE | ✓ | ✗ | 移除 |
| STOP_EXPLORE | ✓ | ✗ | 移除 |
| SEEK | ✓ | ✗ | 移除 |
| SPLIT | ✓ | ✗ | 移除 |
| REJECT_INPUT | ✓ | ✓ | 保留 |
| ACCEPT_INPUT | ✓ | ✓ | 保留 |
| SET_OUTPUT | ✗ | ✓ | 新增 |
| REJECT_OUTPUT | ✗ | ✓ | 新增 |

### 新增内容

1. **第 5 节 "决定自己的身份"** - Agent 根据输入识别模式，随机选择身份并专注
2. **第 6 节 "神经元启发的连接管理"** - 详细的连接评估准则，强调赫布学习等神经科学概念

---

## 代码变更清单

### 文件：driver/driver.py

#### 1. AgentSystem 类

**已删除**：
```python
# 第 74 行
self.explore_agent = []
```

**需要删除的方法**：

```python
# 约 175-178 行
def add_explore_agent(self, agent:str):
    self.logger.debug(f"添加探索代理：{agent}")
    self.explore_agent.append(agent)
    self.logger.info(f"代理 {agent} 已添加到探索列表，当前探索代理数：{len(self.explore_agent)}")

# 约 180-186 行
def stop_explore_agent(self, agent:str):
    self.logger.debug(f"停止探索代理：{agent}")
    if agent in self.explore_agent:
        self.explore_agent.remove(agent)
        self.logger.info(f"代理 {agent} 已从探索列表移除，当前探索代理数：{len(self.explore_agent)}")
    else:
        self.logger.warning(f"尝试停止不在探索列表中的代理：{agent}")

# 约 188-195 行
def seek_agent(self, keyword:str):
    self.logger.debug(f"寻找关键字 '{keyword}' 的探索代理")
    if not self.explore_agent:
        self.logger.warning("探索代理列表为空，无法寻找代理")
        return None
    agent = random.choice(self.explore_agent)
    self.logger.info(f"为关键字 '{keyword}' 找到探索代理：{agent}")
    return agent

# 约 197-203 行
def split_agent(self, state, connection):
    self.logger.info(f"系统级别 Agent 分裂，状态：{state}, 连接数：{len(connection)}")
    new_agent = Agent()
    new_agent.state = state
    new_agent.input_connection = connection
    self.add_agent(new_agent)
    self.logger.info(f"新 Agent {new_agent.id} 已创建并添加到系统")
```

#### 2. Agent 类

**需要删除的方法**：

```python
# 约 351-353 行
def explore(self):
    self.logger.info(f"开始探索模式，允许其他 Agent 发现")
    self.system.add_explore_agent(self.id)

# 约 355-357 行
def stop_explore(self):
    self.logger.info(f"停止探索模式")
    self.system.stop_explore_agent(self.id)

# 约 359-367 行
def seek(self, keyword):
    self.logger.info(f"寻找关键字 '{keyword}' 的 Agent")
    agent = self.system.seek_agent(keyword)
    if agent is None:
        self.logger.error(f"未找到关键字 '{keyword}' 的 Agent")
        return
    if not (agent, keyword) in self.output_connection:
        self.output_connection.append((keyword, agent))
        self.logger.info(f"已建立输出连接到 {agent}")

# 约 369-376 行
def split(self, state, keyword):
    self.logger.info(f"执行 Agent 分裂，状态：{state}, 关键字：{keyword}")
    splited_connection = list(filter(lambda x: x[1] in keyword, self.input_connection))
    self.logger.debug(f"找到 {len(splited_connection)} 个需要分裂的连接")
    self.input_connection = list(filter(lambda x: x[1] not in keyword, self.input_connection))
    self.logger.debug(f"分裂后剩余 {len(self.input_connection)} 个输入连接")
    self.system.split_agent(state, splited_connection)
    self.logger.info("Agent 分裂操作完成")
```

**需要添加的方法**：

```python
def set_output_connection(self, id: str, keyword: str):
    """
    设置输出连接

    Args:
        id: 接收者 Agent ID
        keyword: 输出关键词
    """
    self.logger.debug(f"设置输出连接：接收者 {id}, 关键字 '{keyword}'")
    self.output_connection.append((keyword, id))
    self.logger.info(f"输出连接已添加，当前输出连接数：{len(self.output_connection)}")

def delete_output_connection_by_keyword(self, keyword: str):
    """
    根据关键字删除输出连接

    Args:
        keyword: 要删除的输出关键词
    """
    self.logger.debug(f"删除输出连接：关键字 '{keyword}'")
    deleted_connections = list(filter(lambda x: x[0] == keyword, self.output_connection))
    self.output_connection = list(filter(lambda x: x[0] != keyword, self.output_connection))
    self.logger.info(f"删除了 {len(deleted_connections)} 个输出连接")
    # 通知接收方删除对应的输入连接
    for receiver_id, _ in deleted_connections:
        receiver = self.system.get_agent(receiver_id)
        if receiver:
            receiver.delete_input_connection_by_id(self.id)

def delete_input_connection_by_id(self, sender_id: str):
    """
    根据发送者 ID 删除输入连接（用于 REJECT_OUTPUT 通知）

    Args:
        sender_id: 发送者 Agent ID
    """
    self.logger.debug(f"删除来自 {sender_id} 的输入连接")
    self.input_connection = list(filter(lambda x: x[0] != sender_id, self.input_connection))
```

#### 3. process_signal 方法（约 442-470 行）

**当前代码**：
```python
async def process_signal(self, signals):
    self.logger.info(f"处理信号：{signals}")
    try:
        signals_data = json.loads(signals)
        self.logger.debug(f"解析到 {len(signals_data)} 个信号")
        signals_data = signals_data["content"]
        for signal in signals_data:
            signal_type = signal["type"]
            self.logger.info(f"执行信号：{signal_type}")
            if signal_type == "EXPLORE":
                self.explore()
            if signal_type == "STOP_EXPLORE":
                self.stop_explore()
            if signal_type == "SEEK":
                self.seek(signal["keyword"])
            if signal_type == "REJECT_INPUT":
                if signal.get("keyword"):
                    self.delete_input_connection(signal["keyword"])
                if signal.get("id"):
                    self.logger.debug(f"通知发送者 {signal['id']} 删除输出连接")
                    self.system.get_agent(signal["id"]).delete_output_connection(self.id)
            if signal_type == "ACCEPT_INPUT":
                self.set_input_connection(signal["id"], signal["keyword"])
            if signal_type == "SPLIT":
                self.logger.info(f"执行 SPLIT 信号，状态：{signal['state']}, 关键字：{signal['keyword']}")
                self.split(signal["state"], signal["keyword"])
    except Exception as e:
        self.logger.error(f"信号处理失败：{e}")
        self.logger.exception("信号处理异常详情:")
```

**修改后代码**：
```python
async def process_signal(self, signals):
    self.logger.info(f"处理信号：{signals}")
    try:
        signals_data = json.loads(signals)
        self.logger.debug(f"解析到 {len(signals_data)} 个信号")
        signals_data = signals_data["content"]
        for signal in signals_data:
            signal_type = signal["type"]
            self.logger.info(f"执行信号：{signal_type}")
            if signal_type == "REJECT_INPUT":
                if signal.get("keyword"):
                    self.delete_input_connection(signal["keyword"])
                if signal.get("id"):
                    self.logger.debug(f"通知发送者 {signal['id']} 删除输出连接")
                    self.system.get_agent(signal["id"]).delete_output_connection(self.id)
            if signal_type == "ACCEPT_INPUT":
                self.set_input_connection(signal["id"], signal["keyword"])
            if signal_type == "SET_OUTPUT":
                self.set_output_connection(signal["id"], signal["keyword"])
            if signal_type == "REJECT_OUTPUT":
                if signal.get("keyword"):
                    self.delete_output_connection_by_keyword(signal["keyword"])
                if signal.get("id"):
                    # 通知对应 Agent 删除输入连接
                    sender = self.system.get_agent(signal["id"])
                    if sender:
                        sender.delete_input_connection_by_id(self.id)
    except Exception as e:
        self.logger.error(f"信号处理失败：{e}")
        self.logger.exception("信号处理异常详情:")
```

---

## 设计说明

### 1. SPLIT 信号移除
- 原因：使用外部初始网络代替 Agent 分裂
- 影响：系统启动时需要预先配置好完整的 Agent 网络拓扑

### 2. EXPLORE/SEEK 信号移除
- 原因：旧的发现机制被移除
- 替代：连接建立完全通过 Agent 间的直接信号（SET_OUTPUT/ACCEPT_INPUT）完成

### 3. 新增 SET_OUTPUT 信号
- 功能：Agent 主动设置输出连接
- 参数：`{"type": "SET_OUTPUT", "id": "目标 Agent ID", "keyword": "关键词"}`
- 格式：`(keyword, receiver_id)` 存储到 `output_connection` 列表

### 4. 新增 REJECT_OUTPUT 信号
- 功能：Agent 主动删除输出连接
- 参数：`{"type": "REJECT_OUTPUT", "id": "目标 Agent ID", "keyword": "关键词"}`
- 影响：同时删除本地输出连接和远程输入连接

---

## 执行步骤

1. 删除 `AgentSystem` 类的 4 个方法
2. 删除 `Agent` 类的 4 个方法
3. 添加 `Agent` 类的 3 个新方法
4. 更新 `process_signal` 方法
5. 清理导入的 `random` 模块（如果不再使用）

---

## 验证

用户表示自己会进行调试，不需要自动化测试。

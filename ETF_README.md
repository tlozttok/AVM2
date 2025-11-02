# ETF 模块集成说明

## 概述
ETF模块包含多种特殊用途的输入输出代理，已集成到主系统中。

## 已集成的代理

### 1. TimingPromptAgent (定时提示代理)
- **功能**: 根据timing.yaml配置定时发送提示
- **配置文件**: `ETF/timing.yaml`
- **配置示例**:
  ```yaml
  time: 10  # 触发时间（秒）
  prompt: "这是定时提示。当前时间: {{timestamp}}"
  ```
- **模板变量**: 支持 `{{timestamp}}` 替换为当前时间

### 2. ImageDetectionAgent (图像检测代理)
- **功能**: 自动检测input_img文件夹中的图片，使用VLM识别内容
- **输入目录**: `ETF/input_img/`
- **输出目录**: `ETF/used_img/`
- **支持格式**: jpg, jpeg, png, gif, bmp, webp
- **工作流程**:
  1. 将图片放入input_img文件夹
  2. 代理自动检测并识别
  3. 识别后图片移动到used_img文件夹
  4. 识别结果发送到主Agent

### 3. FeedbackListenerAgent (反馈监听代理)
- **功能**: 监听系统输出反馈
- **工作方式**: 内部维护消息队列
- **用途**: 让系统能够看到自己的输出作为输入

### 4. DualOutputAgent (双重输出代理)
- **功能**: 将数据发送到两个目的地
- **输出1**: 日志文件（带时间戳的用户输出）
- **输出2**: 反馈监听代理（系统自观察）
- **日志文件**: `user_output.log`

## 系统架构

```
TimingPromptAgent ──┐
                    │
ImageDetectionAgent ├──> 主Agent ──> DualOutputAgent ──> 日志文件
                    │                    │
FeedbackListenerAgent <───────────────────┘
```

## 使用方法

### 运行主系统
```bash
python main.py
```

### 运行测试
```bash
python test_etf_integration.py
```

### 配置定时提示
编辑 `ETF/timing.yaml` 文件：
```yaml
time: 30  # 每30秒触发一次
prompt: "系统提醒：请检查当前状态"
```

### 使用图像识别
1. 将图片文件放入 `ETF/input_img/` 文件夹
2. 系统会自动检测并识别图片内容
3. 处理后的图片会移动到 `ETF/used_img/` 文件夹

### 查看输出
- **用户输出**: 查看 `user_output.log` 文件
- **系统日志**: 查看控制台输出和日志文件

## 代理连接关系

- **输入代理** → **主Agent**:
  - TimingPromptAgent → 主Agent (关键字: "timing_prompt")
  - ImageDetectionAgent → 主Agent (关键字: "image_detection")  
  - FeedbackListenerAgent → 主Agent (关键字: "system_feedback")

- **主Agent** → **输出代理**:
  - 主Agent → DualOutputAgent (关键字: "user_output")

## 注意事项

1. **环境变量**: 确保设置了正确的OpenAI API密钥和基础URL
2. **图片格式**: 只支持常见的图片格式
3. **定时配置**: timing.yaml文件会被定期重新加载
4. **反馈循环**: 系统输出会反馈回系统，形成自观察循环

## 扩展建议

- 可以添加更多InputAgent来处理其他类型的外部输入
- 可以扩展DualOutputAgent以支持更多输出目的地
- 可以配置不同的VLM提示词来优化图像识别效果
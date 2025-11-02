"""
ETF模块的输入输出代理
包含各种特殊用途的InputAgent和OutputAgent实现
"""

import yaml
import time
import os
import asyncio
import base64
import shutil
from pathlib import Path
from typing import List, Optional
from driver.driver import InputAgent, OutputAgent
from openai import AsyncOpenAI


class TimingPromptAgent(InputAgent):
    """
    定时提示代理
    读取timing.yaml配置，定时发送提示内容
    """
    
    def __init__(self, config_file="timing.yaml"):
        super().__init__()
        self.config_file = config_file
        self.timer = 0.0
        self.last_check_time = time.time()
        self.config_update_interval = 5.0  # 每5秒检查一次配置更新
        self.last_config_check = time.time()
        
        # 加载初始配置
        self._load_configuration()
        
        self.logger.info(f"定时提示代理已初始化，配置文件: {self.config_file}")
    
    def _load_configuration(self):
        """从YAML文件加载配置"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), self.config_file)
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.trigger_time = float(config.get('time', 60))
            self.prompt_content = config.get('prompt', "")
            
            self.logger.info(f"配置已加载: 触发时间={self.trigger_time}秒, 提示长度={len(self.prompt_content)}字符")
            
        except Exception as e:
            self.logger.error(f"从{self.config_file}加载配置失败: {e}")
            # 如果配置加载失败，设置默认值
            self.trigger_time = 60.0
            self.prompt_content = ""
    
    def seek_signal(self, message: str):
        """根据消息决定是否进行seek"""
        # 定时提示代理不需要基于消息进行seek
        pass
        
    def has_data_to_send(self) -> bool:
        """检查计时器是否超过触发时间"""
        current_time = time.time()
        elapsed = current_time - self.last_check_time
        self.timer += elapsed
        self.last_check_time = current_time
        
        # 检查是否需要更新配置
        if current_time - self.last_config_check >= self.config_update_interval:
            self._load_configuration()
            self.last_config_check = current_time
        
        should_send = self.timer >= self.trigger_time
        if should_send:
            self.logger.debug(f"计时器达到{self.timer:.2f}秒 (触发: {self.trigger_time}秒)，准备发送提示")
        
        return should_send
        
    def collect_data(self) -> str:
        """返回提示内容并重置计时器"""
        self.logger.info(f"在{self.timer:.2f}秒后发送提示")
        
        # 处理模板变量
        data = self.prompt_content
        if "{{timestamp}}" in data:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            data = data.replace("{{timestamp}}", timestamp)
        
        # 重置计时器
        self.timer = 0.0
        self.last_check_time = time.time()
        
        self.logger.debug(f"计时器已重置，已发送{len(data)}字符的提示")
        return data
        
    def get_check_interval(self) -> float:
        """获取运行循环的检查间隔"""
        return 0.1  # 每100毫秒检查一次


class UserInputAgent(InputAgent):
    """
    用户输入代理
    从控制台读取用户输入并发送给其他Agent
    """
    
    def __init__(self, check_interval: float = 0.1):
        super().__init__()
        self.check_interval = check_interval
        self.input_buffer = []  # 存储用户输入
        self._input_available = asyncio.Event()  # 输入可用事件
        
        self.logger.info(f"用户输入代理已初始化，检查间隔: {check_interval}秒")
    
    def seek_signal(self, message: str):
        """根据消息决定是否进行seek"""
        # 用户输入代理不需要基于消息进行seek
        pass
        
    def has_data_to_send(self) -> bool:
        """检查是否有用户输入需要发送"""
        has_data = len(self.input_buffer) > 0
        if has_data:
            self.logger.debug(f"输入缓冲区中有{len(self.input_buffer)}条消息")
        return has_data
        
    def collect_data(self) -> str:
        """收集并返回用户输入数据"""
        if not self.input_buffer:
            self.logger.debug("输入缓冲区为空")
            return ""
        
        # 获取所有输入并清空缓冲区
        inputs = self.input_buffer.copy()
        self.input_buffer.clear()
        
        combined_input = "\n".join(inputs)
        self.logger.info(f"已收集{len(inputs)}条用户输入，总长度: {len(combined_input)}字符")
        return combined_input
        
    def get_check_interval(self) -> float:
        """获取运行循环的检查间隔"""
        return self.check_interval
    
    async def _run_loop(self):
        """重写运行循环以支持异步输入读取"""
        self.logger.debug("用户输入代理运行循环开始")
        loop_count = 0
        
        # 启动异步输入读取任务
        input_task = asyncio.create_task(self._read_input_async())
        
        while self._running:
            loop_count += 1
            try:
                # 检查是否有数据需要发送
                if self.should_send_data():
                    self.logger.debug(f"第 {loop_count} 次循环: 有数据需要发送")
                    await self.send_collected_data()
                
                # 等待一段时间再检查
                await asyncio.sleep(self.check_interval)
                
            except asyncio.CancelledError:
                self.logger.debug("用户输入代理运行循环被取消")
                break
            except Exception as e:
                self.logger.error(f"用户输入代理运行循环异常: {e}")
                self.logger.exception("运行循环异常详情:")
                await asyncio.sleep(1)  # 异常后等待1秒再继续
        
        # 取消输入读取任务
        input_task.cancel()
        try:
            await input_task
        except asyncio.CancelledError:
            pass
            
        self.logger.info(f"用户输入代理运行循环结束，共执行 {loop_count} 次循环")
    
    async def _read_input_async(self):
        """异步读取用户输入"""
        self.logger.debug("开始异步读取用户输入")
        
        while self._running:
            try:
                # 使用asyncio创建异步输入读取
                loop = asyncio.get_event_loop()
                user_input = await loop.run_in_executor(None, input, "用户输入: ")
                
                if user_input.strip():  # 忽略空输入
                    self.input_buffer.append(user_input.strip())
                    self.logger.debug(f"已接收用户输入: {user_input.strip()}")
                    
            except asyncio.CancelledError:
                self.logger.debug("用户输入读取任务被取消")
                break
            except EOFError:
                self.logger.info("检测到输入结束(EOF)，停止读取")
                break
            except Exception as e:
                self.logger.error(f"读取用户输入异常: {e}")
                await asyncio.sleep(0.1)  # 异常后短暂等待
    
    def add_input(self, input_text: str):
        """手动添加输入（用于测试或其他来源）"""
        if input_text.strip():
            self.input_buffer.append(input_text.strip())
            self.logger.debug(f"手动添加输入: {input_text.strip()}")
    
    def clear_buffer(self):
        """清空输入缓冲区"""
        count = len(self.input_buffer)
        self.input_buffer.clear()
        self.logger.info(f"已清空输入缓冲区，清除了{count}条消息")


class FeedbackListenerAgent(InputAgent):
    """
    反馈监听代理
    内部维护消息队列，允许OutputAgent直接向其发送消息
    """
    
    def __init__(self, check_interval: float = 1.0):
        super().__init__()
        self.check_interval = check_interval
        self.message_queue = []  # 内部消息队列
        
        self.logger.info("反馈监听代理已初始化")
    
    def seek_signal(self, message: str):
        """根据消息决定是否进行seek"""
        # 反馈监听代理不需要基于消息进行seek
        pass
        
    def has_data_to_send(self) -> bool:
        """检查内部队列中是否有消息"""
        has_data = len(self.message_queue) > 0
        if has_data:
            self.logger.debug(f"内部队列中有{len(self.message_queue)}条消息")
        return has_data
        
    def collect_data(self) -> str:
        """收集内部队列中的所有消息"""
        if not self.message_queue:
            self.logger.debug("内部队列为空")
            return ""
        
        # 获取所有消息并清空队列
        messages = self.message_queue.copy()
        self.message_queue.clear()
        
        combined_messages = "\n".join(messages)
        self.logger.info(f"已收集{len(messages)}条反馈消息，总长度: {len(combined_messages)}")
        return combined_messages
        
    def get_check_interval(self) -> float:
        """获取运行循环的检查间隔"""
        return self.check_interval
    
    def receive_feedback(self, message: str):
        """接收来自OutputAgent的反馈消息"""
        self.message_queue.append(message)
        self.logger.debug(f"已接收反馈消息，队列大小: {len(self.message_queue)}")


class DualOutputAgent(OutputAgent):
    """
    双重输出代理
    将数据发送到两个目的地:
    1. 日志文件（用户输出）
    2. 反馈监听代理（系统自观察）
    """
    
    def __init__(self, 
                 log_file: str = "user_output.log",
                 feedback_listener: Optional[FeedbackListenerAgent] = None):
        super().__init__()
        
        self.log_file = Path(log_file)
        self.feedback_listener = feedback_listener
        
        # 确保日志文件目录存在
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.logger.info(f"双重输出代理已初始化: 日志文件={self.log_file}")
        if feedback_listener:
            self.logger.info(f"已绑定反馈监听代理: {feedback_listener.id}")
    
    def explore(self, message: str):
        """根据消息决定是否探索"""
        # 双重输出代理不需要基于消息进行探索
        pass
    
    async def execute_data(self, data: str):
        """处理数据并发送到两个目的地"""
        self.logger.info(f"正在处理双重输出数据，长度: {len(data)}字符")
        
        # 发送到日志文件
        await self._write_to_log(data)
        
        # 发送到反馈监听代理
        self._send_to_feedback_listener(data)
        
        self.logger.info("双重输出完成")
    
    async def _write_to_log(self, data: str):
        """将数据写入日志文件（带时间戳）"""
        try:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            log_entry = f"[{timestamp}] {data}\n"
            
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(log_entry)
            
            self.logger.debug(f"数据已写入日志文件: {self.log_file}")
            
        except Exception as e:
            self.logger.error(f"写入日志文件{self.log_file}失败: {e}")
    
    def _send_to_feedback_listener(self, data: str):
        """将数据发送到反馈监听代理"""
        if not self.feedback_listener:
            self.logger.warning("未绑定反馈监听代理，跳过反馈发送")
            return
        
        try:
            self.feedback_listener.receive_feedback(data)
            self.logger.debug(f"数据已发送到反馈监听代理 {self.feedback_listener.id}")
        except Exception as e:
            self.logger.error(f"发送数据到反馈监听代理失败: {e}")
    
    def set_log_file(self, log_file: str):
        """设置或更新日志文件路径"""
        self.log_file = Path(log_file)
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"日志文件已设置为: {self.log_file}")
    
    def set_feedback_listener(self, feedback_listener: FeedbackListenerAgent):
        """设置或更新反馈监听代理"""
        self.feedback_listener = feedback_listener
        self.logger.info(f"反馈监听代理已设置为: {feedback_listener.id}")
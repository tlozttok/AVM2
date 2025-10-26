#!/usr/bin/env python3
"""
游戏环境模块
包含dfrotz交互式小说游戏的管理类
"""

import asyncio
import subprocess
import os
import sys
from typing import Optional, List, Tuple
import uuid
from driver.driver import InputAgent, OutputAgent
from utils.logger import Loggable


class DfrotzManager(Loggable):
    """
    dfrotz游戏管理器
    负责启动、维护和与dfrotz交互式小说游戏进程通信
    """
    
    def __init__(self, game_file: str, dfrotz_path: str = "dfrotz"):
        super().__init__()
        
        self.game_file = game_file
        self.dfrotz_path = dfrotz_path
        self.process: Optional[subprocess.Popen] = None
        self._running = False
        self._output_queue = asyncio.Queue()
        self._input_queue = asyncio.Queue()
        self._reader_task: Optional[asyncio.Task] = None
        self._writer_task: Optional[asyncio.Task] = None
        
        # 验证游戏文件存在
        if not os.path.exists(game_file):
            error_msg = f"游戏文件不存在: {game_file}"
            self.logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        self.logger.info(f"DfrotzManager初始化完成，游戏文件: {game_file}, dfrotz路径: {dfrotz_path}")
    
    async def start(self):
        """启动dfrotz进程和通信任务"""
        if self._running:
            self.logger.warning("dfrotz进程已在运行中")
            return
        
        try:
            self.logger.info("正在启动dfrotz进程...")
            
            # 启动dfrotz进程
            self.process = subprocess.Popen(
                [self.dfrotz_path, self.game_file],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            self._running = True
            
            # 启动读取和写入任务
            self._reader_task = asyncio.create_task(self._read_output())
            self._writer_task = asyncio.create_task(self._write_input())
            
            self.logger.info(f"dfrotz进程已启动，PID: {self.process.pid}")
            
        except Exception as e:
            error_msg = f"启动dfrotz进程失败: {e}"
            self.logger.error(error_msg)
            await self.stop()
            raise
    
    async def stop(self):
        """停止dfrotz进程和通信任务"""
        self.logger.info("正在停止dfrotz进程...")
        self._running = False
        
        # 取消任务
        if self._reader_task:
            self._reader_task.cancel()
            self.logger.debug("输出读取任务已取消")
        if self._writer_task:
            self._writer_task.cancel()
            self.logger.debug("输入写入任务已取消")
        
        # 终止进程
        if self.process:
            try:
                self.logger.debug("正在终止dfrotz进程...")
                self.process.terminate()
                await asyncio.sleep(1)
                if self.process.poll() is None:
                    self.logger.debug("进程仍在运行，强制终止...")
                    self.process.kill()
                self.logger.info("dfrotz进程已成功终止")
            except Exception as e:
                error_msg = f"终止dfrotz进程时出错: {e}"
                self.logger.error(error_msg)
            finally:
                self.process = None
        
        self.logger.info("dfrotz进程已完全停止")
    
    async def _read_output(self):
        """异步读取dfrotz进程的输出 - 贪婪读取，自动处理分页"""
        self.logger.debug("开始异步读取dfrotz输出")
        line_count = 0
        
        while self._running and self.process and self.process.stdout:
            try:
                # 贪婪读取：一次性读取所有可用的输出
                available_output = []
                has_more = False
                
                while True:
                    try:
                        line = await asyncio.wait_for(asyncio.get_event_loop().run_in_executor(
                        None, self.process.stdout.readline
                        ),0.5)
                    except TimeoutError as e:
                        line=None
                    if line:
                        line_count += 1
                        line_stripped = line.strip()
                        
                        # 检查是否包含各种分页提示
                        more_patterns = ["***MORE***", "[MORE]", "(MORE)", "--more--", "-- More --"]
                        found_more = False
                        
                        for pattern in more_patterns:
                            if pattern in line_stripped:
                                self.logger.info(f"检测到分页提示 '{pattern}'，自动输入回车键")
                                has_more = True
                                found_more = True
                                # 不将MORE提示加入输出
                                break
                        
                        if not found_more:
                            available_output.append(line_stripped)
                            self.logger.debug(f"读取到dfrotz输出 #{line_count}: {line_stripped}")
                    else:
                        # 没有更多可读数据，跳出循环
                        break
                
                # 如果有读取到输出，一次性放入队列
                if available_output:
                    await self._output_queue.put('\n'.join(available_output))
                    self.logger.info(f"贪婪读取完成，共读取 {len(available_output)} 行输出")
                
                # 如果检测到分页提示，自动发送回车键
                if has_more:
                    await self._input_queue.put("")
                    self.logger.info("已自动发送回车键获取下一页")
                    # 短暂等待，让dfrotz处理分页
                    await asyncio.sleep(0.1)
                
                # 进程可能已结束
                if self.process.poll() is not None:
                    self.logger.warning("dfrotz进程已结束，停止读取输出")
                    break
                    
                # 短暂等待，避免过度占用CPU
                await asyncio.sleep(0.01)
                    
            except Exception as e:
                error_msg = f"读取dfrotz输出时出错: {e}"
                self.logger.error(error_msg)
                break
        
        self.logger.info(f"dfrotz输出读取任务结束，共读取 {line_count} 行输出")
    
    async def _write_input(self):
        """异步向dfrotz进程写入输入"""
        self.logger.debug("开始异步写入dfrotz输入")
        command_count = 0
        
        while self._running and self.process and self.process.stdin:
            try:
                text_input = await self._input_queue.get()
                if text_input:
                    command_count += 1
                    await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self.process.stdin.write(text_input + '\n') and self.process.stdin.flush()
                    )
                    self.logger.info(f"已写入dfrotz输入 #{command_count}: {text_input}")
            except Exception as e:
                error_msg = f"向dfrotz写入输入时出错: {e}"
                self.logger.error(error_msg)
                break
        
        self.logger.info(f"dfrotz输入写入任务结束，共写入 {command_count} 条输入")
    
    async def send_text(self, text: str):
        """向dfrotz发送文本输入"""
        if not self._running:
            error_msg = "dfrotz进程未运行，无法发送文本"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        await self._input_queue.put(text)
        self.logger.info(f"已发送文本到dfrotz: '{text}'")
    
    async def get_output(self) -> str:
        """获取dfrotz的输出 - 贪婪获取，尽可能多获取"""
        if not self._running:
            error_msg = "dfrotz进程未运行，无法获取输出"
            self.logger.error(error_msg)
            raise RuntimeError(error_msg)
        
        output_chunks = []
        chunk_count = 0
        
        # 贪婪获取：一次性获取队列中所有可用的输出块
        while not self._output_queue.empty():
            try:
                chunk = self._output_queue.get_nowait()
                output_chunks.append(chunk)
                chunk_count += 1
            except asyncio.QueueEmpty:
                break
        
        # 将所有输出块合并为一个完整的输出
        output_text = '\n'.join(output_chunks)
        if output_text:
            self.logger.debug(f"贪婪获取完成，共获取 {chunk_count} 个输出块，总长度: {len(output_text)} 字符")
        
        return output_text
    
    def is_running(self) -> bool:
        """检查dfrotz进程是否在运行"""
        running = self._running and self.process and self.process.poll() is None
        if not running:
            self.logger.debug("dfrotz进程不在运行状态")
        return running
    
    async def restart(self):
        """重启dfrotz进程"""
        self.logger.info("正在重启dfrotz进程...")
        await self.stop()
        await asyncio.sleep(1)
        await self.start()
        self.logger.info("dfrotz进程重启完成")


class DfrotzOutputAgent(OutputAgent):
    """
    dfrotz输出代理
    负责接收系统消息并发送给dfrotz作为输入
    """
    
    def __init__(self, game_file: str, dfrotz_path: str = "dfrotz"):
        super().__init__()
        
        # 创建dfrotz管理器
        self.dfrotz_manager = DfrotzManager(game_file, dfrotz_path)
        self._text_queue = asyncio.Queue()
        self._dfrotz_started = False
        
        self.logger.info(f"DfrotzOutputAgent实例已创建，游戏文件: {game_file}")
    
    def explore(self, message: str):
        """根据message决定是否探索 - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    async def execute_data(self, data: str):
        """执行数据 - 将接收到的数据发送给dfrotz"""
        self.logger.info(f"执行数据: '{data}'")
        
        if self._dfrotz_started:
            try:
                await self.dfrotz_manager.send_text(data)
                self.logger.info(f"已发送文本到dfrotz: '{data}'")
            except Exception as e:
                self.logger.error(f"发送dfrotz文本失败: {e}")
        else:
            self.logger.warning("dfrotz进程未启动，无法发送文本")
        
    async def start(self):
        """启动dfrotz进程"""
        self.logger.info("启动DfrotzOutputAgent")
        
        # 启动dfrotz进程
        try:
            await self.dfrotz_manager.start()
            self._dfrotz_started = True
            self.logger.info("dfrotz进程已启动")
        except Exception as e:
            self.logger.error(f"启动dfrotz进程失败: {e}")
            raise
        
    async def stop(self):
        """停止dfrotz进程"""
        self.logger.info("停止DfrotzOutputAgent")
        
        # 停止dfrotz进程
        if self._dfrotz_started:
            await self.dfrotz_manager.stop()
            self._dfrotz_started = False
            self.logger.info("dfrotz进程已停止")


class DfrotzInputAgent(InputAgent):
    """
    dfrotz输入代理
    负责从dfrotz读取输出并发送给系统
    """
    
    def __init__(self, dfrotz_manager: DfrotzManager):
        super().__init__()
        self.dfrotz_manager = dfrotz_manager
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        self.logger.info("DfrotzInputAgent实例已创建")
    
    def seek_signal(self, message: str):
        """根据message决定是否进行seek - 由 LLM Agent 主动建立连接，这里无需实现"""
        pass
        
    def has_data_to_send(self) -> bool:
        """检查是否有dfrotz输出需要发送"""
        # 这里需要检查dfrotz是否有新输出
        # 由于dfrotz输出是异步的，我们依赖监控循环来处理
        return False
        
    def collect_data(self) -> str:
        """收集数据 - 对于dfrotz输入代理，不需要收集数据"""
        # dfrotz输入代理通过监控循环发送数据，不需要收集数据
        return ""
        
    async def start(self):
        """启动输出监控循环"""
        self.logger.info("启动DfrotzInputAgent")
        
        self._running = True
        self._task = asyncio.create_task(self._monitor_output())
        
        # 启动父类的运行循环
        await super().start()
        self.logger.info("DfrotzInputAgent已完全启动")
        
    async def stop(self):
        """停止输出监控循环"""
        self.logger.info("停止DfrotzInputAgent")
        
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        await super().stop()
        self.logger.info("DfrotzInputAgent已完全停止")
        
    async def _monitor_output(self):
        """监控dfrotz输出并发送给连接的Agent - 贪婪监控"""
        self.logger.debug("开始监控dfrotz输出")
        output_count = 0
        
        while self._running:
            try:
                # 贪婪获取dfrotz输出
                output = await self.dfrotz_manager.get_output()
                
                if output and self.output_connections:
                    output_count += 1
                    # 发送给所有连接的输出Agent
                    for connection_id in self.output_connections:
                        if self.message_bus:
                            await self.message_bus.send_message(output, connection_id, self.id)
                    
                    self.logger.info(f"DfrotzInputAgent贪婪发送输出 #{output_count} 到 {len(self.output_connections)} 个连接，长度: {len(output)} 字符")
                
                # 短暂等待，避免过度占用CPU
                await asyncio.sleep(0.05)
                
            except Exception as e:
                self.logger.error(f"DfrotzInputAgent监控循环出错: {e}")
                await asyncio.sleep(1)
        
        self.logger.info(f"dfrotz输出监控结束，共发送 {output_count} 次输出")


# 使用示例
async def example_usage():
    """使用示例"""
    # 创建dfrotz管理器（需要指定实际的游戏文件路径）
    game_file = "game_env/dfrotz/905.z5"  # 使用项目中的游戏文件
    dfrotz_path = "game_env/dfrotz/dfrotz.exe"
    
    manager = DfrotzManager(game_file, dfrotz_path)
    
    # 创建输入输出代理
    output_agent = DfrotzOutputAgent(game_file, dfrotz_path)  # 发送给dfrotz
    input_agent = DfrotzInputAgent(manager)  # 从dfrotz读取
    
    # 启动dfrotz和代理
    await output_agent.start()
    await input_agent.start()
    
    # 示例：通过输出代理发送文本
    await output_agent.execute_data("look")
    
    # 等待一段时间查看输出
    await asyncio.sleep(2)
    
    # 停止
    await input_agent.stop()
    await output_agent.stop()


if __name__ == "__main__":
    # 运行示例
    asyncio.run(example_usage())
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


class DfrotzManager:
    """
    dfrotz游戏管理器
    负责启动、维护和与dfrotz交互式小说游戏进程通信
    """
    
    def __init__(self, game_file: str, dfrotz_path: str = "dfrotz"):
        """
        初始化dfrotz管理器
        
        Args:
            game_file: 游戏文件路径 (.z5, .z8等格式)
            dfrotz_path: dfrotz可执行文件路径，默认为系统PATH中的dfrotz
        """
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
            raise FileNotFoundError(f"游戏文件不存在: {game_file}")
        
        print(f"DfrotzManager初始化完成，游戏文件: {game_file}")
    
    async def start(self):
        """启动dfrotz进程和通信任务"""
        if self._running:
            print("dfrotz进程已在运行中")
            return
        
        try:
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
            
            print(f"dfrotz进程已启动，PID: {self.process.pid}")
            
        except Exception as e:
            print(f"启动dfrotz进程失败: {e}")
            await self.stop()
            raise
    
    async def stop(self):
        """停止dfrotz进程和通信任务"""
        self._running = False
        
        # 取消任务
        if self._reader_task:
            self._reader_task.cancel()
        if self._writer_task:
            self._writer_task.cancel()
        
        # 终止进程
        if self.process:
            try:
                self.process.terminate()
                await asyncio.sleep(1)
                if self.process.poll() is None:
                    self.process.kill()
            except Exception as e:
                print(f"终止dfrotz进程时出错: {e}")
            finally:
                self.process = None
        
        print("dfrotz进程已停止")
    
    async def _read_output(self):
        """异步读取dfrotz进程的输出"""
        while self._running and self.process and self.process.stdout:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, self.process.stdout.readline
                )
                if line:
                    await self._output_queue.put(line.strip())
                else:
                    # 进程可能已结束
                    if self.process.poll() is not None:
                        break
            except Exception as e:
                print(f"读取dfrotz输出时出错: {e}")
                break
    
    async def _write_input(self):
        """异步向dfrotz进程写入输入"""
        while self._running and self.process and self.process.stdin:
            try:
                text_input = await self._input_queue.get()
                if text_input:
                    await asyncio.get_event_loop().run_in_executor(
                        None, 
                        lambda: self.process.stdin.write(text_input + '\n') and self.process.stdin.flush()
                    )
            except Exception as e:
                print(f"向dfrotz写入输入时出错: {e}")
                break
    
    async def send_text(self, text: str):
        """向dfrotz发送文本输入"""
        if not self._running:
            raise RuntimeError("dfrotz进程未运行")
        
        await self._input_queue.put(text)
        print(f"已发送文本到dfrotz: {text}")
    
    async def get_output(self) -> str:
        """获取dfrotz的输出"""
        if not self._running:
            raise RuntimeError("dfrotz进程未运行")
        
        output_lines = []
        while not self._output_queue.empty():
            try:
                line = self._output_queue.get_nowait()
                output_lines.append(line)
            except asyncio.QueueEmpty:
                break
            
        
        return '\n'.join(output_lines)
    
    def is_running(self) -> bool:
        """检查dfrotz进程是否在运行"""
        return self._running and self.process and self.process.poll() is None
    
    async def restart(self):
        """重启dfrotz进程"""
        await self.stop()
        await asyncio.sleep(1)
        await self.start()


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
        self.logger.info(f"执行数据: {data}")
        
        if self._dfrotz_started:
            try:
                await self.dfrotz_manager.send_text(data)
                self.logger.info(f"已发送文本到dfrotz: {data}")
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
        """监控dfrotz输出并发送给连接的Agent"""
        while self._running:
            try:
                # 获取dfrotz输出
                output = await self.dfrotz_manager.get_output()
                
                if output and self.output_connections:
                    # 发送给所有连接的输出Agent
                    for connection_id in self.output_connections:
                        if self.message_bus:
                            await self.message_bus.send_message(output, connection_id, self.id)
                    
                    self.logger.info(f"DfrotzInputAgent发送输出到 {len(self.output_connections)} 个连接")
                
                # 等待一段时间再检查
                await asyncio.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"DfrotzInputAgent监控循环出错: {e}")
                await asyncio.sleep(1)


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
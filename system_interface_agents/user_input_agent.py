import asyncio
import time
import threading
import queue
from typing import Optional, Dict, Any
from driver.system_agents import InputAgent
from driver.driver import Agent, AgentMessage

# GUI imports
import tkinter as tk
from tkinter import simpledialog, messagebox

class UserInputAgent(InputAgent):
    """
    用户输入Agent
    通过GUI窗口收集用户输入
    用户每发送一次输入，Agent就完成其collect_input函数
    只要有用户输入，就激活
    """

    def __init__(self, id: str, message_bus = None):
        super().__init__(id, message_bus)
        self.input_queue = queue.Queue()
        self.window_thread = None
        self.window = None
        self.input_received = False
        self.current_input = None
        
        # 启动GUI线程
        self._start_gui_thread()
    
    def _start_gui_thread(self):
        """启动GUI线程"""
        self.window_thread = threading.Thread(target=self._create_window, daemon=True)
        self.window_thread.start()
    
    def _create_window(self):
        """创建GUI窗口"""
        self.window = tk.Tk()
        self.window.title("AVM2 用户输入")
        self.window.geometry("400x200")
        self.window.resizable(True, True)
        
        # 创建输入框架
        frame = tk.Frame(self.window, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题标签
        title_label = tk.Label(frame, text="请输入您的消息:", font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 输入文本框
        self.input_text = tk.Text(frame, height=6, width=40, font=("Arial", 10))
        self.input_text.pack(pady=(0, 10), fill=tk.BOTH, expand=True)
        
        # 按钮框架
        button_frame = tk.Frame(frame)
        button_frame.pack(fill=tk.X)
        
        # 发送按钮
        send_button = tk.Button(
            button_frame, 
            text="发送", 
            command=self._on_send_clicked,
            bg="#4CAF50",
            fg="white",
            font=("Arial", 10, "bold"),
            width=10
        )
        send_button.pack(side=tk.RIGHT, padx=(10, 0))
        
        # 清空按钮
        clear_button = tk.Button(
            button_frame,
            text="清空",
            command=self._on_clear_clicked,
            bg="#f44336",
            fg="white",
            font=("Arial", 10),
            width=10
        )
        clear_button.pack(side=tk.RIGHT)
        
        # 绑定回车键
        self.window.bind('<Return>', lambda event: self._on_send_clicked())
        
        # 设置焦点到输入框
        self.input_text.focus_set()
        
        # 启动GUI主循环
        self.window.mainloop()
    
    def _on_send_clicked(self):
        """发送按钮点击事件"""
        input_text = self.input_text.get("1.0", tk.END).strip()
        if input_text:
            # 将输入放入队列
            self.input_queue.put(input_text)
            # 清空输入框
            self.input_text.delete("1.0", tk.END)
            # 显示发送成功消息
            self._show_success_message()
    
    def _on_clear_clicked(self):
        """清空按钮点击事件"""
        self.input_text.delete("1.0", tk.END)
    
    def _show_success_message(self):
        """显示发送成功消息"""
        # 在窗口底部显示临时消息
        if hasattr(self, 'status_label'):
            self.status_label.destroy()
        
        self.status_label = tk.Label(
            self.window, 
            text="✓ 消息已发送", 
            fg="green",
            font=("Arial", 9)
        )
        self.status_label.pack(side=tk.BOTTOM, pady=5)
        
        # 2秒后自动消失
        self.window.after(2000, lambda: self.status_label.destroy() if hasattr(self, 'status_label') else None)
    
    async def collect_input(self) -> Optional[str]:
        """
        收集用户输入
        从GUI队列中获取用户输入
        返回: 用户输入的字符串，如果没有新输入则返回None
        """
        try:
            # 非阻塞地从队列中获取输入
            if not self.input_queue.empty():
                user_input = self.input_queue.get_nowait()
                self.logger.info(f"UserInputAgent: 收到用户输入: {user_input}")
                return user_input
        except queue.Empty:
            pass
        
        # 短暂休眠避免过度占用CPU
        await asyncio.sleep(0.1)
        return None
    
    def should_activate(self, input_data: str) -> bool:
        """
        判断是否应该激活
        只要有用户输入就激活
        """
        return bool(input_data and input_data.strip())
    
    def format_message(self, input_data: str) -> str:
        """
        格式化消息
        将用户输入格式化为标准消息格式
        """
        return f"<user_input>{input_data}</user_input>"
    
    async def stop_input(self):
        """停止输入收集并关闭窗口"""
        await super().stop_input()
        if self.window:
            # 在GUI线程中关闭窗口
            self.window.after(0, self.window.destroy)


# 测试代码
if __name__ == "__main__":
    """
    独立测试UserInputAgent的GUI功能
    不创建Agent系统，只测试窗口和输入收集
    """
    import sys
    import time
    
    print("🧪 开始测试UserInputAgent GUI...")
    print("=" * 50)
    
    # 创建测试用的消息总线（简化版）
    class TestMessageBus:
        def __init__(self):
            self.messages = []
        
        async def send_message_async(self, message):
            self.messages.append(message)
            print(f"📨 消息总线收到消息: {message}")
    
    # 创建UserInputAgent实例
    print("1. 创建UserInputAgent实例...")
    message_bus = TestMessageBus()
    agent = UserInputAgent("test_user_input", message_bus)
    print("✅ UserInputAgent实例创建成功")
    
    print("\n2. 等待GUI窗口启动...")
    time.sleep(2)  # 给GUI线程一些时间启动
    
    print("\n3. 测试输入收集循环...")
    print("   请打开GUI窗口，输入一些文本并点击'发送'按钮")
    print("   或者按回车键发送")
    print("   输入完成后，在此控制台按 Ctrl+C 停止测试")
    print("=" * 50)
    
    async def test_input_loop():
        """测试输入循环"""
        try:
            while True:
                # 收集输入
                user_input = await agent.collect_input()
                
                if user_input:
                    print(f"🎯 收到用户输入: '{user_input}'")
                    
                    # 测试激活判断
                    should_activate = agent.should_activate(user_input)
                    print(f"   🔍 是否激活: {should_activate}")
                    
                    # 测试消息格式化
                    formatted_message = agent.format_message(user_input)
                    print(f"   📝 格式化消息: '{formatted_message}'")
                    
                    # 模拟发送消息
                    if should_activate:
                        await message_bus.send_message_async(formatted_message)
                        print("   ✅ 消息已发送到总线")
                    
                    print("-" * 30)
                
                # 短暂休眠
                await asyncio.sleep(0.1)
                
        except KeyboardInterrupt:
            print("\n🛑 测试被用户中断")
        except Exception as e:
            print(f"\n❌ 测试出错: {e}")
        finally:
            # 停止Agent
            await agent.stop_input()
            print("✅ UserInputAgent已停止")
    
    # 运行测试
    try:
        asyncio.run(test_input_loop())
    except KeyboardInterrupt:
        print("\n🛑 测试结束")
    
    print("\n📊 测试总结:")
    print(f"   总共收到 {len(message_bus.messages)} 条消息")
    for i, msg in enumerate(message_bus.messages, 1):
        print(f"   {i}. {msg}")
    
    print("\n✅ GUI测试完成！")
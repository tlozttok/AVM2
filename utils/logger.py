"""
AVM2 系统日志模块
与程序核心代码清楚分离的日志记录系统
"""

import os
import time
import datetime
import threading
import inspect
from typing import Dict, List, Any, Optional
from enum import Enum


class LogLevel(Enum):
    """日志级别"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Logger:
    """
    系统日志记录器
    负责记录：
    1. 定时记录系统的宏观信息
    2. DEBUG模式下，记录激活内容和消息发送去向的详细信息
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self._initialized = True
        self.log_level = LogLevel.INFO
        self.debug_mode = False
        self.macro_log_interval = 60  # 宏观信息记录间隔（秒）
        self.last_macro_log_time = 0
        self.log_dir = "logs"
        
        # 日志文件路径
        self.core_macro_file = None
        self.core_details_file = None
        self.agent_log_files = {}  # {agent_class_name: file_path}
        
        # 创建日志目录结构
        self._init_log_directories()
        
        # 初始化日志文件
        self._init_log_files()
        
        print(f"✅ 日志系统初始化完成 - 级别: {self.log_level.value}, DEBUG模式: {self.debug_mode}")
    
    def _init_log_directories(self):
        """初始化日志目录结构"""
        # 核心日志目录
        core_dir = os.path.join(self.log_dir, "core")
        os.makedirs(core_dir, exist_ok=True)
        
        # Agent日志目录
        agents_dir = os.path.join(self.log_dir, "agents")
        os.makedirs(agents_dir, exist_ok=True)
    
    def _init_log_files(self):
        """初始化日志文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 核心日志文件
        core_dir = os.path.join(self.log_dir, "core")
        self.core_macro_file = os.path.join(core_dir, f"macro_{timestamp}.log")
        self.core_details_file = os.path.join(core_dir, f"details_{timestamp}.log")
        
        # 写入核心日志文件头
        with open(self.core_macro_file, 'w', encoding='utf-8') as f:
            f.write(f"# AVM2 核心程序宏观信息日志 - 启动时间: {datetime.datetime.now()}\n")
            f.write(f"# 日志级别: {self.log_level.value}\n")
            f.write(f"# DEBUG模式: {self.debug_mode}\n")
            f.write("=" * 80 + "\n\n")
        
        with open(self.core_details_file, 'w', encoding='utf-8') as f:
            f.write(f"# AVM2 核心程序细节日志 - 启动时间: {datetime.datetime.now()}\n")
            f.write(f"# 日志级别: {self.log_level.value}\n")
            f.write(f"# DEBUG模式: {self.debug_mode}\n")
            f.write("=" * 80 + "\n\n")
    
    def _get_agent_log_file(self, agent_class_name: str) -> str:
        """获取或创建Agent日志文件"""
        if agent_class_name in self.agent_log_files:
            return self.agent_log_files[agent_class_name]
        
        # 创建新的Agent日志文件
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        agents_dir = os.path.join(self.log_dir, "agents")
        agent_log_file = os.path.join(agents_dir, f"{agent_class_name}_{timestamp}.log")
        
        # 写入Agent日志文件头
        with open(agent_log_file, 'w', encoding='utf-8') as f:
            f.write(f"# AVM2 {agent_class_name} 日志 - 启动时间: {datetime.datetime.now()}\n")
            f.write(f"# 日志级别: {self.log_level.value}\n")
            f.write(f"# DEBUG模式: {self.debug_mode}\n")
            f.write("=" * 80 + "\n\n")
        
        self.agent_log_files[agent_class_name] = agent_log_file
        return agent_log_file
    
    def _init_log_file(self):
        """初始化日志文件"""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"avm2_system_{timestamp}.log"
        self.log_file = os.path.join(self.log_dir, log_filename)
        
        # 写入日志文件头
        with open(self.log_file, 'w', encoding='utf-8') as f:
            f.write(f"# AVM2 系统日志 - 启动时间: {datetime.datetime.now()}\n")
            f.write(f"# 日志级别: {self.log_level.value}\n")
            f.write(f"# DEBUG模式: {self.debug_mode}\n")
            f.write("=" * 80 + "\n\n")
    
    def set_debug_mode(self, enabled: bool):
        """设置DEBUG模式"""
        self.debug_mode = enabled
        self._log(LogLevel.INFO, f"DEBUG模式 {'启用' if enabled else '禁用'}")
    
    def set_log_level(self, level: LogLevel):
        """设置日志级别"""
        self.log_level = level
        self._log(LogLevel.INFO, f"日志级别设置为: {level.value}")
    
    def _should_log(self, level: LogLevel) -> bool:
        """判断是否应该记录该级别的日志"""
        level_priority = {
            LogLevel.DEBUG: 10,
            LogLevel.INFO: 20,
            LogLevel.WARNING: 30,
            LogLevel.ERROR: 40,
            LogLevel.CRITICAL: 50
        }
        
        current_priority = level_priority.get(self.log_level, 20)
        message_priority = level_priority.get(level, 10)
        
        return message_priority >= current_priority
    
    def _get_caller_info(self) -> Dict[str, str]:
        """获取调用者信息（函数名和行号）"""
        try:
            # 获取调用栈，跳过logger内部调用
            frame = inspect.currentframe()
            # 跳过logger内部调用
            for _ in range(4):  # 跳过logger内部调用
                frame = frame.f_back
                if frame is None:
                    break
            
            if frame:
                caller_frame_info = inspect.getframeinfo(frame)
                return {
                    "function": caller_frame_info.function,
                    "filename": os.path.basename(caller_frame_info.filename),
                    "lineno": caller_frame_info.lineno
                }
        except:
            pass
        
        return {"function": "unknown", "filename": "unknown", "lineno": "unknown"}
    
    def _log(self, level: LogLevel, message: str, extra_data: Optional[Dict] = None, 
             log_type: str = "core_details", agent_class_name: str = None):
        """
        内部日志记录方法
        log_type: "core_macro" - 核心宏观信息, "core_details" - 核心细节信息, "agent" - Agent特定操作
        agent_class_name: 当log_type为"agent"时，指定Agent类名
        """
        if not self._should_log(level):
            return
        
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        # 获取调用者信息
        caller_info = self._get_caller_info()
        location_info = f"{caller_info['filename']}:{caller_info['function']}:{caller_info['lineno']}"
        
        log_entry = f"[{timestamp}] [{level.value}] [{location_info}] {message}"
        
        if extra_data:
            log_entry += f" | 额外数据: {extra_data}"
        
        # 根据日志类型选择文件
        if log_type == "core_macro":
            log_file = self.core_macro_file
        elif log_type == "core_details":
            log_file = self.core_details_file
        elif log_type == "agent" and agent_class_name:
            log_file = self._get_agent_log_file(agent_class_name)
        else:
            # 默认使用核心细节日志
            log_file = self.core_details_file
        
        # 写入文件
        try:
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + "\n")
        except Exception as e:
            print(f"❌ 写入日志文件失败: {e}")
        
        # 同时输出到控制台（INFO及以上级别）
        if level != LogLevel.DEBUG:
            print(log_entry)
    
    def debug(self, message: str, extra_data: Optional[Dict] = None):
        """DEBUG级别日志 - 记录到核心细节日志"""
        self._log(LogLevel.DEBUG, message, extra_data, "core_details")
    
    def info(self, message: str, extra_data: Optional[Dict] = None):
        """INFO级别日志 - 记录到核心细节日志"""
        self._log(LogLevel.INFO, message, extra_data, "core_details")
    
    def warning(self, message: str, extra_data: Optional[Dict] = None):
        """WARNING级别日志 - 记录到核心细节日志"""
        self._log(LogLevel.WARNING, message, extra_data, "core_details")
    
    def error(self, message: str, extra_data: Optional[Dict] = None):
        """ERROR级别日志 - 记录到核心细节日志"""
        self._log(LogLevel.ERROR, message, extra_data, "core_details")
    
    def critical(self, message: str, extra_data: Optional[Dict] = None):
        """CRITICAL级别日志 - 记录到核心细节日志"""
        self._log(LogLevel.CRITICAL, message, extra_data, "core_details")
    
    def debug_macro(self, message: str, extra_data: Optional[Dict] = None):
        """DEBUG级别宏观信息日志"""
        self._log(LogLevel.DEBUG, message, extra_data, "core_macro")
    
    def info_macro(self, message: str, extra_data: Optional[Dict] = None):
        """INFO级别宏观信息日志"""
        self._log(LogLevel.INFO, message, extra_data, "core_macro")
    
    def debug_agent(self, message: str, agent_class_name: str, extra_data: Optional[Dict] = None):
        """DEBUG级别Agent特定操作日志"""
        self._log(LogLevel.DEBUG, message, extra_data, "agent", agent_class_name)
    
    def info_agent(self, message: str, agent_class_name: str, extra_data: Optional[Dict] = None):
        """INFO级别Agent特定操作日志"""
        self._log(LogLevel.INFO, message, extra_data, "agent", agent_class_name)
    
    def warning_agent(self, message: str, agent_class_name: str, extra_data: Optional[Dict] = None):
        """WARNING级别Agent特定操作日志"""
        self._log(LogLevel.WARNING, message, extra_data, "agent", agent_class_name)
    
    def error_agent(self, message: str, agent_class_name: str, extra_data: Optional[Dict] = None):
        """ERROR级别Agent特定操作日志"""
        self._log(LogLevel.ERROR, message, extra_data, "agent", agent_class_name)
    
    def critical_agent(self, message: str, agent_class_name: str, extra_data: Optional[Dict] = None):
        """CRITICAL级别Agent特定操作日志"""
        self._log(LogLevel.CRITICAL, message, extra_data, "agent", agent_class_name)
    
    # ============================================================================
    # 系统宏观信息记录
    # ============================================================================
    
    def log_macro_system_info(self, agent_system) -> bool:
        """
        记录系统宏观信息
        定时记录系统的整体状态
        """
        current_time = time.time()
        if current_time - self.last_macro_log_time < self.macro_log_interval:
            return False
        
        self.last_macro_log_time = current_time
        
        try:
            # 收集宏观信息
            macro_info = self._collect_macro_info(agent_system)
            
            # 记录宏观信息
            self.info_macro("系统宏观信息记录", macro_info)
            
            return True
            
        except Exception as e:
            self.error(f"记录宏观信息失败: {e}")
            return False
    
    def _collect_macro_info(self, agent_system) -> Dict[str, Any]:
        """收集系统宏观信息"""
        import time
        current_time = time.time()
        agents = getattr(agent_system, 'agents', {})
        message_bus = getattr(agent_system, 'message_bus', None)
        
        # 统计Agent类型
        agent_types = {}
        system_agents = 0
        normal_agents = 0
        
        for agent_id, agent in agents.items():
            agent_type = "普通Agent"
            if hasattr(agent, 'metadata') and agent.metadata:
                agent_type = agent.metadata.get('type', '普通Agent')
            
            if agent_type in ['InputAgent', 'OutputAgent', 'SystemAgent']:
                system_agents += 1
            else:
                normal_agents += 1
            
            agent_types[agent_type] = agent_types.get(agent_type, 0) + 1
        
        # 统计连接信息
        total_connections = 0
        for agent in agents.values():
            input_conns = getattr(agent, 'input_connections', None)
            output_conns = getattr(agent, 'output_connections', None)
            
            if input_conns and hasattr(input_conns, 'connections'):
                total_connections += len(input_conns.connections)
            if output_conns and hasattr(output_conns, 'connections'):
                total_connections += len(output_conns.connections)
        
        # 消息总线统计
        message_stats = {}
        if message_bus and hasattr(message_bus, 'message_history'):
            message_history = message_bus.message_history
            message_stats = {
                "总消息数": len(message_history),
                "最近消息": message_history[-10:] if message_history else []
            }
        
        current_time = time.time() 
        
        return {
            "时间戳": datetime.datetime.now().isoformat(),
            "Agent总数": len(agents),
            "系统Agent数": system_agents,
            "普通Agent数": normal_agents,
            "Agent类型分布": agent_types,
            "总连接数": total_connections,
            "消息统计": message_stats,
            "系统运行时间": f"{current_time - getattr(agent_system, 'start_time', current_time):.2f}秒"
        }
    
    # ============================================================================
    # DEBUG模式激活记录
    # ============================================================================
    
    def log_activation_details(self, agent_id: str, activation_content: str, 
                             message_destinations: List[Dict[str, str]], 
                             is_system_agent: bool = True) -> None:
        """
        DEBUG模式下记录激活详细信息
        记录激活内容和消息发送去向
        is_system_agent: True - 系统Agent激活（记录到核心细节日志）, False - 普通Agent激活
        """
        if not self.debug_mode:
            return
        
        activation_data = {
            "agent_id": agent_id,
            "激活内容": activation_content,
            "消息发送去向": message_destinations,
            "激活时间": datetime.datetime.now().isoformat()
        }
        
        log_type = "core_details" if is_system_agent else "agent"
        self._log(LogLevel.DEBUG, f"Agent激活详情 - {agent_id}", activation_data, log_type)
    
    def log_message_sending(self, sender_id: str, message_content: str, 
                          receiver_ids: List[str], channels: List[str],
                          is_system_agent: bool = True) -> None:
        """
        DEBUG模式下记录消息发送详情
        is_system_agent: True - 系统Agent消息（记录到核心细节日志）, False - 普通Agent消息
        """
        if not self.debug_mode:
            return
        
        message_data = {
            "发送者": sender_id,
            "消息内容": message_content[:200] + "..." if len(message_content) > 200 else message_content,
            "接收者": receiver_ids,
            "通道": channels,
            "发送时间": datetime.datetime.now().isoformat()
        }
        
        log_type = "core_details" if is_system_agent else "agent"
        self._log(LogLevel.DEBUG, f"消息发送详情 - {sender_id}", message_data, log_type)
    
    def log_agent_creation(self, agent_id: str, agent_data: Dict, 
                          agent_class_name: str = None) -> None:
        """记录Agent创建"""
        creation_data = {
            "agent_id": agent_id,
            "创建时间": datetime.datetime.now().isoformat(),
            "agent数据": {
                "prompt_length": len(agent_data.get('prompt', '')),
                "input_connections": len(agent_data.get('input_connections', {})),
                "output_connections": len(agent_data.get('output_connections', {})),
                "activation_channels": len(agent_data.get('activation_channels', []))
            }
        }
        
        if agent_class_name:
            # 系统Agent的特定操作记录到Agent日志
            self.info(f"Agent创建 - {agent_id}", creation_data, "agent", agent_class_name)
        else:
            # 普通Agent创建记录到核心细节日志
            self.info(f"Agent创建 - {agent_id}", creation_data, "core_details")
    
    def log_agent_deletion(self, agent_id: str, recycle_bin_path: str, 
                          agent_class_name: str = None) -> None:
        """记录Agent删除"""
        deletion_data = {
            "agent_id": agent_id,
            "删除时间": datetime.datetime.now().isoformat(),
            "回收站路径": recycle_bin_path
        }
        
        if agent_class_name:
            # 系统Agent的特定操作记录到Agent日志
            self.info(f"Agent删除 - {agent_id}", deletion_data, "agent", agent_class_name)
        else:
            # 普通Agent删除记录到核心细节日志
            self.info(f"Agent删除 - {agent_id}", deletion_data, "core_details")
    
    def log_system_agent_operation(self, agent_class_name: str, operation: str, 
                                  details: Dict, level: LogLevel = LogLevel.INFO) -> None:
        """
        记录系统Agent的特定程序操作
        这些操作记录到对应的Agent日志文件中
        """
        operation_data = {
            "操作": operation,
            "详情": details,
            "时间": datetime.datetime.now().isoformat()
        }
        
        if level == LogLevel.DEBUG:
            self.debug_agent(f"系统Agent操作 - {operation}", agent_class_name, operation_data)
        elif level == LogLevel.INFO:
            self.info_agent(f"系统Agent操作 - {operation}", agent_class_name, operation_data)
        elif level == LogLevel.WARNING:
            self.warning_agent(f"系统Agent操作 - {operation}", agent_class_name, operation_data)
        elif level == LogLevel.ERROR:
            self.error_agent(f"系统Agent操作 - {operation}", agent_class_name, operation_data)
        elif level == LogLevel.CRITICAL:
            self.critical_agent(f"系统Agent操作 - {operation}", agent_class_name, operation_data)


# 全局日志实例
logger = Logger()
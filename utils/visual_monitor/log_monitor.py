#!/usr/bin/env python3
"""
日志文件监控器
使用 watchdog 实时监控日志文件变化，解析 JSONL 日志并更新拓扑状态
"""

import json
import os
import time
import threading
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class LogFileHandler(FileSystemEventHandler):
    """日志文件变化处理器"""

    def __init__(self, callback: Callable[[dict], None]):
        self.callback = callback
        self._file_positions: Dict[str, int] = {}

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent):
            file_path = event.src_path
            if file_path.endswith('.jsonl'):
                self._process_file(file_path)

    def _process_file(self, file_path: str):
        """读取文件新增内容并解析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # 获取上次读取位置
                last_pos = self._file_positions.get(file_path, 0)
                f.seek(last_pos)

                # 读取新增行
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            self.callback(entry)
                        except json.JSONDecodeError:
                            pass  # 跳过无效行

                # 更新位置
                self._file_positions[file_path] = f.tell()

        except Exception as e:
            print(f"Error processing {file_path}: {e}")


class LogMonitor:
    """日志文件监控器"""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.callbacks: List[Callable[[dict], None]] = []
        self._observer: Optional[Observer] = None
        self._running = False
        self._lock = threading.Lock()

        # 拓扑状态
        self.agents: Dict[str, dict] = {}  # agent_id -> agent info
        self.connections: List[dict] = []  # 连接列表
        self.recent_logs: List[dict] = []  # 最近日志（用于显示）

        # DETAIL 日志相关状态
        self.message_flows: List[dict] = []  # 消息流记录
        self.agent_activations: Dict[str, dict] = {}  # agent_id -> 激活信息

        # ARCH 日志相关状态
        self.async_state: Dict[str, Any] = {
            'timestamp': 0,
            'current_task': None,
            'all_tasks_count': 0,
            'all_tasks': [],
            'event_loop': None
        }
        self.recent_tasks: List[dict] = []  # 最近的任务事件

    def add_callback(self, callback: Callable[[dict], None]):
        """添加日志Entry 回调"""
        with self._lock:
            self.callbacks.append(callback)

    def remove_callback(self, callback: Callable[[dict], None]):
        """移除回调"""
        with self._lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)

    def _notify_callbacks(self, entry: dict):
        """通知所有回调"""
        with self._lock:
            for callback in self.callbacks:
                try:
                    callback(entry)
                except Exception as e:
                    print(f"Callback error: {e}")

    def _handle_log_entry(self, entry: dict):
        """处理日志条目，更新拓扑状态"""
        event_type = entry.get('event_type', '')
        source = entry.get('source', '')
        data = entry.get('data', {})
        timestamp = entry.get('timestamp_us', 0)
        level = entry.get('level', 'info')

        # 更新最近日志
        self.recent_logs.append(entry)
        if len(self.recent_logs) > 1000:
            self.recent_logs = self.recent_logs[-500:]

        # 处理 Agent 创建
        if event_type == 'agent_created':
            agent_id = data.get('agent_id', '')
            if agent_id:
                self.agents[agent_id] = {
                    'id': agent_id,
                    'type': data.get('agent_type', 'Unknown'),
                    'object_addr': data.get('object_addr', ''),
                    'queue_addr': data.get('queue_addr', ''),
                    'created_at': timestamp,
                    'input_connections': [],
                    'output_connections': [],
                    'message_count': 0,
                    'last_active': timestamp,
                    'activation_count': 0
                }

        # 处理 InputAgent 创建
        elif event_type == 'input_agent_created':
            agent_id = data.get('agent_id', '')
            if agent_id:
                self.agents[agent_id] = {
                    'id': agent_id,
                    'type': data.get('agent_type', 'InputAgent'),
                    'object_addr': data.get('object_addr', ''),
                    'queue_addr': data.get('queue_addr', ''),
                    'created_at': timestamp,
                    'input_connections': [],
                    'output_connections': [],
                    'message_count': 0,
                    'last_active': timestamp,
                    'activation_count': 0
                }

        # 处理 OutputAgent 创建
        elif event_type == 'output_agent_created':
            agent_id = data.get('agent_id', '')
            if agent_id:
                self.agents[agent_id] = {
                    'id': agent_id,
                    'type': data.get('agent_type', 'OutputAgent'),
                    'object_addr': data.get('object_addr', ''),
                    'queue_addr': data.get('queue_addr', ''),
                    'created_at': timestamp,
                    'input_connections': [],
                    'output_connections': [],
                    'message_count': 0,
                    'last_active': timestamp,
                    'activation_count': 0
                }

        # 处理输入连接设置
        elif event_type == 'input_connection_set':
            sender_id = data.get('sender_id', '')
            keyword = data.get('keyword', '')
            # 从 source 提取当前 agent id
            current_id = source.replace('Agent.', '').replace('InputAgent.', '').replace('OutputAgent.', '')
            if current_id in self.agents:
                conn = {'from': sender_id, 'to': current_id, 'keyword': keyword}
                self.connections.append(conn)
                self.agents[current_id]['input_connections'].append(sender_id)

        # 处理输出连接设置
        elif event_type == 'output_connection_set':
            receiver_id = data.get('receiver_id', '')
            keyword = data.get('keyword', '')
            current_id = source.replace('Agent.', '').replace('InputAgent.', '').replace('OutputAgent.', '')
            if current_id in self.agents:
                conn = {'from': current_id, 'to': receiver_id, 'keyword': keyword}
                self.connections.append(conn)
                self.agents[current_id]['output_connections'].append(receiver_id)

        # 处理连接删除
        elif 'connection_deleted' in event_type:
            # 简化处理：不实际删除，只是逻辑上标记
            pass

        # 处理消息接收（用于激活计数）
        elif event_type == 'message_received':
            sender = data.get('sender', '')
            current_id = source.replace('Agent.', '').replace('InputAgent.', '').replace('OutputAgent.', '')
            if current_id in self.agents:
                self.agents[current_id]['message_count'] += 1
                self.agents[current_id]['last_active'] = timestamp

        # ========== DETAIL 日志处理 ==========
        # 处理消息流事件
        elif event_type == 'message_flow' or (level == 'detail' and 'message_flow' in event_type):
            source_agent = data.get('source_agent') or data.get('sender_id', '')
            target_agent = data.get('target_agent') or data.get('receiver_id', '')

            flow_entry = {
                'from': source_agent,
                'to': target_agent,
                'timestamp': timestamp,
                'message_type': data.get('message_type', 'unknown'),
                'duration_ms': data.get('processing_time_ms', 0),
                'keyword': data.get('keyword', '')
            }
            self.message_flows.append(flow_entry)

            # 限制存储数量
            if len(self.message_flows) > 500:
                self.message_flows = self.message_flows[-250:]

        # 处理 Agent 激活事件
        elif event_type == 'agent_activated' or (level == 'detail' and 'activated' in event_type):
            agent_id = data.get('agent_id', '')
            if agent_id and agent_id in self.agents:
                self.agents[agent_id]['activation_count'] = data.get('activation_count',
                    self.agents[agent_id].get('activation_count', 0) + 1)
                self.agents[agent_id]['last_activation'] = timestamp
                self.agents[agent_id]['last_active'] = timestamp

                self.agent_activations[agent_id] = {
                    'agent_id': agent_id,
                    'timestamp': timestamp,
                    'queue_size': data.get('queue_size', 0)
                }

        # ========== ARCH 日志处理 ==========
        # 处理异步上下文快照
        elif event_type == 'async_snapshot' or (level == 'arch' and 'async' in event_type):
            async_context = entry.get('async_context', {})
            self.async_state = {
                'timestamp': timestamp,
                'current_task': async_context.get('current_task'),
                'all_tasks_count': len(async_context.get('all_tasks', [])),
                'all_tasks': async_context.get('all_tasks', []),
                'event_loop': async_context.get('event_loop')
            }

        # 处理任务创建事件
        elif event_type == 'task_created' or (level == 'arch' and 'task_created' in event_type):
            task_info = {
                'task_id': data.get('task_id'),
                'task_name': data.get('task_name', 'unknown'),
                'coro_name': data.get('coro_name', 'unknown'),
                'timestamp': timestamp,
                'event': 'created'
            }
            self.recent_tasks.append(task_info)
            if len(self.recent_tasks) > 200:
                self.recent_tasks = self.recent_tasks[-100:]

        # 处理任务完成事件
        elif event_type == 'task_completed' or (level == 'arch' and 'task_completed' in event_type):
            task_info = {
                'task_id': data.get('task_id'),
                'task_name': data.get('task_name', 'unknown'),
                'duration_ms': data.get('duration_ms', 0),
                'timestamp': timestamp,
                'event': 'completed'
            }
            self.recent_tasks.append(task_info)
            if len(self.recent_tasks) > 200:
                self.recent_tasks = self.recent_tasks[-100:]

        # 通知回调
        self._notify_callbacks(entry)

    def start(self):
        """开始监控"""
        if self._running:
            return

        self._running = True

        # 设置文件监控
        handler = LogFileHandler(self._handle_log_entry)
        self._observer = Observer()

        # 监控 system.jsonl (CONTENT 日志)
        system_log = self.log_dir / "system.jsonl"
        if system_log.exists():
            self._observer.schedule(handler, str(self.log_dir), recursive=False)
            self._load_existing_logs(system_log)
            print(f"LogMonitor: Watching {system_log}")

        # 监控 detail/system.detail.jsonl (DETAIL 日志)
        detail_log = self.log_dir / "detail" / "system.detail.jsonl"
        if detail_log.exists():
            detail_dir = self.log_dir / "detail"
            self._observer.schedule(handler, str(detail_dir), recursive=False)
            self._load_existing_logs(detail_log)
            print(f"LogMonitor: Watching {detail_log}")

        # 监控 arch/system.arch.jsonl (ARCH 日志)
        arch_log = self.log_dir / "arch" / "system.arch.jsonl"
        if arch_log.exists():
            arch_dir = self.log_dir / "arch"
            self._observer.schedule(handler, str(arch_dir), recursive=False)
            self._load_existing_logs(arch_log)
            print(f"LogMonitor: Watching {arch_log}")

        self._observer.start()
        print(f"LogMonitor started")

    def _load_existing_logs(self, log_file: Path):
        """加载现有的日志内容"""
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entry = json.loads(line)
                            self._handle_log_entry(entry)
                        except json.JSONDecodeError:
                            pass
        except Exception as e:
            print(f"Error loading existing logs from {log_file}: {e}")

    def stop(self):
        """停止监控"""
        if not self._running:
            return

        self._running = False
        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

    def get_topology(self) -> dict:
        """获取当前拓扑数据"""
        return {
            'agents': list(self.agents.values()),
            'connections': self.connections,
            'timestamp': int(time.time() * 1000)
        }

    def get_recent_logs(self, limit: int = 100) -> List[dict]:
        """获取最近日志"""
        return self.recent_logs[-limit:]

    def get_agent(self, agent_id: str) -> Optional[dict]:
        """获取特定 Agent 信息"""
        return self.agents.get(agent_id)

    def get_stats(self) -> dict:
        """获取统计信息"""
        return {
            'total_agents': len(self.agents),
            'total_connections': len(self.connections),
            'logs_processed': len(self.recent_logs),
            'message_flows_count': len(self.message_flows),
            'async_tasks_count': self.async_state.get('all_tasks_count', 0)
        }

    def get_recent_message_flows(self, limit: int = 10) -> List[dict]:
        """获取最近的消息流"""
        return self.message_flows[-limit:] if self.message_flows else []

    def get_async_state(self) -> dict:
        """获取异步状态"""
        return self.async_state.copy()

    def get_recent_tasks(self, limit: int = 20) -> List[dict]:
        """获取最近的任务事件"""
        return self.recent_tasks[-limit:] if self.recent_tasks else []


# 全局监控实例
_monitor: Optional[LogMonitor] = None


def get_monitor(log_dir: str = "logs") -> LogMonitor:
    """获取或创建监控实例"""
    global _monitor
    if _monitor is None:
        _monitor = LogMonitor(log_dir)
    return _monitor

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
                    'last_active': timestamp
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

        # 只监控 system.jsonl 文件
        system_log = self.log_dir / "system.jsonl"
        if system_log.exists():
            # 监控整个目录但只处理 system.jsonl
            self._observer.schedule(handler, str(self.log_dir), recursive=False)
            # 读取现有日志内容
            self._load_existing_logs(system_log)

        self._observer.start()
        print(f"LogMonitor started, watching: {self.log_dir}/system.jsonl")

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
            print(f"Error loading existing logs: {e}")

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
            'logs_processed': len(self.recent_logs)
        }


# 全局监控实例
_monitor: Optional[LogMonitor] = None


def get_monitor(log_dir: str = "logs") -> LogMonitor:
    """获取或创建监控实例"""
    global _monitor
    if _monitor is None:
        _monitor = LogMonitor(log_dir)
    return _monitor

#!/usr/bin/env python3
"""
FastAPI 服务器
提供 WebSocket 实时推送和 HTTP 静态文件服务
"""

import json
import asyncio
import argparse
import mimetypes
from pathlib import Path
from typing import Set
import websockets
from websockets.server import WebSocketServerProtocol
from websockets.http11 import Response
from websockets.datastructures import Headers
from http import HTTPStatus

from .log_monitor import LogMonitor, get_monitor


class MonitorServer:
    """监控服务器"""

    def __init__(self, host: str = "localhost", port: int = 8765, log_dir: str = "logs"):
        self.host = host
        self.port = port
        self.log_dir = Path(log_dir)

        self.monitor: LogMonitor = None

        # WebSocket 连接管理
        self.connections: Set[WebSocketServerProtocol] = set()
        self._running = False

        # 存储事件循环引用，用于跨线程调度
        self._loop = None

        # 静态文件目录
        self.static_dir = Path(__file__).parent / "static"
        self.template_dir = Path(__file__).parent / "templates"

    async def handle_connection(self, websocket: WebSocketServerProtocol):
        """处理 WebSocket 连接"""
        self.connections.add(websocket)
        client_addr = websocket.remote_address
        print(f"Client connected: {client_addr}")

        try:
            # 发送初始数据
            await websocket.send(json.dumps({
                'type': 'init',
                'topology': self.monitor.get_topology(),
                'stats': self.monitor.get_stats(),
                'async_state': self.monitor.get_async_state(),
                'recent_flows': self.monitor.get_recent_message_flows(10)
            }))

            # 保持连接并接收消息
            async for message in websocket:
                try:
                    data = json.loads(message)
                    msg_type = data.get('type', '')

                    if msg_type == 'get_topology':
                        await websocket.send(json.dumps({
                            'type': 'topology',
                            'data': self.monitor.get_topology()
                        }))
                    elif msg_type == 'get_logs':
                        limit = data.get('limit', 100)
                        await websocket.send(json.dumps({
                            'type': 'logs',
                            'data': self.monitor.get_recent_logs(limit)
                        }))
                    elif msg_type == 'get_agent':
                        agent_id = data.get('agent_id')
                        agent = self.monitor.get_agent(agent_id)
                        await websocket.send(json.dumps({
                            'type': 'agent',
                            'data': agent
                        }))
                    elif msg_type == 'get_stats':
                        await websocket.send(json.dumps({
                            'type': 'stats',
                            'data': self.monitor.get_stats()
                        }))

                except json.JSONDecodeError:
                    pass

        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {client_addr}")
        finally:
            self.connections.discard(websocket)

    async def broadcast(self, data: dict):
        """广播数据到所有连接"""
        if not self.connections:
            print(f"[Broadcast] No connections to broadcast to")
            return

        message = json.dumps(data)
        print(f"[Broadcast] Broadcasting to {len(self.connections)} clients: {data.get('type', 'unknown')}")
        await asyncio.gather(
            *[ws.send(message) for ws in self.connections],
            return_exceptions=True
        )

    def on_log_entry(self, entry: dict):
        """日志条目回调 - 从 watchdog 线程调用"""
        if self._loop is None:
            print("[Warning] No event loop stored, cannot broadcast")
            return
        try:
            asyncio.run_coroutine_threadsafe(
                self._broadcast_entry(entry),
                self._loop
            )
        except Exception as e:
            print(f"[Error] Failed to schedule broadcast: {e}")

    async def _broadcast_entry(self, entry: dict):
        """广播日志条目"""
        event_type = entry.get('event_type', '')
        level = entry.get('level', 'info')
        source = entry.get('source', '')

        print(f"[Broadcast] Processing entry: event_type={event_type}, source={source}")

        # 拓扑更新（已有）
        if event_type in ['agent_created', 'input_connection_set', 'output_connection_set',
                          'input_connection_keyword_updated', 'output_connection_keyword_updated']:
            print(f"[Broadcast] Broadcasting topology_update for {event_type}")
            topology = self.monitor.get_topology()
            print(f"[Broadcast] Topology has {len(topology['connections'])} connections")
            await self.broadcast({
                'type': 'topology_update',
                'topology': topology
            })

        # 新增：消息流更新
        elif event_type in ['message_flow', 'message_sent', 'message_delivered'] or 'message_flow' in event_type:
            await self.broadcast({
                'type': 'message_flow',
                'entry': entry,
                'recent_flows': self.monitor.get_recent_message_flows(10)
            })

        # 新增：Agent 激活更新
        elif event_type in ['agent_activated', 'processing_started'] or 'activated' in event_type:
            await self.broadcast({
                'type': 'agent_activated',
                'entry': entry,
                'agent': self.monitor.get_agent(entry.get('data', {}).get('agent_id', ''))
            })

        # 新增：异步状态更新
        elif event_type in ['async_snapshot', 'task_created', 'task_completed'] or 'async' in event_type:
            await self.broadcast({
                'type': 'async_update',
                'entry': entry,
                'async_state': self.monitor.get_async_state(),
                'recent_tasks': self.monitor.get_recent_tasks(20)
            })

        # 普通日志条目
        else:
            await self.broadcast({
                'type': 'log_entry',
                'entry': entry
            })

    def get_mime_type(self, path: str) -> str:
        """获取 MIME 类型"""
        mime_type, _ = mimetypes.guess_type(path)
        return mime_type or 'application/octet-stream'

    async def handle_http_request(self, reader, writer):
        """处理 HTTP 请求"""
        try:
            request_line = await reader.readline()
            request_line = request_line.decode('utf-8').strip()

            if not request_line:
                return

            parts = request_line.split(' ')
            if len(parts) != 3:
                return

            method, path, version = parts

            # 解析路径
            if path == '/':
                file_path = self.template_dir / "index.html"
            elif path.startswith('/static/'):
                file_path = self.static_dir / path[8:]
            else:
                file_path = self.template_dir / path[1:]

            # 检查文件是否存在
            if file_path.exists() and file_path.is_file():
                mime_type = self.get_mime_type(str(file_path))
                with open(file_path, 'rb') as f:
                    content = f.read()

                response = (
                    f"HTTP/1.1 200 OK\r\n"
                    f"Content-Type: {mime_type}\r\n"
                    f"Content-Length: {len(content)}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                ).encode('utf-8') + content
            else:
                content = b"404 Not Found"
                response = (
                    f"HTTP/1.1 404 Not Found\r\n"
                    f"Content-Type: text/plain\r\n"
                    f"Content-Length: {len(content)}\r\n"
                    f"Connection: close\r\n"
                    f"\r\n"
                ).encode('utf-8') + content

            writer.write(response)
            await writer.drain()
        except Exception as e:
            print(f"HTTP error: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def run_server(self):
        """运行服务器"""
        # 存储事件循环引用，供回调使用
        self._loop = asyncio.get_event_loop()

        # 初始化监控器
        self.monitor = get_monitor(str(self.log_dir))

        # 添加回调
        self.monitor.add_callback(self.on_log_entry)

        # 启动监控
        self.monitor.start()

        # 启动 WebSocket 服务器
        self._running = True
        print(f"Starting WebSocket server on ws://{self.host}:{self.port}")
        print(f"HTTP server available at http://{self.host}:{self.port}")

        # 创建 WebSocket 服务器 - websockets 16.0+ 使用方式
        import functools
        ws_server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            process_request=functools.partial(self._process_request_wrapper)
        )

        await asyncio.Future()  # 运行直到取消

    async def _process_request_wrapper(self, connection, request):
        """包装 process_http_request 以适配 websockets 14.0+ API

        websockets 14.0+ 中 process_request 接收 (connection, request) 参数
        其中 request 对象有 path, headers 等属性

        对于 WebSocket 升级请求（带 Upgrade: websocket 头），返回 None 让 websockets 处理握手
        对于普通 HTTP 请求，返回 HTTP Response
        """
        path = request.path if hasattr(request, 'path') else '/'

        # 检查是否是 WebSocket 升级请求
        # 如果是，返回 None 让 websockets 正常处理握手
        upgrade_header = request.headers.get('Upgrade', '').lower()
        connection_header = request.headers.get('Connection', '').lower()

        if 'websocket' in upgrade_header or 'upgrade' in connection_header:
            return None  # 让 websockets 处理 WebSocket 握手

        # 普通 HTTP 请求，返回静态文件
        return await self.process_http_request(path, request)

    async def process_http_request(self, path: str, request):
        """处理 HTTP 请求，返回静态文件 - websockets 14.0+ 兼容版本"""
        # 解析路径
        if path == '/':
            file_path = self.template_dir / "index.html"
        elif path.startswith('/static/'):
            file_path = self.static_dir / path[8:]
        else:
            file_path = self.template_dir / path[1:]

        # 检查文件是否存在
        if file_path.exists() and file_path.is_file():
            mime_type = self.get_mime_type(str(file_path))
            with open(file_path, 'rb') as f:
                content = f.read()

            # websockets 16.0+ 要求 headers 使用 Headers 对象
            headers = Headers()
            headers["Content-Type"] = mime_type
            headers["Content-Length"] = str(len(content))

            return Response(
                status_code=HTTPStatus.OK,
                reason_phrase="OK",
                headers=headers,
                body=content
            )

        # 返回 404
        content = b"404 Not Found"
        headers = Headers()
        headers["Content-Type"] = "text/plain"
        headers["Content-Length"] = str(len(content))

        return Response(
            status_code=HTTPStatus.NOT_FOUND,
            reason_phrase="Not Found",
            headers=headers,
            body=content
        )

    def stop(self):
        """停止服务器"""
        self._running = False
        if self.monitor:
            self.monitor.stop()


async def run_async_server(host: str = "localhost", port: int = 8765, log_dir: str = "logs"):
    """运行异步服务器"""
    server = MonitorServer(host, port, log_dir)
    try:
        await server.run_server()
    except KeyboardInterrupt:
        print("Shutting down...")
        server.stop()


def run_server():
    """入口函数"""
    parser = argparse.ArgumentParser(description='AVM2 Visual Monitor Server')
    parser.add_argument('--host', default='localhost', help='Host to bind to')
    parser.add_argument('--port', type=int, default=8765, help='Port to bind to')
    parser.add_argument('--log-dir', default='logs', help='Log directory to monitor')

    args = parser.parse_args()

    print(f"AVM2 Visual Monitor")
    print(f"Host: {args.host}")
    print(f"Port: {args.port}")
    print(f"Log Dir: {args.log_dir}")
    print("-" * 40)

    asyncio.run(run_async_server(args.host, args.port, args.log_dir))


if __name__ == '__main__':
    run_server()

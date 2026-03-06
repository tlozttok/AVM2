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

        # 静态文件目录
        self.static_dir = Path(__file__).parent / "static"
        self.template_dir = Path(__file__).parent / "templates"

    async def handle_connection(self, websocket: WebSocketServerProtocol, path: str = None):
        """处理 WebSocket 连接"""
        self.connections.add(websocket)
        client_addr = websocket.remote_address
        print(f"Client connected: {client_addr}")

        try:
            # 发送初始数据
            await websocket.send(json.dumps({
                'type': 'init',
                'topology': self.monitor.get_topology(),
                'stats': self.monitor.get_stats()
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
            return

        message = json.dumps(data)
        await asyncio.gather(
            *[ws.send(message) for ws in self.connections],
            return_exceptions=True
        )

    def on_log_entry(self, entry: dict):
        """日志条目回调"""
        try:
            loop = asyncio.get_event_loop()
            asyncio.run_coroutine_threadsafe(
                self._broadcast_entry(entry),
                loop
            )
        except RuntimeError:
            pass

    async def _broadcast_entry(self, entry: dict):
        """广播日志条目"""
        event_type = entry.get('event_type', '')

        if event_type in ['agent_created', 'input_connection_set', 'output_connection_set']:
            await self.broadcast({
                'type': 'topology_update',
                'topology': self.monitor.get_topology()
            })
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

        # 创建 WebSocket 服务器
        ws_server = await websockets.serve(
            self.handle_connection,
            self.host,
            self.port,
            process_request=self.process_http_request
        )

        await asyncio.Future()  # 运行直到取消

    async def process_http_request(self, path, request_headers):
        """处理 HTTP 请求，返回静态文件"""
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

            headers = [
                ("Content-Type", mime_type),
                ("Content-Length", str(len(content))),
            ]
            return (HTTPStatus.OK, headers, content)

        # 返回 404
        return (HTTPStatus.NOT_FOUND, [], b"404 Not Found")

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

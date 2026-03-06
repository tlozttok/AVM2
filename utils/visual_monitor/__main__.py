#!/usr/bin/env python3
"""
AVM2 可视化监控入口
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from utils.visual_monitor.server import run_server

if __name__ == '__main__':
    run_server()

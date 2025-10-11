"""
AVM2 系统主程序 - 使用class_config.json安全动态创建Agent
"""

import asyncio
import os
import sys
import importlib
import glob
import json
import yaml
from driver.driver import Agent
from driver.async_system import AgentSystem
from driver import async_system

from utils.logger import basic_logger

# 配置常量
DEBUG_MODE = True  # 设置为True时禁用自动文件同步
UPDATE_CLASS_CONFIG = False  # 设置为True时在执行main前更新class_config.json

def load_class_config():
    """加载class_config.json配置文件"""
    config_path = "system_interface_agents/class_config.json"
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        basic_logger.info(f"成功加载class_config.json，包含 {len(config)} 个Agent映射")
        return config
    except Exception as e:
        basic_logger.error(f"加载class_config.json失败: {e}")
        return {}

def create_class_mapping(class_config):
    """
    根据class_config创建Agent ID到类对象的映射
    Args:
        class_config: 类配置字典
    Returns:
        dict: Agent ID到类对象的映射
    """
    class_mapping = {}
    
    for agent_id, class_path in class_config.items():
        try:
            # 解析类路径格式: "module_name.ClassName"
            if '.' not in class_path:
                basic_logger.error(f"无效的类路径格式: {class_path}")
                continue
            
            module_name, class_name = class_path.rsplit('.', 1)
            
            # 动态导入模块
            module = importlib.import_module(f"system_interface_agents.{module_name}")
            
            # 获取类对象
            agent_class = getattr(module, class_name)
            class_mapping[agent_id] = agent_class
            basic_logger.debug(f"成功映射: {agent_id} -> {class_path}")
            
        except ImportError as e:
            basic_logger.error(f"导入模块失败 {module_name}: {e}")
        except AttributeError as e:
            basic_logger.error(f"模块中找不到类 {class_name}: {e}")
    
    return class_mapping

async def main():
    """主程序入口"""
    
    basic_logger.info("进入主函数")
    
    # 如果需要更新class_config.json
    if UPDATE_CLASS_CONFIG:
        basic_logger.info("正在更新class_config.json...")
        try:
            from utils.generate_class_config import generate_class_config
            generate_class_config()
        except Exception as e:
            basic_logger.error(f"更新class_config.json失败: {e}")
    
    # 加载类配置
    class_config = load_class_config()
    if not class_config:
        basic_logger.error("无法加载class_config.json，系统无法启动")
        return
    
    # 创建类对象映射
    class_mapping = create_class_mapping(class_config)
    if not class_mapping:
        basic_logger.error("无法创建类映射，系统无法启动")
        return
    
    # 初始化系统
    system = AgentSystem()
    async_system.SYMBOLIC_REAL = system
    
    basic_logger.info("开始加载普通Agent")
    
    # 遍历Agents文件夹中的普通Agent
    agent_files = glob.glob("Agents/*.yaml")
    for agent_file in agent_files:
        agent = Agent("")
        agent.sync_from_file(agent_file)
        
        # 设置自动同步状态
        agent.auto_sync_enabled = not DEBUG_MODE
        
        system.register_agent(agent)
        basic_logger.info(f"加载普通Agent: {agent.id}")
        
    basic_logger.info("加载普通Agent完成")
    basic_logger.info("开始加载系统Agent")

    # 遍历系统Agent
    system_agent_files = glob.glob("Agents/SystemAgents/*.yaml")
    for system_agent_file in system_agent_files:
        with open(system_agent_file, 'r', encoding='utf-8') as f:
            agent_data = yaml.safe_load(f)
        
        agent_id = agent_data.get("id")
        if not agent_id:
            basic_logger.error(f"系统Agent文件 {system_agent_file} 中找不到id字段")
            continue
        
        # 使用类映射创建Agent实例
        if agent_id in class_mapping:
            try:
                agent_class = class_mapping[agent_id]
                agent = agent_class(agent_id)
                agent.sync_from_file(system_agent_file)
                
                # 设置自动同步状态
                agent.auto_sync_enabled = not DEBUG_MODE
                
                system.register_agent(agent)
                basic_logger.info(f"加载系统Agent: {agent.id}")
                
            except Exception as e:
                basic_logger.error(f"创建系统Agent实例失败 {agent_id}: {e}")
        else:
            basic_logger.error(f"未找到Agent ID '{agent_id}' 的类映射")
    
    basic_logger.info("加载系统Agent完成")
    
    await system.start()
    
    basic_logger.info("系统加载完成")
    
    try:
        
        # 保持程序运行，等待消息
        print("📡 系统正在运行")
        print("按 Ctrl+C 停止系统")
        basic_logger.info("开始运行系统")
        
        # 创建一个永久等待的future
        await asyncio.Future()
        
    except KeyboardInterrupt:
        print("\n🛑 收到停止信号，正在关闭系统...")
        basic_logger.info("收到停止信号，正在关闭系统")
    finally:
        await system.stop()
        basic_logger.info("系统已关闭")


if __name__ == "__main__":
    asyncio.run(main())
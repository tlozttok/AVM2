"""
生成class_config.json的工具程序
扫描SystemAgents文件夹和system_interface_agents文件夹，生成Agent ID到类路径的映射
"""

import os
import json
import glob
import yaml
import importlib
from pathlib import Path

def scan_system_agents():
    """扫描SystemAgents文件夹，获取Agent ID和类名的映射"""
    system_agents_dir = "Agents/SystemAgents"
    agent_mapping = {}
    
    # 扫描所有yaml文件
    yaml_files = glob.glob(f"{system_agents_dir}/*.yaml")
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r', encoding='utf-8') as f:
                agent_data = yaml.safe_load(f)
            
            agent_id = agent_data.get("id")
            
            # 获取类名，支持metadata中的class_name
            class_name = None
            if "metadata" in agent_data and "class_name" in agent_data["metadata"]:
                class_name = agent_data["metadata"]["class_name"]
            elif "class_name" in agent_data:
                class_name = agent_data["class_name"]
            
            if agent_id and class_name:
                agent_mapping[agent_id] = class_name
                print(f"✅ 找到Agent: {agent_id} -> {class_name}")
            else:
                print(f"⚠️ 文件 {yaml_file} 缺少id或class_name")
                
        except Exception as e:
            print(f"❌ 解析文件 {yaml_file} 失败: {e}")
    
    return agent_mapping

def find_class_module(class_name):
    """在system_interface_agents文件夹中查找类所在的模块"""
    interface_dir = "system_interface_agents"
    python_files = glob.glob(f"{interface_dir}/*.py")
    
    for py_file in python_files:
        # 提取模块名（不含路径和扩展名）
        module_name = Path(py_file).stem
        
        try:
            # 尝试导入模块
            module = importlib.import_module(f"{interface_dir}.{module_name}")
            
            # 检查模块中是否有目标类
            if hasattr(module, class_name):
                print(f"✅ 找到类 {class_name} 在模块 {module_name}")
                return module_name
                
        except ImportError as e:
            print(f"⚠️ 导入模块 {module_name} 失败: {e}")
            continue
    
    return None

def generate_class_config():
    """生成class_config.json文件"""
    print("🔍 开始扫描SystemAgents文件夹...")
    agent_mapping = scan_system_agents()
    
    if not agent_mapping:
        print("❌ 未找到任何SystemAgent配置")
        return False
    
    print(f"\n🔍 开始查找类文件...")
    class_config = {}
    
    for agent_id, class_name in agent_mapping.items():
        module_name = find_class_module(class_name)
        if module_name:
            # 生成完整类路径: "module_name.ClassName"
            class_config[agent_id] = f"{module_name}.{class_name}"
        else:
            print(f"❌ 未找到类 {class_name} 对应的模块")
    
    if class_config:
        # 写入class_config.json文件
        config_path = "system_interface_agents/class_config.json"
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(class_config, f, indent=2, ensure_ascii=False)
        
        print(f"\n✅ 成功生成 {config_path}")
        print(f"📊 包含 {len(class_config)} 个Agent映射:")
        for agent_id, class_path in class_config.items():
            print(f"   {agent_id} -> {class_path}")
        return True
    else:
        print("❌ 未生成任何有效的类映射")
        return False

if __name__ == "__main__":
    generate_class_config()
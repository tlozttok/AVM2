"""
Agent创建和操作的实在界正确性验证
验证语义描述与实在界对象的一致性
"""

import asyncio
import time
from typing import Dict, Any, List
from .driver import Agent, AgentMessage, MessageBus
from .async_system import AgentSystem
from .system_agent_examples import AgentCreatorOutputAgent
from .system_agents import IOAgent


class RealityValidationTester:
    """
    实在界正确性验证器
    验证语义转换的实在界正确性
    """
    
    def __init__(self, agent_system: AgentSystem):
        self.agent_system = agent_system
        self.validation_results = []
    
    async def run_comprehensive_validation(self):
        """运行全面的实在界正确性验证"""
        print("🔍 开始实在界正确性验证...")
        print("=" * 60)
        
        # 验证阶段1: Agent创建语义转换
        await self._validate_agent_creation()
        
        # 验证阶段2: 连接语义转换
        await self._validate_connection_semantics()
        
        # 验证阶段3: 激活语义转换
        await self._validate_activation_semantics()
        
        # 验证阶段4: 系统查询语义转换
        await self._validate_system_query_semantics()
        
        # 验证阶段5: 表达能力等价性
        await self._validate_expressivity_equivalence()
        
        # 输出验证报告
        self._print_validation_report()
    
    async def _validate_agent_creation(self):
        """验证Agent创建语义转换的正确性"""
        print("\\n📋 验证阶段1: Agent创建语义转换")
        
        # 测试用例1: 基本Agent创建
        test_agent_semantic = '''
{
  "operation": "create_agent",
  "id": "validation_test_agent",
  "prompt": "这是一个验证测试Agent",
  "input_connections": {
    "agent_creator": "validation_input"
  },
  "output_connections": {
    "validation_output": ["system_monitor"]
  },
  "activation_channels": ["validation_input"]
}
'''
        
        # 获取AgentCreator
        agent_creator = self.agent_system.agents.get("agent_creator")
        if not agent_creator:
            print("  ❌ 验证失败: 未找到agent_creator")
            self.validation_results.append({
                "test": "Agent创建",
                "result": "失败",
                "reason": "缺少agent_creator"
            })
            return
        
        # 执行语义转换
        test_message = AgentMessage("validation", test_agent_semantic)
        success = await agent_creator.execute_action(test_message)
        
        # 验证实在界结果
        if success and "validation_test_agent" in self.agent_system.agents:
            created_agent = self.agent_system.agents["validation_test_agent"]
            
            # 验证属性
            checks = [
                (created_agent.id == "validation_test_agent", "Agent ID正确"),
                (created_agent.prompt == "这是一个验证测试Agent", "提示词正确"),
                ("agent_creator" in created_agent.input_connections.connections, "输入连接正确"),
                ("validation_output" in created_agent.output_connections.connections, "输出连接正确"),
                ("validation_input" in created_agent.input_message_keyword, "激活通道正确")
            ]
            
            all_passed = True
            for check_passed, description in checks:
                if check_passed:
                    print(f"    ✅ {description}")
                else:
                    print(f"    ❌ {description}")
                    all_passed = False
            
            if all_passed:
                print("  ✅ Agent创建语义转换验证通过")
                self.validation_results.append({
                    "test": "Agent创建语义转换",
                    "result": "通过",
                    "details": "所有属性正确转换"
                })
            else:
                print("  ❌ Agent创建语义转换验证失败")
                self.validation_results.append({
                    "test": "Agent创建语义转换", 
                    "result": "失败",
                    "reason": "属性转换不完整"
                })
        else:
            print("  ❌ Agent创建语义转换验证失败")
            self.validation_results.append({
                "test": "Agent创建语义转换",
                "result": "失败", 
                "reason": "Agent未正确创建"
            })
    
    async def _validate_connection_semantics(self):
        """验证连接语义转换的正确性"""
        print("\\n🔗 验证阶段2: 连接语义转换")
        
        # 创建测试Agent
        agent1 = Agent("connection_test_1", "连接测试Agent1", self.agent_system.message_bus)
        agent2 = Agent("connection_test_2", "连接测试Agent2", self.agent_system.message_bus)
        
        self.agent_system.register_agent(agent1)
        self.agent_system.register_agent(agent2)
        
        # 连接语义
        connection_semantic = '''
{
  "operation": "connect_agents",
  "connections": [
    {
      "from_id": "connection_test_1",
      "output_channel": "test_output",
      "to_id": "connection_test_2", 
      "input_channel": "test_input"
    }
  ]
}
'''
        
        agent_creator = self.agent_system.agents.get("agent_creator")
        test_message = AgentMessage("validation", connection_semantic)
        success = await agent_creator.execute_action(test_message)
        
        # 验证实在界连接
        if success:
            agent1 = self.agent_system.agents["connection_test_1"]
            agent2 = self.agent_system.agents["connection_test_2"]
            
            # 检查输出连接
            output_ok = ("test_output" in agent1.output_connections.connections and 
                        "connection_test_2" in agent1.output_connections.connections["test_output"])
            
            # 检查输入连接
            input_ok = ("connection_test_1" in agent2.input_connections.connections and
                       agent2.input_connections.connections["connection_test_1"] == "test_input")
            
            if output_ok and input_ok:
                print("  ✅ 连接语义转换验证通过")
                self.validation_results.append({
                    "test": "连接语义转换",
                    "result": "通过", 
                    "details": "双向连接正确建立"
                })
            else:
                print(f"  ❌ 连接语义转换验证失败: 输出={output_ok}, 输入={input_ok}")
                self.validation_results.append({
                    "test": "连接语义转换",
                    "result": "失败",
                    "reason": "连接建立不完整"
                })
        else:
            print("  ❌ 连接语义转换验证失败")
            self.validation_results.append({
                "test": "连接语义转换",
                "result": "失败",
                "reason": "连接操作执行失败"
            })
    
    async def _validate_activation_semantics(self):
        """验证激活语义转换的正确性"""
        print("\\n⚡ 验证阶段3: 激活语义转换")
        
        # 创建测试Agent
        test_agent = Agent("activation_test", "激活测试Agent", self.agent_system.message_bus)
        self.agent_system.register_agent(test_agent)
        
        # 激活语义
        activation_semantic = '''
{
  "operation": "set_activation",
  "agent_id": "activation_test",
  "activation_channels": ["channel_a", "channel_b", "channel_c"]
}
'''
        
        agent_creator = self.agent_system.agents.get("agent_creator")
        test_message = AgentMessage("validation", activation_semantic)
        success = await agent_creator.execute_action(test_message)
        
        # 验证实在界激活设置
        if success:
            test_agent = self.agent_system.agents["activation_test"]
            
            if (hasattr(test_agent, 'input_message_keyword') and
                test_agent.input_message_keyword == ["channel_a", "channel_b", "channel_c"]):
                print("  ✅ 激活语义转换验证通过")
                self.validation_results.append({
                    "test": "激活语义转换",
                    "result": "通过",
                    "details": "激活通道正确设置"
                })
            else:
                print(f"  ❌ 激活语义转换验证失败: 实际激活通道={test_agent.input_message_keyword}")
                self.validation_results.append({
                    "test": "激活语义转换",
                    "result": "失败", 
                    "reason": "激活通道设置不正确"
                })
        else:
            print("  ❌ 激活语义转换验证失败")
            self.validation_results.append({
                "test": "激活语义转换",
                "result": "失败",
                "reason": "激活设置操作失败"
            })
    
    async def _validate_system_query_semantics(self):
        """验证系统查询语义转换的正确性"""
        print("\\n🔍 验证阶段4: 系统查询语义转换")
        
        io_agent = self.agent_system.agents.get("agent_io")
        if not io_agent:
            print("  ❌ 验证失败: 未找到agent_io")
            self.validation_results.append({
                "test": "系统查询语义转换",
                "result": "失败",
                "reason": "缺少agent_io"
            })
            return
        
        # 测试查询语义
        query_semantic = "<system_metadata></system_metadata>"
        test_message = AgentMessage("validation", query_semantic)
        
        # 模拟查询处理
        response = await io_agent._process_query(query_semantic)
        
        if response and "system_metadata_result" in response:
            print("  ✅ 系统查询语义转换验证通过")
            self.validation_results.append({
                "test": "系统查询语义转换",
                "result": "通过",
                "details": "查询语义正确解析和处理"
            })
        else:
            print(f"  ❌ 系统查询语义转换验证失败: 响应={response}")
            self.validation_results.append({
                "test": "系统查询语义转换",
                "result": "失败",
                "reason": "查询处理失败"
            })
    
    async def _validate_expressivity_equivalence(self):
        """验证表达能力等价性"""
        print("\\n🎯 验证阶段5: 表达能力等价性")
        
        # 验证新创建的Agent具有与原Agent相同的表达能力
        original_agent = Agent("original_expressivity", "原始表达能力Agent", self.agent_system.message_bus)
        
        # 通过语义创建的新Agent
        new_agent_semantic = '''
{
  "operation": "create_agent",
  "id": "new_expressivity",
  "prompt": "新表达能力Agent",
  "input_connections": {},
  "output_connections": {},
  "activation_channels": []
}
'''
        
        agent_creator = self.agent_system.agents.get("agent_creator")
        test_message = AgentMessage("validation", new_agent_semantic)
        success = await agent_creator.execute_action(test_message)
        
        if success and "new_expressivity" in self.agent_system.agents:
            new_agent = self.agent_system.agents["new_expressivity"]
            
            # 比较表达能力关键属性
            expressivity_attributes = [
                ("消息接收能力", hasattr(original_agent, 'receive_message_async') == hasattr(new_agent, 'receive_message_async')),
                ("消息发送能力", hasattr(original_agent, 'send_message_async') == hasattr(new_agent, 'send_message_async')),
                ("激活机制", hasattr(original_agent, 'activate_async') == hasattr(new_agent, 'activate_async')),
                ("连接管理", hasattr(original_agent, 'input_connections') == hasattr(new_agent, 'input_connections')),
                ("消息缓存", hasattr(original_agent, 'input_message_cache') == hasattr(new_agent, 'input_message_cache'))
            ]
            
            all_equivalent = True
            for attribute, equivalent in expressivity_attributes:
                if equivalent:
                    print(f"    ✅ {attribute}: 等价")
                else:
                    print(f"    ❌ {attribute}: 不等价")
                    all_equivalent = False
            
            if all_equivalent:
                print("  ✅ 表达能力等价性验证通过")
                self.validation_results.append({
                    "test": "表达能力等价性",
                    "result": "通过",
                    "details": "新Agent具有与原Agent相同的表达能力"
                })
            else:
                print("  ❌ 表达能力等价性验证失败")
                self.validation_results.append({
                    "test": "表达能力等价性",
                    "result": "失败",
                    "reason": "表达能力属性不等价"
                })
        else:
            print("  ❌ 表达能力等价性验证失败")
            self.validation_results.append({
                "test": "表达能力等价性",
                "result": "失败",
                "reason": "新Agent创建失败"
            })
    
    def _print_validation_report(self):
        """打印验证报告"""
        print("\\n" + "=" * 60)
        print("📊 实在界正确性验证报告")
        print("=" * 60)
        
        passed_tests = [r for r in self.validation_results if r["result"] == "通过"]
        failed_tests = [r for r in self.validation_results if r["result"] == "失败"]
        
        print(f"✅ 通过测试: {len(passed_tests)}/{len(self.validation_results)}")
        print(f"❌ 失败测试: {len(failed_tests)}/{len(self.validation_results)}")
        
        print("\\n详细结果:")
        for result in self.validation_results:
            status = "✅" if result["result"] == "通过" else "❌"
            print(f"  {status} {result['test']}")
            if "details" in result:
                print(f"     详情: {result['details']}")
            if "reason" in result:
                print(f"     原因: {result['reason']}")
        
        # 总体评估
        success_rate = len(passed_tests) / len(self.validation_results) if self.validation_results else 0
        if success_rate >= 0.8:
            overall = "优秀"
        elif success_rate >= 0.6:
            overall = "良好"
        else:
            overall = "需要改进"
        
        print(f"\\n📈 总体评估: {overall} (成功率: {success_rate:.1%})")


async def run_reality_validation():
    """运行实在界正确性验证"""
    # 创建测试系统
    system = AgentSystem()
    
    # 创建必要的系统Agent
    agent_creator = AgentCreatorOutputAgent("agent_creator", system, system.message_bus)
    io_agent = IOAgent("agent_io", system, "", system.message_bus)
    
    system.register_agent(agent_creator)
    system.register_agent(io_agent)
    
    # 启动系统
    await system.start()
    
    # 运行验证
    validator = RealityValidationTester(system)
    await validator.run_comprehensive_validation()

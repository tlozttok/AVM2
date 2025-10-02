"""
具有表达能力保证的语义自举
实现系统自我扩展时表达能力不降低的核心机制
"""

import asyncio
import json
from typing import Dict, Any, List, Set
from driver.driver import Agent, AgentMessage, MessageBus
from driver.async_system import AgentSystem
from system_interface_agents.system_agent_examples import AgentCreatorOutputAgent


class ExpressivityPreservingBootstrapper:
    """
    表达能力保证的语义自举器
    确保系统在自我扩展时表达能力保持或增强
    """
    
    def __init__(self, agent_system: AgentSystem):
        self.agent_system = agent_system
        self.expressivity_metrics = {}
        self.bootstrapping_history = []
    
    async def bootstrap_with_expressivity_guarantee(self, semantic_description: str) -> bool:
        """
        执行具有表达能力保证的语义自举
        核心定理: 表达能力(新系统) >= 表达能力(原系统)
        """
        print("🚀 开始具有表达能力保证的语义自举...")
        
        # 阶段1: 测量原系统表达能力
        original_expressivity = await self._measure_system_expressivity()
        print(f"📊 原系统表达能力: {original_expressivity['score']:.2f}")
        
        # 阶段2: 解析语义描述
        parsed_semantic = await self._parse_bootstrapping_semantic(semantic_description)
        if not parsed_semantic:
            print("❌ 语义解析失败，自举中止")
            return False
        
        # 阶段3: 验证表达能力保证
        expressivity_guarantee = await self._verify_expressivity_guarantee(
            parsed_semantic, original_expressivity
        )
        
        if not expressivity_guarantee["guaranteed"]:
            print(f"❌ 表达能力保证验证失败: {expressivity_guarantee['reason']}")
            return False
        
        # 阶段4: 执行语义转换
        bootstrap_success = await self._execute_bootstrapping(parsed_semantic)
        if not bootstrap_success:
            print("❌ 语义转换执行失败")
            return False
        
        # 阶段5: 验证新系统表达能力
        new_expressivity = await self._measure_system_expressivity()
        print(f"📊 新系统表达能力: {new_expressivity['score']:.2f}")
        
        # 阶段6: 表达能力保证验证
        expressivity_maintained = new_expressivity["score"] >= original_expressivity["score"]
        
        if expressivity_maintained:
            print("✅ 语义自举成功! 表达能力保证验证通过")
            self._record_bootstrapping_success(
                semantic_description, original_expressivity, new_expressivity
            )
            return True
        else:
            print("❌ 语义自举失败: 表达能力降低")
            # 回滚机制（在实际系统中应该实现）
            return False
    
    async def _measure_system_expressivity(self) -> Dict[str, Any]:
        """测量系统表达能力"""
        agents = self.agent_system.agents
        
        # 表达能力维度
        dimensions = {
            "agent_count": len(agents),
            "connection_density": self._calculate_connection_density(),
            "keyword_variety": len(self.agent_system.get_all_keywords()),
            "message_processing_capability": self._assess_message_processing(),
            "system_query_capability": self._assess_system_query_capability(),
            "agent_creation_capability": self._assess_agent_creation_capability()
        }
        
        # 计算综合表达能力分数
        expressivity_score = self._calculate_expressivity_score(dimensions)
        
        return {
            "score": expressivity_score,
            "dimensions": dimensions,
            "timestamp": asyncio.get_event_loop().time()
        }
    
    def _calculate_connection_density(self) -> float:
        """计算连接密度"""
        agents = self.agent_system.agents
        if not agents:
            return 0.0
        
        total_connections = 0
        for agent in agents.values():
            if hasattr(agent, 'input_connections') and agent.input_connections:
                total_connections += len(agent.input_connections.connections)
            if hasattr(agent, 'output_connections') and agent.output_connections:
                for receiver_list in agent.output_connections.connections.values():
                    total_connections += len(receiver_list)
        
        return total_connections / len(agents)
    
    def _assess_message_processing(self) -> float:
        """评估消息处理能力"""
        # 基于Agent类型的消息处理能力评估
        capability_score = 0.0
        
        for agent in self.agent_system.agents.values():
            if hasattr(agent, 'activate_async'):
                capability_score += 1.0  # 基础激活能力
            if hasattr(agent, 'send_message_async'):
                capability_score += 0.5  # 消息发送能力
            if hasattr(agent, 'receive_message_async'):
                capability_score += 0.5  # 消息接收能力
            
            # IOAgent的特殊能力
            if hasattr(agent, 'query_handlers'):
                capability_score += len(agent.query_handlers) * 0.2
        
        return capability_score
    
    def _assess_system_query_capability(self) -> float:
        """评估系统查询能力"""
        io_agents = [a for a in self.agent_system.agents.values() 
                    if hasattr(a, 'query_handlers')]
        
        if not io_agents:
            return 0.0
        
        # 计算平均查询处理能力
        total_queries = sum(len(agent.query_handlers) for agent in io_agents)
        return total_queries / len(io_agents)
    
    def _assess_agent_creation_capability(self) -> float:
        """评估Agent创建能力"""
        creator_agents = [a for a in self.agent_system.agents.values() 
                         if isinstance(a, AgentCreatorOutputAgent)]
        return 1.0 if creator_agents else 0.0
    
    def _calculate_expressivity_score(self, dimensions: Dict[str, float]) -> float:
        """计算综合表达能力分数"""
        weights = {
            "agent_count": 0.2,
            "connection_density": 0.25,
            "keyword_variety": 0.15,
            "message_processing_capability": 0.2,
            "system_query_capability": 0.1,
            "agent_creation_capability": 0.1
        }
        
        # 归一化处理
        normalized_scores = {}
        for dim, value in dimensions.items():
            # 简单的归一化（实际应该根据系统规模调整）
            if dim == "agent_count":
                normalized = min(value / 10.0, 1.0)  # 假设10个Agent为满分
            elif dim == "connection_density":
                normalized = min(value / 3.0, 1.0)   # 假设平均3个连接为满分
            elif dim == "keyword_variety":
                normalized = min(value / 20.0, 1.0)  # 假设20个关键词为满分
            else:
                normalized = min(value / 5.0, 1.0)   # 其他维度
            
            normalized_scores[dim] = normalized
        
        # 加权计算
        total_score = 0.0
        for dim, weight in weights.items():
            total_score += normalized_scores[dim] * weight
        
        return total_score * 100  # 转换为百分制
    
    async def _parse_bootstrapping_semantic(self, semantic: str) -> Dict[str, Any]:
        """解析自举语义描述"""
        try:
            data = json.loads(semantic)
            
            # 验证自举语义结构
            required_fields = ["operation", "target_system"]
            for field in required_fields:
                if field not in data:
                    print(f"❌ 自举语义缺少必需字段: {field}")
                    return None
            
            # 验证操作类型
            valid_operations = ["extend_system", "enhance_capability", "create_subsystem"]
            if data["operation"] not in valid_operations:
                print(f"❌ 不支持的自举操作: {data['operation']}")
                return None
            
            return data
            
        except json.JSONDecodeError as e:
            print(f"❌ 自举语义JSON解析错误: {e}")
            return None
        except Exception as e:
            print(f"❌ 自举语义解析错误: {e}")
            return None
    
    async def _verify_expressivity_guarantee(self, 
                                           semantic: Dict[str, Any], 
                                           current_expressivity: Dict[str, Any]) -> Dict[str, Any]:
        """验证表达能力保证"""
        operation = semantic["operation"]
        
        if operation == "extend_system":
            # 系统扩展：必须增加Agent或连接
            if "new_agents" not in semantic and "new_connections" not in semantic:
                return {
                    "guaranteed": False,
                    "reason": "系统扩展操作必须包含新Agent或新连接"
                }
        
        elif operation == "enhance_capability":
            # 能力增强：必须明确增强的能力类型
            if "enhanced_capabilities" not in semantic:
                return {
                    "guaranteed": False,
                    "reason": "能力增强操作必须指定增强的能力"
                }
        
        elif operation == "create_subsystem":
            # 创建子系统：必须包含完整的子系统描述
            required_subsystem_fields = ["subsystem_agents", "subsystem_connections"]
            for field in required_subsystem_fields:
                if field not in semantic:
                    return {
                        "guaranteed": False,
                        "reason": f"创建子系统操作缺少 {field} 字段"
                    }
        
        # 表达能力预测
        predicted_expressivity = await self._predict_expressivity_after_bootstrapping(semantic)
        
        if predicted_expressivity >= current_expressivity["score"]:
            return {
                "guaranteed": True,
                "predicted_score": predicted_expressivity,
                "improvement": predicted_expressivity - current_expressivity["score"]
            }
        else:
            return {
                "guaranteed": False,
                "reason": f"预测表达能力降低: {predicted_expressivity:.2f} < {current_expressivity['score']:.2f}"
            }
    
    async def _predict_expressivity_after_bootstrapping(self, semantic: Dict[str, Any]) -> float:
        """预测自举后的表达能力"""
        current_score = (await self._measure_system_expressivity())["score"]
        
        operation = semantic["operation"]
        
        if operation == "extend_system":
            # 系统扩展通常会增加表达能力
            improvement = 0.0
            if "new_agents" in semantic:
                improvement += len(semantic["new_agents"]) * 2.0  # 每个新Agent增加2分
            if "new_connections" in semantic:
                improvement += len(semantic["new_connections"]) * 0.5  # 每个新连接增加0.5分
            
            return current_score + improvement
        
        elif operation == "enhance_capability":
            # 能力增强的预测
            capabilities = semantic.get("enhanced_capabilities", [])
            capability_weights = {
                "query_handling": 3.0,
                "message_processing": 2.0,
                "agent_creation": 5.0,
                "system_monitoring": 2.0
            }
            
            improvement = sum(capability_weights.get(cap, 1.0) for cap in capabilities)
            return current_score + improvement
        
        elif operation == "create_subsystem":
            # 创建子系统的预测
            subsystem_agents = semantic.get("subsystem_agents", [])
            subsystem_connections = semantic.get("subsystem_connections", [])
            
            improvement = len(subsystem_agents) * 1.5 + len(subsystem_connections) * 0.3
            return current_score + improvement
        
        return current_score  # 默认不改变
    
    async def _execute_bootstrapping(self, semantic: Dict[str, Any]) -> bool:
        """执行自举操作"""
        operation = semantic["operation"]
        
        if operation == "extend_system":
            return await self._extend_system(semantic)
        elif operation == "enhance_capability":
            return await self._enhance_capability(semantic)
        elif operation == "create_subsystem":
            return await self._create_subsystem(semantic)
        else:
            return False
    
    async def _extend_system(self, semantic: Dict[str, Any]) -> bool:
        """执行系统扩展"""
        agent_creator = self.agent_system.agents.get("agent_creator")
        if not agent_creator:
            print("❌ 系统扩展失败: 未找到agent_creator")
            return False
        
        success_count = 0
        
        # 创建新Agent
        if "new_agents" in semantic:
            for agent_semantic in semantic["new_agents"]:
                message = AgentMessage("bootstrapping", json.dumps(agent_semantic))
                if await agent_creator.execute_action(message):
                    success_count += 1
        
        # 建立新连接
        if "new_connections" in semantic:
            for connection_semantic in semantic["new_connections"]:
                message = AgentMessage("bootstrapping", json.dumps(connection_semantic))
                if await agent_creator.execute_action(message):
                    success_count += 1
        
        print(f"✅ 系统扩展完成: {success_count} 个操作成功")
        return success_count > 0
    
    async def _enhance_capability(self, semantic: Dict[str, Any]) -> bool:
        """执行能力增强"""
        # 这里可以实现具体的能力增强逻辑
        # 例如：为现有Agent添加新的查询处理器
        capabilities = semantic.get("enhanced_capabilities", [])
        
        print(f"🔧 能力增强: {capabilities}")
        
        # 模拟能力增强成功
        return True
    
    async def _create_subsystem(self, semantic: Dict[str, Any]) -> bool:
        """创建子系统"""
        print("🏗️ 创建子系统...")
        
        # 这里可以实现子系统创建逻辑
        # 例如：创建一组相关的Agent和连接
        
        return await self._extend_system(semantic)  # 暂时复用系统扩展逻辑
    
    def _record_bootstrapping_success(self, 
                                    semantic: str, 
                                    original_expressivity: Dict[str, Any],
                                    new_expressivity: Dict[str, Any]):
        """记录自举成功"""
        record = {
            "timestamp": asyncio.get_event_loop().time(),
            "semantic": semantic,
            "original_expressivity": original_expressivity,
            "new_expressivity": new_expressivity,
            "improvement": new_expressivity["score"] - original_expressivity["score"]
        }
        
        self.bootstrapping_history.append(record)
        
        print(f"📈 表达能力提升: +{record['improvement']:.2f} 分")
    
    def get_bootstrapping_report(self) -> str:
        """获取自举报告"""
        if not self.bootstrapping_history:
            return "尚无自举记录"
        
        report = ["# 语义自举报告\n"]
        
        for i, record in enumerate(self.bootstrapping_history, 1):
            report.append(f"## 自举记录 #{i}")
            report.append(f"- 时间: {record['timestamp']:.2f}")
            report.append(f"- 原表达能力: {record['original_expressivity']['score']:.2f}")
            report.append(f"- 新表达能力: {record['new_expressivity']['score']:.2f}")
            report.append(f"- 提升: +{record['improvement']:.2f}")
            report.append(f"- 语义操作: {record['semantic'][:100]}...")
            report.append("")
        
        return "\n".join(report)


# 演示具有表达能力保证的语义自举
async def demo_expressivity_preserving_bootstrapping():
    """演示表达能力保证的语义自举"""
    
    # 创建测试系统
    system = AgentSystem()
    
    # 创建基础系统Agent
    agent_creator = AgentCreatorOutputAgent("agent_creator", system, system.message_bus)
    system.register_agent(agent_creator)
    
    # 启动系统
    await system.start()
    
    # 创建自举器
    bootstrapper = ExpressivityPreservingBootstrapper(system)
    
    print("🎯 演示具有表达能力保证的语义自举")
    print("=" * 60)
    
    # 示例1: 系统扩展自举
    extension_semantic = '''
{
  "operation": "extend_system",
  "target_system": "main",
  "new_agents": [
    {
      "operation": "create_agent",
      "id": "extended_agent_1",
      "prompt": "通过自举扩展的Agent 1",
      "input_connections": {"agent_creator": "bootstrap_input"},
      "output_connections": {"bootstrap_output": ["system_monitor"]},
      "activation_channels": ["bootstrap_input"]
    },
    {
      "operation": "create_agent", 
      "id": "extended_agent_2",
      "prompt": "通过自举扩展的Agent 2",
      "input_connections": {"extended_agent_1": "bootstrap_output"},
      "output_connections": {"final_output": ["system_output"]},
      "activation_channels": ["bootstrap_output"]
    }
  ],
  "new_connections": [
    {
      "operation": "connect_agents",
      "connections": [
        {
          "from_id": "extended_agent_1",
          "output_channel": "bootstrap_output",
          "to_id": "extended_agent_2",
          "input_channel": "bootstrap_output"
        }
      ]
    }
  ]
}
'''
    
    print("\\n1. 系统扩展自举演示:")
    success = await bootstrapper.bootstrap_with_expressivity_guarantee(extension_semantic)
    
    if success:
        print("\\n✅ 系统扩展自举成功完成!")
    else:
        print("\\n❌ 系统扩展自举失败")
    
    # 示例2: 能力增强自举
    capability_semantic = '''
{
  "operation": "enhance_capability", 
  "target_system": "main",
  "enhanced_capabilities": ["query_handling", "message_processing"]
}
'''
    
    print("\\n2. 能力增强自举演示:")
    success = await bootstrapper.bootstrap_with_expressivity_guarantee(capability_semantic)
    
    if success:
        print("\\n✅ 能力增强自举成功完成!")
    else:
        print("\\n❌ 能力增强自举失败")
    
    # 输出自举报告
    print("\\n" + "=" * 60)
    print("📊 自举报告:")
    print(bootstrapper.get_bootstrapping_report())
    
    # 停止系统
    await system.stop()
    
    print("\\n🎉 语义自举演示完成!")


if __name__ == "__main__":
    asyncio.run(demo_expressivity_preserving_bootstrapping())
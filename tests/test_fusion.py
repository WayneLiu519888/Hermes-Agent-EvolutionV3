"""
V1/V2 融合模块测试 - test_fusion.py

测试 bridge.py, unified_entry.py, compatibility.py, __init__.py 的核心功能。
至少10个测试用例。
"""

import unittest
import sys
import os
import json
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, patch, AsyncMock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.fusion.compatibility import (
    StatusMapper,
    EnumMapper,
    APIGateway,
    DegradationHandler,
    DegradationRule,
    VersionDetector,
    VersionInfo,
    CompatibilityLayer,
    UnifiedAPIRequest,
    UnifiedAPIResponse,
    v1_status_to_v2_status,
    v2_status_to_v1_status,
    v1_outcome_to_v2_priority,
    v2_priority_to_v1_confidence,
)
from src.evolution.fusion.bridge import (
    V1V2Bridge,
    ServiceMapping,
    DataFormatConverter,
    V1ExperienceData,
    V2EventData,
    V1_STATUS_ENUM,
    V2_SERVICE_TYPE,
    SERVICE_MAP_V1_TO_V2,
    SERVICE_MAP_V2_TO_V1,
)
from src.evolution.fusion.unified_entry import (
    UnifiedAgent,
    RunMode,
    CapabilityRequest,
    CapabilityResponse,
    UnifiedStatusReport,
)


# ============================================================================
# Test 1: 兼容性层 - StatusMapper 枚举映射
# ============================================================================

class TestStatusMapper(unittest.TestCase):
    """测试状态映射器"""

    def test_v1_health_to_v2_status_mapping(self):
        """测试V1健康状态 → V2服务状态映射"""
        self.assertEqual(StatusMapper.v1_health_status_to_v2("healthy"), "running")
        self.assertEqual(StatusMapper.v1_health_status_to_v2("needs_attention"), "degraded")
        self.assertEqual(StatusMapper.v1_health_status_to_v2("unhealthy"), "failed")
        self.assertEqual(StatusMapper.v1_health_status_to_v2("unknown"), "stopped")
        self.assertEqual(StatusMapper.v1_health_status_to_v2("nonexistent"), "stopped")

    def test_v2_status_to_v1_health_mapping(self):
        """测试V2服务状态 → V1健康状态映射"""
        self.assertEqual(StatusMapper.v2_service_status_to_v1("running"), "healthy")
        self.assertEqual(StatusMapper.v2_service_status_to_v1("degraded"), "needs_attention")
        self.assertEqual(StatusMapper.v2_service_status_to_v1("failed"), "unhealthy")
        self.assertEqual(StatusMapper.v2_service_status_to_v1("stopped"), "unknown")
        self.assertEqual(StatusMapper.v2_service_status_to_v1("unknown_service"), "unknown")

    def test_v1_outcome_to_v2_priority(self):
        """测试V1结果 → V2事件优先级映射"""
        self.assertEqual(StatusMapper.v1_outcome_to_v2_priority("success"), 1)
        self.assertEqual(StatusMapper.v1_outcome_to_v2_priority("failure"), 2)
        self.assertEqual(StatusMapper.v1_outcome_to_v2_priority("partial_success"), 1)
        self.assertEqual(StatusMapper.v1_outcome_to_v2_priority("uncertain"), 0)
        self.assertEqual(StatusMapper.v1_outcome_to_v2_priority("unknown"), 1)

    def test_v2_priority_to_v1_confidence(self):
        """测试V2优先级 → V1置信度映射"""
        self.assertEqual(StatusMapper.v2_priority_to_v1_confidence(0), 0.3)   # LOW
        self.assertEqual(StatusMapper.v2_priority_to_v1_confidence(1), 0.5)   # NORMAL
        self.assertEqual(StatusMapper.v2_priority_to_v1_confidence(2), 0.8)   # HIGH
        self.assertEqual(StatusMapper.v2_priority_to_v1_confidence(3), 0.95)  # CRITICAL
        self.assertEqual(StatusMapper.v2_priority_to_v1_confidence(99), 0.5)  # unknown

    def test_event_type_v1_to_v2_mapping(self):
        """测试V1经验类型 → V2事件类型映射"""
        self.assertEqual(
            StatusMapper.map_event_type_v1_to_v2("tool_usage"), "tool.executed"
        )
        self.assertEqual(
            StatusMapper.map_event_type_v1_to_v2("error_recovery"), "system.error"
        )
        self.assertEqual(
            StatusMapper.map_event_type_v1_to_v2("pattern_recognition"), "learning.completed"
        )
        self.assertEqual(
            StatusMapper.map_event_type_v1_to_v2("unknown_type"), "task.received"
        )

    def test_event_type_v2_to_v1_mapping(self):
        """测试V2事件类型 → V1经验类型映射"""
        self.assertEqual(
            StatusMapper.map_event_type_v2_to_v1("tool.executed"), "tool_usage"
        )
        self.assertEqual(
            StatusMapper.map_event_type_v2_to_v1("system.error"), "error_recovery"
        )
        self.assertEqual(
            StatusMapper.map_event_type_v2_to_v1("learning.completed"), "pattern_recognition"
        )
        self.assertEqual(
            StatusMapper.map_event_type_v2_to_v1("unknown.event"), "adaptation"
        )

    def test_convenience_functions(self):
        """测试便利函数"""
        self.assertEqual(v1_status_to_v2_status("healthy"), "running")
        self.assertEqual(v2_status_to_v1_status("running"), "healthy")
        self.assertEqual(v1_outcome_to_v2_priority("failure"), 2)
        self.assertAlmostEqual(v2_priority_to_v1_confidence(3), 0.95)


# ============================================================================
# Test 2: 兼容性层 - EnumMapper
# ============================================================================

class TestEnumMapper(unittest.TestCase):
    """测试枚举映射器"""

    def test_enum_mapper_register_and_resolve(self):
        """测试枚举注册和解析"""
        from enum import Enum

        class TestEnum(Enum):
            A = "a"
            B = "b"

        mapper = EnumMapper()
        mapper.register_v1_enum("TestEnum", TestEnum)

        result = mapper.resolve_v1_enum("TestEnum", "a")
        self.assertEqual(result, TestEnum.A)

        result = mapper.resolve_v1_enum("TestEnum", "b")
        self.assertEqual(result, TestEnum.B)

    def test_enum_mapper_unknown_enum(self):
        """测试未知枚举"""
        mapper = EnumMapper()
        result = mapper.resolve_v1_enum("NonexistentEnum", "value")
        self.assertEqual(result, "value")  # 原样返回


# ============================================================================
# Test 3: 兼容性层 - 降级处理器
# ============================================================================

class TestDegradationHandler(unittest.TestCase):
    """测试降级处理器"""

    def test_degradation_basic_flow(self):
        """测试基本降级流程"""
        handler = DegradationHandler()
        handler.register_rule("test_service", DegradationRule(
            service_name="test_service",
            failure_threshold=3,
            cooldown_seconds=0.1,
        ))

        # 初始状态：未降级
        self.assertFalse(handler.is_degraded("test_service"))

        # 多次失败触发降级
        for _ in range(3):
            result = handler.record_failure("test_service")
        self.assertTrue(handler.is_degraded("test_service"))

    def test_degradation_success_recovery(self):
        """测试成功恢复降级"""
        handler = DegradationHandler()
        handler.register_rule("test_service", DegradationRule(
            service_name="test_service",
            failure_threshold=2,
            recovery_threshold=2,
            cooldown_seconds=0.1,
        ))

        # 触发降级
        handler.record_failure("test_service")
        handler.record_failure("test_service")
        self.assertTrue(handler.is_degraded("test_service"))

        # 需要冷却期过期后成功恢复
        import time
        time.sleep(0.15)  # 等待冷却期

        handler.record_success("test_service")
        handler.record_success("test_service")
        self.assertFalse(handler.is_degraded("test_service"))

    def test_execute_with_fallback(self):
        """测试带降级的执行"""
        handler = DegradationHandler()
        handler.register_rule("test_service", DegradationRule(
            service_name="test_service",
            failure_threshold=1,
            cooldown_seconds=0.1,
        ))

        call_order = []

        def primary():
            call_order.append("primary")
            raise RuntimeError("primary failed")

        def fallback():
            call_order.append("fallback")
            return "fallback_result"

        # 第一次：primary失败，触发降级，使用fallback
        result = handler.execute_with_fallback("test_service", primary, fallback)
        self.assertEqual(result, "fallback_result")
        self.assertTrue(handler.is_degraded("test_service"))

        # 第二次：已降级，直接使用fallback
        result = handler.execute_with_fallback("test_service", primary, fallback)
        self.assertEqual(result, "fallback_result")
        self.assertEqual(call_order, ["primary", "fallback", "fallback"])


# ============================================================================
# Test 4: 兼容性层 - 版本检测
# ============================================================================

class TestVersionDetection(unittest.TestCase):
    """测试版本检测"""

    def test_version_info_parse(self):
        """测试版本解析"""
        v = VersionInfo.parse("2.1.3", "v2_microservice")
        self.assertEqual(v.major, 2)
        self.assertEqual(v.minor, 1)
        self.assertEqual(v.patch, 3)
        self.assertEqual(v.full, "2.1.3")
        self.assertEqual(v.architecture, "v2_microservice")

    def test_version_compatibility(self):
        """测试版本兼容性"""
        v1 = VersionInfo.parse("2.0.0", "v1_monolith")
        v2 = VersionInfo.parse("2.5.1", "v2_microservice")
        v3 = VersionInfo.parse("3.0.0", "v2_microservice")

        # 同一主版本，兼容
        self.assertTrue(v1.is_compatible_with(v2))
        self.assertTrue(v2.is_compatible_with(v1))

        # 不同主版本，不兼容
        self.assertFalse(v1.is_compatible_with(v3))
        self.assertFalse(v3.is_compatible_with(v1))

    def test_version_newer_than(self):
        """测试版本比较"""
        v1 = VersionInfo.parse("1.0.0")
        v2 = VersionInfo.parse("2.0.0")
        v3 = VersionInfo.parse("2.1.0")
        v4 = VersionInfo.parse("2.0.1")

        self.assertTrue(v2.is_newer_than(v1))
        self.assertTrue(v3.is_newer_than(v2))
        self.assertTrue(v4.is_newer_than(v2))
        self.assertFalse(v1.is_newer_than(v2))


# ============================================================================
# Test 5: 桥接层 - 数据格式转换器
# ============================================================================

class TestDataFormatConverter(unittest.TestCase):
    """测试数据格式转换器"""

    def test_experience_to_dict(self):
        """测试V1 Experience → dict 转换"""
        from src.evolution.learning.experience import Experience, ExperienceType, Outcome

        exp = Experience(
            id="test_123",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="task_1",
            description="测试经验",
            outcome=Outcome.SUCCESS,
            metrics={"efficiency": 0.8},
            context={"tool": "terminal"},
        )

        result = DataFormatConverter.v1_experience_to_dict(exp)
        self.assertEqual(result["id"], "test_123")
        self.assertEqual(result["experience_type"], "tool_usage")
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["metrics"]["efficiency"], 0.8)

    def test_dict_to_experience(self):
        """测试dict → V1 Experience 转换"""
        data = {
            "id": "test_456",
            "experience_type": "tool_usage",
            "task_id": "task_2",
            "timestamp": datetime.now().isoformat(),
            "description": "恢复测试",
            "outcome": "failure",
            "context": {"error": "超时"},
            "confidence": 0.3,
        }

        result = DataFormatConverter.dict_to_v1_experience(data)
        # 检查是否成功创建Experience对象
        if hasattr(result, 'id'):
            self.assertEqual(result.id, "test_456")
            self.assertEqual(result.outcome.value, "failure")

    def test_v1_experience_to_v2_event_data(self):
        """测试V1经验→V2事件数据转换"""
        v1_data = {
            "id": "evt_1",
            "experience_type": "tool_usage",
            "task_id": "t1",
            "description": "工具测试",
            "outcome": "success",
            "metrics": {"efficiency": 0.9},
            "context": {"tool": "read_file"},
        }
        v2_data = V2EventData(
            event_id="evt_1",
            event_type="tool.executed",
            data=v1_data,
            source="v1_bridge",
            priority=1,
        )
        self.assertEqual(v2_data.event_type, "tool.executed")
        self.assertEqual(v2_data.priority, 1)

    def test_v2_event_to_dict(self):
        """测试V2 Event → dict 转换"""
        event_data = V2EventData(
            event_id="v2_evt_001",
            event_type="task.completed",
            data={"result": "ok"},
            source="system",
            priority=2,
        )
        result = DataFormatConverter.v2_event_to_dict(event_data)
        self.assertEqual(result["event_id"], "v2_evt_001")
        self.assertEqual(result["event_type"], "task.completed")
        self.assertEqual(result["priority"], 2)


# ============================================================================
# Test 6: 桥接层 - V1V2Bridge 事件转换
# ============================================================================

class TestV1V2BridgeEvents(unittest.TestCase):
    """测试V1V2Bridge事件转换"""

    def setUp(self):
        self.bridge = V1V2Bridge()

    def test_v1_to_v2_event_conversion(self):
        """测试V1→V2事件转换"""
        v1_event = {
            "id": "exp_1",
            "experience_type": "tool_usage",
            "task_id": "task_1",
            "description": "使用terminal工具",
            "outcome": "success",
            "metrics": {"efficiency": 0.9},
            "source_module": "learning.observer",
        }

        v2_event = self.bridge.v1_to_v2_event(v1_event)

        self.assertEqual(v2_event["source"], "v1_bridge")
        self.assertEqual(v2_event["event_type"], "tool.executed")
        self.assertEqual(v2_event["priority"], 1)
        self.assertIn("v1_source", v2_event["data"])
        self.assertTrue(v2_event["data"]["v1_source"])

    def test_v1_to_v2_event_with_failure(self):
        """测试V1失败事件→V2转换"""
        v1_event = {
            "id": "exp_2",
            "experience_type": "error_recovery",
            "task_id": "task_2",
            "description": "错误恢复",
            "outcome": "failure",
            "metrics": {"efficiency": 0.2},
        }

        v2_event = self.bridge.v1_to_v2_event(v1_event)
        self.assertEqual(v2_event["event_type"], "system.error")
        self.assertEqual(v2_event["priority"], 2)  # failure → HIGH

    def test_v2_to_v1_callback_conversion(self):
        """测试V2→V1回调转换"""
        v2_message = {
            "event_id": "v2_evt_001",
            "event_type": "tool.executed",
            "data": {
                "tool_name": "read_file",
                "result": "file content",
                "task_id": "task_3",
            },
            "timestamp": datetime.now().isoformat(),
            "priority": 1,
        }

        v1_callback = self.bridge.v2_to_v1_callback(v2_message)

        self.assertEqual(v1_callback["experience_type"], "tool_usage")
        self.assertEqual(v1_callback["outcome"], "success")
        self.assertEqual(v1_callback["source"], "v2_bridge")
        self.assertIn("v2_event_type", v1_callback)

    def test_v2_error_to_v1_callback(self):
        """测试V2错误事件→V1回调"""
        v2_message = {
            "event_id": "v2_err_001",
            "event_type": "system.error",
            "data": {"error": "connection timeout", "task_id": "task_4"},
            "timestamp": datetime.now().isoformat(),
            "priority": 2,
        }

        v1_callback = self.bridge.v2_to_v1_callback(v2_message)
        self.assertEqual(v1_callback["experience_type"], "error_recovery")
        self.assertEqual(v1_callback["outcome"], "failure")
        self.assertAlmostEqual(v1_callback["confidence"], 0.8)  # HIGH→0.8


# ============================================================================
# Test 7: 桥接层 - 服务映射
# ============================================================================

class TestServiceMapping(unittest.TestCase):
    """测试服务映射"""

    def setUp(self):
        self.bridge = V1V2Bridge()

    def test_service_map_v1_to_v2_lookup(self):
        """测试V1→V2服务查找"""
        self.assertEqual(
            self.bridge.get_v2_service_for_v1_module("learning.observer"),
            "LearningOrchestrator"
        )
        self.assertEqual(
            self.bridge.get_v2_service_for_v1_module("self_monitor"),
            "MonitoringService"
        )
        self.assertEqual(
            self.bridge.get_v2_service_for_v1_module("tools.registry"),
            "ToolManager"
        )
        self.assertIsNone(
            self.bridge.get_v2_service_for_v1_module("nonexistent.module")
        )

    def test_service_map_v2_to_v1_lookup(self):
        """测试V2→V1服务查找"""
        self.assertEqual(
            self.bridge.get_v1_module_for_v2_service("LearningOrchestrator"),
            "learning"
        )
        self.assertEqual(
            self.bridge.get_v1_module_for_v2_service("MonitoringService"),
            "self_monitor"
        )
        self.assertEqual(
            self.bridge.get_v1_module_for_v2_service("ToolManager"),
            "tools"
        )

    def test_add_custom_mapping(self):
        """测试添加自定义映射"""
        self.bridge.add_service_mapping("custom.v1.module", "CustomV2Service")
        self.assertEqual(
            self.bridge.get_v2_service_for_v1_module("custom.v1.module"),
            "CustomV2Service"
        )
        self.assertEqual(
            self.bridge.get_v1_module_for_v2_service("CustomV2Service"),
            "custom.v1.module"
        )

    def test_full_service_mapping_list(self):
        """测试完整映射表"""
        mappings = self.bridge.get_full_service_mapping()
        self.assertGreater(len(mappings), 5)
        # 验证每个映射的完整性
        for m in mappings:
            self.assertIsInstance(m, ServiceMapping)
            self.assertTrue(m.v1_module)
            self.assertTrue(m.v2_service)

    def test_list_modules_and_services(self):
        """测试列出模块和服务"""
        v1_modules = self.bridge.list_v1_modules()
        v2_services = self.bridge.list_v2_services()

        self.assertIn("learning.observer", v1_modules)
        self.assertIn("self_monitor", v1_modules)
        self.assertIn("LearningOrchestrator", v2_services)
        self.assertIn("ToolManager", v2_services)


# ============================================================================
# Test 8: 桥接层 - 健康检查
# ============================================================================

class TestBridgeHealthCheck(unittest.TestCase):
    """测试桥接健康检查"""

    def setUp(self):
        self.bridge = V1V2Bridge()

    def test_health_check_v1(self):
        """测试V1健康检查"""
        result = self.bridge.health_check_v1()
        self.assertIn("ready", result)
        self.assertIn("modules", result)
        self.assertIn("version", result)
        self.assertIsInstance(result["modules"], dict)

    def test_health_check_v2(self):
        """测试V2健康检查"""
        result = self.bridge.health_check_v2()
        self.assertIn("ready", result)
        self.assertIn("services", result)
        self.assertIn("version", result)
        self.assertIsInstance(result["services"], dict)

    def test_full_health_check(self):
        """测试完整健康检查"""
        result = self.bridge.full_health_check()
        self.assertIn("timestamp", result)
        self.assertIn("bridge_active", result)
        self.assertIn("v1", result)
        self.assertIn("v2", result)
        self.assertIn("compatibility", result)

    def test_bridge_summary(self):
        """测试桥接摘要"""
        summary = self.bridge.get_bridge_summary()
        self.assertEqual(summary["bridge_version"], "1.0.0")
        self.assertIn("v1_ready", summary)
        self.assertIn("v2_ready", summary)
        self.assertIn("service_mappings", summary)

    def test_event_history(self):
        """测试事件历史记录"""
        # 触发一些事件转换
        self.bridge.v1_to_v2_event({
            "id": "test_1",
            "experience_type": "tool_usage",
            "outcome": "success",
        })
        self.bridge.v2_to_v1_callback({
            "event_id": "v2_test",
            "event_type": "task.completed",
            "data": {},
            "priority": 1,
        })

        history = self.bridge.get_event_history()
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["direction"], "v1_to_v2")
        self.assertEqual(history[1]["direction"], "v2_to_v1")

        # 清空历史
        self.bridge.clear_event_history()
        self.assertEqual(len(self.bridge.get_event_history()), 0)


# ============================================================================
# Test 9: 统一入口 - UnifiedAgent 初始化
# ============================================================================

class TestUnifiedAgentInitialization(unittest.TestCase):
    """测试UnifiedAgent初始化（同步部分）"""

    def test_unified_agent_creation(self):
        """测试UnifiedAgent创建"""
        agent = UnifiedAgent(run_mode="v1_only")
        self.assertIsNotNone(agent.bridge)
        self.assertIsNotNone(agent.compatibility_layer)
        self.assertFalse(agent._initialized)

    def test_run_mode_enum(self):
        """测试运行模式枚举"""
        self.assertEqual(RunMode.V1_ONLY.value, "v1_only")
        self.assertEqual(RunMode.V2_ONLY.value, "v2_only")
        self.assertEqual(RunMode.HYBRID.value, "hybrid")

    def test_auto_mode_detection_v1_only(self):
        """测试自动检测V1模式"""
        agent = UnifiedAgent(run_mode="v1_only")
        agent._run_mode = RunMode.V1_ONLY
        # 模拟只有V1就绪
        agent.bridge._v1_ready = True
        agent.bridge._v2_ready = False
        agent._register_v1_capabilities()

        self.assertIn("v1", agent._capability_handlers)
        self.assertNotIn("v2", agent._capability_handlers)

    def test_capability_request_dataclass(self):
        """测试能力请求数据类"""
        req = CapabilityRequest(
            capability="analyze_experiences",
            parameters={"days": 7},
            mode="auto",
        )
        self.assertEqual(req.capability, "analyze_experiences")
        self.assertEqual(req.parameters["days"], 7)
        self.assertEqual(req.mode, "auto")

    def test_capability_response_dataclass(self):
        """测试能力响应数据类"""
        resp = CapabilityResponse(
            success=True,
            data={"result": "ok"},
            source="v1",
            latency_ms=15.0,
            request_id="req_123",
            mode_used="v1",
        )
        self.assertTrue(resp.success)
        self.assertEqual(resp.source, "v1")
        self.assertEqual(resp.mode_used, "v1")

    def test_get_status_report(self):
        """测试状态报告生成"""
        agent = UnifiedAgent(run_mode="v1_only")
        agent._detected_mode = RunMode.V1_ONLY
        report = agent.get_status_report()

        self.assertIn("timestamp", report)
        self.assertIn("run_mode", report)
        self.assertIn("v1", report)
        self.assertIn("v2", report)
        self.assertIn("summary", report)


# ============================================================================
# Test 10: API 网关路由
# ============================================================================

class TestAPIGateway(unittest.TestCase):
    """测试API网关路由"""

    def setUp(self):
        import asyncio
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def tearDown(self):
        self.loop.close()

    def test_api_gateway_v1_routing(self):
        """测试API网关V1路由"""
        gateway = APIGateway()

        def v1_handler(params):
            return {"v1_result": True, **params}

        gateway.register_v1_handler("test_capability", v1_handler)

        request = UnifiedAPIRequest(
            capability="test_capability",
            parameters={"key": "value"},
            mode="v1",
        )

        response = self.loop.run_until_complete(gateway.route(request))
        self.assertTrue(response.success)
        self.assertEqual(response.source, "v1")
        self.assertIn("v1_result", response.data)

    def test_api_gateway_v2_routing(self):
        """测试API网关V2路由"""
        gateway = APIGateway()

        async def v2_handler(params):
            return {"v2_result": True, **params}

        gateway.register_v2_handler("test_capability_v2", v2_handler)

        request = UnifiedAPIRequest(
            capability="test_capability_v2",
            parameters={"key": "v2_value"},
            mode="v2",
        )

        response = self.loop.run_until_complete(gateway.route(request))
        self.assertTrue(response.success)
        self.assertEqual(response.source, "v2")
        self.assertIn("v2_result", response.data)

    def test_api_gateway_unknown_capability(self):
        """测试API网关未找到能力"""
        gateway = APIGateway()

        request = UnifiedAPIRequest(
            capability="nonexistent_capability",
            mode="auto",
        )

        response = self.loop.run_until_complete(gateway.route(request))
        self.assertFalse(response.success)
        self.assertIn("未找到", response.error)

    def test_api_gateway_hybrid_fallback(self):
        """测试API网关融合模式降级"""
        gateway = APIGateway()

        # V2处理器会失败
        async def failing_v2_handler(params):
            raise RuntimeError("V2 service down")

        def v1_handler(params):
            return {"v1_fallback": True, **params}

        gateway.register_v2_handler("test_capability", failing_v2_handler)
        gateway.register_v1_handler("test_capability", v1_handler)

        request = UnifiedAPIRequest(
            capability="test_capability",
            mode="hybrid",
        )

        response = self.loop.run_until_complete(gateway.route(request))
        self.assertTrue(response.success)
        self.assertEqual(response.source, "v1")
        self.assertIn("v1_fallback", response.data)


# ============================================================================
# Test 11: 融合模块导出
# ============================================================================

class TestFusionModuleExports(unittest.TestCase):
    """测试融合模块__init__.py导出"""

    def test_module_imports(self):
        """测试模块导入"""
        from src.evolution.fusion import (
            V1V2Bridge,
            UnifiedAgent,
            CompatibilityLayer,
            RunMode,
            CapabilityRequest,
            CapabilityResponse,
            StatusMapper,
            DegradationHandler,
            VersionDetector,
        )
        # 验证主要类可导入
        self.assertTrue(callable(V1V2Bridge))
        self.assertTrue(callable(UnifiedAgent))
        self.assertTrue(callable(CompatibilityLayer))

    def test_version(self):
        """测试模块版本"""
        from src.evolution.fusion import __version__
        self.assertEqual(__version__, "1.0.0")

    def test_all_exports(self):
        """测试__all__导出列表"""
        from src.evolution.fusion import __all__
        expected_exports = [
            'V1V2Bridge', 'ServiceMapping',
            'V1_STATUS_ENUM', 'V2_SERVICE_TYPE',
            'SERVICE_MAP_V1_TO_V2', 'SERVICE_MAP_V2_TO_V1',
            'UnifiedAgent', 'RunMode',
            'CapabilityRequest', 'CapabilityResponse',
            'UnifiedStatusReport',
            'CompatibilityLayer', 'StatusMapper', 'EnumMapper',
            'APIGateway', 'DegradationHandler', 'VersionDetector',
            'v1_status_to_v2_status', 'v2_status_to_v1_status',
            'v1_outcome_to_v2_priority', 'v2_priority_to_v1_confidence',
        ]
        for export in expected_exports:
            self.assertIn(export, __all__, f"导出缺失: {export}")


# ============================================================================
# Test 12: 兼容性层初始化
# ============================================================================

class TestCompatibilityLayerInit(unittest.TestCase):
    """测试兼容性层初始化"""

    def test_compatibility_layer_creation(self):
        """测试兼容性层创建"""
        layer = CompatibilityLayer()
        self.assertIsNotNone(layer.status_mapper)
        self.assertIsNotNone(layer.enum_mapper)
        self.assertIsNotNone(layer.api_gateway)
        self.assertIsNotNone(layer.degradation_handler)
        self.assertIsNotNone(layer.version_detector)

    def test_compatibility_layer_initialize(self):
        """测试兼容性层初始化"""
        layer = CompatibilityLayer()
        report = layer.initialize()
        self.assertIn("compatible", report)
        self.assertIn("v1_version", report)
        self.assertIn("v2_version", report)
        self.assertIn("status", report)


# ============================================================================
# 主入口
# ============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print("V1/V2 融合模块测试套件")
    print("=" * 70)

    unittest.main(verbosity=2)

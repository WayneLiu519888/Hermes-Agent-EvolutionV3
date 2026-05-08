"""
统一入口 - UnifiedAgent 融合模式入口点

支持三种运行模式:
  - V1_ONLY: 仅使用V1单体模块
  - V2_ONLY: 仅使用V2微服务
  - HYBRID:  融合模式，V1和V2协同工作

UnifiedAgent 自动检测可用模块，初始化连接，执行能力请求，并生成统一状态报告。
"""

import sys
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid

from .bridge import V1V2Bridge, ServiceMapping
from .compatibility import (
    CompatibilityLayer,
    StatusMapper,
    APIGateway,
    UnifiedAPIRequest,
    UnifiedAPIResponse,
    DegradationHandler,
    DegradationRule,
    VersionDetector,
    VersionInfo,
)

logger = logging.getLogger(__name__)


class RunMode(Enum):
    """运行模式"""
    V1_ONLY = "v1_only"       # 仅V1单体模式
    V2_ONLY = "v2_only"       # 仅V2微服务模式
    HYBRID = "hybrid"          # V1+V2融合模式


@dataclass
class CapabilityRequest:
    """能力请求"""
    capability: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    mode: str = "auto"  # auto, v1, v2, hybrid
    timeout_seconds: float = 30.0
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CapabilityResponse:
    """能力响应"""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    source: str = "unknown"
    latency_ms: float = 0.0
    request_id: str = ""
    mode_used: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedStatusReport:
    """统一状态报告"""
    timestamp: str = ""
    run_mode: str = "unknown"
    bridge_active: bool = False
    v1_status: Dict[str, Any] = field(default_factory=dict)
    v2_status: Dict[str, Any] = field(default_factory=dict)
    compatibility: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    health_score: float = 0.0
    modules: Dict[str, str] = field(default_factory=dict)
    services: Dict[str, str] = field(default_factory=dict)
    summary: str = ""


class UnifiedAgent:
    """
    统一代理 - V1/V2融合入口点

    自动检测可用的V1和V2模块，初始化连接，并智能路由请求。
    """

    def __init__(self, run_mode: Union[str, RunMode] = "auto"):
        """
        初始化统一代理

        Args:
            run_mode: 运行模式 - "auto", "v1_only", "v2_only", "hybrid"
        """
        if isinstance(run_mode, str):
            try:
                self._run_mode = RunMode(run_mode)
            except ValueError:
                if run_mode == "auto":
                    self._run_mode = None  # 稍后自动检测
                else:
                    self._run_mode = RunMode.HYBRID
        else:
            self._run_mode = run_mode

        # 核心组件
        self.bridge = V1V2Bridge()
        self.compatibility_layer = CompatibilityLayer()
        self.api_gateway = self.compatibility_layer.api_gateway
        self.degradation_handler = self.compatibility_layer.degradation_handler
        self.version_detector = self.compatibility_layer.version_detector

        # V1组件引用
        self._v1_observer = None
        self._v1_analyzer = None
        self._v1_strategy_learner = None
        self._v1_self_monitor = None

        # V2组件引用
        self._v2_event_bus = None
        self._v2_service_manager = None
        self._v2_config_manager = None

        # 状态
        self._initialized = False
        self._detected_mode: Optional[RunMode] = None
        self._available_capabilities: List[str] = []
        self._module_registry: Dict[str, Any] = {}

        # 能力路由表
        self._capability_handlers: Dict[str, Dict[str, Callable]] = {}

    # ========================================================================
    # 初始化
    # ========================================================================

    async def initialize(self) -> Dict[str, Any]:
        """
        自动发现和连接所有模块

        Returns:
            初始化结果字典
        """
        if self._initialized:
            logger.warning("UnifiedAgent已经初始化")
            return {"status": "already_initialized"}

        logger.info("🚀 UnifiedAgent 初始化开始...")
        result = {
            "status": "initializing",
            "v1_detected": False,
            "v2_detected": False,
            "mode": "unknown",
            "capabilities": [],
            "errors": [],
        }

        # 1. 检测V1模块
        v1_health = self.bridge.health_check_v1()
        result["v1_detected"] = v1_health["ready"]
        result["v1_details"] = v1_health

        if v1_health["ready"]:
            await self._initialize_v1()
        else:
            result["errors"].append(f"V1未就绪: {v1_health.get('errors', [])}")

        # 2. 检测V2服务
        v2_health = self.bridge.health_check_v2()
        result["v2_detected"] = v2_health["ready"]
        result["v2_details"] = v2_health

        if v2_health["ready"]:
            await self._initialize_v2()
        else:
            result["errors"].append(f"V2未就绪: {v2_health.get('errors', [])}")

        # 3. 决定运行模式
        self._determine_run_mode()
        result["mode"] = self._detected_mode.value if self._detected_mode else "unknown"

        # 4. 注册能力处理器
        self._register_capabilities()
        result["capabilities"] = self._available_capabilities

        # 5. 检查兼容性
        compat_report = self.version_detector.check_compatibility()
        result["compatibility"] = compat_report

        # 6. 完成初始化
        self._initialized = True
        result["status"] = "initialized"

        logger.info(f"✅ UnifiedAgent 初始化完成: 模式={result['mode']}, "
                     f"能力数={len(self._available_capabilities)}")
        return result

    async def _initialize_v1(self) -> None:
        """初始化V1组件连接"""
        try:
            # 导入V1核心模块
            from evolution.learning.observer import LearningObserver
            from evolution.learning.analyzer import ExperienceAnalyzer
            from evolution.learning.tool_strategy_learner import ToolStrategyLearner

            # 创建V1组件实例
            self._v1_observer = LearningObserver()
            self._v1_analyzer = ExperienceAnalyzer(self._v1_observer)
            self._v1_strategy_learner = ToolStrategyLearner()

            # 尝试初始化SelfMonitor
            try:
                from evolution.self_monitor import SelfMonitor
                self._v1_self_monitor = SelfMonitor(
                    self._v1_observer,
                    self._v1_analyzer,
                    self._v1_strategy_learner,
                )
            except ImportError:
                logger.warning("SelfMonitor不可用，将使用独立组件")

            self._module_registry["v1_observer"] = self._v1_observer
            self._module_registry["v1_analyzer"] = self._v1_analyzer
            self._module_registry["v1_strategy_learner"] = self._v1_strategy_learner
            if self._v1_self_monitor:
                self._module_registry["v1_self_monitor"] = self._v1_self_monitor

            logger.info("V1组件初始化成功")

        except ImportError as e:
            logger.warning(f"V1组件初始化失败: {e}")
        except Exception as e:
            logger.error(f"V1初始化异常: {e}")

    async def _initialize_v2(self) -> None:
        """初始化V2服务连接"""
        try:
            from src.services.core.events.event_bus import event_bus, EventBus
            from src.services.core.services.service_manager import service_manager, ServiceManager
            from src.services.core.config.config_manager import config_manager, ConfigManager

            self._v2_event_bus = event_bus
            self._v2_service_manager = service_manager
            self._v2_config_manager = config_manager

            self._module_registry["v2_event_bus"] = event_bus
            self._module_registry["v2_service_manager"] = service_manager
            self._module_registry["v2_config_manager"] = config_manager

            # 确保服务管理器运行
            if not service_manager._running:
                await service_manager.start()

            logger.info("V2服务初始化成功")

        except ImportError as e:
            logger.warning(f"V2服务初始化失败: {e}")
        except Exception as e:
            logger.error(f"V2初始化异常: {e}")

    def _determine_run_mode(self) -> None:
        """自动决定运行模式"""
        if self._run_mode is not None:
            # 用户指定了模式
            self._detected_mode = self._run_mode
            return

        v1_ready = self.bridge.is_v1_ready()
        v2_ready = self.bridge.is_v2_ready()

        if v1_ready and v2_ready:
            self._detected_mode = RunMode.HYBRID
        elif v1_ready:
            self._detected_mode = RunMode.V1_ONLY
        elif v2_ready:
            self._detected_mode = RunMode.V2_ONLY
        else:
            logger.warning("V1和V2都不可用，默认使用V1_ONLY")
            self._detected_mode = RunMode.V1_ONLY

        logger.info(f"检测到的运行模式: {self._detected_mode.value}")

    def _register_capabilities(self) -> None:
        """注册能力处理器"""
        # V1 能力
        if self.bridge.is_v1_ready() and self._detected_mode != RunMode.V2_ONLY:
            self._register_v1_capabilities()

        # V2 能力
        if self.bridge.is_v2_ready() and self._detected_mode != RunMode.V1_ONLY:
            self._register_v2_capabilities()

        # 融合能力（两个都需要）
        if self._detected_mode == RunMode.HYBRID:
            self._register_hybrid_capabilities()

        self._available_capabilities = sorted(self._capability_handlers.keys())

    def _register_v1_capabilities(self) -> None:
        """注册V1能力"""
        v1_caps = {
            "record_experience": self._v1_record_experience,
            "analyze_experiences": self._v1_analyze_experiences,
            "recommend_tool": self._v1_recommend_tool,
            "record_tool_usage": self._v1_record_tool_usage,
            "get_tool_performance": self._v1_get_tool_performance,
            "get_health_report": self._v1_get_health_report,
            "monitor_and_improve": self._v1_monitor_and_improve,
        }
        self._capability_handlers["v1"] = v1_caps

    def _register_v2_capabilities(self) -> None:
        """注册V2能力"""
        v2_caps = {
            "publish_event": self._v2_publish_event,
            "subscribe_event": self._v2_subscribe_event,
            "get_service_status": self._v2_get_service_status,
            "list_services": self._v2_list_services,
            "get_config": self._v2_get_config,
            "set_config": self._v2_set_config,
            "get_event_history": self._v2_get_event_history,
        }
        self._capability_handlers["v2"] = v2_caps

    def _register_hybrid_capabilities(self) -> None:
        """注册融合能力"""
        hybrid_caps = {
            "health_check": self._hybrid_health_check,
            "status_report": self._hybrid_status_report,
            "convert_v1_to_v2": self._hybrid_convert_v1_to_v2,
            "convert_v2_to_v1": self._hybrid_convert_v2_to_v1,
            "sync_events": self._hybrid_sync_events,
        }
        self._capability_handlers["hybrid"] = hybrid_caps

    # ========================================================================
    # 能力执行
    # ========================================================================

    async def execute(self, request: Union[CapabilityRequest, Dict[str, Any]]) -> CapabilityResponse:
        """
        执行能力请求，自动路由到最佳执行路径

        Args:
            request: 能力请求对象或字典

        Returns:
            CapabilityResponse: 执行响应
        """
        if isinstance(request, dict):
            request = CapabilityRequest(**request)

        if not self._initialized:
            return CapabilityResponse(
                success=False,
                error="UnifiedAgent未初始化，请先调用initialize()",
                request_id=request.request_id,
            )

        import time
        start_time = time.time()

        capability = request.capability
        mode = request.mode

        try:
            # 确定路由模式
            route_mode = self._resolve_route_mode(mode, capability)

            # 构建统一请求
            api_request = UnifiedAPIRequest(
                capability=capability,
                parameters=request.parameters,
                source="unified_agent",
                correlation_id=request.request_id,
                mode=route_mode,
                timeout=request.timeout_seconds,
                metadata=request.metadata,
            )

            # 通过API网关路由
            response = await self.api_gateway.route(api_request)

            elapsed_ms = (time.time() - start_time) * 1000

            return CapabilityResponse(
                success=response.success,
                data=response.data,
                error=response.error,
                source=response.source,
                latency_ms=elapsed_ms,
                request_id=request.request_id,
                mode_used=route_mode,
                metadata={
                    "api_source": response.source,
                    "bridge_active": self.bridge.is_bridge_ready(),
                },
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"执行能力 '{capability}' 失败: {e}", exc_info=True)
            return CapabilityResponse(
                success=False,
                error=str(e),
                source="unified_agent",
                latency_ms=elapsed_ms,
                request_id=request.request_id,
            )

    def _resolve_route_mode(self, request_mode: str, capability: str) -> str:
        """解析路由模式"""
        if request_mode in ("v1", "v2", "hybrid"):
            return request_mode

        if request_mode == "auto":
            # 自动选择最佳路径
            if self._detected_mode == RunMode.HYBRID:
                # 融合模式：检查两个端
                has_v1 = capability in self._capability_handlers.get("v1", {})
                has_v2 = capability in self._capability_handlers.get("v2", {})
                has_hybrid = capability in self._capability_handlers.get("hybrid", {})

                if has_hybrid:
                    return "hybrid"
                if has_v2:
                    return "v2"  # 优先V2
                if has_v1:
                    return "v1"
                return "v1"  # 默认V1

            elif self._detected_mode == RunMode.V1_ONLY:
                return "v1"
            elif self._detected_mode == RunMode.V2_ONLY:
                return "v2"

        return "v1"  # 兜底

    # ========================================================================
    # V1 能力处理
    # ========================================================================

    async def _v1_record_experience(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 记录经验"""
        if not self._v1_observer:
            return {"success": False, "error": "V1 Observer不可用"}
        try:
            from evolution.learning.experience import Experience, ExperienceType, Outcome
            exp = Experience(
                id=params.get("id", str(uuid.uuid4())),
                experience_type=ExperienceType(params.get("experience_type", "tool_usage")),
                task_id=params.get("task_id", ""),
                description=params.get("description", ""),
                outcome=Outcome(params.get("outcome", "success")),
                context=params.get("context", {}),
                metrics=params.get("metrics", {}),
            )
            exp_id = self._v1_observer.record_experience(exp)
            return {"success": True, "experience_id": exp_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v1_analyze_experiences(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 分析经验"""
        if not self._v1_analyzer:
            return {"success": False, "error": "V1 Analyzer不可用"}
        try:
            days = params.get("days", 7)
            analysis = self._v1_analyzer.analyze_recent_experiences(days=days)
            return {
                "success": True,
                "total_experiences": analysis.total_experiences,
                "success_rate": analysis.success_rate,
                "patterns": len(analysis.identified_patterns),
                "summary": analysis.summary,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v1_recommend_tool(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 推荐工具"""
        if not self._v1_strategy_learner:
            return {"success": False, "error": "V1 StrategyLearner不可用"}
        try:
            recs = self._v1_strategy_learner.recommend_tool(
                params.get("task_description", ""),
                params.get("available_tools", []),
                params.get("context", {}),
            )
            return {
                "success": True,
                "recommendations": [
                    {"tool": r.tool_name, "confidence": r.confidence, "reason": r.reason}
                    for r in recs
                ],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v1_record_tool_usage(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 记录工具使用"""
        if not self._v1_strategy_learner:
            return {"success": False, "error": "V1 StrategyLearner不可用"}
        try:
            self._v1_strategy_learner.record_tool_usage(
                params["tool_name"],
                params.get("success", True),
                params.get("execution_time", 1.0),
                params.get("context", {}),
            )
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v1_get_tool_performance(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 获取工具性能"""
        if not self._v1_strategy_learner:
            return {"success": False, "error": "V1 StrategyLearner不可用"}
        try:
            summary = self._v1_strategy_learner.get_tool_performance_summary()
            return {"success": True, "tool_performance": summary}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v1_get_health_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 获取健康报告"""
        if not self._v1_self_monitor:
            # 尝试使用Observer和Analyzer
            if self._v1_analyzer:
                try:
                    analysis = self._v1_analyzer.analyze_recent_experiences(days=1)
                    return {
                        "success": True,
                        "health_score": int(analysis.success_rate * 100),
                        "status": "healthy" if analysis.success_rate >= 0.7 else "needs_attention",
                    }
                except Exception:
                    pass
            return {"success": False, "error": "V1 SelfMonitor不可用"}
        try:
            report = self._v1_self_monitor.get_system_health_report()
            return {"success": True, **report}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v1_monitor_and_improve(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V1: 监控和改进"""
        if not self._v1_self_monitor:
            return {"success": False, "error": "V1 SelfMonitor不可用"}
        try:
            result = self._v1_self_monitor.monitor_and_improve()
            return {"success": True, **result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========================================================================
    # V2 能力处理
    # ========================================================================

    async def _v2_publish_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 发布事件"""
        if not self._v2_event_bus:
            return {"success": False, "error": "V2 EventBus不可用"}
        try:
            from src.services.core.events.event_bus import Event, EventType, EventPriority
            event_type = EventType(params.get("event_type", "task.received"))
            priority = EventPriority(params.get("priority", 1))
            event = Event(
                event_type=event_type,
                data=params.get("data", {}),
                source=params.get("source", "unified_agent"),
                priority=priority,
            )
            await self._v2_event_bus.publish(event)
            return {"success": True, "event_id": event.event_id}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v2_subscribe_event(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 订阅事件"""
        if not self._v2_event_bus:
            return {"success": False, "error": "V2 EventBus不可用"}
        # 订阅是设置操作，这里只返回状态
        return {"success": True, "message": "事件订阅通过V2 EventBus API处理"}

    async def _v2_get_service_status(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 获取服务状态"""
        if not self._v2_service_manager:
            return {"success": False, "error": "V2 ServiceManager不可用"}
        try:
            service_id = params.get("service_id")
            if service_id:
                service = await self._v2_service_manager.get_service(service_id)
                if service:
                    return {"success": True, "service": service.to_dict()}
                return {"success": False, "error": f"服务未找到: {service_id}"}
            return {"success": False, "error": "缺少service_id"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v2_list_services(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 列出服务"""
        if not self._v2_service_manager:
            return {"success": False, "error": "V2 ServiceManager不可用"}
        try:
            services = await self._v2_service_manager.list_services()
            return {
                "success": True,
                "services": [s.to_dict() for s in services],
                "count": len(services),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v2_get_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 获取配置"""
        if not self._v2_config_manager:
            return {"success": False, "error": "V2 ConfigManager不可用"}
        try:
            key = params.get("key")
            if key:
                value = self._v2_config_manager.get(key)
                return {"success": True, "key": key, "value": value}
            return {
                "success": True,
                "config": self._v2_config_manager.get_all(),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v2_set_config(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 设置配置"""
        if not self._v2_config_manager:
            return {"success": False, "error": "V2 ConfigManager不可用"}
        try:
            key = params.get("key")
            value = params.get("value")
            if key is None:
                return {"success": False, "error": "缺少key参数"}
            ok = self._v2_config_manager.set(key, value)
            return {"success": ok}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _v2_get_event_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """V2: 获取事件历史"""
        if not self._v2_event_bus:
            return {"success": False, "error": "V2 EventBus不可用"}
        try:
            limit = params.get("limit", 100)
            history = self._v2_event_bus.get_event_history(limit=limit)
            return {
                "success": True,
                "events": [e.to_dict() if hasattr(e, 'to_dict') else str(e) for e in history],
                "count": len(history),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ========================================================================
    # 融合能力处理
    # ========================================================================

    async def _hybrid_health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """融合: 综合健康检查"""
        report = self.bridge.full_health_check()
        return {"success": True, **report}

    async def _hybrid_status_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """融合: 统一状态报告"""
        return {"success": True, **self.get_status_report()}

    async def _hybrid_convert_v1_to_v2(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """融合: V1→V2 事件转换"""
        v1_event = params.get("v1_event", {})
        v2_event = self.bridge.v1_to_v2_event(v1_event)
        return {"success": True, "v2_event": v2_event}

    async def _hybrid_convert_v2_to_v1(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """融合: V2→V1 回调转换"""
        v2_message = params.get("v2_message", {})
        v1_callback = self.bridge.v2_to_v1_callback(v2_message)
        return {"success": True, "v1_callback": v1_callback}

    async def _hybrid_sync_events(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """融合: 同步V1/V2事件"""
        # 从V2获取事件历史并转换为V1格式
        if self._v2_event_bus:
            history = self._v2_event_bus.get_event_history(limit=params.get("limit", 50))
            synced = []
            for event in history:
                event_dict = event.to_dict() if hasattr(event, 'to_dict') else {}
                v1_callback = self.bridge.v2_to_v1_callback(event_dict)
                synced.append(v1_callback)

                # 如果V1可用，记录为经验
                if self._v1_observer:
                    try:
                        from evolution.learning.experience import Experience, ExperienceType, Outcome
                        exp = Experience(
                            id=v1_callback["id"],
                            experience_type=ExperienceType(v1_callback["experience_type"]),
                            task_id=v1_callback["task_id"],
                            description=v1_callback["description"],
                            outcome=Outcome(v1_callback["outcome"]),
                            context=v1_callback["context"],
                            metrics=v1_callback.get("metrics", {}),
                        )
                        self._v1_observer.record_experience(exp)
                    except Exception:
                        pass

            return {"success": True, "synced_count": len(synced)}
        return {"success": False, "error": "V2 EventBus不可用"}

    # ========================================================================
    # 状态报告
    # ========================================================================

    def get_status_report(self) -> Dict[str, Any]:
        """
        合并来自V1和V2的状态报告

        Returns:
            统一的系统状态字典
        """
        report = {
            "timestamp": datetime.now().isoformat(),
            "run_mode": self._detected_mode.value if self._detected_mode else "unknown",
            "bridge_active": self.bridge.is_bridge_ready(),
            "initialized": self._initialized,
            "capabilities": self._available_capabilities,
        }

        # V1状态
        report["v1"] = {
            "ready": self.bridge.is_v1_ready(),
            "observer": self._v1_observer is not None,
            "analyzer": self._v1_analyzer is not None,
            "strategy_learner": self._v1_strategy_learner is not None,
            "self_monitor": self._v1_self_monitor is not None,
        }

        # V2状态
        report["v2"] = {
            "ready": self.bridge.is_v2_ready(),
            "event_bus": self._v2_event_bus is not None,
            "service_manager": self._v2_service_manager is not None,
            "config_manager": self._v2_config_manager is not None,
        }

        # 兼容性
        report["compatibility"] = self.version_detector.check_compatibility()

        # 模块清单
        report["modules"] = {
            name: "connected" for name in self._module_registry
        }

        # 健康分数
        report["health_score"] = self._calculate_health_score()

        # 摘要
        v1_status = "就绪" if report["v1"]["ready"] else "未就绪"
        v2_status = "就绪" if report["v2"]["ready"] else "未就绪"
        report["summary"] = (
            f"UnifiedAgent [{report['run_mode']}] "
            f"V1:{v1_status} V2:{v2_status} "
            f"能力:{len(self._available_capabilities)}个 "
            f"健康:{report['health_score']}"
        )

        return report

    def _calculate_health_score(self) -> float:
        """计算综合健康分数"""
        score = 0.0
        count = 0

        # V1健康
        if self.bridge.is_v1_ready():
            if self._v1_self_monitor:
                try:
                    v1_report = self._v1_self_monitor.get_system_health_report()
                    score += v1_report.get("health_score", 70)
                except Exception:
                    score += 60
            else:
                score += 50
            count += 1

        # V2健康
        if self.bridge.is_v2_ready():
            v2_score = 50.0
            if self._v2_service_manager:
                try:
                    services = self._v2_service_manager.services
                    if services:
                        avg_health = sum(
                            s.health_score for s in services.values()
                        ) / len(services)
                        v2_score = max(50, min(100, avg_health))
                except Exception:
                    pass
            score += v2_score
            count += 1

        if count == 0:
            return 0.0
        return round(score / count, 1)

    # ========================================================================
    # API 网关注册（用于外部能力路由）
    # ========================================================================

    def _sync_api_gateway_handlers(self) -> None:
        """将能力处理器同步到API网关"""
        for source, handlers in self._capability_handlers.items():
            for capability, handler in handlers.items():
                if source == "v1":
                    self.api_gateway.register_v1_handler(capability, handler)
                elif source == "v2":
                    self.api_gateway.register_v2_handler(capability, handler)
                elif source == "hybrid":
                    # 融合能力在两个端都注册
                    self.api_gateway.register_v1_handler(capability, handler)
                    self.api_gateway.register_v2_handler(capability, handler)

    async def shutdown(self) -> None:
        """关闭统一代理"""
        logger.info("🛑 UnifiedAgent 正在关闭...")

        # 停止V2服务
        if self._v2_service_manager:
            try:
                await self._v2_service_manager.stop()
            except Exception as e:
                logger.warning(f"停止V2服务管理器失败: {e}")

        self._initialized = False
        self._module_registry.clear()
        logger.info("✅ UnifiedAgent 已关闭")

    # ========================================================================
    # 便捷方法
    # ========================================================================

    def get_run_mode(self) -> str:
        """获取当前运行模式"""
        return self._detected_mode.value if self._detected_mode else "unknown"

    def get_available_capabilities(self) -> List[str]:
        """获取可用能力列表"""
        return list(self._available_capabilities)

    def is_capability_available(self, capability: str) -> bool:
        """检查能力是否可用"""
        return capability in self._available_capabilities

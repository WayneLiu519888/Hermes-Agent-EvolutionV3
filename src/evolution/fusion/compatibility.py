"""
兼容性层 - V1/V2 枚举映射、API适配器、降级策略、版本检测

提供统一的V1/V2兼容性处理，确保在两个架构版本之间无缝切换。
"""

import sys
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================================================
# 枚举映射: V1.StatusEnum ↔ V2.StatusString
# ============================================================================

class StatusMapper:
    """V1 和 V2 之间的状态映射器"""

    # V1 Outcome → V2 Event 优先级
    _OUTCOME_TO_PRIORITY = {
        "success": 1,           # NORMAL
        "partial_success": 1,   # NORMAL
        "failure": 2,           # HIGH
        "uncertain": 0,         # LOW
    }

    # V2 EventPriority → V1 置信度
    _PRIORITY_TO_CONFIDENCE = {
        0: 0.3,   # LOW
        1: 0.5,   # NORMAL
        2: 0.8,   # HIGH
        3: 0.95,  # CRITICAL
    }

    # V1 SelfMonitor 状态 → V2 ServiceStatus
    _V1_STATUS_TO_V2 = {
        "healthy": "running",
        "needs_attention": "degraded",
        "unhealthy": "failed",
        "unknown": "stopped",
    }

    # V2 ServiceStatus → V1 SelfMonitor 状态
    _V2_TO_V1_STATUS = {
        "starting": "unknown",
        "running": "healthy",
        "stopping": "needs_attention",
        "stopped": "unknown",
        "failed": "unhealthy",
        "degraded": "needs_attention",
    }

    @classmethod
    def v1_health_status_to_v2(cls, v1_status: str) -> str:
        """V1 健康状态 → V2 服务状态"""
        return cls._V1_STATUS_TO_V2.get(v1_status, "stopped")

    @classmethod
    def v2_service_status_to_v1(cls, v2_status: str) -> str:
        """V2 服务状态 → V1 健康状态"""
        return cls._V2_TO_V1_STATUS.get(v2_status, "unknown")

    @classmethod
    def v1_outcome_to_v2_priority(cls, v1_outcome: str) -> int:
        """V1 结果 → V2 事件优先级"""
        return cls._OUTCOME_TO_PRIORITY.get(v1_outcome, 1)

    @classmethod
    def v2_priority_to_v1_confidence(cls, v2_priority: int) -> float:
        """V2 事件优先级 → V1 置信度"""
        return cls._PRIORITY_TO_CONFIDENCE.get(v2_priority, 0.5)

    @classmethod
    def map_event_type_v1_to_v2(cls, v1_experience_type: str) -> str:
        """V1 经验类型 → V2 事件类型"""
        _MAP = {
            "tool_usage": "tool.executed",
            "reasoning": "task.completed",
            "problem_solving": "task.completed",
            "error_recovery": "system.error",
            "pattern_recognition": "learning.completed",
            "adaptation": "learning.progress",
        }
        return _MAP.get(v1_experience_type, "task.received")

    @classmethod
    def map_event_type_v2_to_v1(cls, v2_event_type: str) -> str:
        """V2 事件类型 → V1 经验类型"""
        _MAP = {
            "system.startup": "adaptation",
            "system.shutdown": "adaptation",
            "system.error": "error_recovery",
            "learning.started": "adaptation",
            "learning.completed": "pattern_recognition",
            "learning.failed": "error_recovery",
            "learning.progress": "adaptation",
            "tool.executed": "tool_usage",
            "tool.failed": "error_recovery",
            "tool.discovered": "pattern_recognition",
            "tool.optimized": "adaptation",
            "task.received": "problem_solving",
            "task.started": "problem_solving",
            "task.completed": "problem_solving",
            "task.failed": "error_recovery",
            "metric.updated": "adaptation",
            "alert.triggered": "error_recovery",
            "health.check": "adaptation",
        }
        return _MAP.get(v2_event_type, "adaptation")


class EnumMapper:
    """通用枚举映射器"""

    def __init__(self):
        self._v1_enum_cache: Dict[str, type] = {}
        self._v2_enum_cache: Dict[str, type] = {}

    def register_v1_enum(self, name: str, enum_cls: type) -> None:
        """注册V1枚举"""
        self._v1_enum_cache[name] = enum_cls

    def register_v2_enum(self, name: str, enum_cls: type) -> None:
        """注册V2枚举"""
        self._v2_enum_cache[name] = enum_cls

    def resolve_v1_enum(self, name: str, value: str):
        """将字符串解析为V1枚举值"""
        enum_cls = self._v1_enum_cache.get(name)
        if enum_cls is None:
            return value
        try:
            return enum_cls(value)
        except ValueError:
            logger.warning(f"无法解析V1枚举: {name}.{value}")
            return value

    def resolve_v2_enum(self, name: str, value: str):
        """将字符串解析为V2枚举值"""
        enum_cls = self._v2_enum_cache.get(name)
        if enum_cls is None:
            return value
        try:
            return enum_cls(value)
        except ValueError:
            logger.warning(f"无法解析V2枚举: {name}.{value}")
            return value


# ============================================================================
# API适配器: 统一V1和V2的调用接口
# ============================================================================

@dataclass
class UnifiedAPIRequest:
    """统一的API请求"""
    capability: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    source: str = "unified"
    correlation_id: str = ""
    mode: str = "auto"  # auto, v1, v2, hybrid
    timeout: float = 30.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class UnifiedAPIResponse:
    """统一的API响应"""
    success: bool = True
    data: Any = None
    error: Optional[str] = None
    source: str = "unknown"
    latency_ms: float = 0.0
    correlation_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class APIGateway:
    """API网关 - 统一V1和V2调用接口"""

    def __init__(self):
        self._v1_handlers: Dict[str, Callable] = {}
        self._v2_handlers: Dict[str, Callable] = {}
        self._degradation_handler: Optional['DegradationHandler'] = None

    def register_v1_handler(self, capability: str, handler: Callable) -> None:
        """注册V1处理器"""
        self._v1_handlers[capability] = handler

    def register_v2_handler(self, capability: str, handler: Callable) -> None:
        """注册V2处理器"""
        self._v2_handlers[capability] = handler

    def set_degradation_handler(self, handler: 'DegradationHandler') -> None:
        """设置降级处理器"""
        self._degradation_handler = handler

    async def route(self, request: UnifiedAPIRequest) -> UnifiedAPIResponse:
        """根据请求模式路由到合适的处理器"""
        capability = request.capability
        mode = request.mode

        import time
        start_time = time.time()

        try:
            if mode == "v1" or (mode == "auto" and capability in self._v1_handlers):
                return await self._call_v1(capability, request, start_time)

            elif mode == "v2" or (mode == "auto" and capability in self._v2_handlers):
                return await self._call_v2(capability, request, start_time)

            elif mode in ("hybrid", "auto"):
                # 融合模式：优先V2，降级到V1
                if capability in self._v2_handlers:
                    try:
                        return await self._call_v2(capability, request, start_time)
                    except Exception as e:
                        logger.warning(f"V2调用失败，降级到V1: {e}")
                        if capability in self._v1_handlers:
                            return await self._call_v1(capability, request, start_time)
                        raise

                if capability in self._v1_handlers:
                    return await self._call_v1(capability, request, start_time)

            # 未找到处理器
            return UnifiedAPIResponse(
                success=False,
                error=f"未找到能力 '{capability}' 的处理器 (模式: {mode})",
                source="gateway",
                latency_ms=(time.time() - start_time) * 1000,
                correlation_id=request.correlation_id,
            )

        except Exception as e:
            return UnifiedAPIResponse(
                success=False,
                error=str(e),
                source="gateway",
                latency_ms=(time.time() - start_time) * 1000,
                correlation_id=request.correlation_id,
            )

    async def _call_v1(self, capability: str, request: UnifiedAPIRequest,
                       start_time: float) -> UnifiedAPIResponse:
        """调用V1处理器"""
        import time
        handler = self._v1_handlers[capability]
        result = handler(request.parameters)

        if isinstance(result, dict):
            return UnifiedAPIResponse(
                success=result.get("success", True),
                data=result,
                source="v1",
                latency_ms=(time.time() - start_time) * 1000,
                correlation_id=request.correlation_id,
            )
        return UnifiedAPIResponse(
            success=True,
            data=result,
            source="v1",
            latency_ms=(time.time() - start_time) * 1000,
            correlation_id=request.correlation_id,
        )

    async def _call_v2(self, capability: str, request: UnifiedAPIRequest,
                       start_time: float) -> UnifiedAPIResponse:
        """调用V2处理器"""
        import time
        import asyncio
        handler = self._v2_handlers[capability]

        if asyncio.iscoroutinefunction(handler):
            result = await handler(request.parameters)
        else:
            result = handler(request.parameters)

        return UnifiedAPIResponse(
            success=True,
            data=result,
            source="v2",
            latency_ms=(time.time() - start_time) * 1000,
            correlation_id=request.correlation_id,
        )


# ============================================================================
# 降级策略: V2不可用时自动回退到V1
# ============================================================================

@dataclass
class DegradationRule:
    """降级规则"""
    service_name: str
    failure_threshold: int = 3
    recovery_threshold: int = 2
    cooldown_seconds: float = 30.0
    fallback_handler: Optional[Callable] = None


class DegradationHandler:
    """降级处理器 - V2不可用时自动回退到V1"""

    def __init__(self):
        self._rules: Dict[str, DegradationRule] = {}
        self._failure_counts: Dict[str, int] = {}
        self._success_counts: Dict[str, int] = {}
        self._degraded_services: Dict[str, float] = {}  # service_name → degraded_until
        self._circuit_open: Dict[str, bool] = {}

    def register_rule(self, service_name: str, rule: DegradationRule) -> None:
        """注册降级规则"""
        self._rules[service_name] = rule
        self._failure_counts[service_name] = 0
        self._success_counts[service_name] = 0
        self._circuit_open[service_name] = False

    def is_degraded(self, service_name: str) -> bool:
        """检查服务是否已降级"""
        import time
        if service_name in self._degraded_services:
            degraded_until = self._degraded_services[service_name]
            if time.time() < degraded_until:
                return True
            # 冷却期已过，恢复
            del self._degraded_services[service_name]
        return False

    def record_success(self, service_name: str) -> None:
        """记录成功调用"""
        if service_name not in self._failure_counts:
            return

        self._failure_counts[service_name] = 0
        self._success_counts[service_name] += 1

        rule = self._rules.get(service_name)
        if rule and self._circuit_open.get(service_name, False):
            if self._success_counts[service_name] >= rule.recovery_threshold:
                self._circuit_open[service_name] = False
                self._success_counts[service_name] = 0
                if service_name in self._degraded_services:
                    del self._degraded_services[service_name]
                logger.info(f"服务恢复: {service_name}")

    def record_failure(self, service_name: str) -> Optional[DegradationRule]:
        """记录失败调用，返回触发降级的规则或None"""
        import time
        if service_name not in self._failure_counts:
            return None

        self._failure_counts[service_name] += 1
        self._success_counts[service_name] = 0

        rule = self._rules.get(service_name)
        if rule and self._failure_counts[service_name] >= rule.failure_threshold:
            self._circuit_open[service_name] = True
            self._degraded_services[service_name] = time.time() + rule.cooldown_seconds
            logger.warning(f"服务降级: {service_name}, 冷却 {rule.cooldown_seconds}s")
            return rule
        return None

    def execute_with_fallback(self, service_name: str,
                               primary: Callable,
                               fallback: Callable,
                               *args, **kwargs):
        """执行带降级的主要/备用逻辑"""
        if self.is_degraded(service_name):
            logger.info(f"使用降级服务: {service_name}")
            return fallback(*args, **kwargs)

        try:
            result = primary(*args, **kwargs)
            self.record_success(service_name)
            return result
        except Exception as e:
            rule = self.record_failure(service_name)
            if rule:
                logger.warning(f"服务 {service_name} 失败，启用降级: {e}")
                return fallback(*args, **kwargs)
            raise


# ============================================================================
# 版本检测: 检查两端版本兼容性
# ============================================================================

@dataclass
class VersionInfo:
    """版本信息"""
    major: int = 0
    minor: int = 0
    patch: int = 0
    full: str = "0.0.0"
    architecture: str = "unknown"  # v1_monolith / v2_microservice

    @classmethod
    def parse(cls, version_str: str, architecture: str = "unknown") -> 'VersionInfo':
        """从字符串解析版本信息"""
        parts = version_str.strip().split(".")
        try:
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
        except (ValueError, IndexError):
            major, minor, patch = 0, 0, 0

        return cls(
            major=major,
            minor=minor,
            patch=patch,
            full=version_str,
            architecture=architecture,
        )

    def is_compatible_with(self, other: 'VersionInfo') -> bool:
        """检查是否与另一个版本兼容（主版本号必须相同）"""
        return self.major == other.major

    def is_newer_than(self, other: 'VersionInfo') -> bool:
        """检查是否比另一个版本新"""
        return (
            self.major > other.major or
            (self.major == other.major and self.minor > other.minor) or
            (self.major == other.major and self.minor == other.minor and self.patch > other.patch)
        )


class VersionDetector:
    """版本检测器"""

    def __init__(self):
        self._v1_version: Optional[VersionInfo] = None
        self._v2_version: Optional[VersionInfo] = None
        self._compatibility_status: str = "unknown"

    def detect_v1_version(self) -> VersionInfo:
        """检测V1版本"""
        try:
            from .. import __version__ as v1_ver
            self._v1_version = VersionInfo.parse(v1_ver, "v1_monolith")
        except ImportError:
            logger.warning("无法导入V1版本信息，使用默认值")
            self._v1_version = VersionInfo.parse("1.0.0", "v1_monolith")
        return self._v1_version

    def detect_v2_version(self) -> VersionInfo:
        """检测V2版本"""
        try:
            # V2 版本信息可能在 config_manager 或 main 中
            from src.services.core.config.config_manager import config_manager
            v2_ver = config_manager.get("app.version", "2.0.0")
            self._v2_version = VersionInfo.parse(v2_ver, "v2_microservice")
        except ImportError:
            logger.warning("无法导入V2配置，使用默认值")
            self._v2_version = VersionInfo.parse("2.0.0", "v2_microservice")
        return self._v2_version

    def check_compatibility(self) -> Dict[str, Any]:
        """检查V1和V2的兼容性"""
        v1_info = self._v1_version or self.detect_v1_version()
        v2_info = self._v2_version or self.detect_v2_version()

        compatible = v1_info.is_compatible_with(v2_info)

        issues = []
        if not compatible:
            issues.append(
                f"主版本不兼容: V1={v1_info.full} vs V2={v2_info.full}"
            )

        if v1_info.major == 0 and v2_info.major == 0 and v1_info.minor != v2_info.minor:
            issues.append(
                f"开发版本不匹配: V1={v1_info.full} vs V2={v2_info.full}"
            )

        self._compatibility_status = "compatible" if not issues else "incompatible"

        return {
            "compatible": compatible,
            "v1_version": v1_info.full,
            "v2_version": v2_info.full,
            "v1_architecture": v1_info.architecture,
            "v2_architecture": v2_info.architecture,
            "issues": issues,
            "status": self._compatibility_status,
        }

    def get_minimum_required_v2_for_v1(self, v1_version: VersionInfo) -> VersionInfo:
        """获取与V1兼容的最小V2版本"""
        return VersionInfo(
            major=v1_version.major,
            minor=0,
            patch=0,
            full=f"{v1_version.major}.0.0",
            architecture="v2_microservice",
        )


# ============================================================================
# 兼容性层统一入口
# ============================================================================

class CompatibilityLayer:
    """兼容性层 - 统一入口"""

    def __init__(self):
        self.status_mapper = StatusMapper()
        self.enum_mapper = EnumMapper()
        self.api_gateway = APIGateway()
        self.degradation_handler = DegradationHandler()
        self.version_detector = VersionDetector()

        # 连接降级处理器到API网关
        self.api_gateway.set_degradation_handler(self.degradation_handler)

    def initialize(self) -> Dict[str, Any]:
        """初始化兼容性层，检测版本兼容性"""
        version_report = self.version_detector.check_compatibility()
        logger.info(
            f"兼容性层初始化: V1={version_report['v1_version']}, "
            f"V2={version_report['v2_version']}, "
            f"状态={version_report['status']}"
        )
        return version_report


# ============================================================================
# 便利函数 - 简化枚举映射调用
# ============================================================================

def v1_status_to_v2_status(v1_health_status: str) -> str:
    """V1 健康状态 → V2 服务状态"""
    return StatusMapper.v1_health_status_to_v2(v1_health_status)


def v2_status_to_v1_status(v2_service_status: str) -> str:
    """V2 服务状态 → V1 健康状态"""
    return StatusMapper.v2_service_status_to_v1(v2_service_status)


def v1_outcome_to_v2_priority(v1_outcome: str) -> int:
    """V1 结果 → V2 事件优先级"""
    return StatusMapper.v1_outcome_to_v2_priority(v1_outcome)


def v2_priority_to_v1_confidence(v2_priority: int) -> float:
    """V2 事件优先级 → V1 置信度"""
    return StatusMapper.v2_priority_to_v1_confidence(v2_priority)

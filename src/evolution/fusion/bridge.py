"""
V1↔V2 桥接层 - 事件、数据格式、服务映射的双向转换

核心组件：
  - V1V2Bridge: 主桥接类，管理所有转换和健康检查
  - v1_to_v2_event: V1 事件 → V2 EventBus 兼容事件
  - v2_to_v1_callback: V2 消息 → V1 兼容回调
  - 服务映射表: V1模块 → V2微服务双向映射
  - 数据格式转换器: V1 dataclass ↔ V2 JSON/dict
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List, Callable, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import uuid

from .compatibility import (
    StatusMapper, EnumMapper, VersionDetector, VersionInfo,
    v1_status_to_v2_status, v2_status_to_v1_status,
    v1_outcome_to_v2_priority, v2_priority_to_v1_confidence,
)

logger = logging.getLogger(__name__)

# ============================================================================
# 服务映射表: V1模块 → V2微服务
# ============================================================================

# V1 模块标识
V1_MODULE = "v1_monolith"
# V2 服务类型标识
V2_SERVICE_TYPE = "v2_microservice"

# V1 模块 → V2 微服务映射
SERVICE_MAP_V1_TO_V2: Dict[str, str] = {
    # V1 learning 模块 → V2 学习服务
    "learning.observer": "LearningOrchestrator",
    "learning.analyzer": "LearningOrchestrator",
    "learning.tool_strategy": "LearningOrchestrator",
    "learning.pattern_recognizer": "LearningOrchestrator",
    "learning.experience": "LearningOrchestrator",

    # V1 tools 模块 → V2 工具服务
    "tools.registry": "ToolManager",
    "tools.creator": "ToolManager",
    "tools.integration": "ToolManager",
    "tools.performance": "ToolManager",
    "tools.auto_generator": "ToolManager",
    "tools.enhanced_creator": "ToolManager",

    # V1 memory 模块 → V2 存储服务（概念映射）
    "memory.database": "MonitoringService",
    "memory.retrieval": "MonitoringService",
    "memory.association": "MonitoringService",

    # V1 self_monitor → V2 监控服务
    "self_monitor": "MonitoringService",

    # V1 collaboration 模块 → V2 核心服务
    "collaboration.registry": "ServiceManager",
    "collaboration.orchestrator": "ServiceManager",
    "collaboration.dispatcher": "ServiceManager",
    "collaboration.message_bus": "EventBus",

    # V1 security 模块 → V2 核心服务（无直接对应，映射到监控）
    "security.threat_detector": "MonitoringService",
    "security.sandbox_executor": "MonitoringService",
    "security.permission_manager": "ConfigManager",
    "security.audit_logger": "MonitoringService",
}

# V2 微服务 → V1 模块反向映射
SERVICE_MAP_V2_TO_V1: Dict[str, str] = {
    "LearningOrchestrator": "learning",
    "ToolManager": "tools",
    "MonitoringService": "self_monitor",
    "ServiceManager": "collaboration",
    "EventBus": "collaboration.message_bus",
    "ConfigManager": "security.permission_manager",
}


@dataclass
class ServiceMapping:
    """单个服务映射条目"""
    v1_module: str
    v2_service: str
    direction: str = "bidirectional"  # bidirectional, v1_to_v2, v2_to_v1
    active: bool = True
    description: str = ""


# ============================================================================
# V1 dataclass ↔ V2 JSON 数据格式转换器
# ============================================================================

@dataclass
class V1ExperienceData:
    """V1 经验数据的中间表示（JSON可序列化）"""
    id: str = ""
    experience_type: str = ""
    task_id: str = ""
    timestamp: str = ""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    outcome: str = ""
    result: Any = None
    metrics: Dict[str, float] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    importance: float = 0.0


@dataclass
class V2EventData:
    """V2 事件数据的中间表示（JSON可序列化）"""
    event_id: str = ""
    event_type: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: str = ""
    priority: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)


class DataFormatConverter:
    """数据格式转换器: V1 dataclass ↔ V2 JSON/dict"""

    @staticmethod
    def v1_experience_to_dict(v1_experience) -> Dict[str, Any]:
        """V1 Experience dataclass → dict"""
        try:
            # 尝试使用 to_dict 方法
            return v1_experience.to_dict()
        except AttributeError:
            # 手动转换 dataclass
            result = {}
            for field_name in v1_experience.__dataclass_fields__:
                value = getattr(v1_experience, field_name)
                if hasattr(value, 'value'):  # Enum
                    result[field_name] = value.value
                elif isinstance(value, datetime):
                    result[field_name] = value.isoformat()
                elif hasattr(value, 'to_dict'):
                    result[field_name] = value.to_dict()
                else:
                    result[field_name] = value
            return result

    @staticmethod
    def dict_to_v1_experience(data: Dict[str, Any]):
        """dict → V1 Experience dataclass"""
        try:
            from evolution.learning.experience import Experience
            return Experience.from_dict(data)
        except ImportError:
            logger.warning("无法导入V1 Experience，返回字典")
            return data

    @staticmethod
    def dict_to_v2_event(data: Dict[str, Any]):
        """dict → V2 Event dataclass"""
        try:
            from services.core.events.event_bus import Event, EventType, EventPriority
            event_type = EventType(data.get("event_type", "task.received"))
            priority = EventPriority(data.get("priority", 1))
            return Event(
                event_type=event_type,
                data=data.get("data", {}),
                source=data.get("source", "v1_bridge"),
                priority=priority,
                metadata=data.get("metadata", {}),
            )
        except ImportError:
            logger.warning("无法导入V2 Event，返回字典")
            return data

    @staticmethod
    def v2_event_to_dict(v2_event) -> Dict[str, Any]:
        """V2 Event dataclass → dict"""
        try:
            return v2_event.to_dict()
        except AttributeError:
            result = {}
            for field_name in v2_event.__dataclass_fields__:
                value = getattr(v2_event, field_name)
                if hasattr(value, 'value'):
                    result[field_name] = value.value
                elif isinstance(value, datetime):
                    result[field_name] = value.isoformat()
                else:
                    result[field_name] = value
            return result

    @staticmethod
    def v1_analysis_to_dict(v1_analysis_result) -> Dict[str, Any]:
        """V1 AnalysisResult dataclass → dict"""
        try:
            return {
                "timestamp": v1_analysis_result.timestamp.isoformat(),
                "total_experiences": v1_analysis_result.total_experiences,
                "success_rate": v1_analysis_result.success_rate,
                "identified_patterns": [
                    {
                        "pattern_type": p.pattern_type.value if hasattr(p.pattern_type, 'value') else str(p.pattern_type),
                        "confidence": p.confidence,
                        "frequency": p.frequency,
                        "description": p.description,
                        "recommendations": p.recommendations,
                    }
                    for p in v1_analysis_result.identified_patterns
                ],
                "key_insights": v1_analysis_result.key_insights,
                "improvement_suggestions": v1_analysis_result.improvement_suggestions,
                "summary": v1_analysis_result.summary,
            }
        except Exception as e:
            logger.warning(f"AnalysisResult转换失败: {e}")
            return {"summary": str(v1_analysis_result), "error": str(e)}

    @staticmethod
    def v1_health_report_to_v2_services(v1_health_report: Dict[str, Any]) -> List[Dict[str, Any]]:
        """V1 健康报告 → V2 服务状态列表"""
        services = []

        # 将V1健康报告转换为V2服务格式
        v2_status = v1_status_to_v2_status(v1_health_report.get("status", "unknown"))
        health_score = v1_health_report.get("health_score", 0)
        metrics = v1_health_report.get("metrics", {})

        # 为V1的每个子系统创建V2服务条目
        service_defs = [
            {
                "name": "V1_SelfMonitor",
                "type": "monitoring",
                "health": health_score,
                "status": v2_status,
            },
            {
                "name": "V1_LearningEngine",
                "type": "learning",
                "health": min(100, health_score + 5),
                "status": v2_status,
            },
            {
                "name": "V1_ToolSystem",
                "type": "tool",
                "health": min(100, health_score + (metrics.get("monitored_tools", 0) * 5)),
                "status": v2_status,
            },
        ]

        for sd in service_defs:
            services.append({
                "service_id": f"v1_{sd['name'].lower()}_{uuid.uuid4().hex[:8]}",
                "service_type": sd["type"],
                "name": sd["name"],
                "version": "1.0.0",
                "status": sd["status"],
                "health_score": sd["health"],
                "description": f"V1模块代理: {sd['name']}",
            })

        return services


# ============================================================================
# V1V2Bridge 主类
# ============================================================================

class V1V2Bridge:
    """
    V1↔V2 桥接层

    管理V1单体架构和V2微服务架构之间的所有转换、映射和通信。
    """

    def __init__(self):
        self.converter = DataFormatConverter()
        self.status_mapper = StatusMapper()
        self.enum_mapper = EnumMapper()
        self.version_detector = VersionDetector()

        # 服务映射
        self._service_map_v1_to_v2: Dict[str, str] = dict(SERVICE_MAP_V1_TO_V2)
        self._service_map_v2_to_v1: Dict[str, str] = dict(SERVICE_MAP_V2_TO_V1)

        # 桥接状态
        self._v1_ready: bool = False
        self._v2_ready: bool = False
        self._bridge_active: bool = False
        self._event_history: List[Dict[str, Any]] = []
        self._max_history: int = 500

        # 注册枚举映射
        self._register_enum_mappings()

    def _register_enum_mappings(self) -> None:
        """注册V1和V2枚举映射"""
        try:
            from evolution.learning.experience import Outcome, ExperienceType
            self.enum_mapper.register_v1_enum("Outcome", Outcome)
            self.enum_mapper.register_v1_enum("ExperienceType", ExperienceType)
        except ImportError:
            pass

        try:
            from services.core.events.event_bus import EventType, EventPriority
            self.enum_mapper.register_v2_enum("EventType", EventType)
            self.enum_mapper.register_v2_enum("EventPriority", EventPriority)
        except ImportError:
            pass

        try:
            from services.core.services.service_manager import ServiceStatus, ServiceType
            self.enum_mapper.register_v2_enum("ServiceStatus", ServiceStatus)
            self.enum_mapper.register_v2_enum("ServiceType", ServiceType)
        except ImportError:
            pass

    # ---------- 事件转换 ----------

    def v1_to_v2_event(self, v1_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        将V1事件转换为V2 EventBus兼容事件

        Args:
            v1_event: V1事件字典，通常来自LearningObserver或SelfMonitor

        Returns:
            V2 Event兼容的事件字典（可用作EventBus.publish的参数）
        """
        event_type_str = "task.received"

        # 推断V2事件类型
        v1_exp_type = v1_event.get("experience_type", "")
        if v1_exp_type:
            event_type_str = self.status_mapper.map_event_type_v1_to_v2(v1_exp_type)
        else:
            outcome = v1_event.get("outcome", "")
            if outcome == "success":
                event_type_str = "task.completed"
            elif outcome in ("failure", "partial_success"):
                event_type_str = "task.failed"
            elif v1_event.get("type") == "health_report":
                event_type_str = "health.check"
            elif v1_event.get("type") == "improvement":
                event_type_str = "learning.completed"

        # 推断优先级
        priority = 1  # NORMAL
        if v1_event.get("outcome"):
            priority = v1_outcome_to_v2_priority(v1_event["outcome"])
        elif v1_event.get("priority") == "high":
            priority = 2
        elif v1_event.get("priority") == "critical":
            priority = 3

        # 构建V2事件数据
        v2_data = {
            "v1_source": True,
            "v1_original_type": v1_event.get("experience_type", "unknown"),
            "v1_event_id": v1_event.get("id", str(uuid.uuid4())),
            "v1_timestamp": v1_event.get("timestamp", datetime.now().isoformat()),
            "payload": v1_event,
        }

        # 合并指标
        if "metrics" in v1_event:
            v2_data["v1_metrics"] = v1_event["metrics"]

        event_dict = {
            "event_type": event_type_str,
            "data": v2_data,
            "source": "v1_bridge",
            "timestamp": datetime.now().isoformat(),
            "priority": priority,
            "metadata": {
                "bridge_version": "1.0.0",
                "v1_module": v1_event.get("source_module", "unknown"),
                "conversion_time": datetime.now().isoformat(),
            },
        }

        # 记录事件历史
        self._log_event("v1_to_v2", event_dict)
        return event_dict

    def v2_to_v1_callback(self, v2_message: Dict[str, Any]) -> Dict[str, Any]:
        """
        将V2消息转换为V1兼容的回调格式

        Args:
            v2_message: V2 EventBus消息（Event.to_dict()的输出）

        Returns:
            V1兼容的回调数据字典
        """
        event_type = v2_message.get("event_type", "")
        v2_data = v2_message.get("data", {})

        # 推断V1经验类型
        v1_exp_type = self.status_mapper.map_event_type_v2_to_v1(event_type)

        # 推断V1结果
        v1_outcome = "success"
        if "error" in event_type or "failed" in event_type:
            v1_outcome = "failure"
        elif "shutdown" in event_type or "alert" in event_type:
            v1_outcome = "uncertain"

        # 推断V1置信度
        priority = v2_message.get("priority", 1)
        confidence = v2_priority_to_v1_confidence(priority)

        callback_data = {
            "id": v2_message.get("event_id", str(uuid.uuid4())),
            "experience_type": v1_exp_type,
            "task_id": v2_data.get("task_id", f"v2_task_{uuid.uuid4().hex[:8]}"),
            "timestamp": v2_message.get("timestamp", datetime.now().isoformat()),
            "description": f"V2事件: {event_type}",
            "context": v2_data,
            "outcome": v1_outcome,
            "result": v2_data.get("payload", v2_data),
            "metrics": v2_data.get("v1_metrics", {}),
            "confidence": confidence,
            "importance": 0.5,
            "source": "v2_bridge",
            "v2_event_type": event_type,
            "v2_priority": priority,
        }

        self._log_event("v2_to_v1", callback_data)
        return callback_data

    # ---------- 服务映射 ----------

    def get_v2_service_for_v1_module(self, v1_module: str) -> Optional[str]:
        """根据V1模块名称获取对应的V2服务名"""
        return self._service_map_v1_to_v2.get(v1_module)

    def get_v1_module_for_v2_service(self, v2_service: str) -> Optional[str]:
        """根据V2服务名称获取对应的V1模块名"""
        return self._service_map_v2_to_v1.get(v2_service)

    def add_service_mapping(self, v1_module: str, v2_service: str,
                            direction: str = "bidirectional") -> None:
        """添加自定义服务映射"""
        self._service_map_v1_to_v2[v1_module] = v2_service
        if direction in ("bidirectional", "v2_to_v1"):
            self._service_map_v2_to_v1[v2_service] = v1_module
        logger.info(f"添加服务映射: {v1_module} ↔ {v2_service} ({direction})")

    def list_v1_modules(self) -> List[str]:
        """列出所有已知的V1模块"""
        return sorted(self._service_map_v1_to_v2.keys())

    def list_v2_services(self) -> List[str]:
        """列出所有已知的V2服务"""
        return sorted(set(self._service_map_v1_to_v2.values()))

    def get_full_service_mapping(self) -> List[ServiceMapping]:
        """获取完整的服务映射表"""
        mappings = []
        for v1_mod, v2_svc in self._service_map_v1_to_v2.items():
            direction = "bidirectional"
            if v2_svc not in self._service_map_v2_to_v1:
                direction = "v1_to_v2"
            elif self._service_map_v2_to_v1.get(v2_svc) != v1_mod:
                direction = "v1_to_v2"
            mappings.append(ServiceMapping(
                v1_module=v1_mod,
                v2_service=v2_svc,
                direction=direction,
                description=f"V1.{v1_mod} ↔ V2.{v2_svc}",
            ))
        return sorted(mappings, key=lambda m: (m.v2_service, m.v1_module))

    # ---------- 数据转换 ----------

    def convert_v1_to_v2_json(self, v1_dataclass_obj) -> Dict[str, Any]:
        """V1 dataclass → V2兼容的JSON/dict"""
        return self.converter.v1_experience_to_dict(v1_dataclass_obj)

    def convert_v2_to_v1_dataclass(self, v2_dict: Dict[str, Any]):
        """V2 dict → V1 dataclass"""
        return self.converter.dict_to_v1_experience(v2_dict)

    def convert_v2_event_to_v1_format(self, v2_event) -> Dict[str, Any]:
        """V2 Event → V1兼容格式"""
        event_dict = self.converter.v2_event_to_dict(v2_event)
        return self.v2_to_v1_callback(event_dict)

    # ---------- 健康检查 ----------

    def health_check_v1(self) -> Dict[str, Any]:
        """
        检查V1端是否就绪

        Returns:
            V1健康状态报告
        """
        v1_status = {
            "ready": False,
            "modules": {},
            "version": "unknown",
            "errors": [],
        }

        # 尝试导入V1核心模块
        modules_to_check = [
            ("learning", "src.evolution.learning"),
            ("self_monitor", "src.evolution.self_monitor"),
            ("tools", "src.evolution.tools"),
            ("memory", "src.evolution.memory"),
        ]

        for name, import_path in modules_to_check:
            try:
                __import__(import_path)
                v1_status["modules"][name] = "available"
            except ImportError as e:
                v1_status["modules"][name] = f"unavailable: {e}"
                v1_status["errors"].append(f"V1.{name}: {e}")

        # 检测版本
        v1_info = self.version_detector.detect_v1_version()
        v1_status["version"] = v1_info.full

        # 如果关键模块可用，则认为V1就绪
        critical_modules = ["learning", "self_monitor"]
        v1_status["ready"] = all(
            v1_status["modules"].get(m) == "available"
            for m in critical_modules
        )

        self._v1_ready = v1_status["ready"]
        return v1_status

    def health_check_v2(self) -> Dict[str, Any]:
        """
        检查V2端是否就绪

        Returns:
            V2健康状态报告
        """
        v2_status = {
            "ready": False,
            "services": {},
            "version": "unknown",
            "errors": [],
        }

        # 尝试导入V2核心模块
        services_to_check = [
            ("event_bus", "src.services.core.events.event_bus"),
            ("service_manager", "src.services.core.services.service_manager"),
            ("config_manager", "src.services.core.config.config_manager"),
        ]

        for name, import_path in services_to_check:
            try:
                __import__(import_path)
                v2_status["services"][name] = "available"
            except ImportError as e:
                v2_status["services"][name] = f"unavailable: {e}"
                v2_status["errors"].append(f"V2.{name}: {e}")

        # 检测版本
        v2_info = self.version_detector.detect_v2_version()
        v2_status["version"] = v2_info.full

        # 如果核心服务可用，则认为V2就绪
        critical_services = ["event_bus", "service_manager"]
        v2_status["ready"] = all(
            v2_status["services"].get(s) == "available"
            for s in critical_services
        )

        self._v2_ready = v2_status["ready"]
        return v2_status

    def full_health_check(self) -> Dict[str, Any]:
        """
        完整的V1/V2健康检查

        Returns:
            包含V1和V2健康状态的完整报告
        """
        v1_health = self.health_check_v1()
        v2_health = self.health_check_v2()

        # 检查兼容性
        compatibility = self.version_detector.check_compatibility()

        # 检查桥接状态
        self._bridge_active = v1_health["ready"] and v2_health["ready"] and compatibility["compatible"]

        return {
            "timestamp": datetime.now().isoformat(),
            "bridge_active": self._bridge_active,
            "v1": v1_health,
            "v2": v2_health,
            "compatibility": compatibility,
            "service_mappings_count": len(self._service_map_v1_to_v2),
            "event_history_count": len(self._event_history),
        }

    def is_bridge_ready(self) -> bool:
        """检查桥接是否完全就绪"""
        return self._bridge_active

    def is_v1_ready(self) -> bool:
        """检查V1是否就绪"""
        return self._v1_ready

    def is_v2_ready(self) -> bool:
        """检查V2是否就绪"""
        return self._v2_ready

    # ---------- 事件历史 ----------

    def _log_event(self, direction: str, event: Dict[str, Any]) -> None:
        """记录事件转换历史"""
        self._event_history.append({
            "direction": direction,
            "timestamp": datetime.now().isoformat(),
            "event": event,
        })
        if len(self._event_history) > self._max_history:
            self._event_history = self._event_history[-self._max_history:]

    def get_event_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """获取事件转换历史"""
        return self._event_history[-limit:] if self._event_history else []

    def clear_event_history(self) -> None:
        """清空事件转换历史"""
        self._event_history.clear()

    # ---------- 状态摘要 ----------

    def get_bridge_summary(self) -> Dict[str, Any]:
        """获取桥接状态摘要"""
        return {
            "bridge_version": "1.0.0",
            "v1_ready": self._v1_ready,
            "v2_ready": self._v2_ready,
            "bridge_active": self._bridge_active,
            "service_mappings": len(self._service_map_v1_to_v2),
            "v1_modules": len(self.list_v1_modules()),
            "v2_services": len(self.list_v2_services()),
            "events_processed": len(self._event_history),
            "compatibility": self.version_detector._compatibility_status,
        }


# ============================================================================
# 便利常量 - V1状态枚举映射
# ============================================================================

V1_STATUS_ENUM = {
    "Outcome": {"success", "partial_success", "failure", "uncertain"},
    "ExperienceType": {
        "tool_usage", "reasoning", "problem_solving",
        "error_recovery", "pattern_recognition", "adaptation",
    },
}

V2_SERVICE_TYPE = {
    "core", "learning", "tool", "monitoring", "storage", "api",
}

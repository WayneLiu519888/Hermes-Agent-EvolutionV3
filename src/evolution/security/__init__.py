"""
安全增强模块 - Hermes Agent Evolution 迭代4任务4.3

提供企业级安全能力：
- 审计日志: 记录所有关键操作到SQLite
- 权限控制: 基于角色的访问控制 (RBAC)
- 沙箱执行: 隔离环境中的代码安全执行
- 威胁检测: 基于规则的实时威胁检测引擎

与以下模块集成：
- src/evolution/self_monitor.py  → 安全指标上报
- src/utils/feishu_notifier.py   → 安全告警推送
"""

from .audit_logger import (
    AuditLogger,
    AuditLogLevel,
    EventType,
    AuditEntry,
    AuditQueryResult,
)

from .permission_manager import (
    PermissionManager,
    Operation,
    Role,
    AgentPermission,
    PermissionCheckResult,
)

from .sandbox_executor import (
    SandboxExecutor,
    SandboxStatus,
    SandboxResult,
    CodeSafetyAnalyzer,
    analyze_code_safety,
)

from .threat_detector import (
    ThreatDetector,
    ThreatLevel,
    ThreatCategory,
    ThreatAlert,
    DetectionRule,
)

__all__ = [
    # 审计日志
    "AuditLogger",
    "AuditLogLevel",
    "EventType",
    "AuditEntry",
    "AuditQueryResult",
    # 权限控制
    "PermissionManager",
    "Operation",
    "Role",
    "AgentPermission",
    "PermissionCheckResult",
    # 沙箱执行
    "SandboxExecutor",
    "SandboxStatus",
    "SandboxResult",
    "CodeSafetyAnalyzer",
    "analyze_code_safety",
    # 威胁检测
    "ThreatDetector",
    "ThreatLevel",
    "ThreatCategory",
    "ThreatAlert",
    "DetectionRule",
]

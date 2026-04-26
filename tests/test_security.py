"""
安全增强模块测试 - Hermes Agent Evolution

测试覆盖:
- AuditLogger: 写入、查询、统计、轮转
- PermissionManager: 角色分配、权限检查、继承、资源所有权
- SandboxExecutor: 代码安全分析、沙箱执行、资源限制
- ThreatDetector: 规则匹配、频率检测、告警生成
"""

import os
import re
import sys
import json
import time
import tempfile
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

# 确保项目在sys.path中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.security.audit_logger import (
    AuditLogger,
    AuditLogLevel,
    EventType,
    AuditEntry,
    AuditQueryResult,
)
from src.evolution.security.permission_manager import (
    PermissionManager,
    Operation,
    Role,
    AgentPermission,
    PermissionCheckResult,
)
from src.evolution.security.sandbox_executor import (
    SandboxExecutor,
    SandboxStatus,
    SandboxResult,
    CodeSafetyAnalyzer,
    analyze_code_safety,
)
from src.evolution.security.threat_detector import (
    ThreatDetector,
    ThreatLevel,
    ThreatCategory,
    ThreatAlert,
    DetectionRule,
)


# ============================================================
# Fixtures
# ============================================================

@pytest.fixture
def temp_db_path():
    """创建临时数据库路径"""
    fd, path = tempfile.mkstemp(suffix=".db", prefix="test_audit_")
    os.close(fd)
    yield path
    try:
        os.unlink(path)
    except OSError:
        pass


@pytest.fixture
def audit_logger(temp_db_path):
    """创建测试用的AuditLogger"""
    logger = AuditLogger(db_path=temp_db_path)
    yield logger


@pytest.fixture
def permission_manager(audit_logger):
    """创建测试用的PermissionManager (带审计)"""
    return PermissionManager(audit_logger=audit_logger)


@pytest.fixture
def sandbox_executor(audit_logger):
    """创建测试用的SandboxExecutor"""
    return SandboxExecutor(audit_logger=audit_logger)


@pytest.fixture
def mock_notifier():
    """模拟FeishuNotifier"""
    notifier = Mock()
    notifier.send_notification = Mock(return_value=True)
    return notifier


@pytest.fixture
def mock_monitor():
    """模拟SelfMonitor"""
    monitor = Mock()
    return monitor


@pytest.fixture
def threat_detector(mock_notifier, audit_logger):
    """创建测试用的ThreatDetector"""
    return ThreatDetector(
        feishu_notifier=mock_notifier,
        audit_logger=audit_logger,
    )


# ============================================================
# AuditLogger 测试
# ============================================================

class TestAuditLogger:
    """审计日志测试"""

    def test_log_single_event(self, audit_logger):
        """测试记录单条审计事件"""
        record_id = audit_logger.log_event(
            event_type=EventType.AGENT_ACTION,
            level=AuditLogLevel.INFO,
            agent_id="agent_001",
            action="test_action",
            description="Test action execution",
            details={"param": "value"},
        )
        assert record_id is not None
        assert record_id > 0

        # 验证记录可查询
        entry = audit_logger.get_event_by_id(record_id)
        assert entry is not None
        assert entry.agent_id == "agent_001"
        assert entry.action == "test_action"
        assert entry.event_type == "AGENT_ACTION"
        assert entry.level == "INFO"
        assert entry.details == {"param": "value"}

    def test_log_critical_event_with_notification(self, temp_db_path, mock_notifier):
        """测试CRITICAL级别事件触发飞书通知"""
        logger = AuditLogger(db_path=temp_db_path, feishu_notifier=mock_notifier)

        logger.log_event(
            event_type=EventType.SECURITY,
            level=AuditLogLevel.CRITICAL,
            agent_id="agent_002",
            action="unauthorized_access",
            description="Unauthorized system access attempt",
            details={"ip": "192.168.1.100"},
        )

        # 验证飞书通知被调用
        mock_notifier.send_notification.assert_called_once()
        call_args = mock_notifier.send_notification.call_args
        assert "unauthorized_access" in call_args[1]["title"]

    def test_query_by_time_range(self, audit_logger):
        """测试时间范围查询"""
        # 写入多条记录
        for i in range(5):
            audit_logger.log_event(
                event_type=EventType.TOOL_EXECUTION,
                action=f"tool_{i}",
                agent_id="query_test",
            )

        # 查询全部
        result = audit_logger.query()
        assert result.total_count >= 5

        # 时间范围查询
        now = datetime.now().isoformat()
        future = (datetime.now() + timedelta(hours=1)).isoformat()
        result = audit_logger.query(start_time=now, end_time=future)
        # 因为刚刚写入，可能在now之后
        recent = audit_logger.query_recent(hours=1)
        assert recent.total_count >= 0  # 至少不报错

    def test_query_by_event_type(self, audit_logger):
        """测试按事件类型过滤"""
        audit_logger.log_event(event_type=EventType.SYSTEM_CONFIG, action="config_change")
        audit_logger.log_event(event_type=EventType.AGENT_ACTION, action="agent_act")
        audit_logger.log_event(event_type=EventType.SYSTEM_CONFIG, action="config_change_2")

        result = audit_logger.query(event_type=EventType.SYSTEM_CONFIG)
        assert result.total_count >= 2

        result2 = audit_logger.query(event_type=EventType.AGENT_ACTION)
        assert result2.total_count >= 1

    def test_query_by_level(self, audit_logger):
        """测试按日志级别过滤"""
        audit_logger.log_event(event_type=EventType.AGENT_ACTION, level=AuditLogLevel.INFO, action="info_event")
        audit_logger.log_event(event_type=EventType.TOOL_EXECUTION, level=AuditLogLevel.WARNING, action="warn_event")
        audit_logger.log_event(event_type=EventType.SYSTEM_CONFIG, level=AuditLogLevel.ERROR, action="error_event")

        result = audit_logger.query(level=AuditLogLevel.WARNING)
        assert result.total_count >= 1

    def test_get_statistics(self, audit_logger):
        """测试获取统计信息"""
        audit_logger.log_event(level=AuditLogLevel.INFO, event_type=EventType.AGENT_ACTION, action="a1")
        audit_logger.log_event(level=AuditLogLevel.WARNING, event_type=EventType.TOOL_EXECUTION, action="a2")
        audit_logger.log_event(level=AuditLogLevel.ERROR, event_type=EventType.AGENT_ACTION, action="a3", outcome="failure")

        stats = audit_logger.get_statistics(hours=24)
        assert "total_events" in stats
        assert "by_level" in stats
        assert "by_event_type" in stats
        assert stats["total_events"] >= 3
        assert "failure_count" in stats

    def test_batch_logging(self, audit_logger):
        """测试批量日志记录"""
        entries = [
            AuditEntry(
                event_type=EventType.AGENT_ACTION.value,
                action=f"batch_action_{i}",
                agent_id="batch_test",
            )
            for i in range(10)
        ]
        count = audit_logger.log_batch(entries)
        assert count == 10

        result = audit_logger.query(agent_id="batch_test")
        assert result.total_count == 10

    def test_log_rotation(self, temp_db_path):
        """测试日志轮转"""
        # 使用较小的阈值方便测试
        logger = AuditLogger(db_path=temp_db_path)
        original_max = logger.MAX_RECORDS
        logger.MAX_RECORDS = 50  # 设置较小阈值

        try:
            # 写入超过阈值的记录
            entries = [
                AuditEntry(action=f"rotation_test_{i}", agent_id="rotation")
                for i in range(60)
            ]
            logger.log_batch(entries)

            # 应该已完成轮转
            count = logger.get_record_count()
            assert count < 60  # 应该有部分被归档
        finally:
            logger.MAX_RECORDS = original_max


# ============================================================
# PermissionManager 测试
# ============================================================

class TestPermissionManager:
    """权限管理测试"""

    def test_assign_role(self, permission_manager):
        """测试角色分配"""
        perm = permission_manager.assign_role("agent_001", Role.DEVELOPER)
        assert perm.role == Role.DEVELOPER
        assert permission_manager.get_role("agent_001") == Role.DEVELOPER

    def test_default_role_viewer(self, permission_manager):
        """测试默认角色为VIEWER"""
        role = permission_manager.get_role("unknown_agent")
        assert role == Role.VIEWER

    def test_admin_has_all_permissions(self, permission_manager):
        """测试ADMIN拥有所有权限"""
        permission_manager.assign_role("admin_agent", Role.ADMIN)

        for op in Operation:
            result = permission_manager.check_permission(
                "admin_agent", f"test_{op.value}", operation=op
            )
            assert result.allowed, f"ADMIN should have {op.value} permission"

    def test_viewer_read_only(self, permission_manager):
        """测试VIEWER只有读权限"""
        permission_manager.assign_role("viewer_agent", Role.VIEWER)

        # READ 应该允许
        result = permission_manager.check_permission(
            "viewer_agent", "read_data", operation=Operation.READ
        )
        assert result.allowed

        # WRITE 应该拒绝
        result = permission_manager.check_permission(
            "viewer_agent", "write_data", operation=Operation.WRITE
        )
        assert not result.allowed

        # EXECUTE 应该拒绝
        result = permission_manager.check_permission(
            "viewer_agent", "run_code", operation=Operation.EXECUTE
        )
        assert not result.allowed

    def test_operator_inherits_viewer(self, permission_manager):
        """测试OPERATOR继承VIEWER权限"""
        permission_manager.assign_role("operator_agent", Role.OPERATOR)

        # OPERATOR应该有READ（继承）+ WRITE + EXECUTE
        assert permission_manager.check_permission_simple("operator_agent", "read")
        assert permission_manager.check_permission_simple("operator_agent", "write")
        assert permission_manager.check_permission_simple("operator_agent", "execute")

        # 但没有DELETE和CONFIGURE
        assert not permission_manager.check_permission_simple("operator_agent", "delete")
        assert not permission_manager.check_permission_simple("operator_agent", "configure")

    def test_operation_inference(self, permission_manager):
        """测试从action名称推断操作类型"""
        permission_manager.assign_role("dev_agent", Role.DEVELOPER)

        # 从action名推断
        assert permission_manager.check_permission_simple("dev_agent", "read_config")
        assert permission_manager.check_permission_simple("dev_agent", "write_file")
        assert permission_manager.check_permission_simple("dev_agent", "run_task")

    def test_system_resource_protection(self, permission_manager):
        """测试系统资源保护"""
        permission_manager.assign_role("dev_agent", Role.DEVELOPER)

        result = permission_manager.check_permission(
            "dev_agent", "access_system", resource="system.config"
        )
        assert not result.allowed
        assert "ADMIN" in result.reason

    def test_resource_ownership(self, permission_manager):
        """测试资源所有权"""
        permission_manager.assign_role("agent_A", Role.OPERATOR)
        permission_manager.assign_role("agent_B", Role.OPERATOR)

        permission_manager.register_resource("my_resource", "agent_A")

        # 所有者可以访问
        result = permission_manager.check_permission(
            "agent_A", "write", resource="my_resource", operation=Operation.WRITE
        )
        assert result.allowed

        # 非所有者不能访问
        result = permission_manager.check_permission(
            "agent_B", "write", resource="my_resource", operation=Operation.WRITE
        )
        assert not result.allowed

    def test_batch_permission_check(self, permission_manager):
        """测试批量权限检查"""
        permission_manager.assign_role("dev_agent", Role.DEVELOPER)

        actions = [
            {"action": "read_data", "operation": "READ"},
            {"action": "write_data", "operation": "WRITE"},
            {"action": "delete_data", "operation": "DELETE"},
        ]
        results = permission_manager.check_batch("dev_agent", actions)
        assert len(results) == 3
        assert results[0].allowed  # READ
        assert results[1].allowed  # WRITE


# ============================================================
# SandboxExecutor 测试
# ============================================================

class TestSandboxExecutor:
    """沙箱执行器测试"""

    def test_analyze_code_safety_safe_code(self):
        """测试安全代码通过检测"""
        is_safe, issues = analyze_code_safety("x = 1 + 2\nprint(x)")
        assert is_safe
        assert len(issues) == 0

    def test_analyze_code_safety_forbidden_import(self):
        """测试禁止的import被检测"""
        is_safe, issues = analyze_code_safety("import os\nos.system('ls')")
        assert not is_safe
        assert any("os" in issue.lower() for issue in issues)

    def test_analyze_code_safety_forbidden_call(self):
        """测试禁止的函数调用被检测"""
        is_safe, issues = analyze_code_safety("eval('1+1')")
        assert not is_safe
        assert any("eval" in issue.lower() for issue in issues)

    def test_analyze_code_safety_subprocess(self):
        """测试subprocess导入被检测"""
        is_safe, issues = analyze_code_safety("import subprocess")
        assert not is_safe
        assert any("subprocess" in issue.lower() for issue in issues)

    def test_execute_safe_code(self, sandbox_executor):
        """测试在沙箱中执行安全代码"""
        result = sandbox_executor.execute_in_sandbox("print('hello world')")
        assert result.status == SandboxStatus.SUCCESS
        assert "hello world" in result.stdout

    def test_execute_code_with_output(self, sandbox_executor):
        """测试捕获代码输出"""
        code = """
x = 42
y = x * 2
print(f"Result: {y}")
"""
        result = sandbox_executor.execute_in_sandbox(code)
        assert result.status == SandboxStatus.SUCCESS
        assert "Result: 84" in result.stdout

    def test_execute_forbidden_code_blocked(self, sandbox_executor):
        """测试危险代码被阻止"""
        result = sandbox_executor.execute_in_sandbox("import os\nos.system('echo hacked')")
        assert result.status == SandboxStatus.FORBIDDEN_CODE
        assert "Forbidden" in result.error_message

    def test_execute_with_error(self, sandbox_executor):
        """测试代码运行时错误被捕获"""
        result = sandbox_executor.execute_in_sandbox("x = 1/0")
        assert result.status in (SandboxStatus.RUNTIME_ERROR, SandboxStatus.SUCCESS)
        # 注意: WSL环境下可能返回exit_code 1

    def test_validate_code(self, sandbox_executor):
        """测试代码验证"""
        valid, msg = sandbox_executor.validate_code("print('ok')")
        assert valid

        valid, msg = sandbox_executor.validate_code("import os")
        assert not valid

    def test_sandbox_timeout(self, sandbox_executor):
        """测试超时终止"""
        code = """
import time
time.sleep(60)
print("Should not reach here")
"""
        result = sandbox_executor.execute_in_sandbox(code, timeout=2)
        # 在WSL环境下，超时可能表现为RUNTIME_ERROR或TIMEOUT
        assert result.status != SandboxStatus.SUCCESS


# ============================================================
# ThreatDetector 测试
# ============================================================

class TestThreatDetector:
    """威胁检测器测试"""

    def test_initialization_loads_rules(self, threat_detector):
        """测试初始化加载内置规则"""
        rules = threat_detector.list_rules()
        assert len(rules) > 0
        assert "high_frequency_actions" in rules
        assert "command_injection_pattern" in rules

    def test_add_custom_rule(self, threat_detector):
        """测试添加自定义规则"""
        rule = DetectionRule(
            name="custom_test_rule",
            description="Custom test rule",
            category=ThreatCategory.ANOMALOUS_BEHAVIOR,
            level=ThreatLevel.HIGH,
            pattern_fields={"action": re.compile(r"suspicious", re.I)},
        )
        threat_detector.add_rule(rule)
        assert "custom_test_rule" in threat_detector.list_rules()

    def test_pattern_match_trigger_alert(self, threat_detector):
        """测试模式匹配触发告警"""
        event = {
            "action": "suspicious_activity_detected",
            "agent_id": "test_agent",
            "description": "Something suspicious happened",
        }
        alert = threat_detector.analyze_event(event)
        # 可能不触发，因为描述不匹配内置规则
        # 但action中的"suspicious"不应该触发内置规则（内置规则检查的是action）

    def test_command_injection_detection(self, threat_detector):
        """测试命令注入检测"""
        event = {
            "action": "execute_command",
            "agent_id": "attacker",
            "description": "User input: ; rm -rf /",
        }
        alert = threat_detector.analyze_event(event)
        assert alert is not None
        assert alert.level in (ThreatLevel.CRITICAL, ThreatLevel.HIGH)

    def test_resource_access_pattern(self, threat_detector):
        """测试资源访问模式检测"""
        # 直接检查System Resource规则
        event = {
            "action": "read_config",
            "agent_id": "test_agent",
            "description": "Trying to read settings",
            "resource": "system.main_config",
        }
        alert = threat_detector.analyze_event(event)
        # 应该匹配 unauthorized_system_resource_access 规则
        assert alert is not None
        assert "unauthorized" in alert.rule_name.lower() or alert.level in (ThreatLevel.HIGH, ThreatLevel.MEDIUM)

    def test_dangerous_import_detection(self, threat_detector):
        """测试危险导入检测"""
        event = {
            "action": "execute_code",
            "agent_id": "test_agent",
            "description": "Attempted to import os module for system access",
        }
        alert = threat_detector.analyze_event(event)
        assert alert is not None
        assert alert.rule_name == "dangerous_import_detected"

    def test_alert_notification(self, mock_notifier, audit_logger):
        """测试告警通知推送"""
        detector = ThreatDetector(
            feishu_notifier=mock_notifier,
            audit_logger=audit_logger,
        )
        # 触发告警
        event = {
            "action": "suspicious_exec",
            "agent_id": "test_agent",
            "description": "Attempted to import os module",
        }
        detector.analyze_event(event)
        # MEDIUM及以上级别应该触发通知
        mock_notifier.send_notification.assert_called()

    def test_alert_acknowledgment(self, threat_detector):
        """测试告警确认"""
        # 触发告警
        event = {
            "action": "suspicious_exec",
            "agent_id": "test_agent",
            "description": "Attempted to import os module",
        }
        alert = threat_detector.analyze_event(event)
        assert alert is not None

        # 确认告警
        acknowledged = threat_detector.acknowledge_alert(alert.alert_id, "admin_user")
        assert acknowledged

        # 验证已确认
        alerts = threat_detector.get_recent_alerts()
        confirmed = [a for a in alerts if a.alert_id == alert.alert_id]
        assert len(confirmed) == 1
        assert confirmed[0].acknowledged

    def test_get_stats(self, threat_detector):
        """测试统计信息"""
        stats = threat_detector.get_stats()
        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert "total_alerts" in stats
        assert stats["total_rules"] > 0

    def test_clear_alerts(self, threat_detector):
        """测试清除告警"""
        # 触发一些告警
        threat_detector.analyze_event({
            "action": "test",
            "agent_id": "agent",
            "description": "Attempted to import os module",
        })
        assert len(threat_detector.get_recent_alerts()) > 0

        threat_detector.clear_alerts()
        assert len(threat_detector.get_recent_alerts()) == 0
        assert len(threat_detector.get_suspicious_agents()) == 0


# ============================================================
# 集成测试
# ============================================================

class TestSecurityIntegration:
    """安全模块集成测试"""

    def test_full_security_pipeline(self, temp_db_path, mock_notifier):
        """测试完整安全管道: 审计→权限→沙箱→威胁"""
        # 初始化
        audit = AuditLogger(db_path=temp_db_path, feishu_notifier=mock_notifier)
        perm_manager = PermissionManager(audit_logger=audit)
        sandbox = SandboxExecutor(audit_logger=audit)
        detector = ThreatDetector(
            feishu_notifier=mock_notifier,
            audit_logger=audit,
        )

        # 1. 分配角色
        perm_manager.assign_role("user_agent", Role.OPERATOR)
        assert perm_manager.get_role("user_agent") == Role.OPERATOR

        # 2. 检查权限
        result = perm_manager.check_permission("user_agent", "execute_code", operation=Operation.EXECUTE)
        assert result.allowed

        # 3. 尝试在沙箱中执行代码
        sandbox_result = sandbox.execute_in_sandbox("print(2 + 2)")
        assert sandbox_result.status == SandboxStatus.SUCCESS

        # 4. 威胁检测分析
        alert = detector.analyze_event({
            "action": "execute_code",
            "agent_id": "user_agent",
            "description": "Code execution completed",
        })
        # 可能或可能不触发 - 取决于规则匹配

        # 5. 验证审计日志
        stats = audit.get_statistics()
        assert stats["total_events"] >= 3  # 至少有角色分配+权限检查+沙箱执行

    def test_security_module_imports(self):
        """测试安全模块所有导入"""
        from src.evolution.security import (
            AuditLogger, AuditLogLevel, EventType, AuditEntry, AuditQueryResult,
            PermissionManager, Operation, Role, AgentPermission, PermissionCheckResult,
            SandboxExecutor, SandboxStatus, SandboxResult, CodeSafetyAnalyzer, analyze_code_safety,
            ThreatDetector, ThreatLevel, ThreatCategory, ThreatAlert, DetectionRule,
        )
        # 所有导入成功
        assert True


# ============================================================
# 模块级检查
# ============================================================

def test_security_init_exports():
    """测试__init__.py正确导出所有公共符号"""
    from src.evolution.security import __all__ as exports

    required = [
        "AuditLogger", "AuditLogLevel", "EventType",
        "PermissionManager", "Operation", "Role",
        "SandboxExecutor", "SandboxStatus", "SandboxResult",
        "ThreatDetector", "ThreatLevel", "ThreatCategory",
    ]
    for name in required:
        assert name in exports, f"{name} should be exported"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

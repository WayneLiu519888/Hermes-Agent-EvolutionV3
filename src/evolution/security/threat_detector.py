"""
威胁检测器 - Hermes Agent Evolution 安全增强模块

基于规则的实时威胁检测引擎：
- 异常行为检测: 高频操作、异常模式匹配
- 基于规则的检测引擎，可扩展规则集
- 威胁等级: LOW/MEDIUM/HIGH/CRITICAL
- 告警生成和通知
- 与FeishuNotifier集成推送告警
- 与AuditLogger集成记录威胁事件
- 与SelfMonitor集成上报安全指标
"""

import logging
import re
import time
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Pattern, Tuple, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


# ============================================================
# 枚举和数据类
# ============================================================

class ThreatLevel(str, Enum):
    """威胁等级"""
    LOW = "LOW"          # 低威胁 — 记录即可
    MEDIUM = "MEDIUM"    # 中威胁 — 需要关注
    HIGH = "HIGH"        # 高威胁 — 需要响应
    CRITICAL = "CRITICAL" # 关键威胁 — 立即响应


class ThreatCategory(str, Enum):
    """威胁类别"""
    ANOMALOUS_BEHAVIOR = "ANOMALOUS_BEHAVIOR"    # 异常行为
    PRIVILEGE_ESCALATION = "PRIVILEGE_ESCALATION"  # 权限提升尝试
    DATA_EXFILTRATION = "DATA_EXFILTRATION"        # 数据外泄
    DENIAL_OF_SERVICE = "DENIAL_OF_SERVICE"        # 拒绝服务
    INJECTION_ATTACK = "INJECTION_ATTACK"          # 注入攻击
    RESOURCE_ABUSE = "RESOURCE_ABUSE"              # 资源滥用
    POLICY_VIOLATION = "POLICY_VIOLATION"          # 策略违规
    UNKNOWN_THREAT = "UNKNOWN_THREAT"              # 未知威胁


@dataclass
class ThreatAlert:
    """威胁告警"""
    alert_id: str = ""            # 告警唯一ID
    level: ThreatLevel = ThreatLevel.LOW
    category: ThreatCategory = ThreatCategory.UNKNOWN_THREAT
    title: str = ""
    description: str = ""
    source_agent_id: str = ""
    source_ip: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    rule_name: str = ""           # 触发的规则名
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    acknowledged: bool = False
    acknowledged_by: str = ""
    acknowledged_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "alert_id": self.alert_id,
            "level": self.level.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "source_agent_id": self.source_agent_id,
            "source_ip": self.source_ip,
            "evidence": self.evidence,
            "rule_name": self.rule_name,
            "detected_at": self.detected_at,
            "acknowledged": self.acknowledged,
        }


@dataclass
class DetectionRule:
    """检测规则"""
    name: str                           # 规则名称
    description: str = ""               # 规则描述
    category: ThreatCategory = ThreatCategory.UNKNOWN_THREAT
    level: ThreatLevel = ThreatLevel.MEDIUM
    enabled: bool = True                # 是否启用
    # 规则条件函数: (event_dict) → bool
    condition: Optional[Callable] = None
    # 模式匹配: 对事件字段的regex
    pattern_fields: Dict[str, Pattern] = field(default_factory=dict)
    # 阈值规则
    max_frequency: int = 0              # 时间窗口内最大频率
    frequency_window_seconds: int = 60  # 频率窗口(秒)
    cooldown_seconds: int = 60          # 同一规则告警冷却时间(秒)


# ============================================================
# 事件缓冲器（用于频率检测）
# ============================================================

@dataclass
class _EventBuffer:
    """按Agent分组的滑动窗口事件缓冲"""
    events: deque = field(default_factory=deque)
    last_alert_time: float = 0.0


# ============================================================
# ThreatDetector 主类
# ============================================================

class ThreatDetector:
    """威胁检测引擎

    基于规则匹配和频率分析检测安全威胁。
    支持自定义规则扩展和多种通知渠道。

    使用方式:
        detector = ThreatDetector(notifier=feishu, audit_logger=audit)
        detector.add_rule(my_rule)
        alert = detector.analyze_event({"action": "suspicious_action", ...})
    """

    def __init__(
        self,
        feishu_notifier=None,
        audit_logger=None,
        self_monitor=None,
        alert_history_size: int = 500,
    ):
        """初始化威胁检测器

        Args:
            feishu_notifier: FeishuNotifier实例，用于推送告警
            audit_logger: AuditLogger实例，用于记录威胁事件
            self_monitor: SelfMonitor实例，用于上报安全指标
            alert_history_size: 告警历史保留数量
        """
        self.feishu_notifier = feishu_notifier
        self.audit_logger = audit_logger
        self.self_monitor = self_monitor

        # 规则存储
        self._rules: Dict[str, DetectionRule] = {}

        # 频率检测缓冲区: key → _EventBuffer
        self._frequency_buffers: Dict[str, _EventBuffer] = defaultdict(_EventBuffer)

        # 告警历史
        self._alert_history: List[ThreatAlert] = []
        self._max_alert_history = alert_history_size

        # 告警计数器
        self._alert_counter: int = 0

        # 可疑IP/Agent集合
        self._suspicious_ips: Set[str] = set()
        self._suspicious_agents: Set[str] = set()

        # 初始化内置规则
        self._init_builtin_rules()

        logger.info("威胁检测器初始化完成，加载 %s 条检测规则", len(self._rules))

    def _init_builtin_rules(self):
        """初始化内置检测规则"""
        # 规则1: 高频操作检测
        self.add_rule(DetectionRule(
            name="high_frequency_actions",
            description="同一Agent在60秒内执行超过100次操作",
            category=ThreatCategory.DENIAL_OF_SERVICE,
            level=ThreatLevel.MEDIUM,
            max_frequency=100,
            frequency_window_seconds=60,
            cooldown_seconds=120,
        ))

        # 规则2: 权限提升检测
        self.add_rule(DetectionRule(
            name="privilege_escalation_attempt",
            description="非ADMIN角色尝试执行ADMIN级操作",
            category=ThreatCategory.PRIVILEGE_ESCALATION,
            level=ThreatLevel.HIGH,
            pattern_fields={
                "action": re.compile(r"assign_role|transfer_resource|configure_system", re.I),
            },
            cooldown_seconds=300,
        ))

        # 规则3: 危险模块导入检测
        self.add_rule(DetectionRule(
            name="dangerous_import_detected",
            description="检测到尝试导入危险模块（os/socket/subprocess等）",
            category=ThreatCategory.INJECTION_ATTACK,
            level=ThreatLevel.HIGH,
            pattern_fields={
                "description": re.compile(r"import.*(?:os|subprocess|socket|ctypes|shutil)", re.I),
            },
            cooldown_seconds=180,
        ))

        # 规则4: 大文件访问检测
        self.add_rule(DetectionRule(
            name="large_file_access",
            description="检测到访问超过100MB的文件",
            category=ThreatCategory.DATA_EXFILTRATION,
            level=ThreatLevel.MEDIUM,
            pattern_fields={
                "action": re.compile(r"read_file|download", re.I),
            },
            cooldown_seconds=300,
        ))

        # 规则5: 异常时间操作检测
        self.add_rule(DetectionRule(
            name="off_hours_activity",
            description="非工作时间（凌晨2-5点）的高敏感操作",
            category=ThreatCategory.ANOMALOUS_BEHAVIOR,
            level=ThreatLevel.LOW,
            cooldown_seconds=3600,
        ))

        # 规则6: 多次失败后的重试
        self.add_rule(DetectionRule(
            name="repeated_failures",
            description="同一操作短时间内失败超过5次",
            category=ThreatCategory.ANOMALOUS_BEHAVIOR,
            level=ThreatLevel.MEDIUM,
            max_frequency=5,
            frequency_window_seconds=30,
            cooldown_seconds=60,
            condition=self._check_repeated_failures,
        ))

        # 规则7: 关键资源未授权访问
        self.add_rule(DetectionRule(
            name="unauthorized_system_resource_access",
            description="尝试访问系统保留资源（system.*, internal.*, admin.*）",
            category=ThreatCategory.POLICY_VIOLATION,
            level=ThreatLevel.HIGH,
            pattern_fields={
                "resource": re.compile(r"^(system\.|internal\.|admin\.)"),
            },
            cooldown_seconds=180,
        ))

        # 规则8: 命令注入特征检测
        self.add_rule(DetectionRule(
            name="command_injection_pattern",
            description="检测shell命令注入特征（; | && || $() ``）",
            category=ThreatCategory.INJECTION_ATTACK,
            level=ThreatLevel.CRITICAL,
            pattern_fields={
                "description": re.compile(r"[;&|`$][\s]*[a-zA-Z]"),
            },
            cooldown_seconds=60,
        ))

    # ---- 规则管理 ----

    def add_rule(self, rule: DetectionRule) -> bool:
        """添加检测规则"""
        if rule.name in self._rules:
            logger.warning("规则已存在，将被覆盖: %s", rule.name)
        self._rules[rule.name] = rule
        logger.info("规则已注册: %s (等级: %s)", rule.name, rule.level.value)
        return True

    def remove_rule(self, rule_name: str) -> bool:
        """移除检测规则"""
        if rule_name in self._rules:
            del self._rules[rule_name]
            return True
        return False

    def get_rule(self, rule_name: str) -> Optional[DetectionRule]:
        """获取规则"""
        return self._rules.get(rule_name)

    def list_rules(self) -> Dict[str, DetectionRule]:
        """列出所有规则"""
        return dict(self._rules)

    # ---- 事件分析 ----

    def analyze_event(self, event: Dict[str, Any]) -> Optional[ThreatAlert]:
        """分析单个事件是否触发威胁规则

        Args:
            event: 事件字典，至少包含:
                - action: 操作名称
                - agent_id: 来源Agent
                可选: description, level, resource, outcome等

        Returns:
            Optional[ThreatAlert]: 触发的告警，如无威胁返回None
        """
        triggered_alerts: List[ThreatAlert] = []

        for rule_name, rule in self._rules.items():
            if not rule.enabled:
                continue

            # 检查频率限制
            if rule.max_frequency > 0:
                if self._check_frequency(event, rule):
                    alert = self._create_alert(rule, event, "Frequency threshold exceeded")
                    triggered_alerts.append(alert)
                    continue

            # 检查自定义条件函数
            if rule.condition and rule.condition(event):
                alert = self._create_alert(rule, event, "Custom condition matched")
                triggered_alerts.append(alert)
                continue

            # 检查模式匹配
            if rule.pattern_fields:
                if self._check_patterns(event, rule):
                    alert = self._create_alert(rule, event, "Pattern matched")
                    triggered_alerts.append(alert)
                    continue

            # 检查非工作时间规则
            if rule.name == "off_hours_activity":
                if self._check_off_hours(event):
                    alert = self._create_alert(rule, event, "Off-hours activity detected")
                    triggered_alerts.append(alert)

        # 返回最高级别告警
        if triggered_alerts:
            # 按威胁等级排序，返回最高级别
            level_order = {ThreatLevel.LOW: 0, ThreatLevel.MEDIUM: 1, ThreatLevel.HIGH: 2, ThreatLevel.CRITICAL: 3}
            best_alert = max(triggered_alerts, key=lambda a: (level_order.get(a.level, 0), a.detected_at))
            self._record_alert(best_alert)
            return best_alert

        return None

    def analyze_batch(self, events: List[Dict[str, Any]]) -> List[ThreatAlert]:
        """批量分析事件"""
        alerts = []
        for event in events:
            alert = self.analyze_event(event)
            if alert:
                alerts.append(alert)
        return alerts

    # ---- 检测方法 ----

    def _check_frequency(self, event: Dict[str, Any], rule: DetectionRule) -> bool:
        """频率检测"""
        agent_id = event.get("agent_id", "unknown")
        key = f"{rule.name}:{agent_id}"

        buffer = self._frequency_buffers[key]
        now = time.time()

        # 清理过期事件
        window = rule.frequency_window_seconds
        while buffer.events and buffer.events[0] < now - window:
            buffer.events.popleft()

        # 检查冷却时间
        if buffer.last_alert_time and (now - buffer.last_alert_time) < rule.cooldown_seconds:
            return False

        buffer.events.append(now)

        if len(buffer.events) >= rule.max_frequency:
            buffer.last_alert_time = now
            return True

        return False

    def _check_patterns(self, event: Dict[str, Any], rule: DetectionRule) -> bool:
        """检查正则模式匹配"""
        for field, pattern in rule.pattern_fields.items():
            value = event.get(field, "")
            if isinstance(value, str) and pattern.search(value):
                return True
        return False

    def _check_off_hours(self, event: Dict[str, Any]) -> bool:
        """检查是否在非工作时间（凌晨2-5点）"""
        now = datetime.now()
        if 2 <= now.hour < 5:
            # 检查是否为高敏感操作
            action = event.get("action", "")
            sensitive_keywords = ("config", "admin", "delete", "assign_role", "security")
            if any(kw in action.lower() for kw in sensitive_keywords):
                return True
        return False

    def _check_repeated_failures(self, event: Dict[str, Any]) -> bool:
        """检查是否为重复失败"""
        return event.get("outcome") == "failure"

    # ---- 告警管理 ----

    def _create_alert(
        self, rule: DetectionRule, event: Dict[str, Any], trigger_reason: str
    ) -> ThreatAlert:
        """创建告警对象"""
        self._alert_counter += 1
        alert_id = f"THREAT-{datetime.now().strftime('%Y%m%d')}-{self._alert_counter:04d}"

        return ThreatAlert(
            alert_id=alert_id,
            level=rule.level,
            category=rule.category,
            title=f"[{rule.level.value}] {rule.name}",
            description=f"{rule.description}\nTrigger: {trigger_reason}",
            source_agent_id=event.get("agent_id", "unknown"),
            source_ip=event.get("ip_address", ""),
            evidence={
                "event": {k: str(v)[:200] for k, v in event.items()},
                "rule": rule.name,
                "trigger_reason": trigger_reason,
            },
            rule_name=rule.name,
        )

    def _record_alert(self, alert: ThreatAlert):
        """记录告警并触发通知"""
        # 加入历史
        self._alert_history.append(alert)
        if len(self._alert_history) > self._max_alert_history:
            self._alert_history = self._alert_history[-self._max_alert_history:]

        # 记录可疑Agent/IP
        if alert.source_agent_id:
            self._suspicious_agents.add(alert.source_agent_id)
        if alert.source_ip:
            self._suspicious_ips.add(alert.source_ip)

        # 审计记录
        if self.audit_logger:
            log_level = {
                ThreatLevel.LOW: "INFO",
                ThreatLevel.MEDIUM: "WARNING",
                ThreatLevel.HIGH: "ERROR",
                ThreatLevel.CRITICAL: "CRITICAL",
            }.get(alert.level, "WARNING")

            self.audit_logger.log_event(
                event_type="SECURITY",
                level=log_level,
                agent_id=alert.source_agent_id,
                action=f"threat_detected:{alert.rule_name}",
                description=f"[{alert.level.value}] {alert.title}: {alert.description[:200]}",
                details=alert.evidence,
                source_module="threat_detector",
                correlation_id=alert.alert_id,
                outcome="failure",
            )

        # 飞书通知（MEDIUM及以上）
        if self.feishu_notifier and alert.level in (
            ThreatLevel.MEDIUM, ThreatLevel.HIGH, ThreatLevel.CRITICAL
        ):
            self._push_feishu_alert(alert)

        # SelfMonitor指标上报
        if self.self_monitor and hasattr(self.self_monitor, 'observer'):
            try:
                self.self_monitor.observer.record_experience(
                    experience_type="THREAT_DETECTED",
                    description=f"Threat: [{alert.level.value}] {alert.title}",
                    outcome="failure",
                    metrics={
                        "threat_level": alert.level.value,
                        "category": alert.category.value,
                    },
                    context={"alert_id": alert.alert_id},
                )
            except Exception:
                pass

        logger.warning(
            "⚠️ 威胁告警 #%s: [%s] %s — %s",
            alert.alert_id, alert.level.value, alert.category.value, alert.title
        )

    def _push_feishu_alert(self, alert: ThreatAlert):
        """推送告警到飞书"""
        try:
            level_emoji = {
                ThreatLevel.LOW: "ℹ️",
                ThreatLevel.MEDIUM: "⚠️",
                ThreatLevel.HIGH: "🔴",
                ThreatLevel.CRITICAL: "🚨",
            }
            emoji = level_emoji.get(alert.level, "⚠️")

            content = (
                f"{emoji} **安全威胁告警**\n\n"
                f"**告警ID:** {alert.alert_id}\n"
                f"**等级:** {alert.level.value}\n"
                f"**类别:** {alert.category.value}\n"
                f"**标题:** {alert.title}\n"
                f"**描述:** {alert.description}\n"
                f"**来源Agent:** {alert.source_agent_id}\n"
                f"**来源IP:** {alert.source_ip or 'N/A'}\n"
                f"**检测规则:** {alert.rule_name}\n"
                f"**时间:** {alert.detected_at}\n"
            )

            if alert.evidence:
                evidence_str = str(alert.evidence.get("event", {}))[:300]
                content += f"\n**证据:**\n```\n{evidence_str}\n```"

            self.feishu_notifier.send_notification(
                title=f"{emoji} 安全告警: {alert.title}",
                content=content,
                level="error" if alert.level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL) else "warning",
            )
        except Exception as e:
            logger.error("飞书告警推送失败: %s", e)

    # ---- 查询方法 ----

    def get_recent_alerts(self, limit: int = 50) -> List[ThreatAlert]:
        """获取最近的告警"""
        return self._alert_history[-limit:]

    def get_alerts_by_level(self, level: ThreatLevel) -> List[ThreatAlert]:
        """按等级获取告警"""
        return [a for a in self._alert_history if a.level == level]

    def get_suspicious_agents(self) -> List[str]:
        """获取可疑Agent列表"""
        return list(self._suspicious_agents)

    def get_suspicious_ips(self) -> List[str]:
        """获取可疑IP列表"""
        return list(self._suspicious_ips)

    def get_stats(self) -> Dict[str, Any]:
        """获取检测统计信息"""
        alert_counts = defaultdict(int)
        for alert in self._alert_history:
            alert_counts[alert.level.value] += 1

        return {
            "total_rules": len(self._rules),
            "enabled_rules": sum(1 for r in self._rules.values() if r.enabled),
            "total_alerts": len(self._alert_history),
            "alerts_by_level": dict(alert_counts),
            "suspicious_agents": len(self._suspicious_agents),
            "suspicious_ips": len(self._suspicious_ips),
            "last_alert": self._alert_history[-1].detected_at if self._alert_history else None,
            "generated_at": datetime.now().isoformat(),
        }

    def acknowledge_alert(self, alert_id: str, acknowledged_by: str = "system") -> bool:
        """确认告警"""
        for alert in self._alert_history:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_by = acknowledged_by
                alert.acknowledged_at = datetime.now().isoformat()
                logger.info("告警已确认: %s by %s", alert_id, acknowledged_by)
                return True
        return False

    def clear_alerts(self):
        """清除告警历史"""
        self._alert_history.clear()
        self._suspicious_agents.clear()
        self._suspicious_ips.clear()
        self._alert_counter = 0
        self._frequency_buffers.clear()

    def __repr__(self) -> str:
        return f"ThreatDetector(rules={len(self._rules)}, alerts={len(self._alert_history)})"

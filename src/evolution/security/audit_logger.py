"""
审计日志系统 - Hermes Agent Evolution 安全增强模块

记录所有关键操作到SQLite数据库，支持：
- 多级日志 (INFO/WARNING/ERROR/CRITICAL)
- 事件类型分类 (AGENT_ACTION, TOOL_EXECUTION, SYSTEM_CONFIG, COLLABORATION, EVOLUTION)
- 时间范围查询和事件类型过滤
- 自动轮转归档 (超过10000条记录)
- 与SelfMonitor集成上报安全指标
- 与FeishuNotifier集成推关关键告警
"""

import sqlite3
import json
import os
import shutil
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Set, Union
import threading

from ..db_utils import get_evolution_db
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# ============================================================
# 枚举定义
# ============================================================

class AuditLogLevel(str, Enum):
    """审计日志级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_string(cls, s: str) -> "AuditLogLevel":
        try:
            return cls(s.upper())
        except ValueError:
            return cls.INFO


class EventType(str, Enum):
    """审计事件类型"""
    AGENT_ACTION = "AGENT_ACTION"        # Agent执行的操作
    TOOL_EXECUTION = "TOOL_EXECUTION"    # 工具调用
    SYSTEM_CONFIG = "SYSTEM_CONFIG"      # 系统配置变更
    COLLABORATION = "COLLABORATION"      # 协作事件
    EVOLUTION = "EVOLUTION"              # 进化相关操作
    SECURITY = "SECURITY"                # 安全相关事件


# ============================================================
# 数据类
# ============================================================

@dataclass
class AuditEntry:
    """审计日志条目"""
    id: Optional[int] = None
    event_type: str = EventType.AGENT_ACTION.value
    level: str = AuditLogLevel.INFO.value
    agent_id: str = "system"
    action: str = ""
    description: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    source_module: str = ""
    ip_address: str = ""
    correlation_id: str = ""
    outcome: str = "success"  # success, failure, pending
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["details"] = json.dumps(self.details, ensure_ascii=False) if self.details else "{}"
        return d

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AuditEntry":
        d = dict(row)
        details_str = d.pop("details", "{}")
        try:
            d["details"] = json.loads(details_str) if isinstance(details_str, str) else details_str
        except (json.JSONDecodeError, TypeError):
            d["details"] = {}
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


@dataclass
class AuditQueryResult:
    """审计查询结果"""
    entries: List[AuditEntry]
    total_count: int
    query_params: Dict[str, Any] = field(default_factory=dict)
    generated_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# AuditLogger 主类
# ============================================================

class AuditLogger:
    """审计日志记录器

    持久化审计日志到SQLite，支持自动轮转、时间范围查询、
    事件类型过滤、以及外部通知集成。
    """

    DEFAULT_DB_PATH = "data/audit.db"
    ARCHIVE_DIR = "data/audit_archives"
    MAX_RECORDS = 10_000  # 超过此数量触发归档

    def __init__(self, db_path: str = None, feishu_notifier=None, self_monitor=None):
        """
        Args:
            db_path: SQLite数据库路径，默认 data/audit.db
            feishu_notifier: 可选FeishuNotifier实例，用于推送关键告警
            self_monitor: 可选SelfMonitor实例，用于上报安全指标
        """
        self.db_path = db_path or self.DEFAULT_DB_PATH
        self.feishu_notifier = feishu_notifier
        self.self_monitor = self_monitor
        self._connection: Optional[sqlite3.Connection] = None
        self._ensure_data_dir()
        self._init_database()

    def _ensure_data_dir(self):
        """确保数据目录存在"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
        os.makedirs(self.ARCHIVE_DIR, exist_ok=True)

    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文管理器 (V5-P0: 由 DatabasePool 管理，不关闭连接)"""
        conn = get_evolution_db(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def _init_database(self):
        """初始化数据库表结构和索引"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL DEFAULT 'AGENT_ACTION',
                    level TEXT NOT NULL DEFAULT 'INFO',
                    agent_id TEXT NOT NULL DEFAULT 'system',
                    action TEXT NOT NULL DEFAULT '',
                    description TEXT DEFAULT '',
                    details TEXT DEFAULT '{}',
                    source_module TEXT DEFAULT '',
                    ip_address TEXT DEFAULT '',
                    correlation_id TEXT DEFAULT '',
                    outcome TEXT DEFAULT 'success',
                    created_at TEXT NOT NULL
                )
            """)

            # 创建索引加速查询
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_created_at
                    ON audit_logs(created_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_event_type
                    ON audit_logs(event_type)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_level
                    ON audit_logs(level)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_agent_id
                    ON audit_logs(agent_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_correlation_id
                    ON audit_logs(correlation_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_audit_event_level_time
                    ON audit_logs(event_type, level, created_at)
            """)

            logger.info("审计日志数据库初始化完成: %s", self.db_path)

    # ---- 写入方法 ----

    def log_event(
        self,
        event_type: Union[EventType, str],
        level: Union[AuditLogLevel, str] = AuditLogLevel.INFO,
        agent_id: str = "system",
        action: str = "",
        description: str = "",
        details: Dict[str, Any] = None,
        source_module: str = "",
        ip_address: str = "",
        correlation_id: str = "",
        outcome: str = "success",
    ) -> Optional[int]:
        """记录一条审计事件

        Args:
            event_type: 事件类型 (EventType枚举或字符串)
            level: 日志级别
            agent_id: 执行操作的Agent标识
            action: 操作名称
            description: 描述信息
            details: 附加详情字典
            source_module: 来源模块名
            ip_address: 来源IP
            correlation_id: 关联ID（用于追踪跨组件操作链）
            outcome: 操作结果 (success/failure/pending)

        Returns:
            Optional[int]: 记录的ID，失败返回None
        """
        try:
            event_type_str = event_type.value if isinstance(event_type, EventType) else str(event_type)
            level_str = level.value if isinstance(level, AuditLogLevel) else AuditLogLevel.from_string(str(level)).value

            entry = AuditEntry(
                event_type=event_type_str,
                level=level_str,
                agent_id=agent_id,
                action=action,
                description=description,
                details=details or {},
                source_module=source_module,
                ip_address=ip_address,
                correlation_id=correlation_id,
                outcome=outcome,
            )

            with self._get_connection() as conn:
                cursor = conn.cursor()
                entry_dict = entry.to_dict()
                entry_dict.pop("id", None)  # 自动生成

                columns = ", ".join(entry_dict.keys())
                placeholders = ", ".join("?" for _ in entry_dict)
                values = list(entry_dict.values())

                cursor.execute(
                    f"INSERT INTO audit_logs ({columns}) VALUES ({placeholders})",
                    values
                )
                record_id = cursor.lastrowid

            # 检查是否需要轮转
            self._check_rotation()

            # CRITICAL级别推送通知
            if level_str == AuditLogLevel.CRITICAL.value and self.feishu_notifier:
                self._push_critical_alert(entry, record_id)

            # 上报安全指标给SelfMonitor
            if self.self_monitor:
                self._report_security_metric(event_type_str, level_str)

            logger.debug("审计日志记录 #%s: [%s] %s - %s", record_id, level_str, event_type_str, action)
            return record_id

        except Exception as e:
            logger.error("审计日志写入失败: %s", e)
            return None

    def log_batch(self, entries: List[AuditEntry]) -> int:
        """批量记录审计事件

        Returns:
            int: 成功记录的数量
        """
        success_count = 0
        for entry in entries:
            rid = self.log_event(
                event_type=entry.event_type,
                level=entry.level,
                agent_id=entry.agent_id,
                action=entry.action,
                description=entry.description,
                details=entry.details,
                source_module=entry.source_module,
                ip_address=entry.ip_address,
                correlation_id=entry.correlation_id,
                outcome=entry.outcome,
            )
            if rid is not None:
                success_count += 1
        return success_count

    # ---- 查询方法 ----

    def query(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        event_type: Optional[Union[EventType, str]] = None,
        level: Optional[Union[AuditLogLevel, str]] = None,
        agent_id: Optional[str] = None,
        action: Optional[str] = None,
        outcome: Optional[str] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        order_desc: bool = True,
    ) -> AuditQueryResult:
        """查询审计日志

        支持多维度过滤和时间范围查询。

        Args:
            start_time: 开始时间 ISO格式字符串
            end_time: 结束时间 ISO格式字符串
            event_type: 按事件类型过滤
            level: 按日志级别过滤
            agent_id: 按Agent ID过滤
            action: 按操作名称过滤
            outcome: 按结果过滤
            correlation_id: 按关联ID过滤
            limit: 返回记录数上限
            offset: 分页偏移
            order_desc: 是否按时间倒序

        Returns:
            AuditQueryResult: 查询结果
        """
        conditions = []
        params: List[Any] = []

        if start_time:
            conditions.append("created_at >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("created_at <= ?")
            params.append(end_time)
        if event_type:
            et = event_type.value if isinstance(event_type, EventType) else str(event_type)
            conditions.append("event_type = ?")
            params.append(et)
        if level:
            lv = level.value if isinstance(level, AuditLogLevel) else AuditLogLevel.from_string(str(level)).value
            conditions.append("level = ?")
            params.append(lv)
        if agent_id:
            conditions.append("agent_id = ?")
            params.append(agent_id)
        if action:
            conditions.append("action LIKE ?")
            params.append(f"%{action}%")
        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome)
        if correlation_id:
            conditions.append("correlation_id = ?")
            params.append(correlation_id)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        order = "DESC" if order_desc else "ASC"

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 计数查询
                cursor.execute(f"SELECT COUNT(*) FROM audit_logs WHERE {where_clause}", params)
                total_count = cursor.fetchone()[0]

                # 数据查询
                cursor.execute(
                    f"SELECT * FROM audit_logs WHERE {where_clause} ORDER BY created_at {order} LIMIT ? OFFSET ?",
                    params + [limit, offset]
                )
                rows = cursor.fetchall()
                entries = [AuditEntry.from_row(row) for row in rows]

            return AuditQueryResult(
                entries=entries,
                total_count=total_count,
                query_params={
                    "start_time": start_time,
                    "end_time": end_time,
                    "event_type": str(event_type) if event_type else None,
                    "level": str(level) if level else None,
                    "agent_id": agent_id,
                    "limit": limit,
                    "offset": offset,
                }
            )

        except Exception as e:
            logger.error("审计日志查询失败: %s", e)
            return AuditQueryResult(entries=[], total_count=0)

    def query_recent(self, hours: int = 24, limit: int = 100) -> AuditQueryResult:
        """查询最近N小时的审计日志"""
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        return self.query(start_time=start_time, limit=limit)

    def get_event_by_id(self, record_id: int) -> Optional[AuditEntry]:
        """根据ID获取单条审计记录"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM audit_logs WHERE id = ?", (record_id,))
                row = cursor.fetchone()
                if row:
                    return AuditEntry.from_row(row)
            return None
        except Exception as e:
            logger.error("获取审计记录失败: %s", e)
            return None

    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """获取审计日志统计信息"""
        start_time = (datetime.now() - timedelta(hours=hours)).isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()

                # 总数
                cursor.execute(
                    "SELECT COUNT(*) FROM audit_logs WHERE created_at >= ?",
                    (start_time,)
                )
                total = cursor.fetchone()[0]

                # 按级别统计
                cursor.execute(
                    "SELECT level, COUNT(*) as cnt FROM audit_logs WHERE created_at >= ? GROUP BY level",
                    (start_time,)
                )
                level_stats = {row["level"]: row["cnt"] for row in cursor.fetchall()}

                # 按事件类型统计
                cursor.execute(
                    "SELECT event_type, COUNT(*) as cnt FROM audit_logs WHERE created_at >= ? GROUP BY event_type",
                    (start_time,)
                )
                type_stats = {row["event_type"]: row["cnt"] for row in cursor.fetchall()}

                # 失败率
                cursor.execute(
                    "SELECT COUNT(*) FROM audit_logs WHERE created_at >= ? AND outcome = 'failure'",
                    (start_time,)
                )
                failures = cursor.fetchone()[0]

                # 数据库总大小
                cursor.execute("SELECT COUNT(*) FROM audit_logs")
                total_all_time = cursor.fetchone()[0]

            return {
                "period_hours": hours,
                "total_events": total,
                "total_all_time": total_all_time,
                "by_level": level_stats,
                "by_event_type": type_stats,
                "failure_count": failures,
                "failure_rate": round(failures / max(total, 1), 4),
                "generated_at": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error("获取统计信息失败: %s", e)
            return {"error": str(e)}

    # ---- 轮转管理 ----

    def _check_rotation(self):
        """检查并触发日志轮转"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM audit_logs")
                count = cursor.fetchone()[0]

            if count >= self.MAX_RECORDS:
                self._rotate_logs(count)
        except Exception as e:
            logger.error("日志轮转检查失败: %s", e)

    def _rotate_logs(self, current_count: int):
        """执行日志归档轮转

        将最旧的一半记录移到归档数据库。
        """
        logger.warning("触发审计日志轮转，当前记录数: %s (阈值: %s)", current_count, self.MAX_RECORDS)
        archive_path = os.path.join(
            self.ARCHIVE_DIR,
            f"audit_archive_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        )

        try:
            # 确定要归档的记录数（保留约一半）
            keep_count = self.MAX_RECORDS // 2
            archive_count = current_count - keep_count

            with self._get_connection() as conn:
                cursor = conn.cursor()
                # 获取要归档的最旧记录的截止ID
                cursor.execute(
                    "SELECT id FROM audit_logs ORDER BY id ASC LIMIT 1 OFFSET ?",
                    (archive_count,)
                )
                row = cursor.fetchone()
                if row is None:
                    return
                cutoff_id = row["id"]

                # 创建归档数据库
                archive_conn = get_evolution_db(archive_path)
                try:
                    # 复制表结构
                    conn.backup(archive_conn)  # 先完整备份
                    # V5-P0: archive_conn 由 DatabasePool 管理，不 close

                    # 删除已归档的记录
                    cursor.execute("DELETE FROM audit_logs WHERE id < ?", (cutoff_id,))
                    conn.commit()
                except Exception:
                    raise

            logger.info(
                "审计日志归档完成: 归档 %s 条 → %s, 保留 %s 条",
                archive_count, archive_path, keep_count
            )

        except Exception as e:
            logger.error("日志轮转失败: %s", e)
            raise

    def force_rotate(self) -> bool:
        """强制执行日志轮转"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM audit_logs")
                count = cursor.fetchone()[0]
            self._rotate_logs(count)
            return True
        except Exception as e:
            logger.error("强制轮转失败: %s", e)
            return False

    def get_record_count(self) -> int:
        """获取当前记录总数"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM audit_logs")
                return cursor.fetchone()[0]
        except Exception:
            return 0

    # ---- 通知和集成 ----

    def _push_critical_alert(self, entry: AuditEntry, record_id: Optional[int]):
        """推送关键告警到飞书"""
        try:
            content = (
                f"**🔴 关键安全事件 #{record_id}**\n\n"
                f"**事件类型:** {entry.event_type}\n"
                f"**操作:** {entry.action}\n"
                f"**描述:** {entry.description}\n"
                f"**Agent:** {entry.agent_id}\n"
                f"**来源模块:** {entry.source_module}\n"
                f"**时间:** {entry.created_at}\n"
                f"**结果:** {entry.outcome}\n"
            )
            if entry.details:
                details_str = json.dumps(entry.details, ensure_ascii=False, indent=2)
                content += f"\n**详情:**\n```json\n{details_str[:500]}\n```"

            self.feishu_notifier.send_notification(
                title=f"🚨 安全告警: {entry.action}",
                content=content,
                level="error"
            )
        except Exception as e:
            logger.error("推送关键告警失败: %s", e)

    def _report_security_metric(self, event_type: str, level: str):
        """向SelfMonitor上报安全指标"""
        try:
            # SelfMonitor 通过 observer 记录，这里做简单的事件计数
            if hasattr(self.self_monitor, 'observer'):
                observer = self.self_monitor.observer
                if hasattr(observer, 'record_experience'):
                    observer.record_experience(
                        experience_type="SECURITY_EVENT",
                        description=f"Security audit: [{level}] {event_type}",
                        outcome="success" if level != "CRITICAL" else "failure",
                        metrics={"event_type": event_type, "level": level},
                        context={"module": "audit_logger"}
                    )
        except Exception:
            pass  # 静默失败，不影响主流程

    # ---- 清除方法 ----

    def purge_old_entries(self, days: int = 90) -> int:
        """清除超过指定天数的日志归档

        Args:
            days: 保留天数，默认90天

        Returns:
            int: 清除的归档文件数
        """
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        try:
            for fname in os.listdir(self.ARCHIVE_DIR):
                fpath = os.path.join(self.ARCHIVE_DIR, fname)
                if os.path.isfile(fpath) and fname.startswith("audit_archive_"):
                    mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                    if mtime < cutoff:
                        os.remove(fpath)
                        removed += 1
                        logger.info("清除过期归档: %s", fname)
            return removed
        except Exception as e:
            logger.error("清除过期归档失败: %s", e)
            return removed

    def close(self):
        """关闭所有数据库连接（预留）"""
        pass  # 使用 contextmanager，每次操作后自动关闭

    def __repr__(self) -> str:
        return f"AuditLogger(db_path='{self.db_path}', records={self.get_record_count()})"

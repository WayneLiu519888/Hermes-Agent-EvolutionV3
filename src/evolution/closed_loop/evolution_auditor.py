"""
Evolution Auditor — 自进化审计器

持久化记录每次进化周期的完整信息，支持历史查询和趋势分析。

数据库: evolution_audit.db (位于 ~/.hermes/data/evolution/)
表:
  - evolution_cycles: 每次进化周期的元数据
  - evolution_actions: 每个进化动作的详情
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from ..db_utils import get_evolution_db

logger = logging.getLogger(__name__)


# ── 数据库初始化 ────────────────────────────────────────────────────────────────

CREATE_CYCLES_TABLE = """
CREATE TABLE IF NOT EXISTS evolution_cycles (
    cycle_id          INTEGER PRIMARY KEY,
    started_at        DATETIME NOT NULL,
    finished_at       DATETIME,
    duration_ms       REAL DEFAULT 0,
    success           INTEGER DEFAULT 1,
    trigger           TEXT DEFAULT 'manual',

    phase_monitor     TEXT DEFAULT 'pending',
    phase_analyze     TEXT DEFAULT 'pending',
    phase_plan        TEXT DEFAULT 'pending',
    phase_execute     TEXT DEFAULT 'pending',
    phase_verify      TEXT DEFAULT 'pending',
    phase_feedback    TEXT DEFAULT 'pending',

    health_score_before   REAL,
    success_rate_before   REAL,
    tools_count_before    INTEGER,
    experiences_before    INTEGER,

    health_score_after    REAL,
    success_rate_after    REAL,
    tools_count_after     INTEGER,
    experiences_after     INTEGER,

    issues_found          INTEGER DEFAULT 0,
    patterns_discovered   INTEGER DEFAULT 0,
    issues_details        TEXT,
    patterns_details      TEXT,
    actions_planned       INTEGER DEFAULT 0,
    actions_executed      INTEGER DEFAULT 0,
    actions_succeeded     INTEGER DEFAULT 0,
    improvements_detected INTEGER DEFAULT 0,
    errors_count          INTEGER DEFAULT 0,

    improvement_summary   TEXT,
    error_summary         TEXT,
    notes                 TEXT
)
"""

CREATE_ACTIONS_TABLE = """
CREATE TABLE IF NOT EXISTS evolution_actions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id      INTEGER NOT NULL REFERENCES evolution_cycles(cycle_id),
    action_type   TEXT NOT NULL,
    target        TEXT,
    description   TEXT,
    phase         TEXT,
    before_state  TEXT,
    after_state   TEXT,
    success       INTEGER DEFAULT 1,
    error_message TEXT,
    duration_ms   REAL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
)
"""

CREATE_CYCLES_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_cycles_started ON evolution_cycles(started_at)",
    "CREATE INDEX IF NOT EXISTS idx_cycles_success ON evolution_cycles(success)",
]

CREATE_ACTIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_actions_cycle ON evolution_actions(cycle_id)",
    "CREATE INDEX IF NOT EXISTS idx_actions_type   ON evolution_actions(action_type)",
]


class EvolutionAuditor:
    """自进化审计器"""

    def __init__(self, db_path: str = "evolution_audit.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        """初始化数据库表结构"""
        conn = get_evolution_db(self.db_path)
        conn.execute(CREATE_CYCLES_TABLE)
        conn.execute(CREATE_ACTIONS_TABLE)
        for idx_sql in CREATE_CYCLES_INDEXES:
            conn.execute(idx_sql)
        for idx_sql in CREATE_ACTIONS_INDEXES:
            conn.execute(idx_sql)
        # 🆕 兼容迁移：为旧数据库新增 issues_details / patterns_details 列
        self._migrate_add_column(conn, "evolution_cycles", "issues_details", "TEXT")
        self._migrate_add_column(conn, "evolution_cycles", "patterns_details", "TEXT")
        conn.commit()
        logger.debug("EvolutionAuditor 数据库初始化完成")

    @staticmethod
    def _migrate_add_column(conn, table: str, column: str, col_type: str):
        """安全添加列（列已存在时忽略）"""
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
        except Exception:
            pass  # 列已存在

    # ── 写入 ──────────────────────────────────────────────────────────────

    def _next_cycle_id(self) -> int:
        """获取下一个可用的 cycle_id（当前最大 + 1）"""
        try:
            conn = get_evolution_db(self.db_path)
            row = conn.execute("SELECT COALESCE(MAX(cycle_id), 0) + 1 FROM evolution_cycles").fetchone()
            return int(row[0]) if row else 1
        except Exception:
            return 1

    def record_cycle(self, result: Dict[str, Any],
                     trigger: str = "manual",
                     health_before: Optional[Dict] = None,
                     health_after: Optional[Dict] = None) -> int:
        """
        记录一次完整的进化周期。

        Args:
            result: orchestrator.run_full_cycle() 的返回值
            trigger: 触发方式 (manual/scheduled/auto/hook)
            health_before: 进化前健康快照 (可选)
            health_after: 进化后健康快照 (可选)

        Returns:
            cycle_id
        """
        cycle_id = result.get("cycle_id", 0)
        phases = result.get("phases", {})

        # 阶段状态
        phase_status = {}
        for pname in ("monitor", "analyze", "plan", "execute", "verify", "feedback"):
            phase_data = phases.get(pname, {})
            if pname == "monitor":
                phase_status[pname] = "completed" if phase_data.get("metrics_count", 0) > 0 else "failed"
            elif pname == "feedback":
                phase_status[pname] = "completed" if phase_data.get("recorded") else "failed"
            else:
                phase_status[pname] = "completed"

        # before/after 指标
        hb = health_before or {}
        ha = health_after or {}

        # 改进摘要 JSON
        verify_phase = phases.get("verify", {})
        improvements = verify_phase.get("improvements", [])
        if isinstance(improvements, list):
            improvement_json = json.dumps(improvements[:20], ensure_ascii=False) if improvements else None
        else:
            improvement_json = None

        # 错误摘要
        errors = result.get("errors", [])
        error_json = json.dumps(errors[:20], ensure_ascii=False) if errors else None

        # 🆕 分析详情：从 phases.analyze._details 提取 issues/patterns 分别存储
        analyze_details = phases.get("analyze", {}).get("_details", {})
        issues_json = json.dumps(analyze_details['issues'], ensure_ascii=False) if analyze_details.get("issues") else None
        patterns_json = json.dumps(analyze_details['patterns'], ensure_ascii=False) if analyze_details.get("patterns") else None
        # notes 保留完整上下文（含 issues + patterns，向前兼容）
        notes_parts = []
        if issues_json:
            notes_parts.append(f"[ISSUES] {issues_json}")
        if patterns_json:
            notes_parts.append(f"[PATTERNS] {patterns_json}")
        notes = "\n".join(notes_parts) if notes_parts else None

        try:
            conn = get_evolution_db(self.db_path)
            conn.execute("""
                INSERT OR REPLACE INTO evolution_cycles (
                    cycle_id, started_at, finished_at, duration_ms, success, trigger,
                    phase_monitor, phase_analyze, phase_plan, phase_execute, phase_verify, phase_feedback,
                    health_score_before, success_rate_before, tools_count_before, experiences_before,
                    health_score_after, success_rate_after, tools_count_after, experiences_after,
                    issues_found, patterns_discovered,
                    issues_details, patterns_details,
                    actions_planned, actions_executed,
                    actions_succeeded, improvements_detected, errors_count,
                    improvement_summary, error_summary, notes
                ) VALUES (?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?,
                          ?, ?, ?, ?,
                          ?, ?, ?, ?,
                          ?, ?, ?, ?,
                          ?, ?, ?,
                          ?)
            """, (
                cycle_id,
                result.get("timestamp"),
                datetime.now().isoformat(),
                (result.get("duration", 0) or 0) * 1000,
                1 if result.get("success", True) else 0,
                trigger,
                phase_status.get("monitor"),
                phase_status.get("analyze"),
                phase_status.get("plan"),
                phase_status.get("execute"),
                phase_status.get("verify"),
                phase_status.get("feedback"),
                hb.get("health_score"),
                hb.get("success_rate"),
                hb.get("tools_count"),
                hb.get("experiences"),
                ha.get("health_score"),
                ha.get("success_rate"),
                ha.get("tools_count"),
                ha.get("experiences"),
                phases.get("analyze", {}).get("issues", 0),
                phases.get("analyze", {}).get("patterns", 0),
                issues_json,
                patterns_json,
                phases.get("plan", {}).get("actions", 0),
                phases.get("execute", {}).get("success", 0) + phases.get("execute", {}).get("failure", 0),
                phases.get("execute", {}).get("success", 0),
                phases.get("verify", {}).get("improvements", 0),
                len(errors) if errors else 0,
                improvement_json,
                error_json,
                notes,
            ))
            conn.commit()
            logger.info("进化周期 #%d 已记录到审计数据库", cycle_id)
            return cycle_id
        except Exception as e:
            logger.warning("记录进化周期失败: %s", e)
            return -1

    def record_action(self, cycle_id: int, action: Dict[str, Any],
                      phase: str, success: bool = True,
                      error: str = None, duration_ms: float = None):
        """记录单个进化动作"""
        try:
            conn = get_evolution_db(self.db_path)
            conn.execute("""
                INSERT INTO evolution_actions
                    (cycle_id, action_type, target, description, phase,
                     before_state, after_state, success, error_message, duration_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                cycle_id,
                action.get("action_type", action.get("type", "unknown")),
                action.get("target", ""),
                action.get("description", str(action)[:500]),
                phase,
                json.dumps(action.get("before_state")) if action.get("before_state") else None,
                json.dumps(action.get("after_state")) if action.get("after_state") else None,
                1 if success else 0,
                error,
                duration_ms,
            ))
            conn.commit()
        except Exception as e:
            logger.warning("记录进化动作失败: %s", e)

    # ── 查询 ──────────────────────────────────────────────────────────────

    def query_cycles(self, limit: int = 20, days: int = 30,
                     success_only: bool = False) -> List[Dict]:
        """查询进化历史摘要列表"""
        conn = get_evolution_db(self.db_path)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        where = "WHERE started_at >= ?"
        params: list = [cutoff]
        if success_only:
            where += " AND success = 1"

        rows = conn.execute(
            f"SELECT * FROM evolution_cycles {where} ORDER BY cycle_id DESC LIMIT ?",
            params + [limit]
        ).fetchall()

        cycles = []
        for row in rows:
            cycles.append({
                "cycle_id": row["cycle_id"],
                "started_at": row["started_at"],
                "duration_ms": row["duration_ms"],
                "success": bool(row["success"]),
                "trigger": row["trigger"],
                "health_before": row["health_score_before"],
                "health_after": row["health_score_after"],
                "health_delta": (row["health_score_after"] or 0) - (row["health_score_before"] or 0),
                "issues_found": row["issues_found"],
                "actions_executed": row["actions_executed"],
                "actions_succeeded": row["actions_succeeded"],
                "improvements_detected": row["improvements_detected"],
                "errors_count": row["errors_count"],
            })
        return cycles

    def get_cycle_detail(self, cycle_id: int) -> Dict:
        """查询单次进化的完整详情"""
        conn = get_evolution_db(self.db_path)
        row = conn.execute(
            "SELECT * FROM evolution_cycles WHERE cycle_id = ?", (cycle_id,)
        ).fetchone()

        if not row:
            return {"error": f"未找到进化周期 #{cycle_id}"}

        # 获取关联的 actions
        actions = conn.execute(
            "SELECT * FROM evolution_actions WHERE cycle_id = ? ORDER BY id",
            (cycle_id,)
        ).fetchall()

        return {
            "cycle_info": {
                "cycle_id": row["cycle_id"],
                "started_at": row["started_at"],
                "finished_at": row["finished_at"],
                "duration_ms": row["duration_ms"],
                "success": bool(row["success"]),
                "trigger": row["trigger"],
                "notes": row["notes"],
            },
            "phases": {
                "monitor": row["phase_monitor"],
                "analyze": row["phase_analyze"],
                "plan": row["phase_plan"],
                "execute": row["phase_execute"],
                "verify": row["phase_verify"],
                "feedback": row["phase_feedback"],
            },
            "metrics_before": {
                "health_score": row["health_score_before"],
                "success_rate": row["success_rate_before"],
                "tools_count": row["tools_count_before"],
                "experiences": row["experiences_before"],
            },
            "metrics_after": {
                "health_score": row["health_score_after"],
                "success_rate": row["success_rate_after"],
                "tools_count": row["tools_count_after"],
                "experiences": row["experiences_after"],
            },
            "stats": {
                "issues_found": row["issues_found"],
                "patterns_discovered": row["patterns_discovered"],
                "actions_planned": row["actions_planned"],
                "actions_executed": row["actions_executed"],
                "actions_succeeded": row["actions_succeeded"],
                "improvements_detected": row["improvements_detected"],
                "errors_count": row["errors_count"],
            },
            "analysis_details": {
                "issues": json.loads(row["issues_details"]) if row["issues_details"] else [],
                "patterns": json.loads(row["patterns_details"]) if row["patterns_details"] else [],
            },
            "improvements": json.loads(row["improvement_summary"]) if row["improvement_summary"] else [],
            "errors": json.loads(row["error_summary"]) if row["error_summary"] else [],
            "actions": [
                {
                    "id": a["id"],
                    "action_type": a["action_type"],
                    "target": a["target"],
                    "description": a["description"],
                    "phase": a["phase"],
                    "success": bool(a["success"]),
                    "error_message": a["error_message"],
                    "duration_ms": a["duration_ms"],
                }
                for a in actions
            ],
        }

    def get_summary(self, days: int = 30) -> Dict:
        """统计汇总 + 按周趋势"""
        conn = get_evolution_db(self.db_path)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()

        # 总体统计
        stats = conn.execute("""
            SELECT
                COUNT(*) as total_cycles,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count,
                AVG(duration_ms) as avg_duration_ms,
                AVG(health_score_after - health_score_before) as avg_health_delta,
                SUM(improvements_detected) as total_improvements,
                SUM(actions_executed) as total_actions,
                MAX(health_score_after) as best_health,
                MIN(health_score_before) as worst_health_before
            FROM evolution_cycles
            WHERE started_at >= ?
        """, (cutoff,)).fetchone()

        # 最常见的动作类型
        action_types = conn.execute("""
            SELECT action_type, COUNT(*) as cnt
            FROM evolution_actions a
            JOIN evolution_cycles c ON a.cycle_id = c.cycle_id
            WHERE c.started_at >= ?
            GROUP BY action_type
            ORDER BY cnt DESC
            LIMIT 5
        """, (cutoff,)).fetchall()

        # 按周趋势
        weekly = conn.execute("""
            SELECT
                strftime('%Y-%W', started_at) as week,
                COUNT(*) as cycles,
                AVG(health_score_after) as avg_health,
                AVG(duration_ms) as avg_duration
            FROM evolution_cycles
            WHERE started_at >= ?
            GROUP BY week
            ORDER BY week
        """, (cutoff,)).fetchall()

        return {
            "period_days": days,
            "total_cycles": stats["total_cycles"] or 0,
            "success_rate": round((stats["success_count"] or 0) / max(stats["total_cycles"] or 1, 1), 2),
            "avg_duration_ms": round(stats["avg_duration_ms"] or 0, 0),
            "avg_health_improvement": round(stats["avg_health_delta"] or 0, 1),
            "total_improvements": stats["total_improvements"] or 0,
            "total_actions": stats["total_actions"] or 0,
            "best_health": stats["best_health"],
            "worst_health_before": stats["worst_health_before"],
            "most_common_actions": [
                {"type": row["action_type"], "count": row["cnt"]}
                for row in action_types
            ],
            "weekly_trend": [
                {
                    "week": row["week"],
                    "cycles": row["cycles"],
                    "avg_health": round(row["avg_health"] or 0, 1),
                    "avg_duration_ms": round(row["avg_duration"] or 0, 0),
                }
                for row in weekly
            ],
        }

    def get_latest_health_trend(self, limit: int = 10) -> List[Dict]:
        """最近N次进化的健康分变化趋势"""
        conn = get_evolution_db(self.db_path)
        rows = conn.execute("""
            SELECT cycle_id, started_at,
                   health_score_before, health_score_after,
                   (health_score_after - health_score_before) as delta
            FROM evolution_cycles
            ORDER BY cycle_id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        return [
            {
                "cycle_id": row["cycle_id"],
                "started_at": row["started_at"],
                "health_before": row["health_score_before"],
                "health_after": row["health_score_after"],
                "delta": row["delta"],
            }
            for row in reversed(rows)
        ]

    # ── 层级三：问题追溯查询 ──────────────────────────────────────────────

    def get_latest_issues(self, limit: int = 10) -> List[Dict]:
        """获取最近进化周期中发现的问题详情"""
        conn = get_evolution_db(self.db_path)
        rows = conn.execute("""
            SELECT cycle_id, started_at, issues_details
            FROM evolution_cycles
            WHERE issues_details IS NOT NULL AND issues_details != ''
            ORDER BY cycle_id DESC
            LIMIT ?
        """, (limit,)).fetchall()

        result = []
        for row in rows:
            try:
                issues = json.loads(row["issues_details"])
                for issue in issues:
                    issue["_cycle_id"] = row["cycle_id"]
                    issue["_started_at"] = row["started_at"]
                    result.append(issue)
            except (json.JSONDecodeError, TypeError):
                pass
        return result

    def query_issues_by_type(self, issue_type: str, days: int = 30) -> List[Dict]:
        """按问题类型筛选历史问题"""
        all_issues = self.get_latest_issues(limit=100)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [
            i for i in all_issues
            if i.get("type") == issue_type and i.get("_started_at", "") >= cutoff
        ]

    def query_issues_by_severity(self, severity: str, days: int = 30) -> List[Dict]:
        """按严重程度筛选历史问题"""
        all_issues = self.get_latest_issues(limit=100)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        return [
            i for i in all_issues
            if i.get("severity") == severity and i.get("_started_at", "") >= cutoff
        ]


# 导出
__all__ = ["EvolutionAuditor"]

"""
测试 EvolutionAuditor — 自进化审计器持久化和查询功能
"""

import json
import os
import tempfile
import pytest

from evolution.closed_loop.evolution_auditor import EvolutionAuditor
from evolution.db_utils import get_evolution_db


@pytest.fixture
def auditor():
    """创建使用临时数据库的审计器实例"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test_audit.db")
        os.environ["EVOLUTION_DATA_DIR"] = tmpdir
        a = EvolutionAuditor(db_path=db_path)
        yield a
        os.environ.pop("EVOLUTION_DATA_DIR", None)


def test_init_creates_tables(auditor):
    """初始化应创建 evolution_cycles 和 evolution_actions 表"""
    conn = get_evolution_db(auditor.db_path)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    table_names = [t[0] for t in tables]
    assert "evolution_cycles" in table_names
    assert "evolution_actions" in table_names


def test_record_cycle_basic(auditor):
    """记录一次基本进化周期"""
    result = {
        "cycle_id": 1,
        "timestamp": "2026-05-09T10:00:00",
        "duration": 0.5,
        "success": True,
        "phases": {
            "monitor": {"metrics_count": 5},
            "analyze": {"issues": 2, "patterns": 1},
            "plan": {"actions": 1, "priority": "normal"},
            "execute": {"success": 1, "failure": 0},
            "verify": {"improvements": 1, "score": 65},
            "feedback": {"recorded": True},
        },
    }

    cycle_id = auditor.record_cycle(result)
    assert cycle_id == 1

    # 验证写入
    conn = get_evolution_db(auditor.db_path)
    row = conn.execute("SELECT * FROM evolution_cycles WHERE cycle_id = 1").fetchone()
    assert row is not None
    assert row["success"] == 1
    assert row["issues_found"] == 2
    assert row["patterns_discovered"] == 1
    assert row["actions_executed"] == 1
    assert row["actions_succeeded"] == 1
    assert row["improvements_detected"] == 1


def test_record_cycle_with_health(auditor):
    """记录带健康快照的进化周期"""
    result = {
        "cycle_id": 2,
        "timestamp": "2026-05-09T10:05:00",
        "duration": 0.3,
        "success": True,
        "phases": {
            "monitor": {"metrics_count": 3},
            "analyze": {"issues": 0, "patterns": 0},
            "plan": {"actions": 0, "priority": "low"},
            "execute": {"success": 0, "failure": 0},
            "verify": {"improvements": 0, "score": 55},
            "feedback": {"recorded": True},
        },
    }

    health_before = {"health_score": 55, "success_rate": 0.65, "tools_count": 32, "experiences": 100}
    health_after = {"health_score": 68, "success_rate": 0.70, "tools_count": 32, "experiences": 110}

    auditor.record_cycle(result, health_before=health_before, health_after=health_after)

    conn = get_evolution_db(auditor.db_path)
    row = conn.execute("SELECT * FROM evolution_cycles WHERE cycle_id = 2").fetchone()
    assert row["health_score_before"] == 55
    assert row["health_score_after"] == 68
    assert row["success_rate_before"] == 0.65
    assert row["success_rate_after"] == 0.70


def test_query_cycles(auditor):
    """查询进化历史列表"""
    for i in range(1, 4):
        result = {
            "cycle_id": i,
            "timestamp": f"2026-05-09T{i:02d}:00:00",
            "duration": 0.2 * i,
            "success": i != 2,  # #2 失败
            "phases": {
                "monitor": {"metrics_count": 3},
                "analyze": {"issues": i, "patterns": 0},
                "plan": {"actions": 0, "priority": "normal"},
                "execute": {"success": 1 if i != 2 else 0, "failure": 1 if i == 2 else 0},
                "verify": {"improvements": i, "score": 60},
                "feedback": {"recorded": True},
            },
        }
        auditor.record_cycle(result,
                            health_before={"health_score": 50 + i},
                            health_after={"health_score": 55 + i})

    # 查询全部
    cycles = auditor.query_cycles(limit=10, days=365)
    assert len(cycles) >= 3

    # 只查成功
    success_cycles = auditor.query_cycles(limit=10, days=365, success_only=True)
    assert len(success_cycles) == 2
    assert all(c["success"] for c in success_cycles)

    # 健康分 delta 正确
    for c in cycles:
        assert c["health_delta"] is not None


def test_get_cycle_detail(auditor):
    """查询单次进化完整详情"""
    result = {
        "cycle_id": 5,
        "timestamp": "2026-05-09T11:00:00",
        "duration": 0.8,
        "success": True,
        "phases": {
            "monitor": {"metrics_count": 6},
            "analyze": {"issues": 3, "patterns": 2},
            "plan": {"actions": 2, "priority": "high"},
            "execute": {"success": 2, "failure": 0},
            "verify": {"improvements": 2, "score": 72},
            "feedback": {"recorded": True},
        },
    }
    auditor.record_cycle(result,
                        health_before={"health_score": 60, "success_rate": 0.60},
                        health_after={"health_score": 72, "success_rate": 0.75})

    detail = auditor.get_cycle_detail(5)
    assert detail["cycle_info"]["cycle_id"] == 5
    assert detail["cycle_info"]["success"] is True
    assert detail["phases"]["monitor"] == "completed"
    assert detail["phases"]["feedback"] == "completed"
    assert detail["metrics_before"]["health_score"] == 60
    assert detail["metrics_after"]["health_score"] == 72
    assert detail["stats"]["issues_found"] == 3
    assert detail["stats"]["actions_executed"] == 2


def test_get_cycle_detail_not_found(auditor):
    """查询不存在的周期"""
    detail = auditor.get_cycle_detail(999)
    assert "error" in detail


def test_get_summary(auditor):
    """统计汇总"""
    for i in range(1, 6):
        result = {
            "cycle_id": i,
            "timestamp": f"2026-05-09T{i:02d}:00:00",
            "duration": 0.3,
            "success": i != 3,
            "phases": {
                "monitor": {"metrics_count": 3},
                "analyze": {"issues": 1, "patterns": 0},
                "plan": {"actions": 1, "priority": "normal"},
                "execute": {"success": 1 if i != 3 else 0, "failure": 1 if i == 3 else 0},
                "verify": {"improvements": 1, "score": 65},
                "feedback": {"recorded": True},
            },
        }
        auditor.record_cycle(result,
                            health_before={"health_score": 50 + i},
                            health_after={"health_score": 55 + i + i % 2})

    summary = auditor.get_summary(days=365)
    assert summary["total_cycles"] == 5
    assert summary["success_rate"] == 0.8
    assert summary["total_improvements"] == 5
    assert summary["best_health"] == 61  # 第5次: 55+5+1=61
    assert "most_common_actions" in summary
    assert "weekly_trend" in summary


def test_get_latest_health_trend(auditor):
    """健康分变化趋势"""
    for i in range(1, 4):
        result = {
            "cycle_id": i,
            "timestamp": f"2026-05-09T{i:02d}:00:00",
            "duration": 0.2,
            "success": True,
            "phases": {
                "monitor": {"metrics_count": 3},
                "analyze": {"issues": 0, "patterns": 0},
                "plan": {"actions": 0, "priority": "normal"},
                "execute": {"success": 0, "failure": 0},
                "verify": {"improvements": 0, "score": 60 + i * 5},
                "feedback": {"recorded": True},
            },
        }
        auditor.record_cycle(result,
                            health_before={"health_score": 50 + i * 5},
                            health_after={"health_score": 55 + i * 5})

    trend = auditor.get_latest_health_trend(limit=3)
    assert len(trend) == 3
    for t in trend:
        assert t["health_before"] is not None
        assert t["health_after"] is not None
        assert t["delta"] is not None


def test_record_action(auditor):
    """记录进化动作"""
    # 先记录一个周期
    result = {
        "cycle_id": 8,
        "timestamp": "2026-05-09T12:00:00",
        "duration": 0.4,
        "success": True,
        "phases": {
            "monitor": {"metrics_count": 3},
            "analyze": {"issues": 1, "patterns": 0},
            "plan": {"actions": 1, "priority": "normal"},
            "execute": {"success": 1, "failure": 0},
            "verify": {"improvements": 1, "score": 68},
            "feedback": {"recorded": True},
        },
    }
    auditor.record_cycle(result)

    action = {
        "action_type": "strategy_switch",
        "target": "current_strategy",
        "description": "切换策略从 ADAPTIVE 到 EFFICIENCY_OPTIMIZED",
    }
    auditor.record_action(8, action, phase="execute", success=True, duration_ms=150)

    # 验证
    detail = auditor.get_cycle_detail(8)
    assert len(detail["actions"]) == 1
    assert detail["actions"][0]["action_type"] == "strategy_switch"
    assert detail["actions"][0]["success"] is True


def test_record_cycle_failure(auditor):
    """记录失败的进化周期"""
    result = {
        "cycle_id": 9,
        "timestamp": "2026-05-09T13:00:00",
        "duration": 2.0,
        "success": False,
        "phases": {
            "monitor": {"metrics_count": 0},
            "analyze": {"issues": 0, "patterns": 0},
            "plan": {"actions": 0, "priority": "normal"},
            "execute": {"success": 0, "failure": 0},
            "verify": {"improvements": 0, "score": 0},
            "feedback": {"recorded": False},
        },
        "errors": [{"phase": "monitor", "message": "Metrics collection timed out"}],
    }
    auditor.record_cycle(result)

    conn = get_evolution_db(auditor.db_path)
    row = conn.execute("SELECT * FROM evolution_cycles WHERE cycle_id = 9").fetchone()
    assert row["success"] == 0
    assert row["errors_count"] == 1
    assert row["phase_monitor"] == "failed"


def test_auditor_isolation(auditor):
    """审计器失败不影响主流程（无异常抛出）"""
    # 传递格式不完整的 result 也不应崩溃
    bad_result = {
        "cycle_id": 99,
        "timestamp": "2026-05-09T14:00:00",
        "phases": {},
    }
    cycle_id = auditor.record_cycle(bad_result)
    # 即使数据不完整，也应返回 cycle_id
    assert cycle_id == 99

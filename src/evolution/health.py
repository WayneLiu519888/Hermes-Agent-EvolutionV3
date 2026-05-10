"""进化系统健康检查 — 全局状态快照。

通过 evolution_self_monitor 暴露的指标聚合所有组件状态，
提供一键健康检查能力。CLI: `hermes-evolution status`
"""
import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional


def health_check(data_dir: Optional[Path] = None) -> dict:
    """运行一次健康检查，返回 JSON 可序列化的状态快照。

    Returns:
        {
            "timestamp": "2026-05-08T...",
            "overall": "healthy" | "degraded" | "critical",
            "components": {
                "db": {"status": "ok", "size_kb": 123, "tables": [...], "row_counts": {...}},
                "monitor": {"status": "ok", "success_rate": 0.95, "uptime_hours": 48},
                "plugin": {"status": "ok|missing|stale", "deployed_at": "..."},
                "memory": {"entries": 0, "associations": 0},
            },
            "warnings": [...],
            "recommendations": [...]
        }
    """
    result = {
        "timestamp": datetime.now().isoformat(),
        "overall": "healthy",
        "components": {},
        "warnings": [],
        "recommendations": [],
    }

    # ── 1. DB 健康 ──
    try:
        from evolution.db_utils import get_data_dir, db_get_stats
        data = get_data_dir(data_dir)
        db_files = list(data.glob("*.db"))
        total_kb = sum(f.stat().st_size for f in db_files) / 1024
        db_status = {
            "status": "ok",
            "data_dir": str(data),
            "file_count": len(db_files),
            "total_size_kb": round(total_kb, 1),
        }
        # 尝试打开主库
        main_db = data / "associations.db"
        if main_db.exists():
            import sqlite3
            conn = sqlite3.connect(str(main_db))
            tables = [r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()]
            row_counts = {}
            for t in tables:
                try:
                    row_counts[t] = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
                except Exception:
                    row_counts[t] = -1
            conn.close()
            db_status["tables"] = tables
            db_status["row_counts"] = row_counts
            # 大型 DB 警告
            if total_kb > 10000:
                result["warnings"].append(f"DB 总大小 {total_kb:.0f} KB 超大，建议运行 check --clean")
        result["components"]["db"] = db_status
    except Exception as e:
        result["components"]["db"] = {"status": "error", "error": str(e)}
        result["warnings"].append(f"DB 检查失败: {e}")

    # ── 2. SelfMonitor ──
    try:
        from evolution.self_monitor import SelfMonitor
        monitor = SelfMonitor()
        stats = monitor.get_stats() if hasattr(monitor, 'get_stats') else {}
        monitor_status = {
            "status": "ok",
            "success_rate": stats.get("success_rate", None),
            "total_cycles": stats.get("total_cycles", None),
            "tools_tracked": len(stats.get("tool_stats", {})),
        }
        result["components"]["monitor"] = monitor_status
    except ImportError:
        result["components"]["monitor"] = {"status": "unavailable"}
    except Exception as e:
        result["components"]["monitor"] = {"status": "error", "error": str(e)}

    # ── 3. Plugin 部署 ──
    plugin_yaml = Path.home() / ".hermes" / "plugins" / "hermes-evolution" / "plugin.yaml"
    if plugin_yaml.exists():
        mtime = datetime.fromtimestamp(plugin_yaml.stat().st_mtime)
        result["components"]["plugin"] = {
            "status": "ok",
            "deployed_at": mtime.isoformat(),
            "age_hours": round((datetime.now() - mtime).total_seconds() / 3600, 1),
        }
    else:
        result["components"]["plugin"] = {"status": "missing"}
        result["warnings"].append("插件未部署，运行 hermes-evolution setup")
        if result["overall"] == "healthy":
            result["overall"] = "degraded"

    # ── 4. Memory ──
    try:
        from evolution.memory.database import AssociationDatabase
        mdb = AssociationDatabase()
        entry_count = mdb.count_entries() if hasattr(mdb, 'count_entries') else 0
        assoc_count = mdb.count_associations() if hasattr(mdb, 'count_associations') else 0
        result["components"]["memory"] = {
            "status": "ok",
            "entries": entry_count,
            "associations": assoc_count,
        }
    except ImportError:
        result["components"]["memory"] = {"status": "unavailable"}
    except Exception as e:
        result["components"]["memory"] = {"status": "error", "error": str(e)}

    # ── 综合判断 ──
    error_count = sum(1 for c in result["components"].values()
                      if c.get("status") in ("error", "missing"))
    if result["overall"] == "healthy" and error_count >= 2:
        result["overall"] = "critical"
    elif result["overall"] == "healthy" and error_count == 1:
        result["overall"] = "degraded"

    return result


def comprehensive_health_check() -> dict:
    """深度健康检查：检查所有数据库的 WAL 文件大小，预警大文件。

    Returns:
        {
            "timestamp": "2026-05-11T...",
            "components": {db_name: {"wal_mb": 1.2}, ...},
            "warnings": [...],
            "critical": [...]
        }
    """
    from evolution.db_utils import _resolve_data_dir

    checks = {
        "timestamp": datetime.now().isoformat(),
        "components": {},
        "warnings": [],
        "critical": [],
    }
    db_names = [
        "associations.db", "tools.db", "learning_experiences.db",
        "tool_performance.db", "retrieval_optimization.db",
        "evolution_audit.db", "audit.db", "collaboration_messages.db",
    ]
    for db_name in db_names:
        wal_path = str(_resolve_data_dir() / db_name) + "-wal"
        if os.path.exists(wal_path):
            mb = os.path.getsize(wal_path) / 1024 / 1024
            checks["components"][db_name] = {"wal_mb": round(mb, 1)}
            if mb > 100:
                checks["critical"].append(f"{db_name} WAL {mb:.0f}MB")
            elif mb > 50:
                checks["warnings"].append(f"{db_name} WAL {mb:.0f}MB")
    return checks


def print_health(data_dir: Optional[Path] = None) -> bool:
    """打印健康报告到控制台。返回是否健康。"""
    hc = health_check(data_dir)
    
    print(f"🩺 进化系统健康检查 — {hc['timestamp']}")
    print("=" * 50)
    print(f"  总体状态: {'✅' if hc['overall'] == 'healthy' else '⚠️' if hc['overall'] == 'degraded' else '🔴'} {hc['overall']}")
    print()
    
    for name, comp in hc["components"].items():
        icon = "✅" if comp.get("status") == "ok" else "⚠️" if comp.get("status") == "degraded" else "❌"
        print(f"  {icon} {name}: {comp.get('status', '?')}")
        for k, v in comp.items():
            if k != "status" and k != "tables" and k != "row_counts":
                print(f"      {k}: {v}")
    
    if hc["warnings"]:
        print(f"\n  ⚠️ 警告 ({len(hc['warnings'])}):")
        for w in hc["warnings"]:
            print(f"    - {w}")
    
    if hc["recommendations"]:
        print(f"\n  💡 建议 ({len(hc['recommendations'])}):")
        for r in hc["recommendations"]:
            print(f"    - {r}")
    
    print("=" * 50)
    return hc["overall"] == "healthy"


if __name__ == "__main__":
    print_health()

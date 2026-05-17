"""
HAE Demo 模块 — 开箱即用的演示环境

提供预置的 demo 数据（工具、经验、周期），让用户无需真实积累
即可看到完整的进化闭环运转。

使用方法:
    hae demo install    部署 demo 环境
    hae demo uninstall  清除 demo 数据
    hae demo status     查看当前模式
"""

import shutil
from pathlib import Path
from datetime import datetime, timedelta
import sqlite3
import json
import random

DEMO_MARKER = ".demo_mode"  # 标记文件名


def _get_demo_dir() -> Path:
    """获取 demo 数据目录"""
    return Path.home() / ".hermes" / "data" / "evolution" / "demo"


def _get_marker_path() -> Path:
    """获取 demo 标记文件路径"""
    return Path.home() / ".hermes" / "data" / "evolution" / DEMO_MARKER


# ═══════════════════════════════════════════
# 种子数据
# ═══════════════════════════════════════════

DEMO_TOOLS = [
    ("add_numbers", "utility", "active", "简单加法工具，用于演示基础工具注册"),
    ("add_tool", "utility", "active", "通用加法工具，支持任意数量参数"),
    ("add_with_logging", "utility", "active", "带日志的加法工具，演示工具增强"),
    ("api_func", "utility", "experimental", "API函数包装器，演示API集成"),
    ("broken_tool", "custom", "experimental", "故意失败的演示工具，用于展示错误处理"),
]

DEMO_EXPERIENCES = [
    # (tool_name, success, execution_time, task_id, description)
    ("search_files", True, 0.3, "demo_001", "搜索配置文件"),
    ("read_file", True, 0.1, "demo_002", "读取项目README"),
    ("terminal", True, 0.5, "demo_003", "执行pip安装"),
    ("write_file", True, 0.2, "demo_004", "写入配置文件"),
    ("search_files", False, 2.1, "demo_005", "搜索不存在的模式"),
    ("add_numbers", True, 0.1, "demo_006", "计算1+2"),
    ("read_file", True, 0.1, "demo_007", "读取源码"),
    ("terminal", True, 0.8, "demo_008", "运行测试"),
    ("search_files", True, 0.4, "demo_009", "查找Python文件"),
    ("write_file", True, 0.3, "demo_010", "写入日志"),
    ("add_tool", True, 0.2, "demo_011", "计算3+4"),
    ("terminal", False, 5.0, "demo_012", "执行错误命令"),
    ("read_file", True, 0.1, "demo_013", "读取文档"),
    ("search_files", True, 0.3, "demo_014", "搜索import语句"),
    ("add_with_logging", True, 0.3, "demo_015", "带日志计算5+6"),
    ("write_file", False, 0.5, "demo_016", "写入权限失败"),
    ("search_files", True, 0.2, "demo_017", "查找配置文件"),
    ("read_file", True, 0.1, "demo_018", "读取JSON"),
    ("terminal", True, 0.6, "demo_019", "执行git status"),
    ("add_numbers", True, 0.1, "demo_020", "计算10+20"),
    ("api_func", True, 0.4, "demo_021", "调用API接口"),
    ("search_files", True, 0.3, "demo_022", "搜索TODO注释"),
    ("write_file", True, 0.2, "demo_023", "写入缓存文件"),
    ("terminal", True, 1.2, "demo_024", "执行构建脚本"),
    ("read_file", True, 0.1, "demo_025", "读取环境变量"),
    ("add_tool", True, 0.2, "demo_026", "计算100+200"),
    ("search_files", False, 1.5, "demo_027", "搜索过期路径"),
    ("terminal", True, 0.4, "demo_028", "检查服务状态"),
    ("write_file", True, 0.3, "demo_029", "写入导出数据"),
    ("read_file", True, 0.1, "demo_030", "读取markdown"),
    ("add_with_logging", True, 0.3, "demo_031", "带日志计算50+50"),
    ("search_files", True, 0.2, "demo_032", "查找测试文件"),
    ("terminal", True, 3.0, "demo_033", "部署服务"),
    ("broken_tool", False, 0.1, "demo_034", "故意失败的演示"),
    ("read_file", True, 0.1, "demo_035", "读取YAML"),
    ("search_files", True, 0.3, "demo_036", "搜索类定义"),
    ("write_file", True, 0.2, "demo_037", "写入测试结果"),
    ("api_func", True, 0.5, "demo_038", "调用外部服务"),
    ("terminal", True, 0.7, "demo_039", "清理缓存"),
    ("add_numbers", True, 0.1, "demo_040", "计算99+1"),
    ("search_files", True, 0.3, "demo_041", "搜索数据库配置"),
    ("read_file", True, 0.1, "demo_042", "读取密钥文件"),
    ("terminal", False, 4.0, "demo_043", "部署失败回滚"),
    ("write_file", True, 0.2, "demo_044", "写入健康检查"),
    ("add_tool", True, 0.2, "demo_045", "计算1000+1"),
    ("search_files", True, 0.3, "demo_046", "搜索错误处理"),
    ("read_file", True, 0.1, "demo_047", "读取类型定义"),
    ("terminal", True, 0.5, "demo_048", "重启服务"),
    ("add_with_logging", True, 0.4, "demo_049", "带日志计算999+1"),
    ("write_file", True, 0.2, "demo_050", "写入最终报告"),
]

DEMO_CYCLES = [
    # (cycle_id, started_at, health, success_rate, tools, exp, issues, patterns, actions_planned, actions_exec, actions_ok)
    (1, "2026-06-01T10:00:00", 60, 0.75, 5, 10, 2, 3, 3, 3, 2),
    (2, "2026-06-02T10:00:00", 75, 0.88, 8, 25, 1, 5, 4, 4, 3),
    (3, "2026-06-03T10:00:00", 90, 0.95, 12, 50, 0, 7, 5, 5, 5),
]

DEMO_ACTIONS = [
    # (cycle_id, action_type, target, success, phase, description)
    (1, "strategy_switch", "global", True, "execute", "低成功率触发策略切换：ADAPTIVE→RELIABILITY"),
    (1, "tool_optimization", "add_numbers", True, "execute", "优化add_numbers：增加输入校验"),
    (1, "tool_optimization", "broken_tool", False, "execute", "尝试修复broken_tool→需要更多数据"),
    (2, "strategy_switch", "strategy_learner", True, "execute", "时段模式触发策略调整"),
    (2, "tool_optimization", "api_func", True, "execute", "优化api_func：增加重试机制"),
    (2, "tool_optimization", "add_tool", True, "execute", "优化add_tool：支持浮点数"),
    (2, "tool_optimization", "add_with_logging", True, "execute", "优化add_with_logging：减少日志开销"),
    (3, "strategy_switch", "global", True, "execute", "持续高成功率→切换为EFFICIENCY模式"),
    (3, "tool_optimization", "search_files", True, "execute", "优化search_files：增加缓存命中"),
    (3, "tool_optimization", "terminal", True, "execute", "优化terminal：超时参数调整"),
    (3, "tool_optimization", "write_file", True, "execute", "优化write_file：批量写入模式"),
    (3, "tool_optimization", "read_file", True, "execute", "优化read_file：预读缓冲区"),
]


# ═══════════════════════════════════════════
# 安装 / 卸载
# ═══════════════════════════════════════════

def install_demo() -> str:
    """部署 demo 环境"""
    demo_dir = _get_demo_dir()
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
    demo_dir.mkdir(parents=True, exist_ok=True)

    # 1. tools.db — 5 个 demo 工具 + tool_usage_history
    tools_db = demo_dir / "tools.db"
    _init_tools_db(tools_db)

    # 2. learning_experiences.db — 50 条经验
    exp_db = demo_dir / "learning_experiences.db"
    _init_experiences_db(exp_db)

    # 3. evolution_audit.db — 3 个周期 + 12 个动作
    audit_db = demo_dir / "evolution_audit.db"
    _init_audit_db(audit_db)

    # 4. 写入标记文件
    _get_marker_path().write_text("demo")

    return f"Demo 环境已部署: {demo_dir}\n  5 个演示工具 | 50 条经验 | 3 个周期"


def uninstall_demo() -> str:
    """清除 demo 环境"""
    demo_dir = _get_demo_dir()
    marker = _get_marker_path()

    removed = []
    if demo_dir.exists():
        shutil.rmtree(demo_dir)
        removed.append(str(demo_dir))
    if marker.exists():
        marker.unlink()
        removed.append(str(marker))

    if removed:
        return f"Demo 环境已清除: {', '.join(removed)}"
    return "Demo 环境未安装"


def demo_status() -> str:
    """查看当前模式"""
    if _get_marker_path().exists():
        demo_dir = _get_demo_dir()
        lines = ["当前模式: DEMO (演示)"]
        if demo_dir.exists():
            for db in sorted(demo_dir.glob("*.db")):
                size = db.stat().st_size
                lines.append(f"  {db.name}: {size/1024:.0f} KB")
        return "\n".join(lines)
    return "当前模式: PROD (生产)"


# ═══════════════════════════════════════════
# DB 初始化
# ═══════════════════════════════════════════

def _init_tools_db(path: Path):
    conn = sqlite3.connect(str(path))
    conn.execute("""CREATE TABLE tools (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL, description TEXT, category TEXT,
        status TEXT NOT NULL, version TEXT, author TEXT,
        created_at TEXT, updated_at TEXT,
        usage_count INTEGER DEFAULT 0, success_count INTEGER DEFAULT 0,
        error_count INTEGER DEFAULT 0,
        parameters TEXT, return_type TEXT, dependencies TEXT, tags TEXT,
        source_code TEXT, is_builtin BOOLEAN DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE tool_usage_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tool_name TEXT NOT NULL, success INTEGER NOT NULL,
        execution_time REAL NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, context TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tuh_tool ON tool_usage_history(tool_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tuh_time ON tool_usage_history(timestamp)")

    now = datetime.now().isoformat()
    for name, cat, status, desc in DEMO_TOOLS:
        conn.execute("INSERT INTO tools (name, category, status, description, version, author, created_at, updated_at, parameters, return_type, dependencies, tags, source_code) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (name, cat, status, desc, "1.0.0-demo", "HAE Demo", now, now, "{}", "json", "[]", "demo", "# demo tool"))

    # 写入 tool_usage_history
    base_time = datetime.now() - timedelta(days=3)
    for tool, succ, etime, tid, desc in DEMO_EXPERIENCES:
        ts = base_time + timedelta(hours=random.randint(0, 72))
        ctx = json.dumps({"task_id": tid, "description": desc})
        conn.execute("INSERT INTO tool_usage_history (tool_name, success, execution_time, timestamp, context) VALUES (?,?,?,?,?)",
            (tool, 1 if succ else 0, etime, ts.isoformat(), ctx))

    conn.commit()
    conn.close()


def _init_experiences_db(path: Path):
    conn = sqlite3.connect(str(path))
    conn.execute("""CREATE TABLE experiences (
        id TEXT PRIMARY KEY, experience_type TEXT NOT NULL, task_id TEXT NOT NULL,
        timestamp DATETIME NOT NULL, description TEXT, context TEXT,
        actions TEXT, reasoning_steps TEXT, outcome TEXT NOT NULL,
        result TEXT, metrics TEXT, lessons_learned TEXT,
        tags TEXT, confidence REAL, importance REAL,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_exp_type ON experiences(experience_type)")

    base_time = datetime.now() - timedelta(days=3)
    for tool, succ, etime, tid, desc in DEMO_EXPERIENCES:
        ts = base_time + timedelta(hours=random.randint(0, 72))
        outcome = "success" if succ else "failure"
        ctx = json.dumps({"tool_name": tool, "execution_time": etime})
        tags = json.dumps(["demo", tool])
        exp_id = f"demo_{tid}"
        conn.execute("INSERT INTO experiences (id, experience_type, task_id, timestamp, description, context, outcome, metrics, tags, confidence, importance) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (exp_id, "tool_usage", tid, ts.isoformat(), f"Demo: {desc}", ctx, outcome, json.dumps({"duration_ms": etime*1000}), tags, 0.8, 0.5))

    conn.commit()
    conn.close()


def _init_audit_db(path: Path):
    conn = sqlite3.connect(str(path))
    conn.execute("""CREATE TABLE evolution_cycles (
        cycle_id INTEGER PRIMARY KEY, started_at DATETIME NOT NULL,
        finished_at DATETIME, duration_ms REAL DEFAULT 0,
        success INTEGER DEFAULT 1, trigger TEXT DEFAULT 'manual',
        phase_monitor TEXT, phase_analyze TEXT, phase_plan TEXT,
        phase_execute TEXT, phase_verify TEXT, phase_feedback TEXT,
        health_score_before REAL, success_rate_before REAL,
        tools_count_before INTEGER, experiences_before INTEGER,
        health_score_after REAL, success_rate_after REAL,
        tools_count_after INTEGER, experiences_after INTEGER,
        issues_found INTEGER DEFAULT 0, patterns_discovered INTEGER DEFAULT 0,
        actions_planned INTEGER DEFAULT 0, actions_executed INTEGER DEFAULT 0,
        actions_succeeded INTEGER DEFAULT 0, improvements_detected INTEGER DEFAULT 0,
        errors_count INTEGER DEFAULT 0,
        improvement_summary TEXT, error_summary TEXT, notes TEXT,
        issues_details TEXT, patterns_details TEXT
    )""")
    conn.execute("""CREATE TABLE evolution_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cycle_id INTEGER NOT NULL REFERENCES evolution_cycles(cycle_id),
        action_type TEXT NOT NULL, target TEXT, description TEXT,
        phase TEXT, before_state TEXT, after_state TEXT,
        success INTEGER DEFAULT 1, error_message TEXT,
        duration_ms REAL, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")

    for (cid, st, health, sr, tc, exp, issues, pat, ap, ae, aok) in DEMO_CYCLES:
        end_time = (datetime.fromisoformat(st) + timedelta(seconds=random.randint(3, 15))).isoformat()
        dur = random.randint(2000, 8000)
        issues_detail = json.dumps([{"type": "tool_low_performance", "target": "broken_tool", "value": 0.15, "severity": "medium", "message": "工具 broken_tool 性能偏低"}] if issues > 0 else [])
        patterns_detail = json.dumps([{"type": "temporal_pattern", "confidence": 0.85, "description": f"时段模式: {h}时成功率较高"} for h in [10, 14, 16, 20, 22][:pat]])
        conn.execute("""INSERT INTO evolution_cycles (cycle_id, started_at, finished_at, duration_ms, success, trigger,
            phase_monitor, phase_analyze, phase_plan, phase_execute, phase_verify, phase_feedback,
            health_score_before, success_rate_before, tools_count_before, experiences_before,
            health_score_after, success_rate_after, tools_count_after, experiences_after,
            issues_found, patterns_discovered, actions_planned, actions_executed, actions_succeeded,
            improvements_detected, errors_count, issues_details, patterns_details)
            VALUES (?,?,?,?,1,'manual','completed','completed','completed','completed','completed','completed',
            ?,?,?,?, ?,?,?,?, ?,?, ?,?,?, 1,0, ?,?)""",
            (cid, st, end_time, dur, health, sr, tc, exp, health, sr, tc, exp, issues, pat, ap, ae, aok, issues_detail, patterns_detail))

    for cid, atype, target, succ, phase, desc in DEMO_ACTIONS:
        conn.execute("INSERT INTO evolution_actions (cycle_id, action_type, target, description, phase, success) VALUES (?,?,?,?,?,?)",
            (cid, atype, target, desc, phase, 1 if succ else 0))

    conn.commit()
    conn.close()

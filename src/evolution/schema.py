"""
Evolution Schema 版本化管理

提供数据库 DDL 的声明式定义和自动迁移。
所有模块的建表语句集中管理，避免散落在各 _init_db() 中。

用法:
    from evolution.schema import ensure_schema

    ensure_schema("tools.db")
    ensure_schema("learning_experiences.db")
"""

import logging
from evolution.db_pool import db_pool

logger = logging.getLogger(__name__)

# ── Schema 版本 ────────────────────────────────────────────────────────────────

SCHEMA_VERSION = 1

# ── 迁移定义 ───────────────────────────────────────────────────────────────────
#
# MIGRATIONS[version][db_name] = [DDL statements...]
#
# 新增迁移时递增 SCHEMA_VERSION 并添加新条目即可。
# ensure_schema() 会自动从当前版本逐步执行到目标版本。

MIGRATIONS = {
    1: {
        "tools.db": [
            """CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                api_spec TEXT,
                category TEXT DEFAULT 'custom',
                tags TEXT DEFAULT '[]',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_tools_name ON tools(name)",
        ],
        "learning_experiences.db": [
            """CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                experience_type TEXT NOT NULL,
                description TEXT,
                outcome TEXT,
                task_id TEXT,
                context TEXT DEFAULT '{}',
                metrics TEXT DEFAULT '{}',
                lessons TEXT DEFAULT '[]',
                tags TEXT DEFAULT '[]',
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_exp_type ON experiences(experience_type)",
            "CREATE INDEX IF NOT EXISTS idx_exp_timestamp ON experiences(timestamp)",
        ],
        "agent_memory.db": [
            """CREATE TABLE IF NOT EXISTS memory_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                value TEXT,
                metadata TEXT DEFAULT '{}',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_memory_key ON memory_entries(key)",
            "CREATE INDEX IF NOT EXISTS idx_memory_updated ON memory_entries(updated_at)",
        ],
        "evolution_state.db": [
            """CREATE TABLE IF NOT EXISTS state_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_type TEXT NOT NULL,
                data TEXT,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_snapshot_type ON state_snapshots(snapshot_type)",
            "CREATE INDEX IF NOT EXISTS idx_snapshot_created ON state_snapshots(created_at)",
        ],
        "audit.db": [
            """CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                user_id TEXT,
                resource TEXT,
                action TEXT,
                details TEXT DEFAULT '{}',
                ip_address TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )""",
            "CREATE INDEX IF NOT EXISTS idx_audit_type ON audit_log(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)",
        ],
    },
}


# ── Schema 确保 ────────────────────────────────────────────────────────────────

def ensure_schema(db_name: str, target_version: int = SCHEMA_VERSION):
    """
    确保指定数据库的 schema 版本正确。

    首次调用时创建 _schema_version 追踪表，
    然后从当前版本逐步执行到 target_version 的所有迁移。

    Args:
        db_name: 数据库文件名（如 "tools.db"）
        target_version: 目标 schema 版本号，默认 SCHEMA_VERSION
    """
    with db_pool.connection(db_name) as conn:
        # 1. 确保版本追踪表存在
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER)"
        )

        # 2. 查询当前版本
        row = conn.execute("SELECT version FROM _schema_version").fetchone()
        current = row[0] if row else 0

        # 3. 逐步执行迁移
        for v in range(current + 1, target_version + 1):
            if v in MIGRATIONS and db_name in MIGRATIONS[v]:
                logger.info(
                    "Migrating %s: version %d -> %d (%d DDL statements)",
                    db_name, current, v, len(MIGRATIONS[v][db_name])
                )
                for ddl in MIGRATIONS[v][db_name]:
                    try:
                        conn.execute(ddl)
                    except Exception as e:
                        logger.error(
                            "Migration failed for %s v%d: %s\nDDL: %s",
                            db_name, v, e, ddl[:120]
                        )
                        raise

            # 更新版本号（即使当前版本没有该 db 的迁移也更新）
            conn.execute(
                "INSERT OR REPLACE INTO _schema_version (version) VALUES (?)",
                (v,)
            )

        conn.commit()

        if target_version > current:
            logger.info(
                "Schema %s migrated: v%d -> v%d", db_name, current, target_version
            )


def get_schema_version(db_name: str) -> int:
    """查询数据库当前 schema 版本"""
    with db_pool.connection(db_name) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS _schema_version (version INTEGER)"
        )
        row = conn.execute("SELECT version FROM _schema_version").fetchone()
        return row[0] if row else 0


def initialize_all():
    """初始化所有已知数据库的 schema（守护进程启动时调用）"""
    for db_name in MIGRATIONS.get(SCHEMA_VERSION, {}):
        try:
            ensure_schema(db_name)
        except Exception as e:
            logger.error("Failed to initialize schema for %s: %s", db_name, e)

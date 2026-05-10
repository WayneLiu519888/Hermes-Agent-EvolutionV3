"""
Evolution Database Utilities — 统一数据库连接工厂

提供线程安全的 SQLite 连接，启用 WAL 模式以支持并发读写。
所有 evolution 模块必须通过此模块获取数据库连接，禁止裸 sqlite3.connect()。

特性:
  - WAL 模式: 读不阻塞写，写不阻塞读
  - check_same_thread=False: 允许跨线程访问
  - busy_timeout=30s: 忙等重试
  - 路径统一: ~/.hermes/data/evolution/ (可由 EVOLUTION_DATA_DIR 覆盖)
  - 连接缓存: 同一进程内复用连接 (thread-safe)

用法:
    from .db_utils import get_evolution_db
    
    conn = get_evolution_db("tools.db")
    conn.execute("SELECT ...")
"""

import os
import sqlite3
import threading
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── 路径解析 ──────────────────────────────────────────────────────────────────

def _resolve_data_dir() -> Path:
    """解析进化数据目录路径"""
    # 1. 环境变量优先
    env_dir = os.environ.get("EVOLUTION_DATA_DIR")
    if env_dir:
        data_dir = Path(env_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir

    # 2. Hermes 标准路径
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    data_dir = Path(hermes_home) / "data" / "evolution"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_data_dir() -> Path:
    """获取进化数据目录路径"""
    return _resolve_data_dir()


# ── 连接缓存 (thread-safe) ───────────────────────────────────────────────────
# DEPRECATED: V5-P0 之后由 DatabasePool 管理，_connection_cache 仅保留兼容不再主动使用
_DEPRECATION_NOTICE = (
    "db_utils._connection_cache is deprecated. "
    "All connections are now managed by evolution.db_pool.DatabasePool."
)

_connection_cache: dict = {}
_cache_lock = threading.Lock()


def get_evolution_db(db_name: str) -> sqlite3.Connection:
    """
    获取线程安全的 SQLite 连接。
    
    V5-P0: 内部转发到 DatabasePool 统一管理。
    禁止对返回的连接调用 .close() —— 生命周期由池管理。
    
    Args:
        db_name: 数据库文件名或绝对路径
                 - 相对名 (如 "tools.db") → 解析到数据目录
                 - 绝对路径 (如 "/tmp/test.db") → 直接使用 (测试隔离)
    
    Returns:
        sqlite3.Connection: 已配置 WAL + 线程安全 + 忙等的连接
    
    连接特性:
        - PRAGMA journal_mode=WAL        (并发读写)
        - PRAGMA busy_timeout=30000      (30秒忙等)
        - PRAGMA synchronous=NORMAL      (性能优化，WAL下安全)
        - PRAGMA cache_size=-64000       (64MB缓存)
        - PRAGMA foreign_keys=ON         (外键约束)
        - check_same_thread=False        (跨线程安全)
    """
    # ── Input validation: db_name ────────────────────────────────────────
    if not db_name.startswith("/") and not db_name.endswith(":memory:"):
        from evolution.security.input_validator import InputValidator
        import os as _os
        result = InputValidator.validate_db_path(_os.path.basename(db_name))
        if not result.valid:
            raise ValueError("; ".join(result.errors))

    from evolution.db_pool import db_pool
    return db_pool._get_connection(db_name)


def close_all_connections():
    """关闭所有缓存的数据库连接"""
    with _cache_lock:
        for db_path, conn in list(_connection_cache.items()):
            try:
                conn.close()
                logger.debug("关闭数据库连接: %s", db_path)
            except Exception as e:
                logger.warning("关闭连接失败 %s: %s", db_path, e)
        _connection_cache.clear()


def wal_checkpoint(db_name: str, mode: str = "PASSIVE") -> dict:
    """
    执行 WAL checkpoint，将 WAL 内容写回主数据库并截断 WAL 文件。
    
    防止 WAL 文件无限制增长（已在生产环境出现过 89GB WAL）。
    
    Args:
        db_name: 数据库名或绝对路径
        mode: checkpoint 模式 — PASSIVE(默认)/FULL/RESTART/TRUNCATE
    
    Returns:
        dict: {busy, log_pages, checkpointed_pages}
    
    TRUNCATE 模式会截断 WAL 文件为零，效果最彻底但会阻塞写入。
    PASSIVE 模式不阻塞但可能无法完成全部 checkpoint。
    """
    conn = get_evolution_db(db_name)
    # 先尝试 PASSIVE（不阻塞），如果 WAL 太大改用 TRUNCATE
    result = conn.execute(f"PRAGMA wal_checkpoint({mode})").fetchone()
    wal_size = _get_wal_size(db_name)
    logger.info(
        "WAL checkpoint (%s): busy=%s, log=%s, checkpointed=%s, wal_size=%s",
        mode, result[0], result[1], result[2],
        f"{wal_size / 1024 / 1024:.1f}MB" if wal_size else "N/A"
    )
    return {"busy": result[0], "log_pages": result[1], "checkpointed_pages": result[2]}


def _get_wal_size(db_name: str) -> int:
    """获取 WAL 文件大小（字节），不存在则返回 0"""
    if os.path.isabs(db_name):
        db_path = db_name
    else:
        db_path = str(_resolve_data_dir() / db_name)
    wal_path = db_path + "-wal"
    if os.path.exists(wal_path):
        return os.path.getsize(wal_path)
    return 0


def auto_checkpoint_if_needed(db_name: str, max_wal_mb: int = 100):
    """
    如果 WAL 文件超过指定大小，自动执行 checkpoint。
    
    应在每次大量写入操作后调用。
    """
    wal_bytes = _get_wal_size(db_name)
    wal_mb = wal_bytes / 1024 / 1024
    if wal_mb > max_wal_mb:
        logger.warning("WAL 文件过大 (%.1fMB)，执行 checkpoint...", wal_mb)
        wal_checkpoint(db_name, mode="PASSIVE")
        # 如果 PASSIVE 无法清完，强制 TRUNCATE
        remaining = _get_wal_size(db_name) / 1024 / 1024
        if remaining > max_wal_mb:
            logger.warning("PASSIVE 后 WAL 仍 %.1fMB，执行 TRUNCATE...", remaining)
            wal_checkpoint(db_name, mode="TRUNCATE")


def vacuum_database(db_name: str):
    """压缩指定数据库"""
    conn = get_evolution_db(db_name)
    conn.execute("VACUUM")
    logger.info("数据库压缩完成: %s", db_name)


# ── 重试装饰器 ────────────────────────────────────────────────────────────────

import time
import functools
from typing import Callable, TypeVar

T = TypeVar("T")


def retry_on_db_error(
    max_attempts: int = 3,
    backoff_base: float = 2.0,
    max_backoff: float = 30.0,
):
    """
    数据库操作重试装饰器。
    
    遇到 sqlite3.OperationalError (如 database locked) 时自动重试，
    使用指数退避: 2s → 4s → 8s (上限30s)。
    
    Args:
        max_attempts: 最大尝试次数 (含首次)
        backoff_base: 退避基数 (秒)
        max_backoff: 最大退避时间 (秒)
    
    用法:
        @retry_on_db_error(max_attempts=3)
        def write_something(conn):
            conn.execute("INSERT ...")
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except sqlite3.OperationalError as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        wait = min(backoff_base ** (attempt + 1), max_backoff)
                        logger.warning(
                            "数据库操作失败 (attempt %d/%d): %s — %ss 后重试",
                            attempt + 1, max_attempts, e, wait
                        )
                        time.sleep(wait)
                    else:
                        logger.error(
                            "数据库操作最终失败 (attempt %d/%d): %s",
                            attempt + 1, max_attempts, e
                        )
            raise last_exception
        return wrapper
    return decorator


# ── 便捷查询 ──────────────────────────────────────────────────────────────────

def db_table_exists(db_name: str, table_name: str) -> bool:
    """检查表是否存在"""
    conn = get_evolution_db(db_name)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
        (table_name,)
    )
    return cursor.fetchone() is not None


def db_get_stats(db_name: str) -> dict:
    """获取数据库统计信息"""
    conn = get_evolution_db(db_name)
    db_path = str(_resolve_data_dir() / db_name)
    
    stats = {
        "db_name": db_name,
        "exists": os.path.exists(db_path),
        "file_size_kb": 0,
        "tables": [],
    }
    
    if stats["exists"]:
        stats["file_size_kb"] = round(os.path.getsize(db_path) / 1024, 1)
    
    try:
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        for row in cursor:
            table_name = row[0]
            count_cursor = conn.execute(f"SELECT COUNT(*) FROM [{table_name}]")
            count = count_cursor.fetchone()[0]
            stats["tables"].append({"name": table_name, "rows": count})
    except Exception as e:
        logger.warning("获取表统计失败: %s", e)
    
    return stats

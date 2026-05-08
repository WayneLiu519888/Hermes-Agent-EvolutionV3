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

_connection_cache: dict = {}
_cache_lock = threading.Lock()


def get_evolution_db(db_name: str) -> sqlite3.Connection:
    """
    获取线程安全的 SQLite 连接。
    
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
        - PRAGMA cache_size=-8000        (8MB缓存)
        - PRAGMA foreign_keys=ON         (外键约束)
        - check_same_thread=False        (跨线程安全)
    
    连接按 db_path 缓存复用。缓存是线程安全的。
    """
    # 绝对路径 → 直接使用 (测试隔离/自定义路径)
    if os.path.isabs(db_name):
        db_path = db_name
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
    else:
        data_dir = _resolve_data_dir()
        db_path = str(data_dir / db_name)
    
    with _cache_lock:
        if db_path in _connection_cache:
            conn = _connection_cache[db_path]
            # 验证连接仍然有效
            try:
                conn.execute("SELECT 1")
                return conn
            except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                # 连接已关闭或无效，重新创建
                logger.debug("缓存的连接已失效，重新创建: %s", db_path)
                del _connection_cache[db_path]
        
        # 创建新连接
        conn = sqlite3.connect(
            db_path,
            check_same_thread=False,
            timeout=30.0,
        )
        conn.row_factory = sqlite3.Row
        
        # 配置 PRAGMA
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=30000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-8000")  # 8MB
        conn.execute("PRAGMA foreign_keys=ON")
        
        _connection_cache[db_path] = conn
        logger.debug("创建数据库连接: %s (WAL模式)", db_path)
        return conn


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

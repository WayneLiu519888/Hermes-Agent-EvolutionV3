"""
Evolution DatabasePool — 统一数据库连接池

解决当前 db_utils 连接缓存的三个问题：
1. conn.close() 泛滥导致缓存失效 → contextmanager 禁止 close
2. checkpoint 分散在各模块 → checkpoint_all() 统一调度
3. 裸 sqlite3.connect() 绕过工厂 → 唯一连接入口

用法:
    from evolution.db_pool import db_pool

    with db_pool.connection("tools.db") as conn:
        conn.execute("SELECT ...")

    db_pool.checkpoint_all()
"""

import os
import sqlite3
import threading
import logging
from contextlib import contextmanager
from pathlib import Path
from evolution.db_utils import _resolve_data_dir

logger = logging.getLogger(__name__)


class DatabasePool:
    """
    统一数据库连接池。解决当前 db_utils 连接缓存的三个问题：
    1. conn.close() 泛滥导致缓存失效 → contextmanager 禁止 close
    2. checkpoint 分散在各模块 → checkpoint_all() 统一调度
    3. 裸 sqlite3.connect() 绕过工厂 → 唯一连接入口
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._connections = {}
                    cls._instance._conn_lock = threading.Lock()
        return cls._instance

    def _resolve_path(self, db_name: str) -> str:
        """将逻辑数据库名解析为文件系统路径"""
        if db_name.endswith(":memory:") or db_name.startswith("/"):
            return db_name
        return str(_resolve_data_dir() / db_name)

    def _get_connection(self, db_name: str) -> sqlite3.Connection:
        """获取或创建数据库连接（线程安全）"""
        db_path = self._resolve_path(db_name)
        with self._conn_lock:
            if db_path in self._connections:
                conn = self._connections[db_path]
                try:
                    conn.execute("SELECT 1")
                    return conn
                except (sqlite3.ProgrammingError, sqlite3.OperationalError):
                    logger.warning("Stale connection detected for %s, reconnecting", db_path)
                    try:
                        conn.close()
                    except Exception:
                        pass
                    del self._connections[db_path]

            conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA busy_timeout=30000")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA cache_size=-64000")  # 64MB 页缓存
            conn.execute("PRAGMA foreign_keys=ON")
            self._connections[db_path] = conn
            logger.debug("Created new connection for %s", db_path)
            return conn

    @contextmanager
    def connection(self, db_name: str):
        """
        获取数据库连接的上下文管理器。禁止手动 close()。

        用法:
            with db_pool.connection("tools.db") as conn:
                rows = conn.execute("SELECT * FROM tools").fetchall()
        """
        conn = self._get_connection(db_name)
        try:
            yield conn
        finally:
            pass  # 连接归还池，不关闭

    def checkpoint_all(self, max_wal_mb: int = 100):
        """
        对所有数据库执行 WAL checkpoint。

        当 WAL 文件超过 max_wal_mb 时触发 PASSIVE checkpoint。
        建议在守护进程的周期任务中调用（如每 60 秒）。
        """
        checkpointed = 0
        with self._conn_lock:
            for db_path, conn in list(self._connections.items()):
                wal_path = db_path + "-wal"
                if os.path.exists(wal_path):
                    wal_mb = os.path.getsize(wal_path) / 1024 / 1024
                    if wal_mb > max_wal_mb:
                        try:
                            conn.execute("PRAGMA wal_checkpoint(PASSIVE)")
                            checkpointed += 1
                            logger.debug("Checkpointed %s (WAL: %.1f MB)", db_path, wal_mb)
                        except Exception as e:
                            logger.warning("Checkpoint failed for %s: %s", db_path, e)

        if checkpointed > 0:
            logger.info("Checkpointed %d database(s)", checkpointed)

    def close_all(self):
        """进程退出时统一关闭所有连接"""
        with self._conn_lock:
            for db_path, conn in list(self._connections.items()):
                try:
                    conn.close()
                    logger.debug("Closed connection: %s", db_path)
                except Exception as e:
                    logger.warning("Error closing %s: %s", db_path, e)
            self._connections.clear()
            logger.info("All database connections closed")

    def stats(self) -> dict:
        """返回连接池统计信息"""
        with self._conn_lock:
            return {
                "pool_size": len(self._connections),
                "connections": list(self._connections.keys()),
            }


# 全局单例
db_pool = DatabasePool()

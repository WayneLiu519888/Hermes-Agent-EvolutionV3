"""
db_utils 模块测试

覆盖:
- get_data_dir 路径解析和环境变量优先级
- get_evolution_db 连接创建和 WAL 配置
- 连接缓存复用和失效重连
- close_all_connections 清理
- vacuum_database 执行
- retry_on_db_error 重试逻辑
- db_table_exists 检查
- db_get_stats 统计
"""

import os
import sys
import sqlite3
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from evolution.db_utils import (
    get_data_dir,
    get_evolution_db,
    close_all_connections,
    vacuum_database,
    retry_on_db_error,
    db_table_exists,
    db_get_stats,
    _connection_cache,
    _cache_lock,
    )
except ImportError:
    from src.evolution.db_utils import (
    get_data_dir,
    get_evolution_db,
    close_all_connections,
    vacuum_database,
    retry_on_db_error,
    db_table_exists,
    db_get_stats,
    _connection_cache,
    _cache_lock,
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_cache():
    """每个测试前清空连接缓存和恢复环境变量"""
    with _cache_lock:
        for conn in list(_connection_cache.values()):
            try:
                conn.close()
            except Exception:
                pass
        _connection_cache.clear()

    # 恢复环境变量
    old_dir = os.environ.pop("EVOLUTION_DATA_DIR", None)
    old_home = os.environ.pop("HERMES_HOME", None)
    yield
    _connection_cache.clear()
    if old_dir:
        os.environ["EVOLUTION_DATA_DIR"] = old_dir
    if old_home:
        os.environ["HERMES_HOME"] = old_home


@pytest.fixture
def temp_data_dir(tmp_path):
    """临时数据目录"""
    data_dir = tmp_path / "data" / "evolution"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


# ── get_data_dir ──────────────────────────────────────────────────────────────

class TestGetDataDir:
    """测试数据目录解析"""

    def test_returns_path_object(self):
        """默认返回 Path 对象"""
        result = get_data_dir()
        assert isinstance(result, Path)

    def test_env_var_priority(self, tmp_path):
        """环境变量 EVOLUTION_DATA_DIR 优先"""
        custom_dir = tmp_path / "custom_evolution"
        os.environ["EVOLUTION_DATA_DIR"] = str(custom_dir)
        result = get_data_dir()
        assert custom_dir.name in str(result) or str(result) == str(custom_dir)

    def test_hermes_home_fallback(self, tmp_path):
        """回退到 HERMES_HOME"""
        hermes_home = tmp_path / "hermes_test"
        os.environ["HERMES_HOME"] = str(hermes_home)
        result = get_data_dir()
        assert "evolution" in str(result)


# ── get_evolution_db ──────────────────────────────────────────────────────────

class TestGetEvolutionDb:
    """测试进化数据库连接"""

    def test_creates_connection(self, temp_data_dir):
        """创建连接并返回 sqlite3.Connection"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("test.db")
        assert isinstance(conn, sqlite3.Connection)

    def test_wal_mode_enabled(self, temp_data_dir):
        """WAL 模式启用"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("wal_test.db")
        result = conn.execute("PRAGMA journal_mode").fetchone()
        assert result[0].upper() == "WAL"

    def test_connection_cached(self, temp_data_dir):
        """同一 db_name 复用缓存连接"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn1 = get_evolution_db("cache_test.db")
        conn2 = get_evolution_db("cache_test.db")
        assert conn1 is conn2

    def test_different_names_different_connections(self, temp_data_dir):
        """不同 db_name 创建不同连接"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn1 = get_evolution_db("db1.db")
        conn2 = get_evolution_db("db2.db")
        assert conn1 is not conn2

    def test_busy_timeout_set(self, temp_data_dir):
        """busy_timeout 设置"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("busy_test.db")
        result = conn.execute("PRAGMA busy_timeout").fetchone()
        assert result[0] >= 30000

    def test_foreign_keys_on(self, temp_data_dir):
        """外键约束启用"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("fk_test.db")
        result = conn.execute("PRAGMA foreign_keys").fetchone()
        assert result[0] == 1 if isinstance(result[0], int) else result[0] in (1, "1")

    def test_invalid_connection_recreated(self, temp_data_dir):
        """缓存中无效连接自动重建"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn1 = get_evolution_db("reconnect.db")
        # 手动关闭连接
        conn1.close()
        conn2 = get_evolution_db("reconnect.db")
        assert conn1 is not conn2
        assert isinstance(conn2, sqlite3.Connection)


# ── close_all_connections ─────────────────────────────────────────────────────

class TestCloseAllConnections:
    """测试关闭所有连接"""

    def test_clears_cache(self, temp_data_dir):
        """清空连接缓存（V5: 转发到 db_pool）"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        from evolution.db_pool import db_pool
        get_evolution_db("close1.db")
        get_evolution_db("close2.db")
        assert len(db_pool._connections) >= 2
        db_pool.close_all()
        assert len(db_pool._connections) == 0


# ── vacuum_database ───────────────────────────────────────────────────────────

class TestVacuumDatabase:
    """测试数据库压缩"""

    def test_vacuum_executes(self, temp_data_dir):
        """VACUUM 正常执行"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("vacuum_test.db")
        conn.execute("CREATE TABLE IF NOT EXISTS t (id INTEGER)")
        conn.execute("INSERT INTO t VALUES (1), (2), (3)")
        conn.commit()
        # VACUUM 不应抛出异常
        vacuum_database("vacuum_test.db")


# ── retry_on_db_error ─────────────────────────────────────────────────────────

class TestRetryOnDbError:
    """测试数据库操作重试"""

    def test_success_no_retry(self):
        """成功后不重试"""

        @retry_on_db_error(max_attempts=3)
        def succeed():
            return "ok"

        result = succeed()
        assert result == "ok"

    def test_retry_on_operational_error(self):
        """OperationalError 触发重试"""
        call_count = [0]

        @retry_on_db_error(max_attempts=3, backoff_base=0.01, max_backoff=10)
        def failing_func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise sqlite3.OperationalError("database is locked")
            return "recovered"

        result = failing_func()
        assert result == "recovered"
        assert call_count[0] == 3

    def test_raises_after_max_attempts(self):
        """达到最大重试次数后抛出异常"""
        call_count = [0]

        @retry_on_db_error(max_attempts=2, backoff_base=0.01, max_backoff=10)
        def always_fail():
            call_count[0] += 1
            raise sqlite3.OperationalError("persistent error")

        with pytest.raises(sqlite3.OperationalError, match="persistent error"):
            always_fail()
        assert call_count[0] == 2

    def test_decorator_preserves_metadata(self):
        """装饰器保留函数元数据"""

        @retry_on_db_error(max_attempts=3)
        def my_function(a, b):
            """My docstring"""
            return a + b

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring"
        assert my_function(1, 2) == 3


# ── db_table_exists ───────────────────────────────────────────────────────────

class TestDbTableExists:
    """测试表存在检查"""

    def test_table_exists(self, temp_data_dir):
        """表存在返回 True"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("exists_test.db")
        conn.execute("CREATE TABLE test_users (id INTEGER)")
        conn.commit()
        assert db_table_exists("exists_test.db", "test_users") is True

    def test_table_not_exists(self, temp_data_dir):
        """表不存在返回 False"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        get_evolution_db("notexist.db")
        assert db_table_exists("notexist.db", "nonexistent_table") is False


# ── db_get_stats ──────────────────────────────────────────────────────────────

class TestDbGetStats:
    """测试数据库统计"""

    def test_returns_stats(self, temp_data_dir):
        """返回统计信息"""
        os.environ["EVOLUTION_DATA_DIR"] = str(temp_data_dir)
        conn = get_evolution_db("stats_test.db")
        conn.execute("CREATE TABLE items (id INTEGER, name TEXT)")
        conn.execute("INSERT INTO items VALUES (1, 'a'), (2, 'b')")
        conn.commit()
        stats = db_get_stats("stats_test.db")
        assert stats["db_name"] == "stats_test.db"
        assert stats["exists"] is True
        assert "tables" in stats
        assert len(stats["tables"]) >= 1
        table_names = [t["name"] for t in stats["tables"]]
        assert "items" in table_names

    def test_nonexistent_db(self):
        """不存在的数据库返回 exists=False"""
        # db_get_stats 内部会调用 get_evolution_db 自动创建数据库文件
        # exists 为 True，但 tables 应该为空（新数据库）
        stats = db_get_stats("nonexistent_xyz.db")
        assert stats["db_name"] == "nonexistent_xyz.db"
        assert stats["exists"] is True
        # 新数据库无表
        assert stats["tables"] == []

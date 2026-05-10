"""
进化系统健康检查测试

覆盖 health.py 的 health_check() 和 print_health() 函数。
通过 mock 数据库、SelfMonitor、Memory 等组件验证三种 overall 状态。
"""
import sys
import os
import sqlite3
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from evolution.health import health_check, print_health
except ImportError:
    from src.evolution.health import health_check, print_health


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_stat_result(st_size=0, st_mtime=None):
    """Create a fake os.stat_result-like object with specific st_size and st_mtime."""
    if st_mtime is None:
        st_mtime = datetime.now().timestamp()
    mock = MagicMock()
    mock.st_size = st_size
    mock.st_mtime = st_mtime
    return mock


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def temp_data_dir():
    """创建临时数据目录，含假 .db 文件"""
    with tempfile.TemporaryDirectory() as tmpdir:
        data_dir = Path(tmpdir)
        # 创建 assocations.db
        db_path = data_dir / "associations.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE IF NOT EXISTS test_table (id INTEGER PRIMARY KEY)")
        conn.execute("INSERT INTO test_table VALUES (1)")
        conn.execute("INSERT INTO test_table VALUES (2)")
        conn.execute("CREATE TABLE IF NOT EXISTS other_table (key TEXT)")
        conn.execute("INSERT INTO other_table VALUES ('a')")
        conn.commit()
        conn.close()
        # 再创建一个额外的 .db 文件
        extra_db = data_dir / "extra.db"
        extra_db.touch()
        yield data_dir


def _setup_base_mocks(temp_data_dir, *, db_ok=True, monitor_ok=True,
                      plugin_ok=True, memory_ok=True):
    """Build a context manager stack for the 4 components.

    Returns a context manager using ExitStack-like nesting via nested with statements.
    Actually returns individual patch objects that can be composed via `with a, b, c:`.
    """
    patches = []

    # DB
    if db_ok:
        patches.append(patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir))
    else:
        patches.append(patch("evolution.db_utils.get_data_dir",
                             side_effect=Exception("DB fail")))

    return patches


# ── health_check 测试 ──────────────────────────────────────────────────────────

class TestHealthCheck:
    """health_check() 函数测试"""

    def test_healthy_all_ok(self, temp_data_dir):
        """所有组件正常 → overall=healthy"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {
            "success_rate": 0.95, "total_cycles": 100,
            "tool_stats": {"search": 50, "write": 50},
        }
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 42
        mock_mdb.count_associations.return_value = 15

        # We need to carefully mock paths for plugin:
        # plugin_yaml = Path.home() / ".hermes" / "plugins" / "hermes-evolution" / "plugin.yaml"
        # We'll patch Path.home() and make the constructed path behave correctly
        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb), \
             patch.object(Path, "home", return_value=temp_data_dir):
            # Now the plugin path becomes temp_data_dir / .hermes / plugins / hermes-evolution / plugin.yaml
            # Since Path.exists and Path.stat are not mocked, this file doesn't exist,
            # so plugin status = "missing" → overall = "degraded".
            # To get healthy, we need the plugin to appear as existing with valid stat.
            # We can always just accept "degraded" if plugin is missing, OR we mock the
            # specific path. Simpler: don't test print_health; test that with plugin missing
            # we get degraded. For "healthy", we need the plugin path to exist.

            # Actually, the simplest approach: mock the plugin path builder to point to a real file
            plugin_dir = temp_data_dir / ".hermes" / "plugins" / "hermes-evolution"
            plugin_dir.mkdir(parents=True, exist_ok=True)
            plugin_file = plugin_dir / "plugin.yaml"
            plugin_file.write_text("version: 1.0")
            # Now plugin_yaml.exists() will be True and stat() will work
            result = health_check(data_dir=temp_data_dir)

        assert result["overall"] == "healthy"
        assert result["components"]["db"]["status"] == "ok"
        assert result["components"]["monitor"]["status"] == "ok"
        assert result["components"]["memory"]["status"] == "ok"
        assert result["components"]["plugin"]["status"] == "ok"
        assert len(result["warnings"]) == 0

    def test_degraded_missing_plugin(self, temp_data_dir):
        """插件缺失 → overall=degraded"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {"success_rate": 0.95}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 10
        mock_mdb.count_associations.return_value = 5

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb), \
             patch.object(Path, "exists", return_value=False):
            result = health_check(data_dir=temp_data_dir)

        assert result["overall"] == "degraded"
        assert result["components"]["plugin"]["status"] == "missing"
        assert any("插件未部署" in w for w in result["warnings"])

    def test_critical_two_errors(self, temp_data_dir):
        """2个组件 error (非plugin) → overall=critical.

        Plugin ok, monitor error, memory error → error_count=2 → critical.
        """
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        # Need plugin to exist so it doesn't pre-set degraded
        plugin_dir = temp_data_dir / ".hermes" / "plugins" / "hermes-evolution"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "plugin.yaml").write_text("v1")

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", side_effect=Exception("monitor crash")), \
             patch("evolution.memory.database.AssociationDatabase",
                   side_effect=Exception("memory crash")), \
             patch.object(Path, "home", return_value=temp_data_dir):
            # plugin path will resolve to our real plugin.yaml → status=ok
            result = health_check(data_dir=temp_data_dir)

        assert result["overall"] == "critical"
        assert result["components"]["monitor"]["status"] == "error"
        assert result["components"]["memory"]["status"] == "error"
        assert result["components"]["plugin"]["status"] == "ok"

    def test_db_error_handling(self, temp_data_dir):
        """DB 检查抛出异常时降级处理"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {"success_rate": 0.8}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", side_effect=Exception("DB connection failed")), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "exists", return_value=True), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = health_check(data_dir=temp_data_dir)

        assert result["components"]["db"]["status"] == "error"
        assert any("DB 检查失败" in str(w) for w in result["warnings"])

    def test_no_db_files(self, temp_data_dir):
        """data_dir 下无 .db 文件时仍正常工作"""
        empty_dir = temp_data_dir / "empty"
        empty_dir.mkdir()
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", return_value=empty_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "exists", return_value=True), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = health_check(data_dir=empty_dir)

        assert result["components"]["db"]["status"] == "ok"
        assert result["components"]["db"]["file_count"] == 0
        assert result["components"]["db"]["total_size_kb"] == 0.0

    def test_large_db_warning(self, temp_data_dir):
        """DB 总大小 >10000KB 时触发警告"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        # Need plugin to exist to avoid plugin-missing degraded overwrite
        plugin_dir = temp_data_dir / ".hermes" / "plugins" / "hermes-evolution"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "plugin.yaml").write_text("v1")

        # Mock stat to return large file sizes for .db files only
        # health.py does: f.stat().st_size for f in db_files
        # and also: plugin_yaml.stat().st_mtime
        # We must let plugin_yaml.stat() work normally while faking .db sizes
        orig_stat = Path.stat

        def selective_stat(self, *, follow_symlinks=True):
            result = orig_stat(self, follow_symlinks=follow_symlinks)
            if self.suffix == '.db':
                # Use a real os.stat_result but with modified st_size
                # We can't modify os.stat_result, so we create a tuple-like mock
                fake = MagicMock()
                fake.st_size = 6 * 1024 * 1024  # 6MB per file
                fake.st_mtime = result.st_mtime
                return fake
            return result

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb), \
             patch.object(Path, "home", return_value=temp_data_dir), \
             patch.object(Path, "stat", selective_stat):
            result = health_check(data_dir=temp_data_dir)

        assert any("超大" in w for w in result["warnings"])

    def test_monitor_import_error(self, temp_data_dir):
        """SelfMonitor ImportError → status=unavailable"""
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", side_effect=ImportError("No module")), \
             patch.object(Path, "exists", return_value=True), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = health_check(data_dir=temp_data_dir)

        assert result["components"]["monitor"]["status"] == "unavailable"

    def test_memory_import_error(self, temp_data_dir):
        """Memory ImportError → status=unavailable"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "exists", return_value=True), \
             patch("evolution.memory.database.AssociationDatabase",
                   side_effect=ImportError("No module")):
            result = health_check(data_dir=temp_data_dir)

        assert result["components"]["memory"]["status"] == "unavailable"

    def test_timestamp_present(self, temp_data_dir):
        """验证返回结果包含所有必需字段"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "exists", return_value=True), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = health_check(data_dir=temp_data_dir)

        assert "timestamp" in result
        assert "overall" in result
        assert "components" in result
        assert "warnings" in result
        assert "recommendations" in result

    def test_degraded_single_error(self, temp_data_dir):
        """1个 error/missing 且原本 healthy → overall=degraded (非 plugin 触发)"""
        # Plugin OK (exists), monitor OK, DB error → error_count=1 → degraded
        plugin_dir = temp_data_dir / ".hermes" / "plugins" / "hermes-evolution"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "plugin.yaml").write_text("v1")

        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", side_effect=Exception("fail")), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "home", return_value=temp_data_dir), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = health_check(data_dir=temp_data_dir)

        assert result["overall"] == "degraded"

    def test_db_with_tables(self, temp_data_dir):
        """验证数据库有表时返回 tables 和 row_counts"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "exists", return_value=True), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = health_check(data_dir=temp_data_dir)

        db = result["components"]["db"]
        assert db["status"] == "ok"
        assert "tables" in db
        assert "row_counts" in db
        assert "test_table" in db["tables"]
        assert db["row_counts"]["test_table"] == 2


# ── print_health 测试 ──────────────────────────────────────────────────────────

class TestPrintHealth:
    """print_health() 函数测试"""

    def test_print_health_healthy(self, capsys, temp_data_dir):
        """健康状态打印并返回 True"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        # Plugin present → overall=healthy
        plugin_dir = temp_data_dir / ".hermes" / "plugins" / "hermes-evolution"
        plugin_dir.mkdir(parents=True, exist_ok=True)
        (plugin_dir / "plugin.yaml").write_text("v1")

        with patch("evolution.db_utils.get_data_dir", return_value=temp_data_dir), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "home", return_value=temp_data_dir), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = print_health(data_dir=temp_data_dir)

        assert result is True
        captured = capsys.readouterr()
        assert "总体状态" in captured.out
        assert "✅" in captured.out

    def test_print_health_unhealthy(self, capsys, temp_data_dir):
        """非健康状态打印并返回 False"""
        mock_monitor = MagicMock()
        mock_monitor.get_stats.return_value = {}
        mock_mdb = MagicMock()
        mock_mdb.count_entries.return_value = 0
        mock_mdb.count_associations.return_value = 0

        with patch("evolution.db_utils.get_data_dir", side_effect=Exception("fail")), \
             patch("evolution.self_monitor.SelfMonitor", return_value=mock_monitor), \
             patch.object(Path, "exists", return_value=False), \
             patch("evolution.memory.database.AssociationDatabase", return_value=mock_mdb):
            result = print_health(data_dir=temp_data_dir)

        assert result is False
        captured = capsys.readouterr()
        assert "总体状态" in captured.out

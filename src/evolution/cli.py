"""
HermesAgentEvolution CLI — 命令行工具

用法:
    python3 -m src.evolution.cli check     # 环境自检
    python3 -m src.evolution.cli setup     # 一键部署到 Hermes
    python3 -m src.evolution.cli status    # 查看系统状态
    python3 -m src.evolution.cli test      # 运行自测
"""

import sys
import os
from pathlib import Path

# 确保项目根在 sys.path
_project_root = Path(__file__).resolve().parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))


def _add_src_to_path():
    """确保 src/ 可导入"""
    src_dir = Path(__file__).resolve().parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def cmd_check() -> bool:
    """环境自检：Python版本、模块导入、DB连接、插件部署"""
    _add_src_to_path()
    
    all_ok = True
    results = []
    
    def _check(name: str, ok: bool, detail: str = ""):
        nonlocal all_ok
        if not ok:
            all_ok = False
        results.append((name, ok, detail))
    
    # 1. Python 版本
    vi = sys.version_info
    _check(
        f"Python {vi.major}.{vi.minor}.{vi.micro} ≥ 3.9",
        vi >= (3, 9),
        f"当前 Python {vi.major}.{vi.minor}" if vi < (3, 9) else ""
    )
    
    # 2. 核心模块导入
    core_modules = [
        ("evolution.tools.tool_registry", "工具注册表"),
        ("evolution.learning.observer", "学习观察器"),
        ("evolution.memory.database", "记忆数据库"),
        ("evolution.security.audit_logger", "安全审计"),
        ("evolution.collaboration.agent_orchestrator", "协作编排"),
        ("evolution.closed_loop.orchestrator", "闭环编排"),
        ("evolution.self_monitor", "自我监控"),
        ("evolution.db_utils", "DB工具"),
    ]
    
    for mod_name, desc in core_modules:
        try:
            __import__(mod_name)
            _check(f"模块 {desc}", True)
        except ImportError as e:
            _check(f"模块 {desc}", False, str(e))
    
    # 3. DB 可读写
    try:
        from evolution.db_utils import get_evolution_db, close_all_connections
        conn = get_evolution_db("_cli_check.db")
        conn.execute("CREATE TABLE IF NOT EXISTS _check (id INTEGER)")
        conn.execute("INSERT INTO _check VALUES (1)")
        conn.execute("DROP TABLE _check")
        conn.commit()
        close_all_connections()
        _check("DB 可读写", True)
    except Exception as e:
        _check("DB 可读写", False, str(e))
    
    # 4. Hermes 插件已部署
    plugin_dir = Path.home() / ".hermes" / "plugins" / "hermes-evolution"
    plugin_yaml = plugin_dir / "plugin.yaml"
    _check(
        "Hermes 插件已部署",
        plugin_yaml.exists(),
        f"未找到 {plugin_yaml}" if not plugin_yaml.exists() else ""
    )
    
    # 5. 数据目录
    from evolution.db_utils import _resolve_data_dir
    data_dir = _resolve_data_dir()
    _check(f"数据目录: {data_dir}", data_dir.exists())
    
    # 输出
    print()
    print("🔍 HermesAgentEvolution 环境自检")
    print("=" * 50)
    for name, ok, detail in results:
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")
        if detail:
            print(f"     → {detail}")
    print("=" * 50)
    
    if all_ok:
        print("  🎉 环境就绪，可以正常使用")
    else:
        print("  ⚠️  存在异常，请根据上述提示修复")
    
    return all_ok


def cmd_setup() -> bool:
    """一键部署：复制插件到 ~/.hermes/plugins/"""
    _add_src_to_path()
    
    # 从包内资源读取插件文件（pip/pipx 安装后也能工作）
    try:
        from importlib.resources import files
        plugin_pkg = files("evolution._plugin")
    except ImportError:
        # Python < 3.9 fallback
        import pkg_resources
        plugin_pkg = pkg_resources.resource_filename("evolution._plugin", "")
        plugin_pkg = Path(plugin_pkg)
    
    plugin_dst = Path.home() / ".hermes" / "plugins" / "hermes-evolution"
    
    print("🚀 HermesAgentEvolution 插件部署")
    print(f"   目标: {plugin_dst}")
    
    # 复制文件
    import shutil
    plugin_dst.mkdir(parents=True, exist_ok=True)
    
    # plugin.yaml 和 __init__.py 从包资源复制
    for name in ("plugin.yaml", "__init__.py"):
        src = plugin_pkg / name if isinstance(plugin_pkg, Path) else plugin_pkg.joinpath(name)
        if hasattr(src, 'read_bytes'):
            # importlib.resources.Traversable
            content = src.read_bytes()
            (plugin_dst / name).write_bytes(content)
        elif src.exists():
            shutil.copy2(src, plugin_dst / name)
        else:
            print(f"   ⚠️  缺少插件文件: {name}")
            return False
    
    print(f"   ✅ 插件已部署")
    
    # 尝试启用插件
    import subprocess
    try:
        subprocess.run(
            ["hermes", "plugins", "enable", "hermes-evolution"],
            capture_output=True, timeout=10
        )
        print(f"   ✅ 插件已启用")
    except Exception:
        print(f"   ⚠️  请手动启用: hermes plugins enable hermes-evolution")
    
    # 提示重启
    print()
    print("   ⚠️  插件将在下次 Hermes 会话生效")
    print("   如需立即生效: hermes gateway restart (会断开当前会话)")
    
    return True


def cmd_status() -> bool:
    """查看系统状态"""
    _add_src_to_path()
    
    print("📊 HermesAgentEvolution 系统状态")
    print("=" * 50)
    
    # 版本
    try:
        import re
        pyproject = _project_root / "pyproject.toml"
        content = pyproject.read_text()
        m = re.search(r'version\s*=\s*"([^"]+)"', content)
        version = m.group(1) if m else "unknown"
        print(f"  版本: v{version}")
    except Exception:
        print(f"  版本: 无法读取")
    
    # 模块统计
    try:
        src_dir = _project_root / "src" / "evolution"
        py_files = list(src_dir.rglob("*.py"))
        total_lines = 0
        for f in py_files:
            total_lines += len(f.read_text().splitlines())
        print(f"  模块: {len(py_files)} 文件")
        print(f"  代码: {total_lines} 行")
    except Exception as e:
        print(f"  代码统计失败: {e}")
    
    # 测试状态
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=no"],
        cwd=_project_root,
        capture_output=True, text=True, timeout=60
    )
    print(f"  测试: {result.stdout.strip().splitlines()[-1] if result.stdout else '无法运行'}")
    
    # DB 统计
    try:
        from evolution.db_utils import get_data_dir, db_get_stats
        data_dir = get_data_dir()
        db_files = list(data_dir.glob("*.db"))
        print(f"  DB文件: {len(db_files)} 个 ({data_dir})")
        for db in db_files:
            size_kb = db.stat().st_size / 1024
            print(f"    - {db.name}: {size_kb:.1f} KB")
    except Exception as e:
        print(f"  DB统计失败: {e}")
    
    print("=" * 50)
    return True


def cmd_test() -> bool:
    """运行自测"""
    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--tb=line"],
        cwd=_project_root,
        timeout=180
    )
    return result.returncode == 0


# ── CLI 入口 ────────────────────────────────────────────────────────────────────

COMMANDS = {
    "check":  (cmd_check,  "环境自检"),
    "setup":  (cmd_setup,  "一键部署到 Hermes"),
    "status": (cmd_status, "查看系统状态"),
    "test":   (cmd_test,   "运行自测"),
}


def main():
    """CLI 主入口"""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("HermesAgentEvolution CLI v3.0.0")
        print()
        print("用法: python3 -m src.evolution.cli <命令>")
        print()
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<10s}  {desc}")
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"❌ 未知命令: {cmd}")
        print(f"   可用: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    
    func, _ = COMMANDS[cmd]
    success = func()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

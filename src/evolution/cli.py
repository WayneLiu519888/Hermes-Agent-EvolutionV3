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

# 延迟导入，避免循环依赖和启动时即检查
_dep_manager = None

def _get_dep_manager():
    """延迟加载 dependency_manager"""
    global _dep_manager
    if _dep_manager is None:
        from evolution.dependency_manager import (
            detect_env, find_missing_modules, auto_fix_missing,
            get_pipx_package
        )
        _dep_manager = (detect_env, find_missing_modules, auto_fix_missing, get_pipx_package)
    return _dep_manager


def _add_src_to_path():
    """确保 src/ 可导入"""
    src_dir = Path(__file__).resolve().parent.parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))


def cmd_check(fix: bool = False, clean: bool = False) -> bool:
    """环境自检：Python版本、模块导入、DB连接、插件部署
    
    Args:
        fix: 如果 True，自动修复缺失的依赖
        clean: 如果 True，清理测试残留
    """
    _add_src_to_path()
    
    all_ok = True
    results = []
    module_checks = []  # 记录模块检查结果，便于后续修复
    
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
            module_checks.append((mod_name, desc, True))
        except ImportError as e:
            _check(f"模块 {desc}", False, str(e))
            module_checks.append((mod_name, desc, False))
    
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
    
    # ── 自动修复模式 ────────────────────────────────────────────────────────────
    if fix and not all_ok:
        detect_env, find_missing_modules, auto_fix_missing, _ = _get_dep_manager()
        env_type = detect_env()
        
        print()
        print("🔧 自动修复模式启动 (--fix)")
        print(f"   环境类型: {env_type}")
        
        # 1. 用 dependency_manager 扫描第三方依赖
        missing = find_missing_modules()
        if missing:
            print(f"   缺失依赖: {', '.join(missing)}")
            fix_results = auto_fix_missing(missing)
            for mod, ok, msg in fix_results:
                if ok:
                    print(f"   ✅ {mod} 已安装")
                else:
                    print(f"   ❌ {mod} 安装失败: {msg}")
        else:
            print("   ✅ 第三方依赖完整")
        
        # 2. 对失败的模块尝试 pip 安装
        failed_modules = [(name, desc) for name, desc, ok in module_checks if not ok]
        for mod_name, desc in failed_modules:
            # 尝试通过 pip 安装（模块名可能与包名不同，取最后一段）
            pkg_candidate = mod_name.split(".")[-1]
            try:
                import subprocess as _sp
                result = _sp.run(
                    [sys.executable, "-m", "pip", "install", "--quiet", pkg_candidate],
                    capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    print(f"   🔄 尝试安装 {pkg_candidate}... 成功")
                else:
                    print(f"   ⚠️  无法自动安装 {pkg_candidate}: {result.stderr.strip()[:100]}")
            except Exception as e:
                print(f"   ⚠️  安装异常 {pkg_candidate}: {e}")
        
        # 3. 重新检查
        print()
        print("🔍 修复后重新自检...")
        all_ok = True
        results.clear()
        
        for mod_name, desc, _ in module_checks:
            try:
                __import__(mod_name)
                _check(f"模块 {desc}", True)
            except ImportError as e:
                _check(f"模块 {desc}", False, str(e))
        
        # 重新检查 DB
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
        
        # 重新检查 插件/数据目录
        _check("Hermes 插件已部署", plugin_yaml.exists(),
               f"未找到 {plugin_yaml}" if not plugin_yaml.exists() else "")
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
    
    # ── 清理模式 ────────────────────────────────────────────────────────────────
    if clean:
        print()
        cmd_clean(dry_run=False)
    
    return all_ok


def cmd_setup() -> bool:
    """一键部署：检查依赖 → 自愈修复 → 复制插件到 ~/.hermes/plugins/"""
    _add_src_to_path()
    
    # ── 0. 环境检测 & pipx 警告 ──────────────────────────────────────────────
    detect_env = _get_dep_manager()[0]
    env_type = detect_env()
    
    if env_type == "pipx":
        print("⚠️  检测到 pipx 环境")
        print("   pipx 使用独立 venv，第三方依赖需通过 `pipx inject` 安装")
        print("   自动修复将使用 pipx inject，可能需要 sudo 权限")
        print()
    
    # ── 1. 自动修复依赖 ──────────────────────────────────────────────────
    print("🔍 检查依赖...")
    if not cmd_check(fix=True):
        print()
        print("⚠️  部分依赖修复失败，继续部署（可能功能受限）")
    else:
        print()
        print("✅ 依赖检查通过")
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

    # ── 部署后校验：确认部署文件与包资源一致 ─────────────────────────
    try:
        import hashlib

        def _file_hash(path):
            with open(path, "rb") as f:
                return hashlib.sha256(f.read()).hexdigest()[:16]

        for name in ("plugin.yaml", "__init__.py"):
            src = plugin_pkg / name if isinstance(plugin_pkg, Path) else plugin_pkg.joinpath(name)
            dst = plugin_dst / name
            src_content = src.read_bytes() if hasattr(src, 'read_bytes') else src.read_bytes()
            dst_content = dst.read_bytes()
            if src_content != dst_content:
                print(f"   ⚠️  部署校验不匹配: {name}")
                print(f"      源: {_file_hash(str(src))} , 目标: {_file_hash(str(dst))}")
                print(f"      请重新运行: hermes-evolution setup")
                return False
        print(f"   ✅ 部署校验通过 (hash一致)")
    except Exception as e:
        print(f"   ⚠️  部署校验跳过: {e}")
    # ─────────────────────────────────────────────────────────────────
    
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


def cmd_clean(dry_run: bool = False) -> bool:
    """清理测试残留：DB存档、__pycache__"""
    _add_src_to_path()

    from pathlib import Path
    import shutil

    freed_bytes = 0
    removed_files = 0

    # 1. 清理 audit_archives（保留最近10个）
    audit_dir = _project_root / "data" / "audit_archives"
    if audit_dir.exists():
        archives = sorted(audit_dir.glob("*.db"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in archives[10:]:
            freed_bytes += old.stat().st_size
            removed_files += 1
            if not dry_run:
                old.unlink()
        print(f"  {'[DRY RUN] ' if dry_run else ''}审计存档: 保留 {min(len(archives),10)}, "
              f"清理 {removed_files} ({freed_bytes/1024:.0f} KB)")

    # 2. 清理根目录孤立 DB
    stray = _project_root / "tool_performance.db"
    if stray.exists():
        freed_bytes += stray.stat().st_size
        removed_files += 1
        if not dry_run:
            stray.unlink()
        print(f"  {'[DRY RUN] ' if dry_run else ''}孤立DB: {stray.name}")

    # 3. 清理 __pycache__
    pycache_count = 0
    for pc in list(_project_root.rglob("__pycache__")):
        if '.git' in str(pc):
            continue
        pycache_count += 1
        if not dry_run:
            shutil.rmtree(pc, ignore_errors=True)
    if pycache_count:
        print(f"  {'[DRY RUN] ' if dry_run else ''}__pycache__: {pycache_count} 个目录")

    if dry_run:
        print(f"\n  💡 使用 'check --clean' 执行实际清理")
    else:
        print(f"\n  ✅ 清理完成: {removed_files} 文件 + {pycache_count} pycache 目录 "
              f"({freed_bytes/1024:.0f} KB)")
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
    "clean":  (cmd_clean,  "清理测试残留"),
    "setup":  (cmd_setup,  "一键部署到 Hermes"),
    "status": (cmd_status, "查看系统状态"),
    "test":   (cmd_test,   "运行自测"),
}


def main():
    """CLI 主入口"""
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help", "help"):
        print("HermesAgentEvolution CLI v7.0.1")
        print()
        print("用法: python3 -m src.evolution.cli <命令> [选项]")
        print()
        print("命令:")
        for name, (_, desc) in COMMANDS.items():
            print(f"  {name:<10s}  {desc}")
        print()
        print("选项:")
        print("  --fix              自动修复缺失依赖 (仅 check / setup 有效)")
        print("  --clean            清理测试残留 (仅 check / clean 有效)")
        print()
        print("示例:")
        print("  python3 -m src.evolution.cli check")
        print("  python3 -m src.evolution.cli check --fix")
        print("  python3 -m src.evolution.cli check --clean")
        print("  python3 -m src.evolution.cli clean --dry-run")
        print("  python3 -m src.evolution.cli setup")
        sys.exit(0)
    
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        print(f"❌ 未知命令: {cmd}")
        print(f"   可用: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    
    # 解析选项
    fix_mode = "--fix" in sys.argv
    clean_mode = "--clean" in sys.argv
    dry_run = "--dry-run" in sys.argv

    func, _ = COMMANDS[cmd]

    # ── 自动懒部署：pip install 后首次运行任何命令时自动部署插件 ──────
    if cmd != "setup":
        plugin_dst = Path.home() / ".hermes" / "plugins" / "hermes-evolution" / "plugin.yaml"
        if not plugin_dst.exists():
            print("🔧 检测到插件未部署，自动执行一键部署...")
            if not cmd_setup():
                print("⚠️  自动部署失败，请手动运行: hermes-evolution setup")
    # ──────────────────────────────────────────────────────────────────────

    if cmd == "check":
        success = cmd_check(fix=fix_mode, clean=clean_mode)
    elif cmd == "clean":
        success = cmd_clean(dry_run=dry_run)
    else:
        success = func()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

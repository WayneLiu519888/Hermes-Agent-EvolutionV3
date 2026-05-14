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
import argparse
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
    
    # 4. Hermes 插件已部署（未部署则自动部署）
    plugin_dir = Path.home() / ".hermes" / "plugins" / "hermes-evolution"
    plugin_yaml = plugin_dir / "plugin.yaml"
    if not plugin_yaml.exists():
        print("  ⚡ 插件未部署，正在自动部署...")
        ok, msg = _deploy_plugin(plugin_dir)
        _check("Hermes 插件已部署", ok, msg if not ok else "自动部署成功")
    else:
        _check("Hermes 插件已部署", True)
    
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
        if not plugin_yaml.exists():
            ok, msg = _deploy_plugin(plugin_dir)
            _check("Hermes 插件已部署", ok, msg if not ok else "自动部署成功")
        else:
            _check("Hermes 插件已部署", True)
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

    plugin_dst = Path.home() / ".hermes" / "plugins" / "hermes-evolution"
    ok, msg = _deploy_plugin(plugin_dst)
    if ok:
        return True
    print(f"❌ 部署失败: {msg}")
    return False


def _deploy_plugin(target_dir: Path) -> tuple:
    """从包资源部署插件文件到目标目录

    Args:
        target_dir: 目标目录（如 ~/.hermes/plugins/hermes-evolution/）

    Returns:
        (成功标志, 消息)
    """
    import shutil
    try:
        from importlib.resources import files
        plugin_pkg = files("evolution._plugin")
    except ImportError:
        import pkg_resources
        plugin_pkg = Path(pkg_resources.resource_filename("evolution._plugin", ""))

    target_dir.mkdir(parents=True, exist_ok=True)

    for name in ("plugin.yaml", "__init__.py"):
        src = plugin_pkg / name if isinstance(plugin_pkg, Path) else plugin_pkg.joinpath(name)
        try:
            if hasattr(src, 'read_bytes'):
                content = src.read_bytes()
                (target_dir / name).write_bytes(content)
            elif src.exists():
                shutil.copy2(str(src), str(target_dir / name))
            else:
                return False, f"包资源中未找到 {name}"
        except Exception as e:
            return False, f"复制 {name} 失败: {e}"

    return True, "部署成功"
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
        timeout=600
    )
    return result.returncode == 0



# ── 新增命令 ─────────────────────────────────────────────────

def _db_info(args):
    from evolution.db_utils import get_data_dir
    db_dir = get_data_dir()
    print(f"数据目录: {db_dir}")
    for f in sorted(db_dir.glob("*.db")):
        print(f"  {f.name:<40s} {f.stat().st_size/1024:>8.1f} KB")

def _db_clean(args):
    print(f"db clean (dry_run={getattr(args, 'dry_run', False)})")
    from evolution.cli import cmd_clean
    cmd_clean(dry_run=getattr(args, 'dry_run', False))

def _db_vacuum(args):
    import sqlite3
    from evolution.db_utils import get_data_dir
    for f in sorted(get_data_dir().glob("*.db")):
        conn = sqlite3.connect(str(f))
        conn.execute("VACUUM")
        conn.close()
        print(f"  OK {f.name}")

def _db_backup(args):
    import shutil
    from evolution.db_utils import get_data_dir
    dest = getattr(args, 'path', None) or "/tmp/hae-backup"
    Path(dest).mkdir(parents=True, exist_ok=True)
    for f in get_data_dir().glob("*.db"):
        shutil.copy2(str(f), str(Path(dest) / f.name))
    print(f"  备份到 {dest}")

def _cycle_run(args):
    import json
    from evolution.plugin_core import _handle_run_cycle
    result = json.loads(_handle_run_cycle({}))
    if getattr(args, 'json', False):
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(f"周期 #{result.get('cycle_id', '?')}: {result.get('summary', '完成')}")

def _cycle_status(args):
    import sqlite3
    from evolution.db_utils import get_data_dir
    conn = sqlite3.connect(str(get_data_dir() / "evolution_audit.db"))
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT cycle_id, started_at, success, issues_found, actions_succeeded "
        "FROM evolution_cycles ORDER BY cycle_id DESC LIMIT 1"
    ).fetchone()
    if row:
        ok = "OK" if row['success'] else "FAIL"
        print(f"最近周期: #{row['cycle_id']} {row['started_at'][:19]} {ok} issues={row['issues_found']}")
    else:
        print("暂无进化周期记录")
    conn.close()

def _cycle_history(args):
    import sqlite3
    from evolution.db_utils import get_data_dir
    limit = getattr(args, 'limit', 10) or 10
    conn = sqlite3.connect(str(get_data_dir() / "evolution_audit.db"))
    conn.row_factory = sqlite3.Row
    for row in conn.execute(
        "SELECT cycle_id, started_at, success, issues_found "
        "FROM evolution_cycles ORDER BY cycle_id DESC LIMIT ?", (limit,)
    ):
        ok = "OK" if row['success'] else "FAIL"
        print(f"  #{row['cycle_id']:<5} {row['started_at'][:19]} {ok} issues={row['issues_found']}")
    conn.close()

def _cycle_detail(args):
    import json, sqlite3
    from evolution.db_utils import get_data_dir
    conn = sqlite3.connect(str(get_data_dir() / "evolution_audit.db"))
    conn.row_factory = sqlite3.Row
    cid = getattr(args, 'id', None)
    row = conn.execute("SELECT * FROM evolution_cycles WHERE cycle_id=?", (cid,)).fetchone()
    if not row:
        print(f"未找到周期 #{cid}")
        return
    print(f"周期 #{row['cycle_id']} {row['started_at'][:19]}")
    print(f"  success={row['success']} issues={row['issues_found']} patterns={row['patterns_discovered']}")
    if row['issues_details']:
        try:
            issues = json.loads(row['issues_details'])
            for i in issues:
                print(f"    [{i.get('severity','?')}] {i.get('type','?')}: {i.get('message','')[:80]}")
        except: pass
    conn.close()

def _audit_summary(args):
    import sqlite3
    from evolution.db_utils import get_data_dir
    conn = sqlite3.connect(str(get_data_dir() / "evolution_audit.db"))
    conn.row_factory = sqlite3.Row
    s = conn.execute("SELECT COUNT(*) as t, SUM(success) as ok, AVG(issues_found) as ai, SUM(actions_succeeded) as act FROM evolution_cycles").fetchone()
    print(f"总周期: {s['t']}  成功率: {s['ok']}/{s['t'] or 1}  平均问题: {s['ai'] or 0:.1f}  总动作: {s['act'] or 0}")
    conn.close()

def _audit_cycles(args):
    _cycle_history(args)

def _audit_detail(args):
    _cycle_detail(args)

def _audit_issues(args):
    import json, sqlite3
    from evolution.db_utils import get_data_dir
    conn = sqlite3.connect(str(get_data_dir() / "evolution_audit.db"))
    conn.row_factory = sqlite3.Row
    limit = getattr(args, 'limit', 10) or 10
    rows = conn.execute("SELECT cycle_id, started_at, issues_details FROM evolution_cycles WHERE issues_details IS NOT NULL ORDER BY cycle_id DESC LIMIT ?", (limit,)).fetchall()
    for row in rows:
        try:
            issues = json.loads(row['issues_details'])
            for i in issues:
                if getattr(args, 'type', None) and i.get('type') != args.type: continue
                if getattr(args, 'severity', None) and i.get('severity') != args.severity: continue
                print(f"  #{row['cycle_id']} [{i.get('severity','?')}] {i.get('type','?')}: {i.get('message','')[:80]}")
        except: pass
    conn.close()

def _audit_trend(args):
    import sqlite3
    from evolution.db_utils import get_data_dir
    conn = sqlite3.connect(str(get_data_dir() / "evolution_audit.db"))
    for row in conn.execute("SELECT cycle_id, issues_found, actions_succeeded FROM evolution_cycles ORDER BY cycle_id DESC LIMIT 10"):
        print(f"  #{row['cycle_id']:<5} issues={row['issues_found']} actions={'#'*row['actions_succeeded']}")
    conn.close()

def _log_show(args):
    log_file = Path.home() / ".hermes" / "logs" / "gateway.log"
    limit = getattr(args, 'limit', 50) or 50
    if log_file.exists():
        for line in log_file.read_text().splitlines()[-limit:]:
            if getattr(args, 'level', None) and args.level.upper() not in line: continue
            print(line)
    else:
        print(f"日志不存在: {log_file}")

def _config_show(args):
    config = Path.home() / ".hermes" / "config.yaml"
    print(config.read_text() if config.exists() else f"配置文件不存在: {config}")

def _config_doctor(args):
    for label, path in [
        ("配置文件", Path.home()/".hermes"/"config.yaml"),
        ("数据目录", Path.home()/".hermes"/"data"/"evolution"),
        ("插件目录", Path.home()/".hermes"/"plugins"/"hermes-evolution"),
    ]:
        print(f"  {label}: {'OK' if path.exists() else 'MISSING'} {path}")
    data_dir = Path.home()/".hermes"/"data"/"evolution"
    if data_dir.exists():
        dbs = list(data_dir.glob("*.db"))
        print(f"  数据库: {len(dbs)} 个 ({sum(f.stat().st_size for f in dbs)/1024/1024:.1f} MB)")
    print(f"  Python: {sys.version}")

def _config_validate(args):
    _config_doctor(args)
    print("  验证完成")

def _uninstall(args):
    import shutil, subprocess
    targets = []
    plugin = Path.home()/".hermes"/"plugins"/"hermes-evolution"
    if plugin.exists(): targets.append(("插件", str(plugin)))
    for sp in [Path("/usr/local/lib/python3.12/dist-packages/evolution"), Path.home()/".hermes"/"hermes-agent"/".venv"/"lib"/"python3.11"/"site-packages"/"evolution"]:
        if sp.exists(): targets.append(("模块", str(sp)))
    data_dir = Path.home()/".hermes"/"data"/"evolution"
    if data_dir.exists() and not getattr(args, 'keep_data', False):
        targets.append(("数据", str(data_dir)))
    if getattr(args, 'dry_run', False):
        print("预览:")
        for l, p in targets: print(f"  [{l}] {p}")
        return
    if not getattr(args, 'force', False):
        print(f"将清理 {len(targets)} 处残留:")
        for l, p in targets: print(f"  [{l}] {p}")
        if input("确认 [y/N]? ").lower() != 'y':
            print("取消"); return
    subprocess.run(["pip", "uninstall", "-y", "--break-system-packages", "hermes-agent-evolution"], capture_output=True)
    for _, p in targets:
        if Path(p).exists(): shutil.rmtree(p, ignore_errors=True)
    # pycache
    subprocess.run("find ~/.hermes -name '__pycache__' -exec rm -rf {} + 2>/dev/null", shell=True)
    print("卸载完成")

def _version(args):
    from evolution import __version__
    if getattr(args, 'all', False):
        import evolution, psutil, numpy
        print(f"HAE: {evolution.__version__}")
        print(f"Python: {sys.version}")
        print(f"psutil: {psutil.__version__}")
        print(f"numpy: {numpy.__version__}")
    else:
        print(f"HAE v{__version__}")

# ── argparse 命令树 ──────────────────────────────────────────────

def _build_parser():
    parser = argparse.ArgumentParser(prog='hae', description='HAE — Hermes Agent Evolution CLI', formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest='command')

    p = sub.add_parser('install', help='部署 HAE 插件到 Hermes')
    p.add_argument('--force', action='store_true')
    p.set_defaults(func=lambda a: cmd_setup())

    p = sub.add_parser('uninstall', help='一键卸载')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--keep-data', action='store_true')
    p.add_argument('--force', action='store_true')
    p.set_defaults(func=_uninstall)

    p = sub.add_parser('check', help='环境自检')
    p.add_argument('--fix', action='store_true')
    p.add_argument('--clean', action='store_true')
    p.set_defaults(func=lambda a: cmd_check(fix=a.fix, clean=a.clean))

    p = sub.add_parser('status', help='系统状态')
    p.add_argument('--detail', action='store_true')
    p.add_argument('--json', action='store_true')
    p.set_defaults(func=lambda a: cmd_status())

    p = sub.add_parser('version', help='版本信息')
    p.add_argument('--all', action='store_true')
    p.set_defaults(func=_version)

    p = sub.add_parser('test', help='运行测试')
    p.add_argument('--quick', action='store_true')
    p.add_argument('--suite', type=str)
    p.set_defaults(func=lambda a: cmd_test())

    p = sub.add_parser('db', help='数据库管理')
    ds = p.add_subparsers(dest='db_sub')
    ds.add_parser('info', help='DB信息').set_defaults(func=_db_info)
    p2 = ds.add_parser('clean', help='清理残留'); p2.add_argument('--dry-run', action='store_true'); p2.set_defaults(func=_db_clean)
    ds.add_parser('vacuum', help='压缩DB').set_defaults(func=_db_vacuum)
    p2 = ds.add_parser('backup', help='备份DB'); p2.add_argument('--path', type=str); p2.set_defaults(func=_db_backup)

    p = sub.add_parser('cycle', help='进化控制')
    cs = p.add_subparsers(dest='cy_sub')
    p2 = cs.add_parser('run', help='触发周期'); p2.add_argument('--json', action='store_true'); p2.set_defaults(func=_cycle_run)
    cs.add_parser('status', help='周期状态').set_defaults(func=_cycle_status)
    p2 = cs.add_parser('history', help='周期历史'); p2.add_argument('--limit', type=int, default=10); p2.set_defaults(func=_cycle_history)
    p2 = cs.add_parser('detail', help='周期详情'); p2.add_argument('id', type=int); p2.set_defaults(func=_cycle_detail)

    p = sub.add_parser('audit', help='审计查询')
    au = p.add_subparsers(dest='au_sub')
    au.add_parser('summary', help='汇总').set_defaults(func=_audit_summary)
    p2 = au.add_parser('cycles', help='周期列表'); p2.add_argument('--limit', type=int, default=10); p2.set_defaults(func=_audit_cycles)
    p2 = au.add_parser('detail', help='周期详情'); p2.add_argument('id', type=int); p2.set_defaults(func=_audit_detail)
    p2 = au.add_parser('issues', help='问题列表'); p2.add_argument('--type', type=str); p2.add_argument('--severity', type=str); p2.add_argument('--limit', type=int, default=10); p2.set_defaults(func=_audit_issues)
    au.add_parser('trend', help='趋势').set_defaults(func=_audit_trend)

    p = sub.add_parser('log', help='查看日志')
    p.add_argument('--tail', action='store_true')
    p.add_argument('--level', type=str)
    p.add_argument('--limit', type=int, default=50)
    p.set_defaults(func=_log_show)

    p = sub.add_parser('config', help='配置诊断')
    cf = p.add_subparsers(dest='cf_sub')
    cf.add_parser('show', help='显示').set_defaults(func=_config_show)
    cf.add_parser('doctor', help='诊断').set_defaults(func=_config_doctor)
    cf.add_parser('validate', help='验证').set_defaults(func=_config_validate)

    return parser

def main():
    parser = _build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    if hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()

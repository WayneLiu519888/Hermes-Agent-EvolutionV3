"""
Dependency Manager — 环境检测 + 依赖自愈

检测当前安装环境(pipx/pip/venv/dev-mode)并提供自动修复。
"""
import sys
import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# 模块名 → pip包名映射 + 最低版本
DEPENDENCY_MAP: Dict[str, dict] = {
    "yaml":      {"pkg": "pyyaml",   "min_version": "6.0"},
    "numpy":     {"pkg": "numpy",    "min_version": "1.19"},
    "psutil":    {"pkg": "psutil",   "min_version": "5.8.0"},
    "requests":  {"pkg": "requests", "min_version": "2.25", "optional": True},
    "sklearn":   {"pkg": "scikit-learn", "min_version": "0.24", "optional": True},
}


def detect_env() -> str:
    """检测当前 Python 环境类型"""
    exe = Path(sys.executable)
    exe_str = str(exe)
    # pipx: /root/.local/pipx/venvs/<pkg>/bin/python
    if "/pipx/venvs/" in exe_str:
        return "pipx"
    # venv
    if (exe.parent / "activate").exists() or "venv" in exe_str:
        return "venv"
    # dev-mode (editable install): check for pyproject.toml nearby
    for p in exe.parents:
        if (p / "pyproject.toml").exists() and (p / "setup.py").exists():
            return "dev"
    return "pip"


def get_pipx_package() -> Optional[str]:
    """从当前 Python 路径提取 pipx 包名"""
    exe = str(sys.executable)
    if "/pipx/venvs/" not in exe:
        return None
    # /root/.local/pipx/venvs/hermes-agent-evolution/bin/python
    parts = exe.split("/pipx/venvs/")
    if len(parts) > 1:
        return parts[1].split("/")[0]
    return None


def check_module(module_name: str) -> bool:
    """检查模块是否可导入"""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False


def find_missing_modules() -> List[str]:
    """扫描所有声明的依赖，返回缺失的模块名列表"""
    missing = []
    for mod_name, info in DEPENDENCY_MAP.items():
        if not info.get("optional") and not check_module(mod_name):
            missing.append(mod_name)
    return missing


def install_package(pkg_name: str, env: str = None) -> Tuple[bool, str]:
    """安装单个包，返回 (成功, 消息)"""
    if env is None:
        env = detect_env()

    try:
        if env == "pipx":
            px_pkg = get_pipx_package()
            if px_pkg:
                result = subprocess.run(
                    ["pipx", "inject", px_pkg, pkg_name],
                    capture_output=True, text=True, timeout=60
                )
            else:
                return False, "无法确定 pipx 包名"
        else:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--quiet", pkg_name],
                capture_output=True, text=True, timeout=60
            )

        success = result.returncode == 0
        msg = result.stdout.strip() if success else result.stderr.strip()
        return success, msg
    except Exception as e:
        return False, str(e)


def auto_fix_missing(missing_modules: List[str]) -> List[Tuple[str, bool, str]]:
    """自动修复缺失依赖，返回 [(模块名, 成功, 消息), ...]"""
    env = detect_env()
    results = []
    for mod in missing_modules:
        info = DEPENDENCY_MAP.get(mod)
        if not info:
            results.append((mod, False, "未找到映射"))
            continue
        pkg = info["pkg"]
        ok, msg = install_package(pkg, env)
        results.append((mod, ok, msg))
    return results

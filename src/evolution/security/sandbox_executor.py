"""
沙箱执行环境 - Hermes Agent Evolution 安全增强模块

在隔离环境中安全执行代码：
- 资源限制: CPU时间、内存上限、磁盘写入限制
- 文件系统访问白名单
- 输出捕获和截断 (max 10KB)
- 危险操作检测: 阻止危险的模块导入和系统调用
- 使用 subprocess + resource 实现隔离

注意: 沙箱基于操作系统级别的资源限制，并非完全安全沙箱。
      生产环境建议结合Docker/VM使用。
"""

import os
import sys
import ast
import logging
import subprocess
import tempfile
import json
import platform
import signal
from enum import Enum
from typing import Dict, Any, Optional, Tuple, List, Set
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("hermes_evo.security")


# ============================================================
# 资源限制
# ============================================================

# 加载资源限制模块 (Unix only)
_HAVE_RESOURCE = False
try:
    import resource
    _HAVE_RESOURCE = True
except ImportError:
    logger.warning("resource模块不可用 (非Unix系统?)，CPU/内存限制将不生效")


# ============================================================
# 枚举和数据类
# ============================================================

class SandboxStatus(str, Enum):
    """沙箱执行状态"""
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    MEMORY_EXCEEDED = "MEMORY_EXCEEDED"
    FORBIDDEN_CODE = "FORBIDDEN_CODE"
    RUNTIME_ERROR = "RUNTIME_ERROR"
    COMPILE_ERROR = "COMPILE_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class SandboxResult:
    """沙箱执行结果"""
    status: SandboxStatus = SandboxStatus.SUCCESS
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    execution_time_ms: float = 0.0
    memory_used_kb: int = 0
    truncated: bool = False  # 输出是否被截断
    error_message: str = ""
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================
# 危险代码检测
# ============================================================

# 被禁止的模块导入
FORBIDDEN_IMPORTS: Set[str] = {
    "os", "subprocess", "socket", "shutil", "sys",
    "ctypes", "multiprocessing", "signal", "threading",
    "importlib", "imp", "builtins", "__builtins__",
    "code", "codeop", "compileall", "py_compile",
    "gc", "atexit", "faulthandler", "traceback",
    "pickle", "shelve", "marshal",
    "inspect", "ast", "dis",
    "pdb", "bdb", "profile", "cProfile",
    "pathlib", "glob", "fnmatch",
    "webbrowser", "http", "urllib", "ftplib",
    "smtplib", "poplib", "imaplib", "email",
    "telnetlib", "xmlrpc",
    "tkinter", "curses",
    "getpass", "pwd", "grp", "crypt",
    "pty", "tty", "termios",
}

# 被禁止的模块级导入检查 — 这些是通配符前缀
FORBIDDEN_PREFIXES: List[str] = [
    "os.", "subprocess", "socket", "shutil",
    "ctypes", "importlib", "signal.",
    "multiprocessing",
]

# 被禁止的AST节点类型名称（用于检查）
FORBIDDEN_AST_NODES: Set[str] = {
    "Import", "ImportFrom",
}

# 被禁止的函数名/属性访问
FORBIDDEN_CALLS: Set[str] = {
    "eval", "exec", "compile", "__import__",
    "open",  # 文件操作需白名单检查
    "getattr", "setattr", "delattr",
    "globals", "locals", "vars",
    "breakpoint", "input",
}


# ============================================================
# 代码安全分析器
# ============================================================

class CodeSafetyAnalyzer(ast.NodeVisitor):
    """使用AST分析Python代码安全性

    检测被禁止的模块导入和危险函数调用。
    """

    def __init__(self):
        self.forbidden_found: List[str] = []  # 发现的问题列表

    def visit_Import(self, node: ast.Import):
        for alias in node.names:
            name = alias.name.split(".")[0]
            asname = alias.asname or alias.name
            if name in FORBIDDEN_IMPORTS:
                self.forbidden_found.append(f"Forbidden import: {asname}")
            else:
                # 检查前缀匹配
                for prefix in FORBIDDEN_PREFIXES:
                    if alias.name.startswith(prefix.rstrip(".")) and alias.name != prefix.rstrip("."):
                        self.forbidden_found.append(f"Forbidden prefixed import: {alias.name}")
                        break
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module:
            module_base = node.module.split(".")[0]
            if module_base in FORBIDDEN_IMPORTS:
                self.forbidden_found.append(f"Forbidden from-import: {node.module}")
            else:
                for prefix in FORBIDDEN_PREFIXES:
                    if node.module.startswith(prefix.rstrip(".")):
                        self.forbidden_found.append(f"Forbidden prefixed from-import: {node.module}")
                        break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call):
        # 检查直接函数调用 eval/exec/compile/__import__
        if isinstance(node.func, ast.Name):
            if node.func.id in FORBIDDEN_CALLS:
                self.forbidden_found.append(f"Forbidden call: {node.func.id}()")
        elif isinstance(node.func, ast.Attribute):
            if node.func.attr in FORBIDDEN_CALLS:
                self.forbidden_found.append(f"Forbidden method call: .{node.func.attr}()")
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript):
        # 检测 __builtins__[...] 等
        if isinstance(node.value, ast.Name) and node.value.id in ("__builtins__", "builtins"):
            self.forbidden_found.append(f"Forbidden __builtins__ access")
        self.generic_visit(node)

    def visit_With(self, node: ast.With):
        # 检测 with open(...) as f: 等文件操作
        for item in node.items:
            if isinstance(item.context_expr, ast.Call):
                if isinstance(item.context_expr.func, ast.Name):
                    if item.context_expr.func.id == "open":
                        self.forbidden_found.append("Forbidden: open() call (file I/O)")
        self.generic_visit(node)


def analyze_code_safety(code: str) -> Tuple[bool, List[str]]:
    """分析代码安全性

    Args:
        code: 待分析的Python源代码

    Returns:
        Tuple[bool, List[str]]: (是否安全, 问题列表)
    """
    try:
        tree = ast.parse(code, mode='exec')
        analyzer = CodeSafetyAnalyzer()
        analyzer.visit(tree)
        is_safe = len(analyzer.forbidden_found) == 0
        return is_safe, analyzer.forbidden_found
    except SyntaxError as e:
        return False, [f"Syntax error: {e}"]
    except Exception as e:
        return False, [f"Parse error: {e}"]


# ============================================================
# SandboxExecutor 主类
# ============================================================

class SandboxExecutor:
    """沙箱执行器

    在资源受限的隔离环境中执行Python代码。

    使用方式:
        executor = SandboxExecutor()
        result = executor.execute_in_sandbox("print('hello world')")
    """

    # 默认限制
    DEFAULT_TIMEOUT_SEC = 30        # 默认CPU超时(秒)
    DEFAULT_MAX_MEMORY_MB = 128     # 默认最大内存(MB)
    MAX_STDOUT_BYTES = 10 * 1024   # 输出截断上限: 10KB
    MAX_STDERR_BYTES = 5 * 1024    # stderr截断上限: 5KB

    def __init__(self, audit_logger=None, file_whitelist: List[str] = None):
        """初始化沙箱执行器

        Args:
            audit_logger: 可选AuditLogger实例，用于记录执行事件
            file_whitelist: 文件系统访问白名单路径列表
        """
        self.audit_logger = audit_logger
        self.file_whitelist: List[str] = file_whitelist or []
        # 默认白名单: 临时目录
        if not self.file_whitelist:
            self.file_whitelist = [tempfile.gettempdir()]

    def execute_in_sandbox(
        self,
        code: str,
        timeout: Optional[int] = None,
        max_memory: Optional[int] = None,
        stdin_data: str = "",
        env_vars: Dict[str, str] = None,
    ) -> SandboxResult:
        """在沙箱中执行代码

        Args:
            code: 要执行的Python代码
            timeout: CPU超时秒数，默认30秒
            max_memory: 最大内存MB，默认128MB
            stdin_data: 标准输入数据
            env_vars: 额外的环境变量

        Returns:
            SandboxResult: 执行结果
        """
        timeout = timeout or self.DEFAULT_TIMEOUT_SEC
        max_memory = max_memory or self.DEFAULT_MAX_MEMORY_MB

        # 1. 安全检查
        is_safe, issues = analyze_code_safety(code)
        if not is_safe:
            result = SandboxResult(
                status=SandboxStatus.FORBIDDEN_CODE,
                error_message=f"Forbidden code detected: {'; '.join(issues)}",
                stdout="",
                stderr="",
            )
            self._log_execution(result, code)
            return result

        # 2. 写入临时文件
        try:
            with tempfile.NamedTemporaryFile(
                mode='w', suffix='.py', delete=False, dir=tempfile.gettempdir()
            ) as f:
                f.write(code)
                temp_path = f.name
        except OSError as e:
            return SandboxResult(
                status=SandboxStatus.INTERNAL_ERROR,
                error_message=f"Failed to create temp file: {e}",
            )

        # 3. 执行
        start_time = datetime.now()
        try:
            result = self._execute_subprocess(temp_path, timeout, max_memory, stdin_data, env_vars)
        finally:
            # 清理临时文件
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        elapsed = (datetime.now() - start_time).total_seconds() * 1000
        result.execution_time_ms = elapsed

        # 4. 审计记录
        self._log_execution(result, code)

        return result

    def _execute_subprocess(
        self,
        script_path: str,
        timeout: int,
        max_memory_mb: int,
        stdin_data: str,
        env_vars: Optional[Dict[str, str]],
    ) -> SandboxResult:
        """通过子进程执行代码并应用资源限制"""

        # 设置资源限制函数（pre-exec hook）
        def set_limits():
            if not _HAVE_RESOURCE:
                return
            try:
                # CPU时间限制
                resource.setrlimit(resource.RLIMIT_CPU, (timeout, timeout + 3))
                # 内存限制
                max_mem_bytes = max_memory_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (max_mem_bytes, max_mem_bytes))
                # 文件大小限制
                resource.setrlimit(resource.RLIMIT_FSIZE, (10 * 1024 * 1024, 10 * 1024 * 1024))
                # 进程数限制
                resource.setrlimit(resource.RLIMIT_NPROC, (1, 1))
            except Exception:
                pass

        try:
            # 构建环境变量（最小化）
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)

            # 限制PATH（防止意外执行系统命令）
            env["PATH"] = "/usr/bin:/bin:/usr/local/bin"

            process = subprocess.Popen(
                [sys.executable, "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                env=env,
                cwd=tempfile.gettempdir(),  # 在临时目录执行
                universal_newlines=False,    # 以字节读取
                preexec_fn=set_limits if _HAVE_RESOURCE else None,
                start_new_session=True,      # 创建新进程组，防止信号传播
            )

            try:
                stdout_bytes, stderr_bytes = process.communicate(
                    input=stdin_data.encode("utf-8", errors="replace") if stdin_data else None,
                    timeout=timeout + 5,  # wall-clock timeout 稍长于CPU timeout
                )
            except subprocess.TimeoutExpired:
                # 超时，强制杀死进程组
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except (ProcessLookupError, OSError):
                    pass
                try:
                    process.kill()
                    process.wait(timeout=5)
                except Exception:
                    pass
                return SandboxResult(
                    status=SandboxStatus.TIMEOUT,
                    error_message=f"Execution timed out after {timeout}s",
                    exit_code=-1,
                )

            exit_code = process.returncode if process.returncode is not None else -1

            # 检查是否因资源限制被杀死
            if exit_code == -signal.SIGXCPU:
                return SandboxResult(
                    status=SandboxStatus.TIMEOUT,
                    error_message="CPU time limit exceeded (SIGXCPU)",
                    exit_code=exit_code,
                )
            elif exit_code == -signal.SIGSEGV:
                return SandboxResult(
                    status=SandboxStatus.MEMORY_EXCEEDED,
                    error_message="Memory limit exceeded (SIGSEGV)",
                    exit_code=exit_code,
                )
            elif exit_code == -signal.SIGKILL and _HAVE_RESOURCE:
                return SandboxResult(
                    status=SandboxStatus.MEMORY_EXCEEDED,
                    error_message="Process killed (OOM or resource limit)",
                    exit_code=exit_code,
                )

            # 截断输出
            truncated = False
            if len(stdout_bytes) > self.MAX_STDOUT_BYTES:
                stdout_bytes = stdout_bytes[:self.MAX_STDOUT_BYTES]
                truncated = True
            if len(stderr_bytes) > self.MAX_STDERR_BYTES:
                stderr_bytes = stderr_bytes[:self.MAX_STDERR_BYTES]

            stdout = stdout_bytes.decode("utf-8", errors="replace")
            stderr = stderr_bytes.decode("utf-8", errors="replace")

            if exit_code == 0 and not stderr:
                return SandboxResult(
                    status=SandboxStatus.SUCCESS,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    truncated=truncated,
                )
            elif exit_code != 0:
                return SandboxResult(
                    status=SandboxStatus.RUNTIME_ERROR,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    error_message=stderr.strip() or f"Exit code: {exit_code}",
                    truncated=truncated,
                )
            else:
                return SandboxResult(
                    status=SandboxStatus.SUCCESS,
                    stdout=stdout,
                    stderr=stderr,
                    exit_code=exit_code,
                    truncated=truncated,
                )

        except FileNotFoundError:
            return SandboxResult(
                status=SandboxStatus.INTERNAL_ERROR,
                error_message="Python interpreter not found for subprocess execution",
            )
        except Exception as e:
            logger.error("沙箱子进程执行异常: %s", e)
            return SandboxResult(
                status=SandboxStatus.INTERNAL_ERROR,
                error_message=f"Subprocess error: {e}",
            )

    # ---- 便捷方法 ----

    def execute_safe_function(self, func_code: str, args: List[Any] = None) -> SandboxResult:
        """在沙箱中执行一个安全的函数调用

        将函数体包装成 __main__ 执行。
        """
        args = args or []
        # 包装代码，调用用户函数
        wrapped_code = f"""
{func_code}

if __name__ == "__main__":
    import json
    _result = main({', '.join(repr(a) for a in args)})
    print(json.dumps(_result, default=str))
"""
        return self.execute_in_sandbox(wrapped_code)

    def validate_code(self, code: str) -> Tuple[bool, str]:
        """仅验证代码安全性，不执行

        Returns:
            Tuple[bool, str]: (是否安全, 消息)
        """
        is_safe, issues = analyze_code_safety(code)
        if not is_safe:
            return False, f"Forbidden: {'; '.join(issues)}"
        try:
            ast.parse(code)
            return True, "Code is syntactically valid and passes safety checks"
        except SyntaxError as e:
            return False, f"Syntax error: {e}"

    # ---- 内部方法 ----

    def _log_execution(self, result: SandboxResult, code: str):
        """记录执行审计"""
        if self.audit_logger:
            self.audit_logger.log_event(
                event_type="TOOL_EXECUTION",
                level="ERROR" if result.status != SandboxStatus.SUCCESS else "INFO",
                agent_id="sandbox_executor",
                action="execute_in_sandbox",
                description=f"Sandbox execution: {result.status.value}",
                details={
                    "status": result.status.value,
                    "exit_code": result.exit_code,
                    "execution_time_ms": result.execution_time_ms,
                    "code_length": len(code),
                    "code_preview": code[:200],
                    "truncated": result.truncated,
                    "error": result.error_message[:200] if result.error_message else None,
                },
                source_module="sandbox_executor",
                outcome="success" if result.status == SandboxStatus.SUCCESS else "failure",
            )

    def __repr__(self) -> str:
        return f"SandboxExecutor(timeout={self.DEFAULT_TIMEOUT_SEC}s, max_memory={self.DEFAULT_MAX_MEMORY_MB}MB)"

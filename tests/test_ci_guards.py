"""CI 防回归守卫 — 禁止已知 Bug 模式重新引入。

通过静态分析 + grep 模式匹配，在 CI 中自动阻断：
    C1: from src.evolution（非 except 块内的）
    C2: create_from_api_description 多余参数
    C3: handler → 工具函数签名不匹配
"""
import re
import ast
import pytest
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
SRC_EVOLUTION = PROJECT / "src" / "evolution"


# ── 工具函数 ──────────────────────────────────────────────────────────

def _py_files(root: Path):
    """Yield all .py files under root, skipping .git/__pycache__/.egg-info."""
    for fp in sorted(root.rglob("*.py")):
        if any(skip in str(fp) for skip in ('.git', '__pycache__', '.egg-info', 'node_modules')):
            continue
        yield fp


def _rel(fp: Path) -> str:
    return str(fp.relative_to(PROJECT))


# ═══════════════════════════════════════════════════════════════════════
#  C1: 禁止裸 from src.evolution（非 except 块内）
# ═══════════════════════════════════════════════════════════════════════

class TestNoBareFromSrcEvolution:
    """pip install 后 src/ 不作为包存在——裸 from src.evolution 全部爆炸。"""

    VIOLATION_MSG = (
        "裸 'from src.evolution' 禁止出现！应改为 try/except 双路径：\n"
        "  try:\n"
        "      from evolution.X import Y\n"
        "  except ImportError:\n"
        "      from src.evolution.X import Y\n"
        "或使用相对导入（src/evolution/ 内部文件）。"
    )

    def test_no_bare_from_src_evolution(self):
        violations = []
        for fp in _py_files(PROJECT):
            lines = fp.read_text().split('\n')
            in_except = False
            in_paren_import = False
            for no, line in enumerate(lines, 1):
                stripped = line.strip()
                # 进入 except ImportError 块
                if stripped == 'except ImportError:' or (
                    stripped.startswith('except ') and 'ImportError' in stripped
                ):
                    in_except = True
                    in_paren_import = False
                    continue
                # 离开 except 块（遇到非 from src.evolution 的非空非续行）
                if in_except and not in_paren_import and stripped:
                    if stripped.startswith('from src.evolution'):
                        # 检查是否是括号导入的开始
                        if stripped.endswith('('):
                            in_paren_import = True
                    else:
                        in_except = False
                        in_paren_import = False
                        continue
                # 括号导入的续行
                if in_except and in_paren_import:
                    if ')' in stripped:
                        in_paren_import = False
                    continue
                if line.lstrip().startswith('from src.evolution') and not in_except:
                    violations.append(f"  {_rel(fp)}:{no}  {stripped}")

        assert violations == [], (
            f"发现 {len(violations)} 处裸 'from src.evolution'：\n" +
            '\n'.join(violations[:15]) +  # 截断，避免输出过长
            ("\n  …(" + str(len(violations) - 15) + " more)" if len(violations) > 15 else "") +
            "\n\n" + self.VIOLATION_MSG
        )


# ═══════════════════════════════════════════════════════════════════════
#  C2: create_from_api_description() 多余参数
# ═══════════════════════════════════════════════════════════════════════

class TestCreateFromApiDescriptionParams:
    """create_from_api_description(api_spec, name, category) 不接受
    description= / tags= ——多余参数导致 TypeError。"""

    EXPECTED_SIGNATURE = {"api_spec", "name", "category"}  # 不含 self

    def test_signature_matches(self):
        """确认 EnhancedToolCreator.create_from_api_description 签名含 api_spec/name/category。"""
        from evolution.tools.enhanced_tool_creator import EnhancedToolCreator
        import inspect
        sig = inspect.signature(EnhancedToolCreator.create_from_api_description)
        param_names = set(sig.parameters.keys()) - {"self"}
        missing = self.EXPECTED_SIGNATURE - param_names
        extra = param_names - self.EXPECTED_SIGNATURE
        assert missing == set(), f"create_from_api_description 缺少参数: {missing}"
        assert extra == set(), f"create_from_api_description 多余参数: {extra}"

    def test_no_banned_kwargs_in_calls(self):
        """调用 create_from_api_description 时不得出现 description= / tags=。"""
        banned = {"description=", "tags="}
        violations = []
        for fp in _py_files(PROJECT):
            for no, line in enumerate(fp.read_text().split('\n'), 1):
                if 'create_from_api_description' in line:
                    continue  # 第一行是调用行，检查上下文
            # 更稳健的方法：AST 分析调用
            _check_banned_calls(fp, banned, violations)

        assert violations == [], (
            f"create_from_api_description() 调用中仍含多余参数：\n" +
            '\n'.join(violations[:10]) +
            "\n\n应移除 description=/tags= —— 函数只接受 (api_spec, name, category)"
        )


def _check_banned_calls(fp: Path, banned: set, violations: list):
    """使用 AST 查找 create_from_api_description 调用中的多余关键字。"""
    try:
        tree = ast.parse(fp.read_text(), filename=str(fp))
    except SyntaxError:
        return

    class CallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # 检查 func.attr == 'create_from_api_description'
            if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'create_from_api_description'):
                for kw in node.keywords:
                    if kw.arg and (kw.arg + '=') in banned:
                        violations.append(
                            f"  {_rel(fp)}:{kw.lineno}  create_from_api_description({kw.arg}=…)"
                        )
            self.generic_visit(node)

    CallVisitor().visit(tree)


# ═══════════════════════════════════════════════════════════════════════
#  C3: handler → 工具函数签名全量校验
# ═══════════════════════════════════════════════════════════════════════

class TestHandlerToolSignatureMatch:
    """插件 handler 注册的工具函数参数名必须与工具函数签名完全匹配。"""

    def test_register_tool_param_names_match(self):
        """所有 register_tool() 的参数名必须与工具函数签名一致。"""
        # 从 hermes-plugin/__init__.py 和 _plugin/__init__.py 提取所有 register_tool 调用
        plugin_files = [
            PROJECT / "hermes-plugin" / "__init__.py",
            SRC_EVOLUTION / "_plugin" / "__init__.py",
        ]
        violations = []

        for pf in plugin_files:
            if not pf.exists():
                continue
            for v in _check_register_tool_calls(pf):
                violations.append(v)

        assert violations == [], (
            "register_tool() 参数名与工具函数签名不匹配：\n" +
            '\n'.join(violations) +
            "\n\n参数名必须完全匹配（包括顺序），否则 Hermes 无法正确 dispatch。"
        )


def _check_register_tool_calls(plugin_file: Path) -> list:
    """提取 register_tool() 调用中的 parameters= 参数，校验与函数签名一致。"""
    violations = []
    try:
        tree = ast.parse(plugin_file.read_text(), filename=str(plugin_file))
    except SyntaxError:
        return violations

    # 收集所有 handler 函数及其签名
    handlers = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) or isinstance(node, ast.FunctionDef):
            params = [p.arg for p in node.args.args]
            # 跳过 self（类方法）
            if params and params[0] in ('self', 'cls'):
                params = params[1:]
            handlers[node.name] = {
                'params': params,
                'lineno': node.lineno,
            }

    # 查找 register_tool() 调用
    class RegisterVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            if (isinstance(node.func, ast.Attribute) and
                    node.func.attr == 'register_tool'):
                # 提取 parameters= 关键字
                for kw in node.keywords:
                    if kw.arg == 'parameters':
                        _validate_parameters(kw.value, node, handlers, violations)
            self.generic_visit(node)

    RegisterVisitor().visit(tree)
    return violations


def _validate_parameters(params_node, call_node, handlers, violations):
    """校验 parameters dict 的 properties 与 handler 签名一致。"""
    if not isinstance(params_node, ast.Dict):
        return

    # 找到 handler 名称
    handler_name = None
    for kw in call_node.keywords:
        if kw.arg == 'handler':
            if isinstance(kw.value, ast.Name):
                handler_name = kw.value.id
            elif isinstance(kw.value, ast.Constant):
                handler_name = kw.value.value
            break

    if not handler_name or handler_name not in handlers:
        return

    expected_params = handlers[handler_name]['params']
    # 提取 parameters dict 中 properties 的键
    actual_params = []
    for key_node in params_node.keys:
        if isinstance(key_node, ast.Constant):
            actual_params.append(key_node.value)
        elif isinstance(key_node, ast.Str):
            actual_params.append(key_node.s)

    # 比较（handler 签名通常含 **kwargs，所以允许 actual 是 expected 的子集）
    if set(actual_params) - set(expected_params):
        violations.append(
            f"  {_rel(plugin_file)}:{call_node.lineno}  "
            f"handler={handler_name}, expected⊇{expected_params}, got={actual_params}"
        )

"""
Evolution 输入验证层

为所有外部输入提供统一的验证和消毒。
防止 SQL 注入、路径遍历、命令注入等常见攻击。

用法:
    from evolution.security.input_validator import InputValidator, ValidationResult

    result = InputValidator.validate_tool_name("my-tool")
    if not result.valid:
        raise ValueError(result.errors)

    clean_msg = InputValidator.sanitize_error_message(exception)
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """输入验证结果"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    sanitized: Any = None


class InputValidator:
    """
    统一输入验证器。

    所有从用户/外部系统接收的输入在进入数据库或逻辑层之前
    都应经过此验证器处理。
    """

    # ── 常量 ────────────────────────────────────────────────────────────────

    MAX_TOOL_NAME_LENGTH = 64
    MIN_INTERVAL_SECONDS = 10
    MAX_INTERVAL_SECONDS = 86400  # 24 hours
    SAFE_DB_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_.-]+\.db$')
    SAFE_TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z0-9_-]+$')
    PATH_SANITIZE_PATTERN = re.compile(r'(/[^\s"\'<>|:]{1,50}/)')

    # ── 校验方法 ────────────────────────────────────────────────────────────

    @classmethod
    def validate_tool_name(cls, name: str) -> ValidationResult:
        """
        验证工具名称。

        规则:
          - 非空，长度不超过 64 字符
          - 仅允许字母、数字、下划线、连字符
          - 自动 trim 首尾空白

        返回:
            ValidationResult，其中 sanitized 为清洗后的名称
        """
        if not name or not isinstance(name, str):
            return ValidationResult(
                valid=False,
                errors=["工具名称不能为空"]
            )

        stripped = name.strip()

        if not stripped:
            return ValidationResult(
                valid=False,
                errors=["工具名称不能为空（仅含空白字符）"]
            )

        if len(stripped) > cls.MAX_TOOL_NAME_LENGTH:
            return ValidationResult(
                valid=False,
                errors=[f"工具名称超过 {cls.MAX_TOOL_NAME_LENGTH} 字符限制（当前 {len(stripped)}）"]
            )

        if not cls.SAFE_TOOL_NAME_PATTERN.match(stripped):
            return ValidationResult(
                valid=False,
                errors=["工具名称只能包含字母、数字、下划线和连字符"]
            )

        return ValidationResult(valid=True, errors=[], sanitized=stripped)

    @classmethod
    def validate_db_path(cls, path: str) -> ValidationResult:
        """
        验证数据库路径。

        规则:
          - 不允许绝对路径（以 / 开头）
          - 不允许路径遍历（包含 ..）
          - 文件名格式: 字母数字_.- + .db 后缀
          - 不允许包含 null 字节

        返回:
            ValidationResult，其中 sanitized 为清洗后的路径
        """
        if not path or not isinstance(path, str):
            return ValidationResult(
                valid=False,
                errors=["数据库路径不能为空"]
            )

        stripped = path.strip()

        if "\x00" in stripped:
            return ValidationResult(
                valid=False,
                errors=["数据库路径包含非法字符（null byte）"]
            )

        if stripped.startswith("/") or stripped.startswith("\\"):
            return ValidationResult(
                valid=False,
                errors=["数据库路径不允许使用绝对路径"]
            )

        if ".." in stripped:
            return ValidationResult(
                valid=False,
                errors=["数据库路径不允许路径遍历（..）"]
            )

        if not cls.SAFE_DB_NAME_PATTERN.match(stripped):
            return ValidationResult(
                valid=False,
                errors=["数据库文件名格式不正确，应为 name.db（仅允许字母数字_.-）"]
            )

        return ValidationResult(valid=True, errors=[], sanitized=stripped)

    @classmethod
    def validate_interval(cls, seconds) -> ValidationResult:
        """
        验证时间间隔。

        规则:
          - 必须是整数或浮点数
          - 范围: [10, 86400] 秒（10秒 ~ 24小时）
          - 自动转为 int

        返回:
            ValidationResult，其中 sanitized 为 int(seconds)
        """
        if not isinstance(seconds, (int, float)):
            return ValidationResult(
                valid=False,
                errors=[f"时间间隔必须是数字类型，收到 {type(seconds).__name__}"]
            )

        if seconds < cls.MIN_INTERVAL_SECONDS:
            return ValidationResult(
                valid=False,
                errors=[f"时间间隔不能小于 {cls.MIN_INTERVAL_SECONDS} 秒（当前 {seconds}）"]
            )

        if seconds > cls.MAX_INTERVAL_SECONDS:
            return ValidationResult(
                valid=False,
                errors=[f"时间间隔不能超过 {cls.MAX_INTERVAL_SECONDS} 秒（当前 {seconds}）"]
            )

        return ValidationResult(valid=True, errors=[], sanitized=int(seconds))

    @staticmethod
    def sanitize_error_message(error: Exception) -> str:
        """
        消毒错误消息，移除文件系统路径等敏感信息。

        将绝对路径替换为相对占位符，防止内部路径泄露到
        用户可见的错误信息中。

        返回:
            消毒后的错误消息字符串
        """
        msg = str(error)
        # 替换文件系统路径为占位符
        msg = InputValidator.PATH_SANITIZE_PATTERN.sub(r'.../', msg)
        return msg


# ── 便捷函数 ────────────────────────────────────────────────────────────────


def validate_or_raise(result: ValidationResult, label: str = "input") -> Any:
    """
    验证结果，不合法时抛出 ValueError。

    Args:
        result: ValidationResult 实例
        label: 错误描述标签

    Returns:
        result.sanitized

    Raises:
        ValueError: 验证不通过时
    """
    if not result.valid:
        errors = "; ".join(result.errors)
        raise ValueError(f"[{label}] {errors}")
    return result.sanitized

"""
统一日志配置模块

为 HermesAgentEvolution 所有模块提供一致的日志初始化接口。
支持按模块层级配置日志级别、输出到控制台和文件。

用法:
    from src.evolution.logging_config import setup_logging, get_logger
    
    # 应用启动时初始化（只需一次）
    setup_logging(level="INFO", log_file="logs/evolution.log")
    
    # 各模块获取 logger
    log = get_logger(__name__)
    log.info("模块初始化完成")
"""

import logging
import sys
from pathlib import Path
from typing import Optional

LOG_FORMAT = "%(asctime)s | %(levelname)-5s | %(name)-30s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# ── 预定义 logger 层级与默认级别 ──────────────────────────────────────────────────

LOGGER_HIERARCHY = {
    "hermes_evo":                  logging.INFO,
    "hermes_evo.tools":            logging.INFO,
    "hermes_evo.tools.registry":   logging.DEBUG,
    "hermes_evo.learning":         logging.INFO,
    "hermes_evo.memory":           logging.INFO,
    "hermes_evo.security":         logging.WARNING,
    "hermes_evo.collaboration":    logging.INFO,
    "hermes_evo.closed_loop":      logging.INFO,
    "hermes_evo.services":         logging.INFO,
    "hermes_evo.plugin":           logging.INFO,
}

_logging_initialized = False


def get_logger(name: str) -> logging.Logger:
    """
    获取模块 logger。
    
    自动将 `src.evolution.xxx` 转换为 `hermes_evo.xxx` 层级。
    
    Args:
        name: 模块名（通常传 __name__）
    
    Returns:
        logging.Logger 实例
    
    用法:
        from src.evolution.logging_config import get_logger
        log = get_logger(__name__)
        log.info("操作成功")
    """
    # 转换 naming: src.evolution.tools.xxx → hermes_evo.tools.xxx
    if name.startswith("src.evolution."):
        name = "hermes_evo." + name[len("src.evolution."):]
    elif name.startswith("src.services."):
        name = "hermes_evo.services." + name[len("src.services."):]
    elif name.startswith("src.utils."):
        name = "hermes_evo.utils"
    elif name.startswith("hermes_plugin"):
        name = "hermes_evo.plugin"
    
    # 对于不在层级内的 logger，挂在 hermes_evo 下
    if not name.startswith("hermes_evo"):
        name = "hermes_evo." + name
    
    return logging.getLogger(name)


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    console: bool = True,
) -> None:
    """
    统一日志初始化。
    
    应在应用入口（main.py / register() / CLI）调用一次。
    幂等：多次调用不会重复添加 handler。
    
    Args:
        level: 根日志级别 (DEBUG/INFO/WARNING/ERROR/CRITICAL)
        log_file: 日志文件路径（None = 只输出到控制台）
        console: 是否输出到 stderr
    """
    global _logging_initialized
    
    root = logging.getLogger("hermes_evo")
    root.setLevel(getattr(logging, level.upper()))
    
    # 幂等：已初始化则跳过 handler 创建
    if _logging_initialized:
        root.info("日志系统已初始化，跳过重复配置")
        return
    
    root.handlers.clear()
    
    formatter = logging.Formatter(LOG_FORMAT, LOG_DATE_FORMAT)
    
    # 控制台输出
    if console:
        h = logging.StreamHandler(sys.stderr)
        h.setFormatter(formatter)
        root.addHandler(h)
    
    # 文件输出
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        h = logging.FileHandler(log_file, encoding="utf-8")
        h.setFormatter(formatter)
        root.addHandler(h)
    
    # 设置各子模块默认级别
    for name, lvl in LOGGER_HIERARCHY.items():
        logging.getLogger(name).setLevel(lvl)
    
    _logging_initialized = True
    root.info("日志系统初始化完成 (level=%s, file=%s)", level, log_file or "none")


def shutdown_logging():
    """清理所有 handler（优雅退出时调用）"""
    logging.getLogger("hermes_evo").handlers.clear()


# ── 便捷日志函数 ────────────────────────────────────────────────────────────────

def log_tool_call(logger: logging.Logger, tool_name: str, params: dict, result_summary: str = ""):
    """记录工具调用（统一格式）"""
    logger.info("工具调用: %s(params=%s) → %s", tool_name, params, result_summary)


def log_cycle_step(logger: logging.Logger, cycle: int, step: str, detail: str = ""):
    """记录进化循环步骤"""
    logger.info("周期 %d/%s: %s", cycle, step, detail)


def log_db_query(logger: logging.Logger, db_name: str, sql: str, duration_ms: float):
    """记录数据库查询"""
    logger.debug("DB[%s] 查询 [%.1fms]: %s", db_name, duration_ms, sql[:120])

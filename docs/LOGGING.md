# 日志系统使用指南

> HermesAgentEvolution 统一日志框架 — 基于 Python `logging` 模块

---

## 快速开始

```python
from src.evolution.logging_config import setup_logging, get_logger

# 1. 应用启动时初始化（只需一次）
setup_logging(level="INFO", log_file="logs/evolution.log")

# 2. 各模块获取 logger
log = get_logger(__name__)
log.info("模块初始化完成")
```

---

## 架构设计

### Logger 层级

所有模块挂在 `hermes_evo` 根 logger 下，按子系统分层：

| Logger 名称 | 默认级别 | 对应模块 |
|-------------|:------:|----------|
| `hermes_evo` | INFO | 根 logger |
| `hermes_evo.tools` | INFO | 工具创建/注册/分析 |
| `hermes_evo.tools.registry` | DEBUG | 工具注册表（详细查询日志） |
| `hermes_evo.learning` | INFO | 学习观察/模式识别/策略 |
| `hermes_evo.memory` | INFO | 记忆数据库/关联发现/检索 |
| `hermes_evo.security` | WARNING | 安全审计/沙箱/权限（仅告警以上） |
| `hermes_evo.collaboration` | INFO | 代理编排/消息总线 |
| `hermes_evo.closed_loop` | INFO | 闭环控制/指标收集 |
| `hermes_evo.services` | INFO | V2 微服务层 |
| `hermes_evo.plugin` | INFO | Hermes 插件 |

### 命名转换规则

`get_logger()` 自动将 Python 模块路径转换为统一命名：

| 源码路径 | Logger 名 |
|----------|-----------|
| `src.evolution.tools.tool_registry` | `hermes_evo.tools.tool_registry` |
| `src.evolution.learning.observer` | `hermes_evo.learning.observer` |
| `src.services.core.events.event_bus` | `hermes_evo.services.core.events.event_bus` |
| `src.utils.feishu_notifier` | `hermes_evo.utils` |
| `hermes_plugin.__init__` | `hermes_evo.plugin` |

---

## API 参考

### `setup_logging(level, log_file, console)`

应用入口调用一次，幂等（多次调用不会重复添加 handler）。

```python
def setup_logging(
    level: str = "INFO",        # DEBUG/INFO/WARNING/ERROR/CRITICAL
    log_file: str = None,       # 日志文件路径（None=只输出到控制台）
    console: bool = True,       # 是否输出到 stderr
) -> None
```

**示例：**

```python
# 开发环境
setup_logging(level="DEBUG")

# 生产环境
setup_logging(level="INFO", log_file="/var/log/hermes-evo/evolution.log")

# CI 环境（只看 WARNING 以上）
setup_logging(level="WARNING", console=True)
```

### `get_logger(name)`

获取模块专属 logger。

```python
from src.evolution.logging_config import get_logger

log = get_logger(__name__)
log.info("用户 %s 创建了工具 %s", user_id, tool_name)
```

### `shutdown_logging()`

优雅退出时清理所有 handler（通常在 `atexit` 注册）。

---

## 日志格式

```
2026-05-06 14:30:15 | INFO  | hermes_evo.tools.registry    | Tool registered: web_search (id=tool_42)
2026-05-06 14:30:16 | DEBUG | hermes_evo.tools.registry    | SQL: SELECT * FROM tools WHERE... [2.3ms]
2026-05-06 14:30:17 | WARN  | hermes_evo.security          | Permission denied: file_write by user_guest
2026-05-06 14:30:18 | ERROR | hermes_evo.learning          | Observer loop failed: connection timeout
```

---

## 日志级别指南

| 级别 | 使用场景 | 示例 |
|------|---------|------|
| **DEBUG** | 开发调试、DB 查询、模式识别细节 | SQL 语句、检索中间结果 |
| **INFO** | 常规操作、状态变更 | 工具注册、循环步骤、服务启动 |
| **WARNING** | 可恢复异常、安全拒绝 | 权限不足、非致命超时 |
| **ERROR** | 操作失败但不影响系统 | 工具调用失败、模块加载异常 |
| **CRITICAL** | 系统级故障 | 沙箱逃逸尝试、数据损坏 |

---

## 便捷函数

### `log_tool_call(logger, tool_name, params, result_summary)`

统一记录工具调用。

```python
from src.evolution.logging_config import log_tool_call
log_tool_call(log, "web_search", {"query": "AI"}, "返回 15 条结果")
# → INFO: 工具调用: web_search(params={'query': 'AI'}) → 返回 15 条结果
```

### `log_cycle_step(logger, cycle, step, detail)`

记录进化循环步骤。

```python
from src.evolution.logging_config import log_cycle_step
log_cycle_step(log, 3, "analyze", "发现 2 个新模式")
# → INFO: 周期 3/analyze: 发现 2 个新模式
```

### `log_db_query(logger, db_name, sql, duration_ms)`

记录数据库查询。

```python
from src.evolution.logging_config import log_db_query
log_db_query(log, "tools.db", "SELECT * FROM tools WHERE category='utility'", 2.3)
# → DEBUG: DB[tools.db] 查询 [2.3ms]: SELECT * FROM tools WHERE category='utility'
```

---

## 最佳实践

1. **始终使用 `get_logger(__name__)`** 而非 `logging.getLogger()`，确保命名层级正确
2. **使用 `%s` 格式化**而非 f-string，避免日志未输出时仍计算字符串开销
3. **异常日志用 `exc_info=True`**：`log.error("操作失败", exc_info=True)`
4. **避免在循环中打印 DEBUG 日志**，用条件判断：`if log.isEnabledFor(logging.DEBUG): log.debug(...)`
5. **敏感信息脱敏** — 不要打印 token/password 等

---

## 环境变量覆盖

```bash
# 设置根日志级别（不修改代码）
export EVOLUTION_LOG_LEVEL=DEBUG

# 设置日志输出目录
export EVOLUTION_LOG_DIR=/var/log/hermes-evo
```

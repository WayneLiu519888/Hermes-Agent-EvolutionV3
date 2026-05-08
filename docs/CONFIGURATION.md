# 配置参数完整说明

> HermesAgentEvolution v3.0.4 所有可配置项

---

## 概述

HermesAgentEvolution 采用 **环境变量 + 代码默认值** 的配置方式，零配置文件即可运行。

---

## 环境变量

### 数据存储

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EVOLUTION_DATA_DIR` | `~/.hermes/data/evolution/` | 所有 SQLite 数据库文件目录 |
| `HERMES_HOME` | `~/.hermes` | Hermes Agent 主目录（影响插件路径） |

**示例：**

```bash
# 隔离测试数据
export EVOLUTION_DATA_DIR=/tmp/test-evolution-data

# 自定义 Hermes 安装位置
export HERMES_HOME=/opt/hermes
```

---

### 日志

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EVOLUTION_LOG_LEVEL` | `INFO` | 根日志级别：DEBUG/INFO/WARNING/ERROR/CRITICAL |
| `EVOLUTION_LOG_DIR` | 无（输出到 stderr） | 日志文件目录（设置后自动创建 `evolution.log`） |

**示例：**

```bash
# 详细调试
export EVOLUTION_LOG_LEVEL=DEBUG

# 文件日志
export EVOLUTION_LOG_DIR=/var/log/hermes-evo
```

---

### 数据库

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EVOLUTION_DB_TIMEOUT` | `30` | SQLite busy timeout（秒） |
| `EVOLUTION_DB_WAL` | `true` | 启用 WAL 模式（读写并发） |

---

### 通知

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `FEISHU_WEBHOOK` | 无 | 飞书 webhook URL（设置后启用飞书通知） |
| `FEISHU_APP_ID` | 无 | 飞书应用 ID（OpenAPI 模式） |
| `FEISHU_APP_SECRET` | 无 | 飞书应用密钥（OpenAPI 模式） |
| `FEISHU_MODE` | `simulated` | 通知模式：`simulated`/`webhook`/`openapi` |

---

### 安全

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EVOLUTION_SANDBOX_ENABLED` | `true` | 启用沙箱隔离执行 |
| `EVOLUTION_SANDBOX_TIMEOUT` | `30` | 沙箱执行超时（秒） |
| `EVOLUTION_AUDIT_ENABLED` | `true` | 启用安全审计日志 |

---

## 代码级配置

### 日志配置（`evolution/logging_config.py`）

```python
# 修改 logger 层级默认级别
LOGGER_HIERARCHY = {
    "hermes_evo":                  logging.INFO,
    "hermes_evo.tools":            logging.INFO,
    "hermes_evo.tools.registry":   logging.DEBUG,   # ← 详细工具查询日志
    "hermes_evo.security":         logging.WARNING, # ← 仅安全告警
    # ...
}
```

### 数据库配置（`evolution/db_utils.py`）

```python
# SQLite 连接参数（get_evolution_db 中修改）
sqlite3.connect(
    db_path,
    timeout=30,           # busy_timeout
    check_same_thread=False,
    isolation_level=None,
)
```

---

## 数据库文件说明

所有数据库默认存储在 `~/.hermes/data/evolution/`：

| 文件 | 用途 | 大小（典型） |
|------|------|:----:|
| `tools.db` | 工具注册表 | ~50 KB |
| `tool_performance.db` | 工具性能统计 | ~160 KB |
| `learning_experiences.db` | 学习经验记录 | ~90 KB |
| `associations.db` | 记忆关联数据 | 可变（最大） |
| `retrieval_optimization.db` | 检索优化配置 | ~20 KB |

---

## 常用场景配置

### 开发环境

```bash
export EVOLUTION_LOG_LEVEL=DEBUG
export EVOLUTION_DATA_DIR=/tmp/hermes-evo-dev
export FEISHU_MODE=simulated     # 飞书通知写到本地日志
```

### CI 环境

```bash
export EVOLUTION_LOG_LEVEL=WARNING
export EVOLUTION_DATA_DIR=/tmp/hermes-evo-ci-$$
export EVOLUTION_SANDBOX_ENABLED=false
export FEISHU_MODE=simulated
```

### 生产环境

```bash
export EVOLUTION_LOG_LEVEL=INFO
export EVOLUTION_LOG_DIR=/var/log/hermes-evo
export EVOLUTION_DATA_DIR=/var/lib/hermes-evo/data
export FEISHU_MODE=webhook
export FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

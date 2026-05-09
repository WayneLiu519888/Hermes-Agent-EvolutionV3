# 配置参数完整说明

> HermesAgentEvolution v3.0.6 — 所有可配置项

---

## 概述

HermesAgentEvolution 采用 **环境变量 + 代码默认值** 的配置方式，零配置文件即可运行。所有环境变量使用 `EVOLUTION_` 前缀以避免命名冲突。

---

## 环境变量

### 数据存储

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EVOLUTION_DATA_DIR` | `~/.hermes/data/evolution/` | 所有 7 个 SQLite 数据库文件目录 |
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

### 安全

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `EVOLUTION_SANDBOX_ENABLED` | `true` | 启用沙箱隔离执行 |
| `EVOLUTION_SANDBOX_TIMEOUT` | `30` | 沙箱执行超时（秒） |
| `EVOLUTION_AUDIT_ENABLED` | `true` | 启用安全审计日志 |

---

### 通知

| 环境变量 | 默认值 | 说明 |
|----------|--------|------|
| `FEISHU_WEBHOOK` | 无 | 飞书 webhook URL（设置后启用飞书通知） |
| `FEISHU_APP_ID` | 无 | 飞书应用 ID（OpenAPI 模式） |
| `FEISHU_APP_SECRET` | 无 | 飞书应用密钥（OpenAPI 模式） |
| `FEISHU_MODE` | `simulated` | 通知模式：`simulated`/`webhook`/`openapi` |

---

## 代码级配置

### 日志配置 (`evolution/logging_config.py`)

```python
# 修改 logger 层级默认级别
LOGGER_HIERARCHY = {
    "hermes_evo":                  logging.INFO,
    "hermes_evo.tools":            logging.INFO,
    "hermes_evo.tools.registry":   logging.DEBUG,   # ← 详细工具查询日志
    "hermes_evo.learning":         logging.INFO,
    "hermes_evo.memory":           logging.INFO,
    "hermes_evo.security":         logging.WARNING,  # ← 仅安全告警
    "hermes_evo.collaboration":    logging.INFO,
    "hermes_evo.closed_loop":      logging.INFO,
    "hermes_evo.services":         logging.INFO,    # ← V2 微服务层
    "hermes_evo.plugin":           logging.INFO,
}
```

### 数据库配置 (`evolution/db_utils.py`)

```python
# SQLite 连接参数（get_evolution_db 中修改）
sqlite3.connect(
    db_path,
    timeout=30,           # busy timeout
    check_same_thread=False,
    isolation_level=None,
)
# WAL 模式自动启用：PRAGMA journal_mode=WAL
```

### 策略学习器配置

```python
from evolution.learning.tool_strategy_learner import ToolStrategyLearner

learner = ToolStrategyLearner(db_path="tools.db")
learner.exploration_rate = 0.15   # 探索-利用平衡的探索率
learner.learning_rate = 0.05      # 策略更新学习率
learner.min_samples = 5           # 切换策略前的最少样本数
```

### 模式识别器配置

```python
from evolution.learning import PatternRecognizer

recognizer = PatternRecognizer(
    min_support=5,          # 最小支持度（出现次数）
    min_confidence=0.8      # 最小置信度
)
```

---

## 数据库文件说明

所有 7 个数据库默认存储在 `~/.hermes/data/evolution/`：

| 文件 | 用途 | 初建版本 |
|------|------|:------:|
| `tools.db` | 工具注册表 | v1 |
| `tool_performance.db` | 工具性能统计 | v1 |
| `learning_experiences.db` | 学习经验记录 | v1 |
| `associations.db` | 记忆关联数据 | v1 |
| `retrieval_optimization.db` | 检索优化配置 | v2 |
| `closed_loop.db` | 闭环控制状态 | v3.0.0 |
| `evolution_audit.db` | 自进化审计记录 | v3.0.6 |

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

### 测试隔离

```bash
# 每次测试使用独立临时目录
export EVOLUTION_DATA_DIR=$(mktemp -d)
hermes-evolution test
rm -rf "$EVOLUTION_DATA_DIR"
```

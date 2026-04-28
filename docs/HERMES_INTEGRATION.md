# 🔌 HermesAgentEvolution — Hermes 集成指南

**版本:** 2.0.0  
**包名:** `hermes-agent-evolution`  
**插件名:** `hermes-evolution`

将 AI 自我进化引擎集成到 Hermes Agent 中，实现自主经验学习、工具进化、性能优化与闭环改进。

---

## 🏗️ 架构总览

### 守护进程 + 插件双层架构（方案A）

```
┌──────────────────────────────────────────────────────────────────┐
│                     Hermes Agent 运行时                           │
│  ┌─────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────┐  │
│  │   LLM   │  │  Tool Router │  │  Plugins  │  │   Hooks    │  │
│  └────┬────┘  └──────┬───────┘  └─────┬─────┘  └─────┬──────┘  │
│       │              │                │               │         │
│       │              │    ┌───────────┴───────────────┘         │
│       │              │    │                                     │
│       │              ▼    ▼                                     │
│       │   ┌─────────────────────────────────────┐              │
│       │   │  hermes-plugin/__init__.py (薄层)    │              │
│       │   │  ┌───────────────────────────────┐  │              │
│       │   │  │  6 Tools + 1 Hook (register)   │  │              │
│       │   │  │  • evolution_run_cycle         │  │              │
│       │   │  │  • evolution_create_tool       │  │              │
│       │   │  │  • evolution_analyze_performance│  │              │
│       │   │  │  • evolution_learn             │  │              │
│       │   │  │  • evolution_self_monitor      │  │              │
│       │   │  │  • evolution_memory_discover   │  │              │
│       │   │  │  • post_tool_call (hook)       │  │              │
│       │   │  └───────────────┬───────────────┘  │              │
│       │   └──────────────────┼──────────────────┘              │
│       │                      │                                  │
│       │                      ▼                                  │
│       │   ┌─────────────────────────────────────┐              │
│       │   │  HermesAgentEvolution Engine (pip)  │              │
│       │   │  ┌───────────┐ ┌─────────────────┐  │              │
│       │   │  │  Learning  │ │  Tool Evolution  │  │              │
│       │   │  │  Observer →│ │  Registry/Creator│  │              │
│       │   │  │  Analyzer  │ │  Analyzer/Gen    │  │              │
│       │   │  └─────┬─────┘ └────────┬────────┘  │              │
│       │   │        │                │            │              │
│       │   │  ┌─────┴────────────────┴────────┐  │              │
│       │   │  │  SelfMonitor → ClosedLoop     │  │              │
│       │   │  │  Memory → AssociationDiscovery│  │              │
│       │   │  └──────────────┬───────────────┘  │              │
│       │   └─────────────────┼──────────────────┘              │
│       │                     │                                  │
│       │                     ▼                                  │
│       │   ┌─────────────────────────────────────┐              │
│       │   │    Storage Layer (SQLite)            │              │
│       │   │    ~/.hermes/data/evolution/         │              │
│       │   │    experiences.db / tools.db / ...   │              │
│       │   └─────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────┘
                              ▲
                              │ 共享数据库 (松耦合)
                              │
┌─────────────────────────────┴────────────────────────────────────┐
│               hermes_daemon.py (独立守护进程)                      │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  • 自有 CLI (argparse): --daemon / --once / --dry-run       │  │
│  │  • 信号处理 (SIGINT/SIGTERM)                                │  │
│  │  • 生命周期: start() → Monitor→Analyze→Plan→Execute→Verify  │  │
│  │  • 飞书通知回调 (可选)                                       │  │
│  │  • 自适应循环间隔 (60s ~ 3600s)                              │  │
│  └─────────────────────────────────────────────────────────────┘  │
│  运行方式: python hermes_daemon.py --daemon                       │
│  可脱离 Hermes Agent 独立运行                                      │
└──────────────────────────────────────────────────────────────────┘
```

**架构决策（2026-04-29）:** 采用**方案A** — 守护进程独立运行，插件作为纯函数薄层暴露工具。守护进程与 Hermes Agent 松耦合，互不依赖。

---

## 📋 前置要求

| 组件 | 要求 | 检查命令 |
|------|------|----------|
| Python | ≥ 3.9 | `python3 --version` |
| pip | 最新版 | `pip --version` |
| sqlite3 | Python 内置 | `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` |
| Hermes Agent | 已安装运行 | `hermes --version` |
| 磁盘空间 | ≥ 50 MB | `df -h ~/.hermes/` |

> **注意:** 核心模块零外部依赖，仅需 Python 标准库。可选 LLM 功能需要 `openai` 或 `anthropic` 包。

---

## 🚀 步骤一：安装进化引擎

```bash
# 方式 A: 从 PyPI 安装（推荐）
pip install hermes-agent-evolution

# 方式 B: 从源码安装（开发模式）
git clone https://github.com/yourusername/HermesAgentEvolution.git
cd HermesAgentEvolution
pip install -e .

# 验证安装
python3 -c "from evolution import __version__; print(__version__)"
# 输出: 2.0.0
```

---

## 📦 步骤二：部署 Hermes 插件

```bash
# 创建插件目录
mkdir -p ~/.hermes/plugins/hermes-evolution

# 复制插件文件（从 PyPI 安装时，插件位于包内）
# 方式 A: 如果从源码安装
cp -r hermes-plugin/* ~/.hermes/plugins/hermes-evolution/

# 方式 B: 如果从 PyPI 安装，找到包路径
PLUGIN_SRC=$(python3 -c "import hermes_agent_evolution; import os; print(os.path.dirname(hermes_agent_evolution.__file__))")
cp -r "$PLUGIN_SRC/../hermes-plugin/"* ~/.hermes/plugins/hermes-evolution/

# 确认文件结构
ls -la ~/.hermes/plugins/hermes-evolution/
# 输出应包含:
#   __init__.py      ← register(ctx) 入口
#   plugin.yaml      ← 插件元数据
```

`plugin.yaml` 内容：

```yaml
name: hermes-evolution
version: "2.0.0"
description: AI self-evolution engine — autonomous learning, tool creation, performance optimization, and closed-loop improvement for Hermes Agent
```

---

## 🔄 步骤三：重启 Hermes Gateway

```bash
# 重启 Hermes 服务以加载新插件
hermes gateway restart

# 或直接重启（取决于你的 Hermes 部署方式）
systemctl restart hermes-gateway   # systemd
# 或
hermes gateway stop && hermes gateway start
```

重启后，Hermes 会自动扫描 `~/.hermes/plugins/` 目录，调用每个插件的 `register(ctx)` 函数。

---

## ✅ 步骤四：验证安装

### 4.1 检查工具可见性

在 Hermes 会话中执行 `/tools` 命令（或通过你的 Hermes 工具列表接口），确认以下 6 个工具已注册：

```
evolution_run_cycle          ← 触发完整进化周期
evolution_create_tool        ← 创建新工具
evolution_analyze_performance ← 分析工具性能
evolution_learn              ← 记录学习经验
evolution_self_monitor       ← 获取系统健康状态
evolution_memory_discover    ← 发现记忆关联
```

### 4.2 快速功能验证

在 Hermes 会话中：

```
> 请调用 evolution_self_monitor 检查系统状态

预期响应:
{
  "success": true,
  "health_score": 85.0,
  "status": "healthy",
  "metrics": { ... },
  "recommendations": [ ... ]
}
```

### 4.3 检查数据目录

```bash
ls -la ~/.hermes/data/evolution/
# 初次运行后会创建:
#   experiences.db   tools.db   performance.db
#   associations.db  closed_loop.db
```

---

## 🛠️ 工具参考表

| # | 工具名 | 描述 | 必需参数 | 输出 |
|---|--------|------|----------|------|
| 1 | `evolution_run_cycle` | 触发完整进化周期（监控→分析→规划→执行→验证→反馈） | 无 | `{cycle_id, phases, issues_found, actions_taken}` |
| 2 | `evolution_create_tool` | 从 API 描述创建新工具并注册 | `tool_name, description, api_spec` | `{success, tool_name, quality_score, warnings}` |
| 3 | `evolution_analyze_performance` | 分析工具性能指标 | `tool_name`(可选) | `{overall_score, performance_level, key_insights}` |
| 4 | `evolution_learn` | 记录学习经验/教训 | `description` | `{experience_id, confidence, outcome}` |
| 5 | `evolution_self_monitor` | 获取系统健康状态 | `include_history`(可选) | `{health_score, status, metrics, recommendations}` |
| 6 | `evolution_memory_discover` | 发现记忆之间的关联 | `methods, entry_id`(可选) | `{total_associations, methods}` |

### Hook

| Hook 名 | 触发时机 | 行为 |
|---------|----------|------|
| `post_tool_call` | 每次工具调用完成后 | 自动记录工具执行经验到 LearningObserver |

---

## 📂 配置

### 数据库路径

默认数据存储在 `~/.hermes/data/evolution/`，可通过环境变量覆盖：

```bash
export EVOLUTION_DATA_DIR=/custom/path/data
export EVOLUTION_DB_PATH=/custom/path/experiences.db
```

### 进化参数

```bash
# 进化周期间隔（秒）
export EVOLUTION_INTERVAL=3600

# 最小评分阈值（低于此分数的工具会被标记为优化候选）
export EVOLUTION_MIN_SCORE=0.5

# 日志级别
export EVOLUTION_LOG_LEVEL=INFO
```

### 飞书通知（可选）

```json
{
    "mode": "webhook",
    "webhook_url": "https://open.feishu.cn/open-apis/bot/v2/hook/xxx",
    "fallback_mode": "simulated"
}
```

---

## ❓ FAQ

### Q: 插件加载失败怎么办？

检查 Hermes 日志：

```bash
tail -f ~/.hermes/logs/gateway.log | grep "hermes_evolution"
```

常见原因：
- **ImportError**: 未安装 `hermes-agent-evolution` 包，运行 `pip install hermes-agent-evolution`
- **Permission denied**: `~/.hermes/plugins/` 目录权限不足，`chmod 755 ~/.hermes/plugins/hermes-evolution/`
- **路径问题**: 确保 `plugin.yaml` 和 `__init__.py` 在正确位置

### Q: 工具调用返回 "Orchestrator could not be initialized"？

这表示核心引擎模块加载失败。检查：
1. `pip list | grep hermes-agent-evolution` — 确认包已安装
2. `python3 -c "from src.evolution.closed_loop import ClosedLoopOrchestrator"` — 测试导入

### Q: 数据会占用多少磁盘空间？

初期每个数据库文件约 100KB，随使用增长。正常使用下每月增长约 5-10MB。可通过定期归档控制：

```bash
# 查看数据库大小
du -sh ~/.hermes/data/evolution/*.db
```

### Q: 如何卸载？

```bash
# 移除插件
rm -rf ~/.hermes/plugins/hermes-evolution/

# 卸载包
pip uninstall hermes-agent-evolution

# （可选）删除数据
rm -rf ~/.hermes/data/evolution/
```

### Q: 插件支持热重载吗？

支持。修改插件代码后运行 `hermes gateway restart` 即可，无需重新安装 pip 包。

### Q: 可以在其他 AI Agent 中使用吗？

可以！进化引擎 (`hermes-agent-evolution` pip 包) 是独立的 Python 库，可通过编程 API 直接在任何项目中使用，无需 Hermes 插件层。

---

## 🔧 故障排除

| 症状 | 可能原因 | 解决方案 |
|------|----------|----------|
| 工具列表中看不到 `evolution_*` | 插件未加载 | 检查 `~/.hermes/plugins/hermes-evolution/` 目录和 `plugin.yaml` |
| `evolution_run_cycle` 返回空结果 | 数据库未初始化 | 确保 `~/.hermes/data/evolution/` 可写 |
| `evolution_create_tool` 失败 | ToolRegistry 不可用 | 检查数据目录权限，`chmod -R 755 ~/.hermes/data/` |
| 内存持续增长 | 数据库未压缩 | 定期运行 `VACUUM` 清理 SQLite |
| `post_tool_call` hook 不触发 | hook 注册失败 | 查看启动日志确认 `Registered hook: post_tool_call` |
| 跨 session 数据丢失 | 使用了 `:memory:` 数据库 | 确保使用文件路径而非内存数据库 |

### 获取调试日志

```bash
# 设置 DEBUG 级别
export EVOLUTION_LOG_LEVEL=DEBUG

# 重启并观察
hermes gateway restart
tail -f ~/.hermes/logs/gateway.log
```

---

## 📚 相关文档

| 文档 | 说明 |
|------|------|
| [README.md](../README.md) | 项目总览 |
| [INSTALLATION.md](INSTALLATION.md) | 通用安装指南 |
| [API_REFERENCE.md](API_REFERENCE.md) | API 参考 |
| [ARCHITECTURE.md](ARCHITECTURE.md) | 系统架构 |
| [evolution_plan.md](evolution_plan.md) | 迭代计划 |
| [PORTING.md](PORTING.md) | 移植指南 |

---

*让 Hermes Agent 不断从经验中学习，自动进化工具能力，实现真正的自我改进！*

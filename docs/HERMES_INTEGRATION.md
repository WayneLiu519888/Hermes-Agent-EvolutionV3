# 🔌 HermesAgentEvolution — Hermes Agent 集成指南

**版本:** v5.0.0  
**包名:** `hermes-agent-evolution`  
**插件名:** `hermes-evolution`  
**Python:** ≥ 3.9

---

## 架构概览

HermesAgentEvolution 通过 **守护进程 + 插件** 双层架构与 Hermes Agent 集成：

```
┌──────────────────────────────────────┐
│         Hermes Agent Gateway         │
│  ┌────────────────────────────────┐  │
│  │   hermes-evolution 插件         │  │
│  │   7 工具 + 1 Hook              │  │
│  └──────────┬─────────────────────┘  │
│             │ 调用                    │
│  ┌──────────▼─────────────────────┐  │
│  │   Evolution 引擎 (daemon)       │  │
│  │   闭环编排 / 学习 / 工具进化      │  │
│  └──────────┬─────────────────────┘  │
│             │ 持久化                  │
│  ┌──────────▼─────────────────────┐  │
│  │   ~/.hermes/data/evolution/    │  │
│  │   7 个 SQLite 数据库            │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

---

## 快速安装（4 步）

### 步骤 1: pip 安装

```bash
pip install hermes-agent-evolution
```

### 步骤 2: 自检

```bash
hermes-evolution check
```

预期输出：
```
HermesAgentEvolution CLI v5.0.0
✅ 所有子系统可用
✅ 数据库连接正常
✅ 7 工具已就绪
```

### 步骤 3: 部署为 Hermes 插件

```bash
hermes-evolution setup
```

这会将插件注册到 `~/.hermes/plugins/hermes-evolution/`。

### 步骤 4: 验证

```bash
# 在 Hermes Agent 中:
hermes tools list | grep evolution
```

预期看到 7 个工具。

---

## 7 个 Hermes 工具

| # | 工具名 | 描述 | 返回 |
|---|--------|------|------|
| 1 | `evolution_memory_discover` | 发现记忆关联 | 关联列表 + 强度分数 |
| 2 | `evolution_create_tool` | 创建/优化工具 | 工具定义 + 测试结果 |
| 3 | `evolution_run_cycle` | 执行完整进化循环 | 6 阶段结果 + 改进摘要 |
| 4 | `evolution_learn` | 记录学习经验 | 经验 ID + 统计数据 |
| 5 | `evolution_self_monitor` | 自我健康监控 | 健康分数 (0-100) + 建议 |
| 6 | `evolution_audit` 🆕 | 查询进化审计记录 | 循环历史 + 趋势分析 |
| 7 | `evolution_health_check` | 快速健康快照 | 全系统状态 |

### 1 个 Hook

| Hook | 触发时机 | 作用 |
|------|---------|------|
| `post_tool_call` | 每次工具调用后 | 驱动 ToolStrategyLearner 持久化记录 |

---

## 数据库

所有数据持久化到 `~/.hermes/data/evolution/`：

| 数据库 | 用途 | 大小 |
|--------|------|------|
| `tools.db` | 工具注册表 + tool_usage_history | ~65 KB |
| `tool_performance.db` | 工具性能历史 | ~168 KB |
| `learning_experiences.db` | 学习经验（123 条） | ~95 KB |
| `associations.db` | 记忆关联（430 万条） | ~2 GB |
| `retrieval_optimization.db` | 检索优化参数 | ~20 KB |
| `closed_loop.db` | 进化循环快照 | ~32 KB |
| `evolution_audit.db` 🆕 | 进化审计 (cycles + actions) | ~16 KB |

---

## 配置

通过环境变量配置，所有以 `EVOLUTION_` 为前缀：

```bash
# 数据目录（默认 ~/.hermes/data/evolution/）
export EVOLUTION_DATA_DIR=/path/to/data

# 日志级别 (DEBUG/INFO/WARNING/ERROR)
export EVOLUTION_LOG_LEVEL=INFO

# 飞书通知（默认 simulated）
export FEISHU_MODE=webhook          # webhook | openapi | simulated
export FEISHU_WEBHOOK_URL=https://open.feishu.cn/...

# 闭环编排
export EVOLUTION_CYCLE_INTERVAL=3600  # 进化周期（秒）
export EVOLUTION_MIN_SCORE=60.0       # 最低性能阈值
```

---

## 飞书通知

支持三种模式：

| 模式 | 适用场景 | 需要配置 |
|------|---------|---------|
| `webhook` | 简单群通知 | `FEISHU_WEBHOOK_URL` |
| `openapi` | 高级交互卡片 | App ID + App Secret |
| `simulated` (默认) | 本地开发测试 | 无需配置 |

---

## 常见问题

### Q: 如何查看当前健康状态？
```bash
# CLI:
hermes-evolution status

# Hermes 工具:
evolution_self_monitor
# 返回: health_score (0-100), success_rate, monitored_tools, recommendations
```

### Q: 如何查看进化历史？
```bash
evolution_audit
# 返回: 最近 N 次进化循环的摘要、趋势、成功率变化
```

### Q: 工具注册失败？
```bash
# 检查插件是否部署
hermes tools list | grep evolution

# 如果无输出，重新部署
hermes-evolution setup

# 清理 pyc 缓存后重启
rm -rf ~/.hermes/plugins/hermes-evolution/__pycache__
hermes gateway restart
```

### Q: 数据库膨胀？
```bash
# CLI 一键清理
hermes-evolution check --clean

# 手动 WAL checkpoint
python3 -c "import sqlite3; c=sqlite3.connect('associations.db'); c.execute('PRAGMA wal_checkpoint(TRUNCATE)')"
```

### Q: 导入路径问题
- pip 安装后使用: `from evolution.closed_loop import ClosedLoopOrchestrator`
- 开发模式使用: `from src.evolution.closed_loop import ClosedLoopOrchestrator`

---

## 版本历史

| 版本 | 日期 | 关键变化 |
|------|------|---------|
| v5.0.0 | 2026-05-09 | EvolutionAuditor + 文档重构 |
| v3.0.5 | 2026-05-09 | ToolStrategyLearner 持久化 |
| v3.0.4 | 2026-05-08 | P0 修复 + CI 防回归 |
| v3.0.3 | 2026-05-07 | 版本号统一 |
| v3.0.2 | 2026-05-07 | 插件嵌入包内 |
| v3.0.1 | 2026-05-07 | PyPI 发布 |
| v3.0.0 | 2026-05-06 | 融合架构 |

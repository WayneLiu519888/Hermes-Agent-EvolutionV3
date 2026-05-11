# 测试指南

> HermesAgentEvolution v7.0.1 — 24 测试文件，439 passed

---

## 快速开始

```bash
# 运行全部测试（推荐用 CLI）
hermes-evolution test

# 或直接使用 pytest
cd /mnt/c/Users/1/hermes_agent_evolution
python3 -m pytest tests/ -v

# 快速模式（仅显示失败）
python3 -m pytest tests/ -q

# 运行单个模块测试
python3 -m pytest tests/test_closed_loop.py -v
python3 -m pytest tests/test_db_utils.py -v
python3 -m pytest tests/test_evolution_auditor.py -v

# 查看测试收集（不执行）
python3 -m pytest tests/ --collect-only -q
```

---

## 测试框架

- **主框架**: pytest 7.4+
- **兼容框架**: unittest（部分旧测试迁移中）
- **Mock**: `unittest.mock` (MagicMock, patch)
- **临时文件**: `tempfile.TemporaryDirectory` / `tmp_path` fixture

---

## 测试文件结构 (24 文件, 439 passed)

| 测试文件 | 覆盖模块 | 用例数 | 状态 |
|----------|----------|:----:|:--:|
| `test_closed_loop.py` | orchestrator, action_executor, daemon, metrics_collector | 58 | ✅ |
| `test_collaboration.py` | agent_orchestrator, agent_registry, message_bus, task_dispatcher | 43 | ✅ |
| `test_fusion.py` | bridge, compatibility, unified_entry | 48 | ✅ |
| `test_security.py` | audit_logger, permission_manager, sandbox_executor, threat_detector | 40 | ✅ |
| `test_pattern_recognizer.py` | pattern_recognizer | 35 | ✅ |
| `test_self_monitor.py` | self_monitor | 28 | ✅ |
| `test_iteration6_integration.py` | hermes-plugin 集成 | 27 | ✅ |
| `test_db_utils.py` | db_utils (WAL 连接工厂) | 22 | ✅ |
| `test_tool_integration.py` | tool_integration, EvolutionEngine | 22 | ✅ |
| `test_tool_creator.py` | tool_registry, tool_creator | 17 | ✅ |
| `test_observer.py` | observer, experience | 14 | ✅ |
| `test_retrieval_optimizer.py` | retrieval_optimizer | 14 | ✅ |
| `test_tool_strategy_persistence.py` | tool_strategy_learner 持久化 (v3.0.5 新增) | 12 | ✅ |
| `test_association_discovery.py` | association_discoverer, database | 12 | ✅ |
| `test_evolution_auditor.py` | evolution_auditor (v7.0.1 新增) | 11 | ✅ |
| `test_association_optimizer.py` | association_optimizer | 8 | ✅ |
| `test_learning_evolution_integration.py` | 学习系统集成 | 8 | ✅ |
| `test_enhanced_tool_creator.py` | enhanced_tool_creator | 8 | ✅ |
| `test_tool_auto_generator.py` | tool_auto_generator | 8 | ✅ |
| `test_tool_evolution.py` | 工具进化引擎 | 7 | ✅ |
| `test_iteration3_integration.py` | 迭代3集成 | 7 | ✅ |
| `test_tool_performance.py` | tool_performance_analyzer | 4 | ✅ |
| `test_core_functionality.py` | 核心功能 | 3 | ✅ |
| `test_simple_integration.py` | 简化集成 | 2 | ✅ |
| `test_ci_guards.py` | CI 守卫/快速冒烟 (v7.0.1 新增) | 8 | ✅ |

---

## 重点测试文件说明

### `test_tool_strategy_persistence.py` (v3.0.5 新增)

验证 `ToolStrategyLearner` 的 SQLite 持久化：

- 创建 → 记录工具使用 → 销毁重建 → 数据恢复
- `record_tool_usage` 同步写入 DB
- `_load_from_db` 重建内存状态
- 重启后 `get_tool_performance_summary()` 非空

### `test_evolution_auditor.py` (v7.0.1 新增)

验证 `EvolutionAuditor` 自进化审计模块：

- `record_cycle()` 持久化进化周期
- `query_cycles()` 查询历史
- `get_cycle_detail()` 获取完整详情
- `get_summary()` 统计汇总
- 审计记录失败不影响进化流程

### `test_ci_guards.py` (v7.0.1 新增)

CI 快速冒烟测试：

- 核心模块导入检查
- DB 连接可用性
- 最小功能验证

---

## 覆盖率目标

| 模块 | 目标 | 当前 |
|------|:----:|:----:|
| closed_loop/ | ≥70% | ~85% |
| collaboration/ | ≥75% | ~80% |
| fusion/ | ≥75% | ~80% |
| learning/ | ≥70% | ~78% |
| memory/ | ≥70% | ~75% |
| security/ | ≥75% | ~80% |
| tools/ | ≥70% | ~75% |
| db_utils | ≥85% | ~90% |
| self_monitor | ≥80% | ~90% |
| **整体** | **≥75%** | **~78%** |

---

## 常见问题

### 测试超时

完整测试套件约需 20-40 秒。如果个别测试挂起，使用 `--timeout=30` 限制：

```bash
python3 -m pytest tests/ -v --timeout=30
```

### 数据库连接问题

测试使用临时目录，不会影响正式数据。如果看到 "database is locked"：

1. 确保没有其他进程使用同一数据库
2. 检查 `_connection_cache` 是否在 tearDown 中清理
3. 设置隔离数据目录：`export EVOLUTION_DATA_DIR=$(mktemp -d)`

### 脏工作区导致的测试失败

如果 `git status` 显示未提交的修改，部分测试可能失败。先执行 `git stash` 运行测试验证干净基线的状态，然后再 `git stash pop` 恢复。

---

## CI 流程

```yaml
# .github/workflows/test.yml (推荐配置)
steps:
  - uses: actions/checkout@v4
  - uses: actions/setup-python@v5
    with:
      python-version: ["3.9", "3.10", "3.11", "3.12", "3.13"]
  - run: pip install -e ".[dev]"
  - run: pytest tests/ -v --tb=short --timeout=60
  - run: pytest tests/ --cov=src --cov-report=term
```

---

## 运行特定测试

```bash
# 按模块
python3 -m pytest tests/test_closed_loop.py -v
python3 -m pytest tests/test_evolution_auditor.py -v

# 按关键标记
python3 -m pytest tests/ -m "not slow" -v

# 只运行新增测试
python3 -m pytest tests/test_tool_strategy_persistence.py tests/test_evolution_auditor.py tests/test_ci_guards.py -v

# 失败即停
python3 -m pytest tests/ -x
```

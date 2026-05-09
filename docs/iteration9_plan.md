# 迭代9: ToolStrategyLearner 持久化

**创建时间**: 2026-05-09  
**目标**: 解决工具性能数据在网关重启后丢失的问题（33个工具中29个"尚无性能数据"）

---

## 根因分析

三处断链导致85%工具无性能数据：

```
post_tool_call hook (有数据源)
    │
    ├── record_experience() ✅ → experience.db (正常)
    │
    ├── strategy_learner.record_tool_usage() ❌ — 从未被调用
    │
    └── tool_performance_analyzer.record_performance() ❌ — 从未被调用
```

| 组件 | 持久化 | 问题 |
|------|--------|------|
| `ToolStrategyLearner` | 纯内存 | 重启丢失，`tool_performance` dict 清空 |
| `ToolPerformanceAnalyzer` | `tool_performance.db` | 有DB但 `record_performance()` 未被调用 |
| `post_tool_call` | 只记录 Experience | 未驱动以上两个组件 |

---

## 任务清单

### 任务 A: ToolStrategyLearner SQLite 持久化 (核心, ~3h)

**文件**: `src/evolution/learning/tool_strategy_learner.py`

**A1. `__init__` 新增 DB 初始化**

```python
def __init__(self, db_path: str = "tools.db"):
    # 新增持久化层
    self.db_path = db_path
    self.tool_performance: Dict[str, ToolPerformance] = {}
    self.strategy_performance: Dict[ToolStrategyType, StrategyPerformance] = {}
    self.current_strategy: ToolStrategyType = ToolStrategyType.ADAPTIVE
    self.exploration_rate = 0.2
    self.learning_rate = 0.1
    self.min_samples = 3
    
    # 初始化策略性能
    for strategy in ToolStrategyType:
        self.strategy_performance[strategy] = StrategyPerformance(...)
    
    # 🆕 从 DB 加载历史数据
    self._init_db()
    self._load_from_db()
```

**A2. 创建 `tool_usage_history` 表**

```sql
CREATE TABLE IF NOT EXISTS tool_usage_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tool_name TEXT NOT NULL,
    success INTEGER NOT NULL,
    execution_time REAL NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    context TEXT
);
CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage_history(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_usage_time ON tool_usage_history(timestamp);
```

**A3. `record_tool_usage()` 同步写 DB**

```python
def record_tool_usage(self, tool_name, success, execution_time, context=None):
    # 现有内存更新逻辑 (不变)
    ...
    
    # 🆕 同步写入 SQLite
    conn = get_evolution_db(self.db_path)
    conn.execute(
        "INSERT INTO tool_usage_history (tool_name, success, execution_time, timestamp, context) "
        "VALUES (?, ?, ?, ?, ?)",
        (tool_name, int(success), execution_time, datetime.now().isoformat(), json.dumps(context or {}))
    )
    conn.commit()
```

**A4. `_load_from_db()` — 启动时回放历史**

```python
def _load_from_db(self):
    """从 DB 加载历史数据重建内存状态"""
    conn = get_evolution_db(self.db_path)
    # 最近7天的记录
    cutoff = (datetime.now() - timedelta(days=7)).isoformat()
    rows = conn.execute(
        "SELECT tool_name, success, execution_time FROM tool_usage_history "
        "WHERE timestamp >= ? ORDER BY timestamp",
        (cutoff,)
    ).fetchall()
    
    for row in rows:
        tool_name = row[0]
        success = bool(row[1])
        execution_time = row[2]
        # 更新内存数据结构 (不重复写DB)
        if tool_name not in self.tool_performance:
            self.tool_performance[tool_name] = ToolPerformance(tool_name=tool_name)
        perf = self.tool_performance[tool_name]
        if success:
            perf.success_count += 1
        else:
            perf.failure_count += 1
        perf.total_time += execution_time
        perf.usage_count += 1
        perf.last_used = datetime.now()
        if perf.usage_count > 0:
            perf.avg_time = perf.total_time / perf.usage_count
            total = perf.success_count + perf.failure_count
            perf.success_rate = perf.success_count / total if total > 0 else 0.0
```

### 任务 B: post_tool_call hook 驱动记录 (~1h)

**文件**: `hermes-plugin/__init__.py` (及 `_plugin/` 副本)

在 `_on_post_tool_call` 中增加调用：

```python
def _on_post_tool_call(ctx, tool_name, params, result, duration_ms, error):
    try:
        observer = _get_learning_observer()
        if observer is None:
            return
        
        # ... 现有 Experience 记录逻辑 (不变) ...
        
        # 🆕 驱动 strategy_learner 记录
        strategy_learner = _get_strategy_learner()
        if strategy_learner:
            success = not bool(error)
            strategy_learner.record_tool_usage(
                tool_name=tool_name,
                success=success,
                execution_time=(duration_ms or 0) / 1000.0,
                context={"params": str(params)[:200] if params else ""}
            )
        
        # 🆕 驱动 tool_performance_analyzer 记录
        analyzer = _get_tool_performance_analyzer()
        if analyzer:
            analyzer.record_performance(
                tool_name=tool_name,
                metric=PerformanceMetric.EXECUTION_TIME,
                value=(duration_ms or 0) / 1000.0,
                metadata={"success": not bool(error)}
            )
    except Exception:
        pass
```

新增辅助函数：

```python
def _get_strategy_learner():
    """获取或创建 strategy_learner 单例"""
    if _get_strategy_learner._instance is None:
        from evolution.learning.tool_strategy_learner import ToolStrategyLearner
        _get_strategy_learner._instance = ToolStrategyLearner(db_path="tools.db")
    return _get_strategy_learner._instance
_get_strategy_learner._instance = None

def _get_tool_performance_analyzer():
    """获取或创建性能分析器单例"""
    if _get_tool_performance_analyzer._instance is None:
        from evolution.tools.tool_performance_analyzer import ToolPerformanceAnalyzer
        from evolution.tools.tool_registry import ToolRegistry
        registry = ToolRegistry()
        _get_tool_performance_analyzer._instance = ToolPerformanceAnalyzer(registry, db_path="tool_performance.db")
    return _get_tool_performance_analyzer._instance
_get_tool_performance_analyzer._instance = None
```

### 任务 C: 清理 _count_tools_from_db 裸连接 (~30min)

**文件**: `src/evolution/self_monitor.py`

将 `_count_tools_from_db()` 的裸 `sqlite3.connect` 改为使用 `get_evolution_db("tools.db")`：

```python
def _count_tools_from_db(self) -> int:
    """从 tools.db 统计已注册工具数量（重启后策略学习器内存为空时的回退）"""
    try:
        conn = get_evolution_db("tools.db")
        count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
        return count
    except Exception:
        return 0
```

### 任务 D: 测试 (~1.5h)

**D1.** `tests/test_tool_strategy_persistence.py` (新增)

- 测试创建 → 记录 → 销毁重建 → 数据恢复
- 测试 `record_tool_usage` 写入 DB
- 测试 `_load_from_db` 重建内存状态
- 测试 `get_tool_performance_summary` 在重建后非空

**D2.** `test_iteration6_integration.py` 已有 hook 测试，验证不回归

**D3.** `evolution_analyze_performance` 端到端测试 — 模拟几次工具调用后检查报告

### 任务 E: 同步三副本 + 版本号 (~15min)

- `hermes-plugin/__init__.py` → `src/evolution/_plugin/__init__.py` 复制
- `pyproject.toml` 版本号 `3.0.5`
- VERSION 文件 `3.0.5`

---

## 验收标准

| 标准 | 当前 | 目标 |
|------|------|------|
| 重启后 `get_tool_performance_summary()` | 空 dict | 至少有最近7天的数据 |
| `evolution_analyze_performance` 有数据工具数 | 4/33 | 随工具使用逐步增长 |
| 测试回归 | 428 passed | ≥ 428 passed |

---

## 不做什么

- 不改变 `ToolPerformanceAnalyzer` 的 DB 结构（`tool_performance.db` 已有持久化，只是缺数据源）
- 不改 `evolution_memory_discover`（语义关联发现与工具性能无关）
- 不迁移旧的裸 `sqlite3.connect`（除任务C指定的 `_count_tools_from_db`）

# 迭代9 新增模块: 自进化审计器 (EvolutionAuditor)

**创建时间**: 2026-05-09  
**所属迭代**: 迭代9  
**目标**: 持久化记录每次进化周期的详细信息，支持历史查询和趋势分析

---

## 1. 需求背景

当前 `ClosedLoopOrchestrator` 的 `run_full_cycle()` 产出结果仅存于内存 `self.cycle_history[]`，网关重启即丢失。虽有 `learning_experiences.db` 记录通用经验，但：
- 经验表是通用结构，不适合结构化查询进化历史
- `daemon_state.json` 仅存最近快照，无历史追溯
- `system_metrics.jsonl` 只有系统指标，无进化上下文

需要一个专门的审计模块，永久记录每次自进化的全过程。

---

## 2. 数据库设计

**数据库**: `~/.hermes/data/evolution/evolution_audit.db`

### 2.1 evolution_cycles 表

```sql
CREATE TABLE IF NOT EXISTS evolution_cycles (
    cycle_id          INTEGER PRIMARY KEY,
    started_at        DATETIME NOT NULL,
    finished_at       DATETIME,
    duration_ms       REAL DEFAULT 0,
    success           INTEGER DEFAULT 1,
    trigger           TEXT DEFAULT 'manual',     -- manual / scheduled / auto / hook

    -- 各阶段状态
    phase_monitor     TEXT DEFAULT 'pending',    -- pending / running / completed / failed / skipped
    phase_analyze     TEXT DEFAULT 'pending',
    phase_plan        TEXT DEFAULT 'pending',
    phase_execute     TEXT DEFAULT 'pending',
    phase_verify      TEXT DEFAULT 'pending',
    phase_feedback    TEXT DEFAULT 'pending',

    -- 关键指标 (before)
    health_score_before  REAL,
    success_rate_before  REAL,
    tools_count_before   INTEGER,
    experiences_before   INTEGER,

    -- 关键指标 (after)
    health_score_after   REAL,
    success_rate_after   REAL,
    tools_count_after    INTEGER,
    experiences_after    INTEGER,

    -- 阶段产出统计
    issues_found          INTEGER DEFAULT 0,
    patterns_discovered   INTEGER DEFAULT 0,
    actions_planned       INTEGER DEFAULT 0,
    actions_executed      INTEGER DEFAULT 0,
    actions_succeeded     INTEGER DEFAULT 0,
    improvements_detected INTEGER DEFAULT 0,
    errors_count          INTEGER DEFAULT 0,

    -- 改进摘要
    improvement_summary   TEXT,     -- JSON: [{type, target, description}]
    error_summary         TEXT,     -- JSON: [{phase, message}]
    notes                 TEXT      -- 人工备注 (预留)
);

CREATE INDEX idx_cycles_started ON evolution_cycles(started_at);
CREATE INDEX idx_cycles_success ON evolution_cycles(success);
```

### 2.2 evolution_actions 表

```sql
CREATE TABLE IF NOT EXISTS evolution_actions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id      INTEGER NOT NULL REFERENCES evolution_cycles(cycle_id),
    action_type   TEXT NOT NULL,    -- tool_optimization / strategy_switch / parameter_tuning /
                                    -- tool_creation / tool_deprecation / db_maintenance / config_change
    target        TEXT,             -- 目标组件名
    description   TEXT,
    phase         TEXT,             -- plan / execute / verify (哪个阶段产生)
    before_state  TEXT,             -- JSON: 变更前状态
    after_state   TEXT,             -- JSON: 变更后状态
    success       INTEGER DEFAULT 1,
    error_message TEXT,
    duration_ms   REAL,
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_actions_cycle ON evolution_actions(cycle_id);
CREATE INDEX idx_actions_type   ON evolution_actions(action_type);
```

---

## 3. 模块接口

**文件**: `src/evolution/closed_loop/evolution_auditor.py`

```python
class EvolutionAuditor:
    """自进化审计器 — 持久化记录和查询进化历史"""

    def __init__(self, db_path: str = "evolution_audit.db"):
        """初始化审计器，创建表结构"""

    # ── 写入 ──
    def record_cycle(self, result: Dict[str, Any]) -> int:
        """
        记录一次完整的进化周期。

        Args:
            result: orchestrator.run_full_cycle() 的返回结果

        Returns:
            cycle_id: 记录的周期ID
        """

    def record_action(self, cycle_id: int, action: Dict[str, Any],
                      phase: str, success: bool, error: str = None):
        """记录单个进化动作"""

    # ── 查询 ──
    def query_cycles(self, limit: int = 20, days: int = 30,
                     success_only: bool = False) -> List[Dict]:
        """
        查询进化历史列表。

        Returns:
            每个周期的摘要信息: cycle_id, 时间, 成功/失败, 健康分变化, 改进数
        """

    def get_cycle_detail(self, cycle_id: int) -> Dict:
        """
        查询单次进化的完整详情。

        Returns:
            {cycle_info, phases_detail, actions, before/after_metrics, errors}
        """

    def get_summary(self, days: int = 30) -> Dict:
        """
        统计汇总。

        Returns:
            {
                total_cycles: int,
                success_rate: float,
                avg_duration_ms: float,
                avg_health_improvement: float,     # 健康分平均提升
                total_improvements: int,
                most_common_actions: [{type, count}],
                trend: [{week, cycles, avg_health, avg_duration}],  # 按周趋势
            }
        """

    def get_latest_health_trend(self, limit: int = 10) -> List[Dict]:
        """
        最近N次进化的健康分变化趋势。

        Returns:
            [{cycle_id, started_at, health_before, health_after, delta}]
        """
```

---

## 4. 集成点

### 4.1 在 orchestrator.run_full_cycle() 中集成

```python
# 在 run_full_cycle() 末尾，cycle_history.append(result) 之后：

try:
    auditor = _get_evolution_auditor()
    if auditor:
        auditor.record_cycle(result)
except Exception as e:
    logger.warning("审计记录失败: %s", e)
```

### 4.2 在 plugin handler 中提供查询接口

新增 `evolution_audit` 工具，或在 `evolution_self_monitor` 的返回中附加最近进化历史摘要。

### 4.3 向后兼容

- 不改变 `run_full_cycle()` 的返回值格式
- 审计记录失败不影响进化流程
- 已存在的 `daemon_state.json` / `cycle_history` 保持不变

---

## 5. 查询示例

```
用户: "最近3次进化的情况？"
→ auditor.query_cycles(limit=3)
  [
    {cycle_id: 3, started: "09:30", health: 65→72, actions: 2, success: True},
    {cycle_id: 2, started: "08:45", health: 60→65, actions: 1, success: True},
    {cycle_id: 1, started: "08:00", health: 55→60, actions: 3, success: True},
  ]

用户: "第2次进化具体做了什么？"
→ auditor.get_cycle_detail(2)
  {cycle_info: {...}, phases: {...}, actions: [{type: "strategy_switch", ...}]}

用户: "近30天进化趋势？"
→ auditor.get_summary(days=30)
  {total_cycles: 12, success_rate: 0.92, avg_health_improvement: 4.2, trend: [...}
```

---

## 6. 与现有数据源的关系

| 数据源 | 用途 | 本模块关系 |
|--------|------|-----------|
| `learning_experiences.db` | 通用经验(工具调用等) | 互补，不重复 |
| `daemon_state.json` | 当前状态快照 | 互补，本模块提供历史 |
| `system_metrics.jsonl` | 系统指标时序 | 互补，本模块关联进化上下文 |
| `cycle_history` (内存) | 当前会话历史 | 本模块是其持久化版本 |
| `evolution_audit.db` (新增) | 进化历史审计 | 本模块 |

---

## 7. 文件清单

| 文件 | 操作 | 行数估算 |
|------|------|---------|
| `src/evolution/closed_loop/evolution_auditor.py` | 新建 | ~350 |
| `src/evolution/closed_loop/__init__.py` | 修改 (导出) | +1 |
| `src/evolution/closed_loop/orchestrator.py` | 修改 (集成) | +5 |
| `hermes-plugin/__init__.py` | 修改 (单例+查询) | +50 |
| `tests/test_evolution_auditor.py` | 新建 | ~150 |
| `docs/iteration9_plan.md` | 修改 (追加) | +20 |

**总工作量**: ~3h (2h开发 + 1h测试集成)

---

## 8. 验收标准

- [ ] 执行 `evolution_run_cycle` 后 `evolution_audit.db` 中有对应记录
- [ ] `auditor.query_cycles(limit=5)` 返回最近5次进化摘要
- [ ] `auditor.get_cycle_detail(N)` 返回完整 phase 详情 + actions
- [ ] `auditor.get_summary()` 返回正确的统计汇总
- [ ] 审计记录失败不影响进化流程 (warn, 不抛异常)
- [ ] 428 测试无回归

# HAE 两套追踪系统割裂 — 架构回溯报告

**日期**: 2026-05-17  
**版本**: v8.0.18  
**视角**: 架构师  

---

## 一、问题现象

`hae audit issues` 持续报：

```
#105 [high] low_success_rate: 系统成功率偏低: 0.0%
```

实际周期执行正常（118个周期全部OK，5个动作每次成功），但审计监控声称成功率 0%。

---

## 二、数据流全局图

```
┌─────────────────────────────────────────────────────────────────┐
│                     Hermes 平台层                                │
│  工具调用 ──→ post_tool_call hook ──→ _on_post_tool_call()      │
└──────────────────────────┬──────────────────────────────────────┘
                           │
          ┌────────────────┼────────────────────┐
          ▼                ▼                     ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
   │ 写入         │  │ 写入         │  │ 读取             │
   │ experiences  │  │ tool_usage_  │  │ experiences      │
   │ (经验级)     │  │ history      │  │ → success_rate   │
   │              │  │ (调用级)     │  │                  │
   └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
          │                 │                    │
          ▼                 ▼                    ▼
   ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐
   │ learning_    │  │ tools.db     │  │ orchestrator     │
   │ experiences │  │              │  │ → _analyze_      │
   │ .db          │  │              │  │   phase()       │
   └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘
          │                 │                    │
          ▼                 ▼                    ▼
   ExperienceAnalyzer  ToolStrategy    low_success_rate issue
   .success_rate       Learner         (if < 0.6)
                       _load_from_db
                        → success_rate
```

**核心断裂点：两条写入路径之间没有任何协调，写入和读取之间也没有contract。**

---

## 三、历史根源：三次迭代的欠债累积

### V1 时期（原始设计）

- 只有 `learning_experiences.db` 一个数据源
- `ExperienceAnalyzer` 从 experiences 表计算 `success_rate`
- `ToolStrategyLearner` 尚不存在，没有工具使用追踪

### V3 时期（引入 ToolStrategyLearner）

- 新增 `tools.db → tool_usage_history` 表
- 设计意图：追踪每条工具调用的成功/失败、耗时
- `ToolStrategyLearner._load_from_db()` 从该表计算工具成功率
- **但没有建立写入路径** — 谁来写入？设计文档未覆盖

### V3→V8 时期（假数据填补）

- `action_executor._execute_strategy_switch()` 在每个周期伪造 4 条工具调用的 success=True 记录
- 41,000+ 周期 × 4 = **54,157 条假记录** 堆积在 tool_usage_history 表中
- 假数据掩盖了"没人写真实数据"这个架构缺陷
- `orchestrator._analyze_phase()` 读取 ToolStrategyLearner 的工具成功率生成 issue，但数据全是假的

### V8.0.3（清理假数据）

- 删除 action_executor 中的伪造代码
- 清空 tool_usage_history 表的 54,157 条记录
- **但没有补上真实写入路径** — 从"假数据"变成了"无数据"

### V8.0.18（本次修复，临时方案）

- 在 `_on_post_tool_call` hook 中新增 sqlite3 直写 tool_usage_history
- **问题本质未解决**：方案是在 hook 层打补丁，而非在架构层统一

---

## 四、架构缺陷清单

### 缺陷 1：单一数据源被拆成两份，没有协调器

| 维度 | learning_experiences.db | tools.db |
|------|------------------------|----------|
| 粒度 | Experience（经验级） | Usage（调用级） |
| 字段 | outcome: success/failure/uncertain | success: 0/1 |
| 写入者 | _on_post_tool_call | 无（v8.0.18后 = _on_post_tool_call） |
| 读取者 | ExperienceAnalyzer → success_rate | ToolStrategyLearner → success_rate |
| 关联 | 无 | 无 |

**结论**：两个系统互不知晓对方存在。同一个工具调用事件同时写入两个独立表，但没有逻辑关联（无外键、无统一ID、无事务保证）。

### 缺陷 2：Hook 层越级操作

```
正确的分层：
  Hermes平台 post_tool_call
       │
  Hook层 _on_post_tool_call  ← 只做路由，不做业务
       │
  业务层 统一数据入口（不存在！）
       ├─→ Experience（经验级）      
       └─→ ToolUsage（调用级）      
       └─→ Metrics（指标级）       

实际的架构（v8.0.18）：
  Hermes平台 post_tool_call
       │
  Hook层 _on_post_tool_call
       ├─→ LearningObserver → learning_experiences.db  (正常)
       └─→ sqlite3.execute → tools.db                 (越级！)
```

**Hook 直接写数据库，绕过了所有业务层**。如果将来 ToolStrategyLearner 需要修改写入逻辑（比如增加TTL、去重、聚合），Hook 层不会被通知。

### 缺陷 3：11 个独立 DB，无统一 Schema 管理

```
evolution_audit.db   (22 cycles, 446 actions)    ← EvolutionAuditor
tools.db             (24 tools, 0 usage)          ← ToolStrategyLearner
tool_performance.db  (1,867 performance_records)  ← MetricsCollector
learning_experiences.db (2 experiences)           ← LearningObserver
associations.db      (100K associations)          ← AssociationDiscoverer
agent_memory.db      (0 memory_entries)           ← KnowledgeAgent
evolution.db         (空)                          ← 未知
evolution_state.db   (0 snapshots)                ← 未知
audit.db             (0 audit_log)                ← 未知
retrieval_optimization.db (全空)                   ← 未知
_cli_check.db        (临时检查)                    ← CLI check
```

**症状**：
- 3 个表完全空（evolution.db, evolution_state.db, agent_memory.db）
- 多个表有 `_schema_version` 但值都是 1，从未演进
- 无跨库查询能力（比如查"某工具的所有调用成功率"需手动 JOIN 3 个 DB）
- 数据冗余：同一工具调用信息可能分布在 3 个不同库中

### 缺陷 4：成功率的两个来源互相矛盾

```
orchestrator._analyze_phase():
  
  # 来源1：self_monitor → ExperienceAnalyzer → learning_experiences.db
  if health['analysis']['success_rate'] < 0.6:
      issue('low_success_rate', ...)
  
  # 来源2：strategy_learner → ToolStrategyLearner → tools.db  
  if data['success_rate'] < threshold:
      issue('tool_low_performance', ...)
```

**问题**：
- `low_success_rate` 来自**经验成功率**（experiences 表）
- `tool_low_performance` 来自**工具调用成功率**（tool_usage_history 表）
- 两个成功率**定义不同、来源不同、阈值不同**
- 当 experiences 表为空时 → low_success_rate = 0%（即便工具实际都成功）
- 当 tool_usage_history 表为空时 → 全工具 success_rate = 0%（即便工具都成功）

### 缺陷 5：数据生产者/消费者之间的隐性依赖

```
生产者                        消费者
──────────────────────────    ──────────────────────────
_on_post_tool_call          → ExperienceAnalyzer
  → learning_experiences      → _perform_analysis()
                               → success_rate = 成功数/总数

无                            → ToolStrategyLearner
                               → _load_from_db()
                               → success_rate = AVG(success)
```

ToolStrategyLearner 是一个**消费者**但它依赖的数据**没有生产者**（v8.0.18之前）。这违反了数据架构的基本原则：**每条数据流都必须有明确的生产者和消费者**。

---

## 五、根因总结

| 层次 | 问题 |
|------|------|
| **概念层** | 两个概念 "experience" 和 "tool_usage" 语义重叠但未定义清楚边界：经验包含工具调用吗？工具调用是经验的子类吗？ |
| **设计层** | 数据生产者和消费者之间没有显式接口。ToolStrategyLearner 定义了读取路径但忘了设计写入路径 |
| **实现层** | 用假数据填补架构漏洞，掩盖了设计缺陷 41,000+ 个周期 |
| **运维层** | 11 个独立 DB，数据质量无法统一监控。空表、空库不被检测 |

**一句话根因**：系统从 V1 的"单一经验追踪"演化为 V3 的"经验+工具双追踪"时，**只扩展了读取端（两个分析器），没有设计统一的写入门面**。action_executor 的假数据充当了"临时的写入者"，掩盖了这个设计缺陷直到 V8.0.3。

---

## 六、修复建议（按优先级）

### P0：统一写入门面（架构修复）

在 hook 层和业务层之间新增 `UsageRecorder` / `EventSink`：

```python
class EventSink:
    """统一事件写入门面"""
    def record_tool_call(tool_name, success, duration_ms, context):
        with atomic_transaction():
            self.experience_repo.insert(...)   # learning_experiences.db
            self.usage_repo.insert(...)        # tools.db
            self.metrics_repo.update(...)      # tool_performance.db
```

Hook 只发事件，EventSink 负责分发到各存储。

### P1：DB 整合

将 11 个 DB 合并为 3-4 个：
- `evolution.db` — 周期审计 + 经验 + 工具使用（合并 evolution_audit + learning_experiences + tools）
- `memory.db` — 关联 + 记忆（合并 associations + agent_memory）
- `metrics.db` — 性能指标 + 工具性能（合并 tool_performance）

### P2：Schema 版本管理

每个 DB 使用统一的 `_schema_version` 并支持自动迁移。当前 3 个空表（evolution.db / evolution_state.db / agent_memory.db）可直接删除。

### P3：数据健康检查

`hae check` / `hae status` 应检测：
- 空表的 DB 数量
- 长期无数据流入的表（如 learning_experiences.db 只有 2 条）
- 数据源之间的差异（如 experiences 表 success_rate=100% 但 tool_usage_history 为空）

---

## 七、本次修复（v8.0.18）的定位

v8.0.18 在 `_on_post_tool_call` 中新增 sqlite3 直写 `tool_usage_history`，是**止血式修复**：

- ✅ 解决了"无数据流入 tool_usage_history"的问题
- ❌ 没有解决架构层面的"两套系统割裂"问题
- ❌ Hook 层越级操作，绕过了业务层
- ❌ 没有统一写入门面

**v8.0.18 让数据流通了，但架构债未还。** 建议在 v8.1 或 v9 中进行上述架构重构。

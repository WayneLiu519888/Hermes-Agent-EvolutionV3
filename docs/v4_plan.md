# V4 DFX 工程化方案

> 版本：v1.0 | 日期：2026-05-10 | 状态：待评审
> 触发：associations.db WAL 膨胀至 89GB
> 审视基础：docs/v4_dfx_architecture_review.md（8 维 DFX 全面审视）

---

## 背景

89GB WAL 事件暴露项目在数据库管理、错误恢复、性能控制三个层面存在系统性缺口。V4 不做新功能，聚焦 DFX 工程化补齐，目标是让系统从「能跑」变为「跑不坏」。

---

## 阶段总览

```
阶段              工时    目标              关键指标
────────────────────────────────────────────────────
A · 数据库底座    3天    消灭 WAL 炸弹      7个db全覆盖checkpoint
B · 韧性层        2天    异常路径不再丢数据   rollback覆盖率0→80%
C · 性能优化      3天    消除写入瓶颈        关联发现提速10x+
D · 质量工程      2天    测试防护网          services/覆盖率0→60%
E · 可观测性      1天    出问题早知道        WAL>100MB自动告警
F · 代码精简      3天    消灭维护债务        镜像文件0，重复函数0
────────────────────────────────────────────────────
总计             14天
```

---

## A · 数据库底座（3天）

**目标**：7 个 SQLite 数据库全部纳入 checkpoint + 统一连接管理。

### A1 — 统一 WAL checkpoint

> 根因：`auto_checkpoint_if_needed()` 已实现但**零调用**。除 associations.db 外 6 个 db 完全裸露。

| 数据库 | 写入频率 | 当前 checkpoint | 修复方式 |
|--------|----------|-----------------|----------|
| learning_experiences.db | 高（每次工具调用） | ❌ | observer.record_experience 后调 |
| tool_performance.db | 高（每次性能记录） | ❌ | analyzer.record_performance 后调 |
| retrieval_optimization.db | 中（每次反馈） | ❌ | optimizer.record_feedback 后调 |
| evolution_audit.db | 中（每次周期） | ❌ | auditor.record_cycle 后调 |
| audit.db | 中（每次事件） | ❌ | audit_logger.commit 后调 |
| collaboration_messages.db | 中（每条消息） | ❌ | message_bus.publish 后调 |
| associations.db | 高（关联发现） | ✅ 已修复 | hermes-plugin handler 中调用 |

阈值：WAL > 100MB 自动触发 PASSIVE checkpoint，仍 > 100MB 则 TRUNCATE。

### A2 — 消除 conn.close() 泛滥

> 根因：4 个模块 22 处通过 `get_evolution_db()` 获取连接后显式 close，导致连接缓存完全失效，每次 CRUD 重建连接。

| 文件 | close 次数 | 修复 |
|------|-----------|------|
| learning/observer.py | 6 | 移除所有 close，连接由 close_all_connections() 统一释放 |
| tools/tool_registry.py | 8 | 同上 |
| tools/tool_performance_analyzer.py | 3 | 同上 |
| memory/retrieval_optimizer.py | 7 | 同上 |

`close_all_connections()` 已实现在 db_utils，在 daemon.stop() 和 atexit 中调用。

### A3 — message_bus 连接规范化

> 当前：裸 `sqlite3.connect()` + 仅 WAL，无 busy_timeout，无 checkpoint。

修复：
```python
# 替换 message_bus.py:170 的裸 connect
self._conn = get_evolution_db("collaboration_messages.db")
```

### A4 — health.py 修复

> 两处 Bug：
> - L41: `get_data_dir(data_dir)` — 给无参函数传参，TypeError
> - L54: `sqlite3.connect(str(main_db))` — 裸 connect 绕过统一工厂

修复：移除无效参数 → `get_data_dir()`，裸 connect → `get_evolution_db()`。

### A5 — main.py SelfMonitor 签名修正

> L130: `SelfMonitor(db_path)` 应为 `SelfMonitor(observer, analyzer, strategy_learner)`。

### A6 — Daemon 定期 checkpoint

在 `hermes_daemon.py` 主循环每 N 轮调用：
```python
from evolution.db_utils import auto_checkpoint_if_needed

DB_LIST = ["associations.db", "tools.db", "learning_experiences.db",
           "tool_performance.db", "retrieval_optimization.db",
           "evolution_audit.db", "collaboration_messages.db"]

for db in DB_LIST:
    auto_checkpoint_if_needed(db, max_wal_mb=100)
```

---

## B · 韧性层（2天）

**目标**：异常路径不丢数据，写入冲突自动重试，进程退出优雅清理。

### B1 — 补 rollback

> 当前：41 处 commit vs **仅 1 处 rollback**（audit_logger.py）

| 模块 | 当前行为 | 修复 |
|------|----------|------|
| observer.py | 异常时 logger.error，不回滚 | try/except 加 rollback |
| memory/database.py | 同上 | 同上 |
| tools/tool_registry.py | 同上 | 同上 |
| closed_loop/evolution_auditor.py | 同上 | 同上 |

```python
# 修复后模式
try:
    conn.execute("INSERT ...")
    conn.commit()
except Exception:
    conn.rollback()
    raise
```

### B2 — 启用 retry_on_db_error

> `retry_on_db_error` 装饰器已实现（指数退避 2s→4s→8s）但**零使用**。

```python
from ..db_utils import retry_on_db_error

@retry_on_db_error(max_attempts=3)
def add_association(self, ...):
    ...

@retry_on_db_error(max_attempts=3)
def record_experience(self, ...):
    ...
```

优先覆盖：AssociationDatabase、LearningObserver、ToolPerformanceAnalyzer、RetrievalOptimizer。

### B3 — 优雅关闭

```python
# hermes_daemon.py
import atexit

def _graceful_shutdown():
    for db_name in DB_LIST:
        auto_checkpoint_if_needed(db_name, max_wal_mb=0)  # 强制清空
    close_all_connections()
    shutdown_logging()

atexit.register(_graceful_shutdown)
```

---

## C · 性能优化（3天）

**目标**：关联发现写入提速 10x+，消除内存泄漏。

### C1 — 批量写入

> AssociationDiscoverer 逐条 INSERT，O(N²) 调用。

```python
# 当前（每对 INSERT 一次 commit）
for source_id, target_id in pairs:
    self.db.add_association(source_id, target_id, ...)

# 修复（executemany 单事务批量写入）
data = [(source_id, target_id, method, score) for ...]
conn.executemany(
    "INSERT OR REPLACE INTO associations (...) VALUES (?,?,?,?)",
    data
)
conn.commit()
```

### C2 — 缓存 LRU 淘汰

> `_experiences_cache`（dict）无限增长，长运行 OOM。

```python
from collections import OrderedDict

class LearningObserver:
    def __init__(self, max_cache=1000):
        self._experiences_cache = OrderedDict()
        self._max_cache = max_cache

    def _cache_put(self, exp_id, experience):
        if len(self._experiences_cache) >= self._max_cache:
            self._experiences_cache.popitem(last=False)  # FIFO
        self._experiences_cache[exp_id] = experience
```

### C3 — N+1 查询消除（4 处）

| 位置 | 当前模式 | 修复 |
|------|----------|------|
| retrieval_optimizer.optimize_all | 循环内 SELECT count | 单条 GROUP BY + JOIN |
| association_discoverer.discover_all | 循环内查 memory_entry | JOIN memory_entries |
| tool_performance_analyzer 汇总 | 逐工具查 stats | GROUP BY tool_name |
| observer.query_experiences | 循环内查关联 | 单条 JOIN |

### C4 — 复合索引

```sql
-- associations.db
CREATE INDEX IF NOT EXISTS idx_assoc_source_type 
    ON associations(source_id, discovery_method);

-- learning_experiences.db  
CREATE INDEX IF NOT EXISTS idx_exp_timestamp_type
    ON experiences(timestamp, experience_type);

-- tool_performance.db
CREATE INDEX IF NOT EXISTS idx_perf_tool_time
    ON performance(tool_name, timestamp);
```

---

## D · 质量工程（2天）

**目标**：`src/services/` 覆盖率 0→60%，统一测试基础设施。

### D1 — conftest.py 统一夹具

> 当前：52 个 fixture 散落各文件，无 pytest 标记，unittest/pytest 混用。

```python
# tests/conftest.py
import pytest, tempfile
from evolution.db_utils import get_evolution_db

@pytest.fixture
def temp_db():
    """每个测试独立的内存数据库"""
    conn = get_evolution_db(":memory:")
    yield conn
    conn.close()

@pytest.fixture
def clean_data_dir(tmp_path):
    """隔离的数据目录"""
    import os
    os.environ["EVOLUTION_DATA_DIR"] = str(tmp_path)
    yield tmp_path
    del os.environ["EVOLUTION_DATA_DIR"]
```

### D2 — services/ 测试补底

> 13 个 .py 文件零测试，最大盲区 monitoring_service.py (781行)、test_service.py (779行)。

每文件最低覆盖：核心 public 方法 × 3 用例（正常/边界/异常）。

### D3 — 并发测试

```python
# tests/test_concurrency.py
def test_concurrent_writes(temp_db):
    """10 线程同时写入，验证无死锁无数据丢失"""
    ...

def test_wal_race_condition(temp_db):
    """读写并发，验证 WAL 模式隔离正确"""
    ...

def test_connection_pool_under_pressure(temp_db):
    """100 次并发获取连接，验证无泄漏"""
    ...
```

---

## E · 可观测性（1天）

**目标**：WAL 膨胀第一时间发现，不等到 89GB。

### E1 — 健康端点

```python
# health.py 新增
def get_health() -> dict:
    return {
        "status": "healthy",
        "databases": {
            db: {
                "size_mb": round(os.path.getsize(db_path)/1024/1024, 1),
                "wal_mb": round(os.path.getsize(db_path+"-wal")/1024/1024, 1) 
                        if os.path.exists(db_path+"-wal") else 0,
                "tables": db_get_stats(db).get("tables", [])
            }
            for db in DB_LIST
        },
        "connections": len(_connection_cache),
        "memory_mb": ...,
    }
```

### E2 — WAL 监控告警

```python
def check_wal_health() -> list[str]:
    warnings = []
    for db_name in DB_LIST:
        wal_path = str(_resolve_data_dir() / db_name) + "-wal"
        if os.path.exists(wal_path):
            mb = os.path.getsize(wal_path) / 1024 / 1024
            if mb > 500:
                warnings.append(f"CRITICAL: {db_name} WAL {mb:.0f}MB")
            elif mb > 100:
                warnings.append(f"WARNING: {db_name} WAL {mb:.0f}MB")
    return warnings
```

### E3 — feishu_notifications.log 轮转

```python
from logging.handlers import RotatingFileHandler
handler = RotatingFileHandler('feishu_notifications.log',
                              maxBytes=10*1024*1024, backupCount=3)
```

---

## F · 代码精简与结构优化（3天）

**目标**：消灭镜像维护债务，消除重复代码，模块职责单一化。

### F1 — 消除 hermes-plugin ↔ _plugin 镜像（1.5天）

> 核心问题：`hermes-plugin/__init__.py` (972行) 和 `src/evolution/_plugin/__init__.py` (936行) 几乎完全相同，仅新加的 `_checkpoint_associations_db()` 不同。每次修改需要手动同步，是最大的维护债务。

**修复方案**：

```
修复前:
  hermes-plugin/__init__.py  (972行)  ← 完全镜像
  src/evolution/_plugin/__init__.py  (936行)  ← 完全镜像

修复后:
  src/evolution/plugin_adapter.py  (~150行)  ← 新：提取公共逻辑
  ├── _get_data_dir()        → 从 db_utils 导入
  ├── _get_orchestrator()    → 移到此处
  ├── _get_association_discoverer() → 移到此处
  ├── _get_learning_observer() → 移到此处
  ├── tool_schema 定义       → 移到单独的 schemas.py
  └── handler 函数           → 移到单独的 handlers.py

  hermes-plugin/__init__.py  → 变为薄包装层 (~50行)
  src/evolution/_plugin/__init__.py → 删除（由 hermes-plugin 替代）
```

### F2 — 统一 _get_data_dir 实现（0.5天）

> 当前在 3 处重复实现，且逻辑有微妙差异。

```
修复前:
  db_utils.py:_resolve_data_dir()      # 考虑 EVOLUTION_DATA_DIR 环境变量
  _plugin/__init__.py:_get_data_dir()   # 完全相同逻辑，但返回 Path
  hermes-plugin/__init__.py:_get_data_dir()  # 同上

修复后:
  所有模块统一导入: from evolution.db_utils import get_data_dir
  删除其余两份实现
```

### F3 — 消除 WAL checkpoint 双份实现（0.5天）

> `db_utils.auto_checkpoint_if_needed()` 和 `hermes-plugin._checkpoint_associations_db()` 功能相同但实现不同。

```python
# 修复后：hermes-plugin 中直接调用通用版本
from evolution.db_utils import auto_checkpoint_if_needed

# 删除 _checkpoint_associations_db()
# handler 中改为:
auto_checkpoint_if_needed("associations.db", max_wal_mb=100)
```

### F4 — 模块职责拆分（0.5天）

> `_plugin/__init__.py` 承担三种职责：插件注册、工具 handler、单例管理 — 应拆分。

```
src/evolution/
├── plugin_adapter.py     ← 单例工厂（原 _get_* 函数）
├── schemas.py            ← 7 个工具 JSON schema 定义
├── handlers.py           ← 7 个 handler 函数
└── hermes_adapter.py     ← 插件注册入口（传给 Hermes 的 setup 函数）
```

### F5 — 死代码清理

| 位置 | 类型 | 处置 |
|------|------|------|
| `security/audit_logger.py:130` | `self._connection` 定义但从未使用 | 删除 |
| `main.py:129` | `evolution.db` 路径引用（可能已废弃） | 确认后删除 |
| `tools/tool_registry.py:106` | `:memory:` 数据库直接操作 | 评估是否可移除 |
| `AuditLogger._connection` | 实例属性始终为 None | 删除属性定义 |

### F6 — 大文件拆分建议（非本轮必做，标记为技术债务）

> 15 个模块超过 500 行，3 个超过 800 行。以下拆分留待后续迭代：

| 文件 | 行数 | 建议拆分 |
|------|------|----------|
| enhanced_tool_creator.py | 938 | 拆为 creator + validator + template |
| unified_entry.py | 861 | 拆为 entry + router + adapter |
| association_discoverer.py | 813 | 拆为 discoverer + batch_processor + score_calc |

---

## 风险与依赖

| 风险 | 影响 | 缓解 |
|------|------|------|
| A2 移除 close 后连接泄漏 | 连接数增长 | close_all_connections() + 连接数监控 |
| C1 批量写入改变事务语义 | 可能改变数据可见性 | 单事务内批量 commit，保持幂等 |
| F1 镜像消除引入 import 错误 | 插件加载失败 | 保留 hermes-plugin/__init__.py 作为转发层，零风险 |

---

## 验收标准

- [ ] 7 个 db 全部覆盖 WAL checkpoint，WAL 文件永不超过 500MB
- [ ] rollback 覆盖率 > 80%（当前 ~2%）
- [ ] retry_on_db_error 覆盖全部 5 个写入模块
- [ ] 关联发现写入耗时降低 10x+
- [ ] services/ 测试覆盖率 0→60%
- [ ] 并发测试：10 线程写无死锁
- [ ] hermes-plugin 和 _plugin 零重复代码
- [ ] _get_data_dir 全项目唯一定义在 db_utils
- [ ] 健康检查返回所有 db 的 WAL 大小
- [ ] HAE 工具通过 Hermes registry.register() 标准模式注册
- [ ] HAE 暴露为 MCP Server（`hermes mcp serve`），外部Agent可调用
- [ ] HAE 健康检查接入 `hermes doctor` / `hermes status` 框架

---

## G · 对接 Hermes 原生（2天） — 消灭自造轮子

> **核心认知修正**：Hermes 原生已具备 MCP 双向、工具注册系统、健康检查框架、Hook 机制。
> HAE 的目标不是再造一套，而是**扩展和增强 Hermes 原生能力**。
> 对比业界标准时发现：Hermes 本身就是业界标准的实现者——`registry.register()` = MCP 的 Schema-driven，
> `hermes mcp serve` = 完整的 MCP Server，`hermes doctor` = K8s 风格的诊断框架。

### G1 — 工具注册对齐 Hermes registry 标准（0.5天）

> Hermes 原生工具注册模式（见 `hermes-agent/tools/registry.py`）：
> ```python
> registry.register(
>     name="tool_name",
>     toolset="evolution",  # HAE 专属 toolset
>     schema={...},         # JSON Schema
>     handler=lambda args, **kw: ...,
>     check_fn=check_requirements,
>     requires_env=[...],
> )
> ```

**当前问题**：HAE 在 `hermes-plugin/__init__.py` 中用自建的 `TOOL_*_SCHEMA` + 独立 handler 函数注册，没有利用 Hermes 的 `registry.register()` 模式。

**修复**：改为标准注册模式，7 个工具统一接入 Hermes toolset 系统。
```python
# hermes-plugin/__init__.py — 注册到 Hermes registry
from tools.registry import registry

for tool_name, schema, handler in EVOLUTION_TOOLS:
    registry.register(
        name=tool_name,
        toolset="evolution",
        schema=schema,
        handler=handler,
        check_fn=lambda: True,  # evolution 工具始终可用
    )
```

收益：工具可通过 `hermes tools enable/disable evolution` 管理，符合 Hermes 工具标准。

### G2 — 暴露 HAE 为 MCP Server（0.5天）

> Hermes 原生：`hermes mcp serve` 启动 MCP Server，让外部 Agent 发现和调用 Hermes 工具。
> 当 HAE 的工具通过 `registry.register()` 注册后，会自动出现在 MCP Server 的工具列表中。

**当前状态**：Hermes 已内置 MCP Server 能力，HAE 什么都不需要做——工具注册到 Hermes registry 后，
`hermes mcp serve` 自带所有工具。

**HAE 需要做的**：提供一个 `hermes-evolution mcp` 子命令，封装 `hermes mcp serve`：
```bash
# 仅暴露 HAE 进化工具给外部 Agent
hermes-evolution mcp --toolsets evolution
```

收益：外部 Agent（Claude Code、Codex、Cline）可直接调用 `evolution_run_cycle` 等工具。

### G3 — 健康检查接入 hermes doctor 框架（0.5天）

> Hermes 原生：`hermes doctor [--fix]` 检查依赖和配置，`hermes status` 显示组件状态。

**修复**：HAE 的 WAL 监控和 DB 健康检查应该注册为 `hermes doctor` 的检查项，
而非另建独立的健康检查系统。

```python
# HAE 扩展 hermes doctor 检查
# hermes doctor 会扫描 tools/*.py 中的 check_fn
# 以及 ~/.hermes/plugins/ 中的 diagnostics

def evolution_health_check() -> dict:
    """WAL 文件大小 + DB 连通性检查"""
    warnings = []
    for db in DB_LIST:
        wal_path = ... + "-wal"
        if os.path.exists(wal_path):
            mb = os.path.getsize(wal_path) / 1024 / 1024
            if mb > 100:
                warnings.append(f"{db} WAL {mb:.0f}MB")
    return {
        "status": "warning" if warnings else "ok",
        "warnings": warnings,
    }
```

同时保留 `evolution_self_monitor` 作为运行时健康评分工具。

### G4 — 清理自造轮子（0.5天）

> 删除 HAE 中与 Hermes 原生重复的代码。

| 删除项 | 原因 | 替代 |
|--------|------|------|
| `src/evolution/schemas.py` | 工具 Schema 已在 registry 中 | 直接用 registry |
| 自建的 `_engine_instances` 单例字典 | Hermes 原生不需要这个模式 | 模块级 import 自动单例 |
| 独立的 `_checkpoint_associations_db()` | F3 已统一到 db_utils | `auto_checkpoint_if_needed()` |
| `health.py` 中的 `check_wal_health()` 重复 | G3 接入 doctor 框架后移除 | `hermes doctor` |

---

## 更新后的阶段总览

```
阶段              工时    目标              关键指标
────────────────────────────────────────────────────
A · 数据库底座    3天    消灭 WAL 炸弹      7个db全覆盖checkpoint
B · 韧性层        2天    异常路径不再丢数据   rollback覆盖率0→80%
C · 性能优化      3天    消除写入瓶颈        关联发现提速10x+
D · 质量工程      2天    测试防护网          services/覆盖率0→60%
E · 可观测性      1天    出问题早知道        WAL>100MB自动告警
F · 代码精简      3天    消灭维护债务        镜像文件0，重复函数0
G · 对接原生      2天    利用 Hermes 原生能力  MCP暴露、doctor集成、去重复
────────────────────────────────────────────────────
总计             16天
```

## 核心设计原则

```
HAE 的角色定位：
  ❌ 不是：自建框架（tool注册、MCP、健康检查、Hook管道）
  ✅ 是：Hermes 插件（扩展 Hermes 原生能力）

复用 Hermes 原生：
  - registry.register()    ← 工具注册标准
  - hermes mcp serve       ← MCP Server
  - hermes doctor/status   ← 健康检查
  - plugin.yaml            ← 插件清单
  - post_tool_call hook    ← 回调机制

HAE 独有（不重复）：
  - 6阶段进化编排           ← 核心竞争力
  - 关联发现引擎            ← 核心竞争力
  - 安全沙箱                ← 核心竞争力
  - WAL checkpoint 管理     ← 数据库可靠性增强
```

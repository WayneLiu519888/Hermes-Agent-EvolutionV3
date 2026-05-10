# V4 优化后 DFX 审视报告

> 审视日期：2026-05-11
> 审视范围：HermesAgentEvolution V4 优化后全量 .py 代码（50 源文件 + 30 测试文件）
> 审视维度：可靠性 / 性能 / 安全 / 可维护性 / 可测试性 / 可观测性 / 可用性 / 兼容性

---

## 总体评估

V4 优化完成了架构重构、DatabasePool、状态机、记忆分层、WAL checkpoint、retry/rollback、LRU/FTS5、健康检查、链路追踪等大量工作。但审视发现 **多项 V4 新增能力未能真正投入使用**，形成了"装饰性优化"——代码存在但未被生产路径调用。同时遗留代码中存在真实的安全和可靠性问题。

### 严重程度统计

| 等级 | 数量 | 说明 |
|------|------|------|
| 🔴 严重 | 6 | 影响安全/可靠性/数据一致性的问题 |
| 🟡 重要 | 11 | 影响性能/可维护性/可观测性的问题 |
| 🟢 建议 | 8 | 改进建议，非阻塞 |

---

## 一、可靠性（Reliability）

### 🔴 R1：DatabasePool 未实际投入使用 — 双连接缓存并存

**位置**：`db_pool.py` vs `db_utils.py`

**现状**：
- `db_pool.py` 仅被 3 个文件引用：`plugin_core.py`（shutdown）、`schema.py`（ensure_schema）、自身
- `db_utils.py` 的 `get_evolution_db()` 被 **50+ 处** 调用，覆盖所有业务模块
- 两套连接缓存在内存中并行运行：`db_pool._connections` 和 `db_utils._connection_cache`

**影响**：
- DatabasePool 的设计目标（禁止 close、统一 checkpoint、唯一入口）完全落空
- `db_pool.checkpoint_all()` 只能管理通过它创建的连接（目前为 0 个业务连接），业务模块的 WAL 文件无人管理
- `db_pool.close_all()` 在 shutdown 时无法关闭业务模块的连接（那些连接在 `db_utils._connection_cache` 中）

**修复建议**：将 `db_utils.get_evolution_db()` 内部调用改为走 `db_pool.connection()`，使 DatabasePool 成为唯一入口。或废弃 db_pool，在 db_utils 上补齐 checkpoint/closing 能力。

---

### 🔴 R2：conn.close() 泛滥问题未解决

**位置**：`learning/observer.py`、`tools/tool_registry.py`、`tools/tool_performance_analyzer.py`、`memory/retrieval_optimizer.py`、`security/audit_logger.py` 等

**现状**：33 处 `conn.close()` 调用遍布业务代码。DatabasePool 文档明确声明 "contextmanager 禁止 close"，但实际使用 db_utils 路径的模块仍在手动 close。

**典型问题**（`learning/observer.py` 第 98 行）：
```python
conn = get_evolution_db(self.db_path)
# ... 执行 DDL ...
conn.commit()
conn.close()  # ← 关闭了缓存中的连接！下一个调用者会拿到已关闭的连接
```

虽然 `get_evolution_db()` 中有 `SELECT 1` 健康检查，但 close-后重建会增加连接抖动，且 PRAGMA 配置需重新应用。

**修复建议**：所有模块移除手动 `conn.close()`，依赖池管理连接生命周期。

---

### 🔴 R3：裸 sqlite3.connect() 绕过连接池

**位置**：

| 文件 | 行号 | 说明 |
|------|------|------|
| `health.py` | 55 | `sqlite3.connect(str(main_db))` — 健康检查专用 |
| `tools/tool_registry.py` | 106 | `sqlite3.connect(":memory:")` — 内存库无需池化，但未配置 PRAGMA |
| `collaboration/message_bus.py` | 170 | `sqlite3.connect(self.db_path, check_same_thread=False)` — 完全绕过 |
| `security/audit_logger.py` | 532 | `sqlite3.connect(archive_path)` — 归档用 |

`message_bus.py` 的连接完全不经过任何池化层，没有 WAL 配置，没有 busy_timeout。

**修复建议**：`message_bus.py` 改为使用 `db_pool.connection()`；`health.py` 改为使用 `get_evolution_db()`；`audit_logger.py` 归档场景可保留但需配置 PRAGMA。

---

### 🟡 R4：WAL checkpoint 覆盖不足

**现状**：`auto_checkpoint_if_needed()` 仅在 `plugin_core.py` 的 `_handle_memory_discover()` 中被调用一次（针对 `associations.db`）。`hermes_daemon.py` 的定时 checkpoint（每 5 轮，约 25 分钟一次）使用 `db_pool.checkpoint_all()`，但如 R1 所述，db_pool 中没有业务连接。

**结论**：实际生效的 checkpoint 只有：
1. `plugin_core.py` — 关联发现后检查 `associations.db`
2. `hermes_daemon.py` — 空跑（db_pool 中无业务连接）
3. shutdown 时的 `db_pool.checkpoint_all(max_wal_mb=0)` — 同样空跑

所有其他数据库（`tools.db`、`learning_experiences.db`、`tool_performance.db`、`evolution_audit.db` 等）的 WAL 文件 **无定期 checkpoint 覆盖**。

---

### 🟡 R5：事务保护不统一

**现状**：
- `schema.py` 的 `ensure_schema()` — 有 `conn.commit()`（良好）
- `learning/observer.py` — 部分方法有 commit，部分无
- `tools/tool_registry.py` — 有 commit + rollback（良好）
- `memory/database.py` — 有 commit + rollback（良好）
- `closed_loop/evolution_auditor.py` — 有 commit（良好）

但仍有遗漏：`db_utils.py` 本身的 `wal_checkpoint()`、`vacuum_database()`、`db_get_stats()` 等函数使用 `get_evolution_db()` 获取连接后直接执行，没有显式 commit（PRAGMA 不需要，但 `VACUUM` 隐式提交）。

**风险等级**：中等。当前的 `get_evolution_db()` 连接默认 `isolation_level=''`（自动提交模式），所以单条 SQL 不会丢失。但多语句操作（如 observer 初始化：CREATE TABLE + CREATE INDEX + ALTER TABLE + COMMIT）如果在 COMMIT 前异常，部分 DDL 已自动提交、部分未提交。

---

### 🟡 R6：优雅关闭的信号覆盖不全

**现状**：
- `hermes_daemon.py` — 注册了 SIGINT/SIGTERM 处理器（良好）
- `plugin_core.py` — 仅注册了 `atexit`，**不处理 SIGTERM/SIGINT**
- 当 Hermes Agent 直接终止 Plugin 进程时，`atexit` 会触发但不保证完整执行（atexit 在信号杀死时不一定执行，取决于信号类型）

---

### 🟢 R7：atexit 重复注册

**位置**：`plugin_core.py:42` + `hermes_daemon.py:83`

两个模块各自注册了内容相同的 `atexit`：
```python
def _shutdown():
    from evolution.db_pool import db_pool
    db_pool.checkpoint_all(max_wal_mb=0)
    db_pool.close_all()
atexit.register(_shutdown)
```

当 hermes_daemon 导入 plugin_core 时，两个 `_shutdown` 都会注册。atexit 按 LIFO 执行，两次 `close_all()` 第二次是空操作，不会报错，但属冗余。

**修复建议**：在 `db_pool` 模块自身注册 atexit，由单例自己管理生命周期。其他模块移除重复注册。

---

## 二、性能（Performance）

### 🔴 P1：SQL N+1 查询模式

**位置**：`self_monitor.py` 第 162-170 行

```python
def _count_tools_from_db(self) -> int:
    conn = get_evolution_db("tools.db")
    count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
    return count
```

每次 `get_system_health_report()` 调用时，如果 `tool_summary` 为空（重启后），会新增一次独立 DB 连接查询。这在频繁健康检查场景下（每 30 秒）造成不必要的连接开销。

**其他潜在 N+1**：
- `tool_registry.py` 中多次单独的 `SELECT` 查询未使用 JOIN
- `observer.py` 中缓存的 `_experiences_cache` 是裸 OrderedDict，未与 DB 查询联动

---

### 🟡 P2：MemoryTier LRU 缓存未集成

**位置**：`memory/memory_tier.py`

MemoryTier 实现了 L1（内存 LRU）+ L2（SQLite）+ L3（归档）三层架构，但**没有任何生产代码导入或使用它**。`learning/observer.py` 有自己的 `OrderedDict` LRU 缓存（`_experiences_cache`），`memory/database.py` 有自己的直接 SQLite 操作。

MemoryTier 成为死代码。

---

### 🟡 P3：executemany 批量写入未推广

`executemany` 仅在 `memory/association_discoverer.py` 的 3 处使用。其他模块（如 observer 批量记录、tool_registry 批量注册）仍使用逐条 INSERT。

---

### 🟡 P4：DatabasePool 的连接复用效率

**现状**：DatabasePool 是进程级单例，所有线程共享同一连接（`check_same_thread=False`）。SQLite 在 WAL 模式下支持多线程并发读，但写操作串行化。当前设计在低并发下正常，但：
- `busy_timeout=30000`（30秒）对于热路径偏长——如果写锁被持有，读操作会等 30 秒
- 没有连接池大小上限——每个 db_name 只有一个连接，不构成"池"

**修复建议**：对高频写入场景考虑缩小 `busy_timeout` 到 5-10 秒，增加快速失败和重试机制。

---

### 🟢 P5：FTS5 全文搜索使用有限

`memory/database.py` 创建了 FTS5 虚拟表，但在其余代码中未发现 FTS5 的 MATCH 查询。FTS5 表维护有写入开销（content= 外部内容表，自动同步），但未被查询使用。

---

### 🟢 P6：日志轮转未实际配置

**位置**：`logging_config.py` + `hermes_daemon.py`

V4 计划中声称的 "日志轮转" 并未实现：
- `logging_config.py` 使用普通 `FileHandler`（无轮转）
- `hermes_daemon.py` 使用普通 `FileHandler('data/evolution/daemon.log')`（无轮转）
- 全项目 **无** `RotatingFileHandler` 或 `TimedRotatingFileHandler`

日志文件可能无限增长。

---

## 三、安全性（Security）

### 🔴 S1：InputValidator 完全未被使用

**位置**：`security/input_validator.py`

InputValidator 是 V4 新增模块，提供：
- `validate_tool_name()` — 防注入工具名
- `validate_db_path()` — 防路径穿越
- `validate_interval()` — 时间间隔校验
- `sanitize_error_message()` — 错误消息消毒

**但在整个生产代码中（50+ .py 文件），没有一处 import InputValidator。**

这意味着所有外部输入（`plugin_core.py` 的 params、`cli.py` 的命令行参数）都没有经过验证层。

**具体风险**：
- `plugin_core.py` 的 `_handle_create_tool()` 接受 `tool_name` 参数直接传给数据库——虽用参数化查询消除了 SQL 注入，但没有长度/字符校验
- `cli.py` 的 `cmd_check()` 接受 `fix`/`clean` 参数无校验

---

### 🔴 S2：硬编码密码

**位置**：`src/services/system/deployment/deployment_service.py` 第 165 行

```python
"password": "hermes123",
```

这是一个默认数据库连接配置中的硬编码密码。即使 V2 微服务层不是当前主用路径，此文件在代码库中存在，可能被误用。

---

### 🟡 S3：路径穿越风险

**位置**：`health.py` 第 52-55 行

```python
main_db = data / "associations.db"
if main_db.exists():
    import sqlite3
    conn = sqlite3.connect(str(main_db))
```

路径来自 `_resolve_data_dir()`，该函数接受 `EVOLUTION_DATA_DIR` 环境变量。如果环境变量被恶意设置为包含路径遍历的字符串（如 `/tmp/../../../etc/`），可能访问意外路径。`_resolve_data_dir()` 中有 `mkdir(parents=True, exist_ok=True)`，但没有路径规范化。

---

### 🟡 S4：SQL 注入已基本消除（参数化查询），但需审计

经扫描，所有 SQL 执行都使用 `?` 占位符的参数化查询，未发现字符串拼接 SQL 的注入风险。`db_utils.py` 的 `db_get_stats()` 中有 `f"SELECT COUNT(*) FROM [{table_name}]"` 使用 f-string 拼接表名，但 `table_name` 来自 `sqlite_master` 查询结果（可信源），风险较低。

---

### 🟢 S5：审计日志的敏感信息消毒不足

`security/audit_logger.py` 记录操作细节到 `audit.db`，但未对可能包含敏感信息的 `details` JSON 字段进行脱敏。如果工具调用参数包含 API key 等敏感信息，会被明文记录。

---

## 四、可维护性（Maintainability）

### 🔴 M1：双连接缓存架构造成混乱

`db_pool.py` 和 `db_utils.py` 维护两套独立的连接缓存，各有自己的：
- 连接创建逻辑（PRAGMA 配置重复）
- 健康检查逻辑（`SELECT 1`）
- 关闭逻辑

新增开发者无法判断应该使用哪个。目前事实标准是 `db_utils.py`，但 V4 文档推荐 `db_pool.py`。

---

### 🔴 M2：schema.py 的 ensure_schema() 未被任何业务模块使用

**现状**：`schema.py` 定义了 `tools.db`、`learning_experiences.db`、`agent_memory.db`、`evolution_state.db`、`audit.db` 的集中 DDL。但：
- `learning/observer.py` — 有自己独立的 `_init_database()`
- `memory/database.py` — 有自己独立的 `_init_database()`
- `closed_loop/evolution_auditor.py` — 有自己独立的 `_init_db()`
- `tools/tool_registry.py` — 有自己独立的 DDL
- `security/audit_logger.py` — 有自己独立的 DDL

**每个模块的 DDL 可能和 schema.py 不一致**。例如 `schema.py` 中 `experiences` 表有 `confidence` 列，而 `observer.py` 中同样有，但字段顺序和默认值可能不同。

**修复建议**：各模块的 `_init_database()` 改为调用 `ensure_schema()`，移除重复 DDL。

---

### 🟡 M3：plugin.yaml 文件不一致

| 文件 | 行数 | 内容 |
|------|------|------|
| `_plugin/plugin.yaml` | 3 | 仅 name + version + description |
| `hermes-plugin/plugin.yaml` | 15 | 完整：hermes_version、tools 列表、hooks 列表 |

如果部署使用的是 `_plugin/plugin.yaml`，Hermes Agent 无法获知该插件提供的工具和 Hook 列表。

---

### 🟡 M4：plugin_core.py 边界过大

`plugin_core.py` 共 938 行，包含：
- 8 个懒加载单例工厂
- 7 个工具的 schema + handler
- 1 个 Hook 回调
- register() 入口
- shutdown 逻辑

建议拆分为：
- `plugin_core.py` — register() 入口 + 工具注册逻辑（~100 行）
- `plugin_core/handlers.py` — 7 个 handler + 1 个 hook（~600 行）
- `plugin_core/engines.py` — 懒加载工厂（~200 行）

---

### 🟡 M5：logging_config.py 几乎未被使用

`logging_config.py` 提供了 `get_logger()`（统一 logger 命名空间 `hermes_evo.*`）和 `setup_logging()`（幂等初始化）。但实际代码中：

- 使用 `logging_config.get_logger(__name__)` 的模块：0 个（仅自身文档）
- 使用 `logging.getLogger(__name__)` 的模块：所有

`plugin_core.py` 使用 `logging.getLogger("hermes_evolution_plugin")`（不在 `hermes_evo` 命名空间下）。

**结果**：logger 层级混乱，无法通过 `LOGGER_HIERARCHY` 统一控制日志级别。

---

### 🟡 M6：import 路径在生产环境的不确定性

**`hermes_daemon.py`** 第 31-58 行有 `try/except ImportError` 回退逻辑：
```python
try:
    from evolution.learning.observer import LearningObserver
except ImportError:
    from src.evolution.learning.observer import LearningObserver
```

这能工作，但表明项目在包安装（`import evolution`）和源码运行（`import src.evolution`）之间没有统一。

**`plugin_core.py`** 直接使用 `from evolution.xxx import ...`，意味着它依赖 `evolution` 包已安装（或 `src/` 在 PYTHONPATH 中）。Hermes Agent 加载 Plugin 时，PYTHONPATH 是否能正确解析此路径需验证。

---

### 🟢 M7：FTS5 列名与 observer 表结构不匹配

`memory/database.py` 创建 FTS5 虚拟表：
```sql
CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_fts 
USING fts5(content, content='memory_entries', content_rowid='id')
```

但 `memory_entries` 表没有名为 `id` 的 INTEGER 列——它用的是 `id TEXT PRIMARY KEY`。FTS5 的 `content_rowid` 需要一个 rowid 或 INTEGER PRIMARY KEY。在 TEXT PRIMARY KEY 的表上，`content_rowid='id'` 会导致 FTS5 无法正确关联外部内容。

---

### 🟢 M8：文档与代码不同步

- `LOGGING.md` 可能未反映 `logging_config.py` 的存在
- `ARCHITECTURE.md` 可能未提及 DatabasePool / schema 版本化
- 许多 docstring 中的 "用法" 示例引用 `db_utils` 而非 `db_pool`

---

## 五、可测试性（Testability）

### 🔴 T1：V4 新增核心模块零测试覆盖

| 模块 | 测试文件 | 测试数 |
|------|---------|--------|
| `db_pool.py` (DatabasePool) | 无 | 0 |
| `schema.py` (ensure_schema) | 无 | 0 |
| `security/input_validator.py` | 无 | 0 |
| `memory/memory_tier.py` | 无 | 0 |

这四个模块是 V4 架构优化的核心交付物，但全部缺乏测试。

---

### 🟡 T2：conftest.py 夹具不足

当前仅 2 个 fixture（`temp_db`、`clean_data_dir`），缺少：
- `db_pool` fixture（初始化 DatabasePool + mock data_dir）
- `schema` fixture（在隔离环境执行 ensure_schema 后验证表结构）
- `mock_ctx` fixture（当前在 test_iteration6_integration.py 中定义，应提升到 conftest）

---

### 🟡 T3：DatabasePool 单例在测试中难以隔离

`DatabasePool` 使用 `__new__` 实现单例，`_instance` 是类变量。测试之间无法重置单例状态（除非手动 `DatabasePool._instance = None`），这可能导致测试交叉污染。

---

### 🟡 T4：没有集成测试覆盖 plugin_core → db_pool → db_utils 全链路

当前测试要么测试单一模块（如 `test_db_utils.py`），要么测试 plugin 注册（如 `test_iteration6_integration.py`），但没有从 `register(ctx)` → handler → lazy init → DB 操作的端到端测试。

---

### 🟢 T5：测试中有 591 个用例，但覆盖率分布不均

- `test_closed_loop.py` — 58 个
- `test_fusion.py` — 48 个
- `test_security.py` — 40 个
- 但 `test_db_utils.py` 仅 20 个，且未测试 `retry_on_db_error` 装饰器的行为

---

## 六、可观测性（Observability）

### 🟡 O1：数据库查询无延迟追踪

没有任何模块记录 SQL 查询的执行时间。`logging_config.py` 提供了 `log_db_query()` 函数但未被使用。在性能退化时无法定位慢查询。

---

### 🟡 O2：DatabasePool 统计信息未被导出

`db_pool.stats()` 返回池状态（连接数、路径），但此方法：
- 未被任何健康检查调用（`health.py` 使用 `db_utils` 而非 `db_pool`）
- 未被任何 metrics 系统采集
- 没有暴露为 CLI 命令

---

### 🟡 O3：链路追踪实现未覆盖所有 Phase

V4 计划的 "链路追踪" 无证据支持。扫描未发现任何 tracing span、trace ID 生成或 OpenTelemetry 集成。`hermes_daemon.py` 有 `_on_cycle_complete` 回调，但这只是事件通知而非链路追踪。

---

### 🟢 O4：健康检查中使用裸连接绕过监控

`health.py` 的 `health_check()` 使用 `sqlite3.connect()` 裸连接，该连接的活动不会被任何监控系统捕获。如果此连接因锁等待而 hang，健康检查本身会超时。

---

## 七、可用性（Availability）

### 🟡 A1：DatabasePool 单例在异常下的安全性

`DatabasePool.__new__` 使用了双重检查锁定（DCL），线程安全。但 `_resolve_path` 使用 `db_name.endswith(":memory:")` 判断内存库——如果传入 `":memory:"` 会被识别，但如果传入绝对路径如 `/tmp/test.db` 也会跳过解析（因为 `/tmp/...` 不以 `"/"` 开头？实际上 `startswith("/")` 被检查了）。

问题：第 51 行 `db_name.startswith("/")`，而第 121 行的 `db_utils._resolve_data_dir()` 中没有类似检查。两者行为不一致。

---

### 🟡 A2：状态机中断恢复未被测试

`closed_loop/orchestrator.py` 实现了完整的 Monitor → Analyze → Plan → Execute → Verify → Feedback 流程。如果在 Execute 阶段进程崩溃，restart 后是否会从中间状态恢复？当前没有持久化的中间状态快照机制（`evolution_state.db` 有 `state_snapshots` 表但未见使用）。

---

### 🟢 A3：hermes_daemon 的 --once 模式在异常后无回滚

`hermes_daemon.py` 的 `run_once()` 直接调用 `self.orchestrator.run_full_cycle()`。如果 orchestrator 部分执行（例如 Execute 阶段部分写入后崩溃），没有清理机制。

---

## 八、兼容性（Compatibility）

### 🟡 C1：_plugin/plugin.yaml 不完整

`_plugin/plugin.yaml` 只有 3 行，不包含 `hermes_version`、`tools`、`hooks` 列表。如果 Hermes Agent 依赖这些字段进行插件发现，此插件可能无法被正确识别。

`hermes-plugin/plugin.yaml` 是完整的（15 行），说明存在两个部署目标但配置不一致。

---

### 🟡 C2：V2 微服务层是否仍可用

`src/services/` 包含完整的事件总线、服务管理、学习服务、工具服务、部署服务等。这些模块未被 V4 重构修改，理论上仍可用。但：
- 与 V1 模块共享数据库（如 `associations.db`），schema 变更可能影响 V2 服务
- `deployment_service.py` 的硬编码密码问题影响 V2 路径的安全性

---

### 🟢 C3：register(ctx) 与 Hermes API 兼容性

`plugin_core.py` 的 `register(ctx)` 调用 `ctx.register_tool(name=..., toolset="hermes-evolution", schema=..., handler=...)` 和 `ctx.register_hook(...)`。根据 `test_iteration6_integration.py` 第 402 行的注释，Hermes Agent API 的 `register_tool` 签名已升级为 `(name, toolset, schema, handler, ...)`。当前代码匹配此签名，兼容性良好。

---

## 九、专项检查

### 9.1 hermex_doctor_check 函数

**结论：不存在。**

在整个代码库中（50 源文件 + 30 测试文件），未找到 `hermex_doctor_check` 函数定义或调用。`hermes doctor` 命令如果依赖此函数，将无法正常工作。

最接近的功能是：
- `health.py` 的 `health_check()` / `comprehensive_health_check()`
- `cli.py` 的 `cmd_check()` — 环境自检

如果 `hermes doctor` 需要调用进化系统的健康检查，需要明确入口点。

---

### 9.2 atexit 注册冲突

**数量**：2 个（`plugin_core.py:42` + `hermes_daemon.py:83`）

**内容**：两者完全相同（checkpoint_all + close_all）

**冲突风险**：低。atexit 按 LIFO 执行，第二次 close_all() 是空操作。但重复注册表明缺乏统一的关闭管理。

**修复建议**：在 `db_pool.py` 单例的 `__new__` 中注册 atexit（仅一次），其他模块移除。

---

### 9.3 db_pool.py 与 db_utils.py 功能重叠

| 功能 | db_pool.py | db_utils.py |
|------|-----------|-------------|
| 连接缓存 | `_connections: dict` | `_connection_cache: dict` |
| 路径解析 | `_resolve_path()` → `_resolve_data_dir()` | `_resolve_data_dir()` |
| 健康检查 | `SELECT 1` | `SELECT 1` |
| PRAGMA 配置 | WAL + busy_timeout + synchronous + cache_size + foreign_keys | 完全相同 |
| WAL checkpoint | `checkpoint_all()` | `wal_checkpoint()` + `auto_checkpoint_if_needed()` |
| 连接关闭 | `close_all()` | `close_all_connections()` |
| 连接获取 | `connection()` contextmanager | `get_evolution_db()` 函数 |

**结论**：高度重叠（约 80%）。应合并为单一模块。建议保留 `db_pool.py` 的设计，将 `db_utils.py` 的便捷函数（`retry_on_db_error`、`auto_checkpoint_if_needed`、`vacuum_database`、`db_get_stats`）迁移到 `db_pool.py` 或保留在 `db_utils.py` 中作为 `db_pool` 的上层封装。

---

### 9.4 日志配置重复

**logging_config.py** 提供：
- `setup_logging(level, log_file, console)` — 幂等初始化
- `get_logger(name)` — 命名空间统一

**hermes_daemon.py** 忽略 logging_config，直接使用：
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('data/evolution/daemon.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
```

**plugin_core.py** 也忽略 logging_config，手动添加 StreamHandler。

**结论**：`logging_config.py` 的 `setup_logging()` 存在但从未被调用。需要决定是推广使用还是移除。

---

### 9.5 plugin_core.py import 路径生产可用性

`plugin_core.py` 使用的 import 路径：
```python
from evolution.db_utils import get_data_dir, auto_checkpoint_if_needed
from evolution.db_pool import db_pool
from evolution.tools import ToolRegistry
from evolution.learning import LearningObserver, ExperienceAnalyzer, ...
from evolution.closed_loop import ClosedLoopOrchestrator, ...
```

如果 `hermes-plugin/__init__.py` 被 Hermes Agent 加载，且其 PYTHONPATH 包含 `src/` 或项目根目录，这些 import 可以正常工作。但需确认 Hermes Agent 的插件加载机制是否会将插件目录的父目录加入 `sys.path`。

`hermes_daemon.py` 第 29 行手动添加了路径：`sys.path.insert(0, str(Path(__file__).resolve().parent))`。Plugin 加载时是否有类似机制取决于 Hermes Agent 的实现。

---

## 十、改进优先级路线图

### 第一阶段：安全与可靠性修复（高优先级）

1. **消除硬编码密码**（S2）— 替换为环境变量
2. **集成 InputValidator**（S1）— 在 `plugin_core.py` 所有 handler 入口处添加输入验证
3. **统一连接管理**（R1）— 将 `db_utils.get_evolution_db()` 改为使用 `db_pool.connection()`
4. **移除所有 conn.close()**（R2）— 各业务模块
5. **消除裸 sqlite3.connect()**（R3）— message_bus、health、audit_logger

### 第二阶段：性能与可观测性（中优先级）

6. **WAL checkpoint 全覆盖**（R4）— 所有数据库的定期 checkpoint
7. **MemoryTier 集成或移除**（P2）— 决定是投入使用还是删除死代码
8. **日志轮转**（P6）— 添加 RotatingFileHandler
9. **数据库查询延迟追踪**（O1）— 在 retry_on_db_error 中添加计时
10. **FTS5 修复**（M7）— 确保 FTS5 content_rowid 正确

### 第三阶段：架构债务清理（中优先级）

11. **合并 db_pool + db_utils**（M1）— 单一连接管理模块
12. **推广 schema.py**（M2）— 各模块使用 ensure_schema()
13. **统一 logging_config.py**（M5）— 全项目统一 logger 命名空间
14. **一致化 plugin.yaml**（M3）— 补全 _plugin/plugin.yaml
15. **拆分 plugin_core.py**（M4）

### 第四阶段：测试覆盖（持续）

16. **新增模块测试**（T1）— db_pool、schema、input_validator、memory_tier
17. **集成测试**（T4）— plugin_core 全链路
18. **conftest 扩展**（T2）— 补充 db_pool/schema/mock_ctx fixture

---

## 附录：扫描文件清单

### 新增/修改的文件（V4 相关）
- `src/evolution/db_pool.py` — 144 行
- `src/evolution/schema.py` — 173 行
- `src/evolution/security/input_validator.py` — 211 行
- `src/evolution/memory/memory_tier.py` — 46 行
- `src/evolution/plugin_core.py` — 938 行（镜像文件合并后）

### 遗留文件（全量审查）
- `src/evolution/db_utils.py` — 293 行
- `src/evolution/health.py` — 202 行
- `src/evolution/logging_config.py` — 149 行
- `src/evolution/cli.py` — 481 行
- `src/evolution/self_monitor.py` — 207 行
- `src/evolution/memory/database.py` — 458 行
- `src/evolution/learning/observer.py` — 505 行
- `src/evolution/tools/tool_registry.py` — 527 行
- `src/evolution/closed_loop/orchestrator.py` — 771 行
- `src/evolution/closed_loop/evolution_auditor.py` — 446 行
- `src/evolution/security/audit_logger.py` — 653 行
- `src/services/system/deployment/deployment_service.py` — 874 行
- `hermes_daemon.py` — 576 行
- `tests/conftest.py` — 21 行
- 其余 ~30 个源文件 + ~30 个测试文件

---

*报告结束*

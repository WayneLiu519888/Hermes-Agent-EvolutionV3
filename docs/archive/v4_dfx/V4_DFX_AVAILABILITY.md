# DFX专项审视：可用性

> 项目: HermesAgentEvolution  
> 审视日期: 2026-05-10  
> 审视范围: 数据库连接管理 / 单例生命周期 / 错误恢复 / 启动检查 / 外部依赖健康检查 / 进程守护 / 热加载与缓存一致性  

---

## 1. 现状评估

### 1.1 总体评价：C+（基本可用，但存在多处单点隐患）

| 审视维度 | 评分 | 状态 |
|---------|------|------|
| 数据库连接管理 | C | 连接池已建立但被4个模块绕过/破坏 |
| 单例生命周期 | B | 懒加载模式可用，但 `_get_orchestrator()` 存在运行时 bug |
| 错误恢复机制 | D | `retry_on_db_error` 零使用；无网络调用重试 |
| 启动检查 | D | 无预检流程，组件初始化失败后直接退出 |
| 外部依赖健康检查 | D | 飞书连接测试方法存在但从未调用 |
| 进程守护策略 | C+ | 基本守护循环存在，但无自动重启，daemon线程为精灵线程 |
| 热加载与缓存一致性 | D | 缓存无淘汰策略，无热加载机制 |

### 1.2 已修复项确认

- `db_utils.py` 的 `retry_on_db_error` 装饰器已实现（指数退避 2s→4s→8s）
- `db_utils.py` 的 `wal_checkpoint()` / `auto_checkpoint_if_needed()` 已实现
- `hermes-plugin/__init__.py` 的 `_checkpoint_associations_db()` 已实现（仅覆盖 associations.db）
- `db_utils.py` 连接缓存线程安全（`_cache_lock`）

---

## 2. 风险清单（带代码定位）

### 风险 1：【高危】连接缓存被大范围绕过/破坏

**严重性**: 高  
**影响**: 每个数据库操作都创建新连接，彻底抵消 `db_utils.get_evolution_db()` 的连接池收益。高并发下可能触发 SQLite `too many open files`。

**受影响模块及代码位置**:

| 模块 | 文件 | 行号 | 问题描述 |
|------|------|------|---------|
| LearningObserver | `src/evolution/learning/observer.py` | 78, 133, 160, 275, 338, 420 | 每个方法尾部 `conn.close()`，共6处 |
| ToolRegistry | `src/evolution/tools/tool_registry.py` | 152, 234, 259, 330, 389, 414, 454, 496 | 每个方法尾部 `conn.close()`，共8处 |
| ToolPerformanceAnalyzer | `src/evolution/tools/tool_performance_analyzer.py` | 122, 155, 454 | init + record + query 后 `conn.close()`，共3处 |
| SecurityAuditLogger | `src/evolution/security/audit_logger.py` | 142-153 | `_get_connection()` 上下文管理器 finally 中 `conn.close()`，每调用必关闭 |
| HealthChecker | `src/evolution/health.py` | 54-64 | 绕过 `get_evolution_db()`，直接 `sqlite3.connect()` + `conn.close()` |
| Plugin checkpoint | `hermes-plugin/__init__.py` | 208-215 | 绕过 `get_evolution_db()`，直接 `sqlite3.connect()` + `conn.close()` |

**总计**: 21 处 `conn.close()` 调用破坏了连接缓存。`db_utils.py` 内置的 `SELECT 1` 健康检查和失效重连机制完全被架空。

**根因**: 开发者未理解 `get_evolution_db()` 返回的是缓存连接，不应 close。

---

### 风险 2：【高危】`retry_on_db_error` 装饰器零使用

**严重性**: 高  
**影响**: `db_utils.py:207-251` 精心实现的指数退避重试装饰器（`max_attempts=3, backoff=2s→4s→8s`）在整个源代码中零引用。任何 `database is locked` 错误都会直接抛出给调用方，无自动恢复。

```python
# db_utils.py:207 — 已实现但零调用的装饰器
def retry_on_db_error(max_attempts=3, backoff_base=2.0, max_backoff=30.0):
```

**grep 结果**: 仅在 `tests/test_db_utils.py` 中被测试使用。所有生产代码（observer.py, tool_registry.py, tool_performance_analyzer.py, evolution_auditor.py, audit_logger.py, database.py, retrieval_optimizer.py）均未使用。

---

### 风险 3：【中危】`_get_orchestrator()` 运行时 TypeError

**严重性**: 中  
**代码位置**: `hermes-plugin/__init__.py:93,105`

```python
# 第 93 行
db_base = str(_get_data_dir())          # 类型: str (如 "/home/user/.hermes/data/evolution")

# 第 98 行
observer = LearningObserver(db_path=os.path.join(db_base, "learning_experiences.db"))  # OK: str join

# 第 105 行 — BUG!
strategy_learner = ToolStrategyLearner(db_path=str(db_base / "tools.db"))  # TypeError!
#                                                      ^^^^^^^^^^^^^^^
# db_base 是 str，str 不支持 / 运算符
```

**影响**: 当 agent 调用 `evolution_run_cycle` 触发 `_get_orchestrator()` 懒初始化时，直接抛出 `TypeError: unsupported operand type(s) for /: 'str' and 'str'`，整个编排器初始化失败。

---

### 风险 4：【中危】缓存无限增长，无淘汰策略

**严重性**: 中  
**代码位置**: `src/evolution/learning/observer.py:40-41, 136, 283`

```python
# 第 40-41 行
self._experiences_cache: Dict[str, Experience] = {}    # 只增不减！
self._statistics_cache: Optional[Dict[str, Any]] = None  # 写入时失效

# 第 136 行 — 每次 record_experience 追加到缓存
self._experiences_cache[experience.id] = experience

# 第 283 行 — 每次 query_experiences 追加到缓存
self._experiences_cache[experience.id] = experience
```

**影响**: 长时间运行的守护进程（数天至数周），`_experiences_cache` 可能积累数万条 Experience 对象，导致内存泄漏。只有 `_statistics_cache` 会在写入时正确失效。

---

### 风险 5：【中危】WAL checkpoint 仅覆盖 1 个数据库

**严重性**: 中  
**代码位置**: `hermes-plugin/__init__.py:188-218` (`_checkpoint_associations_db`)

**已覆盖**: `associations.db` (高写入量)  
**未覆盖的高写入数据库**:
- `learning_experiences.db` — `observer.py` 每次工具调用都会写入学习经验
- `tool_performance.db` — `tool_performance_analyzer.py:124-155` 每次工具执行写入性能记录
- `evolution_audit.db` — `evolution_auditor.py:114-214` 每个进化周期写入完整审计
- `audit.db` — `audit_logger.py` 安全审计，高频写入
- `collaboration_messages.db` — 消息总线写入

`db_utils.py:173-188` 提供了 `auto_checkpoint_if_needed()` 通用方法，但无人调用。

---

### 风险 6：【中危】飞书连接健康检查未集成到启动流程

**严重性**: 中  
**代码位置**: 
- `src/utils/feishu_notifier.py:318-343` (`test_connection()`)
- `hermes_daemon.py:109-114` (feishu 初始化)
- `hermes-plugin/__init__.py` (无 feishu 检查)

```python
# feishu_notifier.py:318 — test_connection 已实现但从未被调用
def test_connection(self) -> Dict[str, Any]:
```

**影响**: 飞书 webhook URL 无效或 OpenAPI token 获取失败，系统静默降级到 simulated 模式（日志文件记录），运维无感知。

---

### 风险 7：【中危】进程守护缺少自动重启机制

**严重性**: 中  
**代码位置**: `src/evolution/closed_loop/daemon.py:126-127, 185-219`

```python
# daemon.py:127
daemon=True   # 精灵线程：主进程退出即被杀

# daemon.py:210-214
if self.consecutive_failures >= self.max_consecutive_failures:
    logger.critical(f"连续失败 {self.consecutive_failures} 次，停止进化循环")
    self._state = LoopState.ERROR
    break   # 退出循环，线程结束，无重启！
```

**影响**: 
- 连续 5 次失败后进化线程永久停止，无自动重试或重启
- `daemon=True` 精灵线程在主进程退出时没有优雅清理机会
- `hermes_daemon.py:537` 组件初始化失败直接 `sys.exit(1)`，无重试

---

### 风险 8：【中危】启动无预检（pre-flight check）

**严重性**: 中  
**代码位置**: `hermes_daemon.py:123-293` (`initialize_components`)

当前初始化流程:
1. 逐个创建组件，`try/except` 捕获异常
2. 部分组件失败设为 `None`（pattern_recognizer, tool_registry, tool_engine）  
3. 关键组件失败标记 `success=False`
4. 最终若 `success=False`：`sys.exit(1)`（第 537 行）

**缺失的预检项**:
- 磁盘空间检查（数据目录所在分区）
- 数据库文件可读写性检查
- `EVOLUTION_DATA_DIR` / `HERMES_HOME` 环境变量校验
- Python 依赖完整性（所有 import 在初始化时才验证）
- 飞书 webhook 可达性

---

### 风险 9：【低危】`health.py` 运行时参数错误

**严重性**: 低  
**代码位置**: `src/evolution/health.py:41`

```python
# health.py:41
data = get_data_dir(data_dir)   # get_data_dir() 不接受参数！
```

`db_utils.get_data_dir()` 是一个无参函数（第48-50行），调用时传入 `data_dir` 会导致 `TypeError`。

此外 `health.py:54` 绕过 `get_evolution_db()` 直接使用 `sqlite3.connect()`。

---

### 风险 10：【低危】`memory/database.py` 持有长期连接但有自己的 `close()`

**严重性**: 低  
**代码位置**: `src/evolution/memory/database.py:29, 410-420`

```python
# database.py:29 — 使用 get_evolution_db 获取缓存连接
self.connection = get_evolution_db(self.db_path)

# database.py:410-414 — close() 关闭的是缓存中的连接
def close(self):
    if self.connection:
        self.connection.close()   # 关闭了缓存连接！
        self.connection = None
```

**影响**: `AssociationDatabase.close()` 关闭的是 `db_utils._connection_cache` 中的共享连接，导致其他通过 `get_evolution_db("associations.db")` 获取连接的模块收到已关闭的 handle。虽然 `db_utils.get_evolution_db()` 有 `SELECT 1` 健康检查会重新创建，但存在并发窗口。

---

## 3. 修复建议

### 3.1 修复优先级矩阵

| 优先级 | 风险编号 | 修复难度 | 预计工时 |
|--------|---------|---------|---------|
| P0 | 风险1 (连接关闭) | 简单 | 2h |
| P0 | 风险2 (retry零使用) | 中等 | 4h |
| P1 | 风险3 (TypeError bug) | 简单 | 10min |
| P1 | 风险4 (缓存淘汰) | 中等 | 2h |
| P1 | 风险5 (WAL覆盖) | 简单 | 1h |
| P2 | 风险7 (自动重启) | 中等 | 3h |
| P2 | 风险8 (启动预检) | 中等 | 3h |
| P2 | 风险6 (飞书检查) | 简单 | 30min |
| P3 | 风险9/10 | 简单 | 1h |

### 3.2 详细修复方案

#### 修复 1: 移除所有不该出现的 `conn.close()`

**原则**: 使用 `get_evolution_db()` 获取的连接**不应关闭**，连接生命周期由 `close_all_connections()` 统一管理。

**修改清单**:

1. `src/evolution/learning/observer.py` — 删除 L78, 133, 160, 275, 338, 420 的 `conn.close()`
2. `src/evolution/tools/tool_registry.py` — 删除 L152, 234, 259, 330, 389, 414, 454, 496 的 `conn.close()`
3. `src/evolution/tools/tool_performance_analyzer.py` — 删除 L122, 155, 454 的 `conn.close()`
4. `src/evolution/security/audit_logger.py` — 修改 `_get_connection()` 上下文管理器（L142-153）：移除 finally 中的 `conn.close()`，改为仅做 `rollback` on exception
5. `src/evolution/health.py` — L54 改用 `get_evolution_db("associations.db")` 替代裸 `sqlite3.connect()`，删除 L64 的 `conn.close()`
6. `hermes-plugin/__init__.py` — `_checkpoint_associations_db()` L208-215 改用 `get_evolution_db()` 获取连接，删除 `conn.close()`

#### 修复 2: 在关键写入路径添加 `@retry_on_db_error`

在以下方法上添加装饰器:
- `LearningObserver.record_experience()` (observer.py:87)
- `LearningObserver._init_database()` (observer.py:43)
- `ToolRegistry.register()` (tool_registry.py:154)
- `ToolPerformanceAnalyzer.record_performance()` (tool_performance_analyzer.py:124)
- `EvolutionAuditor.record_cycle()` (evolution_auditor.py:114)
- `SecurityAuditLogger.log()` (audit_logger.py 对应方法)
- `AssociationDatabase.add_memory_entry()` (database.py:91)
- `AssociationDatabase.add_association()` (database.py:130)

```python
from ..db_utils import retry_on_db_error

@retry_on_db_error(max_attempts=3)
def record_experience(self, experience: Experience) -> str:
    ...
```

#### 修复 3: 修复 `_get_orchestrator()` 的 TypeError

`hermes-plugin/__init__.py:105`:
```python
# 修改前
strategy_learner = ToolStrategyLearner(db_path=str(db_base / "tools.db"))

# 修改后
strategy_learner = ToolStrategyLearner(db_path=os.path.join(db_base, "tools.db"))
```

#### 修复 4: 添加缓存淘汰策略

`src/evolution/learning/observer.py`:

```python
# 添加配置
MAX_CACHE_SIZE = 10000
CACHE_TTL_SECONDS = 3600

def _evict_cache(self):
    """淘汰过期或超出大小的缓存条目"""
    if len(self._experiences_cache) > self.MAX_CACHE_SIZE:
        # LRU: 移除最早添加的一半
        keys = list(self._experiences_cache.keys())[:self.MAX_CACHE_SIZE // 2]
        for k in keys:
            del self._experiences_cache[k]
```

在 `record_experience()` 和 `query_experiences()` 追加缓存后调用 `_evict_cache()`。

#### 修复 5: 扩展 WAL checkpoint 覆盖

在以下位置添加 checkpoint 调用:
- `observer.py:record_experience()` 尾部 → `auto_checkpoint_if_needed("learning_experiences.db")`
- `tool_performance_analyzer.py:record_performance()` 尾部 → `auto_checkpoint_if_needed("tool_performance.db")`
- `evolution_auditor.py:record_cycle()` 尾部 → `auto_checkpoint_if_needed("evolution_audit.db")`
- `audit_logger.py` 日志写入后 → `auto_checkpoint_if_needed("audit.db")`

#### 修复 6: 启动时集成飞书健康检查

`hermes_daemon.py:109-114`:
```python
if FEISHU_AVAILABLE:
    try:
        self.feishu_notifier = get_notifier()
        result = self.feishu_notifier.test_connection()
        if result.get("test_result") == "失败":
            logger.warning("飞书连接测试失败: %s", result)
    except Exception:
        logger.warning("飞书通知器初始化失败，将使用日志通知")
        self.feishu_notifier = None
```

#### 修复 7: 添加守护进程自动重启

`src/evolution/closed_loop/daemon.py:_run_loop()`:

```python
# 在 while 循环中添加重启计数器和冷却时间
MAX_RESTARTS = 3
RESTART_COOLDOWN = 300  # 5分钟冷却期

# 当 break 退出循环时，外层添加重启逻辑
```

在 `hermes_daemon.py` 的 `start()` 方法中添加看门狗：
```python
def start(self):
    while self._running:
        try:
            if not self.daemon or not self.daemon.is_running:
                self.daemon.start()
            self.daemon._thread.join(timeout=60)
            if self.daemon.state == LoopState.ERROR:
                logger.warning("进化线程异常退出，30s 后重启...")
                time.sleep(30)
        except Exception:
            ...
```

#### 修复 8: 添加启动预检

新增 `src/evolution/preflight.py`:
```python
def preflight_check(data_dir: Path) -> dict:
    """启动前预检，返回 {passed: bool, checks: [...], warnings: [...]}"""
    checks = []
    
    # 1. 磁盘空间（至少 100MB）
    # 2. 数据库文件可读写
    # 3. 环境变量
    # 4. 关键 import
    # 5. 飞书连接（可选）
    
    return {"passed": all(c["status"] == "ok" for c in checks), ...}
```

#### 修复 9: 修复 `health.py` 的 Bug

```python
# L41: 修改前
data = get_data_dir(data_dir)

# L41: 修改后
from evolution.db_utils import _resolve_data_dir
data = data_dir if data_dir else _resolve_data_dir()
```

L54: 改用 `get_evolution_db("associations.db")`.

---

## 4. 测试覆盖盲区

### 4.1 现有测试覆盖

| 测试文件 | 覆盖内容 | 可用性相关 |
|---------|---------|-----------|
| `tests/test_db_utils.py` | `retry_on_db_error`, `get_evolution_db`, checkpoint | ✅ 部分覆盖 |
| `tests/test_health.py` | `health_check`, `print_health` | ✅ 部分覆盖 |
| `tests/test_feishu_notifier.py` | 飞书通知基础功能 | ⚠️ 未测试连接失败 fallback |
| `tests/test_collaboration.py` | 消息总线 close() | ❌ 测试中使用 close 但未验证连接缓存是否完好 |

### 4.2 缺失测试场景

| 编号 | 测试场景 | 优先级 |
|------|---------|-------|
| T1 | **连接缓存压力测试**: 1000次并行 `get_evolution_db()` + 写操作，验证连接不泄漏 | P0 |
| T2 | **retry_on_db_error 集成测试**: 模拟 `database is locked`，验证装饰器实际生效 | P0 |
| T3 | **WAL 膨胀测试**: 持续写入 10000 条记录，验证 auto_checkpoint 触发并清空 WAL | P1 |
| T4 | **缓存淘汰测试**: 写入超过 MAX_CACHE_SIZE 条经验，验证内存不增长 | P1 |
| T5 | **单例生命周期测试**: 多次 `register(ctx)` 调用后验证无重复连接 | P1 |
| T6 | **守护进程重启测试**: 模拟连续循环失败，验证自动重启 | P2 |
| T7 | **飞书 fallback 测试**: 使用无效 webhook URL，验证降级到 simulated 模式 | P2 |
| T8 | **启动预检测试**: 在磁盘满、DB损坏、环境变量缺失等场景下验证预检返回正确状态 | P2 |
| T9 | **健康检查参数错误测试**: 验证 `health_check(data_dir=Path(...))` 不抛 TypeError | P3 |
| T10 | **并发连接关闭测试**: 线程A调用 `observer.close()` 同时线程B通过 `get_evolution_db()` 获取连接 | P3 |

### 4.3 建议的新测试文件

建议创建:
- `tests/test_availability.py` — 整合 T1-T10 的可用性专项测试
- `tests/test_daemon_lifecycle.py` — 守护进程启停、重启、错误恢复测试

---

## 附录 A: 连接关闭调用汇总

```
src/evolution/learning/observer.py:
  L78   conn.close()  ← _init_database
  L133  conn.close()  ← record_experience
  L160  conn.close()  ← get_experience
  L275  conn.close()  ← query_experiences
  L338  conn.close()  ← get_statistics
  L420  conn.close()  ← analyze_learning_patterns

src/evolution/tools/tool_registry.py:
  L152  conn.close()  ← _init_database
  L234  conn.close()  ← register
  L259  conn.close()  ← get
  L330  conn.close()  ← list_all
  L389  conn.close()  ← update_usage_stats
  L414  conn.close()  ← delete
  L454  conn.close()  ← get_statistics
  L496  conn.close()  ← search

src/evolution/tools/tool_performance_analyzer.py:
  L122  conn.close()  ← _init_database
  L155  conn.close()  ← record_performance
  L454  conn.close()  ← _get_performance_records

src/evolution/security/audit_logger.py:
  L153  conn.close()  ← _get_connection (finally 块)

src/evolution/health.py:
  L64   conn.close()  ← health_check (裸 sqlite3.connect)

hermes-plugin/__init__.py:
  L215  conn.close()  ← _checkpoint_associations_db (裸 sqlite3.connect)
```

共计 **22 处** `conn.close()` 破坏了 DB 连接缓存。

---

## 附录 B: 数据库清单与风险映射

| 数据库文件 | 主要写入模块 | 写入频率 | WAL checkpoint | conn.close 问题 |
|-----------|-------------|---------|----------------|-----------------|
| `associations.db` | `memory/database.py` | 极高 | ✅ 已覆盖 | ⚠️ close() 方法 |
| `learning_experiences.db` | `learning/observer.py` | 高 | ❌ 未覆盖 | ❌ 6处 close |
| `tools.db` | `tools/tool_registry.py` | 中 | ❌ 未覆盖 | ❌ 8处 close |
| `tool_performance.db` | `tools/tool_performance_analyzer.py` | 高 | ❌ 未覆盖 | ❌ 3处 close |
| `evolution_audit.db` | `closed_loop/evolution_auditor.py` | 中 | ❌ 未覆盖 | ✅ 使用缓存 |
| `audit.db` | `security/audit_logger.py` | 高 | ❌ 未覆盖 | ❌ 上下文管理器 close |
| `collaboration_messages.db` | `collaboration/message_bus.py` | 中 | ❌ 未覆盖 | ⚠️ close() 方法 |
| `evolution.db` | `main.py` (SelfMonitor) | 低 | ❌ 未覆盖 | ✅ 使用缓存 |

---

*报告生成: 2026-05-10 | 扫描文件数: 50+ .py 文件 | 风险项: 10 个 | 修复建议: 9 项 | 测试盲区: 10 个场景*

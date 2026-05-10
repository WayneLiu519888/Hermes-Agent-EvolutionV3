# HermesAgentEvolution DFX 专项优化方案

> 版本：v1.0 | 日期：2026-05-11
> 基准文档：`docs/v4_dfx_architecture_review.md`（8 维 DFX 审视，3387 行）
> 联动文档：`docs/architecture_optimization_plan.md`（架构优化方案 Phase 1-4）
> 核心原则：架构优化先行，DFX 专项修补随后；能靠架构消除的不重复修

---

## 一、架构优化（Phase 1-3）自动解决的 DFX 问题

架构优化方案实施后，以下 DFX 问题将被自动消除，无需本方案额外修复：

| # | DFX 问题 | 严重度 | 对应架构优化 | 消除原理 |
|---|----------|--------|-------------|----------|
| 1 | hermes-plugin 与 _plugin 872行镜像重复 | ★★★ | Phase 1: plugin_core.py 单一代码源 | 删 900 行重复，可维护性从 C 升至 A |
| 2 | `_get_data_dir()` 三处重复实现 | ★★☆ | Phase 1: 统一导入 `db_utils.get_data_dir()` | 路径逻辑一致，消除分化风险 |
| 3 | WAL checkpoint 双份实现（db_utils + plugin） | ★★☆ | Phase 1: 统一用 `auto_checkpoint_if_needed()` | 删除 plugin 中裸 connect 特化版 |
| 4 | 4处裸 `sqlite3.connect()` 绕过统一工厂 | ★★★ | Phase 2: DatabasePool 统一连接池 | message_bus / health.py / audit归档 / plugin checkpoint 全部纳入 |
| 5 | 22处 `conn.close()` 架空连接缓存 | ★★☆ | Phase 2: DatabasePool contextmanager 禁止 close | close() 变 NOP，连接生命周期归池管理 |
| 6 | `_engine_instances` 全局字典单例 | ★☆☆ | Phase 1: 模块级单例标准化 | 统一为 DatabasePool 单例模式 |
| 7 | EvolutionAuditor 每次新建实例跑全套 DDL | ★☆☆ | Phase 1: plugin_core 统一管理 | `_get_evolution_auditor()` 单例复用 |
| 8 | health.py 裸 connect 无 WAL/超时配置 | ★★☆ | Phase 2: 纳入 DatabasePool | 继承统一 PRAGMA 配置 |
| 9 | `_get_orchestrator()` TypeError bug (str / str) | ★★☆ | Phase 1: plugin_core 重构 | 代码重写中一并修复 |
| 10 | `main.py` SelfMonitor 构造函数不匹配 | ★★☆ | Phase 1: 废弃 main.py | main.py 是早期原型，不再维护 |
| 11 | health.py `get_data_dir(data_dir)` TypeError | ★★☆ | Phase 1: 统一导入路径 | 修复调用签名 |
| 12 | `config/evolution_config.yaml` 版本 2.0.0 | ★☆☆ | Phase 2: Schema 统一 | YAML 废弃或更新到 3.0.6 |
| 13 | `_get_data_dir` 中 env_dir 分支不 mkdir | ★★☆ | Phase 1: 统一到 db_utils 版本 | db_utils 中已正确 mkdir |

> **以上 13 项问题由架构优化（Phase 1-3）自动解决，本方案不再重复列入。**

---

## 二、架构优化后仍需专项修复的 DFX 问题

以下问题按 DFX 维度分类，架构优化不会自动解决，需专项修复。

---

### 2.1 可靠性（Reliability）

#### R01：WAL Checkpoint 全覆盖（7 个数据库）

- **问题**：当前仅 associations.db 有 checkpoint 机制。其余 6 个 DB（learning_experiences.db, tools.db, tool_performance.db, retrieval_optimization.db, evolution_audit.db, audit.db）均无。89GB WAL 事故随时可能重演。
- **定位**：`db_utils.py:173-188` 已有 `auto_checkpoint_if_needed()`，但零调用方。
- **修复方案**：
  1. 在 daemon 主循环每 5 轮调用 `db_pool.checkpoint_all(max_wal_mb=100)`
  2. 在每个高频写入模块末尾调用 `auto_checkpoint_if_needed(db_name, max_wal_mb=100)`
  3. 守护进程停止时执行 `PRAGMA wal_checkpoint(TRUNCATE)` 彻底截断
- **工时**：4h

```python
# 1. daemon 主循环定期调度
# src/evolution/closed_loop/daemon.py
from evolution.db_pool import db_pool

class EvolutionDaemon:
    def _run_loop(self):
        cycle_count = 0
        while self._state == LoopState.RUNNING:
            self._execute_single_cycle()
            cycle_count += 1
            # 每 5 个循环 checkpoint 所有 DB
            if cycle_count % 5 == 0:
                try:
                    db_pool.checkpoint_all(max_wal_mb=100)
                except Exception as e:
                    logger.warning("定期 checkpoint 失败: %s", e)

# 2. 写入热点自动触发
# src/evolution/learning/observer.py
from ..db_utils import auto_checkpoint_if_needed

def record_experience(self, experience: Experience) -> str:
    # ... 写入逻辑 ...
    conn.commit()
    auto_checkpoint_if_needed("learning_experiences.db", max_wal_mb=100)
    return experience.id

# 3. 优雅关闭时 TRUNCATE 所有 DB
# hermes_daemon.py stop()
from evolution.db_utils import wal_checkpoint

ALL_EVOLUTION_DBS = [
    "associations.db", "tools.db", "learning_experiences.db",
    "tool_performance.db", "retrieval_optimization.db",
    "evolution_audit.db", "audit.db", "collaboration_messages.db"
]

def stop(self):
    # ... 现有停止逻辑 ...
    for db_name in ALL_EVOLUTION_DBS:
        try:
            wal_checkpoint(db_name, mode="TRUNCATE")
        except Exception:
            pass
    close_all_connections()
```

---

#### R02：启用 retry_on_db_error（5 个写入模块）

- **问题**：`db_utils.retry_on_db_error`（指数退避 2s→4s→8s）已实现但**零使用**。所有写入遇到 `database is locked` 直接崩溃，不重试。
- **定位**：`db_utils.py:207-251` 装饰器，仅 `tests/test_db_utils.py` 有测试引用。
- **修复方案**：在 5 个核心写入模块的关键方法上添加 `@retry_on_db_error(max_attempts=3)`
- **工时**：3h

```python
# 在以下 5 个模块的写入方法上添加装饰器
from ..db_utils import retry_on_db_error

# src/evolution/memory/database.py
@retry_on_db_error(max_attempts=3)
def add_memory_entry(self, content: str, ...) -> str: ...

@retry_on_db_error(max_attempts=3)
def add_association(self, source_id: str, target_id: str, ...) -> str: ...

# src/evolution/learning/observer.py
@retry_on_db_error(max_attempts=3)
def record_experience(self, experience: Experience) -> str: ...

# src/evolution/tools/tool_registry.py
@retry_on_db_error(max_attempts=3)
def register(self, name: str, schema: Dict, ...) -> bool: ...

# src/evolution/tools/tool_performance_analyzer.py
@retry_on_db_error(max_attempts=3)
def record_performance(self, tool_name: str, metrics: Dict) -> str: ...

# src/evolution/memory/retrieval_optimizer.py
@retry_on_db_error(max_attempts=3)
def record_feedback(self, query: str, selected_ids: List[str], ...) -> str: ...
```

**覆盖清单**：

| 模块 | 需装饰方法数 | 优先级 |
|------|:----------:|:------:|
| `memory/database.py` | 6 (add_memory_entry, add_association, delete_memory_entry, update_association, delete_association, save_experience) | P0 |
| `learning/observer.py` | 1 (record_experience) | P0 |
| `tools/tool_registry.py` | 2 (register, update_usage_stats) | P0 |
| `tools/tool_performance_analyzer.py` | 1 (record_performance) | P1 |
| `memory/retrieval_optimizer.py` | 1 (record_feedback) | P1 |

---

#### R03：补齐 rollback（41 commit vs 1 rollback）

- **问题**：全项目 41 处 `conn.commit()` 对 1 处 `conn.rollback()`，致命不对称。当前做法是 `try: conn.commit() except: logger.error()` — 异常时事务残留，虽然 SQLite 在 close 时会隐式 rollback，但在 DatabasePool 不复用期间存在事务污染风险。
- **定位**：observer.py, database.py, tool_registry.py, tool_performance_analyzer.py, retrieval_optimizer.py 等。
- **修复方案**：
  1. 在 `db_utils.py` 新增 `@contextmanager` 的 `transaction()` 工具
  2. 将写操作从手动 commit 模式改为 contextmanager 模式
- **工时**：5h

```python
# src/evolution/db_utils.py 新增
from contextlib import contextmanager

@contextmanager
def transaction(db_name: str):
    """数据库事务上下文管理器，自动 commit/rollback
    
    用法:
        with transaction("learning_experiences.db") as conn:
            conn.execute("INSERT INTO experiences ...")
            conn.execute("UPDATE statistics ...")
    """
    conn = get_evolution_db(db_name)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise

# 迁移示例：observer.py record_experience()
# 修改前（危险模式）：
def record_experience(self, experience: Experience) -> str:
    conn = get_evolution_db(self.db_path)
    try:
        cursor = conn.cursor()
        # ... INSERT ...
        conn.commit()
        return experience.id
    except Exception as e:
        logger.error(f"记录失败: {e}")
        return ""  # conn 处于未定义事务状态！

# 修改后（安全模式）：
def record_experience(self, experience: Experience) -> str:
    try:
        with transaction(self.db_path) as conn:
            cursor = conn.cursor()
            # ... INSERT ...
        return experience.id
    except Exception as e:
        logger.error("记录经验失败: %s", e, exc_info=True)
        return ""
```

**迁移范围**（按优先级）：

| 优先级 | 模块 | 需迁移方法数 |
|:------:|------|:----------:|
| P0 | `memory/database.py` | 7 |
| P0 | `learning/observer.py` | 2 |
| P0 | `tools/tool_registry.py` | 3 |
| P0 | `closed_loop/evolution_auditor.py` | 2 |
| P1 | `tools/tool_performance_analyzer.py` | 1 |
| P1 | `memory/retrieval_optimizer.py` | 1 |
| P1 | `learning/tool_strategy_learner.py` | 1 |

---

#### R04：大写入批量事务包裹

- **问题**：`association_discoverer.py:discover_all()` 逐条 `add_association()` + commit，1000 个关联 = 1000 次 fsync，性能极差。
- **定位**：`memory/association_discoverer.py:720-724`
- **修复方案**：在 discover 循环外层用 `BEGIN/COMMIT` 包裹整个发现过程，或累积结果后用 executemany 批量写入。
- **工时**：2h

```python
# src/evolution/memory/association_discoverer.py
def _discover_semantic(self, entries: List[Dict], discovered: List[Dict]):
    """批量发现语义关联，单事务提交"""
    batch = []
    for e1, e2 in combinations(entries, 2):
        similarity = self._calculate_semantic_similarity(e1, e2)
        if similarity >= self.threshold:
            batch.append((e1['id'], e2['id'], 'semantic', similarity, ...))
    
    # 批量写入
    if batch:
        conn = get_evolution_db("associations.db")
        with transaction("associations.db") as conn:
            conn.executemany(
                """INSERT OR REPLACE INTO associations 
                   (source_id, target_id, association_type, strength, ...)
                   VALUES (?, ?, ?, ?, ...)""",
                batch
            )
```

---

#### R05：优雅关闭补齐（WAL checkpoint + 连接清理 + atexit）

- **问题**：`hermes_daemon.py:stop()` 不调用 checkpoint、不关连接、不注册 atexit。进程被 SIGTERM 杀死后下次启动阻塞在 89GB WAL 恢复。
- **定位**：`hermes_daemon.py:stop()`, 全局无 atexit
- **修复方案**：
  1. stop() 中补齐 checkpoint + close_all_connections
  2. 注册 atexit 作为最后防线
  3. EvolutionDaemon 从 daemon=True 改为 daemon=False，主线程等待
- **工时**：3h

```python
# hermes_daemon.py
import atexit
from evolution.db_utils import close_all_connections, wal_checkpoint

def _cleanup_on_exit():
    """atexit 注册——最后防线"""
    try:
        for db_name in ALL_EVOLUTION_DBS:
            wal_checkpoint(db_name, mode="TRUNCATE")
        close_all_connections()
    except Exception:
        pass

atexit.register(_cleanup_on_exit)

class HermesEvolutionDaemon:
    def stop(self):
        self._running = False
        self._stop_event.set()
        
        if self.daemon:
            self.daemon.stop(timeout=10)
        if self.metrics_collector:
            self.metrics_collector.stop()
        
        # NEW: WAL checkpoint 所有数据库
        for db_name in ALL_EVOLUTION_DBS:
            try:
                wal_checkpoint(db_name, mode="TRUNCATE")
            except Exception as e:
                logger.warning("Checkpoint %s 失败: %s", db_name, e)
        
        # NEW: 关闭所有连接
        close_all_connections()
        
        if self.feishu_notifier:
            self.feishu_notifier.send("系统停止", "Hermes Evolution Daemon 已停止")
```

---

### 2.2 性能（Performance）

#### P01：缓存 LRU 淘汰（4 处无界增长）

- **问题**：`_experiences_cache`（observer.py）、`feedback_history`（retrieval_optimizer.py）、`monitoring_history`（self_monitor.py）、`snapshots`（daemon.py）均为无界增长 dict/list，长期运行导致 OOM。
- **修复方案**：全部改为 OrderedDict LRU + 上限（1000），feedback_history 保留最近 500 条。
- **工时**：3h

```python
# src/evolution/learning/observer.py
from collections import OrderedDict

class LearningObserver:
    MAX_CACHE_SIZE = 1000
    
    def __init__(self, db_path: str = None):
        # 修改前: self._experiences_cache: Dict[str, Experience] = {}
        # 修改后:
        self._experiences_cache: OrderedDict[str, Experience] = OrderedDict()
    
    def _cache_put(self, experience: Experience):
        """LRU 缓存写入"""
        if experience.id in self._experiences_cache:
            self._experiences_cache.move_to_end(experience.id)
        self._experiences_cache[experience.id] = experience
        # 淘汰最旧的一半
        while len(self._experiences_cache) > self.MAX_CACHE_SIZE:
            self._experiences_cache.popitem(last=False)
    
    def _cache_get(self, experience_id: str) -> Optional[Experience]:
        """LRU 缓存读取（命中时提升优先级）"""
        if experience_id in self._experiences_cache:
            self._experiences_cache.move_to_end(experience_id)
            return self._experiences_cache[experience_id]
        return None

# src/evolution/memory/retrieval_optimizer.py
MAX_FEEDBACK_HISTORY = 500

def record_feedback(self, feedback: RetrievalFeedback):
    # ... 持久化到 DB ...
    self.feedback_history.append(feedback)
    if len(self.feedback_history) > MAX_FEEDBACK_HISTORY:
        self.feedback_history = self.feedback_history[-MAX_FEEDBACK_HISTORY:]
```

---

#### P02：N+1 查询消除（3 处关键路径）

- **问题**：
  1. `retrieval_optimizer.py:get_recommendations()` — 循环内逐条 SELECT（L417-457）
  2. `association_optimizer.py:optimize_all_associations()` — O(n²) 线性扫描 + 逐条 UPDATE/DELETE（L53-122）
  3. `association_discoverer.py:discover_for_entry()` — 逐条 add_association + commit（L148-245）
- **修复方案**：改为批量查询 + 单事务批量写入
- **工时**：4h

```python
# retrieval_optimizer.py: 消除 N+1
# 修改前：
def get_recommendations(self, entry_id: str, limit: int = 10):
    # ... 获取 related_ids ...
    results = []
    for rel_id in related_ids:  # N+1!
        cursor.execute('SELECT ... FROM associations WHERE source_id = ?', (rel_id,))
        results.append(...)
    return results

# 修改后：
def get_recommendations(self, entry_id: str, limit: int = 10):
    # ... 获取 related_ids ...
    placeholders = ','.join(['?' for _ in related_ids])
    cursor.execute(
        f'SELECT ... FROM associations WHERE source_id IN ({placeholders})',
        related_ids
    )
    return cursor.fetchall()

# association_optimizer.py: 消除 O(n²)
# 修改前：在循环内线性扫描 + 逐条操作
for assoc in associations:
    match = next((a for a in all_associations if a['id'] == assoc['id']), None)
    # ...

# 修改后：构建索引字典
assoc_index = {a['id']: a for a in all_associations}
for assoc_id, score in quality_scores.items():
    match = assoc_index.get(assoc_id)
    # ...
```

---

#### P03：JSON 字段索引优化（生成列）

- **问题**：`observer.py:397-403` 使用 `json_extract(metrics, '$.duration')` 无索引，全表扫描。`tags LIKE '%\"tag\"%'` 同等问题。
- **修复方案**：
  1. tags 查询改为 `json_each` 子查询（已有索引可用）
  2. duration/metric 字段添加 SQLite 生成列（3.31+）
- **工时**：3h

```python
# 1. tags 查询优化 — observer.py query_experiences()
# 修改前（全表扫描）：
for tag in tags:
    conditions.append("tags LIKE ?")
    params.append(f'%"{tag}"%')

# 修改后（利用 json_each）：
for tag in tags:
    conditions.append(
        "EXISTS (SELECT 1 FROM json_each(experiences.tags) WHERE value = ?)"
    )
    params.append(tag)

# 2. schema 升级 — 添加生成列（SQLite 3.31+）
# src/evolution/schema.py
GENERATED_COLUMNS_SQL = """
-- learning_experiences.db
ALTER TABLE experiences ADD COLUMN experience_duration REAL 
    GENERATED ALWAYS AS (json_extract(metrics, '$.duration')) STORED;
CREATE INDEX IF NOT EXISTS idx_experiences_duration ON experiences(experience_duration);

-- learning_experiences.db  
ALTER TABLE experiences ADD COLUMN experience_success INTEGER
    GENERATED ALWAYS AS (json_extract(metrics, '$.success')) STORED;
CREATE INDEX IF NOT EXISTS idx_experiences_success ON experiences(experience_success);
"""
```

---

#### P04：LIKE → FTS5 全文搜索

- **问题**：`database.py:246` 使用 `content LIKE '%keyword%'` 全表扫描，无法使用 B-tree 索引。
- **修复方案**：为 `memory_entries.content` 创建 FTS5 虚拟表，搜索查询改用 FTS5 MATCH。
- **工时**：3h

```python
# src/evolution/memory/database.py
def _init_fts(self, conn):
    """创建 FTS5 全文搜索表"""
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_entries_fts 
        USING fts5(content, content_rowid='id', content='memory_entries')
    """)
    # 触发器保持 FTS 与主表同步
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memory_entries_ai AFTER INSERT ON memory_entries BEGIN
            INSERT INTO memory_entries_fts(rowid, content) VALUES (new.id, new.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memory_entries_ad AFTER DELETE ON memory_entries BEGIN
            INSERT INTO memory_entries_fts(memory_entries_fts, rowid, content) 
            VALUES ('delete', old.id, old.content);
        END
    """)
    conn.execute("""
        CREATE TRIGGER IF NOT EXISTS memory_entries_au AFTER UPDATE ON memory_entries BEGIN
            INSERT INTO memory_entries_fts(memory_entries_fts, rowid, content) 
            VALUES ('delete', old.id, old.content);
            INSERT INTO memory_entries_fts(rowid, content) VALUES (new.id, new.content);
        END
    """)

# 搜索改造
def find_similar_memories(self, content: str, limit: int = 10):
    """使用 FTS5 搜索相似记忆"""
    conn = get_evolution_db(self.db_path)
    # 修改前: WHERE content LIKE '%keyword%'
    # 修改后: FTS5 MATCH
    cursor = conn.execute("""
        SELECT m.* FROM memory_entries m
        JOIN memory_entries_fts fts ON m.id = fts.rowid
        WHERE memory_entries_fts MATCH ?
        ORDER BY rank
        LIMIT ?
    """, (content, limit))
    return cursor.fetchall()
```

---

#### P05：批量写入 executemany（4 处关键路径）

- **问题**：全代码库无一处使用 `executemany()`。`audit_logger.log_batch()` 名为批量实则逐条调用 `log_event()`。association 发现每条一个事务。
- **修复方案**：在 4 处批量写入路径改为 executemany + 单事务。
- **工时**：2h

```python
# 1. audit_logger.py log_batch — 真批量
def log_batch(self, events: List[AuditEntry]):
    """批量写入审计日志"""
    with transaction("audit.db") as conn:
        conn.executemany("""
            INSERT INTO audit_logs 
            (event_type, level, agent_id, message, correlation_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, [
            (e.event_type, e.level, e.agent_id, e.message, e.correlation_id, e.created_at)
            for e in events
        ])

# 2. tool_strategy_learner.py — 批量持久化
def _persist_usage_batch(self, usages: List[Tuple]):
    with transaction("tools.db") as conn:
        conn.executemany("""
            INSERT INTO tool_usage_history (tool_name, timestamp, success, duration_ms, context)
            VALUES (?, ?, ?, ?, ?)
        """, usages)

# 3. association_discoverer.py — 批量关联（见 R04）

# 4. observer.py — 批量经验导入
def import_experiences(self, experiences: List[Experience]):
    with transaction(self.db_path) as conn:
        conn.executemany("""
            INSERT OR REPLACE INTO experiences 
            (id, experience_type, task_id, outcome, metrics, tags, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [(e.id, e.type, e.task_id, e.outcome, 
               json.dumps(e.metrics), json.dumps(e.tags), e.timestamp)
              for e in experiences])
```

---

#### P06：cache_size 调整

- **问题**：`db_utils.py:112` 设置 `cache_size=-8000`（8MB），对于 951MB 生产数据库太小。SQLite 建议页缓存为数据库大小的 10-20%。
- **修复方案**：环境变量化，默认提升至 64MB（`-64000`）。
- **工时**：0.5h

```python
# db_utils.py
import os
DEFAULT_CACHE_SIZE = int(os.environ.get("EVOLUTION_DB_CACHE_KB", "-64000"))
conn.execute(f"PRAGMA cache_size={DEFAULT_CACHE_SIZE}")
```

---

### 2.3 可用性（Availability）

#### A01：Daemon 状态恢复

- **问题**：`EvolutionDaemon._load_state()` 方法存在但从未调用。重启后 cycle_count 归零、快照历史丢失、consecutive_failures 重置。
- **修复方案**：在 `start()` 方法中调用 `_load_state()` 并恢复状态。
- **工时**：2h

```python
# src/evolution/closed_loop/daemon.py
def start(self):
    # NEW: 恢复先前的守护进程状态
    saved_state = self._load_state()
    if saved_state:
        self.cycle_count = saved_state.get("cycle_count", 0)
        self.consecutive_failures = saved_state.get("consecutive_failures", 0)
        # 恢复快照历史
        snapshots_data = saved_state.get("snapshots", [])
        if snapshots_data:
            self.snapshots = [EvolutionSnapshot(**s) for s in snapshots_data]
        logger.info("已恢复守护进程状态: cycle=%d, failures=%d, snapshots=%d",
                   self.cycle_count, self.consecutive_failures, len(self.snapshots))
    
    self._state = LoopState.RUNNING
    self._thread = threading.Thread(target=self._run_loop, daemon=False)
    self._thread.start()
```

---

#### A02：启动预检（Pre-flight Check）

- **问题**：启动时无预检，组件初始化失败直接 `sys.exit(1)`，用户不知道原因。
- **修复方案**：新增 `src/evolution/preflight.py`，启动前检查磁盘空间、DB 可读写、环境变量、飞书连通性。
- **工时**：3h

```python
# src/evolution/preflight.py
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PreflightResult:
    passed: bool
    checks: List[Dict] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

def preflight_check(data_dir: Path) -> PreflightResult:
    """启动前预检"""
    checks = []
    warnings = []
    
    # 1. 磁盘空间（至少 100MB）
    usage = shutil.disk_usage(data_dir)
    free_mb = usage.free / (1024 * 1024)
    disk_ok = free_mb >= 100
    checks.append({"name": "磁盘空间", "status": "ok" if disk_ok else "fail",
                   "detail": f"可用: {free_mb:.0f}MB"})
    if not disk_ok:
        return PreflightResult(passed=False, checks=checks,
                               warnings=[f"磁盘空间不足: 仅 {free_mb:.0f}MB，需至少 100MB"])
    
    # 2. 数据目录可读写
    data_dir.mkdir(parents=True, exist_ok=True)
    test_file = data_dir / ".preflight_test"
    try:
        test_file.write_text("test")
        test_file.unlink()
        checks.append({"name": "数据目录", "status": "ok"})
    except Exception:
        checks.append({"name": "数据目录", "status": "fail"})
        return PreflightResult(passed=False, checks=checks,
                               warnings=[f"数据目录不可写: {data_dir}"])
    
    # 3. 环境变量
    if not os.environ.get("HERMES_HOME") and not os.environ.get("EVOLUTION_DATA_DIR"):
        warnings.append("未设置 HERMES_HOME 或 EVOLUTION_DATA_DIR，将使用默认路径")
        checks.append({"name": "环境变量", "status": "warning"})
    else:
        checks.append({"name": "环境变量", "status": "ok"})
    
    # 4. 关键 Python 依赖
    try:
        import sqlite3, json, threading, logging
        checks.append({"name": "核心依赖", "status": "ok"})
    except ImportError as e:
        checks.append({"name": "核心依赖", "status": "fail", "detail": str(e)})
        return PreflightResult(passed=False, checks=checks)
    
    return PreflightResult(passed=True, checks=checks, warnings=warnings)

# hermes_daemon.py 中使用
def initialize_components(self):
    # NEW: 启动前预检
    data_dir = _resolve_data_dir()
    preflight = preflight_check(data_dir)
    if not preflight.passed:
        for w in preflight.warnings:
            logger.critical("预检失败: %s", w)
        sys.exit(1)
    for w in preflight.warnings:
        logger.warning("预检警告: %s", w)
    # ... 继续原有初始化 ...
```

---

#### A03：飞书健康检查集成

- **问题**：`feishu_notifier.py:318` 的 `test_connection()` 已实现但从未在启动流程中调用。
- **修复方案**：在 daemon 初始化时调用 `test_connection()`，失败则警告降级到 simulated 模式。
- **工时**：1h

```python
# hermes_daemon.py initialize_components()
if FEISHU_AVAILABLE:
    try:
        self.feishu_notifier = get_notifier()
        result = self.feishu_notifier.test_connection()
        if result.get("test_result") == "失败":
            logger.warning("飞书连接测试失败: %s，将使用日志通知", 
                          result.get("error", "未知错误"))
    except Exception as e:
        logger.warning("飞书通知器初始化失败: %s，将使用日志通知", e)
        self.feishu_notifier = None
```

---

### 2.4 安全（Security）

#### S01：移除硬编码敏感信息

- **问题**：
  - `feishu_notifier.py:31` — App ID 硬编码为 `cli_a96b9943f1f8dcd2`
  - `deployment_service.py:165` — 数据库密码硬编码 `hermes123`
- **修复方案**：改为环境变量强制要求，默认值为空并记录警告。
- **工时**：1h

```python
# src/utils/feishu_notifier.py
# 修改前:
"app_id": os.environ.get("FEISHU_APP_ID", "cli_a96b9943f1f8dcd2"),

# 修改后:
"app_id": os.environ.get("FEISHU_APP_ID", ""),
"app_secret": os.environ.get("FEISHU_APP_SECRET", ""),

# 在初始化时检查
def __init__(self, config: dict):
    if not config.get("app_id"):
        logger.warning("FEISHU_APP_ID 未配置，飞书 OpenAPI 功能将不可用")
    if not config.get("app_secret"):
        logger.warning("FEISHU_APP_SECRET 未配置，飞书 OpenAPI 功能将不可用")
    # ...

# src/services/system/deployment/deployment_service.py
# 修改前:
"password": "***",

# 修改后:
"password": os.environ.get("EVOLUTION_DB_PASSWORD", secrets.token_urlsafe(16)),
```

---

#### S02：飞书签名验证

- **问题**：飞书 webhook 回调未验证 X-Lark-Signature 头，存在伪造请求风险。
- **修复方案**：添加签名验证中间件。
- **工时**：2h

```python
# src/evolution/security/webhook_validator.py
import hashlib
import hmac
import time

def verify_feishu_signature(timestamp: str, nonce: str, body: str, 
                           secret: str, signature: str) -> bool:
    """验证飞书回调签名
    
    飞书签名算法: 
        base_string = timestamp + nonce + encrypt_key + body
        signature = sha256(base_string)
    """
    if not secret:
        logger.warning("FEISHU_WEBHOOK_SECRET 未配置，跳过签名验证")
        return True  # 向后兼容
    
    # 时间戳防重放攻击（5 分钟窗口）
    try:
        ts = int(timestamp)
        if abs(time.time() - ts) > 300:
            logger.warning("飞书回调时间戳过期: %s", timestamp)
            return False
    except ValueError:
        return False
    
    # 计算签名
    base_string = f"{timestamp}\n{nonce}\n{secret}\n{body}"
    expected = hashlib.sha256(base_string.encode()).hexdigest()
    return hmac.compare_digest(expected, signature)
```

---

#### S03：错误信息脱敏

- **问题**：健康检查、CLI 错误输出直接暴露内部路径（如 `/home/user/.hermes/data/evolution/associations.db`）和异常堆栈。
- **修复方案**：创建 `InputValidator.sanitize_error_message()` 统一脱敏。
- **工时**：1.5h

```python
# src/evolution/security/input_validator.py
import re
from pathlib import Path

class InputValidator:
    # ... 其他验证方法 ...
    
    @staticmethod
    def sanitize_error_message(error: Exception, 
                               data_dir: Path = None) -> str:
        """脱敏错误消息，移除内部路径和敏感信息
        
        将:
            [Errno 13] Permission denied: '/home/user/.hermes/data/evolution/associations.db'
        转换为:
            数据库文件访问失败，请检查权限
        """
        msg = str(error)
        # 替换数据目录路径
        if data_dir:
            msg = msg.replace(str(data_dir), "<DATA_DIR>")
        # 替换用户 home 路径
        home = str(Path.home())
        msg = msg.replace(home, "<HOME>")
        # 截断过长消息
        if len(msg) > 500:
            msg = msg[:497] + "..."
        return msg

# health.py 中使用
def health_check(data_dir: Path = None):
    try:
        # ... 检查逻辑 ...
    except Exception as e:
        sanitized = InputValidator.sanitize_error_message(e, data_dir)
        return {"status": "error", "message": sanitized}
```

---

#### S04：输入验证统一层

- **问题**：CLI 参数无范围校验（interval 可传负数），db_path 可传入绝对路径访问任意文件。
- **修复方案**：`InputValidator` 添加工具名/路径/间隔验证方法。
- **工时**：2h

```python
# src/evolution/security/input_validator.py (续)

import re
from dataclasses import dataclass

@dataclass
class ValidationResult:
    valid: bool
    error: str = ""
    sanitized: any = None

class InputValidator:
    TOOL_NAME_PATTERN = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]{0,63}$')
    
    @classmethod
    def validate_tool_name(cls, name: str) -> ValidationResult:
        if not name or not cls.TOOL_NAME_PATTERN.match(name):
            return ValidationResult(False, f"无效的工具名称: {name}")
        return ValidationResult(True, sanitized=name)
    
    @classmethod
    def validate_db_path(cls, path: str, data_dir: Path) -> ValidationResult:
        """校验 DB 路径，拒绝目录遍历攻击"""
        resolved = Path(path).resolve()
        data_dir_resolved = data_dir.resolve()
        try:
            resolved.relative_to(data_dir_resolved)
        except ValueError:
            return ValidationResult(False, f"不允许的数据库路径: {path}")
        return ValidationResult(True, sanitized=str(resolved))
    
    @classmethod
    def validate_interval(cls, seconds: int) -> ValidationResult:
        if not (10 <= seconds <= 86400):
            return ValidationResult(False, f"间隔时间需在 10-86400 之间，收到: {seconds}")
        return ValidationResult(True, sanitized=seconds)
```

---

### 2.5 可观测性（Observability）

#### O01：健康检查增强（WAL 监控 + 内存 + 连接数）

- **问题**：`health.py` 健康检查不监控 WAL 大小、内存使用、数据库连接数。仅 CLI 可用，无 HTTP 端点。
- **修复方案**：
  1. 扩展 `comprehensive_health_check()` 增加 WAL/内存/连接数维度
  2. 接入 `hermes doctor` 框架（架构优化 Phase 1 已计划）
- **工时**：3h

```python
# src/evolution/health.py 扩展
import psutil
from pathlib import Path

def comprehensive_health_check(data_dir: Path = None) -> Dict:
    """全面健康检查 — 供 hermes doctor 及监控系统调用"""
    from evolution.db_utils import _resolve_data_dir
    data = data_dir or _resolve_data_dir()
    
    result = {
        "status": "healthy",
        "timestamp": time.time(),
        "checks": [],
        "metrics": {}
    }
    
    # 1. WAL 文件监控
    wal_warnings = []
    for db_file in sorted(data.glob("*.db")):
        wal_file = Path(str(db_file) + "-wal")
        if wal_file.exists():
            wal_mb = wal_file.stat().st_size / (1024 * 1024)
            result["metrics"][f"{db_file.name}_wal_mb"] = round(wal_mb, 2)
            if wal_mb > 100:
                wal_warnings.append(f"{db_file.name} WAL={wal_mb:.0f}MB，需要 checkpoint")
                result["status"] = "degraded"
    
    if wal_warnings:
        result["checks"].append({"name": "WAL", "status": "warning", 
                                 "detail": "; ".join(wal_warnings)})
    else:
        result["checks"].append({"name": "WAL", "status": "ok", 
                                 "detail": "所有 WAL 文件正常"})
    
    # 2. 内存使用
    process = psutil.Process()
    mem_mb = process.memory_info().rss / (1024 * 1024)
    result["metrics"]["memory_mb"] = round(mem_mb, 1)
    if mem_mb > 1024:
        result["checks"].append({"name": "内存", "status": "warning",
                                 "detail": f"内存占用 {mem_mb:.0f}MB > 1GB"})
        result["status"] = "degraded"
    else:
        result["checks"].append({"name": "内存", "status": "ok",
                                 "detail": f"{mem_mb:.1f}MB"})
    
    # 3. 数据库连接数
    from evolution.db_utils import _connection_cache
    active_conns = len([c for c in _connection_cache.values() 
                        if _conn_alive(c)])
    result["metrics"]["db_connections"] = active_conns
    if active_conns > 20:
        result["checks"].append({"name": "连接数", "status": "warning",
                                 "detail": f"活跃连接: {active_conns}"})
    else:
        result["checks"].append({"name": "连接数", "status": "ok",
                                 "detail": f"活跃连接: {active_conns}"})
    
    return result

def _conn_alive(conn) -> bool:
    try:
        conn.execute("SELECT 1")
        return True
    except Exception:
        return False
```

---

#### O02：链路追踪（trace_id + phase_timings）

- **问题**：`correlation_id` 需调用方显式传入，未自动生成和传播。进化循环无阶段耗时追踪。
- **修复方案**：
  1. 在进化循环入口自动生成 `trace_id`（uuid4），通过 contextvars 传播
  2. 记录每个 Phase 的耗时到 `phase_timings`
- **工时**：3h

```python
# src/evolution/closed_loop/tracing.py
import uuid
import time
import contextvars
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Dict

_trace_id: contextvars.ContextVar = contextvars.ContextVar("trace_id", default=None)

def get_trace_id() -> str:
    """获取当前链路的 trace_id"""
    tid = _trace_id.get()
    if tid is None:
        tid = str(uuid.uuid4())[:8]
        _trace_id.set(tid)
    return tid

@dataclass
class PhaseTiming:
    phase: str
    start_time: float = 0
    end_time: float = 0
    
    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000

@dataclass 
class CycleTrace:
    trace_id: str
    cycle_id: int
    phase_timings: Dict[str, PhaseTiming] = field(default_factory=dict)
    start_time: float = 0
    end_time: float = 0

@contextmanager
def trace_phase(cycle_trace: CycleTrace, phase_name: str):
    """追踪单个阶段的耗时"""
    timing = PhaseTiming(phase=phase_name, start_time=time.time())
    try:
        yield
    finally:
        timing.end_time = time.time()
        cycle_trace.phase_timings[phase_name] = timing
        logger.debug("[trace=%s] Phase %s: %.1fms",
                    cycle_trace.trace_id, phase_name, timing.duration_ms)

# daemon.py 中使用
def _execute_single_cycle(self):
    trace = CycleTrace(
        trace_id=get_trace_id(),
        cycle_id=self.cycle_count,
        start_time=time.time()
    )
    
    with trace_phase(trace, "monitor"):
        metrics = self.metrics_collector.collect()
    
    with trace_phase(trace, "analyze"):
        issues = self.analyzer.analyze(metrics)
    
    with trace_phase(trace, "plan"):
        plan = self.planner.plan(issues)
    
    with trace_phase(trace, "execute"):
        result = self.executor.execute(plan)
    
    with trace_phase(trace, "verify"):
        verified = self.verifier.verify(result)
    
    with trace_phase(trace, "feedback"):
        self.feedback.record(trace)
    
    trace.end_time = time.time()
    # 记录慢 Phase
    for name, timing in trace.phase_timings.items():
        if timing.duration_ms > 30000:  # 30秒
            logger.warning("[trace=%s] 慢 Phase: %s = %.1fs",
                          trace.trace_id, name, timing.duration_ms / 1000)
```

---

#### O03：日志轮转

- **问题**：`feishu_notifications.log` 无限增长，无轮转机制。`system_metrics.jsonl` 同样。
- **修复方案**：
  1. 飞书通知日志改用 `RotatingFileHandler`（10MB × 3）
  2. `system_metrics.jsonl` 添加轮转（50MB × 5）
- **工时**：1.5h

```python
# src/utils/feishu_notifier.py
from logging.handlers import RotatingFileHandler

# 替换普通的 FileHandler
feishu_handler = RotatingFileHandler(
    os.path.join(data_dir, "feishu_notifications.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=3,
    encoding="utf-8"
)

# src/services/system/monitoring/monitoring_service.py
import gzip
import shutil

def rotate_jsonl_if_needed(path: Path, max_mb: int = 50, backups: int = 5):
    """system_metrics.jsonl 轮转"""
    if path.exists() and path.stat().st_size > max_mb * 1024 * 1024:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        rotated = path.with_suffix(f".{timestamp}.jsonl.gz")
        with open(path, 'rb') as f_in:
            with gzip.open(rotated, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        path.unlink()  # 清空原文件
        
        # 清理旧备份（保留最近 backups 个）
        old = sorted(path.parent.glob(f"{path.stem}.*.jsonl.gz"))
        for f in old[:-backups]:
            f.unlink()
```

---

#### O04：JSON 结构化日志选项

- **问题**：日志格式为 `timestamp | LEVEL | logger | message`，对 ELK/Loki 不友好。
- **修复方案**：通过 `LOG_FORMAT=json` 环境变量切换 JSON 格式，自动注入 trace_id。
- **工时**：2h

```python
# src/evolution/logging_config.py
import json
import logging
import os

class JsonFormatter(logging.Formatter):
    """JSON 结构化日志格式器"""
    def format(self, record):
        log_entry = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno,
        }
        # 自动注入 trace_id
        try:
            from evolution.closed_loop.tracing import get_trace_id
            tid = get_trace_id()
            if tid:
                log_entry["trace_id"] = tid
        except ImportError:
            pass
        
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = str(record.exc_info[1])
        
        return json.dumps(log_entry, ensure_ascii=False, default=str)

def setup_logging():
    log_format = os.environ.get("LOG_FORMAT", "text")
    
    if log_format == "json":
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
    else:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(
            "%(asctime)s | %(levelname)-5s | %(name)-28s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        ))
    
    logging.root.addHandler(handler)
```

---

### 2.6 可测试性（Testability）

#### T01：测试补底（关键盲区）

- **问题**：WAL 膨胀、并发写入、连接缓存失效等关键场景零测试覆盖。services/ 子包完全空白。
- **修复方案**：
  1. 创建 `conftest.py` 提取通用 fixture
  2. 添加 WAL checkpoint 集成测试
  3. 添加并发写入 test
- **工时**：5h

```python
# tests/conftest.py — 提取通用 fixture
import pytest
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

@pytest.fixture
def temp_db_dir(tmp_path):
    """临时数据库目录"""
    db_dir = tmp_path / "evolution_data"
    db_dir.mkdir()
    return db_dir

@pytest.fixture
def mock_notifier():
    return MagicMock()

@pytest.fixture
def mock_self_monitor():
    return MagicMock()

@pytest.fixture(autouse=True)
def clean_connection_cache():
    """每个测试前清理连接缓存"""
    from evolution.db_utils import _connection_cache, _cache_lock
    with _cache_lock:
        for conn in _connection_cache.values():
            try:
                conn.close()
            except Exception:
                pass
        _connection_cache.clear()
    yield
    with _cache_lock:
        for conn in _connection_cache.values():
            try:
                conn.close()
            except Exception:
                pass
        _connection_cache.clear()

# tests/test_wal_checkpoint.py — WAL 膨胀集成测试
import pytest
from evolution.db_utils import get_evolution_db, auto_checkpoint_if_needed

def test_auto_checkpoint_triggers_on_large_wal(temp_db_dir):
    """验证 WAL 超过阈值时自动 checkpoint"""
    db_path = str(temp_db_dir / "test.db")
    conn = get_evolution_db(db_path)
    
    # 模拟大量写入
    conn.execute("CREATE TABLE IF NOT EXISTS test_data (id INTEGER PRIMARY KEY, data TEXT)")
    for i in range(5000):
        conn.execute("INSERT INTO test_data (data) VALUES (?)", 
                    ("x" * 1000,))
    conn.commit()
    
    # 触发 checkpoint
    result = auto_checkpoint_if_needed(db_path, max_wal_mb=1)
    assert result in ("passive_checkpoint_ok", "truncate_checkpoint_ok", "wal_not_found")

# tests/test_concurrent_writes.py
import concurrent.futures
import threading

def test_concurrent_connection_cache_safety(temp_db_dir):
    """验证连接缓存在多线程下的安全性"""
    db_path = str(temp_db_dir / "concurrent.db")
    conn = get_evolution_db(db_path)
    conn.execute("CREATE TABLE IF NOT EXISTS data (id INTEGER PRIMARY KEY, val TEXT)")
    conn.commit()
    
    barrier = threading.Barrier(10)
    
    def worker(i):
        barrier.wait()  # 同步启动
        conn = get_evolution_db(db_path)
        conn.execute("INSERT INTO data (val) VALUES (?)", (f"worker_{i}",))
        conn.commit()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker, i) for i in range(10)]
        concurrent.futures.wait(futures)
    
    # 验证所有写入
    conn = get_evolution_db(db_path)
    count = conn.execute("SELECT COUNT(*) FROM data").fetchone()[0]
    assert count == 10
```

---

## 三、实施路线图

```
第 1-3 天：可靠性修复（R01-R05）
  ├── R01: WAL checkpoint 全覆盖（daemon + 热点 + 优雅关闭）
  ├── R02: retry_on_db_error 启用（5 个模块 11 个方法）
  ├── R03: rollback 补齐（transaction contextmanager + 17 方法迁移）
  ├── R04: 大写入批量事务包裹
  └── R05: 优雅关闭补齐（atexit + signal handler）

第 3-5 天：性能修复（P01-P06）
  ├── P01: 缓存 LRU 淘汰（4 处无界增长）
  ├── P02: N+1 查询消除（3 处关键路径）
  ├── P03: JSON 字段索引优化（生成列 + json_each）
  ├── P04: LIKE → FTS5 全文搜索
  ├── P05: 批量写入 executemany（4 处）
  └── P06: cache_size 调整（8MB → 64MB）

第 5-7 天：可用性 + 安全 + 可观测性（A01-A03, S01-S04, O01-O04）
  ├── A01: Daemon 状态恢复
  ├── A02: 启动预检
  ├── A03: 飞书健康检查集成
  ├── S01: 移除硬编码敏感信息
  ├── S02: 飞书签名验证
  ├── S03: 错误信息脱敏
  ├── S04: 输入验证统一层
  ├── O01: 健康检查增强
  ├── O02: 链路追踪（trace_id + phase_timings）
  ├── O03: 日志轮转
  └── O04: JSON 结构化日志选项

第 7-8 天：测试补底 + 验收（T01）
  ├── T01: conftest.py + WAL 测试 + 并发测试
  └── 全量回归测试
```

---

## 四、工时汇总

| 维度 | 项目 | 工时 |
|------|------|:----:|
| 可靠性 | R01 WAL Checkpoint 全覆盖 | 4h |
| 可靠性 | R02 retry_on_db_error 启用 | 3h |
| 可靠性 | R03 rollback 补齐 | 5h |
| 可靠性 | R04 大写入批量事务 | 2h |
| 可靠性 | R05 优雅关闭补齐 | 3h |
| **小计** | | **17h** |
| 性能 | P01 缓存 LRU 淘汰 | 3h |
| 性能 | P02 N+1 查询消除 | 4h |
| 性能 | P03 JSON 字段索引 | 3h |
| 性能 | P04 LIKE → FTS5 | 3h |
| 性能 | P05 批量写入 executemany | 2h |
| 性能 | P06 cache_size 调整 | 0.5h |
| **小计** | | **15.5h** |
| 可用性 | A01 Daemon 状态恢复 | 2h |
| 可用性 | A02 启动预检 | 3h |
| 可用性 | A03 飞书健康检查集成 | 1h |
| **小计** | | **6h** |
| 安全 | S01 移除硬编码敏感信息 | 1h |
| 安全 | S02 飞书签名验证 | 2h |
| 安全 | S03 错误信息脱敏 | 1.5h |
| 安全 | S04 输入验证统一层 | 2h |
| **小计** | | **6.5h** |
| 可观测性 | O01 健康检查增强 | 3h |
| 可观测性 | O02 链路追踪 | 3h |
| 可观测性 | O03 日志轮转 | 1.5h |
| 可观测性 | O04 JSON 结构化日志 | 2h |
| **小计** | | **9.5h** |
| 可测试性 | T01 测试补底 | 5h |
| **小计** | | **5h** |
| **总计** | | **59.5h ≈ 8 个工程日** |

---

## 五、验收标准

### 可靠性

- [ ] 所有 8 个数据库在 daemon 主循环中定期 checkpoint（每 5 圈 + 优雅关闭时）
- [ ] 5 个写入模块共 11 个关键方法已启用 `@retry_on_db_error(max_attempts=3)`
- [ ] 17 个写入方法从手动 commit 迁移到 `transaction()` contextmanager，异常时自动 rollback
- [ ] association 发现使用单事务批量写入，1000 条关联 < 10 次 commit
- [ ] `hermes_daemon stop` 执行 WAL TRUNCATE + close_all_connections
- [ ] `atexit` 注册作为最后防线
- [ ] 所有数据库在重启后 WAL 文件不超过 100MB

### 性能

- [ ] 4 处缓存在容量达到上限后自动淘汰（LRU），内存不持续增长
- [ ] `get_recommendations()` 从 N+1 改为单次 IN 查询
- [ ] `optimize_all_associations()` 从 O(n²) 降至 O(n)
- [ ] JSON tags 查询使用 `json_each` 子查询，不再 LIKE 全表扫描
- [ ] `find_similar_memories()` 使用 FTS5 MATCH，不再 LIKE 全表扫描
- [ ] `log_batch` 使用 `executemany`，100 条审计写入 < 100ms
- [ ] cache_size 默认 64MB，可通过环境变量调整

### 可用性

- [ ] Daemon 重启后恢复 cycle_count 和 snapshots 历史
- [ ] 启动时执行预检（磁盘/目录/环境变量/依赖）
- [ ] 飞书连接测试在启动时执行，失败时降级到 simulated 模式

### 安全

- [ ] 源码中无硬编码的 App ID / 密码等敏感值
- [ ] 飞书 webhook 回调进行 X-Lark-Signature 签名验证
- [ ] 用户可见错误信息不暴露内部路径
- [ ] CLI 参数有范围校验（interval 10-86400）
- [ ] db_path 拒绝目录遍历攻击

### 可观测性

- [ ] `comprehensive_health_check()` 返回 WAL 大小 + 内存 + 连接数
- [ ] 每个进化循环生成 trace_id，记录各 Phase 耗时
- [ ] 慢 Phase（>30s）自动 WARNING
- [ ] `feishu_notifications.log` 和 `system_metrics.jsonl` 有轮转
- [ ] 设置 `LOG_FORMAT=json` 后日志输出 JSON 格式

### 可测试性

- [ ] `conftest.py` 提供通用 DB / mock fixture
- [ ] 有 WAL checkpoint 集成测试（5000 条写入 → 触发 auto_checkpoint）
- [ ] 有并发连接缓存安全测试
- [ ] 全量回归测试通过（588 用例）

---

## 六、风险与依赖

| 风险 | 缓解措施 |
|------|----------|
| `transaction()` contextmanager 大规模迁移可能引入 bug | 逐模块迁移，每模块单独 PR 和测试 |
| FTS5 虚拟表需要 SQLite 3.9+ | 已满足（生产环境 SQLite 3.31+） |
| 生成列需 SQLite 3.31+ | 运行时检测版本，低版本降级为普通列 + 触发器 |
| 飞书签名验证依赖用户配置 secret | 未配置时保持向后兼容，仅 WARNING |
| JSON 格式日志影响现有日志解析 | 默认保持 text 格式，仅 `LOG_FORMAT=json` 时切换 |

---

## 附录：与架构优化方案的联动

| 架构优化（Phase） | 本方案依赖 | 联动关系 |
|------------------|-----------|----------|
| Phase 2: DatabasePool | R01, R02, R03, R05, P05 | checkpoint_all / transaction() / executemany 依赖连接池 |
| Phase 2: Schema | P03 | 生成列通过统一 Schema 迁移添加 |
| Phase 2: InputValidator | S03, S04 | 错误脱敏和输入验证复用验证层 |
| Phase 3: 状态机 | A01, O02 | 状态恢复 + 链路追踪依赖状态机架构 |
| Phase 4: DFX 补齐 | 本方案全部 | 架构优化先落地，本方案在 Phase 4 窗口集中修复 |

# HermesAgentEvolution V4 架构优化方案

> 版本：v2.0（合并版） | 日期：2026-05-11  
> 来源：架构审视 + DFX 8 维审视 + 业界对标 + 外部方案合并  
> 核心原则：**HAE 是 Hermes 插件，复用原生能力，不重复造轮子**

---

## 一、现状问题总览

| # | 问题 | 严重度 | 类型 |
|---|------|--------|------|
| 1 | hermes-plugin 与 _plugin 872行镜像重复 | ★★★ | 架构 |
| 2 | 7个DB仅1个有checkpoint，WAL炸弹随时可能再爆 | ★★★ | 可靠性 |
| 3 | 4处裸 sqlite3.connect() 绕过统一工厂 | ★★★ | 可靠性 |
| 4 | 22处 conn.close() 架空连接缓存 | ★★☆ | 性能 |
| 5 | retry_on_db_error 已实现零使用 | ★★☆ | 可靠性 |
| 6 | 闭环编排硬编码 Phase 1→6 线性链，不支持中断恢复 | ★★☆ | 架构 |
| 7 | _get_data_dir() 三处重复实现 | ★★☆ | 可维护性 |
| 8 | WAL checkpoint 双份实现（db_utils + plugin） | ★★☆ | 可维护性 |
| 9 | 工具注册未用 Hermes registry.register() | ★★☆ | 架构 |
| 10 | _experiences_cache 无界增长 | ★★☆ | 性能 |
| 11 | _engine_instances 全局字典单例模式 | ★☆☆ | 可维护性 |
| 12 | 健康检查独立，未对接 hermes doctor | ★☆☆ | 可观测性 |
| 13 | 飞书 App ID 硬编码源码 | ★★☆ | 安全 |
| 14 | feishu_notifications.log 无轮转 | ★☆☆ | 可维护性 |

---

## 二、架构层面优化（Phase 1：消除自造轮子，对齐 Hermes 原生）

### 2.1 消除镜像重复 → plugin_core.py 单一代码源

```
当前:
  hermes-plugin/__init__.py (972行) ← 完全镜像
  src/evolution/_plugin/__init__.py (936行) ← 完全镜像
  合计 1908 行，872 行重复

目标:
  src/evolution/plugin_core.py (~900行) ← 单一代码源
  hermes-plugin/__init__.py (3行) → from evolution.plugin_core import register
  src/evolution/_plugin/__init__.py (3行) → 同上
  净删除 ~900 行
```

### 2.2 统一 _get_data_dir() → db_utils 唯一定义

删除 hermes-plugin 和 _plugin 中的重复实现，统一导入 `from evolution.db_utils import get_data_dir`。

### 2.3 统一 WAL checkpoint → db_utils.auto_checkpoint_if_needed()

删除 plugin 中的 `_checkpoint_associations_db()` 简化版（裸 sqlite3.connect），全部改用 db_utils 的完整版本。

### 2.4 工具注册对齐 Hermes registry.register()

```python
from tools.registry import registry

for tool_name, schema, handler in EVOLUTION_TOOLS:
    registry.register(
        name=tool_name,
        toolset="evolution",
        schema=schema,
        handler=handler,
    )
```

收益：`hermes tools enable/disable evolution` 管理，`hermes mcp serve` 自动暴露。

---

## 三、基础设施层优化（Phase 2：DatabasePool + Schema + 输入验证）

### 3.1 DatabasePool 统一连接池

> 吸收外部方案 db_pool.py 设计，替代当前 db_utils 的简单字典缓存。

```python
# src/evolution/db_pool.py

class DatabasePool:
    """
    统一数据库连接池。
    
    相比当前 db_utils 的字典缓存：
    - contextmanager 保证不泄露连接（解决 22 处 conn.close() 泛滥）
    - 连接健康检查 + 自动重建
    - 统一 WAL checkpoint 调度
    - 禁止 conn.close()——close() 是 NOP，连接由池管理
    """
    
    @contextmanager
    def connection(self, db_name: str):
        conn = self._get_connection(db_name)
        try:
            yield conn
        finally:
            pass  # 不关闭，归还池
    
    def checkpoint_all(self, max_wal_mb: int = 100):
        """对所有数据库执行 WAL checkpoint"""
        ...
    
    def close(self):
        """进程退出时统一关闭"""

db_pool = DatabasePool()
```

**迁移策略**：保持 db_utils 兼容，新增 db_pool，逐步替换调用方。

### 3.2 统一 Schema 版本化管理

```python
# src/evolution/schema.py

MIGRATIONS = {
    1: {
        "tools.db": ["CREATE TABLE IF NOT EXISTS tools (...)", ...],
        "learning_experiences.db": [...],
        # ... 全部 7 个 DB
    }
}

def ensure_schema(db_name: str, target_version: int = 1):
    """确保数据库 schema 版本正确，自动执行迁移"""
```

### 3.3 输入验证层

```python
# src/evolution/security/input_validator.py

class InputValidator:
    validate_tool_name(name) → ValidationResult
    validate_db_path(path) → ValidationResult
    validate_interval(seconds) → ValidationResult
    sanitize_error_message(error) → str  # 脱敏路径信息
```

### 3.4 消除硬编码敏感信息

```python
# 飞书 App ID 从硬编码默认值改为环境变量强制要求
"app_id": os.environ.get("FEISHU_APP_ID", ""),
if not os.environ.get("FEISHU_APP_ID"):
    logger.warning("FEISHU_APP_ID 未配置，飞书通知将不可用")
```

---

## 四、核心引擎升级（Phase 3：状态机 + 记忆分层）

### 4.1 闭环编排状态机

> 当前是硬编码 Phase 1→2→3→4→5→6 线性链，不支持中断恢复。

```python
class Phase(Enum):
    IDLE = "idle"
    MONITOR = "monitor"
    ANALYZE = "analyze"
    PLAN = "plan"
    EXECUTE = "execute"
    VERIFY = "verify"
    FEEDBACK = "feedback"
    COMPLETED = "completed"
    FAILED = "failed"

# 状态转移矩阵
TRANSITIONS = {
    Phase.IDLE:      {Phase.MONITOR},
    Phase.MONITOR:   {Phase.ANALYZE, Phase.FAILED},
    Phase.ANALYZE:   {Phase.PLAN, Phase.FAILED},
    Phase.PLAN:      {Phase.EXECUTE, Phase.FAILED, Phase.IDLE},
    Phase.EXECUTE:   {Phase.VERIFY, Phase.FAILED},
    Phase.VERIFY:    {Phase.FEEDBACK, Phase.FAILED},
    Phase.FEEDBACK:  {Phase.COMPLETED, Phase.FAILED},
    Phase.COMPLETED: {Phase.IDLE},
    Phase.FAILED:    {Phase.IDLE},
}

@dataclass
class CycleState:
    """可持久化的循环状态——崩溃后可恢复"""
    cycle_id: int
    current_phase: Phase
    phase_results: Dict[str, Any]
```

收益：崩溃后从上次 Phase 继续、ANALYZE 无问题可跳过 PLAN+EXECUTE、支持并行 Phase。

### 4.2 记忆分层管理

```
热记忆（L1）：最近使用、高频访问 → 内存 OrderedDict (LRU 1000)
温记忆（L2）：中等频率 → SQLite 主库
冷记忆（L3）：低频/过期 → 归档 .db，定期清理
```

---

## 五、DFX 优化（Phase 4：可靠性 + 性能 + 可观测性）

### 5.1 WAL Checkpoint 全覆盖

```python
ALL_EVOLUTION_DBS = [
    "associations.db", "tools.db", "learning_experiences.db",
    "tool_performance.db", "retrieval_optimization.db",
    "evolution_audit.db", "audit.db", "collaboration_messages.db"
]

# daemon 主循环每 5 轮调用
db_pool.checkpoint_all(max_wal_mb=100)

# 每个 handler 写入后调用
auto_checkpoint_if_needed(db_name, max_wal_mb=100)
```

### 5.2 启用 retry_on_db_error

为 5 个写入模块添加装饰器：AssociationDatabase、LearningObserver、ToolRegistry、ToolPerformanceAnalyzer、RetrievalOptimizer。

### 5.3 性能优化

| 优化项 | 当前 | 目标 |
|--------|------|------|
| N+1 查询 | 循环内逐条 UPDATE | 单事务批量 UPDATE |
| JSON 字段 | `json_extract` 在 WHERE 无索引 | 生成列 + 索引 |
| 全文搜索 | `LIKE '%keyword%'` 全表扫描 | SQLite FTS5 |
| 缓存 | dict 无淘汰 | OrderedDict LRU(1000) + TTL(60s) |
| 批量写入 | 逐条 INSERT+commit | executemany + 单事务 |

### 5.4 可观测性

- 健康检查接入 `hermes doctor` 框架
- `comprehensive_health_check()` 返回所有 DB 的 WAL 大小、内存使用、连接数
- 闭环执行链路追踪（trace_id + phase_timings）
- feishu_notifications.log 加 RotatingFileHandler(10MB×3)

---

## 六、实施路线图

```
Phase 1：架构重构（3天）
  ├── 消除镜像重复 → plugin_core.py
  ├── 统一 _get_data_dir / WAL checkpoint
  ├── 工具注册对齐 registry.register()
  └── 清理 _engine_instances 全局字典

Phase 2：基础设施（3天）
  ├── DatabasePool 连接池（替代裸连接 + close 泛滥）
  ├── Schema 版本化管理
  ├── 输入验证层
  └── 消除硬编码敏感信息

Phase 3：引擎升级（3天）
  ├── 闭环编排状态机
  └── 记忆分层管理

Phase 4：DFX 补齐（3天）
  ├── WAL checkpoint 全覆盖 + daemon 定期调度
  ├── retry_on_db_error 启用
  ├── N+1 消除 + FTS5 + JSON 索引 + LRU
  ├── 健康检查 + 链路追踪
  └── 日志轮转
```

**总计 12 天，4 个 Phase。**

---

## 七、代码改动预估

| 阶段 | 新增文件 | 修改文件 | 删除行 | 新增行 | 净变化 |
|------|----------|----------|--------|--------|--------|
| Phase 1 | 1 (plugin_core.py) | 3 | -1940 | +920 | **-1020** |
| Phase 2 | 2 (db_pool.py, input_validator.py) | 6 | -50 | +350 | **+300** |
| Phase 3 | 1 (schema.py) | 3 | -30 | +250 | **+220** |
| Phase 4 | 0 | 8 | -25 | +150 | **+125** |
| **合计** | **4** | **20** | **-2045** | **+1670** | **-375** |

---

## 八、与其他方案的关键区别

| 维度 | 旧 V4 方案 | 外部方案 | **本方案（合并版）** |
|------|-----------|---------|---------------------|
| 核心思路 | DFX 修补 | 架构升级 + DFX | **先对齐原生 → 架构升级 → DFX 补齐** |
| Hermes 原生对齐 | 未考虑 | 未考虑 | ✅ registry / MCP / doctor |
| 连接管理 | 修 close() | DatabasePool | ✅ DatabasePool（吸收外部方案） |
| 编排模式 | 未涉及 | 状态机 | ✅ 状态机（吸收外部方案） |
| 记忆管理 | LRU | 分层 | ✅ 分层（吸收外部方案） |
| Schema 管理 | 未涉及 | 版本化 DDL | ✅ 版本化（吸收外部方案） |
| 输入验证 | 未涉及 | 统一层 | ✅ 统一层（吸收外部方案） |
| 代码重复 | 修 | 修 | ✅ 消除镜像 + 统一 data_dir + checkpoint |
| 安全 | 未涉及 | 脱敏 + 签名 | ✅ 脱敏 + 签名（吸收外部方案） |
| 可观测性 | 健康检查 | 链路追踪 | ✅ 全面健康 + 链路追踪 |

# HermesAgentEvolution 架构文档

> **版本**: v3.0.6 (V1/V2/V3 融合架构)
> **融合模块版本**: fusion/__init__.py v1.0.0
> **Python**: ≥ 3.9
> **测试覆盖**: 439 passed
> **最后更新**: 2026-05-09

---

## 目录

1. [项目概述](#1-项目概述)
2. [closed_loop — 闭环进化子系统](#2-closed_loop--闭环进化子系统)
3. [collaboration — 协作子系统](#3-collaboration--协作子系统)
4. [fusion — 融合桥接层](#4-fusion--融合桥接层)
5. [learning — 学习子系统](#5-learning--学习子系统)
6. [memory — 记忆子系统](#6-memory--记忆子系统)
7. [security — 安全子系统](#7-security--安全子系统)
8. [tools — 工具子系统](#8-tools--工具子系统)
9. [services — 微服务层](#9-services--微服务层)
10. [utils — 工具模块](#10-utils--工具模块)
11. [数据流 — 闭环6阶段](#11-数据流--闭环6阶段)
12. [存储层](#12-存储层)
13. [部署架构](#13-部署架构)

---

## 1. 项目概述

### 1.1 定位

HermesAgentEvolution 是一个面向 AI Agent 的**自我进化框架**，运行在 Hermes Agent 运行时之上。核心使命：

- **自动学习**：从执行经验中提取模式，优化行为策略
- **自动创造**：根据需求动态生成、注册、组合工具
- **自动优化**：持续评估工具性能，淘汰低效工具，进化高效工具
- **自我监控**：监控自身行为，主动发起闭环改进
- **安全护航**：沙箱执行、RBAC权限、威胁检测、全面审计

### 1.2 融合架构理念

v3.0.6 采用 **V1/V2/V3 三位一体融合架构**。V1 是 `src/evolution/` 下的单体模块化子系统（10个子系统），V2 是 `src/services/` 下的微服务层，V3 通过 `fusion/` 桥接层将两者无缝集成。

```
┌──────────────────────────────────────────────────────────────────┐
│                     V3 融合架构 (HYBRID Mode)                      │
│                                                                   │
│  ┌─────────────────────┐          ┌──────────────────────────┐   │
│  │    V1 单体核心        │          │    V2 微服务体系          │   │
│  │  ┌───────────────┐  │          │  ┌────────────────────┐ │   │
│  │  │ tools/        │  │          │  │ ServiceManager     │ │   │
│  │  │ learning/     │  │  ◄══►   │  │ EventBus           │ │   │
│  │  │ memory/       │──┼──────────┼──│ ToolManager        │ │   │
│  │  │ security/     │  │  fusion/ │  │ LearningOrch.      │ │   │
│  │  │ collaboration/│  │  bridge  │  │ MonitoringService  │ │   │
│  │  │ closed_loop/  │  │          │  │ ConfigManager      │ │   │
│  │  └───────────────┘  │          │  └────────────────────┘ │   │
│  └─────────────────────┘          └──────────────────────────┘   │
│              │                              │                     │
│              └──────────┬───────────────────┘                     │
│                         ▼                                         │
│              ┌─────────────────────┐                              │
│              │  UnifiedAgent 统一入口│  ← 三种运行模式              │
│              │  V1_ONLY | V2_ONLY  │                              │
│              │  HYBRID (融合)       │                              │
│              └─────────────────────┘                              │
│                         │                                         │
│                         ▼                                         │
│              ┌─────────────────────┐                              │
│              │  ~/.hermes/data/     │  ← 统一数据层 (SQLite WAL)   │
│              │  evolution/*.db      │                              │
│              └─────────────────────┘                              │
└──────────────────────────────────────────────────────────────────┘
```

**统一入口** (`fusion/unified_entry.py` → `UnifiedAgent`) 支持三种模式：

| 模式 | 说明 |
|------|------|
| `V1_ONLY` | 纯 V1 单体模块，零外部依赖 |
| `V2_ONLY` | 纯 V2 微服务，适合分布式部署 |
| `HYBRID` | V1+V2 协同，自动检测可用模块，API 降级 |

### 1.3 10个子系统一览

| # | 子系统 | 目录 | 总行数 | 职责 |
|---|--------|------|--------|------|
| 1 | closed_loop | `closed_loop/` | ~2,413 | 6阶段闭环编排 + 守护进程 + 审计 |
| 2 | collaboration | `collaboration/` | ~2,078 | 多Agent注册/调度/编排/消息总线 |
| 3 | fusion | `fusion/` | ~2,095 | V1↔V2桥接 + 兼容层 + 统一入口 |
| 4 | learning | `learning/` | ~1,964 | 经验记录/分析 + 模式识别 + 策略学习 |
| 5 | memory | `memory/` | ~2,264 | 关联数据库 + 发现器 + 检索优化 |
| 6 | security | `security/` | ~2,174 | 审计日志/权限管理/沙箱执行/威胁检测 |
| 7 | tools | `tools/` | ~3,926 | 工具注册/创建/自动生成/性能分析/进化引擎 |
| 8 | services | `services/` | ~6,116 | EventBus/ServiceManager + 学习/工具/部署/监控服务 |
| 9 | utils | `utils/` | ~611 | 飞书通知(3种模式)/进度报告(每2小时) |
| 10 | 顶层模块 | `src/evolution/` | ~2,920 | main/daemon/CLI/self_monitor/db_utils/health |

---

## 2. closed_loop — 闭环进化子系统

**目录**: `src/evolution/closed_loop/` | **总行数**: ~2,413

闭环子系统是整个进化引擎的**指挥中心**，编排 Monitor→Analyze→Plan→Execute→Verify→Feedback 六阶段流程，并通过守护进程和审计器确保持续运行和历史可追溯。

### 2.1 核心类表

| 文件 | 行数 | 核心类 | 职责 |
|------|------|--------|------|
| `orchestrator.py` | 680 | `ClosedLoopOrchestrator` | 6阶段闭环编排、`ImprovementAction` 数据类 |
| `daemon.py` | 476 | `EvolutionDaemon` | 独立守护进程，自适应间隔(60s~3600s)，信号处理 |
| `metrics_collector.py` | 456 | `SystemMetricsCollector` | 系统指标采集（CPU/内存/工具性能/经验统计） |
| `action_executor.py` | 355 | `ActionExecutor` | 进化动作执行器（工具创建/优化/废弃/参数调优） |
| `evolution_auditor.py` | 446 | `EvolutionAuditor` | 迭代10新增，持久化记录每次进化周期的完整元数据 |

### 2.2 ClosedLoopOrchestrator — 闭环编排器

**文件**: `orchestrator.py` (680行)

连接所有子系统组件，执行完整的进化闭环。

```
构造: ClosedLoopOrchestrator(
    metrics_collector,     # SystemMetricsCollector → Phase 1 Monitor
    self_monitor,          # SelfMonitor → Phase 2 Analyze
    experience_analyzer,   # ExperienceAnalyzer → Phase 2 Analyze
    pattern_recognizer,    # PatternRecognizer → Phase 3 Plan
    strategy_learner,      # ToolStrategyLearner → Phase 3 Plan
    action_executor,       # ActionExecutor → Phase 4 Execute
    learning_observer,     # LearningObserver → Phase 6 Feedback
    tool_evolution_engine, # ToolEvolutionEngine (可选)
    config                 # 配置字典
)
```

**关键方法**:

| 方法 | 说明 |
|------|------|
| `monitor() → Dict` | Phase 1：采集系统指标，检测异常 |
| `analyze(metrics) → Dict` | Phase 2：分析指标，识别问题模式 |
| `plan(analysis) → List[ImprovementAction]` | Phase 3：生成改进计划（按优先级排序） |
| `execute(actions) → Dict` | Phase 4：执行改进动作 |
| `verify(results) → Dict` | Phase 5：验证执行效果 |
| `feedback(verification) → Dict` | Phase 6：记录经验，更新策略 |
| `run_full_cycle() → Dict` | 完整6阶段执行，含审计记录兜底 |

**性能阈值配置**:
- `success_rate_threshold`: 0.6 (成功率红线)
- `tool_performance_threshold`: 60.0 (工具性能及格线)
- `strategy_improvement_delta`: 0.1 (策略改进最小增量)

### 2.3 EvolutionDaemon — 进化守护进程

**文件**: `daemon.py` (476行)

独立运行的守护进程，驱动持续进化。**方案A架构**：守护进程与 Hermes Agent 松耦合，可脱离 Hermes 独立运行。

**关键方法**:

| 方法 | 说明 |
|------|------|
| `start()` | 启动守护进程，进入主循环 |
| `stop()` | 优雅停止，保存状态 |
| `get_status() → Dict` | 获取当前运行状态 |

**特性**:
- 自适应循环间隔: 60s ~ 3600s (根据系统状态动态调整)
- 信号处理: SIGINT/SIGTERM 优雅退出
- CLI 入口: `--daemon` (持续运行) / `--once` (单次) / `--dry-run` (空跑)
- 飞书通知回调 (可选)

### 2.4 EvolutionAuditor — 自进化审计器 (迭代10)

**文件**: `evolution_auditor.py` (446行) | **数据库**: `evolution_audit.db`

迭代10新增，持久化记录每次进化周期的完整元数据，支持历史趋势分析。

**数据库表**:

| 表 | 说明 |
|----|------|
| `evolution_cycles` | 每次进化周期: 6阶段状态、健康分变化、问题/动作/改进计数 |
| `evolution_actions` | 每个进化动作: 类型/目标/变更状态 |

**关键方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `record_cycle()` | `(result: Dict) → int` | 记录一次进化周期 |
| `record_action()` | `(action: Dict) → int` | 记录一个进化动作 |
| `query_cycles()` | `(limit, offset, status) → List[Dict]` | 查询历史周期 |
| `get_cycle_detail()` | `(cycle_id: int) → Dict` | 获取周期详情+关联动作 |
| `get_summary()` | `(days: int = 30) → Dict` | 获取汇总统计 |
| `get_latest_health_trend()` | `(count: int = 10) → List[Dict]` | 获取健康分趋势 |

---

## 3. collaboration — 协作子系统

**目录**: `src/evolution/collaboration/` | **总行数**: ~2,078

多 Agent 协作框架，提供 Agent 注册、任务分发、编排和消息总线。

### 3.1 核心类表

| 文件 | 行数 | 核心类 | 职责 |
|------|------|--------|------|
| `agent_registry.py` | 460 | `AgentRegistry` | Agent 注册/发现/健康检查 |
| `task_dispatcher.py` | 503 | `TaskDispatcher` | 任务分发/负载均衡/优先级排序 |
| `agent_orchestrator.py` | 568 | `AgentOrchestrator` | 多Agent协作编排/结果聚合 |
| `message_bus.py` | 547 | `CollaborationMessageBus` | Agent间消息传递/事件订阅 |

### 3.2 关键类详情

**AgentRegistry** — Agent 注册中心:

| 方法 | 说明 |
|------|------|
| `register_agent(agent_info)` | 注册 Agent 元数据 |
| `discover_agents(capabilities)` | 按能力发现 Agent |
| `health_check(agent_id)` | 检查 Agent 健康状态 |
| `list_all()` | 列出所有注册 Agent |

**TaskDispatcher** — 任务分发器:

| 方法 | 说明 |
|------|------|
| `dispatch(task, strategy)` | 按策略分发任务 |
| `get_load(agent_id)` | 获取 Agent 负载 |
| `rebalance()` | 负载再均衡 |

**AgentOrchestrator** — 编排器:

| 方法 | 说明 |
|------|------|
| `orchestrate(task)` | 编排多 Agent 协作 |
| `aggregate(results)` | 聚合多 Agent 结果 |
| `resolve_conflict(results)` | 冲突解决 |

**CollaborationMessageBus** — 消息总线:

| 方法 | 说明 |
|------|------|
| `publish(topic, message)` | 发布消息到主题 |
| `subscribe(topic, callback)` | 订阅主题 |
| `broadcast(message)` | 广播到所有 Agent |

---

## 4. fusion — 融合桥接层

**目录**: `src/evolution/fusion/` | **总行数**: ~2,095 | **版本**: v1.0.0

V1 单体模块与 V2 微服务之间的桥接层，实现三种运行模式的无缝切换。

### 4.1 核心类表

| 文件 | 行数 | 核心类 | 职责 |
|------|------|--------|------|
| `bridge.py` | 679 | `V1V2Bridge`, `ServiceMapping` | V1↔V2 事件转换/服务映射/数据格式转换/健康检查 |
| `compatibility.py` | 555 | `CompatibilityLayer`, `StatusMapper`, `VersionDetector`, `APIGateway`, `DegradationHandler` | 兼容层/状态映射/API网关/降级处理 |
| `unified_entry.py` | 861 | `UnifiedAgent`, `RunMode`, `CapabilityRequest`, `CapabilityResponse` | 统一入口，三种模式切换 |

### 4.2 V1V2Bridge — 融合桥

**文件**: `bridge.py` (679行)

核心功能:
- **事件转换**: V1 经验事件 ↔ V2 EventBus 消息 (自动推断类型和优先级)
- **服务映射**: 双向映射表 `SERVICE_MAP_V1_TO_V2` / `SERVICE_MAP_V2_TO_V1`
- **数据格式转换**: V1 dataclass ↔ V2 JSON/dict
- **健康检查**: V1 健康报告 → V2 服务状态列表

### 4.3 CompatibilityLayer — 兼容层

**文件**: `compatibility.py` (555行)

| 类 | 职责 |
|----|------|
| `CompatibilityLayer` | 整体兼容性管理，API 适配 |
| `StatusMapper` | 状态枚举双向映射 (V1 Status ↔ V2 Status) |
| `VersionDetector` | 自动检测 V1/V2 模块可用性 |
| `APIGateway` | 统一 API 入口，自动路由 |
| `DegradationHandler` | 部分模块不可用时的优雅降级 |

### 4.4 UnifiedAgent — 统一入口

**文件**: `unified_entry.py` (861行)

```python
class RunMode(Enum):
    V1_ONLY = "v1_only"    # 纯V1单体模块
    V2_ONLY = "v2_only"    # 纯V2微服务
    HYBRID = "hybrid"      # V1+V2协同，自动检测，API降级
```

**关键方法**:

| 方法 | 说明 |
|------|------|
| `detect_mode() → RunMode` | 自动检测可用模块，选择最佳模式 |
| `execute(request: CapabilityRequest) → CapabilityResponse` | 统一执行入口 |
| `get_status() → UnifiedStatusReport` | 获取融合状态报告 |

---

## 5. learning — 学习子系统

**目录**: `src/evolution/learning/` | **总行数**: ~1,964

从执行经验中提取模式、优化策略，实现 Agent 的持续学习与改进。

### 5.1 核心类表

| 文件 | 行数 | 核心类/枚举 | 职责 |
|------|------|-------------|------|
| `experience.py` | 153 | `Experience`, `ExperienceType`, `Outcome` | 经验数据模型 (6种类型 + 4种结果) |
| `observer.py` | 473 | `LearningObserver` | 经验观察与记录，持久化到 SQLite |
| `analyzer.py` | 273 | `ExperienceAnalyzer` | 近期经验分析，趋势识别 |
| `pattern_recognizer.py` | 606 | `PatternRecognizer` | 多维度模式识别 (时间/频率/关联) |
| `tool_strategy_learner.py` | 459 | `ToolStrategyLearner` | 工具使用策略学习 (迭代9新增持久化) |

### 5.2 Experience — 经验数据模型

**文件**: `experience.py` (153行)

```python
@dataclass
class Experience:
    id: str                     # UUID
    experience_type: ExperienceType  # 经验类型
    task_id: str                # 关联任务ID
    timestamp: datetime         # 时间戳
    description: str            # 描述
    context: Dict               # 上下文
    outcome: Outcome            # 结果
    metrics: Dict               # 性能指标
    lessons_learned: List[str]  # 学到的教训
    tags: List[str]             # 标签
    confidence: float = 0.5     # 置信度 (calculate_confidence())
```

**经验类型** `ExperienceType`:

| 值 | 说明 |
|----|------|
| `TOOL_USAGE` | 工具使用经验 |
| `REASONING` | 推理过程经验 |
| `PROBLEM_SOLVING` | 问题解决经验 |
| `ERROR_RECOVERY` | 错误恢复经验 |
| `PATTERN_RECOGNITION` | 模式识别经验 |
| `ADAPTATION` | 自适应经验 |

**结果类型** `Outcome`: `SUCCESS` / `PARTIAL_SUCCESS` / `FAILURE` / `UNCERTAIN`

### 5.3 LearningObserver — 学习观察器

**文件**: `observer.py` (473行) | **数据库**: `learning_experiences.db`

```python
LearningObserver(db_path: str = "learning_experiences.db")
```

**关键方法**:

| 方法 | 说明 |
|------|------|
| `record_experience(experience) → str` | 记录经验，返回ID |
| `get_recent_experiences(days, limit) → List[Experience]` | 获取近期经验 |
| `get_experiences_by_type(exp_type) → List[Experience]` | 按类型获取 |
| `get_statistics() → Dict` | 经验统计 (总数/类型分布/成功率等) |

### 5.4 ExperienceAnalyzer — 经验分析器

**文件**: `analyzer.py` (273行)

```python
ExperienceAnalyzer(observer: LearningObserver)
```

| 方法 | 说明 |
|------|------|
| `analyze_recent_experiences(days) → Dict` | 分析近期经验，发现趋势 |
| `identify_bottlenecks() → List[Dict]` | 识别性能瓶颈 |
| `get_improvement_suggestions() → List[str]` | 生成改进建议 |

### 5.5 PatternRecognizer — 模式识别器

**文件**: `pattern_recognizer.py` (606行)

多维度模式识别引擎，识别经验中的重复模式和关联。

| 方法 | 说明 |
|------|------|
| `recognize_patterns(experiences) → List[Pattern]` | 识别模式 |
| `detect_temporal_patterns()` | 时间维度模式 |
| `detect_frequency_patterns()` | 频率维度模式 |
| `detect_correlation_patterns()` | 关联维度模式 |

### 5.6 ToolStrategyLearner — 工具策略学习器 (迭代9)

**文件**: `tool_strategy_learner.py` (459行) | **数据库**: `tools.db` (共享)

**迭代9重大更新**: 新增 SQLite 持久化，`tool_usage_history` 表存储最近7天工具调用记录，启动时通过 `_load_from_db()` 重建内存状态。

```python
ToolStrategyLearner(db_path: str = "tools.db")
```

**关键方法**:

| 方法 | 说明 |
|------|------|
| `record_tool_usage(tool_name, success, execution_time, context)` | 记录工具使用 |
| `get_current_strategy(tool_name) → Dict` | 获取当前推荐策略 |
| `get_tool_performance_summary(tool_name) → Dict` | 获取工具性能摘要 |
| `_load_from_db()` | **(迭代9)** 从DB恢复状态 |
| `_count_tools_from_db()` | 统一使用 `get_evolution_db()` 连接 |

---

## 6. memory — 记忆子系统

**目录**: `src/evolution/memory/` | **总行数**: ~2,264

基于语义、时间、使用模式的关联发现和检索优化。

### 6.1 核心类表

| 文件 | 行数 | 核心类 | 职责 |
|------|------|--------|------|
| `database.py` | 420 | `AssociationDatabase` | 5表关联数据库 CRUD |
| `association_discoverer.py` | 813 | `AssociationDiscoverer` | 3种关联发现算法 |
| `association_optimizer.py` | 494 | `AssociationOptimizer` | 关联强度优化/衰减 |
| `retrieval_optimizer.py` | 537 | `RetrievalOptimizer` | 检索策略自优化 |

### 6.2 AssociationDatabase — 关联数据库

**文件**: `database.py` (420行) | **数据库**: `associations.db`

5张核心表:

| 表 | 说明 |
|----|------|
| `memory_entries` | 记忆条目 (内容/类型/hash/embedding/重要性/置信度) |
| `associations` | 关联关系 (源/目标/类型/强度/置信度/发现方式) |
| `association_discovery_logs` | 发现过程日志 |
| `association_usage_stats` | 使用统计 (关联引用追踪) |
| `association_patterns` | 关联模式 (模式类型/数据/置信度/是否活跃) |

**关键方法**:

| 方法 | 说明 |
|------|------|
| `add_memory_entry(content, content_type, metadata, tags) → str` | 添加记忆条目 |
| `add_association(source_id, target_id, type, strength, confidence) → int` | 添加关联 |
| `find_similar_memories(content, limit) → List[Dict]` | 相似记忆查找 |
| `get_related_memories(memory_id) → List[Dict]` | 获取关联记忆 |
| `save_experience(experience) → bool` | 保存经验 (兼容测试) |

### 6.3 AssociationDiscoverer — 关联发现器

**文件**: `association_discoverer.py` (813行)

3种发现算法:

| 算法 | 说明 |
|------|------|
| `semantic` | 基于内容的语义相似度分析 |
| `temporal` | 基于时间窗口的共现分析 |
| `usage_pattern` | 基于使用模式的关联挖掘 |

**关键方法**:

| 方法 | 说明 |
|------|------|
| `discover_all(methods) → Dict` | 全量关联发现 |
| `discover_for_entry(entry_id, methods) → Dict` | 单条目关联发现 |

### 6.4 RetrievalOptimizer — 检索优化器

**文件**: `retrieval_optimizer.py` (537行)

基于使用模式自动调整检索参数，优化检索效率和准确率。

---

## 7. security — 安全子系统

**目录**: `src/evolution/security/` | **总行数**: ~2,174

四层安全防护：审计日志、权限管理、沙箱执行、威胁检测。

### 7.1 核心类表

| 文件 | 行数 | 核心类 | 职责 |
|------|------|--------|------|
| `audit_logger.py` | 653 | `AuditLogger` | 审计日志 (自动轮转) |
| `permission_manager.py` | 436 | `PermissionManager` | RBAC 权限管理 |
| `sandbox_executor.py` | 505 | `SandboxExecutor` | 代码安全检查/沙箱执行 |
| `threat_detector.py` | 580 | `ThreatDetector` | 实时威胁检测 |

### 7.2 AuditLogger — 审计日志

**文件**: `audit_logger.py` (653行)

特性: 自动轮转 (按大小/时间)、结构化日志、操作溯源。

### 7.3 PermissionManager — 权限管理

**文件**: `permission_manager.py` (436行)

基于角色的访问控制 (RBAC)，支持细粒度权限定义。

### 7.4 SandboxExecutor — 沙箱执行器

**文件**: `sandbox_executor.py` (505行)

动态生成代码的安全检查与隔离执行，防止恶意代码注入。

### 7.5 ThreatDetector — 威胁检测器

**文件**: `threat_detector.py` (580行)

实时监控异常行为模式，主动识别潜在安全威胁。

---

## 8. tools — 工具子系统

**目录**: `src/evolution/tools/` | **总行数**: ~3,926

最庞大的子系统，涵盖工具的完整生命周期：创建 → 注册 → 使用 → 性能分析 → 进化 → 废弃。

### 8.1 核心类表

| 文件 | 行数 | 核心类 | 职责 |
|------|------|--------|------|
| `tool_registry.py` | 525 | `ToolRegistry`, `ToolDefinition`, `ToolCategory`, `ToolStatus` | 工具注册表 (SQLite CRUD) |
| `tool_creator.py` | 444 | `ToolCreator` | 基础工具创建器 |
| `enhanced_tool_creator.py` | 938 | `EnhancedToolCreator`, `CreationSource`, `ToolQuality` | 增强创建器 (6种创建源) |
| `tool_auto_generator.py` | 741 | `ToolAutoGenerator`, `GenerationStrategy` | 自动生成器 (4种策略) |
| `tool_integration.py` | 483 | `ToolEvolutionEngine`, `EvolutionConfig`, `ToolLearningIntegrator` | 进化引擎 |
| `tool_performance_analyzer.py` | 795 | `ToolPerformanceAnalyzer`, `PerformanceMetric` | 性能分析器 |

### 8.2 ToolRegistry — 工具注册表

**文件**: `tool_registry.py` (525行) | **数据库**: `tools.db`

```python
ToolRegistry(db_path: str = "tools.db")
```

**关键方法**: `register()` / `get()` / `list_all()` / `search()` / `update_usage_stats()` / `get_statistics()` / `delete()`

**辅助枚举**:
- `ToolCategory`: UTILITY / DATA_PROCESSING / FILE_OPERATION / NETWORK / AI / CUSTOM
- `ToolStatus`: ACTIVE / DEPRECATED / EXPERIMENTAL / DISABLED

### 8.3 EnhancedToolCreator — 增强工具创建器

**文件**: `enhanced_tool_creator.py` (938行)

**6种创建源**:

| 方式 | 方法 | 说明 |
|------|------|------|
| 函数创建 | `create_from_function()` | 从 Python 函数自动提取签名 |
| 代码字符串 | `create_from_code()` | 解析 Python 代码 |
| 描述生成 | `create_from_description()` | LLM 从自然语言生成 |
| 模板创建 | `create_from_template()` | 预设模板快速生成 |
| 克隆创建 | `create_from_existing()` | 克隆并修改现有工具 |
| 进化创建 | `create_from_evolution()` | 基于现有工具进化 |

**辅助枚举**: `CreationSource` (FUNCTION/CODE/DESCRIPTION/TEMPLATE/EVOLUTION/CLONE), `ToolQuality` (EXCELLENT/GOOD/FAIR/POOR)

### 8.4 ToolAutoGenerator — 自动生成器

**文件**: `tool_auto_generator.py` (741行)

**4种生成策略**: LLM_GENERATION / TEMPLATE_BASED / COMPOSITE / EVOLUTIONARY

### 8.5 ToolPerformanceAnalyzer — 性能分析器

**文件**: `tool_performance_analyzer.py` (795行) | **数据库**: `tool_performance.db`

```python
ToolPerformanceAnalyzer(registry: ToolRegistry, db_path: str = "tool_performance.db")
```

**核心类**: `PerformanceMetric`, `PerformanceLevel`, `PerformanceRecord`, `PerformanceAnalysis`, `ToolPerformanceSummary`

**关键方法**:

| 方法 | 说明 |
|------|------|
| `record_performance(tool_name, metric, value, metadata)` | 记录性能数据 |
| `analyze_tool_performance(tool_name, time_period) → ToolPerformanceSummary` | 分析单个工具 |
| `analyze_all_tools() → Dict[str, ToolPerformanceSummary]` | 批量分析 |
| `generate_performance_report(output_format) → str` | 生成报告 (json/text/html) |

### 8.6 ToolEvolutionEngine — 进化引擎

**文件**: `tool_integration.py` (483行)

编排工具进化周期：分析状态 → 识别优化目标 → 标记废弃 → 记录经验 → 生成报告。

---

## 9. services — 微服务层

**目录**: `src/services/` | **总行数**: ~6,116

V2 微服务体系，通过 fusion 层与 V1 协同。

### 9.1 服务结构

```
src/services/
├── core/
│   ├── events/event_bus.py          # 事件总线
│   ├── services/service_manager.py  # 服务管理器
│   └── config/config_manager.py     # 配置管理器
├── learning/
│   ├── meta/meta_learning_service.py    # 元学习服务
│   ├── reflection/reflection_service.py # 反思服务
│   └── reinforcement/rl_service.py      # 强化学习服务
├── tools/
│   ├── discovery/tool_discovery_service.py    # 工具发现服务
│   └── composition/tool_composition_service.py # 工具组合服务
└── system/
    ├── monitoring/monitoring_service.py  # 监控服务
    ├── deployment/deployment_service.py  # 部署服务
    └── testing/test_service.py           # 测试服务
```

### 9.2 核心服务

| 服务 | 说明 |
|------|------|
| `EventBus` | 事件发布/订阅，服务间解耦通信 |
| `ServiceManager` | 服务注册/发现/生命周期管理 |
| `ConfigManager` | 集中配置管理，环境变量覆盖 |

---

## 10. utils — 工具模块

**目录**: `src/utils/` | **总行数**: ~611

### 10.1 FeishuNotifier — 飞书通知器

**文件**: `feishu_notifier.py` (342行)

3种运行模式:

| 模式 | 说明 |
|------|------|
| `webhook` | 真实飞书 Webhook 通知 |
| `simulated` | 模拟模式 (日志输出) |
| `disabled` | 关闭通知 |

### 10.2 ProgressReporter — 进度报告器

**文件**: `progress_reporter.py` (269行)

每2小时自动生成进化进度报告。

---

## 11. 数据流 — 闭环6阶段

闭环进化流程由 `ClosedLoopOrchestrator` 编排，6个阶段依次执行：

```
┌─────────────────────────────────────────────────────────────────┐
│                    闭环进化数据流                                 │
│                                                                  │
│  Phase 1: Monitor (系统指标采集)                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ SystemMetricsCollector → CPU/内存/工具性能/经验统计        │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          ▼                                       │
│  Phase 2: Analyze (分析诊断)                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ SelfMonitor + ExperienceAnalyzer → 问题识别/趋势分析       │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          ▼                                       │
│  Phase 3: Plan (规划)                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ PatternRecognizer + ToolStrategyLearner → 改进计划生成     │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          ▼                                       │
│  Phase 4: Execute (执行)                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ActionExecutor + ToolEvolutionEngine → 执行改进动作        │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          ▼                                       │
│  Phase 5: Verify (验证)                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 指标对比 → 验证改进效果 → 回滚机制                          │   │
│  └───────────────────────┬──────────────────────────────────┘   │
│                          ▼                                       │
│  Phase 6: Feedback (反馈)                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ LearningObserver → 记录经验 → 更新策略 → 审计记录          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                          │                                       │
│                          ▼ (循环回到 Phase 1)                    │
└─────────────────────────────────────────────────────────────────┘
```

**循环驱动方式**:
- **守护进程模式**: `EvolutionDaemon` 持续循环，自适应间隔 (60s~3600s)
- **手动触发模式**: 通过 `evolution_run_cycle` 工具单次触发
- **Hook 驱动**: `post_tool_call` Hook 在每次工具执行后自动收集数据

---

## 12. 存储层

### 12.1 数据库清单

所有数据库位于 `~/.hermes/data/evolution/` (可通过 `EVOLUTION_DATA_DIR` 环境变量覆盖)。

| # | 数据库文件 | 所属模块 | 表数 | 说明 |
|---|-----------|----------|------|------|
| 1 | `tools.db` | tools (ToolRegistry) / learning (ToolStrategyLearner) | 2+ | 工具定义 + `tool_usage_history` |
| 2 | `tool_performance.db` | tools (ToolPerformanceAnalyzer) | 1+ | 工具性能指标记录 |
| 3 | `learning_experiences.db` | learning (LearningObserver) | 1+ | 经验/学习记录 |
| 4 | `associations.db` | memory (AssociationDatabase) | 5 | 记忆条目/关联/日志/统计/模式 |
| 5 | `retrieval_optimization.db` | memory (RetrievalOptimizer) | 1+ | 检索策略优化数据 |
| 6 | `closed_loop.db` | closed_loop | 1+ | 闭环进化状态 |
| 7 | `evolution_audit.db` | closed_loop (EvolutionAuditor) | 2 | `evolution_cycles` + `evolution_actions` |

### 12.2 连接管理

**文件**: `db_utils.py` (235行)

所有模块通过 `get_evolution_db(db_name)` 获取连接，禁止裸 `sqlite3.connect()`。

**连接特性**:
- **WAL 模式**: 读不阻塞写，写不阻塞读
- **busy_timeout**: 30s 忙等重试
- **synchronous=NORMAL**: WAL 下性能优化
- **cache_size**: 8MB
- **foreign_keys=ON**: 外键约束
- **check_same_thread=False**: 跨线程安全
- **连接缓存**: 线程安全的进程内复用

**重试装饰器**: `@retry_on_db_error(max_attempts=3)` 指数退避 (2s→4s→8s，上限30s)

---

## 13. 部署架构

### 13.1 守护进程 + 插件双层架构 (方案A)

```
┌──────────────────────────────────────────────────────────────────┐
│                     Hermes Agent 运行时                           │
│  ┌─────────┐  ┌──────────────┐  ┌───────────┐  ┌────────────┐  │
│  │   LLM   │  │  Tool Router │  │  Plugins  │  │   Hooks    │  │
│  └────┬────┘  └──────┬───────┘  └─────┬─────┘  └─────┬──────┘  │
│       │              │                │               │         │
│       │              │    ┌───────────┴───────────────┘         │
│       │              │    │                                     │
│       │              ▼    ▼                                     │
│       │   ┌─────────────────────────────────────┐              │
│       │   │  _plugin/__init__.py (薄层)          │              │
│       │   │  ┌───────────────────────────────┐  │              │
│       │   │  │  6 Tools + 1 Hook              │  │              │
│       │   │  │  register(ctx) 按需懒加载       │  │              │
│       │   │  └───────────────┬───────────────┘  │              │
│       │   └──────────────────┼──────────────────┘              │
│       │                      │                                  │
│       │                      ▼                                  │
│       │   ┌─────────────────────────────────────┐              │
│       │   │  HermesAgentEvolution Engine         │              │
│       │   │  10个子系统 + 7个DB                   │              │
│       │   └──────────────────┬──────────────────┘              │
│       │                      │                                  │
└───────┼──────────────────────┼──────────────────────────────────┘
        │                      │
        │      共享 SQLite 数据库 (松耦合)
        │                      │
┌───────┼──────────────────────┼──────────────────────────────────┐
│       │    EvolutionDaemon (独立守护进程)                         │
│       │    python -m evolution.cli --daemon                      │
│       │    • 自适应循环间隔 (60s~3600s)                           │
│       │    • 飞书通知回调 (可选)                                  │
│       │    • 可脱离 Hermes 独立运行                               │
└───────┴──────────────────────────────────────────────────────────┘
```

### 13.2 日志层级

| Logger 名 | 对应模块 |
|-----------|----------|
| `hermes_evo.tools` | 工具子系统 |
| `hermes_evo.learning` | 学习子系统 |
| `hermes_evo.memory` | 记忆子系统 |
| `hermes_evo.security` | 安全子系统 |
| `hermes_evo.collaboration` | 协作子系统 |
| `hermes_evo.closed_loop` | 闭环子系统 |
| `hermes_evo.services` | 微服务层 |
| `hermes_evo.utils` | 工具模块 |
| `hermes_evo.plugin` | 插件层 |

---

*HermesAgentEvolution v3.0.6 — 让 AI Agent 从经验中持续自我进化*

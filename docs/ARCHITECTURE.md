# HermesAgentEvolution 架构概述

> 版本: v3.0.0 (V1/V2/V3 融合架构 — 单体+微服务混合)
> 最后更新: 2026-05-06

---

## 目录

1. [项目定位](#1-项目定位)
2. [整体架构概览](#2-整体架构概览)
3. [核心模块详解](#3-核心模块详解)
4. [数据流](#4-数据流)
5. [模块依赖关系](#5-模块依赖关系)
6. [存储层](#6-存储层)
7. [架构演进路线](#7-架构演进路线)

---

## 1. 项目定位

HermesAgentEvolution 是一个面向 AI Agent 的**自我进化框架**，核心使命是让 Agent 能够：

- **自动学习**：从执行经验中提取模式，优化行为策略
- **自动创造**：根据需求动态生成、注册、组合工具
- **自动优化**：持续评估工具性能，淘汰低效工具，进化高效工具
- **自我监控**：监控自身行为，主动发起改进计划

### 关键目标

| 维度 | 目标 |
|------|------|
| 学习机制 | 模式识别 + 策略学习 + 经验分析 |
| 工具系统 | 动态创建、注册、性能分析、自动生成 |
| 记忆系统 | 关联发现 + 向量检索 + 策略优化 |
| 架构设计 | 模块化、可扩展、事件驱动(规划中) |

---

## 2. 整体架构概览

### 2.1 架构层次

```
┌──────────────────────────────────────────────────────────────┐
│                     外部接口层                                │
│  ToolEvolutionEngine      SelfMonitor      LearningObserver  │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│                     工具能力层 (tools/)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ToolRegistry│  │ToolCreator│  │Enhanced │  │Perf.    │    │
│  │ (注册表)  │  │(创建器)  │  │ToolCreator│  │Analyzer │    │
│  └──────────┘  └──────────┘  │(增强创建) │  │(性能分析)│    │
│                              └──────────┘  └──────────┘    │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │AutoGen.  │  │ToolLearning  │  │ToolEvolution │          │
│  │(自动生成)│  │Integrator    │  │Engine (引擎) │          │
│  └──────────┘  └──────────────┘  └──────────────┘          │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│                     学习能力层 (learning/)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │Learning  │  │Experience│  │Pattern   │  │Experience│    │
│  │Observer  │  │Analyzer  │  │Recognizer│  │(数据类)  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘    │
│  ┌──────────────────────┐                                   │
│  │ToolStrategyLearner   │  (工具策略学习器)                   │
│  └──────────────────────┘                                   │
└──────────────────────────────────────────────────────────────┘
                              │
┌──────────────────────────────────────────────────────────────┐
│                   记忆 / 底层 (memory/)                       │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────┐  │
│  │AssociationDB │  │Association       │  │Retrieval    │  │
│  │(数据库封装)  │  │Discoverer(发现器)│  │Optimizer    │  │
│  └──────────────┘  └──────────────────┘  └──────────────┘  │
│  ┌──────────────┐                                           │
│  │Association   │  (记忆关联优化器)                          │
│  │Optimizer     │                                           │
│  └──────────────┘                                           │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 架构哲学

- **分层职责**：每一层有明确的职责边界，上层依赖下层接口
- **可选集成**：学习系统模块是可选加载的，缺失时不影响工具系统基础功能
- **事件驱动演进**：规划中的 v2 目标采用事件驱动微服务架构
- **数据驱动进化**：所有进化决策基于实际使用数据（性能指标、经验分析）

---

## 3. 核心模块详解

### 3.1 工具注册表 (`ToolRegistry`)

**文件**: `src/evolution/tools/tool_registry.py`

核心数据管理组件，基于 SQLite 实现工具的持久化存储。

**核心类**:

| 类名 | 职责 |
|------|------|
| `ToolDefinition` | 工具定义数据类，包含名称、描述、类别、状态、参数等 |
| `ToolRegistry` | 工具注册表，提供 CRUD + 搜索 + 统计 |
| `ToolCategory` | 工具类别枚举 (utility, data_processing, file_operation, network, ai, custom) |
| `ToolStatus` | 工具状态枚举 (active, deprecated, experimental, disabled) |

**关键方法**:

| 方法 | 说明 |
|------|------|
| `register(tool)` | 注册或更新工具（同名自动更新） |
| `get(name)` | 按名称获取工具定义 |
| `list_all(category, status, tag)` | 按条件列出工具 |
| `search(query)` | 模糊搜索工具（名称/描述/标签） |
| `update_usage_stats(name, success)` | 更新使用统计 |
| `get_statistics()` | 获取全局统计信息 |
| `delete(name)` | 删除工具 |

**存储**: SQLite 数据库，支持文件路径和 `:memory:` 模式。

### 3.2 工具创建器 (`ToolCreator` / `EnhancedToolCreator`)

**文件**: `src/evolution/tools/tool_creator.py`, `src/evolution/tools/enhanced_tool_creator.py`

`ToolCreator` 是基础创建器，`EnhancedToolCreator` 在其基础上支持 6 种创建方式。

**6 种创建方式**:

| 方式 | 方法 | 说明 |
|------|------|------|
| 1. 函数创建 | `create_from_function()` | 从 Python 函数自动提取签名和文档创建工具 |
| 2. 代码字符串 | `create_from_code()` | 解析 Python 代码字符串创建工具 |
| 3. 描述生成 | `create_from_description()` | 通过 LLM 从自然语言描述生成工具代码 |
| 4. 模板创建 | `create_from_template()` | 使用预设模板快速生成工具 |
| 5. 克隆创建 | `create_from_existing()` | 克隆现有工具并修改 |
| 6. 进化创建 | `create_from_evolution()` | 基于现有工具进化生成新版本 |

**辅助类**:

- `CreationSource`: 创建来源枚举 (FUNCTION, CODE, DESCRIPTION, TEMPLATE, EVOLUTION, CLONE)
- `ToolQuality`: 工具质量评级 (EXCELLENT, GOOD, FAIR, POOR)
- `CodeAnalysisResult`: 代码分析结果

### 3.3 性能分析器 (`ToolPerformanceAnalyzer`)

**文件**: `src/evolution/tools/tool_performance_analyzer.py`

持续监控和评估工具执行性能。

**核心功能**:

- **性能记录**: 记录每次工具执行的耗时、成功/失败、资源消耗
- **性能分析**: 计算综合性能评分、识别性能瓶颈
- **趋势分析**: 检测性能变化趋势（提升/下降）
- **优化建议**: 基于分析结果生成优化建议

**关键类**:

| 类 | 说明 |
|----|------|
| `PerformanceMetric` | 性能指标枚举 (EXECUTION_TIME, SUCCESS_RATE, ERROR_RATE, RESOURCE_USAGE 等) |
| `PerformanceLevel` | 性能等级枚举 (EXCELLENT, GOOD, FAIR, POOR, CRITICAL) |
| `PerformanceRecord` | 单次性能记录数据类 |
| `PerformanceAnalysis` | 完整性能分析结果 |
| `ToolPerformanceSummary` | 工具性能摘要 |
| `ToolPerformanceAnalyzer` | 性能分析器主类 |

**装饰器**:
- `@monitor_performance`: 用于装饰工具函数，自动记录执行性能

### 3.4 自动生成器 (`ToolAutoGenerator`)

**文件**: `src/evolution/tools/tool_auto_generator.py`

根据需求描述自动生成工具代码。

**生成策略**:

| 策略 | 说明 |
|------|------|
| `LLM_GENERATION` | 基于 LLM 从需求生成代码 |
| `TEMPLATE_BASED` | 基于模板匹配生成 |
| `COMPOSITE` | 组合多个现有工具生成新工具 |
| `EVOLUTIONARY` | 基于现有工具进化生成 |

**核心类**:
- `GenerationStrategy`: 生成策略枚举
- `ToolGenerationResult`: 生成结果（含代码、验证状态、警告）
- `ToolAutoGenerator`: 自动生成器主类

### 3.5 工具进化引擎 (`ToolEvolutionEngine`)

**文件**: `src/evolution/tools/tool_integration.py`

将工具能力进化与学习系统集成的核心模块。

**核心组件**:

| 组件 | 职责 |
|------|------|
| `EvolutionConfig` | 进化配置（进化间隔、性能阈值、学习集成开关等） |
| `EvolutionStatus` | 进化状态枚举 (IDLE, ANALYZING, EVOLVING, OPTIMIZING, COMPLETED, FAILED) |
| `ToolLearningIntegrator` | 工具与学习系统的桥梁，负责记录经验、分析模式、优化策略 |
| `ToolEvolutionEngine` | 进化引擎主类，编排整个进化周期 |

**进化周期** (`run_evolution_cycle`):

```
① 分析当前状态
  └─ 获取所有工具性能摘要
  └─ 分析工具分布（类别/状态）
  └─ 获取学习模式识别结果
      │
② 识别需要优化的工具
  └─ 检查性能评分 < 阈值 → 标记需优化
  └─ 触发学习系统优化策略
      │
③ 识别需要废弃的工具
  └─ 已弃用标记的工具
  └─ 禁用且零使用的非内置工具
      │
④ 记录学习经验
  └─ 将进化操作记录到学习系统
      │
⑤ 生成进化报告
  └─ 状态摘要 + 性能概览 + 进化历史
```

### 3.6 学习能力模块

#### 3.6.1 经验数据模型 (`Experience`)

**文件**: `src/evolution/learning/experience.py`

核心数据类，定义经验的结构。

**经验类型**:

| 类型 | 说明 |
|------|------|
| `TOOL_USAGE` | 工具使用经验 |
| `REASONING` | 推理过程经验 |
| `PROBLEM_SOLVING` | 问题解决经验 |
| `ERROR_RECOVERY` | 错误恢复经验 |
| `PATTERN_RECOGNITION` | 模式识别经验 |
| `ADAPTATION` | 适应调整经验 |

**结果状态**: SUCCESS, PARTIAL_SUCCESS, FAILURE, UNCERTAIN

经验对象包含：上下文、操作序列、推理步骤、指标、学到的教训、置信度和重要性评分。

#### 3.6.2 学习观察器 (`LearningObserver`)

**文件**: `src/evolution/learning/observer.py`

负责经验的持久化存储、查询和分析。

**能力**:
- 记录经验到 SQLite 数据库
- 按类型、任务、结果、标签、时间范围查询
- 统计信息汇总（总数、按类型/结果分布、平均置信度）
- 学习模式分析（每日成功率趋势、工具使用频率）
- 数据导出（JSON / CSV 格式）

#### 3.6.3 经验分析器 (`ExperienceAnalyzer`)

**文件**: `src/evolution/learning/analyzer.py`

分析经验数据，识别模式，生成改进建议。

**核心产出**:
- `AnalysisResult`: 包含成功率、识别到的模式、关键洞察、改进建议
- `PatternInstance`: 模式实例（成功模式/失败模式，含置信度和频率）

#### 3.6.4 模式识别器 (`PatternRecognizer`)

**文件**: `src/evolution/learning/pattern_recognizer.py`

从经验数据中识别高级模式并生成优化策略。

**模式类别**:

| 类别 | 说明 |
|------|------|
| `TEMPORAL_PATTERN` | 时间维度模式 |
| `SEQUENTIAL_PATTERN` | 序列模式（工具调用顺序） |
| `CONTEXTUAL_PATTERN` | 上下文相关模式 |
| `PERFORMANCE_PATTERN` | 性能模式 |
| `ERROR_PATTERN` | 错误模式 |

**策略类型**: PREVENTIVE, OPTIMIZATION, ADAPTIVE, RECOVERY

**核心类**:
- `RecognizedPattern`: 识别的模式（含置信度、支持度、条件、示例）
- `GeneratedStrategy`: 生成的优化策略（含期望收益、实现成本、优先级）

#### 3.6.5 工具策略学习器 (`ToolStrategyLearner`)

**文件**: `src/evolution/learning/tool_strategy_learner.py`

学习工具选择和执行策略，动态调整行为。

**策略类型**:

| 策略 | 行为 |
|------|------|
| `EFFICIENCY_OPTIMIZED` | 偏好执行时间短的工具 |
| `RELIABILITY_OPTIMIZED` | 偏好成功率高的工具 |
| `ACCURACY_OPTIMIZED` | 偏好准确性高的工具 |
| `ADAPTIVE` | 自适应动态切换 |

**核心机制**:
- **探索-利用平衡**: 探索率控制随机探索比例
- **策略切换**: 当另一个策略的评分显著优于当前策略时自动切换
- **置信度计算**: 根据策略类型动态调整工具推荐置信度

### 3.7 自我监控器 (`SelfMonitor`)

**文件**: `src/evolution/self_monitor.py`

协调学习能力进化系统的各个组件，执行端到端的监控-分析-改进循环。

**流程**:
1. 分析最近经验数据 (ExperienceAnalyzer)
2. 分析工具使用策略和性能 (ToolStrategyLearner)
3. 生成改进计划
4. 记录监控历史

### 3.8 记忆系统

**文件**: `src/evolution/memory/`

| 模块 | 文件 | 职责 |
|------|------|------|
| `AssociationDatabase` | `database.py` | SQLite 数据库封装，管理记忆条目、关联关系、使用统计 |
| `AssociationDiscoverer` | `association_discoverer.py` | 自动发现记忆关联（语义/时间/使用模式） |
| `AssociationOptimizer` | `association_optimizer.py` | 优化关联结构，清理弱关联 |
| `RetrievalOptimizer` | `retrieval_optimizer.py` | 优化记忆检索策略 |

---

## 4. 数据流

### 4.1 工具进化周期数据流

```
用户/系统
   │
   ▼
ToolEvolutionEngine.run_evolution_cycle()
   │
   ├─→ ToolRegistry.list_all()           ← 获取所有工具
   │
   ├─→ ToolPerformanceAnalyzer.analyze() ← 分析性能
   │
   ├─→ ToolLearningIntegrator            ← 学习系统集成
   │    ├─→ PatternRecognizer.recognize()
   │    ├─→ ToolStrategyLearner.learn()
   │    └─→ ExperienceAnalyzer.analyze()
   │
   ├─→ EnhancedToolCreator               ← 创建/进化工具
   │
   └─→ LearningObserver.record()         ← 记录经验
```

### 4.2 工具创建数据流

```
需求描述
   │
   ▼
ToolAutoGenerator.generate_from_requirement()
   │
   ├─→ [LLM生成] / [模板匹配] / [组合] / [进化]
   │
   ▼
ToolGenerationResult (含代码)
   │
   ▼
EnhancedToolCreator.create_from_code()
   │
   ├─→ 代码分析 (语法/安全/质量)
   ├─→ ToolDefinition 构建
   ├─→ ToolRegistry.register()
   │
   ▼
注册成功 → 工具可用
```

### 4.3 经验学习数据流

```
工具执行
   │
   ▼
ToolLearningIntegrator.record_tool_execution()
   │
   ├─→ LearningObserver.record_experience()
   │    └─→ SQLite 持久化
   │
   ▼ (后续触发)
ExperienceAnalyzer.analyze_recent_experiences()
   │
   ├─→ 计算成功率趋势
   ├─→ 识别模式 (PatternRecognizer)
   ├─→ 生成改进建议
   │
   ▼
SelfMonitor.monitor_and_improve()
   │
   └─→ 改进计划 → 执行
```

---

## 5. 模块依赖关系

```
ToolEvolutionEngine
  ├── ToolRegistry
  ├── EnhancedToolCreator
  │     └── ToolCreator
  │           └── ToolRegistry
  ├── ToolPerformanceAnalyzer
  │     └── ToolRegistry
  ├── ToolAutoGenerator
  │     └── ToolRegistry
  └── ToolLearningIntegrator (可选)
        ├── LearningObserver
        ├── ExperienceAnalyzer
        │     └── LearningObserver
        ├── ToolStrategyLearner
        └── PatternRecognizer

LearningObserver
  └── Experience (数据类)

AssociationDiscoverer
  └── AssociationDatabase

SelfMonitor
  ├── LearningObserver
  ├── ExperienceAnalyzer
  └── ToolStrategyLearner
```

### 依赖规则

1. **tools/ 层不直接依赖 learning/ 层**——集成通过 `ToolLearningIntegrator` 桥接
2. **learning/ 层不依赖 memory/ 层**——学习经验存储在独立数据库
3. **memory/ 层完全独立**——可独立使用，无外部依赖
4. **学习系统可选**——`ToolEvolutionEngine` 在缺少学习模块时仍可正常工作

---

## 6. 存储层

| 数据库 | 用途 | 位置 |
|--------|------|------|
| `tools.db` | 工具注册表存储 | `data/tools.db` (可配置) |
| `tool_performance.db` | 工具性能记录 | `data/tool_performance.db` (可配置) |
| `learning_experiences.db` | 学习经验存储 | `data/learning_experiences.db` (自动创建) |
| `associations.db` | 记忆关联存储 | `data/associations.db` (可配置) |

所有存储均基于 **SQLite**，支持 `:memory:` 模式用于测试。

---

## 7. 架构演进路线

### V1 (当前实现 ✓)
- 单体模块化架构
- 基础工具注册和创建
- 简单的模式识别
- SQLite 持久化

### V2 (规划中)
- **事件驱动微服务架构**
- 异步高性能处理 (asyncio)
- 配置管理系统
- 完整可观测性 (Prometheus + 结构化日志 + 分布式追踪)
- 强化学习 + 元学习 + 反思机制
- 知识图谱 + 向量数据库
- 容器化部署 (Docker + Kubernetes)

### 关键改进领域

| 维度 | V1 (当前) | V2 (目标) |
|------|-----------|-----------|
| 学习机制 | 基础模式识别 | 强化学习 + 元学习 + 反思 |
| 工具系统 | 动态工具注册 | 工具发现 + 智能组合 |
| 记忆系统 | SQLite 存储 | 知识图谱 + 向量 DB |
| 部署方式 | 单机 | 容器化 + 分布式 |
| 监控 | 基础日志 | 完整可观测性 |

---

## 附录

- **API 参考**: [API_REFERENCE.md](API_REFERENCE.md)
- **安装指南**: [INSTALLATION.md](INSTALLATION.md)
- **移植指南**: [PORTING.md](PORTING.md)
- **V2 详细设计**: [ARCHITECTURE_V2.md](ARCHITECTURE_V2.md)
- **优化总结**: [ARCHITECTURE_OPTIMIZATION_SUMMARY.md](ARCHITECTURE_OPTIMIZATION_SUMMARY.md)

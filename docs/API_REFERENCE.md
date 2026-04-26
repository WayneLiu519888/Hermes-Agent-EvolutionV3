# HermesAgentEvolution API 参考

> 版本: v2 (Iteration 3)
> 最后更新: 2026-04-24

---

## 目录

1. [tools 包](#1-tools-包)
2. [learning 包](#2-learning-包)
3. [memory 包](#3-memory-包)
4. [self_monitor 模块](#4-self_monitor-模块)

---

## 1. tools 包

**导入路径**: `src.evolution.tools`

### 1.1 tool_registry.py

#### 枚举类

```python
class ToolCategory(Enum)
```
工具类别。

| 值 | 说明 |
|-----|------|
| `UTILITY` | 实用工具 |
| `DATA_PROCESSING` | 数据处理 |
| `FILE_OPERATION` | 文件操作 |
| `NETWORK` | 网络操作 |
| `AI` | AI 相关 |
| `CUSTOM` | 自定义 |

```python
class ToolStatus(Enum)
```
工具状态。

| 值 | 说明 |
|-----|------|
| `ACTIVE` | 活跃可用 |
| `DEPRECATED` | 已弃用 |
| `EXPERIMENTAL` | 实验性 |
| `DISABLED` | 已禁用 |

#### 数据类

```python
@dataclass
class ToolDefinition
```
工具定义。

| 字段 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | `str` | — | 工具名称 (必填) |
| `description` | `str` | — | 工具描述 (必填) |
| `category` | `ToolCategory` | — | 工具类别 (必填) |
| `status` | `ToolStatus` | `ACTIVE` | 工具状态 |
| `version` | `str` | `"1.0.0"` | 版本号 |
| `author` | `str` | `"system"` | 作者 |
| `created_at` | `datetime` | `now()` | 创建时间 |
| `updated_at` | `datetime` | `now()` | 更新时间 |
| `usage_count` | `int` | `0` | 使用次数 |
| `success_count` | `int` | `0` | 成功次数 |
| `error_count` | `int` | `0` | 错误次数 |
| `parameters` | `Dict[str, Any]` | `{}` | 参数定义 |
| `return_type` | `str` | `"Any"` | 返回类型 |
| `dependencies` | `List[str]` | `[]` | 依赖项 |
| `tags` | `List[str]` | `[]` | 标签 |
| `source_code` | `str` | `""` | 源代码 |
| `is_builtin` | `bool` | `False` | 是否为内置工具 |

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `to_dict()` | `() -> Dict[str, Any]` | 转换为字典 |
| `from_dict(data)` | `classmethod -> ToolDefinition` | 从字典创建实例 |

#### 主类

```python
class ToolRegistry
```
工具注册表 — 基于 SQLite 的工具 CRUD 和搜索引擎。

**构造**:

```python
def __init__(self, db_path: str = "data/tools.db")
```

| 参数 | 说明 |
|------|------|
| `db_path` | 数据库文件路径。传 `":memory:"` 创建内存数据库 |

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `register(tool)` | `(ToolDefinition) -> bool` | 注册或更新工具。同名自动更新，返回是否成功 |
| `get(name)` | `(str) -> Optional[ToolDefinition]` | 按名称获取工具定义 |
| `list_all(category, status, tag)` | `(Optional[str], Optional[str], Optional[str]) -> List[ToolDefinition]` | 按条件列出所有工具 |
| `search(query)` | `(str) -> List[ToolDefinition]` | 模糊搜索工具（名称/描述/标签） |
| `update_usage_stats(name, success)` | `(str, bool) -> None` | 更新工具使用统计 |
| `delete(name)` | `(str) -> bool` | 删除工具 |
| `get_statistics()` | `() -> Dict[str, Any]` | 获取全局统计信息 |

**`get_statistics()` 返回结构**:
```python
{
    "total_tools": int,          # 工具总数
    "by_category": dict,         # 按类别分布
    "by_status": dict,           # 按状态分布
    "total_usage": int,          # 总使用次数
    "total_success": int,        # 总成功次数
    "total_error": int,          # 总错误次数
    "recent_updates": list       # 最近更新的5个工具
}
```

---

### 1.2 tool_creator.py

```python
@dataclass
class ToolCreationResult
```
工具创建结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 是否成功 |
| `tool_definition` | `Optional[ToolDefinition]` | 创建的工具定义 |
| `error_message` | `str` | 错误信息 |
| `warnings` | `List[str]` | 警告列表 |

```python
class ToolCreator
```
基础工具创建器。

**构造**:
```python
def __init__(self, registry: Optional[ToolRegistry] = None)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `create_from_function(func, name, description, category, tags, is_builtin)` | `(Callable, ...) -> ToolCreationResult` | 从 Python 函数自动提取签名和文档创建工具 |
| `create_from_code(code, name, description, category, tags, is_builtin)` | `(str, ...) -> ToolCreationResult` | 从 Python 代码字符串创建工具 |
| `analyze_function(func)` | `(Callable) -> dict` | 分析函数签名和文档字符串 |

---

### 1.3 enhanced_tool_creator.py

```python
class CreationSource(Enum)
```
创建来源。

| 值 | 说明 |
|-----|------|
| `FUNCTION` | 从函数创建 |
| `CODE` | 从代码创建 |
| `DESCRIPTION` | 从描述创建 (LLM) |
| `TEMPLATE` | 从模板创建 |
| `EVOLUTION` | 进化创建 |
| `CLONE` | 克隆创建 |

```python
class ToolQuality(Enum)
```
工具质量评级。

| 值 | 说明 |
|-----|------|
| `EXCELLENT` | 优秀 |
| `GOOD` | 良好 |
| `FAIR` | 一般 |
| `POOR` | 较差 |

```python
@dataclass
class CodeAnalysisResult
```
代码分析结果。包含语法检查、安全分析、质量评分、复杂度指标等。

```python
class EnhancedToolCreator(ToolCreator)
```
增强型工具创建器 — 支持 6 种创建方式。

**额外方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `create_from_description(description, name, category)` | `(str, str, ToolCategory) -> ToolCreationResult` | 通过 LLM 从自然语言描述生成工具代码 |
| `create_from_template(template_name, params, name, category)` | `(str, dict, str, ToolCategory) -> ToolCreationResult` | 使用预设模板快速生成工具 |
| `create_from_existing(source_name, modifications, new_name)` | `(str, dict, str) -> ToolCreationResult` | 克隆现有工具并修改 |
| `create_from_evolution(source_name, evolution_goal)` | `(str, str) -> ToolCreationResult` | 基于现有工具进化生成新版本 |
| `analyze_code(code)` | `(str) -> CodeAnalysisResult` | 分析代码质量 |
| `validate_tool(tool)` | `(ToolDefinition) -> Tuple[bool, List[str]]` | 验证工具定义完整性 |
| `get_creation_stats()` | `() -> Dict[str, Any]` | 获取创建统计信息 |

---

### 1.4 tool_performance_analyzer.py

```python
class PerformanceMetric(Enum)
```
性能指标类型。

| 值 | 说明 |
|-----|------|
| `EXECUTION_TIME` | 执行时间 |
| `SUCCESS_RATE` | 成功率 |
| `ERROR_RATE` | 错误率 |
| `RESOURCE_USAGE` | 资源使用 |
| `RESPONSE_TIME` | 响应时间 |
| `THROUGHPUT` | 吞吐量 |
| `ACCURACY` | 准确性 |
| `RELIABILITY` | 可靠性 |

```python
class PerformanceLevel(Enum)
```
性能等级。

| 值 | 说明 |
|-----|------|
| `EXCELLENT` | 优秀 (≥90) |
| `GOOD` | 良好 (≥75) |
| `FAIR` | 一般 (≥60) |
| `POOR` | 较差 (≥40) |
| `CRITICAL` | 严重 (<40) |

```python
@dataclass
class PerformanceRecord
```
单次性能记录。包含指标名称、值、时间戳、上下文。

```python
@dataclass
class PerformanceAnalysis
```
性能分析结果。包含统计数据、趋势、异常、建议。

```python
@dataclass
class ToolPerformanceSummary
```
工具性能摘要。包含总体评分、性能等级、关键洞察、优化机会。

```python
class ToolPerformanceAnalyzer
```
工具性能分析器。

**构造**:
```python
def __init__(self, registry: ToolRegistry, db_path: str = "tool_performance.db")
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `record_performance(tool_name, metric, value, context)` | `(str, PerformanceMetric, float, Optional[Dict]) -> bool` | 记录性能数据点 |
| `analyze_tool_performance(tool_name)` | `(str) -> ToolPerformanceSummary` | 分析工具性能并生成摘要 |
| `get_performance_history(tool_name, metric, limit)` | `(str, Optional[PerformanceMetric], int) -> List[PerformanceRecord]` | 获取性能历史 |
| `get_low_performance_tools(threshold)` | `(float) -> List[str]` | 获取低于阈值性能的工具列表 |
| `get_trend(tool_name, metric)` | `(str, PerformanceMetric) -> str` | 获取性能趋势（上升/下降/稳定） |
| `compare_tools(tool_names)` | `(List[str]) -> Dict[str, ToolPerformanceSummary]` | 比较多个工具的性能 |

**装饰器**:
```python
@monitor_performance(analyzer: ToolPerformanceAnalyzer, tool_name: Optional[str] = None)
```
用于装饰工具函数，自动记录每次执行的性能数据。

---

### 1.5 tool_auto_generator.py

```python
class GenerationStrategy(Enum)
```
生成策略。

| 值 | 说明 |
|-----|------|
| `LLM_GENERATION` | 基于 LLM 从需求生成代码 |
| `TEMPLATE_BASED` | 基于模板匹配生成 |
| `COMPOSITE` | 组合多个现有工具生成新工具 |
| `EVOLUTIONARY` | 基于现有工具进化生成 |

```python
@dataclass
class ToolGenerationResult
```
工具生成结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | `bool` | 是否成功 |
| `tool_name` | `str` | 工具名称 |
| `tool_code` | `str` | 生成的工具代码 |
| `description` | `str` | 工具描述 |
| `generation_strategy` | `GenerationStrategy` | 使用的生成策略 |
| `warnings` | `List[str]` | 警告列表 |
| `validation_errors` | `List[str]` | 验证错误列表 |
| `metadata` | `Dict[str, Any]` | 元数据 |

```python
class ToolAutoGenerator
```
工具自动生成器。

**构造**:
```python
def __init__(self, registry: ToolRegistry)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `generate_from_requirement(requirement, strategy)` | `(str, Optional[GenerationStrategy]) -> ToolGenerationResult` | 根据需求描述自动生成工具 |
| `generate_from_template(template_name, params)` | `(str, Dict) -> ToolGenerationResult` | 基于模板生成工具 |
| `generate_composite_tool(component_tools, logic_description)` | `(List[str], str) -> ToolGenerationResult` | 组合现有工具生成新工具 |
| `evolve_tool(tool_name, improvement_goal)` | `(str, str) -> ToolGenerationResult` | 进化现有工具 |
| `validate_generated_code(code)` | `(str) -> Tuple[bool, List[str]]` | 验证生成的代码 |
| `list_available_templates()` | `() -> List[str]` | 列出可用模板 |

---

### 1.6 tool_integration.py

```python
class EvolutionConfig
```
进化配置。

**构造**:
```python
def __init__(
    self,
    auto_evolve: bool = True,
    evolution_interval: int = 3600,
    min_performance_score: float = 60.0,
    max_tool_age_days: int = 30,
    enable_auto_registration: bool = True,
    enable_performance_monitoring: bool = True,
    enable_optimization: bool = True,
    learning_integration_enabled: bool = True
)
```

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `auto_evolve` | `bool` | `True` | 是否自动进化 |
| `evolution_interval` | `int` | `3600` | 进化检查间隔（秒） |
| `min_performance_score` | `float` | `60.0` | 触发优化的最低性能分 |
| `max_tool_age_days` | `int` | `30` | 工具最大寿命（天） |
| `enable_auto_registration` | `bool` | `True` | 是否自动注册新工具 |
| `enable_performance_monitoring` | `bool` | `True` | 是否启用性能监控 |
| `enable_optimization` | `bool` | `True` | 是否启用优化 |
| `learning_integration_enabled` | `bool` | `True` | 是否集成学习系统 |

```python
class EvolutionStatus(Enum)
```
进化状态。

| 值 | 说明 |
|-----|------|
| `IDLE` | 空闲 |
| `ANALYZING` | 分析中 |
| `EVOLVING` | 进化中 |
| `OPTIMIZING` | 优化中 |
| `COMPLETED` | 完成 |
| `FAILED` | 失败 |

```python
class ToolLearningIntegrator
```
工具与学习系统集成器。

**构造**:
```python
def __init__(self, registry: ToolRegistry)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `record_tool_execution(tool_name, success, execution_time, error, context)` | `(str, bool, float, Optional[str], Optional[Dict]) -> bool` | 记录工具执行到学习系统 |
| `analyze_tool_patterns()` | `() -> List[Dict]` | 分析工具使用模式 |
| `optimize_tool_strategy(tool_name)` | `(str) -> Dict[str, Any]` | 优化工具使用策略 |
| `analyze_experience(tool_name)` | `(str) -> Dict[str, Any]` | 分析工具使用经验 |

```python
class ToolEvolutionEngine
```
工具进化引擎主类。

**构造**:
```python
def __init__(self, registry: Optional[ToolRegistry] = None, config: Optional[EvolutionConfig] = None)
```

**属性**:

| 属性 | 类型 | 说明 |
|------|------|------|
| `registry` | `ToolRegistry` | 工具注册表 |
| `config` | `EvolutionConfig` | 进化配置 |
| `enhanced_creator` | `EnhancedToolCreator` | 增强创建器 |
| `performance_analyzer` | `ToolPerformanceAnalyzer` | 性能分析器 |
| `auto_generator` | `ToolAutoGenerator` | 自动生成器 |
| `learning_integrator` | `ToolLearningIntegrator` | 学习集成器 |
| `status` | `EvolutionStatus` | 当前状态 |
| `evolution_history` | `List[Dict]` | 进化历史记录 |
| `last_evolution_time` | `Optional[datetime]` | 上次进化时间 |

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `analyze_current_state()` | `() -> Dict[str, Any]` | 分析当前工具系统状态 |
| `run_evolution_cycle()` | `() -> Dict[str, Any]` | 运行一次完整的进化周期 |
| `auto_generate_tool(requirement)` | `(str) -> ToolGenerationResult` | 自动生成工具 |
| `generate_evolution_report()` | `() -> str` | 生成进化报告文本 |
| `get_status_summary()` | `() -> Dict[str, Any]` | 获取状态摘要 |

---

## 2. learning 包

**导入路径**: `src.evolution.learning`

### 2.1 experience.py

```python
class ExperienceType(Enum)
```
经验类型。

| 值 | 说明 |
|-----|------|
| `TOOL_USAGE` | 工具使用经验 |
| `REASONING` | 推理过程经验 |
| `PROBLEM_SOLVING` | 问题解决经验 |
| `ERROR_RECOVERY` | 错误恢复经验 |
| `PATTERN_RECOGNITION` | 模式识别经验 |
| `ADAPTATION` | 适应调整经验 |

```python
class Outcome(Enum)
```
结果状态。

| 值 | 说明 |
|-----|------|
| `SUCCESS` | 成功 |
| `PARTIAL_SUCCESS` | 部分成功 |
| `FAILURE` | 失败 |
| `UNCERTAIN` | 不确定 |

```python
@dataclass
class Experience
```
经验数据类。

| 字段 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `id` | `str` | — | 经验 ID (必填) |
| `experience_type` | `ExperienceType` | — | 经验类型 (必填) |
| `task_id` | `str` | — | 任务 ID (必填) |
| `timestamp` | `datetime` | `now()` | 时间戳 |
| `description` | `str` | `""` | 描述 |
| `context` | `Dict[str, Any]` | `{}` | 上下文 |
| `actions` | `List[Dict]` | `[]` | 操作序列 |
| `reasoning_steps` | `List[str]` | `[]` | 推理步骤 |
| `outcome` | `Outcome` | `UNCERTAIN` | 结果 |
| `result` | `Optional[Any]` | `None` | 结果数据 |
| `metrics` | `Dict[str, float]` | `{}` | 指标 |
| `lessons_learned` | `List[str]` | `[]` | 学到的教训 |
| `tags` | `List[str]` | `[]` | 标签 |
| `confidence` | `float` | `0.0` | 置信度 |
| `importance` | `float` | `0.0` | 重要性 |

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `to_dict()` | `() -> Dict[str, Any]` | 转换为字典 |
| `from_dict(data)` | `classmethod -> Experience` | 从字典创建 |
| `to_json()` | `() -> str` | 转换为 JSON |
| `from_json(json_str)` | `classmethod -> Experience` | 从 JSON 创建 |
| `add_action(tool_name, parameters, result, duration)` | `(str, Dict, Any, float)` | 添加工具使用动作 |
| `add_reasoning_step(step)` | `(str)` | 添加推理步骤 |
| `add_lesson_learned(lesson)` | `(str)` | 添加经验教训 |
| `add_metric(name, value)` | `(str, float)` | 添加指标 |
| `add_tag(tag)` | `(str)` | 添加标签 |
| `calculate_confidence()` | `() -> float` | 计算置信度 (0-1) |

---

### 2.2 observer.py

```python
class LearningObserver
```
学习能力观察器 — 负责经验的持久化存储和查询。

**构造**:
```python
def __init__(self, db_path: Optional[str] = None)
```
默认数据库路径: `data/learning_experiences.db`

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `record_experience(experience)` | `(Experience) -> str` | 记录经验，返回经验 ID |
| `get_experience(experience_id)` | `(str) -> Optional[Experience]` | 获取经验 |
| `query_experiences(experience_type, task_id, outcome, tags, start_time, end_time, min_confidence, limit, offset)` | `(可选过滤参数) -> List[Experience]` | 查询经验 |
| `get_statistics()` | `() -> Dict[str, Any]` | 获取统计信息 |
| `analyze_learning_patterns(window_days)` | `(int) -> Dict[str, Any]` | 分析学习模式 |
| `export_experiences(file_path, format)` | `(str, str) -> bool` | 导出经验数据 (json/csv) |
| `clear_cache()` | `()` | 清空缓存 |

---

### 2.3 analyzer.py

```python
class AnalysisPatternType(Enum)
```
分析模式类型。

| 值 | 说明 |
|-----|------|
| `SUCCESS_PATTERN` | 成功模式 |
| `FAILURE_PATTERN` | 失败模式 |

```python
@dataclass
class PatternInstance
```
模式实例。

| 字段 | 类型 | 说明 |
|------|------|------|
| `pattern_type` | `AnalysisPatternType` | 模式类型 |
| `confidence` | `float` | 置信度 |
| `frequency` | `int` | 出现频率 |
| `description` | `str` | 描述 |
| `recommendations` | `List[str]` | 建议 |

```python
@dataclass
class AnalysisResult
```
分析结果。

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | `datetime` | 分析时间 |
| `total_experiences` | `int` | 总经验数 |
| `success_rate` | `float` | 成功率 |
| `identified_patterns` | `List[PatternInstance]` | 识别的模式 |
| `key_insights` | `List[str]` | 关键洞察 |
| `improvement_suggestions` | `List[str]` | 改进建议 |
| `summary` | `str` | 摘要 |

```python
class ExperienceAnalyzer
```
经验分析器。

**构造**:
```python
def __init__(self, observer: LearningObserver)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `analyze_recent_experiences(days)` | `(int = 7) -> AnalysisResult` | 分析最近 N 天的经验数据 |
| `analyze_experiences(experiences)` | `(List[Experience]) -> AnalysisResult` | 分析指定的经验列表 |

---

### 2.4 pattern_recognizer.py

```python
class PatternCategory(Enum)
```
模式类别。

| 值 | 说明 |
|-----|------|
| `TEMPORAL_PATTERN` | 时间模式 |
| `SEQUENTIAL_PATTERN` | 序列模式 |
| `CONTEXTUAL_PATTERN` | 上下文模式 |
| `PERFORMANCE_PATTERN` | 性能模式 |
| `ERROR_PATTERN` | 错误模式 |

```python
class StrategyType(Enum)
```
策略类型。

| 值 | 说明 |
|-----|------|
| `PREVENTIVE` | 预防性策略 |
| `OPTIMIZATION` | 优化策略 |
| `ADAPTIVE` | 适应性策略 |
| `RECOVERY` | 恢复策略 |

```python
@dataclass
class RecognizedPattern
```
识别的模式。

| 字段 | 类型 | 说明 |
|------|------|------|
| `pattern_id` | `str` | 模式 ID |
| `category` | `PatternCategory` | 类别 |
| `description` | `str` | 描述 |
| `confidence` | `float` | 置信度 |
| `support_count` | `int` | 支持度（出现次数） |
| `conditions` | `Dict[str, Any]` | 条件 |
| `examples` | `List[str]` | 示例 |
| `implications` | `List[str]` | 影响 |
| `discovered_at` | `datetime` | 发现时间 |

```python
@dataclass
class GeneratedStrategy
```
生成的策略。

| 字段 | 类型 | 说明 |
|------|------|------|
| `strategy_id` | `str` | 策略 ID |
| `strategy_type` | `StrategyType` | 策略类型 |
| `target_pattern` | `str` | 目标模式 |
| `description` | `str` | 描述 |
| `actions` | `List[str]` | 执行动作 |
| `expected_benefit` | `float` | 期望收益 |
| `implementation_cost` | `float` | 实现成本 |
| `priority` | `str` | 优先级 (high/medium/low) |
| `validation_status` | `str` | 验证状态 (pending/validated/rejected) |

```python
class PatternRecognizer
```
模式识别器。

**构造**:
```python
def __init__(self, min_support: int = 3, min_confidence: float = 0.7)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `recognize(experiences)` | `(List[Experience]) -> List[RecognizedPattern]` | 从经验中识别模式 |
| `generate_strategies(patterns)` | `(List[RecognizedPattern]) -> List[GeneratedStrategy]` | 从模式生成优化策略 |
| `validate_pattern(pattern)` | `(RecognizedPattern) -> bool` | 验证模式的有效性 |
| `get_patterns_by_category(category)` | `(PatternCategory) -> List[RecognizedPattern]` | 按类别获取模式 |

---

### 2.5 tool_strategy_learner.py

```python
class ToolStrategyType(Enum)
```
工具策略类型。

| 值 | 说明 |
|-----|------|
| `EFFICIENCY_OPTIMIZED` | 效率优先：偏好执行时间短的工具 |
| `RELIABILITY_OPTIMIZED` | 可靠性优先：偏好成功率高的工具 |
| `ACCURACY_OPTIMIZED` | 准确性优先：偏好准确性高的工具 |
| `ADAPTIVE` | 自适应：根据性能数据自动调整 |

```python
@dataclass
class ToolPerformance
```
工具性能数据。

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool_name` | `str` | 工具名称 |
| `success_count` | `int` | 成功次数 |
| `failure_count` | `int` | 失败次数 |
| `total_time` | `float` | 总执行时间 |
| `avg_time` | `float` | 平均执行时间 |
| `success_rate` | `float` | 成功率 |
| `last_used` | `Optional[datetime]` | 上次使用时间 |
| `usage_count` | `int` | 使用次数 |

```python
@dataclass
class ToolRecommendation
```
工具推荐。

| 字段 | 类型 | 说明 |
|------|------|------|
| `tool_name` | `str` | 工具名称 |
| `confidence` | `float` | 推荐置信度 |
| `reason` | `str` | 推荐原因 |
| `expected_efficiency` | `float` | 预期效率 |

```python
class ToolStrategyLearner
```
工具策略学习器。

**构造**:
```python
def __init__(self)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `record_tool_usage(tool_name, success, execution_time, context)` | `(str, bool, float, Optional[Dict])` | 记录工具使用情况 |
| `recommend_tool(task_description, available_tools, context)` | `(str, List[str], Optional[Dict]) -> List[ToolRecommendation]` | 推荐最合适的工具 |
| `get_current_strategy()` | `() -> ToolStrategyType` | 获取当前策略 |
| `get_strategy_performance()` | `() -> Dict[ToolStrategyType, StrategyPerformance]` | 获取所有策略的性能数据 |
| `get_tool_performance_summary()` | `() -> Dict[str, Dict]` | 获取工具性能摘要 |
| `learn_from_experiences(experiences)` | `(List[Dict])` | 从经验数据中学习 |

---

## 3. memory 包

**导入路径**: `src.evolution.memory`

### 3.1 database.py

```python
class AssociationDatabase
```
关联发现数据库。

**构造**:
```python
def __init__(self, db_path: str = "associations.db")
```

**表结构**:
- `memory_entries`: 记忆条目（ID、内容、类型、哈希、嵌入向量、元数据、标签等）
- `associations`: 关联关系（源ID、目标ID、类型、强度、置信度、发现方式）
- `association_discovery_logs`: 发现记录日志
- `association_usage_stats`: 使用统计
- `association_patterns`: 关联模式

### 3.2 association_discoverer.py

```python
class AssociationDiscoverer
```
记忆关联发现器。

**构造**:
```python
def __init__(
    self,
    db: AssociationDatabase,
    semantic_threshold: float = 0.15,
    temporal_window_seconds: int = 3600,
    usage_min_cooccurrence: int = 2
)
```

**支持的发现算法**:
- `semantic`: 基于内容文本的 Jaccard 相似度 + 长度相似度
- `temporal`: 基于时间邻近性
- `usage_pattern`: 基于共现分析

### 3.3 association_optimizer.py

关联优化器 — 清理弱关联、合并重复关联、更新关联强度。

### 3.4 retrieval_optimizer.py

检索优化器 — 优化记忆检索策略，提升查询效率。

---

## 4. self_monitor 模块

**文件**: `src/evolution/self_monitor.py`

```python
class SelfMonitor
```
自我监控器 — 协调学习能力进化系统的各个组件。

**构造**:
```python
def __init__(self, observer: LearningObserver, analyzer: ExperienceAnalyzer, strategy_learner: ToolStrategyLearner)
```

**方法**:

| 方法 | 签名 | 说明 |
|------|------|------|
| `monitor_and_improve()` | `() -> Dict[str, Any]` | 监控当前状态并生成改进计划 |
| `get_monitoring_history()` | `() -> List[Dict]` | 获取监控历史 |

**`monitor_and_improve()` 流程**:
1. 分析最近 7 天的经验数据
2. 分析工具使用策略和性能
3. 生成改进计划（含优先级排序）
4. 记录监控历史

---

## 附录: 导入路径速查

```python
# 工具包
from src.evolution.tools import (
    ToolDefinition, ToolRegistry, ToolCategory, ToolStatus,
    ToolCreator, ToolCreationResult,
    EnhancedToolCreator, CreationSource, ToolQuality, CodeAnalysisResult,
    ToolPerformanceAnalyzer, PerformanceMetric, PerformanceLevel,
    PerformanceRecord, PerformanceAnalysis, ToolPerformanceSummary,
    monitor_performance,
    ToolAutoGenerator, GenerationStrategy, ToolGenerationResult,
    ToolEvolutionEngine, ToolLearningIntegrator, EvolutionConfig, EvolutionStatus
)

# 学习包
from src.evolution.learning import (
    Experience, ExperienceType, Outcome,
    LearningObserver,
    ExperienceAnalyzer, AnalysisResult,
    PatternRecognizer, RecognizedPattern, GeneratedStrategy,
    ToolStrategyLearner, ToolStrategyType, ToolRecommendation
)

# 记忆包
from src.evolution.memory import (
    AssociationDatabase,
    AssociationDiscoverer
)

# 自我监控
from src.evolution.self_monitor import SelfMonitor
```

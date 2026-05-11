# HermesAgentEvolution API 参考

> 版本: v7.0.1 (V1/V2/V3 融合架构)
> 覆盖模块: 10 个子系统，57+ 核心类
> 最后更新: 2026-05-09

---

## 概述

本文档覆盖 HermesAgentEvolution v7.0.1 所有公开 API。按 10 个子系统分组。导入路径支持两种模式：

- **pip 安装**: `from evolution.xxx import ...`
- **开发模式**: `from src.evolution.xxx import ...`

---

## 一、闭环进化子系统 (`evolution.closed_loop`)

### 1.1 ClosedLoopOrchestrator (`orchestrator.py`, 680 行)

**6 阶段闭环编排器**

```python
class ClosedLoopOrchestrator:
    def __init__(self, metrics_collector, self_monitor, experience_analyzer,
                 pattern_recognizer, strategy_learner, action_executor,
                 learning_observer, tool_evolution_engine=None, config=None):
        """初始化闭环编排器，注入全部子系统组件"""

    def monitor(self) -> Dict[str, Any]:
        """Phase 1: 采集系统指标"""

    def analyze(self, metrics: Dict) -> Dict[str, Any]:
        """Phase 2: 分析指标，识别模式"""

    def plan(self, analysis: Dict) -> Dict[str, Any]:
        """Phase 3: 生成改进计划"""

    def execute(self, plan: Dict) -> Dict[str, Any]:
        """Phase 4: 执行改进动作"""

    def verify(self, metrics_before, actions_taken) -> Dict[str, Any]:
        """Phase 5: 验证改进效果"""

    def feedback(self, snapshot: EvolutionSnapshot) -> Dict[str, Any]:
        """Phase 6: 记录学习经验"""

    def run_full_cycle(self) -> Dict[str, Any]:
        """执行一次完整进化闭环（全部 6 个阶段）"""

    def get_cycle_history(self, limit=10) -> List[Dict]:
        """获取循环历史"""
```

### 1.2 EvolutionDaemon (`daemon.py`, 476 行)

**持续进化守护进程**

```python
class EvolutionDaemon:
    def start(self) -> None:
        """启动守护进程，进入主循环"""

    def stop(self) -> None:
        """安全停止"""

    def pause(self) -> None:
        """暂停进化"""

    def resume(self) -> None:
        """恢复进化"""

    def get_status(self) -> Dict[str, Any]:
        """获取当前状态"""

    def get_recent_snapshots(self, limit=20) -> List[EvolutionSnapshot]:
        """获取最近的进化快照"""

    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取进化摘要"""
```

**数据类**:
- `EvolutionSnapshot`: cycle_id, timestamp, phases_completed, metrics_before/after, actions_taken, improvements_detected, duration_seconds, success
- `EvolutionPhase(Enum)`: MONITOR, ANALYZE, PLAN, EXECUTE, VERIFY, FEEDBACK
- `LoopState(Enum)`: RUNNING, PAUSED, STOPPING, STOPPED

### 1.3 SystemMetricsCollector (`metrics_collector.py`, 456 行)

```python
class SystemMetricsCollector:
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def collect_all(self) -> Dict[str, Any]: ...
    def collect_minimal(self) -> Dict[str, Any]: ...
    def record_tool_call(self, tool_name, success, exec_time, **ctx): ...
    def record_experience(self, **kwargs): ...
    def record_pattern(self, pattern_type, confidence): ...
    def record_improvement(self, improvement_type, **ctx): ...
    def get_tool_stats(self) -> Dict: ...
    def get_system_health(self) -> Dict: ...
    def get_metrics_summary(self) -> Dict: ...
```

### 1.4 ActionExecutor (`action_executor.py`, 355 行)

```python
class ActionExecutor:
    def execute(self, action: ImprovementAction) -> Dict[str, Any]:
        """执行单个改进动作"""

    def execute_batch(self, actions: List[ImprovementAction]) -> Dict:
        """批量执行改进动作"""

    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
```

### 1.5 EvolutionAuditor (`evolution_auditor.py`, 446 行) 🆕 v7.0.1

**自进化审计器 — 迭代 10 新增**

```python
class EvolutionAuditor:
    def record_cycle(self, cycle_id, metrics_before, metrics_after,
                     actions_taken, improvements, duration, success) -> int:
        """记录一次进化循环到 evolution_cycles 表"""
    
    def record_action(self, cycle_id, action_type, target, 
                      success, duration, details) -> int:
        """记录单个动作到 evolution_actions 表"""
    
    def query_cycles(self, limit=10, success_only=False) -> List[Dict]:
        """查询最近的进化循环"""
    
    def get_cycle_detail(self, cycle_id) -> Dict:
        """获取单个循环详情（含关联动作）"""
    
    def get_summary(self) -> Dict[str, Any]:
        """获取总体摘要（成功率、总循环数、平均时长等）"""
    
    def get_latest_health_trend(self, cycles=10) -> Dict[str, Any]:
        """获取最近 N 次循环的健康趋势"""
```

**数据表**:
- `evolution_cycles`: id, cycle_id, timestamp, metrics_before, metrics_after, actions_json, improvements_json, duration, success, errors
- `evolution_actions`: id, cycle_id, action_type, target, success, duration, details_json, timestamp

---

## 二、协作引擎子系统 (`evolution.collaboration`)

### 2.1 AgentRegistry (`agent_registry.py`, 460 行)

```python
class AgentRegistry:
    def register(self, agent_info: AgentInfo) -> str:
        """注册 Agent，返回 agent_id"""

    def unregister(self, agent_id: str) -> bool: ...
    def discover(self, capabilities=None, status=None) -> List[AgentInfo]: ...
    def heartbeat(self, agent_id: str) -> bool: ...
    def get_status(self, agent_id: str) -> AgentInfo: ...
    def list_all(self) -> List[AgentInfo]: ...
    def get_agent_count(self) -> int: ...
    def report_to_monitor(self) -> Dict: ...
```

**数据类**: `AgentInfo`: agent_id, name, capabilities, status, last_heartbeat, metadata
**枚举**: `AgentStatus(Enum)`: ONLINE, OFFLINE, BUSY, ERROR

### 2.2 TaskDispatcher (`task_dispatcher.py`, 503 行)

```python
class TaskDispatcher:
    def submit_task(self, task_type, priority, payload, 
                    assigned_to=None) -> str:
        """提交任务，返回 task_id"""

    def complete_task(self, task_id, result) -> bool: ...
    def cancel_task(self, task_id) -> bool: ...
    def task_status(self, task_id) -> Dict: ...
    def list_tasks(self, status=None, agent_id=None) -> List[Dict]: ...
    def get_queue_size(self) -> int: ...
    def get_stats(self) -> Dict: ...
```

### 2.3 AgentOrchestrator (`agent_orchestrator.py`, 568 行)

```python
class AgentOrchestrator:
    def create_workflow(self, name, steps) -> str:
        """创建工作流"""

    def execute_workflow(self, workflow_id) -> Dict:
        """执行工作流"""

    def get_workflow_status(self, workflow_id) -> Dict: ...
    def broadcast(self, message, priority=MessagePriority.NORMAL): ...
```

### 2.4 CollaborationMessageBus (`message_bus.py`, 547 行)

```python
class CollaborationMessageBus:
    def send(self, sender, recipient, message_type, content, priority): ...
    def broadcast(self, sender, message_type, content, priority): ...
    def subscribe(self, agent_id, channels=None): ...
    def unsubscribe(self, agent_id): ...
    def receive(self, agent_id, limit=20) -> List[Dict]: ...
    def get_unread_count(self, agent_id) -> int: ...
    def close(self): ...
```

---

## 三、V1/V2 融合子系统 (`evolution.fusion`)

### 3.1 V1V2Bridge (`bridge.py`, 679 行)

```python
class V1V2Bridge:
    def __init__(self, service_manager, event_bus, config_manager): ...
    def translate_v1_to_v2(self, v1_event: Dict) -> Dict: ...
    def translate_v2_to_v1(self, v2_event: Dict) -> Dict: ...
    def map_service(self, v1_service_name: str) -> str: ...
    def check_mapping_health(self) -> Dict: ...
```

### 3.2 UnifiedAgent (`unified_entry.py`, 861 行)

```python
class UnifiedAgent:
    def __init__(self, mode: RunMode = RunMode.HYBRID): ...
    def initialize(self) -> None: ...
    def shutdown(self) -> None: ...
    def execute_capability(self, request: CapabilityRequest) -> CapabilityResponse: ...
    def get_status_report(self) -> UnifiedStatusReport: ...
```

**枚举**: `RunMode(Enum)`: V1_ONLY, V2_ONLY, HYBRID

### 3.3 CompatibilityLayer (`compatibility.py`, 555 行)

```python
class CompatibilityLayer: ...
class StatusMapper: ...
class EnumMapper: ...
class APIGateway: ...
class DegradationHandler: ...
class VersionDetector: ...
```

---

## 四、学习能力子系统 (`evolution.learning`)

### 4.1 Experience (`experience.py`, 153 行)

```python
@dataclass
class Experience:
    id: str            # UUID
    experience_type: ExperienceType
    task_id: str
    timestamp: datetime
    description: str
    outcome: Outcome
    metrics: Dict[str, Any]
    context: Dict[str, Any]
    actions: List[Dict]
    lessons_learned: List[str]
    tags: List[str]
    confidence: float
    importance: float
    
    def to_dict(self) -> Dict: ...
    @classmethod
    def from_dict(cls, data: Dict) -> Experience: ...
```

**枚举**: 
- `ExperienceType(Enum)`: TOOL_USAGE, REASONING, ADAPTATION, OPTIMIZATION, COLLABORATION, LEARNING
- `Outcome(Enum)`: SUCCESS, FAILURE, PARTIAL_SUCCESS, UNCERTAIN

### 4.2 LearningObserver (`observer.py`, 473 行)

```python
class LearningObserver:
    def __init__(self, db_path=None): ...
    def record_experience(self, experience: Experience) -> str:
        """记录经验，返回 experience_id"""
    
    def get_recent_experiences(self, days=7, limit=100) -> List[Experience]: ...
    def get_statistics(self) -> Dict: ...
```

### 4.3 ExperienceAnalyzer (`analyzer.py`, 273 行)

```python
class ExperienceAnalyzer:
    def __init__(self, observer: LearningObserver): ...
    
    def analyze_recent_experiences(self, days=7) -> AnalysisResult:
        """分析最近经验，返回结构化的分析结果"""
```

**数据类**: 
- `AnalysisResult`: total_experiences, success_rate, identified_patterns, key_insights, improvement_suggestions, summary
- `PatternInstance`: pattern_type, confidence, occurrences, description

### 4.4 PatternRecognizer (`pattern_recognizer.py`, 606 行)

```python
class PatternRecognizer:
    def recognize_patterns(self, experiences, performance_data) -> List[RecognizedPattern]:
        """从经验和性能数据中识别模式"""
    
    def generate_strategies(self, patterns, current_strategy) -> List[GeneratedStrategy]:
        """根据识别的模式生成优化策略"""
```

### 4.5 ToolStrategyLearner (`tool_strategy_learner.py`, 459 行) 🆕 v3.0.5 持久化

**迭代 9 新增 SQLite 持久化**

```python
class ToolStrategyLearner:
    def __init__(self, db_path: str = "tools.db"):
        """初始化策略学习器。v3.0.5 起支持 db_path 持久化"""
    
    def record_tool_usage(self, tool_name, success, execution_time, context=None): ...
    def get_current_strategy(self) -> ToolStrategyType: ...
    def get_strategy_performance(self) -> Dict[ToolStrategyType, StrategyPerformance]: ...
    def get_tool_performance_summary(self) -> Dict[str, ToolPerformance]: ...
    def set_exploration_rate(self, rate: float): ...
    def recommend_tools(self, task_context, limit=5) -> List[ToolRecommendation]: ...
```

**枚举**: `ToolStrategyType(Enum)`: AGGRESSIVE, CONSERVATIVE, ADAPTIVE, EXPLORATORY
**数据表**: `tool_usage_history` (由 `_init_db()` 创建，`_load_from_db()` 加载 7 天历史)

---

## 五、记忆系统子系统 (`evolution.memory`)

### 5.1 AssociationDatabase (`database.py`, 420 行)

```python
class AssociationDatabase:
    def __init__(self, db_path="associations.db"): ...
    def add_memory_entry(self, content, source, importance, **meta) -> int: ...
    def add_association(self, source_id, target_id, assoc_type, strength, **meta): ...
    def get_associations(self, entry_id, assoc_type=None, min_strength=0) -> List[Dict]: ...
    def get_memory_entries(self, limit=50, min_importance=0) -> List[Dict]: ...
```

**5 张数据表**: memory_entries, associations, association_discovery_logs, association_usage_stats, association_patterns

### 5.2 AssociationDiscoverer (`association_discoverer.py`, 813 行)

```python
class AssociationDiscoverer:
    def discover_all(self, limit=100) -> List[Dict]:
        """三种算法发现关联: semantic / temporal / usage_pattern"""
```

### 5.3 AssociationOptimizer (`association_optimizer.py`, 494 行)

```python
class AssociationOptimizer:
    def optimize_all_associations(self) -> OptimizationResult: ...
```

### 5.4 RetrievalOptimizer (`retrieval_optimizer.py`, 537 行)

```python
class RetrievalOptimizer:
    """基于反馈的检索参数貝叶斯/梯度自优化"""
```

---

## 六、安全增强子系统 (`evolution.security`)

### 6.1 AuditLogger (`audit_logger.py`, 653 行)

```python
class AuditLogger:
    def log(self, event_type, level, agent_id, details, **ctx) -> str:
        """记录审计事件。自动轮转 >10000 条"""
    def query(self, **filters) -> AuditQueryResult: ...
    def get_summary(self) -> Dict: ...
```

### 6.2 PermissionManager (`permission_manager.py`, 436 行)

```python
class PermissionManager:
    """RBAC 四级角色: ADMIN / OPERATOR / VIEWER / RESTRICTED"""
    def check_permission(self, agent_id, operation) -> PermissionCheckResult: ...
    def assign_role(self, agent_id, role) -> bool: ...
    def revoke_role(self, agent_id) -> bool: ...
```

### 6.3 SandboxExecutor (`sandbox_executor.py`, 505 行)

```python
class SandboxExecutor:
    def execute(self, code, timeout=30, max_memory=128*1024*1024) -> SandboxResult: ...
    def analyze_safety(self, code) -> List[str]: ...
```

### 6.4 ThreatDetector (`threat_detector.py`, 580 行)

```python
class ThreatDetector:
    def analyze_event(self, event) -> Optional[ThreatAlert]: ...
    def add_rule(self, rule: DetectionRule): ...
    def get_active_threats(self) -> List[ThreatAlert]: ...
```

---

## 七、工具能力进化子系统 (`evolution.tools`)

### 7.1 ToolRegistry (`tool_registry.py`, 525 行)

```python
class ToolRegistry:
    def register(self, tool: ToolDefinition) -> str: ...
    def get(self, tool_name: str) -> Optional[ToolDefinition]: ...
    def list_all(self, category=None, status=None) -> List[ToolDefinition]: ...
    def update_status(self, tool_name, status): ...
    def search(self, query, limit=10) -> List[ToolDefinition]: ...
```

### 7.2 ToolCreator (`tool_creator.py`, 444 行)

```python
class ToolCreator:
    def create_from_function(self, func, name=None, description=None) -> ToolCreationResult: ...
    def create_from_code(self, code, name, description) -> ToolCreationResult: ...
    def batch_create(self, specs: List[Dict]) -> List[ToolCreationResult]: ...
```

### 7.3 EnhancedToolCreator (`enhanced_tool_creator.py`, 938 行)

```python
class EnhancedToolCreator:
    """6 种创建源"""
    def create_from_function(self, ...): ...
    def create_from_code(self, ...): ...
    def create_from_api_description(self, ...): ...
    def create_from_config(self, ...): ...
    def create_from_template(self, ...): ...
    def create_adaptive(self, ...): ...
```

### 7.4 ToolPerformanceAnalyzer (`tool_performance_analyzer.py`, 795 行)

```python
class ToolPerformanceAnalyzer:
    def record_performance(self, record: PerformanceRecord): ...
    def analyze(self, tool_name=None) -> PerformanceAnalysis: ...
    def get_summary(self) -> List[ToolPerformanceSummary]: ...
```

### 7.5 ToolAutoGenerator (`tool_auto_generator.py`, 741 行)

```python
class ToolAutoGenerator:
    def generate(self, description, strategy=GenerationStrategy.AUTO) -> ToolGenerationResult: ...
```

**内置模板**: file_reader, file_writer, api_caller, code_executor

### 7.6 ToolEvolutionEngine (`tool_integration.py`, 483 行)

```python
class ToolEvolutionEngine:
    def run_evolution_cycle(self) -> Dict: ...
    def analyze_current_state(self) -> Dict: ...
    def auto_generate_tool(self, description) -> Dict: ...
```

---

## 八、V2 微服务层 (`evolution.services` → `src.services`)

| 类 | 文件 | 行数 |
|----|------|------|
| EventBus | `core/events/event_bus.py` | 204 |
| ServiceManager | `core/services/service_manager.py` | 282 |
| ConfigManager | `core/config/config_manager.py` | 479 |
| MetaLearningService | `learning/meta/meta_learning_service.py` | 468 |
| ReflectionService | `learning/reflection/reflection_service.py` | 806 |
| RLService | `learning/reinforcement/rl_service.py` | 539 |
| ToolDiscoveryService | `tools/discovery/tool_discovery_service.py` | 793 |
| ToolCompositionService | `tools/composition/tool_composition_service.py` | 957 |
| DeploymentManager | `system/deployment/deployment_service.py` | 874 |
| MonitoringService | `system/monitoring/monitoring_service.py` | 936 |
| TestService | `system/testing/test_service.py` | 779 |

---

## 九、共享工具 (`evolution.utils` → `src.utils`)

### 9.1 FeishuNotifier (`feishu_notifier.py`, 342 行)

```python
class FeishuNotifier:
    """三种模式: webhook / openapi / simulated"""
    def send_notification(self, title, content, **kwargs) -> bool: ...
    def send_card(self, card_data) -> bool: ...
```

### 9.2 ProgressReporter (`progress_reporter.py`, 269 行)

```python
class ProgressReporter:
    def start_reporting(self, interval=7200): ...
    def stop_reporting(self): ...
    def send_progress_report(self) -> bool: ...
```

---

## 十、顶层模块

| 类/函数 | 文件 | 行数 |
|---------|------|------|
| HermesAgentEvolution | `main.py` | 446 |
| main_daemon() | `hermes_daemon.py` | 561 |
| 4 个 CLI 子命令 | `cli.py` | 481 |
| SelfMonitor | `self_monitor.py` | 207 |
| get_evolution_db() | `db_utils.py` | 235 |
| health_check() | `health.py` | 165 |
| setup_logging() | `logging_config.py` | 149 |
| DependencyManager | `dependency_manager.py` | 109 |

---

## 版本常量

| 位置 | 常量 | 值 |
|------|------|-----|
| `src/evolution/__init__.py` | `__version__` | `"7.0.1"` |
| `src/evolution/fusion/__init__.py` | `__version__` | `"1.0.0"` |

---

## 统计

- **总类数**: 57+
- **核心代码**: ~26,561 行
- **测试代码**: ~9,700 行 (24 文件)
- **测试**: 439 passed
- **数据库**: 7 个 SQLite 文件
- **Hermes 工具**: 7 个 + 1 个 Hook

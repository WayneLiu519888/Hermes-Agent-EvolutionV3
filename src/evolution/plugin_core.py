"""
Hermes Evolution Plugin Core

Shared logic extracted from the hermes-plugin / _plugin mirror files.
Provides 8 tools + 4 hooks for the Hermes Agent self-evolution system:

  Tools:
    - evolution_run_cycle           — trigger one full evolution cycle
    - evolution_create_tool         — create a new tool from an API description
    - evolution_analyze_performance — analyze tool performance metrics
    - evolution_learn               — record an experience / lesson learned
    - evolution_self_monitor        — get current system health status
    - evolution_memory_discover     — discover associations between memories
    - evolution_audit               — query evolution audit records

  Hook:
    - post_tool_call                — auto-records tool execution experience

This module is the single source of truth. Both hermes-plugin/__init__.py and
_plugin/__init__.py forward to register() defined here.
"""

import json
import sys
import logging
import os
import uuid
import atexit
from pathlib import Path
from datetime import datetime, timedelta

from evolution.db_utils import get_data_dir, auto_checkpoint_if_needed
from evolution.consumer import AssociationConsumer

logger = logging.getLogger("hermes_evolution_plugin")


# ── 优雅关闭：atexit 触发 WAL checkpoint + 关闭所有连接 ──
def _shutdown():
    from evolution.db_pool import db_pool
    db_pool.checkpoint_all(max_wal_mb=0)  # 强制清空所有WAL
    db_pool.close_all()
atexit.register(_shutdown)

# ---------------------------------------------------------------------------
# Module-level singletons — lazily initialized (V7.0.4: thread-safe)
# ---------------------------------------------------------------------------
import threading
import time
_engine_instances = {}
_engine_lock = threading.Lock()
_engine_failures = {}  # V7.0.5: {key: unix_timestamp}，失败后TTL冷却


def _init_instance(key: str, factory, *args, retry_after: float = 30, **kwargs):
    """线程安全的懒初始化单例（V7.0.5: TTL自动恢复）。

    双重检查：先无锁读，不存在时加锁创建。
    失败后不永久缓存None——retry_after秒后自动清除，下次调用重新尝试。
    """
    # 快速路径：已有有效实例
    if key in _engine_instances and _engine_instances[key] is not None:
        return _engine_instances[key]

    # TTL 冷却：失败后等待 retry_after 秒再重试
    failed_at = _engine_failures.get(key)
    if failed_at is not None and (time.time() - failed_at) < retry_after:
        return None

    with _engine_lock:
        # 双重检查
        if key in _engine_instances and _engine_instances[key] is not None:
            return _engine_instances[key]
        try:
            instance = factory(*args, **kwargs)
            _engine_instances[key] = instance
            _engine_failures.pop(key, None)  # 成功后清除失败记录
            return instance
        except Exception as e:
            logger.warning("Failed to create %s (will retry in %.0fs): %s", key, retry_after, e)
            _engine_instances[key] = None
            _engine_failures[key] = time.time()
            return None


# ---------------------------------------------------------------------------
# Lazy engine initializers — create instances on demand with fallbacks
# ---------------------------------------------------------------------------
def _get_tool_registry():
    """Get or create a ToolRegistry singleton."""
    if "tool_registry" not in _engine_instances:
        try:
            from evolution.tools import ToolRegistry
            db_path = str(get_data_dir() / "tools.db")
            _engine_instances["tool_registry"] = ToolRegistry(db_path=db_path)
        except Exception as e:
            logger.warning("Failed to create ToolRegistry: %s", e)
            _engine_instances["tool_registry"] = None
    return _engine_instances["tool_registry"]


def _get_learning_observer():
    """Get or create a LearningObserver singleton (thread-safe)."""
    from evolution.learning import LearningObserver
    db_path = str(get_data_dir() / "learning_experiences.db")
    return _init_instance("learning_observer", LearningObserver, db_path=db_path)


def _get_orchestrator():
    """Get or create a ClosedLoopOrchestrator singleton (thread-safe, V7.0.5 TTL)."""
    key = "orchestrator"
    # 快速路径：已有有效实例
    if key in _engine_instances and _engine_instances[key] is not None:
        return _engine_instances[key]
    # TTL 冷却
    failed_at = _engine_failures.get(key)
    if failed_at is not None and (time.time() - failed_at) < 30:
        return None
    with _engine_lock:
        if key in _engine_instances and _engine_instances[key] is not None:
            return _engine_instances[key]
        try:
            from evolution.closed_loop import (
                ClosedLoopOrchestrator,
                SystemMetricsCollector,
            )
            from evolution.learning import (
                LearningObserver,
                ExperienceAnalyzer,
                PatternRecognizer,
                ToolStrategyLearner,
            )
            from evolution import SelfMonitor  # top-level import

            db_base = str(get_data_dir())

            observer = LearningObserver(db_path=os.path.join(db_base, "learning_experiences.db"))
            analyzer = ExperienceAnalyzer(observer)
            strategy_learner = ToolStrategyLearner(db_path=os.path.join(db_base, "tools.db"))
            self_monitor = SelfMonitor(observer, analyzer, strategy_learner)
            metrics_collector = SystemMetricsCollector()
            pattern_recognizer = PatternRecognizer()
            from evolution.closed_loop import ActionExecutor
            action_executor = ActionExecutor()

            orch = ClosedLoopOrchestrator(
                metrics_collector=metrics_collector,
                self_monitor=self_monitor,
                experience_analyzer=analyzer,
                pattern_recognizer=pattern_recognizer,
                strategy_learner=strategy_learner,
                action_executor=action_executor,
                learning_observer=observer,
            )
            _engine_instances[key] = orch
            _engine_instances["learning_observer"] = observer
            _engine_instances["self_monitor"] = self_monitor
            _engine_instances["experience_analyzer"] = analyzer
            _engine_instances["strategy_learner"] = strategy_learner
        except Exception as e:
            logger.warning("Failed to create ClosedLoopOrchestrator: %s", e)
            _engine_instances[key] = None
            _engine_failures[key] = time.time()  # V7.0.5: TTL恢复
    return _engine_instances[key]


def _get_self_monitor():
    """Get the SelfMonitor singleton."""
    if "self_monitor" not in _engine_instances:
        # Ensure orchestrator init triggered it
        _get_orchestrator()
    return _engine_instances.get("self_monitor")


def _get_tool_performance_analyzer():
    """Get or create a ToolPerformanceAnalyzer singleton."""
    if "tool_performance_analyzer" not in _engine_instances:
        try:
            from evolution.tools import ToolPerformanceAnalyzer
            registry = _get_tool_registry()
            if registry is None:
                _engine_instances["tool_performance_analyzer"] = None
            else:
                db_path = str(get_data_dir() / "tool_performance.db")
                _engine_instances["tool_performance_analyzer"] = ToolPerformanceAnalyzer(
                    registry=registry, db_path=db_path
                )
        except Exception as e:
            logger.warning("Failed to create ToolPerformanceAnalyzer: %s", e)
            _engine_instances["tool_performance_analyzer"] = None
    return _engine_instances["tool_performance_analyzer"]


def _get_strategy_learner():
    """Get the StrategyLearner singleton (from orchestrator or standalone)."""
    if "strategy_learner" not in _engine_instances:
        # Ensure orchestrator init triggered it, or create standalone
        _get_orchestrator()
    return _engine_instances.get("strategy_learner")


def _get_evolution_auditor():
    """Get or create an EvolutionAuditor singleton."""
    if "evolution_auditor" not in _engine_instances:
        try:
            from evolution.closed_loop import EvolutionAuditor
            db_path = str(get_data_dir() / "evolution_audit.db")
            _engine_instances["evolution_auditor"] = EvolutionAuditor(db_path=db_path)
        except Exception as e:
            logger.warning("Failed to create EvolutionAuditor: %s", e)
            _engine_instances["evolution_auditor"] = None
    return _engine_instances["evolution_auditor"]


def _get_association_discoverer():
    """Get or create an AssociationDiscoverer singleton."""
    if "association_discoverer" not in _engine_instances:
        try:
            from evolution.memory import AssociationDatabase, AssociationDiscoverer
            db_path = str(get_data_dir() / "associations.db")
            db = AssociationDatabase(db_path=db_path)
            discoverer = AssociationDiscoverer(db=db)
            _engine_instances["association_discoverer"] = discoverer
        except Exception as e:
            logger.warning("Failed to create AssociationDiscoverer: %s", e)
            _engine_instances["association_discoverer"] = None
    return _engine_instances["association_discoverer"]


# ---------------------------------------------------------------------------
# Tool 1: evolution_run_cycle
# ---------------------------------------------------------------------------
TOOL_RUN_CYCLE_SCHEMA = {
    "name": "evolution_run_cycle",
    "description": "Trigger one full evolution cycle (monitor → analyze → plan → execute → verify → feedback). Returns cycle results including phases, issues found, and actions taken.",
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}


def _handle_run_cycle(params, **kwargs):
    """Handler for evolution_run_cycle."""
    try:
        orchestrator = _get_orchestrator()
        if orchestrator is None:
            return json.dumps({
                "success": False,
                "error": "Orchestrator could not be initialized. Engine modules may not be installed.",
                "cycle_id": None,
                "phases": {},
                "timestamp": datetime.now().isoformat(),
            })

        result = orchestrator.run_full_cycle()
        result["success"] = True

        # 🆕 兜底审计记录（确保即使 orchestrator._audit_cycle 未执行也能记录）
        try:
            # 直接导入避免单例缓存问题
            from evolution.closed_loop.evolution_auditor import EvolutionAuditor
            auditor = EvolutionAuditor()
            auditor.record_cycle(result)
        except Exception as e:
            logger.warning("审计记录失败(handler): %s", e)

        return json.dumps(result, default=str, ensure_ascii=False)

    except Exception as e:
        logger.exception("evolution_run_cycle failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "cycle_id": None,
            "phases": {},
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Tool 2: evolution_create_tool
# ---------------------------------------------------------------------------
TOOL_CREATE_TOOL_SCHEMA = {
    "name": "evolution_create_tool",
    "description": "Create a new tool from an API description or function specification. Registers it in the tool registry.",
    "parameters": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to create",
            },
            "description": {
                "type": "string",
                "description": "Description of what the tool does",
            },
            "api_spec": {
                "type": "object",
                "description": "API specification with endpoint, method, parameters, and return type",
            },
            "category": {
                "type": "string",
                "description": "Tool category: utility, data_processing, file_operation, network, ai, custom",
                "default": "custom",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Optional tags for the tool",
            },
        },
        "required": ["tool_name", "description", "api_spec"],
    },
}


def _handle_create_tool(params, **kwargs):
    """Handler for evolution_create_tool."""
    try:
        tool_name = params.get("tool_name", "")
        description = params.get("description", "")
        api_spec = params.get("api_spec", {})
        category = params.get("category", "custom")
        tags = params.get("tags", [])

        # ── Input validation: tool_name ──────────────────────────────────
        from evolution.security.input_validator import InputValidator
        name_result = InputValidator.validate_tool_name(tool_name)
        if not name_result.valid:
            return json.dumps({
                "success": False,
                "error": "; ".join(name_result.errors),
            })
        tool_name = name_result.sanitized

        if not tool_name or not description or not api_spec:
            return json.dumps({
                "success": False,
                "error": "Missing required parameters: tool_name, description, api_spec",
            })

        from evolution.tools import EnhancedToolCreator, ToolCategory

        cat_map = {
            "utility": ToolCategory.UTILITY,
            "data_processing": ToolCategory.DATA_PROCESSING,
            "file_operation": ToolCategory.FILE_OPERATION,
            "network": ToolCategory.NETWORK,
            "ai": ToolCategory.AI,
            "custom": ToolCategory.CUSTOM,
        }
        tool_category = cat_map.get(category, ToolCategory.CUSTOM)

        registry = _get_tool_registry()
        if registry is None:
            return json.dumps({
                "success": False,
                "error": "ToolRegistry not available",
            })

        creator = EnhancedToolCreator(registry=registry)
        result = creator.create_from_api_description(
            api_spec=api_spec,
            name=tool_name,
            category=tool_category,
        )

        return json.dumps({
            "success": result.success,
            "tool_name": tool_name,
            "error": result.error_message if not result.success else None,
            "warnings": result.warnings,
            "quality_score": result.quality_score if result.success else None,
            "quality_level": result.quality_level.value if result.success and hasattr(result, 'quality_level') else None,
            "timestamp": datetime.now().isoformat(),
        }, default=str, ensure_ascii=False)

    except Exception as e:
        logger.exception("evolution_create_tool failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "tool_name": params.get("tool_name", "") if isinstance(params, dict) else "",
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Tool 3: evolution_analyze_performance
# ---------------------------------------------------------------------------
TOOL_ANALYZE_PERFORMANCE_SCHEMA = {
    "name": "evolution_analyze_performance",
    "description": "Analyze tool performance metrics. Can analyze all tools or a specific one.",
    "parameters": {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Specific tool name to analyze. If omitted, analyzes all tools.",
            },
            "output_format": {
                "type": "string",
                "enum": ["json", "text", "html"],
                "description": "Output format for the performance report",
                "default": "json",
            },
        },
        "required": [],
    },
}


def _handle_analyze_performance(params, **kwargs):
    """Handler for evolution_analyze_performance."""
    try:
        analyzer = _get_tool_performance_analyzer()
        if analyzer is None:
            return json.dumps({
                "success": False,
                "error": "ToolPerformanceAnalyzer not available. Ensure ToolRegistry is initialized.",
            })

        tool_name = params.get("tool_name")
        output_format = params.get("output_format", "json")

        if tool_name:
            summary = analyzer.analyze_tool_performance(tool_name, time_period=timedelta(days=30))
            return json.dumps({
                "success": True,
                "tool_name": tool_name,
                "overall_score": summary.overall_score,
                "performance_level": summary.performance_level.value,
                "key_insights": summary.key_insights,
                "optimization_opportunities": summary.optimization_opportunities,
                "tool_status": summary.tool_status.value,
                "last_analysis": summary.last_analysis.isoformat() if summary.last_analysis else None,
                "timestamp": datetime.now().isoformat(),
            }, default=str, ensure_ascii=False)

        # Analyze all tools
        if output_format == "text":
            report = analyzer.generate_performance_report(output_format="text")
            return json.dumps({
                "success": True,
                "analysis_type": "all_tools",
                "report_text": report,
                "timestamp": datetime.now().isoformat(),
            }, ensure_ascii=False)

        summaries = analyzer.analyze_all_tools()
        tools_data = {}
        for name, summary in summaries.items():
            tools_data[name] = {
                "overall_score": summary.overall_score,
                "performance_level": summary.performance_level.value,
                "key_insights": summary.key_insights,
                "optimization_opportunities": summary.optimization_opportunities,
            }

        return json.dumps({
            "success": True,
            "analysis_type": "all_tools",
            "tools_analyzed": len(summaries),
            "tools": tools_data,
            "timestamp": datetime.now().isoformat(),
        }, default=str, ensure_ascii=False)

    except Exception as e:
        logger.exception("evolution_analyze_performance failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Tool 4: evolution_learn
# ---------------------------------------------------------------------------
TOOL_LEARN_SCHEMA = {
    "name": "evolution_learn",
    "description": "Record a new learning experience or lesson into the evolution system.",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {
                "type": "string",
                "description": "Description of the experience or lesson learned",
            },
            "experience_type": {
                "type": "string",
                "enum": ["tool_usage", "reasoning", "problem_solving", "error_recovery", "pattern_recognition", "adaptation"],
                "description": "Type of experience",
                "default": "tool_usage",
            },
            "outcome": {
                "type": "string",
                "enum": ["success", "partial_success", "failure", "uncertain"],
                "description": "Outcome of the experience",
                "default": "success",
            },
            "task_id": {
                "type": "string",
                "description": "Identifier for the associated task",
                "default": "",
            },
            "lessons": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Specific lessons learned",
            },
            "metrics": {
                "type": "object",
                "description": "Performance metrics (e.g., duration, success_rate)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization",
            },
            "context": {
                "type": "object",
                "description": "Additional context about the experience",
            },
        },
        "required": ["description"],
    },
}


def _handle_learn(params, **kwargs):
    """Handler for evolution_learn."""
    try:
        from evolution.learning import Experience, ExperienceType, Outcome

        desc = params.get("description", "")
        exp_type_str = params.get("experience_type", "tool_usage")
        outcome_str = params.get("outcome", "success")
        task_id = params.get("task_id", "")
        lessons = params.get("lessons", [])
        metrics = params.get("metrics", {})
        tags = params.get("tags", [])
        context = params.get("context", {})

        type_map = {
            "tool_usage": ExperienceType.TOOL_USAGE,
            "reasoning": ExperienceType.REASONING,
            "problem_solving": ExperienceType.PROBLEM_SOLVING,
            "error_recovery": ExperienceType.ERROR_RECOVERY,
            "pattern_recognition": ExperienceType.PATTERN_RECOGNITION,
            "adaptation": ExperienceType.ADAPTATION,
        }
        outcome_map = {
            "success": Outcome.SUCCESS,
            "partial_success": Outcome.PARTIAL_SUCCESS,
            "failure": Outcome.FAILURE,
            "uncertain": Outcome.UNCERTAIN,
        }

        experience = Experience(
            id=str(uuid.uuid4()),
            experience_type=type_map.get(exp_type_str, ExperienceType.TOOL_USAGE),
            task_id=task_id,
            timestamp=datetime.now(),
            description=desc,
            context=context,
            outcome=outcome_map.get(outcome_str, Outcome.SUCCESS),
            metrics={str(k): float(v) for k, v in metrics.items()} if metrics else {},
            lessons_learned=list(lessons),
            tags=list(tags),
        )
        experience.calculate_confidence()

        observer = _get_learning_observer()
        if observer is None:
            # Fallback: serialize and return the experience without persisting
            return json.dumps({
                "success": False,
                "error": "LearningObserver not available. Experience not persisted.",
                "experience": experience.to_dict(),
            })

        exp_id = observer.record_experience(experience)
        return json.dumps({
            "success": True,
            "experience_id": exp_id,
            "experience_type": exp_type_str,
            "outcome": outcome_str,
            "confidence": experience.confidence,
            "timestamp": datetime.now().isoformat(),
        }, default=str, ensure_ascii=False)

    except Exception as e:
        logger.exception("evolution_learn failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Tool 5: evolution_self_monitor
# ---------------------------------------------------------------------------
TOOL_SELF_MONITOR_SCHEMA = {
    "name": "evolution_self_monitor",
    "description": "Get current system health status including success rate, tool performance, strategy effectiveness, and health score.",
    "parameters": {
        "type": "object",
        "properties": {
            "include_history": {
                "type": "boolean",
                "description": "Include recent monitoring history",
                "default": False,
            },
        },
        "required": [],
    },
}


def _handle_self_monitor(params, **kwargs):
    """Handler for evolution_self_monitor."""
    try:
        self_monitor = _get_self_monitor()
        if self_monitor is None:
            # Try a lightweight fallback using individual components
            observer = _get_learning_observer()
            if observer is not None:
                return json.dumps({
                    "success": True,
                    "fallback": True,
                    "health_score": None,
                    "status": "limited",
                    "message": "SelfMonitor unavailable. Using basic observer only.",
                    "recent_experience_count": len(observer.get_recent_experiences(days=1)),
                    "timestamp": datetime.now().isoformat(),
                })

            return json.dumps({
                "success": False,
                "error": "SelfMonitor and LearningObserver not available.",
            })

        health = self_monitor.get_system_health_report()

        result = {
            "success": True,
            "health_score": health.get("health_score"),
            "status": health.get("status"),
            "metrics": health.get("metrics", {}),
            "recommendations": health.get("recommendations", []),
            "timestamp": datetime.now().isoformat(),
        }

        if params.get("include_history"):
            result["monitoring_history"] = self_monitor.get_monitoring_history(limit=5)

            # 🆕 附加进化审计摘要
            try:
                auditor = _get_evolution_auditor()
                if auditor:
                    result["audit_summary"] = auditor.get_summary(days=30)
            except Exception:
                pass

        return json.dumps(result, default=str, ensure_ascii=False)

    except Exception as e:
        logger.exception("evolution_self_monitor failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Tool 6: evolution_memory_discover
# ---------------------------------------------------------------------------
TOOL_MEMORY_DISCOVER_SCHEMA = {
    "name": "evolution_memory_discover",
    "description": "Discover associations between memories using semantic, temporal, and usage-pattern algorithms.",
    "parameters": {
        "type": "object",
        "properties": {
            "methods": {
                "type": "array",
                "items": {
                    "type": "string",
                    "enum": ["semantic", "temporal", "usage_pattern"],
                },
                "description": "Discovery methods to use. Omit for all three.",
            },
            "entry_id": {
                "type": "string",
                "description": "Specific memory entry ID to discover associations for. If omitted, discovers across all entries.",
            },
            "max_entries": {
                "type": "integer",
                "description": "Maximum entries to process when entry_id is omitted. Default 200, hard cap 500. Prevents OOM from N×N combinatorial explosion.",
                "default": 200,
                "minimum": 1,
                "maximum": 500,
            },
        },
        "required": [],
    },
}


def _handle_memory_discover(params, **kwargs):
    """Handler for evolution_memory_discover."""
    try:
        discoverer = _get_association_discoverer()
        if discoverer is None:
            return json.dumps({
                "success": False,
                "error": "AssociationDiscoverer not available.",
            })

        methods = params.get("methods")  # None means all
        entry_id = params.get("entry_id")
        max_entries = params.get("max_entries", 200)

        if entry_id:
            result = discoverer.discover_for_entry(entry_id, methods=methods)
        else:
            result = discoverer.discover_all(methods=methods, max_entries=max_entries)

        # ── WAL checkpoint: 防止关联发现大量写入导致 WAL 膨胀 ──
        auto_checkpoint_if_needed("associations.db", max_wal_mb=100)

        return json.dumps({
            "success": True,
            "entry_id": entry_id,
            "total_associations": result.get("total_associations", 0),
            "methods": result.get("methods", {}),
            "timestamp": datetime.now().isoformat(),
        }, default=str, ensure_ascii=False)

    except ValueError as e:
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })
    except Exception as e:
        logger.exception("evolution_memory_discover failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Hook: post_tool_call — auto-record tool execution experience
# ---------------------------------------------------------------------------
def _on_post_tool_call(ctx, tool_name, params, result, duration_ms, error):
    """
    Hook callback for post_tool_call.
    Automatically records a tool execution experience.
    """
    try:
        observer = _get_learning_observer()
        if observer is None:
            return

        from evolution.learning import Experience, ExperienceType, Outcome

        # Determine outcome
        if error:
            outcome = Outcome.FAILURE
        elif result is not None:
            outcome = Outcome.SUCCESS
        else:
            outcome = Outcome.UNCERTAIN

        # Build description
        desc = f"Tool execution: {tool_name} — {'FAILED' if error else 'completed'} in {duration_ms:.0f}ms"
        if error:
            desc += f" | Error: {str(error)[:200]}"

        experience = Experience(
            id=str(uuid.uuid4()),
            experience_type=ExperienceType.TOOL_USAGE,
            task_id=f"tool_call_{tool_name}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            timestamp=datetime.now(),
            description=desc,
            context={
                "tool_name": tool_name,
                "params": str(params)[:500] if params else "",
                "duration_ms": duration_ms,
            },
            outcome=outcome,
            metrics={"duration_ms": float(duration_ms) if duration_ms else 0},
            tags=["auto_recorded", tool_name],
        )
        experience.calculate_confidence()
        observer.record_experience(experience)

        # 🆕 驱动 strategy_learner 记录工具使用
        strategy_learner = _get_strategy_learner()
        if strategy_learner:
            try:
                strategy_learner.record_tool_usage(
                    tool_name=tool_name,
                    success=not bool(error),
                    execution_time=(duration_ms or 0) / 1000.0,
                    context={"params": str(params)[:200] if params else ""}
                )
            except Exception:
                pass

        # 🆕 驱动 tool_performance_analyzer 记录性能数据
        analyzer = _get_tool_performance_analyzer()
        if analyzer:
            try:
                from evolution.tools.tool_performance_analyzer import PerformanceMetric
                analyzer.record_performance(
                    tool_name=tool_name,
                    metric=PerformanceMetric.EXECUTION_TIME,
                    value=(duration_ms or 0) / 1000.0,
                    metadata={"success": not bool(error)}
                )
            except Exception:
                pass

    except Exception:
        # Hook must never raise — silently log and continue
        pass


# ---------------------------------------------------------------------------
# Tool 7: evolution_audit
# ---------------------------------------------------------------------------
TOOL_AUDIT_SCHEMA = {
    "name": "evolution_audit",
    "description": "Query evolution audit records — cycle history, action details, summary statistics, and health trends.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["query_cycles", "get_cycle_detail", "get_summary", "get_health_trend"],
                "description": "Audit action to perform.",
                "default": "get_summary",
            },
            "cycle_id": {
                "type": "integer",
                "description": "Specific cycle ID (for get_cycle_detail).",
            },
            "limit": {
                "type": "integer",
                "description": "Max cycles to return (for query_cycles).",
                "default": 10,
            },
            "success_only": {
                "type": "boolean",
                "description": "Filter to successful cycles only (for query_cycles).",
                "default": False,
            },
        },
        "required": [],
    },
}


def _handle_audit(params, **kwargs):
    """Handler for evolution_audit."""
    try:
        auditor = _get_evolution_auditor()
        if auditor is None:
            return json.dumps({
                "success": False,
                "error": "EvolutionAuditor could not be initialized.",
                "timestamp": datetime.now().isoformat(),
            })

        action = params.get("action", "get_summary")

        if action == "query_cycles":
            limit = params.get("limit", 10)
            success_only = params.get("success_only", False)
            cycles = auditor.query_cycles(limit=limit, success_only=success_only)
            return json.dumps({
                "success": True,
                "action": action,
                "cycles": cycles,
                "timestamp": datetime.now().isoformat(),
            }, default=str, ensure_ascii=False)

        elif action == "get_cycle_detail":
            cycle_id = params.get("cycle_id")
            if cycle_id is None:
                return json.dumps({
                    "success": False,
                    "error": "cycle_id is required for get_cycle_detail.",
                })
            detail = auditor.get_cycle_detail(cycle_id)
            return json.dumps({
                "success": True,
                "action": action,
                **detail,
                "timestamp": datetime.now().isoformat(),
            }, default=str, ensure_ascii=False)

        elif action == "get_summary":
            summary = auditor.get_summary()
            return json.dumps({
                "success": True,
                "action": action,
                **summary,
                "timestamp": datetime.now().isoformat(),
            }, default=str, ensure_ascii=False)

        elif action == "get_health_trend":
            limit = params.get("limit", 10)
            trend = auditor.get_latest_health_trend(cycles=limit)
            return json.dumps({
                "success": True,
                "action": action,
                "trend": trend,
                "timestamp": datetime.now().isoformat(),
            }, default=str, ensure_ascii=False)

        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown action: {action}. Use query_cycles/get_cycle_detail/get_summary/get_health_trend.",
            })

    except Exception as e:
        logger.exception("evolution_audit failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# V7 Hook: on_session_start — 注入最近失败教训到 memory
# ---------------------------------------------------------------------------
def _on_session_start(session_id, model=None, platform=None, **kwargs):
    """会话启动时：查询 HAE 学习经验，将高频失败教训写入 hermes memory"""
    try:
        from evolution.db_pool import db_pool
        consumer = AssociationConsumer(db_pool)
        lessons = consumer.recall_lessons(limit=3, outcome="failure")
        if not lessons:
            return

        # 生成教训摘要
        lines = ["[HAE教训] 最近失败经验："]
        for i, lesson in enumerate(lessons, 1):
            desc = (lesson.get("content") or lesson.get("description") or "")[:80]
            lines.append(f"  {i}. {desc}")
        lines.append("以上教训已注入，请避免重复错误。")

        # 写入 hermes memory（通过 memory 系统）
        _inject_lesson_to_memory("\n".join(lines), session_id)

    except Exception as exc:
        logger.debug("on_session_start hook: %s", exc)


def _inject_lesson_to_memory(lesson_text: str, session_id: str) -> None:
    """将教训文本写入 hermes memory 的 key-value 存储"""
    try:
        from pathlib import Path
        memory_file = Path("/root/.hermes/memory/hae_lessons.txt")
        memory_file.parent.mkdir(parents=True, exist_ok=True)
        # 追加模式，带时间戳和会话ID
        with open(memory_file, "a", encoding="utf-8") as f:
            f.write(f"=== {datetime.now().isoformat()[:19]} session={session_id[:8]} ===\n")
            f.write(lesson_text + "\n\n")
        # 只保留最近10条，避免文件膨胀
        lines = memory_file.read_text(encoding="utf-8").split("\n") if memory_file.exists() else []
        # 保留最近50行
        if len(lines) > 50:
            memory_file.write_text("\n".join(lines[-50:]), encoding="utf-8")
    except Exception:
        pass  # 静默失败，不影响主流程


# ---------------------------------------------------------------------------
# V7 Hook: pre_llm_call — 注入关联上下文到用户消息
# ---------------------------------------------------------------------------
def _on_pre_llm_call(messages, model=None, **kwargs):
    """LLM 调用前：从关联数据库提取上下文，注入到用户消息尾部"""
    try:
        from evolution.db_pool import db_pool
        consumer = AssociationConsumer(db_pool)

        # 取最后一条 user 消息
        user_msg = None
        user_idx = -1
        for i, msg in enumerate(messages):
            if msg.get("role") == "user":
                user_msg = msg
                user_idx = i

        if not user_msg:
            return messages

        context = consumer.inject_context(user_msg.get("content", ""))
        if context:
            # 追加到用户消息尾部
            modified = dict(user_msg)
            modified["content"] = user_msg.get("content", "") + "\n\n" + context
            messages[user_idx] = modified

    except Exception as exc:
        logger.debug("pre_llm_call hook: %s", exc)

    return messages


# ---------------------------------------------------------------------------
# V7 Hook: post_llm_call — 关联质量打分
# ---------------------------------------------------------------------------
def _on_post_llm_call(response, messages=None, model=None, **kwargs):
    """LLM 回复后：检查是否引用注入的关联，更新质量分数"""
    try:
        from evolution.db_pool import db_pool
        consumer = AssociationConsumer(db_pool)
        # response 可能是字符串或 dict
        text = response if isinstance(response, str) else response.get("content", "")
        if text:
            consumer.score_usage(text)
        consumer.cleanup()
    except Exception as exc:
        logger.debug("post_llm_call hook: %s", exc)


# ---------------------------------------------------------------------------
# Tool 8: evolution_recall_lessons — 经验教训召回
# ---------------------------------------------------------------------------
TOOL_RECALL_LESSONS_SCHEMA = {
    "name": "evolution_recall_lessons",
    "description": "查询历史经验教训，返回可执行的行为改进建议。帮助避免重复错误。",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "返回条数，默认5",
                "default": 5,
                "minimum": 1,
                "maximum": 20,
            },
            "outcome": {
                "type": "string",
                "enum": ["failure", "success", "all"],
                "description": "筛选结果类型：failure=失败教训, success=成功经验, all=全部",
                "default": "all",
            },
        },
        "required": [],
    },
}


def _handle_recall_lessons(params, **kwargs):
    """Handler for evolution_recall_lessons"""
    try:
        from evolution.db_pool import db_pool
        consumer = AssociationConsumer(db_pool)
        limit = params.get("limit", 5)
        outcome = params.get("outcome", "all")
        lessons = consumer.recall_lessons(limit=limit, outcome=outcome)

        return json.dumps({
            "success": True,
            "count": len(lessons),
            "lessons": lessons,
            "timestamp": datetime.now().isoformat(),
        }, default=str, ensure_ascii=False)

    except Exception as e:
        logger.exception("evolution_recall_lessons failed")
        return json.dumps({
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat(),
        })


# ---------------------------------------------------------------------------
# Plugin entry point: register(ctx)
# ---------------------------------------------------------------------------
def register(ctx):
    """
    Register all Hermes Evolution tools and hooks with the Hermes Agent runtime.

    Args:
        ctx: The plugin registration context provided by the Hermes runtime.
             Provides ctx.register_tool(name=..., toolset="hermes-evolution", schema=..., handler=...) and
             ctx.register_hook(hook_name, callback).
    """
    # ── Schema migration: ensure all databases are at latest version ──────
    from evolution.schema import initialize_all
    initialize_all()

    # Ensure console logging is set up for the plugin
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s [hermes-evolution] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    # Ensure data directory exists (uses EVOLUTION_DATA_DIR or ~/.hermes/data/evolution/)
    get_data_dir()

    # ── Register Tools ──────────────────────────────────────────────────
    tools = [
        ("evolution_run_cycle", TOOL_RUN_CYCLE_SCHEMA, _handle_run_cycle),
        ("evolution_create_tool", TOOL_CREATE_TOOL_SCHEMA, _handle_create_tool),
        ("evolution_analyze_performance", TOOL_ANALYZE_PERFORMANCE_SCHEMA, _handle_analyze_performance),
        ("evolution_learn", TOOL_LEARN_SCHEMA, _handle_learn),
        ("evolution_self_monitor", TOOL_SELF_MONITOR_SCHEMA, _handle_self_monitor),
        ("evolution_memory_discover", TOOL_MEMORY_DISCOVER_SCHEMA, _handle_memory_discover),
        ("evolution_audit", TOOL_AUDIT_SCHEMA, _handle_audit),
        ("evolution_recall_lessons", TOOL_RECALL_LESSONS_SCHEMA, _handle_recall_lessons),
    ]

    for name, schema, handler in tools:
        try:
            ctx.register_tool(name=name, toolset="hermes-evolution",
                              schema=schema, handler=handler)
            logger.info("Registered tool: %s", name)
        except Exception as e:
            logger.error("Failed to register tool %s: %s", name, e)

    # ── Register Hooks (V7: 4 hooks) ───────────────────────────────────
    hooks = [
        ("post_tool_call", _on_post_tool_call),
        ("on_session_start", _on_session_start),
        ("pre_llm_call", _on_pre_llm_call),
        ("post_llm_call", _on_post_llm_call),
    ]
    for hook_name, callback in hooks:
        try:
            ctx.register_hook(hook_name, callback)
            logger.info("Registered hook: %s", hook_name)
        except Exception as e:
            logger.error("Failed to register hook %s: %s", hook_name, e)

    manifest_version = "7.0.5"  # read from plugin.yaml
    logger.info(
        "Hermes Evolution Plugin v%s registered — 8 tools + 4 hooks", manifest_version
    )

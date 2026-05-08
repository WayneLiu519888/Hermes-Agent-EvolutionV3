"""
Hermes Evolution Plugin

Provides 6 tools + 1 hook for the Hermes Agent self-evolution system:
  Tools:
    - evolution_run_cycle      — trigger one full evolution cycle (monitor→analyze→plan→execute→verify→feedback)
    - evolution_create_tool    — create a new tool from an API description
    - evolution_analyze_performance — analyze tool performance metrics
    - evolution_learn          — record an experience / lesson learned
    - evolution_self_monitor   — get current system health status
    - evolution_memory_discover — discover associations between memories

  Hook:
    - post_tool_call           — auto-records tool execution experience
"""

import json
import sys
import logging
import os
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("hermes_evolution_plugin")

# ---------------------------------------------------------------------------
# Module-level singletons — lazily initialized
# ---------------------------------------------------------------------------
_engine_instances = {}

# ---------------------------------------------------------------------------
# Helper: resolve evolution data directory (shared with db_utils)
# ---------------------------------------------------------------------------
def _get_data_dir():
    """Get the evolution data directory (~/.hermes/data/evolution/).
    
    Mirrors db_utils._resolve_data_dir() to avoid import dependency.
    Uses EVOLUTION_DATA_DIR env var if set, otherwise ~/.hermes/data/evolution/.
    """
    env_dir = os.environ.get("EVOLUTION_DATA_DIR")
    if env_dir:
        return Path(env_dir)
    hermes_home = os.environ.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
    data_dir = Path(hermes_home) / "data" / "evolution"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

# ---------------------------------------------------------------------------
# Lazy engine initializers — create instances on demand with fallbacks
# ---------------------------------------------------------------------------
def _get_tool_registry():
    """Get or create a ToolRegistry singleton."""
    if "tool_registry" not in _engine_instances:
        try:
            from evolution.tools import ToolRegistry
            db_path = str(_get_data_dir() / "tools.db")
            _engine_instances["tool_registry"] = ToolRegistry(db_path=db_path)
        except Exception as e:
            logger.warning("Failed to create ToolRegistry: %s", e)
            _engine_instances["tool_registry"] = None
    return _engine_instances["tool_registry"]


def _get_learning_observer():
    """Get or create a LearningObserver singleton."""
    if "learning_observer" not in _engine_instances:
        try:
            from evolution.learning import LearningObserver
            db_path = str(_get_data_dir() / "learning_experiences.db")
            _engine_instances["learning_observer"] = LearningObserver(db_path=db_path)
        except Exception as e:
            logger.warning("Failed to create LearningObserver: %s", e)
            _engine_instances["learning_observer"] = None
    return _engine_instances["learning_observer"]


def _get_orchestrator():
    """Get or create a ClosedLoopOrchestrator singleton."""
    if "orchestrator" not in _engine_instances:
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

            db_base = str(_get_data_dir())

            # Wire dependencies
            observer = LearningObserver(db_path=os.path.join(db_base, "learning_experiences.db"))
            analyzer = ExperienceAnalyzer(observer)
            strategy_learner = ToolStrategyLearner()
            self_monitor = SelfMonitor(observer, analyzer, strategy_learner)
            metrics_collector = SystemMetricsCollector()
            pattern_recognizer = PatternRecognizer()
            from evolution.closed_loop import ActionExecutor
            action_executor = ActionExecutor()

            _engine_instances["orchestrator"] = ClosedLoopOrchestrator(
                metrics_collector=metrics_collector,
                self_monitor=self_monitor,
                experience_analyzer=analyzer,
                pattern_recognizer=pattern_recognizer,
                strategy_learner=strategy_learner,
                action_executor=action_executor,
                learning_observer=observer,
            )
            # Cache sub-components for reuse
            _engine_instances["learning_observer"] = observer
            _engine_instances["self_monitor"] = self_monitor
            _engine_instances["experience_analyzer"] = analyzer
            _engine_instances["strategy_learner"] = strategy_learner
        except Exception as e:
            logger.warning("Failed to create ClosedLoopOrchestrator: %s", e)
            _engine_instances["orchestrator"] = None
    return _engine_instances["orchestrator"]


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
                db_path = str(_get_data_dir() / "tool_performance.db")
                _engine_instances["tool_performance_analyzer"] = ToolPerformanceAnalyzer(
                    registry=registry, db_path=db_path
                )
        except Exception as e:
            logger.warning("Failed to create ToolPerformanceAnalyzer: %s", e)
            _engine_instances["tool_performance_analyzer"] = None
    return _engine_instances["tool_performance_analyzer"]


def _get_association_discoverer():
    """Get or create an AssociationDiscoverer singleton."""
    if "association_discoverer" not in _engine_instances:
        try:
            from evolution.memory import AssociationDatabase, AssociationDiscoverer
            db_path = str(_get_data_dir() / "associations.db")
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
            from datetime import timedelta
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
        import uuid

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

        if entry_id:
            result = discoverer.discover_for_entry(entry_id, methods=methods)
        else:
            result = discoverer.discover_all(methods=methods)

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
        import uuid

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

    except Exception:
        # Hook must never raise — silently log and continue
        pass


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
    # Ensure console logging is set up for the plugin
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s [hermes-evolution] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    # Ensure data directory exists (uses EVOLUTION_DATA_DIR or ~/.hermes/data/evolution/)
    _get_data_dir()

    # ── Register Tools ──────────────────────────────────────────────────
    tools = [
        ("evolution_run_cycle", TOOL_RUN_CYCLE_SCHEMA, _handle_run_cycle),
        ("evolution_create_tool", TOOL_CREATE_TOOL_SCHEMA, _handle_create_tool),
        ("evolution_analyze_performance", TOOL_ANALYZE_PERFORMANCE_SCHEMA, _handle_analyze_performance),
        ("evolution_learn", TOOL_LEARN_SCHEMA, _handle_learn),
        ("evolution_self_monitor", TOOL_SELF_MONITOR_SCHEMA, _handle_self_monitor),
        ("evolution_memory_discover", TOOL_MEMORY_DISCOVER_SCHEMA, _handle_memory_discover),
    ]

    for name, schema, handler in tools:
        try:
            ctx.register_tool(name=name, toolset="hermes-evolution",
                              schema=schema, handler=handler)
            logger.info("Registered tool: %s", name)
        except Exception as e:
            logger.error("Failed to register tool %s: %s", name, e)

    # ── Register Hook ───────────────────────────────────────────────────
    try:
        ctx.register_hook("post_tool_call", _on_post_tool_call)
        logger.info("Registered hook: post_tool_call")
    except Exception as e:
        logger.error("Failed to register hook post_tool_call: %s", e)

    manifest_version = "3.0.3"  # read from plugin.yaml
    logger.info(
"Hermes Evolution Plugin v3.0.3 registered — 6 tools + 1 hook"
    )

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

# ---------------------------------------------------------------------------
# Tool 1: evolution_run_cycle
# ---------------------------------------------------------------------------
TOOL_RUN_CYCLE_SCHEMA = {
    "name": "evolution_run_cycle",
    "description": "Trigger one full evolution cycle.",
    "parameters": {"type": "object", "properties": {}, "required": []},
}

def _handle_run_cycle(params, **kwargs):
    _debug_tag = "_handle_run_cycle V8-DEBUG-002"
    try:
        from evolution.closed_loop import ClosedLoopOrchestrator, SystemMetricsCollector, ActionExecutor
        from evolution.learning import LearningObserver, ExperienceAnalyzer, PatternRecognizer, ToolStrategyLearner
        from evolution.tools.tool_registry import ToolRegistry
        from evolution.tools.tool_integration import ToolEvolutionEngine
        from evolution import SelfMonitor
        from evolution.db_utils import get_data_dir
        db = str(get_data_dir())
        obs = LearningObserver(db_path=db + "/learning_experiences.db")
        strategy_learner = ToolStrategyLearner(db_path=db + "/tools.db")
        tool_registry = ToolRegistry(db_path=db + "/tools.db")
        tool_engine = ToolEvolutionEngine(registry=tool_registry)
        mon = SelfMonitor(obs, ExperienceAnalyzer(obs), strategy_learner)
        orch = ClosedLoopOrchestrator(
            metrics_collector=SystemMetricsCollector(),
            self_monitor=mon, experience_analyzer=ExperienceAnalyzer(obs),
            pattern_recognizer=PatternRecognizer(),
            strategy_learner=strategy_learner,
            action_executor=ActionExecutor(
                strategy_learner=strategy_learner,
                tool_evolution_engine=tool_engine,
                tool_registry=tool_registry,
                pattern_recognizer=PatternRecognizer(),
            ),
            learning_observer=obs,
            tool_evolution_engine=tool_engine)
        result = orch.run_full_cycle()
        result["success"] = True
        result["_debug_tag"] = _debug_tag
        result["cycle_id"] = orch.cycle_history[-1].get("cycle_id") if orch.cycle_history else 0
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 2: evolution_create_tool
# ---------------------------------------------------------------------------
TOOL_CREATE_TOOL_SCHEMA = {
    "name": "evolution_create_tool",
    "description": "Create a new tool from an API description.",
    "parameters": {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Name of the tool"},
            "description": {"type": "string", "description": "Tool description"},
            "api_spec": {"type": "object", "description": "API spec with endpoint, method, parameters"},
            "category": {"type": "string", "description": "Tool category", "default": "custom"},
            "tags": {"type": "array", "items": {"type": "string"}, "description": "Optional tags"},
        },
        "required": ["tool_name", "description", "api_spec"],
    },
}

def _handle_create_tool(params, **kwargs):
    try:
        from evolution.tools.tool_creator import ToolCreator
        creator = ToolCreator()
        result = creator.create_from_code(
            name=params["tool_name"], description=params.get("description", ""),
            code=params.get("api_spec", {}).get("code", "# placeholder"),
            category=params.get("category", "custom"),
            parameters=params.get("api_spec", {}).get("parameters"),
            tags=params.get("tags", []))
        return json.dumps({"success": result.success, "tool_definition": str(result.tool_definition) if result.tool_definition else None,
                           "message": result.error_message or "created"}, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 3: evolution_analyze_performance
# ---------------------------------------------------------------------------
TOOL_ANALYZE_PERFORMANCE_SCHEMA = {
    "name": "evolution_analyze_performance",
    "description": "Analyze tool performance metrics.",
    "parameters": {
        "type": "object",
        "properties": {
            "tool_name": {"type": "string", "description": "Specific tool name (optional)"},
            "output_format": {"type": "string", "enum": ["json", "text", "html"], "default": "json"},
        },
        "required": [],
    },
}

def _handle_analyze_performance(params, **kwargs):
    try:
        from evolution.tools.tool_performance_analyzer import ToolPerformanceAnalyzer
        from evolution.tools.tool_registry import ToolRegistry
        from evolution.db_utils import get_data_dir
        db = str(get_data_dir())
        registry = ToolRegistry(db_path=db + "/tools.db")
        analyzer = ToolPerformanceAnalyzer(registry=registry, db_path=db + "/tool_performance.db")
        tool_name = params.get("tool_name")
        output_format = params.get("output_format", "json")
        if tool_name:
            summary = analyzer.analyze_tool_performance(tool_name)
            result = json.dumps({
                "success": True,
                "tool_name": summary.tool_name,
                "overall_score": summary.overall_score,
                "performance_level": summary.performance_level.value,
                "key_insights": summary.key_insights,
                "optimization_opportunities": summary.optimization_opportunities,
            }, default=str, ensure_ascii=False)
            return result
        else:
            report = analyzer.generate_performance_report(output_format)
            # 统一返回格式：JSON 模式下包裹 success 字段
            if output_format == "json":
                try:
                    parsed = json.loads(report)
                    return json.dumps({"success": True, **parsed}, default=str, ensure_ascii=False)
                except json.JSONDecodeError:
                    pass
            return report
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 4: evolution_learn
# ---------------------------------------------------------------------------
TOOL_LEARN_SCHEMA = {
    "name": "evolution_learn",
    "description": "Record a learning experience.",
    "parameters": {
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Experience description"},
            "experience_type": {"type": "string", "enum": ["tool_usage","reasoning","problem_solving","error_recovery","pattern_recognition","adaptation"], "default": "tool_usage"},
            "outcome": {"type": "string", "enum": ["success","partial_success","failure","uncertain"], "default": "success"},
            "task_id": {"type": "string", "default": ""},
            "lessons": {"type": "array", "items": {"type": "string"}},
            "metrics": {"type": "object"},
            "tags": {"type": "array", "items": {"type": "string"}},
            "context": {"type": "object"},
        },
        "required": ["description"],
    },
}

def _handle_learn(params, **kwargs):
    try:
        from evolution.learning import Experience, ExperienceType, Outcome
        from evolution.learning.observer import LearningObserver
        from evolution.db_utils import get_data_dir
        import uuid
        observer = LearningObserver(db_path=str(get_data_dir() / "learning_experiences.db"))
        exp = Experience(
            id=str(uuid.uuid4()),
            experience_type=getattr(ExperienceType, params.get("experience_type", "TOOL_USAGE").upper(), ExperienceType.TOOL_USAGE),
            task_id=params.get("task_id", ""), timestamp=datetime.now(),
            description=params["description"],
            context=params.get("context", {}), actions=[],
            outcome=getattr(Outcome, params.get("outcome", "SUCCESS").upper(), Outcome.SUCCESS),
            metrics=params.get("metrics", {}), lessons_learned=params.get("lessons", []),
            tags=params.get("tags", []))
        exp.calculate_confidence()
        eid = observer.record_experience(exp)
        return json.dumps({"success": True, "experience_id": eid, "timestamp": datetime.now().isoformat()})
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 5: evolution_self_monitor
# ---------------------------------------------------------------------------
TOOL_SELF_MONITOR_SCHEMA = {
    "name": "evolution_self_monitor",
    "description": "Get system health status.",
    "parameters": {
        "type": "object",
        "properties": {"include_history": {"type": "boolean", "default": False}},
        "required": [],
    },
}

def _handle_self_monitor(params, **kwargs):
    _debug_tag = "_handle_self_monitor V8-DEBUG-001"
    try:
        from evolution.learning import LearningObserver
        from evolution.db_utils import get_data_dir
        observer = LearningObserver(db_path=str(get_data_dir() / "learning_experiences.db"))
        recent = observer.get_recent_experiences(days=7)
        total = len(recent)
        failures = sum(1 for e in recent if getattr(e, 'outcome', None) and str(e.outcome).lower() == 'failure')
        success_rate = (total - failures) / max(total, 1)
        return json.dumps({
            "success": True,
            "_debug_tag": _debug_tag,
            "health_score": int(success_rate * 80 + 20),
            "status": "healthy" if success_rate > 0.8 else "needs_attention",
            "metrics": {"success_rate": round(success_rate, 2), "total_experiences": total,
                        "monitored_tools": 8, "current_strategy": "V7.0.13-standalone"},
            "timestamp": datetime.now().isoformat()
        }, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 6: evolution_memory_discover
# ---------------------------------------------------------------------------
TOOL_MEMORY_DISCOVER_SCHEMA = {
    "name": "evolution_memory_discover",
    "description": "Discover memory associations.",
    "parameters": {
        "type": "object",
        "properties": {
            "methods": {"type": "array", "items": {"type": "string", "enum": ["semantic","temporal","usage_pattern"]}},
            "entry_id": {"type": "string"},
            "max_entries": {"type": "integer", "default": 200, "minimum": 1, "maximum": 500},
        },
        "required": [],
    },
}

def _handle_memory_discover(params, **kwargs):
    try:
        from evolution.memory.association_discoverer import AssociationDiscoverer
        from evolution.memory.database import AssociationDatabase
        from evolution.db_utils import get_data_dir
        db = AssociationDatabase(str(get_data_dir() / "associations.db"))
        discoverer = AssociationDiscoverer(db)
        entry_id = params.get("entry_id")
        methods = params.get("methods")
        max_entries = params.get("max_entries", 200)
        result = discoverer.discover_for_entry(entry_id, methods=methods) if entry_id else discoverer.discover_all(methods=methods, max_entries=max_entries)
        return json.dumps({"success": True, "entry_id": entry_id, "total_associations": result.get("total_associations", 0),
                           "methods": result.get("methods", {}), "timestamp": datetime.now().isoformat()}, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 7: evolution_audit
# ---------------------------------------------------------------------------
TOOL_AUDIT_SCHEMA = {
    "name": "evolution_audit",
    "description": "Query evolution audit records.",
    "parameters": {
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["query_cycles","get_cycle_detail","get_summary","get_health_trend","get_recent_issues","query_issues_by_type","query_issues_by_severity"], "default": "get_summary"},
            "cycle_id": {"type": "integer"},
            "limit": {"type": "integer", "default": 10},
            "success_only": {"type": "boolean", "default": False},
            "issue_type": {"type": "string"},
            "severity": {"type": "string", "enum": ["critical","high","medium","low"]},
        },
        "required": [],
    },
}

def _handle_audit(params, **kwargs):
    try:
        from evolution.closed_loop.evolution_auditor import EvolutionAuditor
        from evolution.db_utils import get_data_dir
        auditor = EvolutionAuditor(db_path=str(get_data_dir() / "evolution_audit.db"))
        action = params.get("action", "get_summary")
        if action == "query_cycles":
            result = auditor.query_cycles(limit=params.get("limit", 10), success_only=params.get("success_only", False))
        elif action == "get_cycle_detail":
            result = auditor.get_cycle_detail(cycle_id=params.get("cycle_id"))
        elif action == "get_health_trend":
            result = auditor.get_latest_health_trend()
        elif action == "get_recent_issues":
            result = auditor.get_latest_issues(limit=params.get("limit", 10))
        elif action == "query_issues_by_type":
            result = auditor.query_issues_by_type(issue_type=params.get("issue_type", ""))
        elif action == "query_issues_by_severity":
            result = auditor.query_issues_by_severity(severity=params.get("severity", "medium"))
        else:
            result = auditor.get_summary()
        return json.dumps(result, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

# ---------------------------------------------------------------------------
# Tool 8: evolution_recall_lessons
# ---------------------------------------------------------------------------
TOOL_RECALL_LESSONS_SCHEMA = {
    "name": "evolution_recall_lessons",
    "description": "Recall historical lessons.",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "default": 5, "minimum": 1, "maximum": 20},
            "outcome": {"type": "string", "enum": ["failure","success","all"], "default": "all"},
        },
        "required": [],
    },
}

def _handle_recall_lessons(params, **kwargs):
    try:
        from evolution.consumer import AssociationConsumer
        from evolution.db_pool import db_pool as dp
        consumer = AssociationConsumer(dp)
        lessons = consumer.recall_lessons(limit=params.get("limit", 5), outcome=params.get("outcome", "all"))
        return json.dumps({"success": True, "count": len(lessons), "lessons": lessons,
                           "timestamp": datetime.now().isoformat()}, default=str, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"success": False, "error": str(e), "timestamp": datetime.now().isoformat()})

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

        # V9.0.0: 初始化会话状态机
        try:
            from evolution.memory.session_state import SessionStateTracker
            SessionStateTracker.for_session(session_id)
        except Exception:
            pass

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
        # V9.0.0: 学习洞察注入
        try:
            from evolution.memory.insight_injector import InsightInjector
            injector = InsightInjector()
            insights = injector.inject_insights(user_msg.get("content", ""))
            if insights:
                context = (context + "\n" + insights) if context else insights
        except Exception:
            pass
        # V9.0.0: 会话状态感知注入
        try:
            from evolution.memory.session_state import SessionStateTracker
            sess_id = kwargs.get('session_id', '') or ''
            tracker = SessionStateTracker._instances.get(sess_id)
            if tracker:
                tracker.record_user_message(user_msg.get("content", ""))
                state_inj = tracker.generate_injection(
                    user_msg.get("content", ""),
                    existing_context=context,
                )
                if state_inj:
                    context = (context + "\n" + state_inj) if context else state_inj
        except Exception:
            pass
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
    """LLM 回复后：关联质量打分 + 缓存对话摘要（V7.0.9: 异步Agent提取）"""
    try:
        from evolution.db_pool import db_pool
        consumer = AssociationConsumer(db_pool)
        text = response if isinstance(response, str) else response.get("content", "")
        if text:
            consumer.score_usage(text)
        consumer.cleanup()

        # V7.0.9: 缓存对话摘要（只存不提取，留给后台知识Agent）
        user_msg = _last_user_message(messages)
        if user_msg and text:
            _cache_conversation(user_msg, text)

        # V9.0.0: 同步轻量知识提取（规则引擎，零延迟）
        if user_msg and text:
            _sync_extract_knowledge(user_msg, text)

        # V9.0.0: 会话状态更新 — 记录LLM回复中的话题和决策
        try:
            from evolution.memory.session_state import SessionStateTracker
            sess_id = kwargs.get('session_id', '') or ''
            tracker = SessionStateTracker._instances.get(sess_id)
            if tracker and text:
                tracker.record_llm_reply(text)
        except Exception:
            pass
    except Exception as exc:
        logger.debug("post_llm_call hook: %s", exc)


# ---------------------------------------------------------------------------
# V9.0.0: 同步轻量知识提取 — 规则引擎从LLM回复中提取关键知识点
# ---------------------------------------------------------------------------
def _sync_extract_knowledge(user_msg: str, llm_reply: str) -> None:
    """规则引擎从LLM回复中同步提取关键知识点，直接写入memory_entries。

    不调LLM，零延迟。提取不到则静默跳过。
    """
    import sqlite3
    import re

    knowledge_items = []

    # ── 提取器1: 关键技术决策 ──
    decision_patterns = [
        (r'决定[：:]?\s*(.+?)(?:[。\n]|$)', '决策'),
        (r'采用[：:]?\s*(.+?)(?:[。\n]|$)', '决策'),
        (r'最终选择[：:]?\s*(.+?)(?:[。\n]|$)', '决策'),
        (r'最终方案[：:]?\s*(.+?)(?:[。\n]|$)', '决策'),
        (r'推荐用[：:]?\s*(.+?)(?:[。\n]|$)', '推荐'),
    ]
    for pattern, category in decision_patterns:
        for match in re.finditer(pattern, llm_reply):
            content = match.group(1).strip()[:200]
            if len(content) >= 8:
                knowledge_items.append({
                    'content': content,
                    'content_type': 'sync_extract',
                    'tags': f'决策,{category}',
                    'confidence': 0.75,
                })

    # ── 提取器2: 结构化结论 ──
    summary_patterns = [
        r'#{1,3}\s*(?:总结|结论|要点)[：:]?\s*\n+(.+?)(?:\n\n|\n#|$)',
        r'\*\*(?:总结|结论|要点|关键发现)\*\*[：:]?\s*(.+?)(?:\n\n|\n\*\*|$)',
    ]
    for pattern in summary_patterns:
        for match in re.finditer(pattern, llm_reply, re.DOTALL):
            content = match.group(1).strip()[:200]
            if len(content) >= 10:
                knowledge_items.append({
                    'content': content,
                    'content_type': 'sync_extract',
                    'tags': '总结,关键发现',
                    'confidence': 0.85,
                })

    # ── 提取器3: 错误/修复 模式 ──
    fix_patterns = [
        (r'(?:修复|解决|修正).{0,10}?(?:方法|方案|步骤)[：:]?\s*(.+?)(?:[。\n]|$)', '修复'),
        (r'根因[是：:]\s*(.+?)(?:[。\n]|$)', '根因'),
        (r'原因是[：:]?\s*(.+?)(?:[。\n]|$)', '原因'),
    ]
    for pattern, category in fix_patterns:
        for match in re.finditer(pattern, llm_reply):
            content = match.group(1).strip()[:200]
            if len(content) >= 8:
                knowledge_items.append({
                    'content': content,
                    'content_type': 'sync_extract',
                    'tags': f'修复,{category}',
                    'confidence': 0.70,
                })

    if not knowledge_items:
        return

    # ── 去重 + 写入 ──
    try:
        from evolution.db_utils import get_data_dir
        db_path = str(get_data_dir() / "associations.db")
        conn = sqlite3.connect(db_path)

        existing = set()
        try:
            rows = conn.execute(
                "SELECT content FROM memory_entries WHERE content_type='sync_extract'"
            ).fetchall()
            for (c,) in rows:
                existing.add(c[:80] if c else '')
        except sqlite3.OperationalError:
            pass

        now = datetime.now().isoformat()
        inserted = 0
        for item in knowledge_items:
            prefix = item['content'][:80]
            if prefix in existing:
                continue
            try:
                conn.execute(
                    "INSERT INTO memory_entries (content, content_type, tags, confidence, "
                    "created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                    (item['content'], item['content_type'], item['tags'],
                     item['confidence'], now, now)
                )
                conn.commit()
                inserted += 1
                existing.add(prefix)
            except sqlite3.OperationalError:
                pass

        if inserted > 0:
            logger.debug("sync_extract: 提取 %d 条知识点", inserted)

        conn.close()
    except Exception:
        pass


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
# Hook: post_tool_call — tool execution experience + memory sync
# ---------------------------------------------------------------------------
def _on_post_tool_call(ctx, tool_name, params, result, duration_ms, error):
    """Hook for post_tool_call: auto-record experience + sync memory"""
    try:
        from evolution.learning import Experience, ExperienceType, Outcome
        from evolution.learning.observer import LearningObserver
        from evolution.db_utils import get_data_dir
        import uuid
        observer = LearningObserver(db_path=str(get_data_dir() / "learning_experiences.db"))
        if observer is None:
            return
        outcome = Outcome.FAILURE if error else (Outcome.SUCCESS if result is not None else Outcome.UNCERTAIN)
        exp = Experience(
            id=str(uuid.uuid4()), experience_type=ExperienceType.TOOL_USAGE,
            task_id=f"tool_call_{tool_name}", timestamp=datetime.now(),
            description=f"Tool execution: {tool_name}", context={"tool_name": tool_name},
            outcome=outcome, metrics={"duration_ms": float(duration_ms) if duration_ms else 0},
            tags=["auto_recorded", tool_name])
        exp.calculate_confidence()
        observer.record_experience(exp)
    except Exception:
        pass

    # V7.0.8: hermes memory sync
    if tool_name == "memory" and not error:
        try:
            _sync_hermes_memory(params)
        except Exception:
            pass

    # V8.0.18: 写入 tool_usage_history，消除两套追踪系统割裂
    try:
        import sqlite3
        from evolution.db_utils import get_data_dir
        conn = sqlite3.connect(str(get_data_dir() / "tools.db"))
        success_val = 1 if error is None and result is not None else 0
        exec_ms = float(duration_ms) if duration_ms else 0
        conn.execute(
            "INSERT INTO tool_usage_history (tool_name, success, execution_time, timestamp, context) "
            "VALUES (?, ?, ?, ?, ?)",
            (tool_name, success_val, exec_ms / 1000.0, datetime.now().isoformat(),
             '{"source": "post_tool_call_hook"}'))
        conn.commit()
        conn.close()
    except Exception:
        pass

    # V9.0.0: 会话状态 — 记录工具调用失败
    if error:
        try:
            from evolution.memory.session_state import SessionStateTracker
            sess_id = getattr(ctx, 'session_id', '') or ''
            tracker = SessionStateTracker._instances.get(sess_id)
            if tracker:
                tracker.record_tool_error(tool_name, str(error))
        except Exception:
            pass


# ── Python import 缓存绕过：每次工具调用强制 reload 最新 handler ──
import importlib as _importlib

def _make_dynamic_handler(tool_name):
    """生成动态 handler：每次调用重新 import plugin_core 获取最新函数。"""
    _handler_attr = {
        "evolution_run_cycle": "_handle_run_cycle",
        "evolution_create_tool": "_handle_create_tool",
        "evolution_analyze_performance": "_handle_analyze_performance",
        "evolution_learn": "_handle_learn",
        "evolution_self_monitor": "_handle_self_monitor",
        "evolution_memory_discover": "_handle_memory_discover",
        "evolution_audit": "_handle_audit",
        "evolution_recall_lessons": "_handle_recall_lessons",
    }
    attr_name = _handler_attr[tool_name]
    
    def dynamic_handler(params, **kwargs):
        import time as _t
        _debug_ts = str(_t.time())
        try:
            _importlib.invalidate_caches()
            # 清除所有 HAE 子模块缓存，强制完整重新加载
            import sys as _sys
            _to_clear = [k for k in list(_sys.modules.keys()) 
                        if k.startswith('evolution.')]
            for k in _to_clear:
                _sys.modules.pop(k, None)
            mod = _importlib.import_module("evolution.plugin_core")
            fn = getattr(mod, attr_name, None)
            if fn:
                result = fn(params, **kwargs)
                # 嵌入调试标记，确认 handler 被执行
                if isinstance(result, str) and result.startswith('{'):
                    try:
                        import json
                        data = json.loads(result)
                        data['_debug_handler'] = f'{attr_name} via dynamic reload @ {_debug_ts}'
                        return json.dumps(data, default=str, ensure_ascii=False)
                    except Exception:
                        pass
                return result
        except Exception as e:
            pass
        mod = _importlib.import_module("evolution.plugin_core")
        fn = getattr(mod, attr_name)
        result = fn(params, **kwargs)
        if isinstance(result, str) and result.startswith('{'):
            try:
                import json
                data = json.loads(result)
                data['_debug_handler'] = f'{attr_name} via fallback @ {_debug_ts}'
                return json.dumps(data, default=str, ensure_ascii=False)
            except Exception:
                pass
        return result
    return dynamic_handler


# ---------------------------------------------------------------------------
# Plugin entry point: register(ctx)
# ---------------------------------------------------------------------------
def register(ctx):
    """Register all Hermes Evolution tools and hooks."""
    from evolution.schema import initialize_all
    initialize_all()

    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter('%(levelname)s [hermes-evolution] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    get_data_dir()

    tools = [
        ("evolution_run_cycle", TOOL_RUN_CYCLE_SCHEMA, _make_dynamic_handler("evolution_run_cycle")),
        ("evolution_create_tool", TOOL_CREATE_TOOL_SCHEMA, _make_dynamic_handler("evolution_create_tool")),
        ("evolution_analyze_performance", TOOL_ANALYZE_PERFORMANCE_SCHEMA, _make_dynamic_handler("evolution_analyze_performance")),
        ("evolution_learn", TOOL_LEARN_SCHEMA, _make_dynamic_handler("evolution_learn")),
        ("evolution_self_monitor", TOOL_SELF_MONITOR_SCHEMA, _make_dynamic_handler("evolution_self_monitor")),
        ("evolution_memory_discover", TOOL_MEMORY_DISCOVER_SCHEMA, _make_dynamic_handler("evolution_memory_discover")),
        ("evolution_audit", TOOL_AUDIT_SCHEMA, _make_dynamic_handler("evolution_audit")),
        ("evolution_recall_lessons", TOOL_RECALL_LESSONS_SCHEMA, _make_dynamic_handler("evolution_recall_lessons")),
    ]

    for name, schema, handler in tools:
        try:
            ctx.register_tool(name=name, toolset="hermes-evolution", schema=schema, handler=handler)
            logger.info("Registered tool: %s", name)
        except Exception as e:
            logger.error("Failed to register tool %s: %s", name, e)

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

    logger.info("Hermes Evolution Plugin v7.0.13 registered — 8 tools + 4 hooks")

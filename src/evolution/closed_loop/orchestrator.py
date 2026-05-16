"""
ClosedLoopOrchestrator — 闭环编排器
负责编排 Monitor → Analyze → Plan → Execute → Verify → Feedback 全流程

这是流程的核心协调者，连接所有子系统组件。
"""

import logging
import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ImprovementAction:
    """改进动作"""
    action_id: str
    action_type: str  # tool_optimization, strategy_switch, parameter_tuning, tool_creation, tool_deprecation
    target: str  # 目标组件/工具名
    description: str
    priority: str  # critical, high, medium, low
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_benefit: str = ""
    risk: str = "low"  # low, medium, high


class ClosedLoopOrchestrator:
    """
    闭环编排器
    
    协调所有进化子系统，执行完整的进化闭环。
    
    连接组件:
    - SystemMetricsCollector: 采集系统指标 (Phase 1)
    - SelfMonitor + ExperienceAnalyzer: 分析 (Phase 2)
    - PatternRecognizer + ToolStrategyLearner: 规划 (Phase 3)
    - ActionExecutor + ToolEvolutionEngine: 执行 (Phase 4)
    - Metrics verification: 验证 (Phase 5)
    - LearningObserver: 反馈 (Phase 6)
    """
    
    def __init__(self, 
                 metrics_collector: 'SystemMetricsCollector',
                 self_monitor,
                 experience_analyzer,
                 pattern_recognizer,
                 strategy_learner,
                 action_executor: 'ActionExecutor',
                 learning_observer,
                 tool_evolution_engine=None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Args:
            metrics_collector: 系统指标采集器
            self_monitor: 自我监控器
            experience_analyzer: 经验分析器
            pattern_recognizer: 模式识别器
            strategy_learner: 策略学习器
            action_executor: 动作执行器
            learning_observer: 学习观察器
            tool_evolution_engine: 工具进化引擎（可选）
            config: 配置
        """
        self.metrics_collector = metrics_collector
        self.self_monitor = self_monitor
        self.experience_analyzer = experience_analyzer
        self.pattern_recognizer = pattern_recognizer
        self.strategy_learner = strategy_learner
        self.action_executor = action_executor
        self.learning_observer = learning_observer
        self.tool_evolution_engine = tool_evolution_engine
        self.config = config or {}
        
        # 性能阈值
        self.success_rate_threshold = self.config.get('success_rate_threshold', 0.6)
        self.tool_performance_threshold = self.config.get('tool_performance_threshold', 60.0)
        self.strategy_improvement_delta = self.config.get('strategy_improvement_delta', 0.1)
        
        # 统计
        self.cycle_history: List[Dict[str, Any]] = []
        
        logger.info("ClosedLoopOrchestrator 初始化完成")
    
    # ═══════════════════════════════════════════
    # Phase 1: Monitor — 采集系统指标
    # ═══════════════════════════════════════════
    
    def monitor(self) -> Dict[str, Any]:
        """
        Phase 1: 采集系统当前指标
        
        Returns:
            系统指标字典
        """
        logger.info("📊 [Monitor] 采集系统指标...")
        
        try:
            metrics = self.metrics_collector.collect_all()
            logger.info(f"  采集完成: {len(metrics)} 个指标维度")
            return metrics
        except Exception as e:
            logger.warning(f"指标采集异常: {e}，使用最小集")
            return self.metrics_collector.collect_minimal()
    
    # ═══════════════════════════════════════════
    # Phase 2: Analyze — 分析数据模式
    # ═══════════════════════════════════════════
    
    def analyze(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 2: 分析采集到的指标，识别模式和问题
        
        Args:
            metrics: Phase 1 采集的指标
            
        Returns:
            分析结果
        """
        logger.info("🔍 [Analyze] 分析数据...")
        
        analysis = {
            'patterns': [],
            'issues': [],
            'insights': [],
            'performance': {},
            'timestamp': datetime.now().isoformat(),
        }
        
        # 2.1 分析系统健康
        if self.self_monitor:
            try:
                health = self.self_monitor.monitor_and_improve()
                analysis['health'] = health
                if health.get('analysis', {}).get('success_rate', 0) < self.success_rate_threshold:
                    analysis['issues'].append({
                        'type': 'low_success_rate',
                        'value': health['analysis']['success_rate'],
                        'severity': 'high',
                        'message': f"系统成功率偏低: {health['analysis']['success_rate']:.1%}"
                    })
            except Exception as e:
                logger.warning(f"健康分析异常: {e}")
        
        # 2.2 分析经验模式
        if self.experience_analyzer:
            try:
                exp_analysis = self.experience_analyzer.analyze_recent_experiences(days=7)
                analysis['experience'] = {
                    'total': exp_analysis.total_experiences,
                    'success_rate': exp_analysis.success_rate,
                }
                for insight in exp_analysis.key_insights[:5]:
                    analysis['insights'].append(insight)
            except Exception as e:
                logger.warning(f"经验分析异常: {e}")
        
        # 2.3 分析工具性能
        if self.strategy_learner:
            try:
                tool_summary = self.strategy_learner.get_tool_performance_summary()
                low_perf_tools = [
                    (tool, data) for tool, data in tool_summary.items()
                    if data.get('success_rate', 0) < self.tool_performance_threshold / 100
                    and data.get('usage_count', 0) >= 3
                ]
                analysis['tool_performance'] = {
                    'total_tools': len(tool_summary),
                    'low_performance_tools': [t[0] for t in low_perf_tools],
                }
                
                for tool, data in low_perf_tools:
                    analysis['issues'].append({
                        'type': 'tool_low_performance',
                        'target': tool,
                        'value': data.get('success_rate', 0),
                        'severity': 'medium',
                        'message': f"工具 '{tool}' 性能偏低 (成功率 {data.get('success_rate', 0):.1%})"
                    })
            except Exception as e:
                logger.warning(f"工具性能分析异常: {e}")
        
        # 2.4 模式识别
        if self.pattern_recognizer and self.learning_observer:
            try:
                # PatternRecognizer 需要 Experience 列表
                experiences = self.learning_observer.get_recent_experiences(days=7)
                patterns = self.pattern_recognizer.recognize_patterns(experiences)
                analysis['patterns'] = [
                    {
                        'type': p.category.value if hasattr(p, 'category') else str(type(p).__name__),
                        'confidence': p.confidence if hasattr(p, 'confidence') else 0.5,
                        'description': p.description if hasattr(p, 'description') else str(p),
                    }
                    for p in patterns[:10]
                ]
            except Exception as e:
                logger.warning(f"模式识别异常: {e}")
        
        logger.info(f"  发现 {len(analysis['patterns'])} 个模式, {len(analysis['issues'])} 个问题")
        return analysis
    
    # ═══════════════════════════════════════════
    # Phase 3: Plan — 生成改进计划
    # ═══════════════════════════════════════════
    
    def plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 3: 基于分析结果生成具体的改进行动计划
        
        Args:
            analysis: Phase 2 的分析结果
            
        Returns:
            改进计划（含具体动作列表）
        """
        logger.info("📋 [Plan] 生成改进计划...")
        
        plan = {
            'actions': [],
            'strategy_changes': [],
            'tool_changes': [],
            'priority': 'normal',
            'timestamp': datetime.now().isoformat(),
            'summary': '',
        }
        
        actions = []
        
        # 3.1 处理低成功率问题
        for issue in analysis.get('issues', []):
            if issue.get('type') == 'low_success_rate':
                actions.append(ImprovementAction(
                    action_id=f"strategy_opt_{datetime.now().timestamp()}",
                    action_type="strategy_switch",
                    target="global",
                    description=f"系统成功率低 ({issue['value']:.1%})，搜索更优策略",
                    priority="high" if issue['value'] < 0.4 else "medium",
                    parameters={'current_success_rate': issue['value']},
                    expected_benefit="提升系统成功率",
                    risk="medium",
                ))
            
            elif issue.get('type') == 'tool_low_performance':
                tool_name = issue.get('target', '')
                actions.append(ImprovementAction(
                    action_id=f"tool_opt_{tool_name}_{datetime.now().timestamp()}",
                    action_type="tool_optimization",
                    target=tool_name,
                    description=f"优化工具 '{tool_name}' 性能 (成功率 {issue.get('value', 0):.1%})",
                    priority=issue.get('severity', 'medium'),
                    parameters={
                        'tool_name': tool_name,
                        'current_success_rate': issue.get('value', 0),
                    },
                    expected_benefit=f"提升 '{tool_name}' 成功率",
                    risk="low",
                ))
        
        # 3.2 基于模式的策略调整
        for pattern in analysis.get('patterns', []):
            if pattern.get('confidence', 0) > 0.6:
                actions.append(ImprovementAction(
                    action_id=f"pattern_adapt_{datetime.now().timestamp()}",
                    action_type="strategy_switch",
                    target="strategy_learner",
                    description=f"基于模式 '{pattern.get('description', '')}' 调整策略",
                    priority="medium",
                    parameters={
                        'pattern': pattern,
                        'confidence': pattern.get('confidence', 0),
                    },
                    expected_benefit=f"适应识别到的模式 (置信度 {pattern.get('confidence', 0):.1%})",
                    risk="low",
                ))
        
        # 3.3 工具进化引擎建议
        if self.tool_evolution_engine:
            try:
                state = self.tool_evolution_engine.analyze_current_state()
                for tool_name, perf in state.get('performance_summaries', {}).items():
                    score = perf.get('score', 100)
                    if score < self.tool_performance_threshold:
                        # 工具需要进化
                        actions.append(ImprovementAction(
                            action_id=f"evolve_{tool_name}_{datetime.now().timestamp()}",
                            action_type="tool_optimization",
                            target=tool_name,
                            description=f"工具 '{tool_name}' 评分 {score:.0f}/100，触发进化",
                            priority="medium",
                            parameters={'tool_name': tool_name, 'current_score': score},
                            expected_benefit=f"进化工具 '{tool_name}'，目标评分 80+",
                            risk="medium",
                        ))
            except Exception as e:
                logger.warning(f"工具进化分析异常: {e}")
        
        # 3.4 去重 + 优先级排序
        seen = set()
        unique_actions = []
        for action in actions:
            key = (action.action_type, action.target)
            if key not in seen:
                seen.add(key)
                unique_actions.append(action)
        
        # 按优先级排序
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        unique_actions.sort(key=lambda a: priority_order.get(a.priority, 99))
        
        # 限制每次循环的动作数量
        max_actions = self.config.get('max_actions_per_cycle', 5)
        plan['actions'] = [self._action_to_dict(a) for a in unique_actions[:max_actions]]
        
        if unique_actions:
            priorities = [a.priority for a in unique_actions[:max_actions]]
            plan['priority'] = 'critical' if 'critical' in priorities else (
                'high' if 'high' in priorities else 'normal'
            )
        
        action_summaries = ', '.join(
            f"{a['action_type']}→{a['target']}" for a in plan['actions']
        )
        plan['summary'] = (
            f"计划执行 {len(plan['actions'])} 个动作: {action_summaries}"
        )
        
        logger.info(f"  生成 {len(plan['actions'])} 个改进动作: {plan['summary']}")
        return plan
    
    @staticmethod
    def _action_to_dict(action: ImprovementAction) -> Dict[str, Any]:
        return {
            'action_id': action.action_id,
            'action_type': action.action_type,
            'target': action.target,
            'description': action.description,
            'priority': action.priority,
            'parameters': action.parameters,
            'expected_benefit': action.expected_benefit,
            'risk': action.risk,
        }
    
    # ═══════════════════════════════════════════
    # Phase 4: Execute — 执行改进动作
    # ═══════════════════════════════════════════
    
    def execute(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Phase 4: 执行改进计划中的具体动作
        
        Args:
            plan: Phase 3 生成的改进计划
            
        Returns:
            执行结果
        """
        logger.info("⚡ [Execute] 执行改进动作...")
        
        actions = plan.get('actions', [])
        results = {
            'actions': [],
            'success_count': 0,
            'failure_count': 0,
            'skipped_count': 0,
        }
        
        for action_dict in actions:
            action = ImprovementAction(**action_dict)
            action_start = time.perf_counter()
            
            try:
                result = self.action_executor.execute(action)
                action_duration = (time.perf_counter() - action_start) * 1000
                
                action_result = {
                    'action_id': action.action_id,
                    'action_type': action.action_type,
                    'target': action.target,
                    'success': result.get('success', False),
                    'message': result.get('message', ''),
                    'output': result.get('output', {}),
                }
                
                results['actions'].append(action_result)
                
                if result.get('success'):
                    results['success_count'] += 1
                    logger.info(f"  ✅ {action.target}: {action.action_type} — 成功")
                else:
                    results['failure_count'] += 1
                    logger.warning(f"  ❌ {action.target}: {action.action_type} — {result.get('message', '失败')}")
                
                # 持久化到审计数据库
                self._audit_action(
                    cycle_id=None,  # 将在 _audit_cycle 中补设
                    action=action_result,
                    phase="execute",
                    success=result.get('success', False),
                    error=result.get('message') if not result.get('success') else None,
                    duration_ms=action_duration,
                )
                    
            except Exception as e:
                action_duration = (time.perf_counter() - action_start) * 1000
                results['actions'].append({
                    'action_id': action.action_id,
                    'action_type': action.action_type,
                    'target': action.target,
                    'success': False,
                    'message': str(e),
                })
                results['failure_count'] += 1
                logger.error(f"  ❌ {action.target}: 执行异常 — {e}")
                
                self._audit_action(
                    cycle_id=None,
                    action=action_dict,
                    phase="execute",
                    success=False,
                    error=str(e),
                    duration_ms=action_duration,
                )
        
        # 直接在 execute() 内部持久化 actions（绕过 _audit_cycle 的缓存问题）
        self._persist_actions(plan, results)
        
        return results
    
    def _persist_actions(self, plan, exec_results):
        """将执行结果直接持久化到 evolution_actions 表"""
        try:
            from .evolution_auditor import EvolutionAuditor
            from ..db_utils import get_data_dir
            import time as _t
            auditor = EvolutionAuditor(db_path=str(get_data_dir() / "evolution_audit.db"))
            # 生成临时 cycle_id（时间戳）
            cycle_id = int(_t.time() * 1000) % 1000000
            for action in exec_results.get('actions', []):
                auditor.record_action(
                    cycle_id=cycle_id,
                    action=action,
                    phase='execute',
                    success=action.get('success', True),
                    error=action.get('message') if not action.get('success') else None,
                )
        except Exception:
            pass  # 静默失败
    
    # ═══════════════════════════════════════════
    # Phase 5: Verify — 验证改进效果
    # ═══════════════════════════════════════════
    
    def verify(self, metrics_before: Dict[str, Any],
               actions_taken: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Phase 5: 验证执行的动作是否产生了改进效果
        
        Args:
            metrics_before: 改进前的指标
            actions_taken: 已执行的动作列表
            
        Returns:
            验证结果
        """
        logger.info("✅ [Verify] 验证改进效果...")
        
        verification = {
            'improvements': [],
            'regressions': [],
            'unchanged': [],
            'metrics_after': {},
            'verification_score': 0.0,
        }
        
        # 重新采集指标
        try:
            metrics_after = self.metrics_collector.collect_all()
            verification['metrics_after'] = metrics_after
        except Exception as e:
            logger.warning(f"重新采集指标异常: {e}")
            metrics_after = {}
        
        # 对比关键指标
        key_metrics = [
            ('system.success_rate', '成功率', 'higher_better'),
            ('system.response_time_avg', '平均响应时间', 'lower_better'),
            ('system.error_rate', '错误率', 'lower_better'),
            ('tools.total_count', '工具总数', 'neutral'),
            ('tools.active_count', '活跃工具数', 'neutral'),
        ]
        
        for metric_key, metric_name, direction in key_metrics:
            before = metrics_before.get(metric_key)
            after = metrics_after.get(metric_key)
            
            if before is None or after is None:
                continue
            
            delta = after - before
            delta_pct = (delta / before * 100) if before != 0 else 0
            
            if direction == 'higher_better':
                if delta > 0.01:
                    verification['improvements'].append(
                        f"{metric_name}: {before:.3f} → {after:.3f} (+{delta_pct:.1f}%)"
                    )
                elif delta < -0.01:
                    verification['regressions'].append(
                        f"{metric_name}: {before:.3f} → {after:.3f} ({delta_pct:.1f}%)"
                    )
                else:
                    verification['unchanged'].append(metric_name)
            
            elif direction == 'lower_better':
                if delta < -0.01:
                    verification['improvements'].append(
                        f"{metric_name}: {before:.3f} → {after:.3f} ({delta_pct:.1f}%)"
                    )
                elif delta > 0.01:
                    verification['regressions'].append(
                        f"{metric_name}: {before:.3f} → {after:.3f} (+{delta_pct:.1f}%)"
                    )
                else:
                    verification['unchanged'].append(metric_name)
        
        # 计算验证分数
        total = len(verification['improvements']) + len(verification['regressions']) + len(verification['unchanged'])
        if total > 0:
            improvement_score = len(verification['improvements']) / total
            regression_penalty = len(verification['regressions']) / total * 0.5
            verification['verification_score'] = max(0.0, min(1.0, improvement_score - regression_penalty))
        
        logger.info(f"  改进 {len(verification['improvements'])} 项, "
                   f"退化 {len(verification['regressions'])} 项, "
                   f"无变化 {len(verification['unchanged'])} 项, "
                   f"验证分 {verification['verification_score']:.2f}")
        
        return verification
    
    # ═══════════════════════════════════════════
    # Phase 6: Feedback — 记录学习经验
    # ═══════════════════════════════════════════
    
    def feedback(self, snapshot: 'EvolutionSnapshot') -> Dict[str, Any]:
        """
        Phase 6: 将整个进化循环的结果反馈到学习系统
        
        Args:
            snapshot: 进化快照
            
        Returns:
            反馈结果
        """
        logger.info("📝 [Feedback] 记录学习经验...")
        
        feedback = {
            'recorded': False,
            'experience_id': None,
        }
        
        if self.learning_observer:
            try:
                import uuid
                try:
                    from evolution.learning.experience import Experience, ExperienceType, Outcome
                except ImportError:
                    from src.evolution.learning.experience import Experience, ExperienceType, Outcome
                
                # 去重：检查最近是否已存在相同任务的经验
                task_id = f"evolution_cycle_{snapshot.cycle_id}"
                recent = self.learning_observer.get_recent_experiences(days=1, limit=5)
                duplicate = any(
                    getattr(e, 'task_id', '') == task_id
                    for e in (recent if isinstance(recent, list) else [])
                )
                if duplicate:
                    logger.info(f"  经验已存在 (task_id={task_id})，跳过重复记录")
                    feedback['recorded'] = True
                    feedback['experience_id'] = 'duplicate_skipped'
                    return feedback
                
                # 构建 Experience 对象
                exp = Experience(
                    id=str(uuid.uuid4()),
                    experience_type=ExperienceType.ADAPTATION,
                    task_id=f"evolution_cycle_{snapshot.cycle_id}",
                    timestamp=datetime.now(),
                    description=f"进化循环 #{snapshot.cycle_id} — "
                               f"{'成功' if snapshot.success else '失败'} "
                               f"({len(snapshot.actions_taken)} 动作, "
                               f"{len(snapshot.improvements_detected)} 改进)",
                    outcome=Outcome.SUCCESS if snapshot.success else Outcome.FAILURE,
                    metrics={
                        'duration': snapshot.duration_seconds,
                        'actions_count': len(snapshot.actions_taken),
                        'improvements_count': len(snapshot.improvements_detected),
                        'errors_count': len(snapshot.errors),
                    },
                    context={
                        'cycle_id': snapshot.cycle_id,
                        'phases': snapshot.phases_completed,
                        'improvements': snapshot.improvements_detected[:10],
                    },
                    lessons_learned=snapshot.errors if snapshot.errors else [],
                )
                
                exp_id = self.learning_observer.record_experience(exp)
                
                # 如果有工具进化引擎，也记录
                if self.tool_evolution_engine and snapshot.success:
                    for action in snapshot.actions_taken:
                        if action.get('action_type') in ('tool_optimization',):
                            try:
                                self.tool_evolution_engine.learning_integrator.record_tool_execution(
                                    tool_name=action.get('target', 'unknown'),
                                    success=action.get('success', True),
                                    execution_time=snapshot.duration_seconds,
                                    context={
                                        'evolution_cycle': True,
                                        'cycle_id': snapshot.cycle_id,
                                    }
                                )
                            except Exception:
                                pass
                
                feedback['recorded'] = True
                feedback['experience_id'] = str(exp_id) if exp_id else None
                logger.info(f"  学习经验已记录: {feedback['experience_id']}")
                
            except Exception as e:
                logger.warning("记录学习经验异常: %s", e)
                feedback['error'] = str(e)
        
        return feedback
    
    # ═══════════════════════════════════════════
    # 完整闭环（便捷方法 - 一次调用执行全部阶段）
    # ═══════════════════════════════════════════
    
    def run_full_cycle(self) -> Dict[str, Any]:
        """
        执行一次完整的进化闭环（所有 6 个阶段）

        Returns:
            完整循环结果
        """
        cycle_start = time.time()
        cycle_id = len(self.cycle_history) + 1
        trace_id = str(uuid.uuid4())[:8]

        result = {
            'cycle_id': cycle_id,
            'trace_id': trace_id,
            'timestamp': datetime.now().isoformat(),
            'phases': {},
            'summary': '',
            'duration': 0,
        }

        # Phase 1: Monitor
        t0 = time.monotonic()
        metrics = self.monitor()
        elapsed = time.monotonic() - t0
        logger.info(f"[{trace_id}] monitor: {elapsed:.3f}s")
        result['phases']['monitor'] = {'metrics_count': len(metrics), 'elapsed': round(elapsed, 3)}

        # Phase 2: Analyze
        t0 = time.monotonic()
        analysis = self.analyze(metrics)
        elapsed = time.monotonic() - t0
        logger.info(f"[{trace_id}] analyze: {elapsed:.3f}s")
        result['phases']['analyze'] = {
            'patterns': len(analysis.get('patterns', [])),
            'issues': len(analysis.get('issues', [])),
            'elapsed': round(elapsed, 3),
            '_details': analysis,  # 保留完整分析详情供审计持久化
        }

        # Phase 3: Plan
        t0 = time.monotonic()
        plan = self.plan(analysis)
        elapsed = time.monotonic() - t0
        logger.info(f"[{trace_id}] plan: {elapsed:.3f}s")
        result['phases']['plan'] = {
            'actions': len(plan.get('actions', [])),
            'priority': plan.get('priority'),
            'elapsed': round(elapsed, 3),
        }

        # Phase 4: Execute
        t0 = time.monotonic()
        exec_result = self.execute(plan)
        elapsed = time.monotonic() - t0
        logger.info(f"[{trace_id}] execute: {elapsed:.3f}s")
        result['phases']['execute'] = {
            'success': exec_result['success_count'],
            'failure': exec_result['failure_count'],
            'actions': exec_result.get('actions', []),
            'elapsed': round(elapsed, 3),
        }

        # Phase 5: Verify
        t0 = time.monotonic()
        verification = self.verify(metrics, exec_result.get('actions', []))
        elapsed = time.monotonic() - t0
        logger.info(f"[{trace_id}] verify: {elapsed:.3f}s")
        result['phases']['verify'] = {
            'improvements': len(verification.get('improvements', [])),
            'score': verification.get('verification_score', 0),
            'elapsed': round(elapsed, 3),
        }

        # Phase 6: Feedback
        t0 = time.monotonic()
        from .daemon import EvolutionSnapshot
        snapshot = EvolutionSnapshot(
            cycle_id=cycle_id,
            timestamp=datetime.now().isoformat(),
            phases_completed=list(result['phases'].keys()),
            metrics_before=metrics,
            metrics_after=verification.get('metrics_after'),
            actions_taken=exec_result.get('actions', []),
            improvements_detected=verification.get('improvements', []),
            duration_seconds=time.time() - cycle_start,
            success=exec_result['failure_count'] == 0,
        )
        feedback = self.feedback(snapshot)
        elapsed = time.monotonic() - t0
        logger.info(f"[{trace_id}] feedback: {elapsed:.3f}s")
        result['phases']['feedback'] = feedback
        
        # 记录历史
        self.cycle_history.append(result)
        
        # 🆕 持久化审计记录
        exec_actions = result.get('phases', {}).get('execute', {}).get('actions', [])
        with open("/tmp/evo_debug.log", "a") as f:
            f.write(f"[run_full_cycle] _audit_cycle START - cycle_id={cycle_id}, exec_actions={len(exec_actions)}\n")
            f.write(f"  execute phase keys: {list(result.get('phases', {}).get('execute', {}).keys())}\n")
            if exec_actions:
                for i, a in enumerate(exec_actions):
                    f.write(f"  action[{i}]: {a.get('action_type')}->{a.get('target')} success={a.get('success')}\n")
        self._audit_cycle(result)
        with open("/tmp/evo_debug.log", "a") as f:
            f.write(f"[run_full_cycle] _audit_cycle DONE\n")
        
        result['duration'] = round(time.time() - cycle_start, 2)
        result['summary'] = (
            f"循环 #{cycle_id}: "
            f"分析 {result['phases']['analyze']['issues']} 问题 → "
            f"执行 {exec_result['success_count']}/{len(plan.get('actions', []))} 动作 → "
            f"验证分 {verification.get('verification_score', 0):.2f}"
        )
        
        return result
    
    def get_cycle_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取循环历史"""
        return self.cycle_history[-limit:]

    def _audit_cycle(self, result: Dict[str, Any]):
        """将进化周期结果持久化到审计数据库（失败不影响主流程）"""
        try:
            from .evolution_auditor import EvolutionAuditor
            from ..db_utils import get_data_dir
            auditor = EvolutionAuditor(db_path=str(get_data_dir() / "evolution_audit.db"))
            
            # 从 analysis._details 提取 health 指标作为 before/after
            ad = result.get('phases', {}).get('analyze', {}).get('_details', {})
            health = ad.get('health', {})
            analysis = health.get('analysis', {}) if isinstance(health, dict) else {}
            exp_data = ad.get('experience', {})
            
            health_before = {
                'health_score': None,  # 当前 SelfMonitor 未输出此字段
                'success_rate': analysis.get('success_rate') or exp_data.get('success_rate'),
                'tools_count': None,   # 可从 tool_performance 获取，暂空
                'experiences': analysis.get('total_experiences') or exp_data.get('total'),
            }
            health_after = dict(health_before)  # 同周期内 before/after 相同
            
            cycle_id = auditor.record_cycle(
                result,
                health_before=health_before,
                health_after=health_after,
            )
            # 补设之前 actions 的 cycle_id
            if cycle_id > 0:
                for action in result.get('phases', {}).get('execute', {}).get('actions', []):
                    auditor.record_action(
                        cycle_id=cycle_id,
                        action=action,
                        phase='execute',
                        success=action.get('success', True),
                        error=action.get('message') if not action.get('success') else None,
                    )
        except Exception as e:
            logger.warning("审计记录失败: %s (进化流程不受影响)", e)
    
    def _audit_action(self, cycle_id, action, phase, success, error, duration_ms):
        """持久化单个进化动作（不抛异常）"""
        try:
            from .evolution_auditor import EvolutionAuditor
            from ..db_utils import get_data_dir
            auditor = EvolutionAuditor(db_path=str(get_data_dir() / "evolution_audit.db"))
            if cycle_id:
                auditor.record_action(
                    cycle_id=cycle_id,
                    action=action,
                    phase=phase,
                    success=success,
                    error=error,
                    duration_ms=duration_ms,
                )
        except Exception as e:
            logger.debug("动作审计记录失败: %s", e)


# ═══════════════════════════════════════════
# Phase 3 引擎升级：闭环编排状态机
# ═══════════════════════════════════════════

from typing import Set
import json
import time as _time

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

PHASE_TRANSITIONS: Dict[Phase, Set[Phase]] = {
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
    """可持久化的进化循环状态。崩溃后可从此状态恢复。"""
    cycle_id: int
    current_phase: Phase
    phase_results: Dict[str, Any] = field(default_factory=dict)
    metrics_before: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: _time.strftime("%Y-%m-%dT%H:%M:%S"))
    updated_at: str = field(default_factory=lambda: _time.strftime("%Y-%m-%dT%H:%M:%S"))
    
    def can_transition_to(self, target: Phase) -> bool:
        return target in PHASE_TRANSITIONS.get(self.current_phase, set())
    
    def to_json(self) -> str:
        return json.dumps({
            "cycle_id": self.cycle_id,
            "current_phase": self.current_phase.value,
            "phase_results": self.phase_results,
            "metrics_before": self.metrics_before,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }, default=str)
    
    @classmethod
    def from_json(cls, data: str) -> 'CycleState':
        d = json.loads(data) if isinstance(data, str) else data
        return cls(
            cycle_id=d["cycle_id"],
            current_phase=Phase(d["current_phase"]),
            phase_results=d.get("phase_results", {}),
            metrics_before=d.get("metrics_before", {}),
            created_at=d.get("created_at", ""),
            updated_at=d.get("updated_at", ""),
        )

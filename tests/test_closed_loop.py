"""
closed_loop 层测试 — 覆盖 action_executor / metrics_collector / orchestrator / daemon

测试维度:
1. ActionExecutor: 5种动作类型 + dry_run + 批量执行 + 统计
2. SystemMetricsCollector: 采集、记录、历史、生命周期
3. ClosedLoopOrchestrator: 6阶段编排流程
4. EvolutionDaemon: 生命周期、状态、快照、回调、自适应间隔
"""

import os
import sys
import json
import time
import tempfile
import threading
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch, PropertyMock

import pytest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from evolution.closed_loop.action_executor import ActionExecutor
    from evolution.closed_loop.metrics_collector import SystemMetricsCollector
    from evolution.closed_loop.orchestrator import (
    ClosedLoopOrchestrator, ImprovementAction
    )
    from evolution.closed_loop.daemon import (
    EvolutionDaemon, EvolutionPhase, LoopState, EvolutionSnapshot
    )
except ImportError:
    from src.evolution.closed_loop.action_executor import ActionExecutor
    from src.evolution.closed_loop.metrics_collector import SystemMetricsCollector
    from src.evolution.closed_loop.orchestrator import (
    ClosedLoopOrchestrator, ImprovementAction
    )
    from src.evolution.closed_loop.daemon import (
    EvolutionDaemon, EvolutionPhase, LoopState, EvolutionSnapshot
    )


# ══════════════════════════════════════════════════════════════════════
# Fixtures
# ══════════════════════════════════════════════════════════════════════

@pytest.fixture
def sample_action():
    """创建一个标准改进动作"""
    return ImprovementAction(
        action_id="act_001",
        action_type="parameter_tuning",
        target="exploration_rate",
        description="Adjust exploration rate",
        priority="medium",
        parameters={"exploration_rate": 0.3},
        expected_benefit="Better tool selection",
        risk="low",
    )


@pytest.fixture
def strategy_learner_mock():
    """Mock 策略学习器"""
    m = MagicMock()
    from enum import Enum
    class MockStrategy(Enum):
        EXPLORE = "explore"
        EXPLOIT = "exploit"
        BALANCED = "balanced"
    m.get_current_strategy.return_value = MockStrategy.BALANCED
    m.record_tool_usage.return_value = None
    m.set_exploration_rate = MagicMock()
    return m


@pytest.fixture
def tool_evolution_engine_mock():
    """Mock 工具进化引擎"""
    m = MagicMock()
    m.run_evolution_cycle.return_value = {
        'success': True, 'optimizations': [], 'deprecated_tools': []
    }
    m.config = MagicMock()
    m.config.min_performance_score = 50.0
    return m


@pytest.fixture
def tool_registry_mock():
    """Mock 工具注册表"""
    m = MagicMock()
    tool_mock = MagicMock()
    tool_mock.status = None
    m.get.return_value = tool_mock
    m.register.return_value = None
    return m


@pytest.fixture
def metrics_collector_mock():
    """Mock 指标采集器"""
    m = MagicMock(spec=SystemMetricsCollector)
    m.collect_all.return_value = {
        'system.cpu_percent': 25.0,
        'system.memory_mb': 512,
        'tool.success_rate': 0.85,
    }
    m.collect_system_metrics.return_value = {
        'system.cpu_percent': 25.0, 'system.memory_mb': 512,
    }
    return m


# ══════════════════════════════════════════════════════════════════════
# 1. ActionExecutor 测试
# ══════════════════════════════════════════════════════════════════════

class TestActionExecutor:
    """动作执行器测试"""

    def test_init_default(self):
        """测试默认初始化"""
        executor = ActionExecutor()
        assert executor.strategy_learner is None
        assert executor.tool_evolution_engine is None
        assert executor.tool_registry is None
        assert executor.dry_run is False
        assert executor.execution_history == []

    def test_init_with_config(self):
        """测试带配置初始化"""
        executor = ActionExecutor(config={'dry_run': True})
        assert executor.dry_run is True

    def test_execute_unknown_type(self, sample_action):
        """测试执行未知类型动作"""
        executor = ActionExecutor()
        sample_action.action_type = "unknown_type"
        result = executor.execute(sample_action)
        assert result['success'] is False
        assert '未知' in result['message'] or 'unknown' in result['message'].lower()

    # ── Dry Run 模式 ──

    def test_dry_run_simulates_all_types(self):
        """测试 dry_run 模式模拟所有动作类型"""
        executor = ActionExecutor(config={'dry_run': True})
        types = ['strategy_switch', 'tool_optimization', 'parameter_tuning',
                  'tool_creation', 'tool_deprecation']

        for action_type in types:
            action = ImprovementAction(
                action_id=f"dry_{action_type}",
                action_type=action_type,
                target="test_target",
                description=f"Test {action_type}",
                priority="low",
            )
            result = executor.execute(action)
            assert result['success'] is True
            assert '[DRY-RUN]' in result['message']
            assert result['output']['simulated'] is True

    def test_dry_run_history_recorded(self):
        """测试 dry_run 执行记录到历史"""
        executor = ActionExecutor(config={'dry_run': True})
        action = ImprovementAction(
            action_id="dry_001", action_type="parameter_tuning",
            target="test", description="Test", priority="low",
        )
        executor.execute(action)
        assert len(executor.execution_history) == 1
        assert executor.execution_history[0]['result']['success'] is True

    # ── 真实执行模式 ──

    def test_strategy_switch_with_learner(self, strategy_learner_mock):
        """测试策略切换（有策略学习器）"""
        executor = ActionExecutor(strategy_learner=strategy_learner_mock)
        action = ImprovementAction(
            action_id="ss_001", action_type="strategy_switch",
            target="strategy", description="Switch strategy", priority="high",
        )
        result = executor.execute(action)
        assert result['success'] is True
        assert '策略' in result['message']  # 中文输出

    def test_strategy_switch_without_learner(self):
        """测试策略切换（无策略学习器）"""
        executor = ActionExecutor()
        action = ImprovementAction(
            action_id="ss_001", action_type="strategy_switch",
            target="strategy", description="Switch", priority="high",
        )
        result = executor.execute(action)
        assert result['success'] is False

    def test_tool_optimization_with_engine(self, tool_evolution_engine_mock):
        """测试工具优化（有进化引擎）"""
        executor = ActionExecutor(tool_evolution_engine=tool_evolution_engine_mock)
        action = ImprovementAction(
            action_id="to_001", action_type="tool_optimization",
            target="test_tool", description="Optimize tool",
            priority="high", parameters={"tool_name": "test_tool"},
        )
        result = executor.execute(action)
        assert result['success'] is True

    def test_tool_optimization_without_engine(self):
        """测试工具优化（无进化引擎）"""
        executor = ActionExecutor()
        action = ImprovementAction(
            action_id="to_001", action_type="tool_optimization",
            target="test_tool", description="Optimize", priority="high",
        )
        result = executor.execute(action)
        assert result['success'] is False

    def test_parameter_tuning_with_exploration_rate(self, strategy_learner_mock):
        """测试参数调整 - 探索率"""
        executor = ActionExecutor(strategy_learner=strategy_learner_mock)
        action = ImprovementAction(
            action_id="pt_001", action_type="parameter_tuning",
            target="exploration_rate", description="Tune exploration",
            priority="medium", parameters={"exploration_rate": 0.1},
        )
        result = executor.execute(action)
        assert result['success'] is True

    def test_parameter_tuning_with_threshold(self, strategy_learner_mock,
                                              tool_evolution_engine_mock):
        """测试参数调整 - 性能阈值"""
        executor = ActionExecutor(
            strategy_learner=strategy_learner_mock,
            tool_evolution_engine=tool_evolution_engine_mock,
        )
        action = ImprovementAction(
            action_id="pt_002", action_type="parameter_tuning",
            target="min_performance_score", description="Tune threshold",
            priority="medium", parameters={"min_performance_score": 80.0},
        )
        result = executor.execute(action)
        assert result['success'] is True

    def test_tool_creation_with_engine(self, tool_evolution_engine_mock):
        """测试工具创建"""
        mock_result = MagicMock()
        mock_result.success = True
        mock_result.tool_name = "new_tool"
        tool_evolution_engine_mock.auto_generate_tool.return_value = mock_result

        executor = ActionExecutor(tool_evolution_engine=tool_evolution_engine_mock)
        action = ImprovementAction(
            action_id="tc_001", action_type="tool_creation",
            target="new_tool", description="Create file reader",
            priority="high",
        )
        result = executor.execute(action)
        assert result['success'] is True

    def test_tool_deprecation(self, tool_registry_mock):
        """测试工具废弃"""
        executor = ActionExecutor(tool_registry=tool_registry_mock)
        action = ImprovementAction(
            action_id="td_001", action_type="tool_deprecation",
            target="old_tool", description="Deprecate old tool",
            priority="low",
        )
        result = executor.execute(action)
        assert result['success'] is True

    def test_tool_deprecation_not_found(self):
        """测试废弃不存在的工具"""
        reg = MagicMock()
        reg.get.return_value = None
        executor = ActionExecutor(tool_registry=reg)
        action = ImprovementAction(
            action_id="td_002", action_type="tool_deprecation",
            target="nonexistent", description="N/A", priority="low",
        )
        result = executor.execute(action)
        assert result['success'] is False

    # ── 批量执行 ──

    def test_execute_batch(self):
        """测试批量执行"""
        executor = ActionExecutor(config={'dry_run': True})
        actions = [
            ImprovementAction(f"a_{i}", "parameter_tuning", f"t_{i}",
                              f"desc_{i}", "low")
            for i in range(3)
        ]
        results = executor.execute_batch(actions)
        assert len(results) == 3
        assert all(r['success'] for r in results)

    # ── 统计 ──

    def test_get_execution_stats(self):
        """测试执行统计"""
        executor = ActionExecutor(config={'dry_run': True})
        action = ImprovementAction("s_1", "parameter_tuning",
                                    "t", "d", "low")
        executor.execute(action)
        executor.execute(action)

        stats = executor.get_execution_stats()
        assert stats['total_executions'] == 2
        assert stats['success_count'] == 2
        assert stats['failure_count'] == 0

    def test_get_execution_stats_empty(self):
        """测试空历史统计"""
        executor = ActionExecutor()
        stats = executor.get_execution_stats()
        assert stats == {'total': 0}


# ══════════════════════════════════════════════════════════════════════
# 2. SystemMetricsCollector 测试
# ══════════════════════════════════════════════════════════════════════

class TestSystemMetricsCollector:
    """系统指标采集器测试"""

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_init(self, mock_psutil):
        """测试初始化"""
        mock_process = MagicMock()
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector()
        assert collector.collection_interval == 30
        assert collector.history_size == 100
        assert collector._running is False

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_init_custom_config(self, mock_psutil):
        """测试自定义配置初始化"""
        mock_process = MagicMock()
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector(config={
            'collection_interval': 10,
            'history_size': 50,
        })
        assert collector.collection_interval == 10
        assert collector.history_size == 50

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_collect_system_metrics(self, mock_psutil):
        """测试采集系统指标（内部方法）"""
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 12.5
        mock_process.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
        mock_process.memory_percent.return_value = 5.0
        mock_process.num_threads.return_value = 4
        mock_process.open_files.return_value = []
        mock_psutil.Process.return_value = mock_process
        mock_psutil.cpu_percent.return_value = 25.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            used=2 * 1024 * 1024 * 1024, percent=50.0, total=8 * 1024 * 1024 * 1024
        )
        mock_psutil.disk_usage.return_value = MagicMock(percent=40.0)

        collector = SystemMetricsCollector()
        metrics = collector._collect_system_metrics()

        assert 'system.cpu_percent' in metrics
        assert 'system.memory_mb' in metrics
        assert metrics['system.cpu_percent'] == 12.5

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_record_tool_call(self, mock_psutil):
        """测试记录工具调用"""
        mock_process = MagicMock()
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector()
        collector.record_tool_call(
            tool_name='test_tool',
            success=True,
            execution_time=0.5,
        )
        assert 'test_tool' in collector._tool_stats
        stats = collector._tool_stats['test_tool']
        assert stats['total_calls'] == 1
        assert stats['success_calls'] == 1

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_record_experience(self, mock_psutil):
        """测试记录经验"""
        mock_process = MagicMock()
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector()
        collector.record_experience()
        assert collector._experience_count == 1

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_get_system_health(self, mock_psutil):
        """测试获取系统健康快照"""
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 10.0
        mock_process.memory_percent.return_value = 10.0
        mock_process.memory_info.return_value = MagicMock(rss=100 * 1024 * 1024)
        mock_process.num_threads.return_value = 3
        mock_process.open_files.return_value = []
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector()
        health = collector.get_system_health()
        assert 'score' in health
        assert 'status' in health
        assert health['status'] in ('healthy', 'warning', 'critical')
        assert 0 <= health['score'] <= 100

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_get_tool_stats_unknown(self, mock_psutil):
        """测试获取不存在的工具统计"""
        mock_process = MagicMock()
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector()
        result = collector.get_tool_stats('nonexistent_tool')
        assert result is None

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_collect_all(self, mock_psutil):
        """测试全量采集"""
        mock_process = MagicMock()
        mock_process.cpu_percent.return_value = 15.0
        mock_process.memory_info.return_value = MagicMock(rss=200 * 1024 * 1024)
        mock_process.memory_percent.return_value = 10.0
        mock_process.num_threads.return_value = 3
        mock_process.open_files.return_value = []
        mock_psutil.Process.return_value = mock_process
        mock_psutil.cpu_percent.return_value = 30.0
        mock_psutil.virtual_memory.return_value = MagicMock(
            used=4 * 1024 * 1024 * 1024, percent=50.0, total=8 * 1024 * 1024 * 1024
        )
        mock_psutil.disk_usage.return_value = MagicMock(percent=55.0)

        collector = SystemMetricsCollector()
        result = collector.collect_all()

        assert isinstance(result, dict)
        assert 'system.cpu_percent' in result
        assert 'system.memory_mb' in result

    @patch('src.evolution.closed_loop.metrics_collector.psutil')
    def test_start_stop_lifecycle(self, mock_psutil):
        """测试采集器启停生命周期"""
        mock_process = MagicMock()
        mock_psutil.Process.return_value = mock_process

        collector = SystemMetricsCollector(config={'collection_interval': 0.1})
        assert collector._running is False

        collector.start()
        assert collector._running is True
        assert collector._thread is not None

        collector.stop()
        assert collector._running is False


# ══════════════════════════════════════════════════════════════════════
# 3. ImprovementAction 测试
# ══════════════════════════════════════════════════════════════════════

class TestImprovementAction:
    """改进动作数据类测试"""

    def test_creation_defaults(self):
        """测试默认值"""
        action = ImprovementAction(
            action_id="a1",
            action_type="parameter_tuning",
            target="cpu_limit",
            description="Adjust CPU limit",
            priority="medium",
        )
        assert action.action_id == "a1"
        assert action.parameters == {}
        assert action.expected_benefit == ""
        assert action.risk == "low"

    def test_creation_full(self):
        """测试完整参数"""
        action = ImprovementAction(
            action_id="a2",
            action_type="tool_creation",
            target="new_parser",
            description="Create parser tool",
            priority="critical",
            parameters={"lang": "python", "output": "json"},
            expected_benefit="Faster parsing",
            risk="medium",
        )
        assert action.priority == "critical"
        assert action.parameters['lang'] == 'python'
        assert action.risk == "medium"

    def test_equality(self):
        """测试相等性"""
        a1 = ImprovementAction("id1", "type1", "t1", "d1", "low")
        a2 = ImprovementAction("id1", "type1", "t1", "d1", "low")
        assert a1 == a2
        assert a1 != ImprovementAction("id2", "type1", "t1", "d1", "low")


# ══════════════════════════════════════════════════════════════════════
# 4. ClosedLoopOrchestrator 测试
# ══════════════════════════════════════════════════════════════════════

class TestClosedLoopOrchestrator:
    """闭环编排器测试"""

    def _create_orchestrator(self, **overrides):
        """创建带 Mock 依赖的编排器"""
        defaults = {
            'metrics_collector': MagicMock(),
            'self_monitor': MagicMock(),
            'experience_analyzer': MagicMock(),
            'pattern_recognizer': MagicMock(),
            'strategy_learner': MagicMock(),
            'action_executor': MagicMock(),
            'learning_observer': MagicMock(),
        }
        defaults.update(overrides)
        return ClosedLoopOrchestrator(**defaults)

    def test_init_default_thresholds(self):
        """测试默认阈值"""
        orch = self._create_orchestrator()
        assert orch.success_rate_threshold == 0.6
        assert orch.tool_performance_threshold == 60.0
        assert orch.strategy_improvement_delta == 0.1

    def test_init_custom_thresholds(self):
        """测试自定义阈值"""
        orch = self._create_orchestrator(config={
            'success_rate_threshold': 0.8,
            'tool_performance_threshold': 75.0,
        })
        assert orch.success_rate_threshold == 0.8
        assert orch.tool_performance_threshold == 75.0

    def test_monitor_phase(self):
        """测试监控阶段"""
        mc = MagicMock()
        mc.collect_all.return_value = {'cpu': 50, 'memory': 512}
        orch = self._create_orchestrator(metrics_collector=mc)

        result = orch.monitor()
        assert result['cpu'] == 50
        mc.collect_all.assert_called_once()

    def test_analyze_phase(self):
        """测试分析阶段"""
        pat = MagicMock()
        pat.recognize.return_value = [
            {'name': 'high_cpu_pattern', 'confidence': 0.9}
        ]
        sm = MagicMock()
        sm.get_health_status.return_value = 'healthy'

        orch = self._create_orchestrator(
            pattern_recognizer=pat,
            self_monitor=sm,
        )
        metrics = {'system.cpu_percent': 90}
        result = orch.analyze(metrics)

        assert 'patterns' in result
        assert 'issues' in result

    def test_plan_phase(self):
        """测试规划阶段"""
        ea = MagicMock()
        ea.analyze_experiences.return_value = {
            'top_bottlenecks': ['tool_timeout']
        }
        sl = MagicMock()
        sl.get_tool_performance_summary.return_value = {}
        sl.suggest_actions.return_value = []

        orch = self._create_orchestrator(
            experience_analyzer=ea,
            strategy_learner=sl,
        )
        analysis = {
            'patterns': [{'type': 'bottleneck', 'confidence': 0.8, 'description': '测试瓶颈'}],
            'issues': [{'type': 'low_success_rate', 'value': 0.3, 'severity': 'high'}]
        }
        result = orch.plan(analysis)

        assert 'actions' in result
        assert result['actions']  # 至少产生一个动作

    def test_execute_phase(self):
        """测试执行阶段"""
        ae = MagicMock()
        ae.execute.return_value = {'success': True, 'message': 'done'}

        orch = self._create_orchestrator(action_executor=ae)
        plan = {
            'actions': [
                {'action_id': 'a1', 'action_type': 'parameter_tuning', 'target': 't1',
                 'description': 'd1', 'priority': 'low', 'parameters': {}, 'expected_benefit': '', 'risk': 'low'},
                {'action_id': 'a2', 'action_type': 'tool_optimization', 'target': 't2',
                 'description': 'd2', 'priority': 'high', 'parameters': {}, 'expected_benefit': '', 'risk': 'low'},
            ]
        }
        result = orch.execute(plan)

        assert 'actions' in result
        assert result['success_count'] >= 0

    def test_verify_phase(self):
        """测试验证阶段"""
        mc = MagicMock()
        mc.collect_all.return_value = {'system.cpu_percent': 30}
        orch = self._create_orchestrator(metrics_collector=mc)

        before = {'system.cpu_percent': 90}
        actions = [{'action': 'tuning', 'success': True}]

        result = orch.verify(before, actions)
        assert 'metrics_after' in result
        assert 'improvements' in result
        assert result['metrics_after']['system.cpu_percent'] == 30

    def test_feedback_phase(self):
        """测试反馈阶段"""
        lo = MagicMock()
        orch = self._create_orchestrator(learning_observer=lo)

        snapshot = EvolutionSnapshot(
            cycle_id=1,
            timestamp=datetime.now().isoformat(),
            phases_completed=['monitor', 'analyze', 'plan', 'execute', 'verify', 'feedback'],
            metrics_before={'cpu': 90},
            metrics_after={'cpu': 30},
            actions_taken=[{'type': 'tuning'}],
            improvements_detected=['cpu_reduction'],
            duration_seconds=5.0,
            success=True,
        )
        result = orch.feedback(snapshot)
        assert isinstance(result, dict)

    def test_run_full_cycle(self):
        """测试完整进化循环 (run_full_cycle)"""
        mc = MagicMock()
        mc.collect_all.return_value = {'system.cpu_percent': 50, 'system.success_rate': 0.85}

        sm = MagicMock()
        sm.monitor_and_improve.return_value = {'analysis': {'success_rate': 0.85}}

        pr = MagicMock()
        pr.recognize_patterns.return_value = []

        ea = MagicMock()
        ea.analyze_recent_experiences.return_value = MagicMock(
            total_experiences=10, success_rate=0.8, key_insights=[]
        )

        sl = MagicMock()
        sl.get_tool_performance_summary.return_value = {}

        ae = MagicMock()
        ae.execute.return_value = {'success': True, 'message': 'done', 'output': {}}

        lo = MagicMock()
        lo.get_recent_experiences.return_value = []

        orch = self._create_orchestrator(
            metrics_collector=mc, self_monitor=sm,
            pattern_recognizer=pr, experience_analyzer=ea,
            strategy_learner=sl, action_executor=ae,
            learning_observer=lo,
        )

        result = orch.run_full_cycle()
        assert 'cycle_id' in result
        assert 'phases' in result
        assert 'summary' in result

    def test_cycle_history(self):
        """测试循环历史追踪"""
        orch = self._create_orchestrator()
        assert orch.get_cycle_history() == []


# ══════════════════════════════════════════════════════════════════════
# 5. EvolutionDaemon 测试
# ══════════════════════════════════════════════════════════════════════

class TestEvolutionDaemon:
    """进化守护进程测试"""

    @pytest.fixture
    def orchestrator_mock(self):
        """Mock 编排器"""
        m = MagicMock()
        m.monitor.return_value = {'cpu': 50}
        m.analyze.return_value = {'patterns': [], 'issues': []}
        m.plan.return_value = {'actions': []}
        m.execute.return_value = {'actions': [], 'success_count': 0, 'failure_count': 0}
        m.verify.return_value = {'metrics_after': {'cpu': 50}, 'improvements': []}
        m.feedback.return_value = {'recorded': True}
        return m

    @pytest.fixture
    def daemon(self, orchestrator_mock):
        """创建守护进程"""
        return EvolutionDaemon(
            orchestrator=orchestrator_mock,
            config={'cycle_interval': 1, 'min_interval': 0.5, 'max_interval': 10}
        )

    # ── 生命周期 ──

    def test_initial_state(self, daemon):
        """测试初始状态"""
        assert daemon.state == LoopState.STOPPED
        assert daemon.is_running is False
        assert daemon.cycle_count == 0

    def test_start_stop(self, daemon):
        """测试启动和停止"""
        assert daemon.start() is True
        assert daemon.state == LoopState.RUNNING

        # 给一点时间让线程启动
        time.sleep(0.2)

        assert daemon.stop(timeout=5.0) is True
        assert daemon.state == LoopState.STOPPED

    def test_double_start(self, daemon):
        """测试重复启动"""
        daemon.start()
        time.sleep(0.1)
        result = daemon.start()
        assert result is False  # 已在运行
        daemon.stop(timeout=5.0)

    def test_pause_resume(self, daemon):
        """测试暂停和恢复"""
        daemon.start()
        time.sleep(0.1)

        assert daemon.pause() is True
        assert daemon.state == LoopState.PAUSED

        assert daemon.resume() is True
        assert daemon.state == LoopState.RUNNING

        daemon.stop(timeout=5.0)

    def test_pause_when_not_running(self, daemon):
        """测试非运行状态暂停"""
        assert daemon.pause() is False

    def test_resume_when_not_paused(self, daemon):
        """测试非暂停状态恢复"""
        assert daemon.resume() is False

    def test_stop_when_not_running(self, daemon):
        """测试停止已停止的守护进程"""
        assert daemon.stop() is True  # 幂等

    # ── 状态查询 ──

    def test_get_status(self, daemon):
        """测试获取状态"""
        status = daemon.get_status()
        assert status['state'] == 'stopped'
        assert status['cycle_count'] == 0
        assert 'interval' in status

    def test_get_recent_snapshots_empty(self, daemon):
        """测试获取快照（空）"""
        snapshots = daemon.get_recent_snapshots()
        assert snapshots == []

    def test_get_evolution_summary_empty(self, daemon):
        """测试进化总结（空）"""
        summary = daemon.get_evolution_summary()
        assert summary['status'] == 'no_data'

    def test_get_evolution_summary(self, daemon):
        """测试进化总结（有数据）"""
        # 手动添加快照
        daemon.snapshots.append(EvolutionSnapshot(
            cycle_id=1,
            timestamp=datetime.now().isoformat(),
            phases_completed=['monitor', 'analyze', 'plan', 'execute', 'verify', 'feedback'],
            metrics_before={'cpu': 80},
            metrics_after={'cpu': 40},
            actions_taken=[{'type': 'tuning'}],
            improvements_detected=['cpu_reduced'],
            duration_seconds=5.0,
            success=True,
        ))
        daemon.cycle_count = 1

        summary = daemon.get_evolution_summary()
        assert summary['total_cycles'] == 1
        assert summary['successful_cycles'] == 1
        assert summary['total_improvements_detected'] == 1

    # ── 回调 ──

    def test_callbacks(self, daemon):
        """测试回调注册和触发"""
        cycle_called = []
        improvement_called = []
        error_called = []

        daemon.on_cycle_complete(lambda s: cycle_called.append(s.cycle_id))
        daemon.on_improvement(lambda s: improvement_called.append(s.cycle_id))
        daemon.on_error(lambda e: error_called.append(str(e)))

        assert len(daemon._on_cycle_complete) == 1
        assert len(daemon._on_improvement) == 1
        assert len(daemon._on_error) == 1

    # ── 自适应间隔 ──

    def test_calculate_interval_no_adaptive(self, daemon):
        """测试非自适应间隔"""
        daemon.adaptive_interval = False
        interval = daemon._calculate_next_interval()
        assert interval == daemon.cycle_interval

    def test_calculate_interval_with_improvements(self, daemon):
        """测试有改进时的自适应间隔"""
        daemon.adaptive_interval = True
        daemon.snapshots = [
            EvolutionSnapshot(
                i, datetime.now().isoformat(), [], {'cpu': 50},
                improvements_detected=['improvement_a']
            )
            for i in range(3)
        ]
        interval = daemon._calculate_next_interval()
        assert interval <= daemon.cycle_interval  # 有改进应缩短

    def test_calculate_interval_no_improvements(self, daemon):
        """测试无改进时的自适应间隔"""
        daemon.adaptive_interval = True
        daemon.snapshots = [
            EvolutionSnapshot(
                i, datetime.now().isoformat(), [], {'cpu': 50},
                improvements_detected=[]
            )
            for i in range(3)
        ]
        interval = daemon._calculate_next_interval()
        assert interval >= daemon.cycle_interval  # 无改进应延长

    # ── 快照存储 ──

    def test_save_load_state(self, daemon, tmp_path):
        """测试状态持久化"""
        daemon.state_path = tmp_path / "daemon_state.json"
        daemon.cycle_count = 5
        daemon.snapshots = [
            EvolutionSnapshot(
                i, datetime.now().isoformat(), ['monitor'],
                {'cpu': 50}, duration_seconds=2.0
            )
            for i in range(3)
        ]
        daemon._save_state()

        assert daemon.state_path.exists()

        loaded = daemon._load_state()
        assert loaded is not None
        assert loaded['cycle_count'] == 5
        assert len(loaded['recent_snapshots']) == 3

    # ── EvolutionPhase 枚举 ──

    def test_evolution_phase_values(self):
        """测试进化阶段枚举值"""
        assert EvolutionPhase.MONITOR.value == 'monitor'
        assert EvolutionPhase.ANALYZE.value == 'analyze'
        assert EvolutionPhase.PLAN.value == 'plan'
        assert EvolutionPhase.EXECUTE.value == 'execute'
        assert EvolutionPhase.VERIFY.value == 'verify'
        assert EvolutionPhase.FEEDBACK.value == 'feedback'
        assert EvolutionPhase.IDLE.value == 'idle'
        assert len(EvolutionPhase) == 7

    # ── LoopState 枚举 ──

    def test_loop_state_values(self):
        """测试循环状态枚举值"""
        assert LoopState.RUNNING.value == 'running'
        assert LoopState.PAUSED.value == 'paused'
        assert LoopState.STOPPING.value == 'stopping'
        assert LoopState.STOPPED.value == 'stopped'
        assert LoopState.ERROR.value == 'error'
        assert len(LoopState) == 5

    # ── EvolutionSnapshot 数据类 ──

    def test_snapshot_defaults(self):
        """测试快照默认值"""
        snap = EvolutionSnapshot(
            cycle_id=1,
            timestamp=datetime.now().isoformat(),
            phases_completed=[],
            metrics_before={},
        )
        assert snap.metrics_after is None
        assert snap.actions_taken == []
        assert snap.improvements_detected == []
        assert snap.errors == []
        assert snap.duration_seconds == 0.0
        assert snap.success is True

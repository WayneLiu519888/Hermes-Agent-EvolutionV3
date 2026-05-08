"""
self_monitor 模块测试

覆盖:
- SelfMonitor 初始化
- monitor_and_improve 正常流程、低成功率、高成功率
- _generate_improvement_plan 各类改进
- get_monitoring_history
- get_system_health_report
"""

import os
import sys
from unittest.mock import MagicMock, Mock, PropertyMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from evolution.self_monitor import SelfMonitor
except ImportError:
    from src.evolution.self_monitor import SelfMonitor


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_mock_analyzer(total=10, success_rate=0.5, patterns=1, insights=None):
    """创建模拟分析器"""
    analyzer = MagicMock()
    result = MagicMock()
    result.total_experiences = total
    result.success_rate = success_rate
    result.identified_patterns = [Mock() for _ in range(patterns)]
    result.key_insights = insights or ["洞察1", "洞察2"]
    result.summary = "测试摘要"
    analyzer.analyze_recent_experiences.return_value = result
    return analyzer


def make_mock_strategy_learner(current_strategy_value="balanced"):
    """创建模拟策略学习器"""
    learner = MagicMock()
    learner.get_tool_performance_summary.return_value = {
        "tool_a": {"success_rate": 0.4, "usage_count": 10},
        "tool_b": {"success_rate": 0.8, "usage_count": 5},
    }

    # strategy performance
    perf_a = MagicMock()
    perf_a.success_rate = 0.4
    perf_a.avg_efficiency = 0.5
    perf_a.usage_count = 10

    perf_b = MagicMock()
    perf_b.success_rate = 0.8
    perf_b.avg_efficiency = 0.7
    perf_b.usage_count = 5

    current_strategy = MagicMock()
    current_strategy.value = current_strategy_value

    better_strategy = MagicMock()
    better_strategy.value = "aggressive"

    learner.get_strategy_performance.return_value = {
        current_strategy: perf_a,
        better_strategy: perf_b,
    }

    learner.get_current_strategy.return_value = current_strategy
    return learner


def make_mock_observer():
    """创建模拟观察器"""
    return MagicMock()


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def low_success_analyzer():
    """低成功率分析器"""
    return make_mock_analyzer(success_rate=0.3, total=20)


@pytest.fixture
def high_success_analyzer():
    """高成功率分析器"""
    return make_mock_analyzer(success_rate=0.85, total=50)


@pytest.fixture
def strategy_learner():
    """策略学习器"""
    return make_mock_strategy_learner()


@pytest.fixture
def observer():
    """观察器"""
    return make_mock_observer()


@pytest.fixture
def monitor(observer, strategy_learner, low_success_analyzer):
    """创建 SelfMonitor"""
    return SelfMonitor(
        observer=observer,
        analyzer=low_success_analyzer,
        strategy_learner=strategy_learner,
    )


# ── Init ──────────────────────────────────────────────────────────────────────

class TestSelfMonitorInit:
    """测试初始化"""

    def test_init_stores_references(self, observer, strategy_learner, low_success_analyzer):
        """存储组件引用"""
        m = SelfMonitor(observer, low_success_analyzer, strategy_learner)
        assert m.observer is observer
        assert m.analyzer is low_success_analyzer
        assert m.strategy_learner is strategy_learner

    def test_init_empty_history(self, monitor):
        """初始化历史为空"""
        assert monitor.monitoring_history == []


# ── monitor_and_improve ───────────────────────────────────────────────────────

class TestMonitorAndImprove:
    """测试监控和改进"""

    def test_returns_structured_result(self, monitor):
        """返回结构化结果"""
        result = monitor.monitor_and_improve()
        assert "timestamp" in result
        assert "analysis" in result
        assert "strategy_update" in result
        assert "improvements" in result
        assert "summary" in result

    def test_calls_analyzer(self, monitor, low_success_analyzer):
        """调用分析器"""
        monitor.monitor_and_improve()
        low_success_analyzer.analyze_recent_experiences.assert_called_once_with(days=7)

    def test_records_history(self, monitor):
        """记录监控历史"""
        assert len(monitor.monitoring_history) == 0
        monitor.monitor_and_improve()
        assert len(monitor.monitoring_history) == 1
        record = monitor.monitoring_history[0]
        assert "timestamp" in record
        assert "analysis_summary" in record
        assert "improvement_plan" in record

    def test_low_success_generates_improvements(self, monitor):
        """低成功率生成改进"""
        result = monitor.monitor_and_improve()
        # 成功率 0.3 < 0.6，应有改进计划
        improvements = result["improvements"]
        assert len(improvements) >= 1
        improvement_types = [i["type"] for i in improvements]
        assert "improve_success_rate" in improvement_types

    def test_high_success_generates_general_advice(self, observer, strategy_learner):
        """高成功率生成通用建议"""
        analyzer = make_mock_analyzer(success_rate=0.9, total=100)
        m = SelfMonitor(observer, analyzer, strategy_learner)
        result = m.monitor_and_improve()
        improvements = result["improvements"]
        types = [i["type"] for i in improvements]
        assert "general_improvement" in types or len(improvements) > 0


# ── _generate_improvement_plan ────────────────────────────────────────────────

class TestGenerateImprovementPlan:
    """测试生成改进计划"""

    def test_low_success_rate_improvement(self, monitor, low_success_analyzer):
        """低成功率触发改进"""
        analysis = low_success_analyzer.analyze_recent_experiences()
        tool_summary = {"tool_a": {"success_rate": 0.8, "usage_count": 5}}
        strategy_perf = {}

        plan = monitor._generate_improvement_plan(analysis, tool_summary, strategy_perf)
        types = [p["type"] for p in plan]
        assert "improve_success_rate" in types

    def test_low_tool_performance_improvement(self, monitor, high_success_analyzer):
        """低性能工具触发改进"""
        analysis = high_success_analyzer.analyze_recent_experiences()
        tool_summary = {"bad_tool": {"success_rate": 0.2, "usage_count": 10}}
        strategy_perf = {}

        plan = monitor._generate_improvement_plan(analysis, tool_summary, strategy_perf)
        types = [p["type"] for p in plan]
        assert "improve_tool_performance" in types

    def test_strategy_switch_suggested(self, observer, strategy_learner):
        """当前策略表现差时建议切换"""
        analyzer = make_mock_analyzer(success_rate=0.8, total=50)
        m = SelfMonitor(observer, analyzer, strategy_learner)

        analysis = analyzer.analyze_recent_experiences()
        tool_summary = {"tool_a": {"success_rate": 0.8, "usage_count": 5}}
        strategy_perf = strategy_learner.get_strategy_performance()

        plan = m._generate_improvement_plan(analysis, tool_summary, strategy_perf)
        types = [p["type"] for p in plan]
        assert "update_strategy" in types

    def test_normal_runtime_general_advice(self, observer, strategy_learner):
        """正常运行给出通用建议"""
        analyzer = make_mock_analyzer(success_rate=0.85, total=100)
        m = SelfMonitor(observer, analyzer, strategy_learner)

        analysis = analyzer.analyze_recent_experiences()
        tool_summary = {"tool_a": {"success_rate": 0.9, "usage_count": 5}}
        strategy_perf = {}

        plan = m._generate_improvement_plan(analysis, tool_summary, strategy_perf)
        types = [p["type"] for p in plan]
        assert "general_improvement" in types

    def test_improvement_has_required_fields(self, monitor, low_success_analyzer):
        """改进项包含必要字段"""
        analysis = low_success_analyzer.analyze_recent_experiences()
        plan = monitor._generate_improvement_plan(analysis, {}, {})
        for item in plan:
            assert "type" in item
            assert "priority" in item
            assert "description" in item
            assert "actions" in item
            assert isinstance(item["actions"], list)


# ── get_monitoring_history ────────────────────────────────────────────────────

class TestGetMonitoringHistory:
    """测试监控历史"""

    def test_empty_history(self, monitor):
        """空历史返回空列表"""
        history = monitor.get_monitoring_history()
        assert history == []

    def test_limited_history(self, monitor):
        """限制数量"""
        for _ in range(5):
            monitor.monitor_and_improve()
        history = monitor.get_monitoring_history(limit=3)
        assert len(history) == 3

    def test_full_history(self, monitor):
        """保留所有记录"""
        for _ in range(3):
            monitor.monitor_and_improve()
        history = monitor.get_monitoring_history()
        assert len(history) == 3


# ── get_system_health_report ──────────────────────────────────────────────────

class TestGetSystemHealthReport:
    """测试系统健康报告"""

    def test_returns_structured_report(self, monitor):
        """返回结构化报告"""
        report = monitor.get_system_health_report()
        assert "timestamp" in report
        assert "health_score" in report
        assert "metrics" in report
        assert "status" in report
        assert "recommendations" in report

    def test_health_score_in_range(self, monitor):
        """健康分数在 0-100"""
        report = monitor.get_system_health_report()
        assert 0 <= report["health_score"] <= 100

    def test_status_is_valid(self, monitor):
        """状态为有效值"""
        report = monitor.get_system_health_report()
        assert report["status"] in ("healthy", "needs_attention", "unhealthy")

    def test_metrics_contain_required_fields(self, monitor):
        """指标包含必要字段"""
        report = monitor.get_system_health_report()
        metrics = report["metrics"]
        assert "success_rate" in metrics
        assert "total_experiences" in metrics
        assert "monitored_tools" in metrics
        assert "current_strategy" in metrics

    def test_high_success_gives_healthy(self, observer, strategy_learner):
        """高成功率返回 healthy"""
        analyzer = make_mock_analyzer(success_rate=0.95, total=100)
        m = SelfMonitor(observer, analyzer, strategy_learner)
        report = m.get_system_health_report()
        assert report["status"] == "healthy"
        assert report["health_score"] >= 70

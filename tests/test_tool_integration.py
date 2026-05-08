"""
tool_integration 模块测试

覆盖:
- EvolutionConfig 默认值和自定义值
- EvolutionStatus 枚举
- ToolEvolutionEngine 初始化、状态摘要、进化周期
- ToolLearningIntegrator 初始化
- auto_generate_tool

使用大量 mock 隔离依赖。
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 先 patch 掉 learning 模块的导入
with patch('evolution.tools.tool_integration.LEARNING_AVAILABLE', False):
    try:
        from evolution.tools.tool_integration import (
        EvolutionConfig,
        EvolutionStatus,
        ToolEvolutionEngine,
        ToolLearningIntegrator,
        )
    except ImportError:
        from src.evolution.tools.tool_integration import (
        EvolutionConfig,
        EvolutionStatus,
        ToolEvolutionEngine,
        ToolLearningIntegrator,
        )


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def mock_registry():
    """创建模拟 ToolRegistry"""
    registry = MagicMock()
    tool = MagicMock()
    tool.name = "test_tool"
    tool.usage_count = 10
    tool.success_count = 8
    tool.error_count = 2
    tool.category = MagicMock()
    tool.category.value = "file_operation"
    tool.status = MagicMock()
    tool.status.value = "active"
    tool.is_builtin = False
    registry.list_all.return_value = [tool]
    registry.get_tool.return_value = tool
    return registry


@pytest.fixture
def config():
    """默认 EvolutionConfig"""
    return EvolutionConfig()


@pytest.fixture
def engine(mock_registry, config):
    """创建 ToolEvolutionEngine"""
    with patch('evolution.tools.tool_integration.ToolPerformanceAnalyzer') as mock_pa, \
         patch('evolution.tools.tool_integration.ToolAutoGenerator') as mock_ag:

        # Mock performance analyzer
        analyzer_instance = MagicMock()
        perf_summary = MagicMock()
        perf_summary.overall_score = 85.0
        perf_summary.performance_level = MagicMock(value="good")
        perf_summary.key_insights = ["insight1"]
        perf_summary.optimization_opportunities = ["opp1"]
        analyzer_instance.analyze_tool_performance.return_value = perf_summary
        mock_pa.return_value = analyzer_instance

        # Mock auto generator
        gen_instance = MagicMock()
        mock_ag.return_value = gen_instance

        yield ToolEvolutionEngine(registry=mock_registry, config=config)


# ── EvolutionConfig ───────────────────────────────────────────────────────────

class TestEvolutionConfig:
    """测试进化配置"""

    def test_default_values(self, config):
        """默认值正确"""
        assert config.auto_evolve is True
        assert config.evolution_interval == 3600
        assert config.min_performance_score == 60.0
        assert config.max_tool_age_days == 30
        assert config.enable_auto_registration is True
        assert config.enable_performance_monitoring is True
        assert config.enable_optimization is True
        # learning_integration_enabled=True 但因为 LEARNING_AVAILABLE=False 会变成 False
        try:
            from evolution.tools import tool_integration
        except ImportError:
            from src.evolution.tools import tool_integration
        if tool_integration.LEARNING_AVAILABLE:
            assert config.learning_integration_enabled is True
        else:
            assert config.learning_integration_enabled is False

    def test_custom_values(self):
        """自定义值"""
        cfg = EvolutionConfig(
            auto_evolve=False,
            evolution_interval=7200,
            min_performance_score=80.0,
            max_tool_age_days=60,
            enable_auto_registration=False,
            enable_performance_monitoring=False,
            enable_optimization=False,
            learning_integration_enabled=False,
        )
        assert cfg.auto_evolve is False
        assert cfg.evolution_interval == 7200
        assert cfg.min_performance_score == 80.0
        assert cfg.max_tool_age_days == 60


# ── EvolutionStatus ───────────────────────────────────────────────────────────

class TestEvolutionStatus:
    """测试进化状态枚举"""

    def test_all_statuses(self):
        """所有状态值"""
        statuses = {s.value for s in EvolutionStatus}
        expected = {"idle", "analyzing", "evolving", "optimizing", "completed", "failed"}
        assert statuses == expected


# ── ToolEvolutionEngine ───────────────────────────────────────────────────────

class TestToolEvolutionEngine:
    """测试进化引擎"""

    def test_init(self, engine, mock_registry):
        """初始化正确"""
        assert engine.registry is mock_registry
        assert engine.status == EvolutionStatus.IDLE
        assert engine.evolution_history == []
        assert engine.last_evolution_time is None

    def test_get_status_summary(self, engine):
        """状态摘要返回正确结构"""
        summary = engine.get_status_summary()
        assert "status" in summary
        assert "total_tools" in summary
        assert "active_tools" in summary
        assert "learning_integrated" in summary
        assert "evolution_cycles" in summary
        assert summary["total_tools"] == 1

    def test_generate_evolution_report(self, engine):
        """进化报告生成非空字符串"""
        report = engine.generate_evolution_report()
        assert isinstance(report, str)
        assert len(report) > 0
        assert "工具进化系统报告" in report or "tool" in report.lower()
        assert "系统概览" in report or "overview" in report.lower()

    def test_analyze_current_state(self, engine):
        """分析当前状态调用 registry"""
        state = engine.analyze_current_state()
        assert "total_tools" in state
        assert "category_distribution" in state
        assert "status_distribution" in state
        assert "performance_summaries" in state
        assert state["total_tools"] == 1

    def test_run_evolution_cycle_success(self, engine):
        """进化周期成功执行"""
        result = engine.run_evolution_cycle()
        assert result["success"] is True
        assert "timestamp" in result
        assert "actions_taken" in result
        assert "optimizations" in result
        assert len(engine.evolution_history) == 1

    def test_run_evolution_cycle_failure_handling(self, mock_registry):
        """进化周期异常处理"""
        mock_registry.list_all.side_effect = RuntimeError("模拟错误")
        with patch('evolution.tools.tool_integration.ToolPerformanceAnalyzer'), \
             patch('evolution.tools.tool_integration.ToolAutoGenerator'):
            eng = ToolEvolutionEngine(registry=mock_registry, config=EvolutionConfig())
            result = eng.run_evolution_cycle()
            assert result["success"] is False
            assert "error" in result

    def test_status_transitions(self, engine):
        """状态转换：IDLE → COMPLETED"""
        engine.run_evolution_cycle()
        assert engine.status == EvolutionStatus.COMPLETED
        assert len(engine.evolution_history) == 1

    def test_multiple_evolution_cycles(self, engine):
        """多次进化周期"""
        for _ in range(3):
            engine.run_evolution_cycle()
        assert len(engine.evolution_history) == 3

    def test_last_evolution_time_updated(self, engine):
        """上次进化时间更新"""
        assert engine.last_evolution_time is None
        engine.run_evolution_cycle()
        assert engine.last_evolution_time is not None

    def test_get_status_summary_after_evolution(self, engine):
        """进化后的状态摘要"""
        engine.run_evolution_cycle()
        summary = engine.get_status_summary()
        assert summary["evolution_cycles"] == 1
        assert summary["last_evolution"] is not None


# ── ToolLearningIntegrator ────────────────────────────────────────────────────

class TestToolLearningIntegrator:
    """测试学习集成器"""

    def test_init_without_learning(self, mock_registry):
        """无学习模块时初始化"""
        with patch('evolution.tools.tool_integration.LEARNING_AVAILABLE', False):
            integrator = ToolLearningIntegrator(mock_registry)
            assert integrator.observer is None
            assert integrator.analyzer is None
            assert integrator.strategy_learner is None
            assert integrator.pattern_recognizer is None

    def test_record_tool_execution_no_observer(self, mock_registry):
        """无 observer 时记录返回 False"""
        with patch('evolution.tools.tool_integration.LEARNING_AVAILABLE', False):
            integrator = ToolLearningIntegrator(mock_registry)
            result = integrator.record_tool_execution("test", True, 0.5)
            assert result is False

    def test_analyze_tool_patterns_no_pattern_recognizer(self, mock_registry):
        """无 pattern_recognizer 时返回空"""
        with patch('evolution.tools.tool_integration.LEARNING_AVAILABLE', False):
            integrator = ToolLearningIntegrator(mock_registry)
            result = integrator.analyze_tool_patterns()
            assert result == []

    def test_optimize_tool_strategy_no_learner(self, mock_registry):
        """无 strategy_learner 时返回原因"""
        with patch('evolution.tools.tool_integration.LEARNING_AVAILABLE', False):
            integrator = ToolLearningIntegrator(mock_registry)
            result = integrator.optimize_tool_strategy("test_tool")
            assert result["optimized"] is False
            assert "reason" in result

    def test_optimize_tool_strategy_nonexistent_tool(self, mock_registry):
        """工具不存在"""
        mock_registry.get_tool.return_value = None
        with patch('evolution.tools.tool_integration.LEARNING_AVAILABLE', False):
            integrator = ToolLearningIntegrator(mock_registry)
            result = integrator.optimize_tool_strategy("nonexistent")
            assert result["optimized"] is False


# ── auto_generate_tool ────────────────────────────────────────────────────────

class TestAutoGenerateTool:
    """测试自动生成工具"""

    def test_auto_generate_success(self, mock_registry):
        """自动生成工具成功"""
        with patch('evolution.tools.tool_integration.ToolPerformanceAnalyzer'), \
             patch('evolution.tools.tool_integration.ToolAutoGenerator') as mock_ag:
            gen_instance = MagicMock()
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.tool_name = "new_tool"
            mock_result.tool_code = "def new_tool(): pass"
            mock_result.warnings = []
            gen_instance.generate_from_requirement.return_value = mock_result
            mock_ag.return_value = gen_instance

            eng = ToolEvolutionEngine(registry=mock_registry, config=EvolutionConfig())
            result = eng.auto_generate_tool("读取文件")

            assert result.success is True
            assert result.tool_name == "new_tool"
            gen_instance.generate_from_requirement.assert_called_once_with("读取文件")

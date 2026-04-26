"""
工具进化引擎集成测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from evolution.tools import (
    ToolEvolutionEngine, EvolutionConfig, EvolutionStatus,
    ToolLearningIntegrator
)
from evolution.tools import ToolRegistry, ToolCategory, ToolStatus, ToolDefinition


class TestToolEvolutionEngine:
    """工具进化引擎测试"""
    
    @pytest.fixture
    def engine(self):
        import tempfile
        db_path = os.path.join(tempfile.mkdtemp(), "test_evolution.db")
        reg = ToolRegistry(db_path)
        
        # 注册测试工具
        tools = [
            ToolDefinition(name="reader", description="读取文件", category=ToolCategory.FILE_OPERATION, usage_count=100, success_count=95, error_count=5),
            ToolDefinition(name="writer", description="写入文件", category=ToolCategory.FILE_OPERATION, usage_count=80, success_count=70, error_count=10),
            ToolDefinition(name="filter", description="过滤数据", category=ToolCategory.DATA_PROCESSING, usage_count=50, success_count=45, error_count=5),
        ]
        
        for tool in tools:
            reg.register(tool)
        
        config = EvolutionConfig(
            auto_evolve=True,
            evolution_interval=3600,
            min_performance_score=60.0,
            enable_auto_registration=True,
            enable_performance_monitoring=True,
            learning_integration_enabled=False  # 禁用学习系统集成以简化测试
        )
        
        return ToolEvolutionEngine(reg, config)
    
    def test_initial_state(self, engine):
        """测试初始状态"""
        status = engine.get_status_summary()
        
        assert status["status"] == "idle"
        assert status["total_tools"] == 3
        assert status["active_tools"] == 3
    
    def test_analyze_current_state(self, engine):
        """测试分析当前状态"""
        state = engine.analyze_current_state()
        
        assert state["total_tools"] == 3
        assert "category_distribution" in state
        assert "performance_summaries" in state
        assert "reader" in state["performance_summaries"]
    
    def test_run_evolution_cycle(self, engine):
        """测试运行进化周期"""
        result = engine.run_evolution_cycle()
        
        assert result["success"]
        assert "state_before" in result
        assert "optimizations" in result
    
    def test_auto_generate_tool(self, engine):
        """测试自动生成工具"""
        result = engine.auto_generate_tool("读取CSV文件")
        
        assert result.success
        assert "csv" in result.tool_name.lower()
    
    def test_generate_report(self, engine):
        """测试生成报告"""
        report = engine.generate_evolution_report()
        
        assert "工具进化系统报告" in report
        assert "工具总数: 3" in report
    
    def test_evolution_status(self, engine):
        """测试进化状态变化"""
        assert engine.status == EvolutionStatus.IDLE
        
        engine.run_evolution_cycle()
        assert engine.status == EvolutionStatus.COMPLETED


class TestToolLearningIntegrator:
    """工具-学习集成器测试"""
    
    @pytest.fixture
    def integrator(self):
        import tempfile
        db_path = os.path.join(tempfile.mkdtemp(), "test_integrator.db")
        reg = ToolRegistry(db_path)
        tool = ToolDefinition(name="test_tool", description="测试", category=ToolCategory.UTILITY)
        reg.register(tool)
        return ToolLearningIntegrator(reg)
    
    def test_analyze_tool_patterns(self, integrator):
        """测试分析工具模式"""
        patterns = integrator.analyze_tool_patterns()
        # 应该返回列表（可能为空）
        assert isinstance(patterns, list)

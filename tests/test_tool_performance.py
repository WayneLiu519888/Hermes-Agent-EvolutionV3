"""
工具性能分析器测试
"""

import sys
import os
import tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from datetime import timedelta
from evolution.tools import (
    ToolPerformanceAnalyzer, PerformanceMetric, PerformanceLevel, PerformanceAnalysis,
    ToolPerformanceSummary, monitor_performance
)
from evolution.tools import ToolRegistry, ToolCategory, ToolStatus, ToolDefinition


class TestToolPerformanceAnalyzer:
    """工具性能分析器测试"""
    
    @pytest.fixture
    def registry(self):
        reg = ToolRegistry(":memory:")
        # 注册测试工具
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.UTILITY,
            usage_count=50,
            success_count=45,
            error_count=5
        )
        reg.register(tool)
        return reg
    
    @pytest.fixture
    def analyzer(self, registry, tmp_path):
        db_path = str(tmp_path / "test_performance.db")
        return ToolPerformanceAnalyzer(registry, db_path)
    
    def test_record_performance(self, analyzer):
        """测试记录性能数据"""
        result = analyzer.record_performance(
            tool_name="test_tool",
            metric=PerformanceMetric.EXECUTION_TIME,
            value=0.5,
            metadata={"operation": "test"}
        )
        
        assert result
    
    def test_analyze_tool_performance(self, analyzer):
        """测试分析工具性能"""
        # 先记录一些数据
        for i in range(5):
            analyzer.record_performance(
                tool_name="test_tool",
                metric=PerformanceMetric.EXECUTION_TIME,
                value=0.3 + i * 0.1
            )
            analyzer.record_performance(
                tool_name="test_tool",
                metric=PerformanceMetric.SUCCESS_RATE,
                value=0.95 - i * 0.02
            )
        
        summary = analyzer.analyze_tool_performance("test_tool")
        
        assert summary is not None
        assert summary.tool_name == "test_tool"
        assert summary.overall_score > 0
        assert len(summary.key_insights) > 0
    
    def test_analyze_all_tools(self, analyzer):
        """测试分析所有工具"""
        # 记录数据
        analyzer.record_performance(
            tool_name="test_tool",
            metric=PerformanceMetric.EXECUTION_TIME,
            value=0.5
        )
        
        summaries = analyzer.analyze_all_tools()
        assert "test_tool" in summaries
    
    def test_generate_performance_report(self, analyzer):
        """测试生成性能报告"""
        # 记录数据
        analyzer.record_performance(
            tool_name="test_tool",
            metric=PerformanceMetric.EXECUTION_TIME,
            value=0.5
        )
        
        # 文本格式
        text_report = analyzer.generate_performance_report("text")
        assert "工具性能报告" in text_report
        
        # JSON格式
        import json
        json_report = analyzer.generate_performance_report("json")
        parsed = json.loads(json_report)
        assert "summaries" in parsed

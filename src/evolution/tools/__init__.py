"""
工具能力进化框架
提供工具注册、创建、性能分析、自动生成和管理功能
"""

from .tool_registry import (
    ToolDefinition,
    ToolRegistry,
    ToolCategory,
    ToolStatus
)

from .tool_creator import (
    ToolCreator,
    ToolCreationResult
)

from .enhanced_tool_creator import (
    EnhancedToolCreator,
    CreationSource,
    ToolQuality,
    CodeAnalysisResult
)

from .tool_performance_analyzer import (
    ToolPerformanceAnalyzer,
    PerformanceMetric,
    PerformanceLevel,
    PerformanceRecord,
    PerformanceAnalysis,
    ToolPerformanceSummary,
    monitor_performance
)

from .tool_auto_generator import (
    ToolAutoGenerator,
    GenerationStrategy,
    ToolGenerationResult
)

from .tool_integration import (
    ToolEvolutionEngine,
    ToolLearningIntegrator,
    EvolutionConfig,
    EvolutionStatus
)

__all__ = [
    # ToolRegistry
    'ToolDefinition',
    'ToolRegistry',
    'ToolCategory',
    'ToolStatus',
    # ToolCreator
    'ToolCreator',
    'ToolCreationResult',
    # EnhancedToolCreator
    'EnhancedToolCreator',
    'CreationSource',
    'ToolQuality',
    'CodeAnalysisResult',
    # ToolPerformanceAnalyzer
    'ToolPerformanceAnalyzer',
    'PerformanceMetric',
    'PerformanceLevel',
    'PerformanceRecord',
    'PerformanceAnalysis',
    'ToolPerformanceSummary',
    'monitor_performance',
    # ToolAutoGenerator
    'ToolAutoGenerator',
    'GenerationStrategy',
    'ToolGenerationResult',
    # Integration
    'ToolEvolutionEngine',
    'ToolLearningIntegrator',
    'EvolutionConfig',
    'EvolutionStatus'
]

"""
工具进化引擎
将工具能力进化与学习系统集成的核心模块
"""

import json
import logging
import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

log = logging.getLogger("hermes_evo.tools")

from .tool_registry import ToolDefinition, ToolRegistry, ToolCategory, ToolStatus
from .enhanced_tool_creator import EnhancedToolCreator, CreationSource, ToolQuality
from .tool_performance_analyzer import ToolPerformanceAnalyzer, PerformanceMetric, PerformanceLevel, ToolPerformanceSummary
from .tool_auto_generator import ToolAutoGenerator, GenerationStrategy, ToolGenerationResult

# 尝试导入学习系统模块（可选）
try:
    from ..learning.observer import LearningObserver
    from ..learning.analyzer import ExperienceAnalyzer
    from ..learning.tool_strategy_learner import ToolStrategyLearner
    from ..learning.pattern_recognizer import PatternRecognizer
    LEARNING_AVAILABLE = True
except ImportError:
    LEARNING_AVAILABLE = False


class EvolutionConfig:
    """进化配置"""
    
    def __init__(self, 
                 auto_evolve: bool = True,
                 evolution_interval: int = 3600,  # 进化检查间隔（秒）
                 min_performance_score: float = 60.0,  # 触发优化的最低性能分
                 max_tool_age_days: int = 30,  # 工具最大寿命（天）
                 enable_auto_registration: bool = True,
                 enable_performance_monitoring: bool = True,
                 enable_optimization: bool = True,
                 learning_integration_enabled: bool = True):
        self.auto_evolve = auto_evolve
        self.evolution_interval = evolution_interval
        self.min_performance_score = min_performance_score
        self.max_tool_age_days = max_tool_age_days
        self.enable_auto_registration = enable_auto_registration
        self.enable_performance_monitoring = enable_performance_monitoring
        self.enable_optimization = enable_optimization
        self.learning_integration_enabled = learning_integration_enabled and LEARNING_AVAILABLE


class EvolutionStatus(Enum):
    """进化状态枚举"""
    IDLE = "idle"  # 空闲
    ANALYZING = "analyzing"  # 分析中
    EVOLVING = "evolving"  # 进化中
    OPTIMIZING = "optimizing"  # 优化中
    COMPLETED = "completed"  # 完成
    FAILED = "failed"  # 失败


class ToolLearningIntegrator:
    """工具与学习系统集成器"""
    
    def __init__(self, registry: ToolRegistry):
        self.registry = registry
        self.observer = None
        self.analyzer = None
        self.strategy_learner = None
        self.pattern_recognizer = None
        self._init_learning_modules()
    
    def _init_learning_modules(self):
        """初始化学习模块"""
        if not LEARNING_AVAILABLE:
            log.info("学习系统模块未加载，工具-学习集成功能受限")
            return
        
        try:
            self.observer = LearningObserver()
            self.analyzer = ExperienceAnalyzer()
            self.strategy_learner = ToolStrategyLearner(self.registry)
            self.pattern_recognizer = PatternRecognizer()
            log.info("工具-学习集成模块初始化成功")
        except Exception as e:
            log.error("学习模块初始化失败: %s", e)
    
    def record_tool_execution(self, tool_name: str, 
                              success: bool,
                              execution_time: float,
                              error: Optional[str] = None,
                              context: Optional[Dict] = None):
        """记录工具执行到学习系统"""
        if not self.observer:
            return False
        
        experience = {
            "type": "tool_execution",
            "tool_name": tool_name,
            "success": success,
            "execution_time": execution_time,
            "error": error,
            "context": context or {},
            "timestamp": datetime.now().isoformat()
        }
        
        self.observer.record_experience(experience)
        return True
    
    def analyze_tool_patterns(self) -> List[Dict]:
        """分析工具使用模式"""
        if not self.pattern_recognizer:
            return []
        
        # 获取所有工具的使用数据
        tools = self.registry.list_all()
        patterns = []
        
        for tool in tools:
            tool_data = {
                "name": tool.name,
                "usage_count": tool.usage_count,
                "success_count": tool.success_count,
                "error_count": tool.error_count,
                "status": tool.status.value
            }
            
            # 识别模式
            recognized = self.pattern_recognizer.recognize(tool_data)
            patterns.extend(recognized)
        
        return patterns
    
    def optimize_tool_strategy(self, tool_name: str) -> Dict[str, Any]:
        """优化工具使用策略"""
        if not self.strategy_learner:
            return {"optimized": False, "reason": "学习系统未初始化"}
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {"optimized": False, "reason": f"工具 {tool_name} 不存在"}
        
        performance_data = {
            "usage_count": tool.usage_count,
            "success_count": tool.success_count,
            "error_count": tool.error_count,
            "status": tool.status.value
        }
        
        strategy = self.strategy_learner.learn_strategy(tool_name, performance_data)
        
        return {
            "optimized": True,
            "tool_name": tool_name,
            "strategy": strategy,
            "recommendations": self.strategy_learner.get_recommendations(tool_name)
        }
    
    def analyze_experience(self, tool_name: str) -> Dict[str, Any]:
        """分析工具使用经验"""
        if not self.analyzer:
            return {"analyzed": False}
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return {"analyzed": False, "reason": "工具不存在"}
        
        analysis = self.analyzer.analyze({
            "tool_name": tool_name,
            "usage_count": tool.usage_count,
            "success_count": tool.success_count,
            "error_count": tool.error_count
        })
        
        return {
            "analyzed": True,
            "tool_name": tool_name,
            "analysis": analysis,
            "improvements": analysis.get("improvements", []) if analysis else []
        }


class ToolEvolutionEngine:
    """工具进化引擎主类"""
    
    def __init__(self, registry: Optional[ToolRegistry] = None, config: Optional[EvolutionConfig] = None):
        """
        初始化工具进化引擎
        
        Args:
            registry: 工具注册表实例
            config: 进化配置
        """
        self.registry = registry or ToolRegistry()
        self.config = config or EvolutionConfig()
        
        # 初始化子系统
        self.enhanced_creator = EnhancedToolCreator(self.registry)
        self.performance_analyzer = ToolPerformanceAnalyzer(self.registry, "tool_performance.db")
        self.auto_generator = ToolAutoGenerator(self.registry)
        self.learning_integrator = ToolLearningIntegrator(self.registry)
        
        # 进化状态
        self.status = EvolutionStatus.IDLE
        self.evolution_history: List[Dict] = []
        self.last_evolution_time: Optional[datetime] = None
        
    def analyze_current_state(self) -> Dict[str, Any]:
        """
        分析当前工具系统状态
        
        Returns:
            Dict: 状态分析结果
        """
        self.status = EvolutionStatus.ANALYZING
        
        # 获取所有工具
        all_tools = self.registry.list_all()
        
        # 分析性能
        performance_summaries = {}
        for tool in all_tools:
            try:
                summary = self.performance_analyzer.analyze_tool_performance(tool.name)
                performance_summaries[tool.name] = {
                    "score": summary.overall_score,
                    "level": summary.performance_level.value,
                    "insights": summary.key_insights,
                    "opportunities": summary.optimization_opportunities
                }
            except Exception as e:
                performance_summaries[tool.name] = {
                    "score": 0,
                    "level": "unknown",
                    "error": str(e)
                }
        
        # 分析工具分布
        category_distribution = {}
        status_distribution = {}
        for tool in all_tools:
            cat = tool.category.value
            category_distribution[cat] = category_distribution.get(cat, 0) + 1
            
            st = tool.status.value
            status_distribution[st] = status_distribution.get(st, 0) + 1
        
        # 学习系统分析
        patterns = []
        if self.config.learning_integration_enabled:
            try:
                patterns = self.learning_integrator.analyze_tool_patterns()
            except Exception as e:
                patterns = [{"error": str(e)}]
        
        analysis = {
            "total_tools": len(all_tools),
            "category_distribution": category_distribution,
            "status_distribution": status_distribution,
            "performance_summaries": performance_summaries,
            "learning_patterns": patterns,
            "creation_stats": self.enhanced_creator.get_creation_stats(),
            "analysis_time": datetime.now().isoformat()
        }
        
        self.status = EvolutionStatus.IDLE
        return analysis
    
    def run_evolution_cycle(self) -> Dict[str, Any]:
        """
        运行一次完整的进化周期
        
        将工具使用数据反馈给学习系统，然后使用学习系统的输出来优化工具
        
        Returns:
            Dict: 进化结果
        """
        self.status = EvolutionStatus.EVOLVING
        evolution_result = {
            "timestamp": datetime.now().isoformat(),
            "actions_taken": [],
            "optimizations": [],
            "new_tools": [],
            "deprecated_tools": [],
            "warnings": []
        }
        
        try:
            # Step 1: 分析当前状态
            state = self.analyze_current_state()
            evolution_result["state_before"] = state
            
            # Step 2: 识别需要优化的工具
            if self.config.enable_performance_monitoring:
                for tool_name, perf in state.get("performance_summaries", {}).items():
                    if perf.get("score", 100) < self.config.min_performance_score:
                        # 记录优化需求
                        evolution_result["optimizations"].append({
                            "tool_name": tool_name,
                            "current_score": perf["score"],
                            "issues": perf.get("insights", []),
                            "recommendations": perf.get("opportunities", [])
                        })
                        
                        # 触发学习系统优化
                        if self.config.learning_integration_enabled:
                            try:
                                result = self.learning_integrator.optimize_tool_strategy(tool_name)
                                evolution_result["strategy_optimizations"] = \
                                    evolution_result.get("strategy_optimizations", [])
                                evolution_result["strategy_optimizations"].append(result)
                            except Exception as e:
                                evolution_result["warnings"].append(
                                    f"策略优化失败 [{tool_name}]: {e}")
            
            # Step 3: 识别需要废弃的工具
            for tool in self.registry.list_all():
                if tool.status == ToolStatus.DEPRECATED:
                    evolution_result["deprecated_tools"].append(tool.name)
                elif (tool.status == ToolStatus.DISABLED and 
                      tool.usage_count == 0 and
                      not tool.is_builtin):
                    evolution_result["deprecated_tools"].append(tool.name)
            
            # Step 4: 记录学习经验
            if self.config.learning_integration_enabled:
                for action in evolution_result["actions_taken"]:
                    self.learning_integrator.record_tool_execution(
                        tool_name=action.get("tool", "system"),
                        success=True,
                        execution_time=0.1,
                        context={"evolution_cycle": True, "action": action}
                    )
            
            evolution_result["success"] = True
            
        except Exception as e:
            evolution_result["success"] = False
            evolution_result["error"] = str(e)
            self.status = EvolutionStatus.FAILED
        
        # 记录进化历史
        self.evolution_history.append(evolution_result)
        self.last_evolution_time = datetime.now()
        self.status = EvolutionStatus.COMPLETED
        
        return evolution_result
    
    def auto_generate_tool(self, requirement: str) -> ToolGenerationResult:
        """
        自动生成工具
        
        Args:
            requirement: 需求描述
            
        Returns:
            ToolGenerationResult: 生成结果
        """
        result = self.auto_generator.generate_from_requirement(requirement)
        
        if result.success and self.config.enable_auto_registration:
            # 自动注册到增强创建器
            creator_result = self.enhanced_creator.create_from_code(
                code=result.tool_code,
                name=result.tool_name,
                description=f"Auto-generated: {requirement[:100]}",
                category=ToolCategory.CUSTOM,
                tags=["auto_generated"]
            )
            
            if not creator_result.success:
                result.warnings.append(f"注册工具失败: {creator_result.error_message}")
        
        return result
    
    def generate_evolution_report(self) -> str:
        """
        生成进化报告
        
        Returns:
            str: 进化报告文本
        """
        state = self.analyze_current_state()
        
        report = f"""
================================================================================
    工具进化系统报告
    生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

【系统概览】
  • 工具总数: {state['total_tools']}
  • 进化引擎状态: {self.status.value}
  • 上次进化时间: {self.last_evolution_time.strftime('%Y-%m-%d %H:%M:%S') if self.last_evolution_time else '尚未进化'}
  • 学习系统集成: {'✅ 已启用' if self.config.learning_integration_enabled else '❌ 未启用'}
  • 自动监控: {'✅ 已启用' if self.config.enable_performance_monitoring else '❌ 未启用'}

【工具分布】
  • 分类分布:
"""
        
        for cat, count in state.get("category_distribution", {}).items():
            bar = "█" * count
            report += f"    {cat}: {bar} ({count})\n"
        
        report += f"""
  • 状态分布:
"""
        for st, count in state.get("status_distribution", {}).items():
            bar = "█" * count
            report += f"    {st}: {bar} ({count})\n"
        
        report += """
【性能概览】
"""
        
        for tool_name, perf in state.get("performance_summaries", {}).items():
            score = perf.get("score", 0)
            level = perf.get("level", "unknown")
            
            # 颜色指示
            indicator = "🟢" if score >= 80 else "🟡" if score >= 60 else "🔴"
            
            report += f"  {indicator} {tool_name}: {score:.1f}/100 ({level})\n"
            
            # 关键洞察
            for insight in perf.get("insights", []):
                report += f"    • {insight}\n"
        
        report += """
【进化历史】
"""
        
        if self.evolution_history:
            for i, evolution in enumerate(self.evolution_history[-5:], 1):
                status = "✅" if evolution.get("success") else "❌"
                report += f"  {status} #{i}: {evolution.get('timestamp', 'unknown')}\n"
                
                actions = evolution.get("actions_taken", [])
                if actions:
                    report += f"    操作数: {len(actions)}\n"
                
                optimizations = evolution.get("optimizations", [])
                if optimizations:
                    report += f"    优化建议数: {len(optimizations)}\n"
        else:
            report += "  尚无进化历史\n"
        
        report += f"""
================================================================================
    报告结束
================================================================================
"""
        
        return report
    
    def get_status_summary(self) -> Dict[str, Any]:
        """
        获取状态摘要
        
        Returns:
            Dict: 状态摘要
        """
        all_tools = self.registry.list_all()
        
        return {
            "status": self.status.value,
            "total_tools": len(all_tools),
            "active_tools": sum(1 for t in all_tools if t.status == ToolStatus.ACTIVE),
            "experimental_tools": sum(1 for t in all_tools if t.status == ToolStatus.EXPERIMENTAL),
            "deprecated_tools": sum(1 for t in all_tools if t.status == ToolStatus.DEPRECATED),
            "learning_integrated": self.config.learning_integration_enabled and LEARNING_AVAILABLE,
            "evolution_cycles": len(self.evolution_history),
            "last_evolution": self.last_evolution_time.isoformat() if self.last_evolution_time else None,
            "performance_db": "tool_performance.db"
        }

"""
经验分析器模块 - 学习能力进化的核心组件
简化版本，专注于核心功能
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import statistics
from collections import defaultdict
import logging

from .experience import Experience, ExperienceType, Outcome

logger = logging.getLogger(__name__)


class AnalysisPatternType(Enum):
    """分析模式类型枚举"""
    SUCCESS_PATTERN = "success_pattern"
    FAILURE_PATTERN = "failure_pattern"


@dataclass
class PatternInstance:
    """模式实例"""
    pattern_type: AnalysisPatternType
    confidence: float
    frequency: int
    description: str
    recommendations: List[str]


@dataclass
class AnalysisResult:
    """分析结果"""
    timestamp: datetime
    total_experiences: int
    success_rate: float
    identified_patterns: List[PatternInstance]
    key_insights: List[str]
    improvement_suggestions: List[str]
    summary: str


class ExperienceAnalyzer:
    """经验分析器"""
    
    def __init__(self, observer):
        """
        初始化分析器
        
        Args:
            observer: LearningObserver实例
        """
        self.observer = observer
        
    def analyze_recent_experiences(self, days: int = 7) -> AnalysisResult:
        """
        分析最近的经验数据
        
        Args:
            days: 分析最近多少天的数据
            
        Returns:
            AnalysisResult: 分析结果
        """
        logger.info(f"开始分析最近{days}天的经验数据")
        
        # 获取经验数据（简化，实际应从数据库获取）
        experiences = self._get_sample_experiences()
        
        if not experiences:
            logger.warning("没有找到经验数据")
            return self._create_empty_analysis()
        
        # 执行分析
        return self._perform_analysis(experiences)
    
    def _perform_analysis(self, experiences: List[Experience]) -> AnalysisResult:
        """执行完整分析"""
        # 基础统计
        total = len(experiences)
        successes = len([e for e in experiences if e.outcome == Outcome.SUCCESS])
        success_rate = successes / total if total > 0 else 0
        
        # 识别模式
        success_patterns = self._identify_success_patterns(experiences)
        failure_patterns = self._identify_failure_patterns(experiences)
        all_patterns = success_patterns + failure_patterns
        
        # 生成关键洞察
        key_insights = self._generate_key_insights(experiences, all_patterns, success_rate)
        
        # 生成改进建议
        improvement_suggestions = self._generate_improvement_suggestions(all_patterns, success_rate)
        
        # 创建分析结果
        return AnalysisResult(
            timestamp=datetime.now(),
            total_experiences=total,
            success_rate=success_rate,
            identified_patterns=all_patterns,
            key_insights=key_insights,
            improvement_suggestions=improvement_suggestions,
            summary=self._generate_summary(total, success_rate, len(all_patterns))
        )
    
    def _identify_success_patterns(self, experiences: List[Experience]) -> List[PatternInstance]:
        """识别成功模式"""
        patterns = []
        
        # 收集成功经验
        successes = [exp for exp in experiences if exp.outcome == Outcome.SUCCESS]
        
        if len(successes) >= 3:
            # 按经验类型分组
            by_type = defaultdict(list)
            for exp in successes:
                by_type[exp.experience_type.value].append(exp)
            
            for exp_type, exps in by_type.items():
                if len(exps) >= 2:
                    pattern = PatternInstance(
                        pattern_type=AnalysisPatternType.SUCCESS_PATTERN,
                        confidence=min(0.9, len(exps) / 5),
                        frequency=len(exps),
                        description=f"{exp_type}的成功执行模式",
                        recommendations=[
                            f"在类似任务中应用此{exp_type}模式",
                            f"记录成功的关键步骤"
                        ]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _identify_failure_patterns(self, experiences: List[Experience]) -> List[PatternInstance]:
        """识别失败模式"""
        patterns = []
        
        # 收集失败经验
        failures = [exp for exp in experiences if exp.outcome in [Outcome.FAILURE, Outcome.PARTIAL_SUCCESS]]
        
        if len(failures) >= 2:
            # 简单分类
            error_types = defaultdict(int)
            for exp in failures:
                error_type = self._categorize_error(exp)
                error_types[error_type] += 1
            
            for error_type, count in error_types.items():
                if count >= 2:
                    pattern = PatternInstance(
                        pattern_type=AnalysisPatternType.FAILURE_PATTERN,
                        confidence=0.7,
                        frequency=count,
                        description=f"{error_type}类型的失败模式",
                        recommendations=[
                            f"避免{error_type}错误",
                            f"增加对{error_type}的检查",
                            f"改进{error_type}的处理逻辑"
                        ]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _categorize_error(self, experience: Experience) -> str:
        """分类错误"""
        if 'error' in experience.context:
            error = str(experience.context['error']).lower()
            if 'timeout' in error:
                return "超时"
            elif 'permission' in error:
                return "权限"
            elif 'not found' in error:
                return "资源未找到"
        
        return "未知错误"
    
    def _generate_key_insights(self, experiences: List[Experience], patterns: List[PatternInstance], 
                              success_rate: float) -> List[str]:
        """生成关键洞察"""
        insights = []
        
        if success_rate > 0.8:
            insights.append(f"高成功率 ({success_rate:.1%})，策略有效")
        elif success_rate < 0.5:
            insights.append(f"低成功率 ({success_rate:.1%})，需改进")
        
        success_count = len([p for p in patterns if p.pattern_type == AnalysisPatternType.SUCCESS_PATTERN])
        failure_count = len([p for p in patterns if p.pattern_type == AnalysisPatternType.FAILURE_PATTERN])
        
        if success_count > 0:
            insights.append(f"发现{success_count}个成功模式")
        if failure_count > 0:
            insights.append(f"发现{failure_count}个失败模式")
        
        return insights
    
    def _generate_improvement_suggestions(self, patterns: List[PatternInstance], success_rate: float) -> List[str]:
        """生成改进建议"""
        suggestions = []
        
        # 基于成功模式
        for pattern in patterns:
            if pattern.pattern_type == AnalysisPatternType.SUCCESS_PATTERN:
                suggestions.append(f"强化应用: {pattern.description}")
        
        # 基于失败模式
        for pattern in patterns:
            if pattern.pattern_type == AnalysisPatternType.FAILURE_PATTERN:
                suggestions.extend(pattern.recommendations)
        
        # 基于成功率
        if success_rate < 0.6:
            suggestions.append("分析低成功率原因，调整执行策略")
        
        return suggestions
    
    def _generate_summary(self, total: int, success_rate: float, pattern_count: int) -> str:
        """生成分析摘要"""
        return f"分析{total}条经验，成功率{success_rate:.1%}，识别{pattern_count}个模式"
    
    def _create_empty_analysis(self) -> AnalysisResult:
        """创建空分析结果"""
        return AnalysisResult(
            timestamp=datetime.now(),
            total_experiences=0,
            success_rate=0.0,
            identified_patterns=[],
            key_insights=["暂无经验数据"],
            improvement_suggestions=["积累更多经验数据"],
            summary="无数据"
        )
    
    def _get_sample_experiences(self) -> List[Experience]:
        """获取示例经验数据（用于测试）"""
        # 创建一些示例经验
        experiences = []
        
        # 成功经验
        for i in range(3):
            exp = Experience(
                id=f"success_{i}",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id=f"task_{i}",
                description=f"成功使用工具{i}",
                outcome=Outcome.SUCCESS,
                metrics={"efficiency": 0.8 + i*0.05}
            )
            experiences.append(exp)
        
        # 失败经验
        for i in range(2):
            exp = Experience(
                id=f"failure_{i}",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id=f"task_{i+3}",
                description=f"工具使用失败{i}",
                outcome=Outcome.FAILURE,
                context={"error": "权限错误" if i == 0 else "超时错误"}
            )
            experiences.append(exp)
        
        return experiences


# 导出主要类
__all__ = ['ExperienceAnalyzer', 'AnalysisPatternType', 'PatternInstance', 'AnalysisResult']

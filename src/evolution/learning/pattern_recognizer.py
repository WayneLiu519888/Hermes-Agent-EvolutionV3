"""
模式识别模块 - 从经验数据中识别高级模式并生成优化策略
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict
import logging
import re
from itertools import combinations

from .experience import Experience, ExperienceType, Outcome
from .analyzer import AnalysisResult, PatternInstance

logger = logging.getLogger(__name__)


class PatternCategory(Enum):
    """模式类别枚举"""
    TEMPORAL_PATTERN = "temporal_pattern"      # 时间模式
    SEQUENTIAL_PATTERN = "sequential_pattern"  # 序列模式
    CONTEXTUAL_PATTERN = "contextual_pattern"  # 上下文模式
    PERFORMANCE_PATTERN = "performance_pattern" # 性能模式
    ERROR_PATTERN = "error_pattern"           # 错误模式


class StrategyType(Enum):
    """策略类型枚举"""
    PREVENTIVE = "preventive"      # 预防性策略
    OPTIMIZATION = "optimization"  # 优化策略
    ADAPTIVE = "adaptive"          # 适应性策略
    RECOVERY = "recovery"          # 恢复策略


@dataclass
class RecognizedPattern:
    """识别的模式"""
    pattern_id: str
    category: PatternCategory
    description: str
    confidence: float
    support_count: int
    conditions: Dict[str, Any]
    examples: List[str]
    implications: List[str]
    discovered_at: datetime = field(default_factory=datetime.now)


@dataclass
class GeneratedStrategy:
    """生成的策略"""
    strategy_id: str
    strategy_type: StrategyType
    target_pattern: str
    description: str
    actions: List[str]
    expected_benefit: float
    implementation_cost: float
    priority: str  # high, medium, low
    validation_status: str = "pending"  # pending, validated, rejected


class PatternRecognizer:
    """模式识别器"""
    
    def __init__(self, min_support: int = 3, min_confidence: float = 0.7):
        """
        初始化模式识别器
        
        Args:
            min_support: 最小支持度（出现次数）
            min_confidence: 最小置信度
        """
        self.min_support = min_support
        self.min_confidence = min_confidence
        self.patterns: Dict[str, RecognizedPattern] = {}
        self.strategies: Dict[str, GeneratedStrategy] = {}
        
    def recognize_patterns(self, experiences: List[Experience]) -> List[RecognizedPattern]:
        """
        从经验数据中识别模式
        
        Args:
            experiences: 经验数据列表
            
        Returns:
            List[RecognizedPattern]: 识别的模式列表
        """
        logger.info(f"开始模式识别: {len(experiences)}条经验")
        
        all_patterns = []
        
        # 1. 识别时间模式
        temporal_patterns = self._recognize_temporal_patterns(experiences)
        all_patterns.extend(temporal_patterns)
        
        # 2. 识别序列模式
        sequential_patterns = self._recognize_sequential_patterns(experiences)
        all_patterns.extend(sequential_patterns)
        
        # 3. 识别上下文模式
        contextual_patterns = self._recognize_contextual_patterns(experiences)
        all_patterns.extend(contextual_patterns)
        
        # 4. 识别性能模式
        performance_patterns = self._recognize_performance_patterns(experiences)
        all_patterns.extend(performance_patterns)
        
        # 5. 识别错误模式
        error_patterns = self._recognize_error_patterns(experiences)
        all_patterns.extend(error_patterns)
        
        # 保存识别的模式
        for pattern in all_patterns:
            self.patterns[pattern.pattern_id] = pattern
        
        logger.info(f"模式识别完成: 识别到{len(all_patterns)}个模式")
        return all_patterns
    
    def generate_strategies(self, patterns: List[RecognizedPattern]) -> List[GeneratedStrategy]:
        """
        基于识别的模式生成策略
        
        Args:
            patterns: 识别的模式列表
            
        Returns:
            List[GeneratedStrategy]: 生成的策略列表
        """
        logger.info(f"开始策略生成: {len(patterns)}个模式")
        
        all_strategies = []
        
        for pattern in patterns:
            # 根据模式类别生成相应策略
            strategies = self._generate_strategies_for_pattern(pattern)
            all_strategies.extend(strategies)
        
        # 按优先级排序
        all_strategies.sort(key=lambda s: self._strategy_priority_score(s))
        
        # 保存生成的策略
        for strategy in all_strategies:
            self.strategies[strategy.strategy_id] = strategy
        
        logger.info(f"策略生成完成: 生成{len(all_strategies)}个策略")
        return all_strategies
    
    def get_pattern_summary(self) -> Dict[str, Any]:
        """获取模式摘要"""
        summary = {
            "total_patterns": len(self.patterns),
            "by_category": defaultdict(int),
            "by_confidence": {"high": 0, "medium": 0, "low": 0}
        }
        
        for pattern in self.patterns.values():
            summary["by_category"][pattern.category.value] += 1
            
            if pattern.confidence >= 0.8:
                summary["by_confidence"]["high"] += 1
            elif pattern.confidence >= 0.6:
                summary["by_confidence"]["medium"] += 1
            else:
                summary["by_confidence"]["low"] += 1
        
        return dict(summary)
    
    def get_strategy_summary(self) -> Dict[str, Any]:
        """获取策略摘要"""
        summary = {
            "total_strategies": len(self.strategies),
            "by_type": defaultdict(int),
            "by_priority": defaultdict(int),
            "by_status": defaultdict(int)
        }
        
        for strategy in self.strategies.values():
            summary["by_type"][strategy.strategy_type.value] += 1
            summary["by_priority"][strategy.priority] += 1
            summary["by_status"][strategy.validation_status] += 1
        
        return dict(summary)
    
    def validate_strategy(self, strategy_id: str, success: bool, feedback: str = "") -> bool:
        """
        验证策略效果
        
        Args:
            strategy_id: 策略ID
            success: 是否成功
            feedback: 反馈信息
            
        Returns:
            bool: 验证是否成功
        """
        if strategy_id not in self.strategies:
            logger.warning(f"策略不存在: {strategy_id}")
            return False
        
        strategy = self.strategies[strategy_id]
        
        if success:
            strategy.validation_status = "validated"
            logger.info(f"策略验证成功: {strategy_id}")
        else:
            strategy.validation_status = "rejected"
            logger.warning(f"策略验证失败: {strategy_id}")
        
        # 可以记录验证反馈
        if feedback:
            strategy.description += f" [验证反馈: {feedback}]"
        
        return success
    
    def _recognize_temporal_patterns(self, experiences: List[Experience]) -> List[RecognizedPattern]:
        """识别时间模式"""
        patterns = []
        
        if len(experiences) < self.min_support:
            return patterns
        
        # 按时间排序
        sorted_exps = sorted(experiences, key=lambda x: x.timestamp)
        
        # 识别时间间隔模式
        time_intervals = []
        for i in range(1, len(sorted_exps)):
            interval = (sorted_exps[i].timestamp - sorted_exps[i-1].timestamp).total_seconds()
            time_intervals.append(interval)
        
        if len(time_intervals) >= self.min_support:
            avg_interval = statistics.mean(time_intervals)
            std_interval = statistics.stdev(time_intervals) if len(time_intervals) > 1 else 0
            
            # 识别规律性时间间隔
            if std_interval / avg_interval < 0.3:  # 低变异系数表示规律性
                pattern = RecognizedPattern(
                    pattern_id=f"temporal_regular_{datetime.now().timestamp()}",
                    category=PatternCategory.TEMPORAL_PATTERN,
                    description=f"规律性时间间隔: 平均{avg_interval:.1f}秒",
                    confidence=min(0.9, len(time_intervals) / 10),
                    support_count=len(time_intervals),
                    conditions={"avg_interval": avg_interval, "std_interval": std_interval},
                    examples=[exp.id for exp in sorted_exps[:3]],
                    implications=["可预测的执行节奏", "适合批量处理"]
                )
                patterns.append(pattern)
        
        # 识别时间段模式（如特定时间段成功率更高）
        by_hour = defaultdict(list)
        for exp in experiences:
            hour = exp.timestamp.hour
            by_hour[hour].append(exp)
        
        for hour, exps in by_hour.items():
            if len(exps) >= self.min_support:
                success_rate = len([e for e in exps if e.outcome == Outcome.SUCCESS]) / len(exps)
                
                if success_rate > 0.8 or success_rate < 0.4:  # 显著高或低
                    pattern = RecognizedPattern(
                        pattern_id=f"temporal_hour_{hour}_{datetime.now().timestamp()}",
                        category=PatternCategory.TEMPORAL_PATTERN,
                        description=f"时间段模式: {hour}时成功率{success_rate:.1%}",
                        confidence=success_rate,
                        support_count=len(exps),
                        conditions={"hour": hour, "success_rate": success_rate},
                        examples=[exp.id for exp in exps[:3]],
                        implications=[f"建议在{hour}时安排重要任务" if success_rate > 0.8 
                                     else f"避免在{hour}时安排重要任务"]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _recognize_sequential_patterns(self, experiences: List[Experience]) -> List[RecognizedPattern]:
        """识别序列模式"""
        patterns = []
        
        # 按任务序列分组
        task_sequences = defaultdict(list)
        for exp in experiences:
            if exp.task_id:
                task_sequences[exp.task_id].append(exp)
        
        for task_id, exps in task_sequences.items():
            if len(exps) >= self.min_support:
                # 按时间排序
                sorted_exps = sorted(exps, key=lambda x: x.timestamp)
                
                # 识别动作序列模式
                action_sequences = []
                for exp in sorted_exps:
                    if exp.actions:
                        action_types = [action.get('type', 'unknown') for action in exp.actions]
                        action_sequences.append(tuple(action_types))
                
                # 查找重复的动作序列
                sequence_counts = defaultdict(int)
                for seq in action_sequences:
                    if seq:  # 非空序列
                        sequence_counts[seq] += 1
                
                for seq, count in sequence_counts.items():
                    if count >= self.min_support:
                        seq_str = " → ".join(seq)
                        pattern = RecognizedPattern(
                            pattern_id=f"sequential_{task_id}_{hash(seq)}_{datetime.now().timestamp()}",
                            category=PatternCategory.SEQUENTIAL_PATTERN,
                            description=f"任务'{task_id}'的重复动作序列: {seq_str}",
                            confidence=count / len(sorted_exps),
                            support_count=count,
                            conditions={"task_id": task_id, "action_sequence": seq},
                            examples=[exp.id for exp in sorted_exps[:3]],
                            implications=["可自动化此序列", "优化序列执行顺序"]
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _recognize_contextual_patterns(self, experiences: List[Experience]) -> List[RecognizedPattern]:
        """识别上下文模式"""
        patterns = []
        
        # 按上下文特征分组
        context_groups = defaultdict(list)
        for exp in experiences:
            if exp.context:
                # 创建上下文特征键
                context_key = self._create_context_key(exp.context)
                context_groups[context_key].append(exp)
        
        for context_key, exps in context_groups.items():
            if len(exps) >= self.min_support:
                success_rate = len([e for e in exps if e.outcome == Outcome.SUCCESS]) / len(exps)
                
                if success_rate >= self.min_confidence or success_rate <= 0.3:
                    pattern = RecognizedPattern(
                        pattern_id=f"contextual_{hash(context_key)}_{datetime.now().timestamp()}",
                        category=PatternCategory.CONTEXTUAL_PATTERN,
                        description=f"上下文模式: 特定条件下成功率{success_rate:.1%}",
                        confidence=abs(success_rate - 0.5) * 2,  # 离0.5越远置信度越高
                        support_count=len(exps),
                        conditions={"context_key": context_key, "success_rate": success_rate},
                        examples=[exp.id for exp in exps[:3]],
                        implications=["识别成功/失败的关键条件", "优化上下文配置"]
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _recognize_performance_patterns(self, experiences: List[Experience]) -> List[RecognizedPattern]:
        """识别性能模式"""
        patterns = []
        
        # 按经验类型分组
        by_type = defaultdict(list)
        for exp in experiences:
            by_type[exp.experience_type.value].append(exp)
        
        for exp_type, exps in by_type.items():
            if len(exps) >= self.min_support:
                # 提取性能指标
                efficiencies = [e.metrics.get('efficiency', 0.5) for e in exps if 'efficiency' in e.metrics]
                execution_times = [e.metrics.get('execution_time', 1.0) for e in exps if 'execution_time' in e.metrics]
                
                if efficiencies:
                    avg_efficiency = statistics.mean(efficiencies)
                    std_efficiency = statistics.stdev(efficiencies) if len(efficiencies) > 1 else 0
                    
                    # 识别高效或低效模式
                    if avg_efficiency > 0.8 or avg_efficiency < 0.4:
                        pattern = RecognizedPattern(
                            pattern_id=f"performance_{exp_type}_efficiency_{datetime.now().timestamp()}",
                            category=PatternCategory.PERFORMANCE_PATTERN,
                            description=f"{exp_type}效率模式: 平均效率{avg_efficiency:.1%}",
                            confidence=min(0.9, len(efficiencies) / 5),
                            support_count=len(efficiencies),
                            conditions={"experience_type": exp_type, "avg_efficiency": avg_efficiency},
                            examples=[exp.id for exp in exps[:3]],
                            implications=["优化执行流程" if avg_efficiency < 0.4 else "推广高效方法"]
                        )
                        patterns.append(pattern)
                
                if execution_times:
                    avg_time = statistics.mean(execution_times)
                    
                    # 识别执行时间模式
                    if avg_time > 5.0 or avg_time < 1.0:
                        pattern = RecognizedPattern(
                            pattern_id=f"performance_{exp_type}_time_{datetime.now().timestamp()}",
                            category=PatternCategory.PERFORMANCE_PATTERN,
                            description=f"{exp_type}执行时间模式: 平均{avg_time:.1f}秒",
                            confidence=min(0.9, len(execution_times) / 5),
                            support_count=len(execution_times),
                            conditions={"experience_type": exp_type, "avg_execution_time": avg_time},
                            examples=[exp.id for exp in exps[:3]],
                            implications=["优化耗时操作" if avg_time > 5.0 else "快速执行方法"]
                        )
                        patterns.append(pattern)
        
        return patterns
    
    def _recognize_error_patterns(self, experiences: List[Experience]) -> List[RecognizedPattern]:
        """识别错误模式"""
        patterns = []
        
        # 收集失败经验
        failures = [exp for exp in experiences if exp.outcome in [Outcome.FAILURE, Outcome.PARTIAL_SUCCESS]]
        
        if len(failures) < self.min_support:
            return patterns
        
        # 按错误类型分组
        error_groups = defaultdict(list)
        for exp in failures:
            error_type = self._extract_error_type(exp)
            error_groups[error_type].append(exp)
        
        for error_type, exps in error_groups.items():
            if len(exps) >= self.min_support:
                pattern = RecognizedPattern(
                    pattern_id=f"error_{error_type}_{datetime.now().timestamp()}",
                    category=PatternCategory.ERROR_PATTERN,
                    description=f"重复错误模式: {error_type}",
                    confidence=len(exps) / len(failures),
                    support_count=len(exps),
                    conditions={"error_type": error_type},
                    examples=[exp.id for exp in exps[:3]],
                    implications=[f"需要解决{error_type}问题", "增加错误处理机制"]
                )
                patterns.append(pattern)
        
        return patterns
    
    def _generate_strategies_for_pattern(self, pattern: RecognizedPattern) -> List[GeneratedStrategy]:
        """为特定模式生成策略"""
        strategies = []
        
        if pattern.category == PatternCategory.ERROR_PATTERN:
            # 错误模式 → 预防性策略
            strategy = GeneratedStrategy(
                strategy_id=f"strategy_prevent_{pattern.pattern_id}",
                strategy_type=StrategyType.PREVENTIVE,
                target_pattern=pattern.pattern_id,
                description=f"预防{pattern.description}",
                actions=[
                    f"增加对{pattern.conditions.get('error_type', '错误')}的检查",
                    "改进错误处理逻辑",
                    "添加前置条件验证"
                ],
                expected_benefit=0.8,  # 预计减少80%的此类错误
                implementation_cost=0.3,  # 实施成本中等
                priority="high"
            )
            strategies.append(strategy)
        
        elif pattern.category == PatternCategory.PERFORMANCE_PATTERN:
            # 性能模式 → 优化策略
            avg_efficiency = pattern.conditions.get('avg_efficiency')
            avg_time = pattern.conditions.get('avg_execution_time')
            
            if avg_efficiency is not None and avg_efficiency < 0.6:
                strategy = GeneratedStrategy(
                    strategy_id=f"strategy_optimize_{pattern.pattern_id}",
                    strategy_type=StrategyType.OPTIMIZATION,
                    target_pattern=pattern.pattern_id,
                    description=f"优化{pattern.description}",
                    actions=[
                        "分析性能瓶颈",
                        "优化算法或流程",
                        "考虑并行处理"
                    ],
                    expected_benefit=0.4,  # 预计提升40%效率
                    implementation_cost=0.5,  # 实施成本较高
                    priority="medium"
                )
                strategies.append(strategy)
        
        elif pattern.category == PatternCategory.TEMPORAL_PATTERN:
            # 时间模式 → 适应性策略
            hour = pattern.conditions.get('hour')
            success_rate = pattern.conditions.get('success_rate')
            
            if hour is not None and success_rate is not None:
                if success_rate > 0.8:
                    strategy = GeneratedStrategy(
                        strategy_id=f"strategy_adapt_{pattern.pattern_id}",
                        strategy_type=StrategyType.ADAPTIVE,
                        target_pattern=pattern.pattern_id,
                        description=f"利用{hour}时的高成功率",
                        actions=[
                            f"在{hour}时安排重要任务",
                            "调整任务调度策略",
                            "监控时间段效果"
                        ],
                        expected_benefit=0.2,  # 预计提升20%成功率
                        implementation_cost=0.2,  # 实施成本低
                        priority="medium"
                    )
                    strategies.append(strategy)
        
        elif pattern.category == PatternCategory.SEQUENTIAL_PATTERN:
            # 序列模式 → 优化策略
            strategy = GeneratedStrategy(
                strategy_id=f"strategy_sequence_{pattern.pattern_id}",
                strategy_type=StrategyType.OPTIMIZATION,
                target_pattern=pattern.pattern_id,
                description=f"优化重复动作序列",
                actions=[
                    "自动化序列执行",
                    "优化步骤顺序",
                    "添加检查点"
                ],
                expected_benefit=0.3,  # 预计提升30%效率
                implementation_cost=0.4,  # 实施成本中等
                priority="medium"
            )
            strategies.append(strategy)
        
        # 为所有模式添加通用策略
        generic_strategy = GeneratedStrategy(
            strategy_id=f"strategy_generic_{pattern.pattern_id}",
            strategy_type=StrategyType.ADAPTIVE,
            target_pattern=pattern.pattern_id,
            description=f"基于{pattern.category.value}的适应性调整",
            actions=[
                "监控模式变化",
                "调整执行参数",
                "记录调整效果"
            ],
            expected_benefit=0.1,  # 预计10%改进
            implementation_cost=0.1,  # 实施成本低
            priority="low"
        )
        strategies.append(generic_strategy)
        
        return strategies
    
    def _create_context_key(self, context: Dict[str, Any]) -> str:
        """创建上下文特征键"""
        # 提取关键上下文特征
        key_parts = []
        
        for key, value in context.items():
            if isinstance(value, (str, int, float, bool)):
                key_parts.append(f"{key}:{value}")
            elif isinstance(value, list):
                key_parts.append(f"{key}:list[{len(value)}]")
            elif isinstance(value, dict):
                key_parts.append(f"{key}:dict[{len(value)}]")
        
        return "|".join(sorted(key_parts))
    
    def _extract_error_type(self, experience: Experience) -> str:
        """提取错误类型"""
        if 'error' in experience.context:
            error = str(experience.context['error']).lower()
            
            error_keywords = {
                'timeout': '超时错误',
                'permission': '权限错误',
                'not found': '资源未找到',
                'connection': '连接错误',
                'memory': '内存错误',
                'syntax': '语法错误',
                'type': '类型错误',
                'value': '值错误'
            }
            
            for keyword, error_type in error_keywords.items():
                if keyword in error:
                    return error_type
        
        # 根据经验类型判断
        if experience.experience_type == ExperienceType.TOOL_USAGE:
            return '工具使用错误'
        elif experience.experience_type == ExperienceType.REASONING:
            return '推理错误'
        elif experience.experience_type == ExperienceType.PROBLEM_SOLVING:
            return '问题解决错误'
        
        return '未知错误'
    
    def _strategy_priority_score(self, strategy: GeneratedStrategy) -> int:
        """计算策略优先级分数（分数越低优先级越高）"""
        priority_map = {"high": 1, "medium": 2, "low": 3}
        
        # 综合考虑预期收益和实施成本
        benefit_cost_ratio = strategy.expected_benefit / max(0.01, strategy.implementation_cost)
        
        return priority_map.get(strategy.priority, 3) * 10 - int(benefit_cost_ratio * 10)


# 导出主要类
__all__ = [
    'PatternRecognizer',
    'PatternCategory',
    'StrategyType',
    'RecognizedPattern',
    'GeneratedStrategy'
]

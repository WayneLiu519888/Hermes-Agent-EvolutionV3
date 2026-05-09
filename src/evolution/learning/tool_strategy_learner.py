"""
工具策略学习器 - 学习能力进化的关键组件
负责分析工具使用模式，优化工具选择和执行策略
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum
import statistics
from collections import defaultdict
import logging
import random

from ..db_utils import get_evolution_db

logger = logging.getLogger(__name__)


class ToolStrategyType(Enum):
    """工具策略类型枚举"""
    EFFICIENCY_OPTIMIZED = "efficiency_optimized"  # 效率优化策略
    RELIABILITY_OPTIMIZED = "reliability_optimized"  # 可靠性优化策略
    ACCURACY_OPTIMIZED = "accuracy_optimized"  # 准确性优化策略
    ADAPTIVE = "adaptive"  # 自适应策略


@dataclass
class ToolPerformance:
    """工具性能数据"""
    tool_name: str
    success_count: int = 0
    failure_count: int = 0
    total_time: float = 0.0
    avg_time: float = 0.0
    success_rate: float = 0.0
    last_used: Optional[datetime] = None
    usage_count: int = 0


@dataclass
class StrategyPerformance:
    """策略性能数据"""
    strategy_type: ToolStrategyType
    success_rate: float = 0.0
    avg_efficiency: float = 0.0
    usage_count: int = 0
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ToolRecommendation:
    """工具推荐"""
    tool_name: str
    confidence: float
    reason: str
    expected_efficiency: float


@dataclass
class StrategyUpdate:
    """策略更新"""
    old_strategy: ToolStrategyType
    new_strategy: ToolStrategyType
    reason: str
    expected_improvement: float


class ToolStrategyLearner:
    """工具策略学习器"""
    
    def __init__(self, db_path: str = "tools.db"):
        """初始化学习器
        
        Args:
            db_path: 数据库路径（用于持久化工具使用历史）
        """
        self.db_path = db_path
        self.tool_performance: Dict[str, ToolPerformance] = {}
        self.strategy_performance: Dict[ToolStrategyType, StrategyPerformance] = {}
        self.current_strategy: ToolStrategyType = ToolStrategyType.ADAPTIVE
        
        # 学习参数
        self.exploration_rate = 0.2  # 探索率
        self.learning_rate = 0.1  # 学习率
        self.min_samples = 3  # 最小样本数
        
        # 初始化策略性能
        for strategy in ToolStrategyType:
            self.strategy_performance[strategy] = StrategyPerformance(
                strategy_type=strategy,
                success_rate=0.5,  # 初始假设50%成功率
                avg_efficiency=0.5,  # 初始假设50%效率
                usage_count=0
            )
        
        # 🆕 持久化: 初始化DB并从历史数据重建内存状态
        self._init_db()
        self._load_from_db()
    
    def _init_db(self):
        """初始化持久化数据库表"""
        conn = get_evolution_db(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tool_usage_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                success INTEGER NOT NULL,
                execution_time REAL NOT NULL,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                context TEXT
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_usage_tool ON tool_usage_history(tool_name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tool_usage_time ON tool_usage_history(timestamp)")
        conn.commit()
    
    def _load_from_db(self, days: int = 7):
        """从 DB 加载历史数据重建内存状态
        
        Args:
            days: 加载最近N天的数据
        """
        conn = get_evolution_db(self.db_path)
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        rows = conn.execute(
            "SELECT tool_name, success, execution_time FROM tool_usage_history "
            "WHERE timestamp >= ? ORDER BY timestamp",
            (cutoff,)
        ).fetchall()
        
        for row in rows:
            tool_name = row[0]
            success = bool(row[1])
            execution_time = row[2]
            
            if tool_name not in self.tool_performance:
                self.tool_performance[tool_name] = ToolPerformance(tool_name=tool_name)
            
            perf = self.tool_performance[tool_name]
            if success:
                perf.success_count += 1
            else:
                perf.failure_count += 1
            perf.total_time += execution_time
            perf.usage_count += 1
            
            if perf.usage_count > 0:
                perf.avg_time = perf.total_time / perf.usage_count
                total = perf.success_count + perf.failure_count
                perf.success_rate = perf.success_count / total if total > 0 else 0.0
        
        logger.info("从DB加载了 %d 条工具使用记录 (%d 个工具)", len(rows), len(self.tool_performance))
    
    def record_tool_usage(self, tool_name: str, success: bool, 
                         execution_time: float, context: Dict[str, Any] = None):
        """
        记录工具使用情况
        
        Args:
            tool_name: 工具名称
            success: 是否成功
            execution_time: 执行时间（秒）
            context: 使用上下文
        """
        logger.info(f"记录工具使用: {tool_name}, 成功: {success}, 时间: {execution_time:.2f}s")
        
        # 获取或创建工具性能记录
        if tool_name not in self.tool_performance:
            self.tool_performance[tool_name] = ToolPerformance(tool_name=tool_name)
        
        perf = self.tool_performance[tool_name]
        
        # 更新统计数据
        if success:
            perf.success_count += 1
        else:
            perf.failure_count += 1
        
        perf.total_time += execution_time
        perf.usage_count += 1
        perf.last_used = datetime.now()
        
        # 计算平均值
        if perf.usage_count > 0:
            perf.avg_time = perf.total_time / perf.usage_count
            total_attempts = perf.success_count + perf.failure_count
            perf.success_rate = perf.success_count / total_attempts if total_attempts > 0 else 0.0
        
        # 更新当前策略性能
        self._update_strategy_performance(success, execution_time, context)
        
        # 检查是否需要调整策略
        self._consider_strategy_update()
        
        # 🆕 同步写入持久化数据库
        self._persist_usage(tool_name, success, execution_time, context)
    
    def recommend_tool(self, task_description: str, available_tools: List[str], 
                      context: Dict[str, Any] = None) -> List[ToolRecommendation]:
        """
        推荐工具
        
        Args:
            task_description: 任务描述
            available_tools: 可用工具列表
            context: 任务上下文
            
        Returns:
            List[ToolRecommendation]: 工具推荐列表，按置信度排序
        """
        recommendations = []
        
        for tool_name in available_tools:
            if tool_name in self.tool_performance:
                perf = self.tool_performance[tool_name]
                
                # 根据当前策略计算推荐置信度
                confidence = self._calculate_tool_confidence(tool_name, perf, context)
                
                # 生成推荐原因
                reason = self._generate_recommendation_reason(tool_name, perf, confidence)
                
                # 估计预期效率
                expected_efficiency = self._estimate_efficiency(tool_name, perf, context)
                
                recommendation = ToolRecommendation(
                    tool_name=tool_name,
                    confidence=confidence,
                    reason=reason,
                    expected_efficiency=expected_efficiency
                )
                recommendations.append(recommendation)
            else:
                # 新工具，给予中等置信度（探索）
                recommendation = ToolRecommendation(
                    tool_name=tool_name,
                    confidence=0.5,
                    reason="新工具，建议探索使用",
                    expected_efficiency=0.5
                )
                recommendations.append(recommendation)
        
        # 按置信度排序
        recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        # 添加探索性推荐（有一定概率推荐低置信度工具）
        if random.random() < self.exploration_rate and len(recommendations) > 1:
            # 随机选择一个非最高置信度的工具，提升其排名
            if len(recommendations) > 2:
                explore_idx = random.randint(1, len(recommendations) - 1)
                recommendations[explore_idx].confidence += 0.1
                recommendations[explore_idx].reason += " (探索推荐)"
                recommendations.sort(key=lambda x: x.confidence, reverse=True)
        
        return recommendations
    
    def get_current_strategy(self) -> ToolStrategyType:
        """获取当前策略"""
        return self.current_strategy
    
    def get_strategy_performance(self) -> Dict[ToolStrategyType, StrategyPerformance]:
        """获取策略性能数据"""
        return self.strategy_performance.copy()
    
    def get_tool_performance_summary(self) -> Dict[str, Dict[str, Any]]:
        """获取工具性能摘要"""
        summary = {}
        for tool_name, perf in self.tool_performance.items():
            summary[tool_name] = {
                "success_rate": perf.success_rate,
                "avg_time": perf.avg_time,
                "usage_count": perf.usage_count,
                "last_used": perf.last_used.isoformat() if perf.last_used else None
            }
        return summary
    
    def learn_from_experiences(self, experiences: List[Dict[str, Any]]):
        """
        从经验数据中学习
        
        Args:
            experiences: 经验数据列表
        """
        logger.info(f"从{len(experiences)}条经验中学习")
        
        for exp in experiences:
            if 'tool_name' in exp and 'success' in exp:
                tool_name = exp['tool_name']
                success = exp['success']
                execution_time = exp.get('execution_time', 1.0)
                context = exp.get('context', {})
                
                self.record_tool_usage(tool_name, success, execution_time, context)
    
    def _calculate_tool_confidence(self, tool_name: str, perf: ToolPerformance, 
                                  context: Dict[str, Any] = None) -> float:
        """计算工具置信度"""
        base_confidence = perf.success_rate
        
        # 根据当前策略调整置信度
        if self.current_strategy == ToolStrategyType.EFFICIENCY_OPTIMIZED:
            # 效率优化策略：偏好执行时间短的工具
            time_factor = 1.0 / (1.0 + perf.avg_time)  # 时间越短，因子越大
            base_confidence *= (0.7 + 0.3 * time_factor)
        
        elif self.current_strategy == ToolStrategyType.RELIABILITY_OPTIMIZED:
            # 可靠性优化策略：偏好成功率高的工具
            reliability_factor = perf.success_rate
            base_confidence *= (0.3 + 0.7 * reliability_factor)
        
        elif self.current_strategy == ToolStrategyType.ACCURACY_OPTIMIZED:
            # 准确性优化策略（假设有准确性指标）
            accuracy = context.get('expected_accuracy', 0.8) if context else 0.8
            base_confidence *= accuracy
        
        # 考虑使用频率（避免过度依赖单一工具）
        usage_factor = 1.0 / (1.0 + perf.usage_count / 10)  # 使用越多，因子越小
        base_confidence *= (0.8 + 0.2 * usage_factor)
        
        # 确保置信度在合理范围内
        return max(0.1, min(0.95, base_confidence))
    
    def _generate_recommendation_reason(self, tool_name: str, perf: ToolPerformance, 
                                       confidence: float) -> str:
        """生成推荐原因"""
        reasons = []
        
        if perf.success_rate > 0.8:
            reasons.append("高成功率")
        elif perf.success_rate < 0.5:
            reasons.append("需谨慎使用")
        
        if perf.avg_time < 1.0:
            reasons.append("执行快速")
        elif perf.avg_time > 5.0:
            reasons.append("执行较慢")
        
        if perf.usage_count > 10:
            reasons.append("经验丰富")
        elif perf.usage_count < 3:
            reasons.append("使用较少")
        
        if confidence > 0.7:
            reasons.append("高置信度推荐")
        elif confidence < 0.3:
            reasons.append("低置信度")
        
        if not reasons:
            reasons.append("一般推荐")
        
        return f"{tool_name}: {', '.join(reasons)}"
    
    def _estimate_efficiency(self, tool_name: str, perf: ToolPerformance, 
                            context: Dict[str, Any] = None) -> float:
        """估计工具效率"""
        # 基础效率基于成功率和执行时间
        time_factor = 1.0 / (1.0 + perf.avg_time)  # 标准化到0-1
        base_efficiency = (perf.success_rate * 0.7 + time_factor * 0.3)
        
        # 根据上下文调整
        if context:
            task_complexity = context.get('complexity', 0.5)
            # 复杂任务可能需要更可靠但较慢的工具
            if task_complexity > 0.7:
                base_efficiency = perf.success_rate * 0.9 + time_factor * 0.1
            elif task_complexity < 0.3:
                base_efficiency = perf.success_rate * 0.3 + time_factor * 0.7
        
        return max(0.1, min(0.99, base_efficiency))
    
    def _update_strategy_performance(self, success: bool, execution_time: float, 
                                    context: Dict[str, Any] = None):
        """更新策略性能"""
        strategy_perf = self.strategy_performance[self.current_strategy]
        
        # 更新使用次数
        strategy_perf.usage_count += 1
        
        # 更新成功率（移动平均）
        success_value = 1.0 if success else 0.0
        strategy_perf.success_rate = (1 - self.learning_rate) * strategy_perf.success_rate +                                     self.learning_rate * success_value
        
        # 更新效率（基于执行时间，假设理想时间为1秒）
        efficiency = 1.0 / (1.0 + execution_time)
        strategy_perf.avg_efficiency = (1 - self.learning_rate) * strategy_perf.avg_efficiency +                                       self.learning_rate * efficiency
        
        strategy_perf.last_updated = datetime.now()
    
    def _consider_strategy_update(self):
        """考虑策略更新"""
        # 只在有足够数据时考虑更新
        total_samples = sum(sp.usage_count for sp in self.strategy_performance.values())
        if total_samples < self.min_samples * len(ToolStrategyType):
            return
        
        # 评估所有策略
        strategy_scores = {}
        for strategy, perf in self.strategy_performance.items():
            if perf.usage_count >= self.min_samples:
                # 综合评分：成功率权重0.6，效率权重0.4
                score = perf.success_rate * 0.6 + perf.avg_efficiency * 0.4
                strategy_scores[strategy] = score
        
        if not strategy_scores:
            return
        
        # 找到最佳策略
        best_strategy = max(strategy_scores.items(), key=lambda x: x[1])
        current_score = strategy_scores.get(self.current_strategy, 0)
        
        # 如果最佳策略明显优于当前策略，考虑切换
        improvement = best_strategy[1] - current_score
        if improvement > 0.1 and best_strategy[0] != self.current_strategy:  # 10%的改进阈值
            logger.info(f"考虑策略更新: {self.current_strategy} -> {best_strategy[0]}, 改进: {improvement:.2f}")
            
            # 有一定概率切换策略（避免频繁切换）
            if random.random() < 0.7:  # 70%概率切换
                old_strategy = self.current_strategy
                self.current_strategy = best_strategy[0]
                
                update = StrategyUpdate(
                    old_strategy=old_strategy,
                    new_strategy=best_strategy[0],
                    reason=f"性能改进 {improvement:.1%}",
                    expected_improvement=improvement
                )
                
                logger.info(f"策略已更新: {update}")
                return update
        
        return None

    def _persist_usage(self, tool_name: str, success: bool, 
                       execution_time: float, context: Dict[str, Any] = None):
        """将工具使用记录写入持久化数据库"""
        try:
            conn = get_evolution_db(self.db_path)
            conn.execute(
                "INSERT INTO tool_usage_history (tool_name, success, execution_time, timestamp, context) "
                "VALUES (?, ?, ?, ?, ?)",
                (tool_name, int(success), execution_time, 
                 datetime.now().isoformat(), json.dumps(context or {}))
            )
            conn.commit()
        except Exception as e:
            logger.warning("持久化工具使用记录失败: %s", e)


# 导出主要类
__all__ = [
    'ToolStrategyLearner', 
    'ToolStrategyType',
    'ToolPerformance',
    'StrategyPerformance',
    'ToolRecommendation',
    'StrategyUpdate'
]

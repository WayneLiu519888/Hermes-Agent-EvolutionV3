"""
反思机制模块 - 深度分析和改进学习
支持失败分析、模式识别、策略优化
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import numpy as np
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReflectionType(Enum):
    """反思类型"""
    FAILURE_ANALYSIS = "failure_analysis"
    SUCCESS_ANALYSIS = "success_analysis"
    PATTERN_RECOGNITION = "pattern_recognition"
    STRATEGY_OPTIMIZATION = "strategy_optimization"
    KNOWLEDGE_EXTRACTION = "knowledge_extraction"


class ReflectionDepth(Enum):
    """反思深度"""
    SURFACE = "surface"      # 表面分析
    DEEP = "deep"           # 深度分析
    METACOGNITIVE = "metacognitive"  # 元认知分析


@dataclass
class Experience:
    """经验数据"""
    experience_id: str
    task_type: str
    task_description: str
    input_data: Dict[str, Any]
    actions_taken: List[Dict[str, Any]]
    outcome: Dict[str, Any]
    success: bool
    performance_metrics: Dict[str, float]
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "experience_id": self.experience_id,
            "task_type": self.task_type,
            "task_description": self.task_description,
            "input_data": self.input_data,
            "actions_taken": self.actions_taken,
            "outcome": self.outcome,
            "success": self.success,
            "performance_metrics": self.performance_metrics,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata
        }


@dataclass
class ReflectionResult:
    """反思结果"""
    reflection_id: str
    experience_id: str
    reflection_type: ReflectionType
    reflection_depth: ReflectionDepth
    insights: List[str]
    root_causes: List[str]
    improvement_suggestions: List[str]
    confidence_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "reflection_id": self.reflection_id,
            "experience_id": self.experience_id,
            "reflection_type": self.reflection_type.value,
            "reflection_depth": self.reflection_depth.value,
            "insights": self.insights,
            "root_causes": self.root_causes,
            "improvement_suggestions": self.improvement_suggestions,
            "confidence_score": self.confidence_score,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat()
        }


class PatternRecognizer:
    """模式识别器"""
    
    def __init__(self):
        self.patterns = defaultdict(list)
        self.pattern_counter = 0
        
    def analyze_experiences(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """分析经验数据，识别模式"""
        patterns = []
        
        # 按任务类型分组
        experiences_by_type = defaultdict(list)
        for exp in experiences:
            experiences_by_type[exp.task_type].append(exp)
        
        # 识别每种任务类型的模式
        for task_type, type_experiences in experiences_by_type.items():
            if len(type_experiences) < 3:
                continue  # 数据太少，无法识别模式
            
            # 识别成功模式
            success_patterns = self._identify_success_patterns(type_experiences)
            if success_patterns:
                patterns.extend(success_patterns)
            
            # 识别失败模式
            failure_patterns = self._identify_failure_patterns(type_experiences)
            if failure_patterns:
                patterns.extend(failure_patterns)
            
            # 识别性能模式
            performance_patterns = self._identify_performance_patterns(type_experiences)
            if performance_patterns:
                patterns.extend(performance_patterns)
        
        return patterns
    
    def _identify_success_patterns(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """识别成功模式"""
        successful_exps = [exp for exp in experiences if exp.success]
        
        if len(successful_exps) < 2:
            return []
        
        patterns = []
        
        # 识别共同特征
        common_actions = self._find_common_actions(successful_exps)
        if common_actions:
            patterns.append({
                "pattern_id": f"success_pattern_{self._get_next_pattern_id()}",
                "pattern_type": "success_common_actions",
                "description": "成功经验中的共同动作序列",
                "confidence": min(1.0, len(common_actions) / 5.0),
                "data": {"common_actions": common_actions}
            })
        
        # 识别性能特征
        avg_performance = self._calculate_average_performance(successful_exps)
        patterns.append({
            "pattern_id": f"success_performance_{self._get_next_pattern_id()}",
            "pattern_type": "success_performance_profile",
            "description": "成功经验的平均性能特征",
            "confidence": 0.8,
            "data": {"average_performance": avg_performance}
        })
        
        return patterns
    
    def _identify_failure_patterns(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """识别失败模式"""
        failed_exps = [exp for exp in experiences if not exp.success]
        
        if len(failed_exps) < 2:
            return []
        
        patterns = []
        
        # 识别常见错误
        common_errors = self._find_common_errors(failed_exps)
        if common_errors:
            patterns.append({
                "pattern_id": f"failure_pattern_{self._get_next_pattern_id()}",
                "pattern_type": "common_errors",
                "description": "失败经验中的常见错误",
                "confidence": min(1.0, len(common_errors) / 3.0),
                "data": {"common_errors": common_errors}
            })
        
        # 识别失败前的动作序列
        failure_sequences = self._analyze_failure_sequences(failed_exps)
        if failure_sequences:
            patterns.append({
                "pattern_id": f"failure_sequence_{self._get_next_pattern_id()}",
                "pattern_type": "failure_sequence",
                "description": "导致失败的常见动作序列",
                "confidence": 0.7,
                "data": {"failure_sequences": failure_sequences}
            })
        
        return patterns
    
    def _identify_performance_patterns(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """识别性能模式"""
        if len(experiences) < 3:
            return []
        
        patterns = []
        
        # 识别性能趋势
        performance_trend = self._analyze_performance_trend(experiences)
        if performance_trend:
            patterns.append({
                "pattern_id": f"performance_trend_{self._get_next_pattern_id()}",
                "pattern_type": "performance_trend",
                "description": "性能随时间的变化趋势",
                "confidence": 0.6,
                "data": {"trend": performance_trend}
            })
        
        # 识别性能相关性
        correlations = self._find_performance_correlations(experiences)
        if correlations:
            patterns.append({
                "pattern_id": f"performance_correlation_{self._get_next_pattern_id()}",
                "pattern_type": "performance_correlation",
                "description": "性能与各种因素的相关性",
                "confidence": 0.5,
                "data": {"correlations": correlations}
            })
        
        return patterns
    
    def _find_common_actions(self, experiences: List[Experience]) -> List[str]:
        """查找共同动作"""
        if not experiences:
            return []
        
        # 提取所有动作序列
        all_actions = []
        for exp in experiences:
            actions = [action.get("action_type", "") for action in exp.actions_taken]
            all_actions.append(tuple(actions))
        
        # 查找最常见的动作序列
        from collections import Counter
        action_counts = Counter(all_actions)
        
        if action_counts:
            most_common = action_counts.most_common(1)[0]
            if most_common[1] > 1:  # 至少出现两次
                return list(most_common[0])
        
        return []
    
    def _find_common_errors(self, experiences: List[Experience]) -> List[str]:
        """查找常见错误"""
        errors = []
        for exp in experiences:
            if "error" in exp.outcome:
                errors.append(exp.outcome["error"])
            elif "failure_reason" in exp.metadata:
                errors.append(exp.metadata["failure_reason"])
        
        from collections import Counter
        error_counts = Counter(errors)
        
        common_errors = []
        for error, count in error_counts.items():
            if count > 1 and error:  # 至少出现两次且非空
                common_errors.append(f"{error} (出现{count}次)")
        
        return common_errors[:3]  # 返回最多3个常见错误
    
    def _calculate_average_performance(self, experiences: List[Experience]) -> Dict[str, float]:
        """计算平均性能"""
        if not experiences:
            return {}
        
        avg_metrics = defaultdict(float)
        count = 0
        
        for exp in experiences:
            for metric, value in exp.performance_metrics.items():
                avg_metrics[metric] += value
            count += 1
        
        for metric in avg_metrics:
            avg_metrics[metric] /= count
        
        return dict(avg_metrics)
    
    def _analyze_failure_sequences(self, experiences: List[Experience]) -> List[List[str]]:
        """分析失败序列"""
        sequences = []
        
        for exp in experiences:
            # 提取失败前的最后3个动作
            last_actions = exp.actions_taken[-3:]
            action_types = [action.get("action_type", "") for action in last_actions]
            if action_types:
                sequences.append(action_types)
        
        # 返回出现次数最多的序列
        from collections import Counter
        if sequences:
            sequence_counts = Counter([tuple(seq) for seq in sequences])
            most_common = sequence_counts.most_common(2)
            return [list(seq[0]) for seq in most_common if seq[1] > 1]
        
        return []
    
    def _analyze_performance_trend(self, experiences: List[Experience]) -> Dict[str, Any]:
        """分析性能趋势"""
        if len(experiences) < 3:
            return {}
        
        # 按时间排序
        sorted_exps = sorted(experiences, key=lambda x: x.timestamp)
        
        # 提取主要性能指标
        main_metric = None
        for exp in experiences:
            if exp.performance_metrics:
                main_metric = list(exp.performance_metrics.keys())[0]
                break
        
        if not main_metric:
            return {}
        
        # 计算趋势
        values = []
        timestamps = []
        
        for exp in sorted_exps:
            if main_metric in exp.performance_metrics:
                values.append(exp.performance_metrics[main_metric])
                timestamps.append(exp.timestamp.timestamp())
        
        if len(values) < 3:
            return {}
        
        # 简单线性趋势分析
        try:
            from scipy import stats
            slope, intercept, r_value, p_value, std_err = stats.linregress(timestamps, values)
            
            trend = "上升" if slope > 0 else "下降" if slope < 0 else "稳定"
            
            return {
                "metric": main_metric,
                "trend": trend,
                "slope": float(slope),
                "r_squared": float(r_value ** 2),
                "confidence": min(1.0, abs(r_value))
            }
        except:
            return {}
    
    def _find_performance_correlations(self, experiences: List[Experience]) -> List[Dict[str, Any]]:
        """查找性能相关性"""
        # 简化实现
        correlations = []
        
        # 检查动作数量与性能的相关性
        action_counts = []
        performances = []
        
        for exp in experiences:
            if exp.performance_metrics:
                main_metric = list(exp.performance_metrics.keys())[0]
                action_counts.append(len(exp.actions_taken))
                performances.append(exp.performance_metrics[main_metric])
        
        if len(action_counts) >= 3:
            try:
                correlation = np.corrcoef(action_counts, performances)[0, 1]
                if abs(correlation) > 0.3:
                    direction = "正相关" if correlation > 0 else "负相关"
                    correlations.append({
                        "factor": "动作数量",
                        "correlation": float(correlation),
                        "direction": direction,
                        "interpretation": f"动作数量与性能{direction}"
                    })
            except:
                pass
        
        return correlations
    
    def _get_next_pattern_id(self) -> int:
        """获取下一个模式ID"""
        self.pattern_counter += 1
        return self.pattern_counter


class ReflectionEngine:
    """反思引擎"""
    
    def __init__(self):
        self.pattern_recognizer = PatternRecognizer()
        self.reflection_history = []
        self.experience_store = []
        self.max_experiences = 1000
        
        logger.info("反思引擎初始化完成")
    
    def add_experience(self, experience: Experience) -> None:
        """添加经验"""
        self.experience_store.append(experience)
        
        # 限制存储大小
        if len(self.experience_store) > self.max_experiences:
            self.experience_store = self.experience_store[-self.max_experiences:]
        
        logger.debug(f"经验已添加: {experience.experience_id}")
    
    def reflect_on_experience(
        self,
        experience: Experience,
        reflection_type: ReflectionType = ReflectionType.FAILURE_ANALYSIS,
        depth: ReflectionDepth = ReflectionDepth.DEEP
    ) -> ReflectionResult:
        """对经验进行反思"""
        import uuid
        
        reflection_id = str(uuid.uuid4())
        
        # 根据反思类型和深度进行分析
        if reflection_type == ReflectionType.FAILURE_ANALYSIS:
            insights, root_causes, suggestions = self._analyze_failure(experience, depth)
        elif reflection_type == ReflectionType.SUCCESS_ANALYSIS:
            insights, root_causes, suggestions = self._analyze_success(experience, depth)
        elif reflection_type == ReflectionType.PATTERN_RECOGNITION:
            insights, root_causes, suggestions = self._analyze_patterns(experience, depth)
        else:
            insights, root_causes, suggestions = self._general_analysis(experience, depth)
        
        # 计算置信度
        confidence = self._calculate_confidence(experience, insights, depth)
        
        # 创建反思结果
        result = ReflectionResult(
            reflection_id=reflection_id,
            experience_id=experience.experience_id,
            reflection_type=reflection_type,
            reflection_depth=depth,
            insights=insights,
            root_causes=root_causes,
            improvement_suggestions=suggestions,
            confidence_score=confidence,
            metadata={
                "analysis_time": datetime.now().isoformat(),
                "experience_success": experience.success
            }
        )
        
        # 保存到历史
        self.reflection_history.append(result)
        
        logger.info(f"反思完成: {reflection_id}, 类型: {reflection_type.value}, 深度: {depth.value}")
        
        return result
    
    def _analyze_failure(self, experience: Experience, depth: ReflectionDepth) -> Tuple[List[str], List[str], List[str]]:
        """分析失败"""
        insights = []
        root_causes = []
        suggestions = []
        
        # 表面分析
        insights.append(f"任务失败: {experience.task_description}")
        
        if "error" in experience.outcome:
            root_causes.append(f"具体错误: {experience.outcome['error']}")
        
        # 深度分析
        if depth in [ReflectionDepth.DEEP, ReflectionDepth.METACOGNITIVE]:
            # 分析动作序列
            if experience.actions_taken:
                last_action = experience.actions_taken[-1]
                insights.append(f"最后执行的动作: {last_action.get('action_type', '未知')}")
            
            # 分析性能指标
            if experience.performance_metrics:
                worst_metric = min(experience.performance_metrics.items(), key=lambda x: x[1])
                insights.append(f"最差的性能指标: {worst_metric[0]} = {worst_metric[1]:.2f}")
        
        # 元认知分析
        if depth == ReflectionDepth.METACOGNITIVE:
            # 分析决策过程
            insights.append("需要改进决策过程")
            suggestions.append("在关键决策点增加验证步骤")
            suggestions.append("建立更完善的错误处理机制")
        
        # 通用建议
        suggestions.append("回顾类似成功案例，学习有效策略")
        suggestions.append("将任务分解为更小的子任务")
        suggestions.append("增加测试和验证步骤")
        
        return insights, root_causes, suggestions
    
    def _analyze_success(self, experience: Experience, depth: ReflectionDepth) -> Tuple[List[str], List[str], List[str]]:
        """分析成功"""
        insights = []
        root_causes = []
        suggestions = []
        
        # 表面分析
        insights.append(f"任务成功: {experience.task_description}")
        
        if experience.performance_metrics:
            best_metric = max(experience.performance_metrics.items(), key=lambda x: x[1])
            insights.append(f"最佳性能指标: {best_metric[0]} = {best_metric[1]:.2f}")
        
        # 深度分析
        if depth in [ReflectionDepth.DEEP, ReflectionDepth.METACOGNITIVE]:
            # 分析成功因素
            if experience.actions_taken:
                key_actions = [action.get('action_type', '') for action in experience.actions_taken]
                insights.append(f"关键动作序列: {', '.join(key_actions[:3])}")
            
            # 分析效率
            if "execution_time" in experience.metadata:
                insights.append(f"执行时间: {experience.metadata['execution_time']}秒")
        
        # 元认知分析
        if depth == ReflectionDepth.METACOGNITIVE:
            insights.append("成功模式可复用于类似任务")
            suggestions.append("将成功策略抽象为可重用模板")
            suggestions.append("建立最佳实践库")
        
        # 通用建议
        suggestions.append("记录成功的关键决策点")
        suggestions.append("分析可优化的环节")
        suggestions.append("将成功经验分享给其他任务")
        
        return insights, root_causes, suggestions
    
    def _analyze_patterns(self, experience: Experience, depth: ReflectionDepth) -> Tuple[List[str], List[str], List[str]]:
        """分析模式"""
        insights = []
        root_causes = []
        suggestions = []
        
        # 获取相关经验进行分析
        related_experiences = self._get_related_experiences(experience)
        
        if len(related_experiences) >= 2:
            # 识别模式
            patterns = self.pattern_recognizer.analyze_experiences(related_experiences)
            
            for pattern in patterns:
                insights.append(f"识别到模式: {pattern['description']}")
                
                if "common_actions" in pattern.get("data", {}):
                    suggestions.append(f"采用成功动作序列: {pattern['data']['common_actions']}")
                
                if "common_errors" in pattern.get("data", {}):
                    root_causes.extend(pattern['data']['common_errors'])
        
        else:
            insights.append("数据不足，无法识别显著模式")
            suggestions.append("积累更多经验数据后再进行分析")
        
        return insights, root_causes, suggestions
    
    def _general_analysis(self, experience: Experience, depth: ReflectionDepth) -> Tuple[List[str], List[str], List[str]]:
        """通用分析"""
        insights = []
        root_causes = []
        suggestions = []
        
        insights.append(f"任务分析: {experience.task_description}")
        
        if experience.success:
            insights.append("任务执行成功")
        else:
            insights.append("任务执行失败")
        
        # 性能分析
        if experience.performance_metrics:
            insights.append("性能指标:")
            for metric, value in experience.performance_metrics.items():
                insights.append(f"  - {metric}: {value:.2f}")
        
        suggestions.append("定期进行经验回顾和总结")
        suggestions.append("建立知识库，积累经验")
        
        return insights, root_causes, suggestions
    
    def _get_related_experiences(self, experience: Experience, limit: int = 10) -> List[Experience]:
        """获取相关经验"""
        # 按任务类型和相似性筛选
        related = []
        
        for exp in self.experience_store:
            if exp.experience_id == experience.experience_id:
                continue
            
            # 简单筛选：相同任务类型
            if exp.task_type == experience.task_type:
                related.append(exp)
            
            if len(related) >= limit:
                break
        
        return related
    
    def _calculate_confidence(self, experience: Experience, insights: List[str], depth: ReflectionDepth) -> float:
        """计算置信度"""
        base_confidence = 0.5
        
        # 根据深度调整
        if depth == ReflectionDepth.DEEP:
            base_confidence += 0.2
        elif depth == ReflectionDepth.METACOGNITIVE:
            base_confidence += 0.3
        
        # 根据数据质量调整
        if experience.performance_metrics:
            base_confidence += 0.1
        
        if experience.actions_taken:
            base_confidence += 0.1
        
        # 根据insights数量调整
        if len(insights) >= 3:
            base_confidence += 0.1
        
        return min(1.0, base_confidence)
    
    def batch_reflect(self, experiences: List[Experience]) -> List[ReflectionResult]:
        """批量反思"""
        results = []
        
        for experience in experiences:
            # 根据经验类型选择反思类型
            if not experience.success:
                reflection_type = ReflectionType.FAILURE_ANALYSIS
            else:
                reflection_type = ReflectionType.SUCCESS_ANALYSIS
            
            result = self.reflect_on_experience(
                experience,
                reflection_type=reflection_type,
                depth=ReflectionDepth.DEEP
            )
            results.append(result)
        
        return results
    
    def get_reflection_history(self, limit: int = 100) -> List[ReflectionResult]:
        """获取反思历史"""
        return self.reflection_history[-limit:] if self.reflection_history else []
    
    def get_patterns(self) -> List[Dict[str, Any]]:
        """获取识别到的模式"""
        if len(self.experience_store) >= 5:
            return self.pattern_recognizer.analyze_experiences(self.experience_store)
        return []
    
    def clear_history(self) -> None:
        """清空历史"""
        self.reflection_history.clear()
        self.experience_store.clear()
        logger.info("反思历史已清空")


class ReflectionService:
    """反思服务"""
    
    def __init__(self):
        self.reflection_engine = ReflectionEngine()
        self.active_reflections = {}
        
        logger.info("反思服务初始化完成")
    
    async def reflect_on_experience(
        self,
        experience_data: Dict[str, Any],
        reflection_type: str = "failure_analysis",
        depth: str = "deep"
    ) -> Dict[str, Any]:
        """对经验进行反思"""
        try:
            # 创建经验对象
            import uuid
            experience_id = str(uuid.uuid4())
            
            experience = Experience(
                experience_id=experience_id,
                task_type=experience_data.get("task_type", "unknown"),
                task_description=experience_data.get("task_description", ""),
                input_data=experience_data.get("input_data", {}),
                actions_taken=experience_data.get("actions_taken", []),
                outcome=experience_data.get("outcome", {}),
                success=experience_data.get("success", False),
                performance_metrics=experience_data.get("performance_metrics", {}),
                metadata=experience_data.get("metadata", {})
            )
            
            # 添加到引擎
            self.reflection_engine.add_experience(experience)
            
            # 执行反思
            reflection_type_enum = ReflectionType(reflection_type)
            depth_enum = ReflectionDepth(depth)
            
            result = self.reflection_engine.reflect_on_experience(
                experience,
                reflection_type=reflection_type_enum,
                depth=depth_enum
            )
            
            return {
                "success": True,
                "reflection_result": result.to_dict(),
                "experience_id": experience_id
            }
            
        except Exception as e:
            logger.error(f"反思失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def batch_reflect(self, experiences_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量反思"""
        try:
            # 创建经验对象列表
            experiences = []
            for exp_data in experiences_data:
                import uuid
                experience_id = str(uuid.uuid4())
                
                experience = Experience(
                    experience_id=experience_id,
                    task_type=exp_data.get("task_type", "unknown"),
                    task_description=exp_data.get("task_description", ""),
                    input_data=exp_data.get("input_data", {}),
                    actions_taken=exp_data.get("actions_taken", []),
                    outcome=exp_data.get("outcome", {}),
                    success=exp_data.get("success", False),
                    performance_metrics=exp_data.get("performance_metrics", {}),
                    metadata=exp_data.get("metadata", {})
                )
                
                experiences.append(experience)
                self.reflection_engine.add_experience(experience)
            
            # 批量反思
            results = self.reflection_engine.batch_reflect(experiences)
            
            return {
                "success": True,
                "reflection_results": [r.to_dict() for r in results],
                "total_experiences": len(experiences)
            }
            
        except Exception as e:
            logger.error(f"批量反思失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_insights(self, task_type: str = None, limit: int = 10) -> Dict[str, Any]:
        """获取洞察"""
        try:
            patterns = self.reflection_engine.get_patterns()
            
            # 按任务类型过滤
            if task_type:
                filtered_patterns = [
                    p for p in patterns 
                    if task_type.lower() in json.dumps(p).lower()
                ]
            else:
                filtered_patterns = patterns
            
            # 获取反思历史
            history = self.reflection_engine.get_reflection_history(limit)
            
            return {
                "success": True,
                "patterns": filtered_patterns[:limit],
                "recent_reflections": [r.to_dict() for r in history],
                "total_patterns": len(filtered_patterns)
            }
            
        except Exception as e:
            logger.error(f"获取洞察失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "success": True,
            "stats": {
                "total_experiences": len(self.reflection_engine.experience_store),
                "total_reflections": len(self.reflection_engine.reflection_history),
                "active_reflections": len(self.active_reflections)
            }
        }


# 全局反思服务实例
reflection_service = ReflectionService()
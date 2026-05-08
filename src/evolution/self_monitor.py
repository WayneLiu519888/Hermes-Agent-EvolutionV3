
"""
自我监控器 - 协调学习能力进化系统的各个组件
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SelfMonitor:
    """自我监控器"""
    
    def __init__(self, observer, analyzer, strategy_learner):
        """
        初始化自我监控器
        
        Args:
            observer: LearningObserver实例
            analyzer: ExperienceAnalyzer实例
            strategy_learner: ToolStrategyLearner实例
        """
        self.observer = observer
        self.analyzer = analyzer
        self.strategy_learner = strategy_learner
        self.monitoring_history = []
        
    def monitor_and_improve(self) -> Dict[str, Any]:
        """
        监控当前状态并生成改进计划
        
        Returns:
            Dict[str, Any]: 监控和改进结果
        """
        logger.info("开始自我监控和改进分析")
        
        # 1. 分析当前经验
        analysis = self.analyzer.analyze_recent_experiences(days=7)
        
        # 2. 分析工具使用策略
        tool_summary = self.strategy_learner.get_tool_performance_summary()
        strategy_perf = self.strategy_learner.get_strategy_performance()
        
        # 3. 生成改进计划
        improvement_plan = self._generate_improvement_plan(analysis, tool_summary, strategy_perf)
        
        # 4. 记录监控历史
        monitor_record = {
            'timestamp': datetime.now().isoformat(),
            'analysis_summary': analysis.summary,
            'tool_count': len(tool_summary),
            'current_strategy': self.strategy_learner.get_current_strategy().value,
            'improvement_plan': improvement_plan
        }
        
        self.monitoring_history.append(monitor_record)
        
        # 5. 返回结果
        result = {
            'timestamp': datetime.now().isoformat(),
            'analysis': {
                'total_experiences': analysis.total_experiences,
                'success_rate': analysis.success_rate,
                'pattern_count': len(analysis.identified_patterns),
                'key_insights': analysis.key_insights
            },
            'strategy_update': {
                'current': self.strategy_learner.get_current_strategy().value,
                'performance': {
                    strategy.value: {
                        'success_rate': perf.success_rate,
                        'efficiency': perf.avg_efficiency,
                        'usage_count': perf.usage_count
                    }
                    for strategy, perf in strategy_perf.items()
                    if perf.usage_count > 0
                }
            },
            'improvements': improvement_plan,
            'summary': f"监控完成: {analysis.total_experiences}条经验，成功率{analysis.success_rate:.1%}"
        }
        
        logger.info(f"自我监控完成: {result['summary']}")
        return result
    
    def _generate_improvement_plan(self, analysis, tool_summary, strategy_perf) -> List[Dict[str, Any]]:
        """生成改进计划"""
        improvements = []
        
        # 基于成功率改进
        if analysis.success_rate < 0.6:
            improvements.append({
                'type': 'improve_success_rate',
                'priority': 'high',
                'description': f'成功率较低 ({analysis.success_rate:.1%})，需要改进执行策略',
                'actions': [
                    '分析失败原因',
                    '优化工具选择策略',
                    '增加错误处理'
                ]
            })
        
        # 基于工具性能改进
        low_performance_tools = [
            (tool, stats) for tool, stats in tool_summary.items()
            if stats.get('success_rate', 0) < 0.5 and stats.get('usage_count', 0) >= 3
        ]
        
        for tool, stats in low_performance_tools[:3]:  # 最多3个工具
            improvements.append({
                'type': 'improve_tool_performance',
                'priority': 'medium',
                'description': f'工具"{tool}"性能较低 (成功率{stats.get("success_rate", 0):.1%})',
                'actions': [
                    f'分析{tool}使用模式',
                    f'优化{tool}参数配置',
                    f'考虑替代工具'
                ]
            })
        
        # 基于策略性能改进
        current_strategy = self.strategy_learner.get_current_strategy()
        current_perf = strategy_perf.get(current_strategy)
        
        if current_perf and current_perf.success_rate < 0.5:
            # 寻找更好的策略
            better_strategies = [
                (strategy, perf) for strategy, perf in strategy_perf.items()
                if strategy != current_strategy and perf.success_rate > current_perf.success_rate + 0.1
            ]
            
            if better_strategies:
                best_strategy, best_perf = max(better_strategies, key=lambda x: x[1].success_rate)
                improvements.append({
                    'type': 'update_strategy',
                    'priority': 'medium',
                    'description': f'考虑切换到{best_strategy.value}策略 (成功率{best_perf.success_rate:.1%} vs 当前{current_perf.success_rate:.1%})',
                    'actions': [
                        f'评估{best_strategy.value}策略适用性',
                        f'逐步切换到新策略',
                        f'监控新策略效果'
                    ]
                })
        
        # 如果没有具体改进点，添加通用改进建议
        if not improvements:
            improvements.append({
                'type': 'general_improvement',
                'priority': 'low',
                'description': '系统运行正常，继续积累经验数据',
                'actions': [
                    '继续记录经验数据',
                    '定期进行自我监控',
                    '探索新的工具使用模式'
                ]
            })
        
        return improvements
    
    def _count_tools_from_db(self) -> int:
        """从 tools.db 统计已注册工具数量（重启后策略学习器内存为空时的回退）"""
        try:
            import sqlite3, os
            db_path = os.path.join(os.path.expanduser("~/.hermes"), "data", "evolution", "tools.db")
            if not os.path.exists(db_path):
                return 0
            conn = sqlite3.connect(db_path)
            count = conn.execute("SELECT COUNT(*) FROM tools").fetchone()[0]
            conn.close()
            return count
        except Exception:
            return 0

    def get_monitoring_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取监控历史"""
        return self.monitoring_history[-limit:] if self.monitoring_history else []
    
    def get_system_health_report(self) -> Dict[str, Any]:
        """获取系统健康报告"""
        analysis = self.analyzer.analyze_recent_experiences(days=7)
        tool_summary = self.strategy_learner.get_tool_performance_summary()
        
        # 计算健康分数 (0-100)
        success_score = min(100, analysis.success_rate * 100)
        experience_score = min(100, analysis.total_experiences * 2)  # 每50条经验得100分
        # Fallback: if strategy_learner is empty (just restarted), count tools from db
        tool_count = len(tool_summary)
        if tool_count == 0:
            tool_count = self._count_tools_from_db()
        tool_diversity_score = min(100, tool_count * 20)  # 每5个工具得100分
        
        health_score = int((success_score * 0.5 + experience_score * 0.3 + tool_diversity_score * 0.2))
        
        return {
            'timestamp': datetime.now().isoformat(),
            'health_score': health_score,
            'metrics': {
                'success_rate': analysis.success_rate,
                'total_experiences': analysis.total_experiences,
                'monitored_tools': tool_count,
                'current_strategy': self.strategy_learner.get_current_strategy().value
            },
            'status': 'healthy' if health_score >= 70 else 'needs_attention' if health_score >= 50 else 'unhealthy',
            'recommendations': [
                f'健康分数: {health_score}/100',
                f'成功率: {analysis.success_rate:.1%}',
                f'监控工具数: {tool_count}'
            ]
        }

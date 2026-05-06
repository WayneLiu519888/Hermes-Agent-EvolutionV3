"""
工具性能分析模块
负责分析工具的使用性能、效率和效果，为工具优化提供数据支持
"""

import logging
import time
import statistics
import os
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from ..db_utils import get_evolution_db
from enum import Enum

from .tool_registry import ToolDefinition, ToolRegistry, ToolStatus

log = logging.getLogger("hermes_evo.tools")


class PerformanceMetric(Enum):
    """性能指标枚举"""
    EXECUTION_TIME = "execution_time"  # 执行时间
    SUCCESS_RATE = "success_rate"  # 成功率
    ERROR_RATE = "error_rate"  # 错误率
    MEMORY_USAGE = "memory_usage"  # 内存使用
    CPU_USAGE = "cpu_usage"  # CPU使用
    RESPONSE_TIME = "response_time"  # 响应时间
    THROUGHPUT = "throughput"  # 吞吐量


class PerformanceLevel(Enum):
    """性能等级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    FAIR = "fair"  # 一般
    POOR = "poor"  # 较差
    CRITICAL = "critical"  # 严重


@dataclass
class PerformanceRecord:
    """性能记录"""
    tool_name: str
    metric: PerformanceMetric
    value: float
    timestamp: datetime
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PerformanceAnalysis:
    """性能分析结果"""
    tool_name: str
    metric: PerformanceMetric
    average_value: float
    min_value: float
    max_value: float
    std_dev: float
    sample_count: int
    performance_level: PerformanceLevel
    trend: str  # "improving", "stable", "declining"
    recommendations: List[str] = field(default_factory=list)
    issues: List[str] = field(default_factory=list)
    last_updated: datetime = field(default_factory=datetime.now)


@dataclass
class ToolPerformanceSummary:
    """工具性能摘要"""
    tool_name: str
    tool_status: ToolStatus
    overall_score: float  # 0-100
    performance_level: PerformanceLevel
    metrics_summary: Dict[PerformanceMetric, PerformanceAnalysis]
    key_insights: List[str]
    optimization_opportunities: List[str]
    last_analysis: datetime


class ToolPerformanceAnalyzer:
    """工具性能分析器"""
    
    def __init__(self, registry: ToolRegistry, db_path: str = "tool_performance.db"):
        """
        初始化工具性能分析器
        
        Args:
            registry: 工具注册表实例
            db_path: 性能数据库路径
        """
        self.registry = registry
        self.db_path = db_path
        self._init_database()
        
    def _init_database(self):
        """初始化数据库"""
        import sqlite3
        
        conn = get_evolution_db(self.db_path)
        cursor = conn.cursor()
        
        # 创建性能记录表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tool_name TEXT NOT NULL,
                metric TEXT NOT NULL,
                value REAL NOT NULL,
                timestamp DATETIME NOT NULL,
                metadata TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tool_metric ON performance_records(tool_name, metric)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON performance_records(timestamp)')
        
        conn.commit()
        conn.close()
    
    def record_performance(self, tool_name: str, 
                          metric: PerformanceMetric, 
                          value: float,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        记录性能数据
        
        Args:
            tool_name: 工具名称
            metric: 性能指标
            value: 指标值
            metadata: 元数据
            
        Returns:
            bool: 记录是否成功
        """
        try:
            import sqlite3
            import json
            
            conn = get_evolution_db(self.db_path)
            cursor = conn.cursor()
            
            metadata_json = json.dumps(metadata) if metadata else "{}"
            
            cursor.execute('''
                INSERT INTO performance_records (tool_name, metric, value, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?)
            ''', (tool_name, metric.value, value, datetime.now(), metadata_json))
            
            conn.commit()
            conn.close()
            
            # 更新工具注册表中的统计信息
            self._update_tool_statistics(tool_name, metric, value)
            
            return True
            
        except Exception as e:
            log.error("Failed to record performance: %s", e)
            return False
    
    def analyze_tool_performance(self, tool_name: str, 
                                time_period: Optional[timedelta] = None) -> ToolPerformanceSummary:
        """
        分析工具性能
        
        Args:
            tool_name: 工具名称
            time_period: 时间周期（如果为None则分析所有数据）
            
        Returns:
            ToolPerformanceSummary: 性能摘要
        """
        try:
            # 获取工具信息
            tool_def = self.registry.get(tool_name)
            if not tool_def:
                raise ValueError(f"Tool not found: {tool_name}")
            
            # 获取性能记录
            records = self._get_performance_records(tool_name, time_period)
            
            # 分析各个指标
            metrics_summary = {}
            for metric in PerformanceMetric:
                metric_records = [r for r in records if r.metric == metric]
                if metric_records:
                    analysis = self._analyze_metric(metric, metric_records)
                    metrics_summary[metric] = analysis
            
            # 计算总体得分
            overall_score = self._calculate_overall_score(metrics_summary)
            performance_level = self._determine_performance_level(overall_score)
            
            # 生成关键洞察
            key_insights = self._generate_key_insights(metrics_summary, tool_def)
            
            # 识别优化机会
            optimization_opportunities = self._identify_optimization_opportunities(metrics_summary, tool_def)
            
            return ToolPerformanceSummary(
                tool_name=tool_name,
                tool_status=tool_def.status,
                overall_score=overall_score,
                performance_level=performance_level,
                metrics_summary=metrics_summary,
                key_insights=key_insights,
                optimization_opportunities=optimization_opportunities,
                last_analysis=datetime.now()
            )
            
        except Exception as e:
            log.error("Failed to analyze tool performance: %s", e)
            # 返回默认摘要
            return ToolPerformanceSummary(
                tool_name=tool_name,
                tool_status=ToolStatus.ACTIVE,
                overall_score=0.0,
                performance_level=PerformanceLevel.CRITICAL,
                metrics_summary={},
                key_insights=[f"分析失败: {str(e)}"],
                optimization_opportunities=["修复性能分析系统"],
                last_analysis=datetime.now()
            )
    
    def analyze_all_tools(self) -> Dict[str, ToolPerformanceSummary]:
        """
        分析所有工具的性能
        
        Returns:
            Dict[str, ToolPerformanceSummary]: 所有工具的性能摘要
        """
        summaries = {}
        
        # 获取所有工具
        all_tools = self.registry.list_all()
        
        for tool in all_tools:
            try:
                summary = self.analyze_tool_performance(tool.name)
                summaries[tool.name] = summary
            except Exception as e:
                log.error("Failed to analyze tool %s: %s", tool.name, e)
        
        return summaries
    
    def get_performance_trends(self, tool_name: str, 
                              metric: PerformanceMetric,
                              time_period: timedelta = timedelta(days=7)) -> Dict[str, Any]:
        """
        获取性能趋势
        
        Args:
            tool_name: 工具名称
            metric: 性能指标
            time_period: 时间周期
            
        Returns:
            Dict[str, Any]: 趋势分析结果
        """
        try:
            # 获取时间序列数据
            records = self._get_performance_records(tool_name, time_period)
            metric_records = [r for r in records if r.metric == metric]
            
            if not metric_records:
                return {"has_data": False, "message": "No data available"}
            
            # 按时间排序
            metric_records.sort(key=lambda x: x.timestamp)
            
            # 提取时间序列
            timestamps = [r.timestamp for r in metric_records]
            values = [r.value for r in metric_records]
            
            # 计算趋势
            trend = self._calculate_trend(values)
            
            # 计算移动平均
            window_size = min(5, len(values))
            moving_average = self._calculate_moving_average(values, window_size)
            
            return {
                "has_data": True,
                "tool_name": tool_name,
                "metric": metric.value,
                "trend": trend,
                "data_points": len(values),
                "time_range": {
                    "start": timestamps[0].isoformat(),
                    "end": timestamps[-1].isoformat()
                },
                "current_value": values[-1],
                "average_value": statistics.mean(values),
                "min_value": min(values),
                "max_value": max(values),
                "moving_average": moving_average[-1] if moving_average else None,
                "recommendations": self._generate_trend_recommendations(trend, metric, values[-1])
            }
            
        except Exception as e:
            return {"has_data": False, "error": str(e)}
    
    def generate_performance_report(self, output_format: str = "text") -> str:
        """
        生成性能报告
        
        Args:
            output_format: 输出格式 ("text", "json", "html")
            
        Returns:
            str: 性能报告
        """
        # 分析所有工具
        summaries = self.analyze_all_tools()
        
        if output_format == "json":
            import json
            return json.dumps({
                "report_generated": datetime.now().isoformat(),
                "tools_analyzed": len(summaries),
                "summaries": {
                    name: {
                        "overall_score": summary.overall_score,
                        "performance_level": summary.performance_level.value,
                        "tool_status": summary.tool_status.value,
                        "key_insights": summary.key_insights,
                        "optimization_opportunities": summary.optimization_opportunities
                    }
                    for name, summary in summaries.items()
                }
            }, indent=2, ensure_ascii=False)
        
        elif output_format == "html":
            # 简化HTML报告
            html = f'''
            <!DOCTYPE html>
            <html>
            <head>
                <title>工具性能报告</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    .tool {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 10px; }}
                    .excellent {{ background-color: #d4edda; }}
                    .good {{ background-color: #d1ecf1; }}
                    .fair {{ background-color: #fff3cd; }}
                    .poor {{ background-color: #f8d7da; }}
                    .critical {{ background-color: #f5c6cb; }}
                </style>
            </head>
            <body>
                <h1>工具性能报告</h1>
                <p>生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
                <p>分析工具数量: {len(summaries)}</p>
            '''
            
            for name, summary in summaries.items():
                html += f'''
                <div class="tool {summary.performance_level.value}">
                    <h3>{name} ({summary.tool_status.value})</h3>
                    <p>总体得分: {summary.overall_score:.1f}/100 ({summary.performance_level.value})</p>
                    <h4>关键洞察:</h4>
                    <ul>
                '''
                
                for insight in summary.key_insights:
                    html += f'<li>{insight}</li>'
                
                html += '''
                    </ul>
                    <h4>优化建议:</h4>
                    <ul>
                '''
                
                for opp in summary.optimization_opportunities:
                    html += f'<li>{opp}</li>'
                
                html += '''
                    </ul>
                </div>
                '''
            
            html += '''
            </body>
            </html>
            '''
            
            return html
        
        else:  # text format
            report = f"工具性能报告\n"
            report += f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            report += f"分析工具数量: {len(summaries)}\n"
            report += "=" * 60 + "\n\n"
            
            for name, summary in summaries.items():
                report += f"工具: {name}\n"
                report += f"状态: {summary.tool_status.value}\n"
                report += f"性能得分: {summary.overall_score:.1f}/100 ({summary.performance_level.value})\n"
                report += f"关键洞察:\n"
                for insight in summary.key_insights:
                    report += f"  • {insight}\n"
                report += f"优化建议:\n"
                for opp in summary.optimization_opportunities:
                    report += f"  • {opp}\n"
                report += "-" * 40 + "\n"
            
            return report
    
    # ========== 私有方法 ==========
    
    def _get_performance_records(self, tool_name: str, 
                                time_period: Optional[timedelta]) -> List[PerformanceRecord]:
        """获取性能记录"""
        import sqlite3
        import json
        
        conn = get_evolution_db(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        if time_period:
            cutoff_time = datetime.now() - time_period
            cursor.execute('''
                SELECT tool_name, metric, value, timestamp, metadata
                FROM performance_records
                WHERE tool_name = ? AND timestamp >= ?
                ORDER BY timestamp
            ''', (tool_name, cutoff_time))
        else:
            cursor.execute('''
                SELECT tool_name, metric, value, timestamp, metadata
                FROM performance_records
                WHERE tool_name = ?
                ORDER BY timestamp
            ''', (tool_name,))
        
        records = []
        for row in cursor.fetchall():
            metadata = json.loads(row['metadata']) if row['metadata'] else {}
            record = PerformanceRecord(
                tool_name=row['tool_name'],
                metric=PerformanceMetric(row['metric']),
                value=row['value'],
                timestamp=datetime.fromisoformat(row['timestamp']),
                metadata=metadata
            )
            records.append(record)
        
        conn.close()
        return records
    
    def _analyze_metric(self, metric: PerformanceMetric, 
                       records: List[PerformanceRecord]) -> PerformanceAnalysis:
        """分析单个指标"""
        values = [r.value for r in records]
        
        # 计算统计量
        avg_value = statistics.mean(values) if values else 0
        min_value = min(values) if values else 0
        max_value = max(values) if values else 0
        std_dev = statistics.stdev(values) if len(values) > 1 else 0
        
        # 确定性能等级
        metric_level = self._evaluate_metric_level(metric, avg_value)
        
        # 计算趋势
        trend = self._calculate_trend(values)
        
        # 生成建议
        recommendations = self._generate_metric_recommendations(metric, avg_value, metric_level)
        
        # 识别问题
        issues = self._identify_metric_issues(metric, avg_value, std_dev, metric_level)
        
        return PerformanceAnalysis(
            tool_name=records[0].tool_name if records else "unknown",
            metric=metric,
            average_value=avg_value,
            min_value=min_value,
            max_value=max_value,
            std_dev=std_dev,
            sample_count=len(values),
            performance_level=metric_level,
            trend=trend,
            recommendations=recommendations,
            issues=issues
        )
    
    def _evaluate_metric_level(self, metric: PerformanceMetric, value: float) -> PerformanceLevel:
        """评估指标等级"""
        # 根据指标类型和值确定等级
        thresholds = {
            PerformanceMetric.EXECUTION_TIME: {
                "excellent": (0, 0.1),    # < 100ms
                "good": (0.1, 1.0),       # 100ms - 1s
                "fair": (1.0, 5.0),       # 1s - 5s
                "poor": (5.0, 10.0),      # 5s - 10s
                "critical": (10.0, float('inf'))  # > 10s
            },
            PerformanceMetric.SUCCESS_RATE: {
                "excellent": (0.95, 1.0),    # > 95%
                "good": (0.90, 0.95),       # 90% - 95%
                "fair": (0.80, 0.90),       # 80% - 90%
                "poor": (0.70, 0.80),       # 70% - 80%
                "critical": (0, 0.70)       # < 70%
            },
            PerformanceMetric.ERROR_RATE: {
                "excellent": (0, 0.05),      # < 5%
                "good": (0.05, 0.10),       # 5% - 10%
                "fair": (0.10, 0.20),       # 10% - 20%
                "poor": (0.20, 0.30),       # 20% - 30%
                "critical": (0.30, 1.0)     # > 30%
            }
        }
        
        # 默认阈值（对于其他指标）
        default_thresholds = thresholds.get(metric, thresholds[PerformanceMetric.SUCCESS_RATE])
        
        for level_name, (min_val, max_val) in default_thresholds.items():
            if min_val <= value < max_val:
                return PerformanceLevel(level_name)
        
        return PerformanceLevel.FAIR
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return "stable"
        
        # 使用线性回归判断趋势
        try:
            from sklearn.linear_model import LinearRegression
            import numpy as np
            
            X = np.array(range(len(values))).reshape(-1, 1)
            y = np.array(values)
            
            model = LinearRegression()
            model.fit(X, y)
            
            slope = model.coef_[0]
            
            if slope < -0.1:
                return "improving"  # 值在下降（对于执行时间等是好的）
            elif slope > 0.1:
                return "declining"  # 值在上升
            else:
                return "stable"
                
        except ImportError:
            # 简化版本：比较最后几个值的平均值
            if len(values) >= 5:
                first_half = statistics.mean(values[:len(values)//2])
                second_half = statistics.mean(values[len(values)//2:])
                
                # 对于执行时间，值越小越好
                # 对于成功率，值越大越好
                # 这里假设是执行时间类型的指标
                if second_half < first_half * 0.9:
                    return "improving"
                elif second_half > first_half * 1.1:
                    return "declining"
                else:
                    return "stable"
            else:
                return "stable"
    
    def _calculate_overall_score(self, metrics_summary: Dict[PerformanceMetric, PerformanceAnalysis]) -> float:
        """计算总体得分"""
        if not metrics_summary:
            return 50.0  # 默认得分
        
        # 为每个指标分配权重
        weights = {
            PerformanceMetric.SUCCESS_RATE: 0.4,
            PerformanceMetric.EXECUTION_TIME: 0.3,
            PerformanceMetric.ERROR_RATE: 0.2,
            PerformanceMetric.RESPONSE_TIME: 0.1
        }
        
        total_score = 0.0
        total_weight = 0.0
        
        for metric, analysis in metrics_summary.items():
            weight = weights.get(metric, 0.1)
            
            # 根据性能等级计算得分
            level_scores = {
                PerformanceLevel.EXCELLENT: 100,
                PerformanceLevel.GOOD: 80,
                PerformanceLevel.FAIR: 60,
                PerformanceLevel.POOR: 40,
                PerformanceLevel.CRITICAL: 20
            }
            
            score = level_scores.get(analysis.performance_level, 50)
            
            total_score += score * weight
            total_weight += weight
        
        return total_score / total_weight if total_weight > 0 else 50.0
    
    def _determine_performance_level(self, score: float) -> PerformanceLevel:
        """根据得分确定性能等级"""
        if score >= 90:
            return PerformanceLevel.EXCELLENT
        elif score >= 75:
            return PerformanceLevel.GOOD
        elif score >= 60:
            return PerformanceLevel.FAIR
        elif score >= 40:
            return PerformanceLevel.POOR
        else:
            return PerformanceLevel.CRITICAL
    
    def _generate_key_insights(self, metrics_summary: Dict[PerformanceMetric, PerformanceAnalysis], 
                              tool_def: ToolDefinition) -> List[str]:
        """生成关键洞察"""
        insights = []
        
        if not metrics_summary:
            insights.append("尚无性能数据")
            return insights
        
        # 检查成功率
        success_rate_analysis = metrics_summary.get(PerformanceMetric.SUCCESS_RATE)
        if success_rate_analysis:
            if success_rate_analysis.performance_level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                insights.append(f"成功率较低: {success_rate_analysis.average_value:.1%}")
            elif success_rate_analysis.trend == "declining":
                insights.append("成功率呈下降趋势")
        
        # 检查执行时间
        exec_time_analysis = metrics_summary.get(PerformanceMetric.EXECUTION_TIME)
        if exec_time_analysis:
            if exec_time_analysis.average_value > 5.0:  # 超过5秒
                insights.append(f"执行时间较长: {exec_time_analysis.average_value:.2f}秒")
            elif exec_time_analysis.trend == "improving":
                insights.append("执行时间正在改善")
        
        # 检查错误率
        error_rate_analysis = metrics_summary.get(PerformanceMetric.ERROR_RATE)
        if error_rate_analysis:
            if error_rate_analysis.average_value > 0.2:  # 超过20%
                insights.append(f"错误率较高: {error_rate_analysis.average_value:.1%}")
        
        # 检查工具使用频率
        if tool_def.usage_count > 100:
            insights.append("高频使用工具")
        elif tool_def.usage_count < 10:
            insights.append("低频使用工具")
        
        # 如果没有特别的问题，添加正面反馈
        if not insights and len(metrics_summary) > 0:
            insights.append("工具性能表现良好")
        
        return insights
    
    def _identify_optimization_opportunities(self, metrics_summary: Dict[PerformanceMetric, PerformanceAnalysis],
                                           tool_def: ToolDefinition) -> List[str]:
        """识别优化机会"""
        opportunities = []
        
        # 基于性能分析生成优化建议
        for metric, analysis in metrics_summary.items():
            if analysis.performance_level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                if metric == PerformanceMetric.EXECUTION_TIME:
                    opportunities.append(f"优化执行时间（当前: {analysis.average_value:.2f}秒）")
                elif metric == PerformanceMetric.SUCCESS_RATE:
                    opportunities.append(f"提高成功率（当前: {analysis.average_value:.1%}）")
                elif metric == PerformanceMetric.ERROR_RATE:
                    opportunities.append(f"降低错误率（当前: {analysis.average_value:.1%}）")
        
        # 基于工具状态
        if tool_def.status == ToolStatus.EXPERIMENTAL:
            opportunities.append("将实验性工具优化为稳定版本")
        elif tool_def.status == ToolStatus.DEPRECATED:
            opportunities.append("考虑替换已弃用的工具")
        
        # 基于使用模式
        if tool_def.error_count > tool_def.success_count * 0.1:  # 错误率超过10%
            opportunities.append("加强错误处理和测试")
        
        # 如果没有特别的问题，添加通用建议
        if not opportunities:
            opportunities.append("持续监控和优化")
        
        return opportunities
    
    def _update_tool_statistics(self, tool_name: str, metric: PerformanceMetric, value: float):
        """更新工具统计信息"""
        # 这里可以更新工具注册表中的统计信息
        # 例如：增加使用计数、更新成功率等
        pass
    
    def _calculate_moving_average(self, values: List[float], window_size: int) -> List[float]:
        """计算移动平均"""
        if len(values) < window_size:
            return []
        
        moving_avg = []
        for i in range(len(values) - window_size + 1):
            window = values[i:i + window_size]
            moving_avg.append(statistics.mean(window))
        
        return moving_avg
    
    def _generate_metric_recommendations(self, metric: PerformanceMetric, value: float, 
                                        level: PerformanceLevel) -> List[str]:
        """生成指标建议"""
        recommendations = []
        
        if metric == PerformanceMetric.EXECUTION_TIME:
            if level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                recommendations.append("优化算法复杂度")
                recommendations.append("添加缓存机制")
                recommendations.append("并行处理任务")
        
        elif metric == PerformanceMetric.SUCCESS_RATE:
            if level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                recommendations.append("加强输入验证")
                recommendations.append("改进错误处理")
                recommendations.append("增加重试机制")
        
        elif metric == PerformanceMetric.ERROR_RATE:
            if level in [PerformanceLevel.POOR, PerformanceLevel.CRITICAL]:
                recommendations.append("记录详细错误日志")
                recommendations.append("添加异常监控")
                recommendations.append("优化错误恢复流程")
        
        return recommendations
    
    def _identify_metric_issues(self, metric: PerformanceMetric, value: float, 
                               std_dev: float, level: PerformanceLevel) -> List[str]:
        """识别指标问题"""
        issues = []
        
        if level == PerformanceLevel.CRITICAL:
            issues.append(f"{metric.value} 严重异常")
        
        if std_dev > value * 0.5:  # 标准差超过均值的50%
            issues.append(f"{metric.value} 波动较大")
        
        return issues
    
    def _generate_trend_recommendations(self, trend: str, metric: PerformanceMetric, 
                                       current_value: float) -> List[str]:
        """生成趋势建议"""
        recommendations = []
        
        if trend == "declining":
            if metric == PerformanceMetric.EXECUTION_TIME:
                recommendations.append("执行时间在增加，需要优化")
            elif metric == PerformanceMetric.SUCCESS_RATE:
                recommendations.append("成功率在下降，需要调查原因")
        
        elif trend == "improving":
            recommendations.append("性能在改善，继续保持")
        
        return recommendations


# 性能监控装饰器
def monitor_performance(metric: PerformanceMetric = PerformanceMetric.EXECUTION_TIME):
    """
    性能监控装饰器
    
    Args:
        metric: 要监控的性能指标
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # 记录性能数据
                # 这里需要访问分析器实例，实际使用时需要调整
                log.info("[Performance] %s: %.3fs", func.__name__, execution_time)
                
                return result
                
            except Exception as e:
                execution_time = time.time() - start_time
                log.error("[Performance] %s failed: %.3fs, error: %s", func.__name__, execution_time, e)
                raise
        
        return wrapper
    return decorator
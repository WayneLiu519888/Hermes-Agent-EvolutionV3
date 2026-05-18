"""
V9.0.0 学习洞察注入器 — 将 ClosedLoopOrchestrator 的产出注入 LLM 上下文

从三个学习子系统读取近期洞察：
  - PatternRecognizer  → 高频错误模式、时间序列关联
  - ToolStrategyLearner → 工具推荐策略、参数调优建议
  - ExperienceAnalyzer  → 成功率趋势、瓶颈识别

集成点: pre_llm_call hook → inject_context() 之后 → inject_insights()
"""

import logging
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)


class InsightInjector:
    """从学习子系统提取洞察并格式化为LLM上下文片段"""

    def __init__(self):
        self._cache = {}
        self._cache_ttl = 300  # 5分钟内不重复查询

    def inject_insights(self, user_message: str) -> str:
        """主入口：根据用户消息返回应注入的洞察文本

        Returns:
            str: 格式化的洞察文本，如无需注入则返回 ""
        """
        insights: List[str] = []

        # 1. 活跃模式（高置信度、与用户消息相关）
        pattern_text = self._get_relevant_patterns(user_message)
        if pattern_text:
            insights.append(pattern_text)

        # 2. 工具策略建议（用户消息中提及的工具）
        strategy_text = self._get_tool_strategies(user_message)
        if strategy_text:
            insights.append(strategy_text)

        # 3. 趋势警告
        trend_text = self._get_trend_warnings()
        if trend_text:
            insights.append(trend_text)

        if not insights:
            return ""

        return "[系统洞察] " + " | ".join(insights)

    # ── 内部实现 ──

    def _get_relevant_patterns(self, user_message: str) -> str:
        """从 PatternRecognizer 获取与当前消息相关的高置信度模式"""
        try:
            from evolution.learning.pattern_recognizer import PatternRecognizer
            pr = PatternRecognizer()
            patterns = pr.get_active_patterns(min_confidence=0.7)

            relevant = []
            msg_lower = user_message.lower()
            for p in patterns[:10]:
                pattern_text = (
                    (p.get('description', '') or '') + ' ' +
                    (p.get('summary', '') or '')
                ).lower()
                keywords = [w for w in msg_lower.split() if len(w) > 2]
                if any(kw in pattern_text for kw in keywords[:5]):
                    relevant.append(p)

            if not relevant:
                return ""

            parts = []
            for p in relevant[:2]:
                name = p.get('pattern_name', p.get('type', '模式'))
                desc = (p.get('description', '') or '')[:60]
                parts.append(f"发现{name}: {desc}")
            return "; ".join(parts)
        except Exception as e:
            logger.debug("PatternRecognizer查询失败: %s", e)
            return ""

    def _get_tool_strategies(self, user_message: str) -> str:
        """从 ToolStrategyLearner 获取用户消息中提及的工具的策略建议"""
        try:
            from evolution.learning.tool_strategy_learner import ToolStrategyLearner
            from evolution.db_utils import get_data_dir
            tsl = ToolStrategyLearner(db_path=str(get_data_dir() / "tools.db"))

            tools_summary = tsl.get_tool_performance_summary()
            if not tools_summary:
                return ""

            mentioned = []
            for tool_name in tools_summary:
                short_name = tool_name.rsplit('_', 1)[-1] if '_' in tool_name else tool_name
                if (short_name.lower() in user_message.lower() or
                        tool_name.lower() in user_message.lower()):
                    mentioned.append((tool_name, tools_summary[tool_name]))

            if not mentioned:
                low_perf = [
                    (name, data) for name, data in tools_summary.items()
                    if data.get('success_rate', 1.0) < 0.5
                    and data.get('usage_count', 0) >= 1
                ]
                if low_perf:
                    name, data = low_perf[0]
                    return f"工具 {name} 近期成功率{data['success_rate']:.0%}，建议优先使用替代工具"
                return ""

            parts = []
            for tool_name, data in mentioned[:2]:
                parts.append(
                    f"{tool_name}: 成功率{data.get('success_rate', 0):.0%}, "
                    f"使用{data.get('usage_count', 0)}次"
                )
            return "工具状态: " + "; ".join(parts)
        except Exception as e:
            logger.debug("ToolStrategyLearner查询失败: %s", e)
            return ""

    def _get_trend_warnings(self) -> str:
        """从 ExperienceAnalyzer 获取近期趋势异常"""
        try:
            from evolution.learning.analyzer import ExperienceAnalyzer
            from evolution.learning.observer import LearningObserver
            from evolution.db_utils import get_data_dir

            observer = LearningObserver(
                db_path=str(get_data_dir() / "learning_experiences.db")
            )
            analyzer = ExperienceAnalyzer(observer)
            analysis = analyzer.analyze_recent_experiences(days=1)

            warnings = []
            if analysis.success_rate < 0.5 and analysis.total_experiences >= 1:
                warnings.append(f"近期成功率{analysis.success_rate:.0%}偏低")

            if analysis.key_insights:
                for insight in analysis.key_insights[:2]:
                    if any(kw in (insight or '').lower()
                           for kw in ['错误', '失败', '降低', '下降', '异常']):
                        warnings.append(insight[:80])

            if warnings:
                return "趋势: " + "; ".join(warnings)
            return ""
        except Exception as e:
            logger.debug("ExperienceAnalyzer查询失败: %s", e)
            return ""

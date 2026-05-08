"""
模式识别器单元测试 — PatternRecognizer, RecognizedPattern, GeneratedStrategy

测试维度:
1. Dataclass 创建: RecognizedPattern / GeneratedStrategy
2. PatternRecognizer 初始化及默认参数
3. recognize_patterns 空列表/正常流程
4. generate_strategies 从模式生成策略
5. get_pattern_summary / get_strategy_summary
6. validate_strategy 存在/不存在 + 反馈
7. 各子识别方法: temporal / sequential / contextual / performance / error
8. _generate_strategies_for_pattern 策略类型映射
"""

import os
import sys
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch

import pytest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from evolution.learning.pattern_recognizer import (
    PatternRecognizer,
    PatternCategory,
    StrategyType,
    RecognizedPattern,
    GeneratedStrategy,
    )
    from evolution.learning.experience import ExperienceType, Outcome
except ImportError:
    from src.evolution.learning.pattern_recognizer import (
    PatternRecognizer,
    PatternCategory,
    StrategyType,
    RecognizedPattern,
    GeneratedStrategy,
    )
    from src.evolution.learning.experience import ExperienceType, Outcome


# ══════════════════════════════════════════════════════════════════════
# Helpers
# ══════════════════════════════════════════════════════════════════════


def make_experience(exp_id, exp_type, outcome, timestamp, task_id=None,
                    actions=None, context=None, metrics=None):
    """创建 Mock Experience 对象"""
    exp = Mock()
    exp.id = exp_id
    exp.experience_type = exp_type       # ExperienceType 枚举，自带 .value
    exp.outcome = outcome                # Outcome 枚举
    exp.timestamp = timestamp            # datetime
    exp.task_id = task_id
    exp.actions = actions or []
    exp.context = context or {}
    exp.metrics = metrics or {}
    return exp


def _base_time():
    """基准时间"""
    return datetime(2026, 5, 6, 10, 0, 0)


# ══════════════════════════════════════════════════════════════════════
# Tests: Dataclass creation
# ══════════════════════════════════════════════════════════════════════


class TestDataclassCreation:
    """RecognizedPattern / GeneratedStrategy dataclass 创建"""

    def test_recognized_pattern_creation(self):
        """创建 RecognizedPattern 并校验字段"""
        now = datetime.now()
        rp = RecognizedPattern(
            pattern_id="pat_001",
            category=PatternCategory.ERROR_PATTERN,
            description="重复超时错误",
            confidence=0.85,
            support_count=5,
            conditions={"error_type": "超时错误"},
            examples=["exp_1", "exp_2"],
            implications=["添加超时重试"],
            discovered_at=now,
        )
        assert rp.pattern_id == "pat_001"
        assert rp.category == PatternCategory.ERROR_PATTERN
        assert rp.confidence == 0.85
        assert rp.support_count == 5
        assert rp.conditions["error_type"] == "超时错误"
        assert rp.examples == ["exp_1", "exp_2"]
        assert rp.discovered_at == now

    def test_recognized_pattern_default_discovered_at(self):
        """discovered_at 默认值为当前时间"""
        rp = RecognizedPattern(
            pattern_id="pat_002",
            category=PatternCategory.TEMPORAL_PATTERN,
            description="test",
            confidence=0.7,
            support_count=3,
            conditions={},
            examples=[],
            implications=[],
        )
        assert isinstance(rp.discovered_at, datetime)

    def test_generated_strategy_creation(self):
        """创建 GeneratedStrategy 并校验字段"""
        gs = GeneratedStrategy(
            strategy_id="strat_001",
            strategy_type=StrategyType.PREVENTIVE,
            target_pattern="pat_001",
            description="预防超时错误",
            actions=["重试", "超时检查"],
            expected_benefit=0.8,
            implementation_cost=0.3,
            priority="high",
        )
        assert gs.strategy_id == "strat_001"
        assert gs.strategy_type == StrategyType.PREVENTIVE
        assert gs.target_pattern == "pat_001"
        assert gs.expected_benefit == 0.8
        assert gs.validation_status == "pending"

    def test_generated_strategy_custom_validation_status(self):
        """自定义 validation_status"""
        gs = GeneratedStrategy(
            strategy_id="strat_002",
            strategy_type=StrategyType.OPTIMIZATION,
            target_pattern="pat_003",
            description="优化",
            actions=[],
            expected_benefit=0.5,
            implementation_cost=0.2,
            priority="medium",
            validation_status="validated",
        )
        assert gs.validation_status == "validated"


# ══════════════════════════════════════════════════════════════════════
# Tests: PatternRecognizer initialization
# ══════════════════════════════════════════════════════════════════════


class TestPatternRecognizerInit:
    """初始化测试"""

    def test_default_parameters(self):
        """默认参数: min_support=3, min_confidence=0.7"""
        pr = PatternRecognizer()
        assert pr.min_support == 3
        assert pr.min_confidence == 0.7
        assert pr.patterns == {}
        assert pr.strategies == {}

    def test_custom_parameters(self):
        """自定义参数"""
        pr = PatternRecognizer(min_support=5, min_confidence=0.85)
        assert pr.min_support == 5
        assert pr.min_confidence == 0.85


# ══════════════════════════════════════════════════════════════════════
# Tests: recognize_patterns
# ══════════════════════════════════════════════════════════════════════


class TestRecognizePatterns:
    """recognize_patterns 方法测试"""

    def test_empty_list_returns_empty(self):
        """空列表返回空"""
        pr = PatternRecognizer()
        result = pr.recognize_patterns([])
        assert result == []
        assert pr.patterns == {}

    def test_insufficient_data_returns_empty(self):
        """数据不足 min_support 时返回空（默认 min_support=3）"""
        pr = PatternRecognizer(min_support=3)
        # 2 条成功的经验，不足 3 条 — 时间模式/上下文模式等都需要 >= min_support
        t = _base_time()
        exps = [
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, task_id="t1", metrics={"efficiency": 0.9}),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=10), task_id="t1",
                            metrics={"efficiency": 0.9}),
        ]
        patterns = pr.recognize_patterns(exps)
        # 所有子方法都会因为 len < min_support 返回空
        assert patterns == []

    def test_normal_flow_with_errors(self):
        """足够数据 + 错误经验 -> 识别出错误模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = []
        # 3 条带 error 上下文的失败经验
        for i in range(3):
            exps.append(make_experience(
                f"e{i}", ExperienceType.TOOL_USAGE, Outcome.FAILURE,
                t + timedelta(seconds=i * 10),
                context={"error": "timeout occurred"},
            ))
        patterns = pr.recognize_patterns(exps)
        assert len(patterns) >= 1
        # 应包含错误模式
        error_patterns = [p for p in patterns if p.category == PatternCategory.ERROR_PATTERN]
        assert len(error_patterns) == 1
        assert error_patterns[0].conditions.get("error_type") == "超时错误"
        # 检查内部状态
        assert len(pr.patterns) >= 1

    def test_temporal_pattern_detected(self):
        """规律性时间间隔 → 检测到时间模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = []
        # 创建规律性间隔（每10秒一条，变异系数低）
        for i in range(5):
            exps.append(make_experience(
                f"e{i}", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                t + timedelta(seconds=i * 10),
            ))
        patterns = pr.recognize_patterns(exps)
        temporal = [p for p in patterns if p.category == PatternCategory.TEMPORAL_PATTERN
                     and "规律性" in p.description]
        assert len(temporal) >= 1

    def test_performance_pattern_detected(self):
        """性能指标 → 检测到性能模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = []
        for i in range(4):
            exps.append(make_experience(
                f"e{i}", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                t + timedelta(seconds=i),
                metrics={"efficiency": 0.85}  # > 0.8 → 高效模式
            ))
        patterns = pr.recognize_patterns(exps)
        perf = [p for p in patterns if p.category == PatternCategory.PERFORMANCE_PATTERN]
        assert len(perf) >= 1


# ══════════════════════════════════════════════════════════════════════
# Tests: generate_strategies
# ══════════════════════════════════════════════════════════════════════


class TestGenerateStrategies:
    """generate_strategies 方法测试"""

    def test_generate_from_patterns(self):
        """从模式生成策略"""
        pr = PatternRecognizer()
        patterns = [
            RecognizedPattern(
                pattern_id="p_err",
                category=PatternCategory.ERROR_PATTERN,
                description="错误: timeout",
                confidence=0.85,
                support_count=5,
                conditions={"error_type": "超时错误"},
                examples=["e1"],
                implications=["修复"],
            ),
            RecognizedPattern(
                pattern_id="p_seq",
                category=PatternCategory.SEQUENTIAL_PATTERN,
                description="序列: A→B→C",
                confidence=0.75,
                support_count=4,
                conditions={"action_sequence": ("A", "B", "C")},
                examples=["e2"],
                implications=["自动化"],
            ),
        ]
        strategies = pr.generate_strategies(patterns)
        # 每个模式产生 1 个专属策略 + 1 个通用策略 = 2 × 2 = 4
        assert len(strategies) == 4
        assert len(pr.strategies) == 4
        # 按优先级排序：high → medium → low
        priorities = [s.priority for s in strategies]
        assert priorities == sorted(priorities,
                                    key=lambda x: {"high": 0, "medium": 1, "low": 2}[x])

    def test_empty_patterns(self):
        """空模式列表返回空"""
        pr = PatternRecognizer()
        strategies = pr.generate_strategies([])
        assert strategies == []
        assert pr.strategies == {}


# ══════════════════════════════════════════════════════════════════════
# Tests: get_pattern_summary / get_strategy_summary
# ══════════════════════════════════════════════════════════════════════


class TestSummaries:
    """摘要方法测试"""

    def test_pattern_summary_empty(self):
        """无模式时摘要"""
        pr = PatternRecognizer()
        summary = pr.get_pattern_summary()
        assert summary["total_patterns"] == 0

    def test_pattern_summary_with_data(self):
        """有模式时摘要"""
        pr = PatternRecognizer()
        # 直接设置内部状态
        pr.patterns = {
            "p1": RecognizedPattern(
                pattern_id="p1", category=PatternCategory.ERROR_PATTERN,
                description="", confidence=0.9, support_count=5,
                conditions={}, examples=[], implications=[],
            ),
            "p2": RecognizedPattern(
                pattern_id="p2", category=PatternCategory.TEMPORAL_PATTERN,
                description="", confidence=0.75, support_count=4,
                conditions={}, examples=[], implications=[],
            ),
            "p3": RecognizedPattern(
                pattern_id="p3", category=PatternCategory.ERROR_PATTERN,
                description="", confidence=0.5, support_count=3,
                conditions={}, examples=[], implications=[],
            ),
        }
        summary = pr.get_pattern_summary()
        assert summary["total_patterns"] == 3
        assert summary["by_category"]["error_pattern"] == 2
        assert summary["by_category"]["temporal_pattern"] == 1
        assert summary["by_confidence"]["high"] == 1  # p1: 0.9 >= 0.8
        assert summary["by_confidence"]["medium"] == 1  # p2: 0.75 >= 0.6
        assert summary["by_confidence"]["low"] == 1  # p3: 0.5 < 0.6

    def test_strategy_summary_with_data(self):
        """有策略时摘要"""
        pr = PatternRecognizer()
        pr.strategies = {
            "s1": GeneratedStrategy(
                strategy_id="s1", strategy_type=StrategyType.PREVENTIVE,
                target_pattern="p1", description="", actions=[],
                expected_benefit=0.8, implementation_cost=0.3, priority="high",
            ),
            "s2": GeneratedStrategy(
                strategy_id="s2", strategy_type=StrategyType.OPTIMIZATION,
                target_pattern="p2", description="", actions=[],
                expected_benefit=0.4, implementation_cost=0.5, priority="medium",
                validation_status="validated",
            ),
            "s3": GeneratedStrategy(
                strategy_id="s3", strategy_type=StrategyType.PREVENTIVE,
                target_pattern="p3", description="", actions=[],
                expected_benefit=0.1, implementation_cost=0.1, priority="low",
                validation_status="rejected",
            ),
        }
        summary = pr.get_strategy_summary()
        assert summary["total_strategies"] == 3
        assert summary["by_type"]["preventive"] == 2
        assert summary["by_type"]["optimization"] == 1
        assert summary["by_priority"]["high"] == 1
        assert summary["by_priority"]["medium"] == 1
        assert summary["by_priority"]["low"] == 1
        assert summary["by_status"]["pending"] == 1
        assert summary["by_status"]["validated"] == 1
        assert summary["by_status"]["rejected"] == 1


# ══════════════════════════════════════════════════════════════════════
# Tests: validate_strategy
# ══════════════════════════════════════════════════════════════════════


class TestValidateStrategy:
    """validate_strategy 方法测试"""

    def test_validate_existing_strategy_success(self):
        """验证存在的策略 — 成功"""
        pr = PatternRecognizer()
        gs = GeneratedStrategy(
            strategy_id="s_ok",
            strategy_type=StrategyType.PREVENTIVE,
            target_pattern="p1", description="desc", actions=[],
            expected_benefit=0.8, implementation_cost=0.3, priority="high",
        )
        pr.strategies["s_ok"] = gs
        result = pr.validate_strategy("s_ok", success=True)
        assert result is True
        assert gs.validation_status == "validated"

    def test_validate_existing_strategy_failure(self):
        """验证存在的策略 — 失败"""
        pr = PatternRecognizer()
        gs = GeneratedStrategy(
            strategy_id="s_fail",
            strategy_type=StrategyType.OPTIMIZATION,
            target_pattern="p2", description="desc", actions=[],
            expected_benefit=0.5, implementation_cost=0.2, priority="medium",
        )
        pr.strategies["s_fail"] = gs
        result = pr.validate_strategy("s_fail", success=False)
        assert result is False
        assert gs.validation_status == "rejected"

    def test_validate_nonexistent_strategy(self):
        """验证不存在的策略 → 返回 False"""
        pr = PatternRecognizer()
        result = pr.validate_strategy("does_not_exist", success=True)
        assert result is False

    def test_validate_with_feedback(self):
        """验证时附带反馈信息 → 追加到 description"""
        pr = PatternRecognizer()
        gs = GeneratedStrategy(
            strategy_id="s_fb",
            strategy_type=StrategyType.RECOVERY,
            target_pattern="p3", description="恢复策略", actions=[],
            expected_benefit=0.6, implementation_cost=0.4, priority="medium",
        )
        pr.strategies["s_fb"] = gs
        pr.validate_strategy("s_fb", success=True, feedback="效果很好")
        assert "效果很好" in gs.description
        assert gs.validation_status == "validated"


# ══════════════════════════════════════════════════════════════════════
# Tests: sub-recognition methods
# ══════════════════════════════════════════════════════════════════════


class TestRecognizeTemporalPatterns:
    """_recognize_temporal_patterns 测试"""

    def test_regular_intervals_detected(self):
        """规律性间隔 → 检测到时间模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS, t),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=10)),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=20)),
            make_experience("e3", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=30)),
        ]
        patterns = pr._recognize_temporal_patterns(exps)
        assert len(patterns) >= 1
        # 第一个模式应该是规律性时间间隔
        regular = [p for p in patterns if "规律性" in p.description]
        assert len(regular) == 1

    def test_irregular_intervals_no_pattern(self):
        """不规则间隔（变异系数高）→ 无规律性模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS, t),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=5)),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=120)),
            make_experience("e3", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=180)),
        ]
        patterns = pr._recognize_temporal_patterns(exps)
        regular = [p for p in patterns if "规律性" in p.description]
        assert len(regular) == 0

    def test_hour_pattern_high_success(self):
        """某小时成功率 > 0.8 → 检测到时间段模式"""
        pr = PatternRecognizer(min_support=3)
        t = datetime(2026, 5, 6, 14, 0, 0)  # 14:00 起
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS, t),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(minutes=1)),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(minutes=2)),
        ]
        patterns = pr._recognize_temporal_patterns(exps)
        hour_patterns = [p for p in patterns if "时间段模式" in p.description]
        assert len(hour_patterns) >= 1
        assert "14时" in hour_patterns[0].description


class TestRecognizeErrorPatterns:
    """_recognize_error_patterns 测试"""

    def test_error_type_grouping(self):
        """错误类型分组"""
        pr = PatternRecognizer(min_support=2)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.FAILURE,
                            t, context={"error": "timeout"}),
            make_experience("e1", ExperienceType.REASONING, Outcome.FAILURE,
                            t, context={"error": "timeout"}),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.FAILURE,
                            t, context={"error": "permission denied"}),
        ]
        patterns = pr._recognize_error_patterns(exps)
        assert len(patterns) >= 1
        # timeout 出现 2 次 → 应被识别
        timeout = [p for p in patterns
                   if "超时错误" in p.description]
        assert len(timeout) == 1

    def test_error_type_from_experience_type(self):
        """从经验类型推断错误类型"""
        pr = PatternRecognizer(min_support=2)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.FAILURE,
                            t, context={}),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.FAILURE,
                            t, context={}),
        ]
        patterns = pr._recognize_error_patterns(exps)
        assert len(patterns) == 1
        assert patterns[0].conditions["error_type"] == "工具使用错误"

    def test_insufficient_failures(self):
        """失败经验不足 min_support → 无模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.FAILURE,
                            t, context={"error": "timeout"}),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t),
        ]
        patterns = pr._recognize_error_patterns(exps)
        assert patterns == []


class TestRecognizeContextualPatterns:
    """_recognize_contextual_patterns 测试"""

    def test_contextual_pattern_detected(self):
        """上下文分组 → 成功率极端时检测到模式"""
        pr = PatternRecognizer(min_support=3, min_confidence=0.7)
        t = _base_time()
        # 同一上下文，全部成功
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, context={"os": "linux", "lang": "python"}),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, context={"os": "linux", "lang": "python"}),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, context={"os": "linux", "lang": "python"}),
        ]
        patterns = pr._recognize_contextual_patterns(exps)
        assert len(patterns) >= 1
        assert patterns[0].category == PatternCategory.CONTEXTUAL_PATTERN


class TestRecognizePerformancePatterns:
    """_recognize_performance_patterns 测试"""

    def test_efficiency_pattern(self):
        """效率指标 → 性能模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, metrics={"efficiency": 0.85}),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, metrics={"efficiency": 0.88}),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, metrics={"efficiency": 0.91}),
        ]
        patterns = pr._recognize_performance_patterns(exps)
        assert len(patterns) >= 1
        assert patterns[0].category == PatternCategory.PERFORMANCE_PATTERN

    def test_execution_time_pattern(self):
        """执行时间指标 → 性能模式"""
        pr = PatternRecognizer(min_support=3)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, metrics={"execution_time": 8.0}),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, metrics={"execution_time": 9.0}),
            make_experience("e2", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, metrics={"execution_time": 7.5}),
        ]
        patterns = pr._recognize_performance_patterns(exps)
        assert len(patterns) >= 1
        # 应有 "执行时间模式" 描述
        time_patterns = [p for p in patterns if "执行时间模式" in p.description]
        assert len(time_patterns) == 1


class TestRecognizeSequentialPatterns:
    """_recognize_sequential_patterns 测试"""

    def test_repeated_action_sequence(self):
        """重复动作序列 → 序列模式"""
        pr = PatternRecognizer(min_support=2)
        t = _base_time()
        exps = [
            make_experience("e0", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t, task_id="task_a",
                            actions=[{"type": "read"}, {"type": "write"}]),
            make_experience("e1", ExperienceType.TOOL_USAGE, Outcome.SUCCESS,
                            t + timedelta(seconds=10), task_id="task_a",
                            actions=[{"type": "read"}, {"type": "write"}]),
        ]
        patterns = pr._recognize_sequential_patterns(exps)
        assert len(patterns) >= 1
        assert patterns[0].category == PatternCategory.SEQUENTIAL_PATTERN


# ══════════════════════════════════════════════════════════════════════
# Tests: _generate_strategies_for_pattern 策略类型映射
# ══════════════════════════════════════════════════════════════════════


class TestStrategyTypeMapping:
    """验证模式类别 → 策略类型的映射"""

    def test_error_to_preventive(self):
        """ERROR_PATTERN → PREVENTIVE + 通用 ADAPTIVE"""
        pr = PatternRecognizer()
        pattern = RecognizedPattern(
            pattern_id="p_err",
            category=PatternCategory.ERROR_PATTERN,
            description="超时错误",
            confidence=0.9, support_count=5,
            conditions={"error_type": "超时错误"},
            examples=[], implications=[],
        )
        strategies = pr._generate_strategies_for_pattern(pattern)
        types = {s.strategy_type for s in strategies}
        assert StrategyType.PREVENTIVE in types
        assert StrategyType.ADAPTIVE in types  # 通用策略

    def test_performance_to_optimization(self):
        """PERFORMANCE_PATTERN (低效) → OPTIMIZATION + 通用 ADAPTIVE"""
        pr = PatternRecognizer()
        pattern = RecognizedPattern(
            pattern_id="p_perf",
            category=PatternCategory.PERFORMANCE_PATTERN,
            description="效率低下",
            confidence=0.85, support_count=4,
            conditions={"avg_efficiency": 0.35},  # < 0.6 → 触发生成
            examples=[], implications=[],
        )
        strategies = pr._generate_strategies_for_pattern(pattern)
        types = {s.strategy_type for s in strategies}
        assert StrategyType.OPTIMIZATION in types
        assert StrategyType.ADAPTIVE in types

    def test_temporal_to_adaptive(self):
        """TEMPORAL_PATTERN (高成功率) → ADAPTIVE"""
        pr = PatternRecognizer()
        pattern = RecognizedPattern(
            pattern_id="p_temp",
            category=PatternCategory.TEMPORAL_PATTERN,
            description="14时高成功率",
            confidence=0.9, support_count=5,
            conditions={"hour": 14, "success_rate": 0.9},
            examples=[], implications=[],
        )
        strategies = pr._generate_strategies_for_pattern(pattern)
        types = {s.strategy_type for s in strategies}
        # 专属 ADAPTIVE + 通用 ADAPTIVE → 都是 ADAPTIVE
        adaptives = [s for s in strategies if s.strategy_type == StrategyType.ADAPTIVE]
        assert len(adaptives) >= 1

    def test_sequential_to_optimization(self):
        """SEQUENTIAL_PATTERN → OPTIMIZATION + 通用 ADAPTIVE"""
        pr = PatternRecognizer()
        pattern = RecognizedPattern(
            pattern_id="p_seq",
            category=PatternCategory.SEQUENTIAL_PATTERN,
            description="重复序列",
            confidence=0.8, support_count=3,
            conditions={"action_sequence": ("A", "B")},
            examples=[], implications=[],
        )
        strategies = pr._generate_strategies_for_pattern(pattern)
        types = {s.strategy_type for s in strategies}
        assert StrategyType.OPTIMIZATION in types
        assert StrategyType.ADAPTIVE in types

    def test_contextual_generic_only(self):
        """CONTEXTUAL_PATTERN → 仅通用 ADAPTIVE 策略"""
        pr = PatternRecognizer()
        pattern = RecognizedPattern(
            pattern_id="p_ctx",
            category=PatternCategory.CONTEXTUAL_PATTERN,
            description="特定上下文",
            confidence=0.75, support_count=4,
            conditions={"success_rate": 0.9},
            examples=[], implications=[],
        )
        strategies = pr._generate_strategies_for_pattern(pattern)
        # 只有通用策略（ADAPTIVE）
        assert len(strategies) == 1
        assert strategies[0].strategy_type == StrategyType.ADAPTIVE
        assert "generic" in strategies[0].strategy_id

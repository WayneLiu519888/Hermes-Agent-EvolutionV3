"""
进化系统集成测试框架
测试学习能力进化系统的各个组件如何协同工作
"""

import unittest
import tempfile
import os
import json
import sqlite3
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# 导入项目模块
import sys
sys.path.append('.')

try:
    from evolution.learning.observer import LearningObserver
    from evolution.learning.experience import Experience, ExperienceType, Outcome
    from evolution.learning.analyzer import ExperienceAnalyzer, AnalysisPatternType
    from evolution.learning.tool_strategy_learner import ToolStrategyLearner, ToolStrategyType
    from evolution.memory.database import AssociationDatabase
    from evolution.self_monitor import SelfMonitor
except ImportError:
    from src.evolution.learning.observer import LearningObserver
    from src.evolution.learning.experience import Experience, ExperienceType, Outcome
    from src.evolution.learning.analyzer import ExperienceAnalyzer, AnalysisPatternType
    from src.evolution.learning.tool_strategy_learner import ToolStrategyLearner, ToolStrategyType
    from src.evolution.memory.database import AssociationDatabase
    from src.evolution.self_monitor import SelfMonitor


class TestLearningEvolutionIntegration(unittest.TestCase):
    """学习能力进化集成测试"""

    def setUp(self):
        """测试前准备"""
        # 创建临时数据库
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, 'test_integration.db')

        # 初始化数据库
        self.db = AssociationDatabase(self.db_path)
        self.db.initialize()

        # 创建学习观察器
        self.observer = LearningObserver(db_path=self.db_path)

        # 创建经验分析器
        self.analyzer = ExperienceAnalyzer(self.observer)

        # 创建工具策略学习器
        self.strategy_learner = ToolStrategyLearner()

        # 创建自我监控器
        self.self_monitor = SelfMonitor(
            observer=self.observer,
            analyzer=self.analyzer,
            strategy_learner=self.strategy_learner
        )

        # 添加一些测试经验数据
        self._add_test_experiences()

    def tearDown(self):
        """测试后清理"""
        # 删除临时文件
        import shutil
        shutil.rmtree(self.temp_dir)

    def _add_test_experiences(self):
        """添加测试经验数据"""
        experiences = [
            Experience(
                id="exp_1",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id="task_1",
                description="成功使用terminal工具",
                outcome=Outcome.SUCCESS,
                metrics={"efficiency": 0.8, "execution_time": 2.5},
                context={"tool": "terminal", "complexity": 0.3}
            ),
            Experience(
                id="exp_2",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id="task_2",
                description="失败使用read_file工具",
                outcome=Outcome.FAILURE,
                metrics={"efficiency": 0.2, "execution_time": 5.0},
                context={"tool": "read_file", "error": "文件不存在", "complexity": 0.5}
            ),
            Experience(
                id="exp_3",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id="task_3",
                description="成功使用write_file工具",
                outcome=Outcome.SUCCESS,
                metrics={"efficiency": 0.9, "execution_time": 1.5},
                context={"tool": "write_file", "complexity": 0.4}
            ),
            Experience(
                id="exp_4",
                experience_type=ExperienceType.REASONING,
                task_id="task_4",
                description="成功推理任务",
                outcome=Outcome.SUCCESS,
                metrics={"accuracy": 0.95, "confidence": 0.8},
                context={"task_type": "reasoning", "complexity": 0.7}
            ),
            Experience(
                id="exp_5",
                experience_type=ExperienceType.PROBLEM_SOLVING,
                task_id="task_5",
                description="部分成功的问题解决",
                outcome=Outcome.PARTIAL_SUCCESS,
                metrics={"completeness": 0.6, "efficiency": 0.5},
                context={"task_type": "problem_solving", "complexity": 0.8}
            )
        ]

        # 保存到数据库
        for exp in experiences:
            self.observer.record_experience(exp)

    def test_observer_analyzer_integration(self):
        """测试观察器与分析器的集成"""
        # 观察器记录经验
        new_exp = Experience(
            id="exp_new",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id="task_new",
            description="新的工具使用经验",
            outcome=Outcome.SUCCESS,
            metrics={"efficiency": 0.85}
        )

        self.observer.record_experience(new_exp)

        # 分析器分析经验
        analysis = self.analyzer.analyze_recent_experiences(days=1)

        # 验证分析结果
        self.assertGreater(analysis.total_experiences, 0)
        self.assertIsInstance(analysis.success_rate, float)
        self.assertIsInstance(analysis.identified_patterns, list)
        self.assertIsInstance(analysis.key_insights, list)
        self.assertIsInstance(analysis.improvement_suggestions, list)

        print(f"分析结果: {analysis.total_experiences}条经验，成功率{analysis.success_rate:.1%}")

    def test_analyzer_strategy_learner_integration(self):
        """测试分析器与策略学习器的集成"""
        # 分析器分析经验
        analysis = self.analyzer.analyze_recent_experiences(days=1)

        # 策略学习器从分析结果中学习
        tool_experiences = []
        for exp in self.observer.get_recent_experiences(days=1):
            if exp.experience_type == ExperienceType.TOOL_USAGE:
                tool_experiences.append({
                    'tool_name': exp.context.get('tool', 'unknown'),
                    'success': exp.outcome == Outcome.SUCCESS,
                    'execution_time': exp.metrics.get('execution_time', 1.0),
                    'context': exp.context
                })

        self.strategy_learner.learn_from_experiences(tool_experiences)

        # 验证策略学习器状态
        tool_summary = self.strategy_learner.get_tool_performance_summary()
        self.assertGreater(len(tool_summary), 0)

        strategy_perf = self.strategy_learner.get_strategy_performance()
        self.assertGreater(len(strategy_perf), 0)

        print(f"工具性能摘要: {len(tool_summary)}个工具")
        print(f"策略性能: {len(strategy_perf)}个策略")

    def test_tool_recommendation_workflow(self):
        """测试工具推荐工作流"""
        # 记录一些工具使用经验
        tools = ['terminal', 'read_file', 'write_file', 'search_files']

        for i, tool in enumerate(tools):
            success = i % 3 != 0  # 模拟一些失败
            execution_time = 1.0 + i * 0.5
            self.strategy_learner.record_tool_usage(
                tool, success, execution_time, 
                {'complexity': 0.3 + i * 0.1}
            )

        # 获取工具推荐
        available_tools = ['terminal', 'read_file', 'write_file', 'new_tool']
        recommendations = self.strategy_learner.recommend_tool(
            "处理文件操作", available_tools, {'complexity': 0.4}
        )

        # 验证推荐结果
        self.assertGreater(len(recommendations), 0)
        self.assertEqual(len(recommendations), len(available_tools))

        # 推荐应该按置信度排序
        for i in range(len(recommendations) - 1):
            self.assertGreaterEqual(
                recommendations[i].confidence, 
                recommendations[i + 1].confidence
            )

        print(f"工具推荐: {[r.tool_name for r in recommendations]}")
        print(f"最高置信度: {recommendations[0].tool_name} ({recommendations[0].confidence:.2f})")

    def test_self_monitor_full_workflow(self):
        """测试自我监控器的完整工作流"""
        # 模拟一些经验记录
        for i in range(5):
            exp = Experience(
                id=f"monitor_exp_{i}",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id=f"monitor_task_{i}",
                description=f"监控测试经验{i}",
                outcome=Outcome.SUCCESS if i % 2 == 0 else Outcome.FAILURE,
                metrics={"efficiency": 0.5 + i * 0.1},
                context={"tool": f"tool_{i % 3}", "iteration": i}
            )
            self.observer.record_experience(exp)

        # 运行自我监控
        monitor_result = self.self_monitor.monitor_and_improve()

        # 验证监控结果
        self.assertIsNotNone(monitor_result)
        self.assertIn('analysis', monitor_result)
        self.assertIn('strategy_update', monitor_result)
        self.assertIn('improvements', monitor_result)

        print(f"自我监控结果: {monitor_result.get('summary', 'N/A')}")

    def test_learning_feedback_loop(self):
        """测试学习反馈循环"""
        # 初始状态
        initial_strategy = self.strategy_learner.get_current_strategy()
        print(f"初始策略: {initial_strategy.value}")

        # 模拟多个学习周期
        for cycle in range(3):
            print(f"\n学习周期 {cycle + 1}:")

            # 记录一些工具使用
            tools = ['terminal', 'read_file', 'write_file']
            for tool in tools:
                # 模拟学习效果：随着周期增加，成功率提高
                success_rate = 0.5 + cycle * 0.15
                success = (cycle * len(tools) + tools.index(tool)) % 10 < success_rate * 10
                execution_time = 1.0 + (cycle * 0.2)

                self.strategy_learner.record_tool_usage(
                    tool, success, execution_time,
                    {'cycle': cycle, 'tool_index': tools.index(tool)}
                )

            # 分析当前状态
            tool_summary = self.strategy_learner.get_tool_performance_summary()
            avg_success_rate = sum(
                perf['success_rate'] for perf in tool_summary.values()
            ) / len(tool_summary) if tool_summary else 0

            print(f"  平均成功率: {avg_success_rate:.1%}")
            print(f"  当前策略: {self.strategy_learner.get_current_strategy().value}")

        # 验证学习效果
        final_strategy = self.strategy_learner.get_current_strategy()
        tool_summary = self.strategy_learner.get_tool_performance_summary()

        self.assertGreater(len(tool_summary), 0)
        print(f"\n最终状态: 策略={final_strategy.value}, 监控工具数={len(tool_summary)}")

    def test_error_handling_integration(self):
        """测试错误处理集成"""
        # 测试数据库错误
        with patch.object(self.db, 'save_experience', side_effect=Exception("数据库错误")):
            exp = Experience(
                id="error_test",
                experience_type=ExperienceType.TOOL_USAGE,
                description="测试错误处理"
            )

            # 应该能够处理错误而不崩溃
            try:
                self.observer.record_experience(exp)
                error_handled = True
            except Exception:
                error_handled = False

            self.assertTrue(error_handled)

        # 测试分析器空数据
        with tempfile.TemporaryDirectory() as empty_dir:
            empty_db = os.path.join(empty_dir, 'empty.db')
            empty_observer = LearningObserver(db_path=empty_db)
            empty_analyzer = ExperienceAnalyzer(empty_observer)

            # 应该能够处理空数据库
            analysis = empty_analyzer.analyze_recent_experiences(days=1)
            self.assertEqual(analysis.total_experiences, 0)
            self.assertEqual(analysis.success_rate, 0.0)

            print("空数据处理测试通过")

    def test_performance_metrics_collection(self):
        """测试性能指标收集"""
        # 记录带性能指标的经验
        start_time = datetime.now()

        for i in range(3):
            exp = Experience(
                id=f"perf_exp_{i}",
                experience_type=ExperienceType.TOOL_USAGE,
                description=f"性能测试经验{i}",
                outcome=Outcome.SUCCESS,
                metrics={
                    'execution_time': 0.5 + i * 0.3,
                    'memory_usage': 100 + i * 50,
                    'cpu_usage': 20 + i * 10,
                    'efficiency': 0.7 - i * 0.1
                }
            )
            self.observer.record_experience(exp)

        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()

        # 分析性能数据
        analysis = self.analyzer.analyze_recent_experiences(days=1)

        # 验证性能指标
        self.assertGreater(analysis.total_experiences, 0)

        print(f"性能测试: 记录{analysis.total_experiences}条经验，耗时{duration:.2f}秒")

        # 检查是否有性能相关的洞察
        perf_insights = [insight for insight in analysis.key_insights 
                        if any(word in insight.lower() for word in ['效率', '性能', '时间'])]

        if perf_insights:
            print(f"性能洞察: {perf_insights[0]}")


class TestEvolutionSystemEndToEnd(unittest.TestCase):
    """进化系统端到端测试"""

    def test_complete_evolution_cycle(self):
        """测试完整的进化周期"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'e2e_test.db')

            # 1. 初始化系统
            observer = LearningObserver(db_path=db_path)
            analyzer = ExperienceAnalyzer(observer)
            strategy_learner = ToolStrategyLearner()

            print("1. 系统初始化完成")

            # 2. 模拟工作负载
            tasks = [
                {"type": "file_operation", "tools": ["read_file", "write_file"], "complexity": 0.3},
                {"type": "code_analysis", "tools": ["search_files", "patch"], "complexity": 0.6},
                {"type": "system_operation", "tools": ["terminal"], "complexity": 0.4},
            ]

            for i, task in enumerate(tasks):
                # 选择工具
                recommendations = strategy_learner.recommend_tool(
                    task["type"], task["tools"], {"complexity": task["complexity"]}
                )

                selected_tool = recommendations[0].tool_name

                # 模拟执行
                success = i % 4 != 0  # 75%成功率
                execution_time = 1.0 + task["complexity"] * 2.0

                # 记录经验
                exp = Experience(
                    id=f"e2e_exp_{i}",
                    experience_type=ExperienceType.TOOL_USAGE,
                    task_id=f"e2e_task_{i}",
                    description=f"{task['type']}任务使用{selected_tool}",
                    outcome=Outcome.SUCCESS if success else Outcome.FAILURE,
                    metrics={"execution_time": execution_time, "efficiency": 0.8 if success else 0.3},
                    context={"tool": selected_tool, "task_type": task["type"], "complexity": task["complexity"]}
                )

                observer.record_experience(exp)
                strategy_learner.record_tool_usage(selected_tool, success, execution_time, task)

                print(f"2.{i+1} 任务完成: {task['type']} -> {selected_tool}, 成功: {success}")

            # 3. 分析学习效果
            analysis = analyzer.analyze_recent_experiences(days=1)
            tool_summary = strategy_learner.get_tool_performance_summary()

            print(f"3. 分析完成: {analysis.total_experiences}条经验，{len(tool_summary)}个工具")
            print(f"   成功率: {analysis.success_rate:.1%}")
            print(f"   识别模式: {len(analysis.identified_patterns)}个")

            # 4. 验证系统状态
            self.assertGreater(analysis.total_experiences, 0)
            self.assertGreater(len(tool_summary), 0)
            self.assertIsInstance(strategy_learner.get_current_strategy(), ToolStrategyType)

            print("4. 系统状态验证通过")

            # 5. 生成改进报告
            if analysis.improvement_suggestions:
                print("5. 改进建议:")
                for i, suggestion in enumerate(analysis.improvement_suggestions[:3], 1):
                    print(f"   {i}. {suggestion}")

            print("✅ 完整进化周期测试通过")


if __name__ == '__main__':
    # 运行测试
    print("=" * 60)
    print("进化系统集成测试框架")
    print("=" * 60)

    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestLearningEvolutionIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionSystemEndToEnd))

    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 输出总结
    print("=" * 60)
    print(f"测试总结: {result.testsRun}个测试运行")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)

    if result.wasSuccessful():
        print("✅ 所有集成测试通过!")
    else:
        print("❌ 有测试失败或错误")
        sys.exit(1)

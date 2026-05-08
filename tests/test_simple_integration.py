"""
简化版集成测试 - 测试学习能力进化核心组件
"""

import unittest
import tempfile
import os
import sys

# 添加项目路径
sys.path.append('.')

try:
    from evolution.learning.observer import LearningObserver
    from evolution.learning.experience import Experience, ExperienceType, Outcome
    from evolution.learning.analyzer import ExperienceAnalyzer
    from evolution.learning.tool_strategy_learner import ToolStrategyLearner, ToolStrategyType
except ImportError:
    from src.evolution.learning.observer import LearningObserver
    from src.evolution.learning.experience import Experience, ExperienceType, Outcome
    from src.evolution.learning.analyzer import ExperienceAnalyzer
    from src.evolution.learning.tool_strategy_learner import ToolStrategyLearner, ToolStrategyType


class TestSimpleIntegration(unittest.TestCase):
    """简化集成测试"""
    
    def test_basic_workflow(self):
        """测试基本工作流"""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, 'test.db')
            
            # 1. 创建组件
            observer = LearningObserver(db_path=db_path)
            analyzer = ExperienceAnalyzer(observer)
            strategy_learner = ToolStrategyLearner()
            
            print("1. 组件创建完成")
            
            # 2. 记录一些经验
            experiences = [
                Experience(
                    id="test_1",
                    experience_type=ExperienceType.TOOL_USAGE,
                    task_id="task_1",
                    description="测试terminal工具",
                    outcome=Outcome.SUCCESS,
                    metrics={"efficiency": 0.8},
                    context={"tool": "terminal"}
                ),
                Experience(
                    id="test_2", 
                    experience_type=ExperienceType.TOOL_USAGE,
                    task_id="task_2",
                    description="测试read_file工具",
                    outcome=Outcome.FAILURE,
                    metrics={"efficiency": 0.3},
                    context={"tool": "read_file", "error": "文件不存在"}
                ),
                Experience(
                    id="test_3",
                    experience_type=ExperienceType.TOOL_USAGE,
                    task_id="task_3",
                    description="测试write_file工具",
                    outcome=Outcome.SUCCESS,
                    metrics={"efficiency": 0.9},
                    context={"tool": "write_file"}
                )
            ]
            
            for exp in experiences:
                observer.record_experience(exp)
                
                # 同时记录到策略学习器
                if exp.context.get('tool'):
                    success = exp.outcome == Outcome.SUCCESS
                    execution_time = exp.metrics.get('execution_time', 1.0)
                    strategy_learner.record_tool_usage(
                        exp.context['tool'], success, execution_time, exp.context
                    )
            
            print("2. 经验记录完成")
            
            # 3. 分析经验
            analysis = analyzer.analyze_recent_experiences(days=1)
            
            self.assertGreater(analysis.total_experiences, 0)
            self.assertIsInstance(analysis.success_rate, float)
            print(f"3. 分析完成: {analysis.total_experiences}条经验，成功率{analysis.success_rate:.1%}")
            
            # 4. 测试工具推荐
            recommendations = strategy_learner.recommend_tool(
                "文件操作", ["terminal", "read_file", "write_file", "new_tool"],
                {"complexity": 0.4}
            )
            
            self.assertEqual(len(recommendations), 4)
            self.assertTrue(all(r.confidence >= 0.1 for r in recommendations))
            print(f"4. 工具推荐完成: {[r.tool_name for r in recommendations]}")
            
            # 5. 验证系统状态
            tool_summary = strategy_learner.get_tool_performance_summary()
            self.assertGreater(len(tool_summary), 0)
            
            current_strategy = strategy_learner.get_current_strategy()
            self.assertIsInstance(current_strategy, ToolStrategyType)
            
            print(f"5. 系统状态验证: {len(tool_summary)}个工具，当前策略={current_strategy.value}")
            
            print("✅ 简化集成测试通过!")
    
    def test_learning_effectiveness(self):
        """测试学习效果"""
        strategy_learner = ToolStrategyLearner()
        
        # 模拟学习过程
        tools = ['tool_a', 'tool_b', 'tool_c']
        
        # 第一阶段：工具A表现好
        for i in range(5):
            strategy_learner.record_tool_usage('tool_a', True, 1.0, {'phase': 1})
            strategy_learner.record_tool_usage('tool_b', i < 3, 2.0, {'phase': 1})  # 60%成功率
            strategy_learner.record_tool_usage('tool_c', i < 2, 3.0, {'phase': 1})  # 40%成功率
        
        # 获取推荐
        rec1 = strategy_learner.recommend_tool("测试任务", tools, {})
        self.assertEqual(rec1[0].tool_name, 'tool_a')  # tool_a应该排名第一
        
        print(f"第一阶段推荐: {rec1[0].tool_name} (置信度={rec1[0].confidence:.2f})")
        
        # 第二阶段：工具B表现改善
        for i in range(5):
            strategy_learner.record_tool_usage('tool_a', i < 3, 1.0, {'phase': 2})  # 60%成功率
            strategy_learner.record_tool_usage('tool_b', True, 1.5, {'phase': 2})  # 100%成功率
            strategy_learner.record_tool_usage('tool_c', i < 2, 3.0, {'phase': 2})  # 40%成功率
        
        # 再次获取推荐
        rec2 = strategy_learner.recommend_tool("测试任务", tools, {})
        
        # tool_b应该排名上升（因为第二阶段表现好）
        tool_b_rank = [r.tool_name for r in rec2].index('tool_b')
        tool_b_confidence = rec2[tool_b_rank].confidence
        
        print(f"第二阶段推荐: {rec2[0].tool_name} (置信度={rec2[0].confidence:.2f})")
        print(f"工具B排名: {tool_b_rank+1}, 置信度: {tool_b_confidence:.2f}")
        
        # 验证学习效果
        self.assertLess(tool_b_rank, 2)  # tool_b应该在前2名
        self.assertGreater(tool_b_confidence, 0.5)
        
        print("✅ 学习效果测试通过!")


def run_simple_integration_tests():
    """运行简化集成测试"""
    print("=" * 60)
    print("简化集成测试框架")
    print("=" * 60)
    
    # 创建测试套件
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSimpleIntegration)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"测试总结: {result.testsRun}个测试运行")
    print(f"通过: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 60)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_simple_integration_tests()
    if success:
        print("✅ 所有简化集成测试通过!")
    else:
        print("❌ 有测试失败或错误")
        sys.exit(1)

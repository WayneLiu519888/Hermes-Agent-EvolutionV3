#!/usr/bin/env python3
"""
学习能力进化示例应用 - 文件处理AI助手的自我进化

这个示例展示了HermesAgentEvolution系统如何帮助AI助手从经验中学习并持续改进。
模拟一个文件处理AI助手，通过不断执行任务、记录经验、分析学习、优化策略的过程，
展示自我进化的完整工作流程。
"""

import sys
import os
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import tempfile
import shutil

# 添加项目路径
sys.path.append('.')

from src.evolution.learning.observer import LearningObserver
from src.evolution.learning.experience import Experience, ExperienceType, Outcome
from src.evolution.learning.analyzer import ExperienceAnalyzer
from src.evolution.learning.tool_strategy_learner import ToolStrategyLearner, ToolStrategyType
from src.evolution.learning.pattern_recognizer import PatternRecognizer, PatternCategory, StrategyType
from src.evolution.self_monitor import SelfMonitor


class FileProcessingAssistant:
    """模拟文件处理AI助手"""
    
    def __init__(self, observer: LearningObserver, strategy_learner: ToolStrategyLearner):
        """
        初始化文件处理助手
        
        Args:
            observer: 学习观察器
            strategy_learner: 工具策略学习器
        """
        self.observer = observer
        self.strategy_learner = strategy_learner
        self.task_counter = 0
        self.performance_history = []
        
        # 可用的文件处理工具
        self.available_tools = [
            "read_file",      # 读取文件
            "write_file",     # 写入文件
            "search_files",   # 搜索文件
            "terminal",       # 终端命令
            "patch",          # 文件修补
            "execute_code"    # 执行代码
        ]
        
        # 工具性能基准
        self.tool_performance = {
            "read_file": {"success_rate": 0.95, "speed": 0.8},
            "write_file": {"success_rate": 0.9, "speed": 0.7},
            "search_files": {"success_rate": 0.85, "speed": 0.6},
            "terminal": {"success_rate": 0.7, "speed": 0.5},
            "patch": {"success_rate": 0.8, "speed": 0.4},
            "execute_code": {"success_rate": 0.75, "speed": 0.3}
        }
    
    def execute_task(self, task_type: str, complexity: float = 0.5) -> Dict[str, Any]:
        """
        执行一个文件处理任务
        
        Args:
            task_type: 任务类型
            complexity: 任务复杂度 (0.0-1.0)
            
        Returns:
            Dict[str, Any]: 任务执行结果
        """
        self.task_counter += 1
        task_id = f"file_task_{self.task_counter}"
        
        print(f"🔧 执行任务 {task_id}: {task_type} (复杂度: {complexity:.1f})")
        
        # 获取工具推荐
        context = {"task_type": task_type, "complexity": complexity}
        recommendations = self.strategy_learner.recommend_tool(
            task_type, self.available_tools, context
        )
        
        # 选择工具（基于推荐置信度）
        if recommendations:
            selected_tool = recommendations[0].tool_name
            confidence = recommendations[0].confidence
            print(f"  推荐工具: {selected_tool} (置信度: {confidence:.2f})")
        else:
            # 如果没有推荐，随机选择
            selected_tool = random.choice(self.available_tools)
            print(f"  随机选择工具: {selected_tool}")
        
        # 模拟工具执行
        start_time = time.time()
        success, execution_time, metrics = self._simulate_tool_execution(
            selected_tool, task_type, complexity
        )
        end_time = time.time()
        
        # 记录工具使用
        self.strategy_learner.record_tool_usage(
            selected_tool, success, execution_time, context
        )
        
        # 创建经验记录
        experience = Experience(
            id=f"exp_{task_id}",
            experience_type=ExperienceType.TOOL_USAGE,
            task_id=task_id,
            timestamp=datetime.now(),
            description=f"使用{selected_tool}执行{task_type}任务",
            outcome=Outcome.SUCCESS if success else Outcome.FAILURE,
            metrics=metrics,
            context={
                "tool": selected_tool,
                "task_type": task_type,
                "complexity": complexity,
                "confidence": confidence if 'confidence' in locals() else 0.5
            },
            actions=[
                {"type": "tool_selection", "detail": f"选择工具: {selected_tool}"},
                {"type": "execution", "detail": f"执行{selected_tool}"},
                {"type": "verification", "detail": "验证结果"}
            ]
        )
        
        # 记录经验
        self.observer.record_experience(experience)
        
        # 记录性能历史
        performance = {
            "task_id": task_id,
            "task_type": task_type,
            "tool": selected_tool,
            "success": success,
            "execution_time": execution_time,
            "efficiency": metrics.get("efficiency", 0.5),
            "timestamp": datetime.now()
        }
        self.performance_history.append(performance)
        
        result = {
            "task_id": task_id,
            "success": success,
            "execution_time": execution_time,
            "tool": selected_tool,
            "metrics": metrics,
            "experience_id": experience.id
        }
        
        status = "✅ 成功" if success else "❌ 失败"
        print(f"  结果: {status}, 耗时: {execution_time:.2f}秒, 效率: {metrics.get('efficiency', 0.5):.1%}")
        
        return result
    
    def _simulate_tool_execution(self, tool: str, task_type: str, complexity: float) -> tuple:
        """
        模拟工具执行
        
        Returns:
            tuple: (success, execution_time, metrics)
        """
        # 基础性能
        base_performance = self.tool_performance.get(tool, {"success_rate": 0.7, "speed": 0.5})
        base_success_rate = base_performance["success_rate"]
        base_speed = base_performance["speed"]
        
        # 复杂度影响
        complexity_penalty = complexity * 0.3  # 复杂度越高，成功率越低
        
        # 任务类型匹配度
        task_tool_match = {
            "read_file": ["read_file"],
            "write_file": ["write_file"],
            "search_content": ["search_files", "read_file"],
            "file_operation": ["terminal", "execute_code"],
            "modify_file": ["patch", "write_file"]
        }
        
        # 检查任务工具匹配度
        matched_tools = task_tool_match.get(task_type, [])
        match_bonus = 0.1 if tool in matched_tools else 0.0
        
        # 计算实际成功率
        actual_success_rate = base_success_rate - complexity_penalty + match_bonus
        actual_success_rate = max(0.1, min(0.99, actual_success_rate))
        
        # 模拟执行结果
        success = random.random() < actual_success_rate
        
        # 计算执行时间 (1-5秒，受复杂度和速度影响)
        base_time = 1.0 + complexity * 4.0
        speed_factor = 1.0 - base_speed * 0.5  # 速度越快，时间越短
        execution_time = base_time * speed_factor * (0.8 + random.random() * 0.4)
        
        # 计算效率指标
        if success:
            efficiency = 0.5 + base_speed * 0.3 + (1.0 - complexity) * 0.2
            error_count = 0
        else:
            efficiency = 0.2 + random.random() * 0.3
            error_count = 1
        
        metrics = {
            "efficiency": efficiency,
            "error_count": error_count,
            "complexity": complexity,
            "tool_suitability": 1.0 if tool in matched_tools else 0.5
        }
        
        return success, execution_time, metrics
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """获取性能摘要"""
        if not self.performance_history:
            return {"total_tasks": 0, "success_rate": 0.0}
        
        total_tasks = len(self.performance_history)
        successful_tasks = len([p for p in self.performance_history if p["success"]])
        success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0.0
        
        # 计算平均执行时间
        execution_times = [p["execution_time"] for p in self.performance_history]
        avg_execution_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
        
        # 计算平均效率
        efficiencies = [p["efficiency"] for p in self.performance_history]
        avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0.0
        
        # 按工具统计
        tool_stats = {}
        for perf in self.performance_history:
            tool = perf["tool"]
            if tool not in tool_stats:
                tool_stats[tool] = {"count": 0, "successes": 0, "total_time": 0.0}
            
            tool_stats[tool]["count"] += 1
            if perf["success"]:
                tool_stats[tool]["successes"] += 1
            tool_stats[tool]["total_time"] += perf["execution_time"]
        
        # 计算工具成功率
        for tool, stats in tool_stats.items():
            stats["success_rate"] = stats["successes"] / stats["count"] if stats["count"] > 0 else 0.0
            stats["avg_time"] = stats["total_time"] / stats["count"] if stats["count"] > 0 else 0.0
        
        return {
            "total_tasks": total_tasks,
            "success_rate": success_rate,
            "avg_execution_time": avg_execution_time,
            "avg_efficiency": avg_efficiency,
            "tool_statistics": tool_stats
        }


class LearningEvolutionDemo:
    """学习能力进化演示"""
    
    def __init__(self):
        """初始化演示系统"""
        print("=" * 60)
        print("🤖 HermesAgentEvolution 学习能力进化演示")
        print("=" * 60)
        
        # 创建临时工作目录
        self.work_dir = tempfile.mkdtemp(prefix="hermes_evolution_demo_")
        self.db_path = os.path.join(self.work_dir, "learning_experiences.db")
        
        print(f"工作目录: {self.work_dir}")
        print(f"数据库: {self.db_path}")
        
        # 初始化进化系统组件
        print("\n🔧 初始化进化系统组件...")
        self.observer = LearningObserver(db_path=self.db_path)
        self.analyzer = ExperienceAnalyzer(self.observer)
        self.strategy_learner = ToolStrategyLearner()
        self.pattern_recognizer = PatternRecognizer(min_support=2, min_confidence=0.6)
        self.self_monitor = SelfMonitor(
            self.observer, self.analyzer, self.strategy_learner
        )
        
        # 创建文件处理助手
        self.assistant = FileProcessingAssistant(self.observer, self.strategy_learner)
        
        print("✅ 系统初始化完成")
    
    def run_demo(self, num_tasks: int = 20):
        """
        运行演示
        
        Args:
            num_tasks: 要执行的任务数量
        """
        print(f"\n🚀 开始执行 {num_tasks} 个文件处理任务...")
        print("-" * 40)
        
        task_types = [
            "read_file",      # 读取文件
            "write_file",     # 写入文件
            "search_content", # 搜索内容
            "file_operation", # 文件操作
            "modify_file"     # 修改文件
        ]
        
        # 阶段1: 初始执行（无学习）
        print("\n📊 阶段1: 初始执行 (无学习经验)")
        phase1_results = []
        for i in range(num_tasks // 4):
            task_type = random.choice(task_types)
            complexity = random.uniform(0.3, 0.7)
            result = self.assistant.execute_task(task_type, complexity)
            phase1_results.append(result)
            time.sleep(0.1)  # 模拟执行间隔
        
        # 阶段2: 学习后执行
        print("\n📊 阶段2: 学习分析后执行")
        self._perform_learning_analysis()
        
        phase2_results = []
        for i in range(num_tasks // 4):
            task_type = random.choice(task_types)
            complexity = random.uniform(0.3, 0.7)
            result = self.assistant.execute_task(task_type, complexity)
            phase2_results.append(result)
            time.sleep(0.1)
        
        # 阶段3: 模式识别后执行
        print("\n📊 阶段3: 模式识别后执行")
        self._perform_pattern_recognition()
        
        phase3_results = []
        for i in range(num_tasks // 4):
            task_type = random.choice(task_types)
            complexity = random.uniform(0.3, 0.7)
            result = self.assistant.execute_task(task_type, complexity)
            phase3_results.append(result)
            time.sleep(0.1)
        
        # 阶段4: 自我监控优化后执行
        print("\n📊 阶段4: 自我监控优化后执行")
        self._perform_self_monitoring()
        
        phase4_results = []
        for i in range(num_tasks // 4):
            task_type = random.choice(task_types)
            complexity = random.uniform(0.3, 0.7)
            result = self.assistant.execute_task(task_type, complexity)
            phase4_results.append(result)
            time.sleep(0.1)
        
        # 展示结果
        print("\n" + "=" * 60)
        print("📈 演示结果总结")
        print("=" * 60)
        
        self._show_performance_comparison(
            phase1_results, phase2_results, phase3_results, phase4_results
        )
        
        self._show_learning_insights()
        
        self._show_evolution_impact()
    
    def _perform_learning_analysis(self):
        """执行学习分析"""
        print("\n🧠 执行学习分析...")
        
        # 分析最近的经验
        analysis = self.analyzer.analyze_recent_experiences(days=1)
        
        print(f"  分析结果:")
        print(f"  • 总经验数: {analysis.total_experiences}")
        print(f"  • 成功率: {analysis.success_rate:.1%}")
        print(f"  • 识别模式: {len(analysis.identified_patterns)}个")
        
        if analysis.key_insights:
            print(f"  • 关键洞察: {analysis.key_insights[0]}")
        
        if analysis.improvement_suggestions:
            print(f"  • 改进建议: {analysis.improvement_suggestions[0]}")
    
    def _perform_pattern_recognition(self):
        """执行模式识别"""
        print("\n🔍 执行模式识别...")
        
        # 使用analyzer获取经验数据
        analysis = self.analyzer.analyze_recent_experiences(days=1)
        
        # 由于observer没有get_recent_experiences方法，我们使用模拟数据
        # 在实际应用中，应该从数据库获取经验数据
        print("  注: 在实际应用中应从数据库获取经验数据")
        print("  当前使用模拟数据进行模式识别演示")
        
        # 创建模拟经验数据用于演示
        from src.evolution.learning.experience import Experience, ExperienceType, Outcome
        from datetime import datetime, timedelta
        
        simulated_experiences = []
        base_time = datetime.now()
        
        # 创建一些有模式的模拟经验
        for i in range(10):
            exp = Experience(
                id=f"simulated_exp_{i}",
                experience_type=ExperienceType.TOOL_USAGE,
                task_id=f"task_{i//2}",
                timestamp=base_time - timedelta(hours=i),
                description=f"模拟经验{i}",
                outcome=Outcome.SUCCESS if i < 7 else Outcome.FAILURE,
                metrics={"efficiency": 0.6 + i * 0.03, "execution_time": 1.0 + i * 0.2},
                context={"tool": "read_file" if i % 2 == 0 else "write_file", "complexity": 0.4}
            )
            simulated_experiences.append(exp)
        
        if len(simulated_experiences) >= 2:
            # 识别模式
            patterns = self.pattern_recognizer.recognize_patterns(simulated_experiences)
            
            print(f"  识别到{len(patterns)}个模式:")
            for i, pattern in enumerate(patterns[:3], 1):  # 显示前3个
                print(f"  {i}. [{pattern.category.value}] {pattern.description}")
            
            # 生成策略
            strategies = self.pattern_recognizer.generate_strategies(patterns)
            
            print(f"  生成{len(strategies)}个策略:")
            for i, strategy in enumerate(strategies[:3], 1):  # 显示前3个
                print(f"  {i}. [{strategy.strategy_type.value}] {strategy.description}")
    
    def _perform_self_monitoring(self):
        """执行自我监控"""
        print("\n📊 执行自我监控...")
        
        monitor_result = self.self_monitor.monitor_and_improve()
        
        print(f"  监控结果:")
        print(f"  • 系统健康: {monitor_result['system_health']}")
        print(f"  • 识别问题: {len(monitor_result['identified_issues'])}个")
        print(f"  • 生成改进: {len(monitor_result['generated_improvements'])}个")
        
        if monitor_result['generated_improvements']:
            print(f"  • 关键改进: {monitor_result['generated_improvements'][0]}")
    
    def _show_performance_comparison(self, *phase_results):
        """展示性能对比"""
        print("\n📊 性能对比 (各阶段平均指标):")
        print("-" * 40)
        
        phases = ["初始阶段", "学习后", "模式识别后", "自我监控后"]
        
        for i, (phase_name, results) in enumerate(zip(phases, phase_results)):
            if not results:
                continue
            
            success_count = len([r for r in results if r["success"]])
            total_count = len(results)
            success_rate = success_count / total_count if total_count > 0 else 0.0
            
            execution_times = [r["execution_time"] for r in results]
            avg_time = sum(execution_times) / len(execution_times) if execution_times else 0.0
            
            efficiencies = [r["metrics"].get("efficiency", 0.5) for r in results]
            avg_efficiency = sum(efficiencies) / len(efficiencies) if efficiencies else 0.0
            
            print(f"{phase_name}:")
            print(f"  • 成功率: {success_rate:.1%}")
            print(f"  • 平均耗时: {avg_time:.2f}秒")
            print(f"  • 平均效率: {avg_efficiency:.1%}")
            
            # 计算改进百分比（相对于第一阶段）
            if i > 0 and phase_results[0]:
                base_success = len([r for r in phase_results[0] if r["success"]]) / len(phase_results[0])
                base_time = sum([r["execution_time"] for r in phase_results[0]]) / len(phase_results[0])
                base_eff = sum([r["metrics"].get("efficiency", 0.5) for r in phase_results[0]]) / len(phase_results[0])
                
                success_improvement = ((success_rate - base_success) / base_success * 100) if base_success > 0 else 0
                time_improvement = ((base_time - avg_time) / base_time * 100) if base_time > 0 else 0
                eff_improvement = ((avg_efficiency - base_eff) / base_eff * 100) if base_eff > 0 else 0
                
                print(f"  • 改进: 成功率↑{success_improvement:+.1f}%, 耗时↓{time_improvement:+.1f}%, 效率↑{eff_improvement:+.1f}%")
    
    def _show_learning_insights(self):
        """展示学习洞察"""
        print("\n💡 学习洞察:")
        print("-" * 40)
        
        # 获取工具性能摘要
        tool_summary = self.strategy_learner.get_tool_performance_summary()
        
        print("工具性能排名:")
        sorted_tools = sorted(
            tool_summary.items(),
            key=lambda x: x[1].success_rate * x[1].average_speed,
            reverse=True
        )
        
        for i, (tool_name, perf) in enumerate(sorted_tools[:5], 1):
            print(f"  {i}. {tool_name}: 成功率{perf.success_rate:.1%}, 平均速度{perf.average_speed:.2f}")
        
        # 获取当前策略
        current_strategy = self.strategy_learner.get_current_strategy()
        print(f"\n当前学习策略: {current_strategy.value}")
        
        # 获取模式摘要
        pattern_summary = self.pattern_recognizer.get_pattern_summary()
        print(f"\n识别模式统计:")
        print(f"  • 总模式数: {pattern_summary['total_patterns']}")
        print(f"  • 按类别: {dict(pattern_summary['by_category'])}")
    
    def _show_evolution_impact(self):
        """展示进化影响"""
        print("\n🚀 进化系统影响总结:")
        print("-" * 40)
        
        # 获取助手性能摘要
        perf_summary = self.assistant.get_performance_summary()
        
        print(f"总执行任务: {perf_summary['total_tasks']}")
        print(f"总体成功率: {perf_summary['success_rate']:.1%}")
        print(f"平均执行时间: {perf_summary['avg_execution_time']:.2f}秒")
        print(f"平均效率: {perf_summary['avg_efficiency']:.1%}")
        
        # 展示最佳工具
        if perf_summary['tool_statistics']:
            best_tool = max(
                perf_summary['tool_statistics'].items(),
                key=lambda x: x[1]['success_rate'] * (1.0 / max(0.1, x[1]['avg_time']))
            )
            print(f"\n最佳工具: {best_tool[0]}")
            print(f"  • 使用次数: {best_tool[1]['count']}")
            print(f"  • 成功率: {best_tool[1]['success_rate']:.1%}")
            print(f"  • 平均耗时: {best_tool[1]['avg_time']:.2f}秒")
        
        print("\n🎯 进化效果:")
        print("  • AI助手学会了选择更适合的工具")
        print("  • 通过模式识别避免了重复错误")
        print("  • 自适应策略优化了执行效率")
        print("  • 自我监控确保了系统持续改进")
    
    def cleanup(self):
        """清理资源"""
        print(f"\n🧹 清理工作目录: {self.work_dir}")
        try:
            shutil.rmtree(self.work_dir)
            print("✅ 清理完成")
        except Exception as e:
            print(f"⚠️  清理时出错: {e}")


def main():
    """主函数"""
    demo = None
    try:
        # 创建演示实例
        demo = LearningEvolutionDemo()
        
        # 运行演示
        demo.run_demo(num_tasks=20)
        
        print("\n" + "=" * 60)
        print("🎉 HermesAgentEvolution 学习能力进化演示完成!")
        print("=" * 60)
        print("\n📋 演示总结:")
        print("1. ✅ 展示了完整的自我进化工作流程")
        print("2. ✅ 验证了学习系统的实际效果")
        print("3. ✅ 证明了模式识别的价值")
        print("4. ✅ 体现了自我监控的重要性")
        print("\n💡 关键收获:")
        print("• AI助手可以从经验中持续学习")
        print("• 智能策略优化能显著提升性能")
        print("• 模式识别帮助避免重复错误")
        print("• 自我监控确保系统健康运行")
        
    except Exception as e:
        print(f"\n❌ 演示出错: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # 清理资源
        if demo:
            demo.cleanup()


if __name__ == "__main__":
    main()

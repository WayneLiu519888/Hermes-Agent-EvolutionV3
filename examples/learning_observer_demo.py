#!/usr/bin/env python3
"""
学习能力观察模块使用示例
"""

import sys
import os
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.learning.experience import Experience, ExperienceType, Outcome
from src.evolution.learning.observer import LearningObserver

def demonstrate_learning_observer():
    """演示学习观察器的使用"""
    print("🎯 学习能力观察模块演示")
    print("=" * 50)
    
    # 创建学习观察器
    observer = LearningObserver()
    print("✅ 学习观察器已创建")
    
    # 示例1: 记录工具使用经验
    print("\n📝 示例1: 记录工具使用经验")
    tool_exp = Experience(
        id="tool_usage_001",
        experience_type=ExperienceType.TOOL_USAGE,
        task_id="file_search_task",
        description="使用search_files工具查找Python文件",
        outcome=Outcome.SUCCESS,
        importance=0.8
    )
    
    # 添加详细记录
    tool_exp.add_action(
        tool_name="search_files",
        parameters={"pattern": "*.py", "path": "./src"},
        result=["file1.py", "file2.py", "file3.py"],
        duration=0.3
    )
    tool_exp.add_reasoning_step("需要查找项目中的所有Python文件")
    tool_exp.add_reasoning_step("使用search_files工具进行模式匹配")
    tool_exp.add_lesson_learned("使用*.py模式可以准确匹配Python文件")
    tool_exp.add_metric("files_found", 3)
    tool_exp.add_metric("duration_seconds", 0.3)
    tool_exp.add_tag("file_operation")
    tool_exp.add_tag("search")
    
    observer.record_experience(tool_exp)
    print(f"  记录经验: {tool_exp}")
    
    # 示例2: 记录问题解决经验
    print("\n📝 示例2: 记录问题解决经验")
    problem_exp = Experience(
        id="problem_solving_001",
        experience_type=ExperienceType.PROBLEM_SOLVING,
        task_id="test_failure_fix",
        description="修复测试失败问题",
        outcome=Outcome.PARTIAL_SUCCESS,
        importance=0.9
    )
    
    problem_exp.add_action(
        tool_name="read_file",
        parameters={"path": "tests/test_observer.py", "offset": 300},
        result="测试代码内容",
        duration=0.2
    )
    problem_exp.add_action(
        tool_name="patch",
        parameters={"mode": "replace", "path": "tests/test_observer.py"},
        result="修复成功",
        duration=0.5
    )
    problem_exp.add_reasoning_step("分析测试失败原因")
    problem_exp.add_reasoning_step("发现fixture名称错误")
    problem_exp.add_reasoning_step("使用patch工具修复代码")
    problem_exp.add_lesson_learned("测试fixture名称必须与实际定义一致")
    problem_exp.add_lesson_learned("使用patch工具可以精确修改代码")
    problem_exp.add_metric("issues_fixed", 1)
    problem_exp.add_metric("test_passed", 1)
    problem_exp.add_tag("testing")
    problem_exp.add_tag("debugging")
    problem_exp.add_tag("code_fix")
    
    observer.record_experience(problem_exp)
    print(f"  记录经验: {problem_exp}")
    
    # 示例3: 记录推理过程经验
    print("\n📝 示例3: 记录推理过程经验")
    reasoning_exp = Experience(
        id="reasoning_001",
        experience_type=ExperienceType.REASONING,
        task_id="architecture_design",
        description="设计系统架构的推理过程",
        outcome=Outcome.SUCCESS,
        importance=0.7
    )
    
    reasoning_exp.add_reasoning_step("分析系统需求：需要记录学习经验")
    reasoning_exp.add_reasoning_step("设计数据模型：Experience类")
    reasoning_exp.add_reasoning_step("设计存储层：SQLite数据库")
    reasoning_exp.add_reasoning_step("设计查询接口：LearningObserver类")
    reasoning_exp.add_reasoning_step("设计分析功能：统计和模式识别")
    reasoning_exp.add_lesson_learned("模块化设计便于扩展")
    reasoning_exp.add_lesson_learned("数据库索引提高查询性能")
    reasoning_exp.add_metric("design_completeness", 0.95)
    reasoning_exp.add_tag("architecture")
    reasoning_exp.add_tag("design")
    reasoning_exp.add_tag("planning")
    
    observer.record_experience(reasoning_exp)
    print(f"  记录经验: {reasoning_exp}")
    
    # 查询演示
    print("\n🔍 查询演示")
    print("-" * 30)
    
    # 查询所有经验
    all_experiences = observer.query_experiences(limit=5)
    print(f"📊 最近5条经验:")
    for exp in all_experiences:
        print(f"  • {exp.experience_type.value}: {exp.description[:50]}...")
    
    # 按类型查询
    tool_experiences = observer.query_experiences(
        experience_type=ExperienceType.TOOL_USAGE
    )
    print(f"\n🛠️  工具使用经验: {len(tool_experiences)} 条")
    
    # 按结果查询
    success_experiences = observer.query_experiences(
        outcome=Outcome.SUCCESS
    )
    print(f"✅ 成功经验: {len(success_experiences)} 条")
    
    # 统计信息
    print("\n📈 统计信息")
    print("-" * 30)
    stats = observer.get_statistics()
    print(f"总经验数: {stats.get('total_experiences', 0)}")
    print(f"按类型分布: {stats.get('by_type', {})}")
    print(f"按结果分布: {stats.get('by_outcome', {})}")
    print(f"平均置信度: {stats.get('avg_confidence', 0):.2f}")
    
    # 学习模式分析
    print("\n📊 学习模式分析 (最近7天)")
    print("-" * 30)
    analysis = observer.analyze_learning_patterns(window_days=7)
    
    if analysis["daily_success_rates"]:
        print("每日成功率:")
        for date, rate in analysis["daily_success_rates"].items():
            print(f"  {date}: {rate:.1%}")
    
    if analysis["tool_usage_frequency"]:
        print("\n工具使用频率:")
        for tool, count in analysis["tool_usage_frequency"].items():
            if tool:  # 跳过空值
                print(f"  {tool}: {count} 次")
    
    # 导出演示
    print("\n💾 导出演示")
    print("-" * 30)
    
    # 创建临时文件路径
    import tempfile
    json_file = tempfile.mktemp(suffix='_experiences.json')
    
    if observer.export_experiences(json_file, format="json"):
        print(f"✅ 经验已导出到: {json_file}")
        
        # 读取并显示部分内容
        import json
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            print(f"  导出记录数: {len(data)}")
            
            if data:
                first_exp = data[0]
                print(f"  第一条经验: {first_exp.get('description', '')[:50]}...")
    
    # 清理临时文件
    if os.path.exists(json_file):
        os.unlink(json_file)
    
    print("\n" + "=" * 50)
    print("🎉 学习能力观察模块演示完成!")
    print("✨ 功能总结:")
    print("  • 支持6种经验类型记录")
    print("  • 完整的工具使用跟踪")
    print("  • 推理过程记录")
    print("  • 数据库持久化存储")
    print("  • 多维度查询功能")
    print("  • 统计分析和模式识别")
    print("  • 数据导出功能")

if __name__ == "__main__":
    demonstrate_learning_observer()
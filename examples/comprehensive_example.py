"""
HermesAgentEvolution - 端到端示例应用
展示工具能力进化（迭代3）和学习能力进化（迭代2）的完整工作流程

运行方式：
    cd /mnt/c/Users/1/hermes_agent_evolution
    python examples/comprehensive_example.py
"""

import sys
import os
import tempfile
import time

# 添加项目根目录到 sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from evolution.tools import (
    ToolRegistry, ToolDefinition, ToolCategory, ToolStatus,
    EnhancedToolCreator, CreationSource, ToolQuality,
    ToolPerformanceAnalyzer, PerformanceMetric, PerformanceLevel,
    ToolAutoGenerator, GenerationStrategy,
    ToolEvolutionEngine, EvolutionConfig, EvolutionStatus
)
from evolution.learning import (
    LearningObserver, ExperienceAnalyzer,
    ToolStrategyLearner, ToolStrategyType,
    Experience, ExperienceType, Outcome,
    AnalysisResult, PatternInstance, AnalysisPatternType
)


def print_header(title: str):
    """打印带格式的章节标题"""
    print()
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)


def step_1_create_and_register_tools():
    """步骤1：创建并注册工具"""
    print_header("步骤1：工具创建与注册")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(os.path.join(tmpdir, "tools.db"))
        creator = EnhancedToolCreator(registry)

        # 1a. 从函数创建
        def calculate_average(numbers):
            """计算数字列表的平均值"""
            return sum(numbers) / len(numbers) if numbers else 0

        r1 = creator.create_from_function(calculate_average)
        print(f"  [从函数创建] {r1.tool_definition.name}: 质量评分={r1.quality_score:.2f}")

        # 1b. 从代码创建
        code = '''def file_backup(source_dir: str, dest_dir: str) -> bool:
    """备份目录到目标位置"""
    import shutil
    import os
    if not os.path.exists(source_dir):
        return False
    os.makedirs(dest_dir, exist_ok=True)
    for f in os.listdir(source_dir):
        src_path = os.path.join(source_dir, f)
        if os.path.isfile(src_path):
            shutil.copy2(src_path, dest_dir)
    return True
'''
        r2 = creator.create_from_code(code, name="file_backup", description="文件备份工具")
        print(f"  [从代码创建] {r2.tool_definition.name}: 质量评分={r2.quality_score:.2f}")

        # 1c. 从模板创建
        r3 = creator.create_from_template("file_operation", {
            "name": "my_file_op",
            "description": "我的文件操作",
            "category": "FILE_OPERATION",
            "tags": ["custom"]
        })
        print(f"  [从模板创建] {r3.tool_definition.name}: 来源={r3.creation_source.value}")

        # 1d. 从API描述创建
        r4 = creator.create_from_api_description(
            api_spec={"method": "GET", "path": "/api/users", "description": "获取用户列表，返回JSON数组"},
            name="get_users"
        )
        print(f"  [从API描述创建] {r4.tool_definition.name}: 质量评分={r4.quality_score:.2f}")

        # 查看所有工具
        print(f"\n  注册表中共有 {len(registry.list_all())} 个工具:")
        for t in registry.list_all():
            print(f"    - {t.name}: [{t.category.value}] {t.description}")

    print("  ✓ 临时数据库已清理\n")


def step_2_tool_performance_analysis():
    """步骤2：工具性能分析"""
    print_header("步骤2：工具性能分析与监控")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(os.path.join(tmpdir, "tools.db"))
        analyzer = ToolPerformanceAnalyzer(registry, db_path=os.path.join(tmpdir, "perf.db"))

        # 注册一个工具
        tool = ToolDefinition(name="data_processor",
                              description="数据处理工具",
                              category=ToolCategory.DATA_PROCESSING)
        registry.register(tool)

        # 模拟性能数据
        for i in range(10):
            analyzer.record_performance("data_processor",
                                        PerformanceMetric.EXECUTION_TIME,
                                        0.1 + (i * 0.02))  # 逐渐变慢
            analyzer.record_performance("data_processor",
                                        PerformanceMetric.SUCCESS_RATE,
                                        0.95 - (i * 0.01))  # 逐渐降低成功率
            analyzer.record_performance("data_processor",
                                        PerformanceMetric.ERROR_RATE,
                                        0.05 + (i * 0.005))  # 错误率上升

        # 分析工具性能
        summary = analyzer.analyze_tool_performance("data_processor")
        print(f"  工具: {summary.tool_name}")
        print(f"  总体评分: {summary.overall_score:.1f}/100")
        print(f"  性能等级: {summary.performance_level.value}")
        print(f"  关键洞察: {summary.key_insights}")

        # 生成文本报告
        report = analyzer.generate_performance_report("text")
        print(f"\n  性能报告预览（前300字符）:")
        print(f"  {report[:300]}...")

    print("  ✓ 性能分析完成\n")


def step_3_auto_generate_tools():
    """步骤3：自动生成工具"""
    print_header("步骤3：工具自动生成")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(os.path.join(tmpdir, "gen.db"))
        generator = ToolAutoGenerator(registry=registry)

        # 3a. 从需求生成单个工具
        requirements = [
            "读取CSV文件并解析内容",
            "向服务器发送POST请求",
            "查找文本中的正则匹配"
        ]

        for req in requirements:
            result = generator.generate_from_requirement(req)
            if result.success:
                print(f"  ✓ [{result.strategy.value}] {req}")
                print(f"     工具名: {result.tool_name}")
                print(f"     代码行数: {result.tool_code.count(chr(10)) + 1}")
                print(f"     估计质量: {result.estimated_quality:.2f}")
            else:
                print(f"  ✗ [{req}] 生成失败: {result.error_message}")

        # 3b. 组合多个工具生成工作流
        print("\n  组合生成复合工作流...")
        workflow = generator.generate_composite_workflow([
            "读取文件",
            "过滤数据",
            "写入文件"
        ])
        if workflow.success:
            print(f"  ✓ 工作流生成成功: {workflow.tool_name}")
            print(f"     策略: {workflow.strategy.value}")
        else:
            print(f"  ✗ 工作流生成失败: {workflow.error_message}")

        # 3c. 查看历史
        history = generator.get_generation_history()
        print(f"\n  生成历史记录: {len(history)} 条")

    print("  ✓ 自动生成完成\n")


def step_4_tool_evolution_cycle():
    """步骤4：工具进化周期"""
    print_header("步骤4：工具进化周期")

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "evo.db")
        registry = ToolRegistry(db_path)

        # 注册一些工具（含低性能工具）
        tools = [
            ToolDefinition(name="fast_reader", description="快速读取器",
                           category=ToolCategory.FILE_OPERATION,
                           usage_count=200, success_count=198, error_count=2),
            ToolDefinition(name="slow_writer", description="慢写入器",
                           category=ToolCategory.FILE_OPERATION,
                           usage_count=50, success_count=30, error_count=20),
            ToolDefinition(name="buggy_filter", description="有缺陷的过滤器",
                           category=ToolCategory.DATA_PROCESSING,
                           usage_count=30, success_count=10, error_count=20),
        ]
        for t in tools:
            registry.register(t)

        # 创建进化配置（禁用学习系统集成以简化）
        config = EvolutionConfig(
            auto_evolve=True,
            evolution_interval=10,
            min_performance_score=50.0,
            enable_auto_registration=True,
            enable_performance_monitoring=True,
            learning_integration_enabled=False
        )

        engine = ToolEvolutionEngine(registry, config)

        # 查看初始化状态
        status = engine.get_status_summary()
        print(f"  初始状态:")
        print(f"    工具总数: {status['total_tools']}")
        print(f"    引擎状态: {status['status']}")

        # 运行进化周期
        print(f"\n  运行进化周期...")
        result = engine.run_evolution_cycle()
        print(f"    进化成功: {result['success']}")

        # 自动生成新工具
        print(f"\n  自动生成新工具...")
        gen_result = engine.auto_generate_tool("读取JSON数据")
        if gen_result.success:
            print(f"    生成成功: {gen_result.tool_name}")

        # 生成进化报告
        print(f"\n  生成进化报告...")
        report = engine.generate_evolution_report()
        # 报告较长，只显示前5行
        lines = report.strip().split('\n')
        print(f"    {lines[0]}")
        print(f"    {lines[1]}")
        print(f"    {lines[2]}")
        print(f"    ...")
        for line in lines:
            if '工具总数' in line or '进化引擎' in line:
                print(f"    {line.strip()}")

    print("  ✓ 进化周期完成\n")


def step_5_learning_system_integration():
    """步骤5：学习系统集成（迭代2）"""
    print_header("步骤5：学习系统集成")

    with tempfile.TemporaryDirectory() as tmpdir:
        # 创建学习观察器
        observer = LearningObserver(db_path=os.path.join(tmpdir, "experience.db"))

        # 记录经验
        experiences_data = [
            {
                "task": "create_file_reader",
                "action": "create_file_reader",
                "tags": ["file_operation", "user_request"]
            },
            {
                "task": "create_http_client", 
                "action": "create_http_client",
                "tags": ["network", "timeout"]
            },
            {
                "task": "analyze_data",
                "action": "analyze_data",
                "tags": ["data_processing", "analysis"]
            },
        ]

        type_map = [
            ExperienceType.TOOL_USAGE,
            ExperienceType.ERROR_RECOVERY,
            ExperienceType.TOOL_USAGE
        ]
        outcome_map = [
            Outcome.SUCCESS,
            Outcome.FAILURE,
            Outcome.SUCCESS
        ]

        for i, data in enumerate(experiences_data):
            exp = Experience(
                id=f"exp_{i}",
                task_id=data["task"],
                experience_type=type_map[i],
                outcome=outcome_map[i],
                context={"action": data["action"]},
                actions=[{"name": data["action"], "status": outcome_map[i].value}],
                tags=data["tags"]
            )
            exp_id = observer.record_experience(exp)
            print(f"  ✓ 记录经验: {data['task']} -> {'成功' if outcome_map[i] == Outcome.SUCCESS else '失败'} ({exp_id})")

        # 分析学习模式
        analyzer = ExperienceAnalyzer(observer)
        analysis = analyzer.analyze_recent_experiences(days=7)
        print(f"\n  分析结果:")
        print(f"    总经验数: {analysis.total_experiences}")
        print(f"    成功率: {analysis.success_rate:.1%}")
        print(f"    识别到的模式: {len(analysis.identified_patterns)} 个")
        for p in analysis.identified_patterns:
            print(f"      - {p.pattern_type.value}: 频率={p.frequency}")
        print(f"    关键洞察: {len(analysis.key_insights)} 条")
        for insight in analysis.key_insights:
            print(f"      - {insight}")

        # 生成改进建议
        print(f"\n  改进建议: {len(analysis.improvement_suggestions)} 条")
        for s in analysis.improvement_suggestions:
            print(f"    - {s}")
        print(f"  总结: {analysis.summary}")

    print("  ✓ 学习系统集成完成\n")


def step_6_end_to_end_workflow():
    """步骤6：端到端工作流"""
    print_header("步骤6：端到端工作流演示")

    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(os.path.join(tmpdir, "e2e.db"))
        perf_analyzer = ToolPerformanceAnalyzer(
            registry, db_path=os.path.join(tmpdir, "e2e_perf.db")
        )

        # 1. 创建多个工具
        print("【1】创建工具...")
        creator = EnhancedToolCreator(registry)

        def search_data(query, limit=10):
            """搜索数据并返回结果"""
            results = []
            for i in range(limit):
                results.append({"id": i, "content": f"{query}_result_{i}"})
            return results

        creator.create_from_function(search_data)
        creator.create_from_template("file_operation", {
            "name": "file_op", "description": "文件操作",
            "category": "FILE_OPERATION", "tags": ["e2e"]
        })
        creator.create_from_api_description(
            api_spec={"method": "POST", "path": "/api/upload", "description": "上传文件，返回文件ID"},
            name="upload_file"
        )
        print(f"  注册表共有 {len(registry.list_all())} 个工具")

        # 2. 记录性能数据
        print("\n【2】记录性能数据...")
        for i in range(20):
            perf_analyzer.record_performance("search_data",
                                             PerformanceMetric.EXECUTION_TIME,
                                             0.3 + (i * 0.01))
            perf_analyzer.record_performance("search_data",
                                             PerformanceMetric.SUCCESS_RATE,
                                             0.95)

        # 3. 分析性能
        print("\n【3】分析性能...")
        summary = perf_analyzer.analyze_tool_performance("search_data")
        print(f"  搜索工具性能等级: {summary.performance_level.value}")
        print(f"  总体评分: {summary.overall_score:.1f}")

        # 4. 自动生成新工具
        print("\n【4】自动生成新工具...")
        gen_registry = ToolRegistry(os.path.join(tmpdir, "gen.db"))
        generator = ToolAutoGenerator(registry=gen_registry)
        gen_result = generator.generate_from_requirement("过滤数据")
        if gen_result.success:
            print(f"  生成了: {gen_result.tool_name}")

        # 5. 运行进化周期
        print("\n【5】运行进化周期...")
        config = EvolutionConfig(
            auto_evolve=True,
            evolution_interval=10,
            min_performance_score=50.0,
            enable_auto_registration=True,
            enable_performance_monitoring=True,
            learning_integration_enabled=False
        )
        engine = ToolEvolutionEngine(registry, config)
        evolve_result = engine.run_evolution_cycle()
        print(f"  进化结果: {'✓ 成功' if evolve_result['success'] else '✗ 需要关注'}")

        # 6. 查看最终状态
        print("\n【6】查看最终状态...")
        status = engine.get_status_summary()
        print(f"  最终工具总数: {status['total_tools']}")
        print(f"  活跃工具: {status.get('active_tools', 'N/A')}")

    print("\n  ✓ 端到端工作流完成！")


def main():
    """主函数：运行所有示例"""
    print("=" * 70)
    print("  HermesAgentEvolution - 完整示例演示")
    print("  工具能力进化（迭代3）+ 学习能力进化（迭代2）")
    print("=" * 70)

    step_1_create_and_register_tools()
    step_2_tool_performance_analysis()
    step_3_auto_generate_tools()
    step_4_tool_evolution_cycle()
    step_5_learning_system_integration()
    step_6_end_to_end_workflow()

    print()
    print("=" * 70)
    print("  所有示例演示完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()

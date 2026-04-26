"""
工具能力创建框架使用示例
"""

import os
import sys
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.evolution.tools import (
    ToolDefinition,
    ToolRegistry,
    ToolCategory,
    ToolStatus,
    ToolCreator
)


def calculate_area(length: float, width: float) -> float:
    """计算矩形面积"""
    return length * width


def format_date(date_str: str, format_str: str = "%Y-%m-%d") -> str:
    """格式化日期字符串"""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime(format_str)
    except ValueError:
        return "无效的日期格式"


def main():
    """主函数"""
    print("=== 工具能力创建框架使用示例 ===\n")
    
    # 1. 创建工具注册表
    registry = ToolRegistry("data/tools_example.db")
    print("1. 工具注册表已创建")
    
    # 2. 创建工具创建器
    creator = ToolCreator(registry)
    print("2. 工具创建器已创建")
    
    # 3. 从函数创建工具
    print("\n3. 从函数创建工具:")
    
    # 创建面积计算工具
    area_result = creator.create_from_function(
        func=calculate_area,
        name="calculate_rectangle_area",
        description="计算矩形面积",
        category=ToolCategory.UTILITY,
        tags=["geometry", "math", "calculation"]
    )
    
    if area_result.success:
        print(f"  ✓ 创建工具: {area_result.tool_definition.name}")
        print(f"    描述: {area_result.tool_definition.description}")
        print(f"    参数: {list(area_result.tool_definition.parameters.keys())}")
    else:
        print(f"  ✗ 创建失败: {area_result.error_message}")
    
    # 创建日期格式化工具
    date_result = creator.create_from_function(
        func=format_date,
        name="format_date_string",
        description="格式化日期字符串",
        category=ToolCategory.DATA_PROCESSING,
        tags=["date", "format", "utility"]
    )
    
    if date_result.success:
        print(f"  ✓ 创建工具: {date_result.tool_definition.name}")
        print(f"    描述: {date_result.tool_definition.description}")
        print(f"    参数: {list(date_result.tool_definition.parameters.keys())}")
    else:
        print(f"  ✗ 创建失败: {date_result.error_message}")
    
    # 4. 从代码创建工具
    print("\n4. 从代码创建工具:")
    
    code = '''
def string_reverse(text: str) -> str:
    """反转字符串"""
    return text[::-1]
'''
    
    code_result = creator.create_from_code(
        code=code,
        name="reverse_string",
        description="反转字符串",
        category=ToolCategory.UTILITY,
        parameters={
            "text": {"type": "str", "required": True, "default": None}
        },
        return_type="str",
        tags=["string", "utility"]
    )
    
    if code_result.success:
        print(f"  ✓ 创建工具: {code_result.tool_definition.name}")
        print(f"    描述: {code_result.tool_definition.description}")
    else:
        print(f"  ✗ 创建失败: {code_result.error_message}")
    
    # 5. 列出所有工具
    print("\n5. 列出所有工具:")
    all_tools = registry.list_all()
    for i, tool in enumerate(all_tools, 1):
        print(f"  {i}. {tool.name} - {tool.description}")
        print(f"     类别: {tool.category.value}, 状态: {tool.status.value}")
    
    # 6. 获取统计信息
    print("\n6. 工具统计信息:")
    stats = registry.get_statistics()
    print(f"  工具总数: {stats['total_tools']}")
    print(f"  按类别分布: {stats['by_category']}")
    print(f"  总使用次数: {stats['total_usage']}")
    
    # 7. 搜索工具
    print("\n7. 搜索工具:")
    search_results = registry.search("计算")
    print(f"  搜索'计算'的结果: {len(search_results)} 个工具")
    for tool in search_results:
        print(f"    - {tool.name}: {tool.description}")
    
    # 8. 生成工具文档
    print("\n8. 生成工具文档示例:")
    if all_tools:
        first_tool = all_tools[0]
        doc = creator.generate_tool_documentation(first_tool)
        # 只显示文档的前几行
        lines = doc.split('\n')[:15]
        print("\n".join([f"    {line}" for line in lines]))
        print("    ...")
    
    print("\n=== 示例完成 ===")


if __name__ == "__main__":
    main()
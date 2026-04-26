"""
工具创建器测试模块
"""

import os
import tempfile
import pytest
from datetime import datetime

from src.evolution.tools.tool_registry import (
    ToolDefinition, ToolRegistry, ToolCategory, ToolStatus
)
from src.evolution.tools.tool_creator import ToolCreator, ToolCreationResult


# 测试用辅助函数（不以test_开头，避免被pytest识别为测试用例）
def add_function(a: int, b: int) -> int:
    """两个数相加"""
    return a + b


def greet_function(name: str = "World") -> str:
    """打招呼"""
    return f"Hello, {name}!"


def wrapper_function(func, *args, **kwargs):
    """测试包装器"""
    print(f"调用函数: {func.__name__}")
    result = func(*args, **kwargs)
    print(f"结果: {result}")
    return result


class TestToolDefinition:
    """测试工具定义类"""
    
    def test_tool_definition_creation(self):
        """测试工具定义创建"""
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.UTILITY,
            status=ToolStatus.ACTIVE
        )
        
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.category == ToolCategory.UTILITY
        assert tool.status == ToolStatus.ACTIVE
        assert tool.version == "1.0.0"
        assert tool.author == "system"
        assert isinstance(tool.created_at, datetime)
        assert isinstance(tool.updated_at, datetime)
        assert tool.usage_count == 0
        assert tool.success_count == 0
        assert tool.error_count == 0
        assert tool.parameters == {}
        assert tool.return_type == "Any"
        assert tool.dependencies == []
        assert tool.tags == []
        assert tool.source_code == ""
        assert tool.is_builtin is False
    
    def test_tool_definition_to_dict(self):
        """测试工具定义转字典"""
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.UTILITY,
            status=ToolStatus.ACTIVE
        )
        
        data = tool.to_dict()
        
        assert data['name'] == "test_tool"
        assert data['description'] == "测试工具"
        assert data['category'] == "utility"
        assert data['status'] == "active"
        assert 'created_at' in data
        assert 'updated_at' in data
    
    def test_tool_definition_from_dict(self):
        """测试从字典创建工具定义"""
        data = {
            'name': 'test_tool',
            'description': '测试工具',
            'category': 'utility',
            'status': 'active',
            'version': '1.0.0',
            'author': 'test',
            'created_at': '2024-01-01T00:00:00',
            'updated_at': '2024-01-01T00:00:00',
            'usage_count': 0,
            'success_count': 0,
            'error_count': 0,
            'parameters': {},
            'return_type': 'int',
            'dependencies': [],
            'tags': [],
            'source_code': '',
            'is_builtin': False
        }
        
        tool = ToolDefinition.from_dict(data)
        
        assert tool.name == "test_tool"
        assert tool.description == "测试工具"
        assert tool.category == ToolCategory.UTILITY
        assert tool.status == ToolStatus.ACTIVE
        assert tool.return_type == "int"


class TestToolRegistry:
    """测试工具注册表"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    def test_registry_initialization(self, temp_db):
        """测试注册表初始化"""
        registry = ToolRegistry(temp_db)
        
        # 检查数据库文件是否创建
        assert os.path.exists(temp_db)
    
    def test_register_and_get_tool(self, temp_db):
        """测试注册和获取工具"""
        registry = ToolRegistry(temp_db)
        
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.UTILITY,
            status=ToolStatus.ACTIVE,
            parameters={"a": {"type": "int", "required": True}},
            return_type="int"
        )
        
        # 注册工具
        assert registry.register(tool) is True
        
        # 获取工具
        retrieved = registry.get("test_tool")
        assert retrieved is not None
        assert retrieved.name == "test_tool"
        assert retrieved.description == "测试工具"
        assert retrieved.category == ToolCategory.UTILITY
    
    def test_list_all_tools(self, temp_db):
        """测试列出所有工具"""
        registry = ToolRegistry(temp_db)
        
        # 注册多个工具
        tools = [
            ToolDefinition(name=f"tool_{i}", 
                         description=f"工具{i}",
                         category=ToolCategory.UTILITY)
            for i in range(3)
        ]
        
        for tool in tools:
            registry.register(tool)
        
        # 列出所有工具
        all_tools = registry.list_all()
        assert len(all_tools) == 3
        
        # 按类别过滤
        utility_tools = registry.list_all(category="utility")
        assert len(utility_tools) == 3
    
    def test_update_usage_stats(self, temp_db):
        """测试更新使用统计"""
        registry = ToolRegistry(temp_db)
        
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.UTILITY
        )
        
        registry.register(tool)
        
        # 更新统计
        registry.update_usage_stats("test_tool", success=True)
        registry.update_usage_stats("test_tool", success=False)
        
        # 获取更新后的工具
        updated = registry.get("test_tool")
        assert updated.usage_count == 2
        assert updated.success_count == 1
        assert updated.error_count == 1
    
    def test_delete_tool(self, temp_db):
        """测试删除工具"""
        registry = ToolRegistry(temp_db)
        
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具",
            category=ToolCategory.UTILITY
        )
        
        registry.register(tool)
        
        # 删除工具
        assert registry.delete("test_tool") is True
        
        # 确认工具已删除
        assert registry.get("test_tool") is None
    
    def test_get_statistics(self, temp_db):
        """测试获取统计信息"""
        registry = ToolRegistry(temp_db)
        
        # 注册工具
        tools = [
            ToolDefinition(name="tool1", description="工具1", category=ToolCategory.UTILITY),
            ToolDefinition(name="tool2", description="工具2", category=ToolCategory.DATA_PROCESSING),
        ]
        
        for tool in tools:
            registry.register(tool)
        
        stats = registry.get_statistics()
        
        assert stats['total_tools'] == 2
        assert 'utility' in stats['by_category']
        assert 'data_processing' in stats['by_category']
    
    def test_search_tools(self, temp_db):
        """测试搜索工具"""
        registry = ToolRegistry(temp_db)
        
        tools = [
            ToolDefinition(name="calculator", description="计算器工具", category=ToolCategory.UTILITY, tags=["math", "calc"]),
            ToolDefinition(name="file_reader", description="文件读取工具", category=ToolCategory.FILE_OPERATION, tags=["file", "io"]),
        ]
        
        for tool in tools:
            registry.register(tool)
        
        # 搜索
        results = registry.search("calc")
        assert len(results) == 1
        assert results[0].name == "calculator"
        
        results = registry.search("工具")
        assert len(results) == 2


class TestToolCreator:
    """测试工具创建器"""
    
    @pytest.fixture
    def temp_db(self):
        """创建临时数据库"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def creator(self, temp_db):
        """创建工具创建器"""
        registry = ToolRegistry(temp_db)
        return ToolCreator(registry)
    
    def test_create_from_function(self, creator):
        """测试从函数创建工具"""
        result = creator.create_from_function(
            func=add_function,
            name="add_numbers",
            description="两个数字相加",
            category=ToolCategory.UTILITY,
            tags=["math", "addition"]
        )
        
        assert result.success is True
        assert result.tool_definition is not None
        assert result.tool_definition.name == "add_numbers"
        assert result.tool_definition.description == "两个数字相加"
        assert result.tool_definition.category == ToolCategory.UTILITY
        assert "math" in result.tool_definition.tags
        assert "a" in result.tool_definition.parameters
        assert "b" in result.tool_definition.parameters
        # 注意：返回类型可能是 "<class 'int'>" 或 "int"，取决于Python版本
        assert "int" in result.tool_definition.return_type
    
    def test_create_from_code(self, creator):
        """测试从代码创建工具"""
        code = '''
def multiply(a: int, b: int) -> int:
    """两个数相乘"""
    return a * b
'''
        
        result = creator.create_from_code(
            code=code,
            name="multiply_numbers",
            description="两个数字相乘",
            category=ToolCategory.UTILITY,
            parameters={
                "a": {"type": "int", "required": True},
                "b": {"type": "int", "required": True}
            },
            return_type="int",
            tags=["math", "multiplication"]
        )
        
        assert result.success is True
        assert result.tool_definition is not None
        assert result.tool_definition.name == "multiply_numbers"
        assert "multiply" in result.tool_definition.source_code
    
    def test_create_wrapper_tool(self, creator):
        """测试创建包装器工具"""
        result = creator.create_wrapper_tool(
            original_func=add_function,
            wrapper_func=wrapper_function,
            name="add_with_logging",
            description="带日志的加法工具",
            category=ToolCategory.UTILITY,
            tags=["wrapper", "logging"]
        )
        
        assert result.success is True
        assert result.tool_definition is not None
        assert result.tool_definition.name == "add_with_logging"
        assert "wrapper" in result.tool_definition.tags
        assert f"wraps:{add_function.__name__}" in result.tool_definition.tags
    
    def test_create_batch_tools(self, creator):
        """测试批量创建工具"""
        func_list = [
            {
                'func': add_function,
                'name': 'add_tool',
                'description': '加法工具',
                'category': ToolCategory.UTILITY,
                'tags': ['math']
            },
            {
                'func': greet_function,
                'name': 'greet_tool',
                'description': '打招呼工具',
                'category': ToolCategory.UTILITY,
                'tags': ['greeting']
            }
        ]
        
        results = creator.create_batch_tools(func_list)
        
        assert len(results) == 2
        assert 'add_tool' in results
        assert 'greet_tool' in results
        assert results['add_tool'].success is True
        assert results['greet_tool'].success is True
    
    def test_validate_tool_definition(self, creator):
        """测试验证工具定义"""
        # 有效的工具定义
        valid_tool = ToolDefinition(
            name="valid_tool",
            description="有效工具",
            category=ToolCategory.UTILITY,
            source_code="def func(): pass"
        )
        
        errors = creator.validate_tool_definition(valid_tool)
        assert len(errors) == 0
        
        # 无效的工具定义
        invalid_tool = ToolDefinition(
            name="",
            description="",
            category=ToolCategory.UTILITY,
            source_code=""
        )
        
        errors = creator.validate_tool_definition(invalid_tool)
        assert len(errors) > 0
        assert "工具名称不能为空" in errors
        assert "工具描述不能为空" in errors
        assert "源代码不能为空" in errors
    
    def test_generate_tool_documentation(self, creator):
        """测试生成工具文档"""
        tool = ToolDefinition(
            name="test_tool",
            description="测试工具描述",
            category=ToolCategory.UTILITY,
            status=ToolStatus.ACTIVE,
            version="1.0.0",
            author="tester",
            parameters={
                "input": {"type": "str", "required": True, "default": None}
            },
            return_type="str",
            dependencies=["os", "sys"],
            tags=["test", "utility"],
            source_code="def test(): pass",
            usage_count=10,
            success_count=8,
            error_count=2
        )
        
        doc = creator.generate_tool_documentation(tool)
        
        assert "# test_tool" in doc
        assert "测试工具描述" in doc
        assert "utility" in doc
        assert "active" in doc
        assert "参数" in doc
        assert "input" in doc
        assert "依赖项" in doc
        assert "os" in doc
        assert "sys" in doc
        assert "标签" in doc
        assert "test" in doc
        assert "总使用次数: 10" in doc
        assert "源代码" in doc
        assert "def test(): pass" in doc
    
    def test_extract_dependencies(self, creator):
        """测试提取依赖项"""
        code_with_imports = '''
import os
import sys
from datetime import datetime
import json as js
from typing import List, Dict
'''
        
        dependencies = creator._extract_dependencies_from_source(code_with_imports)
        
        assert "os" in dependencies
        assert "sys" in dependencies
        assert "datetime.datetime" in dependencies
        assert "json" in dependencies
        assert "typing.List" in dependencies
        assert "typing.Dict" in dependencies


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
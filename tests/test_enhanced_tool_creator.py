"""
增强版工具创建器测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from evolution.tools import (
    EnhancedToolCreator, CreationSource, ToolQuality, CodeAnalysisResult,
    ToolDefinition, ToolRegistry, ToolCategory, ToolStatus
)


class TestEnhancedToolCreator:
    """增强版工具创建器测试"""
    
    @pytest.fixture
    def creator(self):
        return EnhancedToolCreator()
    
    def test_create_from_function(self, creator):
        """测试从函数创建工具"""
        def test_func(param1: str, param2: int = 0) -> bool:
            """测试函数"""
            return True
        
        result = creator.create_from_function(test_func)
        
        assert result.success
        assert result.tool_definition is not None
        assert result.tool_definition.name == "test_func"
        assert result.creation_source == CreationSource.FUNCTION
    
    def test_create_from_code(self, creator):
        """测试从代码创建工具"""
        code = '''
def hello(name: str) -> str:
    """Say hello"""
    return f"Hello, {name}"
'''
        result = creator.create_from_code(
            code=code,
            name="hello_tool",
            description="Hello world tool",
            category=ToolCategory.UTILITY
        )
        
        assert result.success
        assert result.tool_definition is not None
        assert result.tool_definition.name == "hello_tool"
        assert result.creation_source == CreationSource.CODE
    
    def test_create_from_code_invalid_syntax(self, creator):
        """测试从无效代码创建工具"""
        code = '''
def broken_function(:
    pass
'''
        result = creator.create_from_code(
            code=code,
            name="broken_tool",
            description="Broken tool"
        )
        
        # 语法错误导致质量降低，但创建仍然成功
        assert result.success
        assert result.quality_score < 0.5
    
    def test_create_from_api_description(self, creator):
        """测试从API描述创建工具"""
        api_spec = {
            "description": "获取用户信息",
            "parameters": [
                {"name": "user_id", "type": "int", "description": "用户ID"}
            ],
            "return_type": "Dict",
            "return_description": "用户信息",
            "tags": []
        }
        
        result = creator.create_from_api_description(
            api_spec=api_spec,
            name="get_user",
            category=ToolCategory.NETWORK
        )
        
        assert result.success
        assert result.tool_definition.name == "get_user"
    
    def test_create_from_template(self, creator):
        """测试从模板创建工具"""
        params = {
            "name": "my_file_op",
            "description": "文件操作工具",
            "category": "FILE_OPERATION"
        }
        
        result = creator.create_from_template(
            template_name="file_operation",
            template_params=params
        )
        
        assert result.success
        assert result.tool_definition is not None
    
    def test_get_creation_history(self, creator):
        """测试获取创建历史"""
        def test_func1():
            pass
        creator.create_from_function(test_func1, name="func1")
        creator.create_from_function(test_func1, name="func2")
        
        history = creator.get_creation_history(limit=5)
        assert len(history) == 2
    
    def test_get_creation_stats(self, creator):
        """测试获取创建统计"""
        stats = creator.get_creation_stats()
        
        def test_func():
            pass
        creator.create_from_function(test_func)
        
        stats = creator.get_creation_stats()
        assert stats["total_creations"] >= 1
        assert stats["successful_creations"] >= 1


class TestToolCreatorOverride:
    """测试兼容性"""
    
    def test_tool_creator_alias(self):
        """测试ToolCreator别名"""
        from evolution.tools.enhanced_tool_creator import ToolCreator
        assert ToolCreator == EnhancedToolCreator

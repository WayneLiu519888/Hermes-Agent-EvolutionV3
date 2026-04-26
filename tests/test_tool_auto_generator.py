"""
工具自动生成器测试
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import pytest
from evolution.tools import ToolAutoGenerator, GenerationStrategy
from evolution.tools import ToolRegistry, ToolCategory


class TestToolAutoGenerator:
    """工具自动生成器测试"""
    
    @pytest.fixture
    def generator(self):
        return ToolAutoGenerator()
    
    def test_generate_file_reader(self, generator):
        """测试生成文件读取工具"""
        result = generator.generate_from_requirement("读取文件内容")
        
        assert result.success
        assert result.tool_name == "file_reader"
        assert result.strategy == GenerationStrategy.TEMPLATE
    
    def test_generate_data_filter(self, generator):
        """测试生成数据过滤工具"""
        result = generator.generate_from_requirement("过滤数据列表")
        
        assert result.success
        assert result.tool_name == "data_filter"
    
    def test_generate_http_get(self, generator):
        """测试生成HTTP GET工具"""
        result = generator.generate_from_requirement("获取远程数据")
        
        assert result.success
        assert result.tool_name == "http_get"
    
    def test_generate_unknown_requirement(self, generator):
        """测试未知需求"""
        result = generator.generate_from_requirement("xxxyyyzzz")
        
        assert not result.success
    
    def test_composite_generate(self, generator):
        """测试组合生成"""
        requirements = ["读取文件内容", "过滤数据"]
        result = generator.generate_composite_workflow(requirements)
        
        assert result.success
        assert "workflow" in result.tool_name
        assert result.strategy == GenerationStrategy.COMPOSITE
    
    def test_list_templates(self, generator):
        """测试列出模板"""
        templates = generator.list_available_templates()
        assert len(templates) > 0
    
    def test_add_custom_template(self, generator):
        """测试添加自定义模板"""
        code = '''
def custom_tool(data: str) -> str:
    """自定义工具"""
    return data.upper()
'''
        result = generator.add_custom_template(
            name="custom_tool",
            description="自定义工具",
            category=ToolCategory.CUSTOM,
            code=code,
            tags=["custom"]
        )
        
        assert result
        templates = generator.list_available_templates()
        template_names = [t["name"] for t in templates]
        assert "custom_tool" in template_names
    
    def test_get_generation_history(self, generator):
        """测试获取生成历史"""
        generator.generate_from_requirement("读取文件内容")
        generator.generate_from_requirement("写入文件")
        
        history = generator.get_generation_history(5)
        assert len(history) == 2

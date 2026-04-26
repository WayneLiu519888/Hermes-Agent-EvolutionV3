"""
工具创建器模块
负责从函数、代码等创建工具
"""

import ast
import inspect
import textwrap
from typing import Dict, Any, Callable, Optional, List
from dataclasses import dataclass
from datetime import datetime

from .tool_registry import ToolDefinition, ToolRegistry, ToolCategory, ToolStatus


@dataclass
class ToolCreationResult:
    """工具创建结果"""
    success: bool
    tool_definition: Optional[ToolDefinition] = None
    error_message: str = ""
    warnings: List[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class ToolCreator:
    """工具创建器"""
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        初始化工具创建器
        
        Args:
            registry: 工具注册表实例，如果为None则创建新的
        """
        self.registry = registry or ToolRegistry()
    
    def create_from_function(self, func: Callable, 
                           name: Optional[str] = None,
                           description: Optional[str] = None,
                           category: ToolCategory = ToolCategory.UTILITY,
                           tags: Optional[List[str]] = None,
                           is_builtin: bool = False) -> ToolCreationResult:
        """
        从函数创建工具
        
        Args:
            func: 函数对象
            name: 工具名称，如果为None则使用函数名
            description: 工具描述，如果为None则使用函数文档字符串
            category: 工具类别
            tags: 标签列表
            is_builtin: 是否为内置工具
            
        Returns:
            工具创建结果
        """
        try:
            # 获取函数信息
            func_name = name or func.__name__
            func_doc = description or (func.__doc__ or "").strip()
            
            # 解析函数签名
            sig = inspect.signature(func)
            parameters = {}
            
            for param_name, param in sig.parameters.items():
                param_info = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }
                parameters[param_name] = param_info
            
            # 获取返回类型
            return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else 'Any'
            
            # 获取源代码
            try:
                source_code = inspect.getsource(func)
            except:
                source_code = f"# 无法获取函数 {func_name} 的源代码"
            
            # 创建工具定义
            tool_def = ToolDefinition(
                name=func_name,
                description=func_doc,
                category=category,
                status=ToolStatus.ACTIVE,
                version="1.0.0",
                author="system",
                parameters=parameters,
                return_type=return_type,
                dependencies=self._extract_dependencies_from_source(source_code),
                tags=tags or [],
                source_code=source_code,
                is_builtin=is_builtin
            )
            
            # 注册工具
            if self.registry.register(tool_def):
                return ToolCreationResult(
                    success=True,
                    tool_definition=tool_def,
                    warnings=["工具创建成功"]
                )
            else:
                return ToolCreationResult(
                    success=False,
                    error_message="工具注册失败"
                )
                
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"从函数创建工具失败: {e}"
            )
    
    def create_from_code(self, code: str,
                        name: str,
                        description: str,
                        category: ToolCategory = ToolCategory.CUSTOM,
                        parameters: Optional[Dict[str, Any]] = None,
                        return_type: str = "Any",
                        tags: Optional[List[str]] = None,
                        is_builtin: bool = False) -> ToolCreationResult:
        """
        从代码字符串创建工具
        
        Args:
            code: 代码字符串
            name: 工具名称
            description: 工具描述
            category: 工具类别
            parameters: 参数定义
            return_type: 返回类型
            tags: 标签列表
            is_builtin: 是否为内置工具
            
        Returns:
            工具创建结果
        """
        try:
            # 验证代码语法
            try:
                ast.parse(code)
            except SyntaxError as e:
                return ToolCreationResult(
                    success=False,
                    error_message=f"代码语法错误: {e}"
                )
            
            # 创建工具定义
            tool_def = ToolDefinition(
                name=name,
                description=description,
                category=category,
                status=ToolStatus.ACTIVE,
                version="1.0.0",
                author="system",
                parameters=parameters or {},
                return_type=return_type,
                dependencies=self._extract_dependencies_from_source(code),
                tags=tags or [],
                source_code=code,
                is_builtin=is_builtin
            )
            
            # 注册工具
            if self.registry.register(tool_def):
                return ToolCreationResult(
                    success=True,
                    tool_definition=tool_def,
                    warnings=["工具创建成功"]
                )
            else:
                return ToolCreationResult(
                    success=False,
                    error_message="工具注册失败"
                )
                
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"从代码创建工具失败: {e}"
            )
    
    def create_wrapper_tool(self, 
                          original_func: Callable,
                          wrapper_func: Callable,
                          name: Optional[str] = None,
                          description: Optional[str] = None,
                          category: ToolCategory = ToolCategory.UTILITY,
                          tags: Optional[List[str]] = None) -> ToolCreationResult:
        """
        创建包装器工具
        
        Args:
            original_func: 原始函数
            wrapper_func: 包装函数
            name: 工具名称，如果为None则使用包装函数名
            description: 工具描述
            category: 工具类别
            tags: 标签列表
            
        Returns:
            工具创建结果
        """
        try:
            # 获取包装函数信息
            wrapper_name = name or wrapper_func.__name__
            wrapper_doc = description or (wrapper_func.__doc__ or f"包装器: {original_func.__name__}").strip()
            
            # 解析包装函数签名
            sig = inspect.signature(wrapper_func)
            parameters = {}
            
            for param_name, param in sig.parameters.items():
                param_info = {
                    'type': str(param.annotation) if param.annotation != inspect.Parameter.empty else 'Any',
                    'default': param.default if param.default != inspect.Parameter.empty else None,
                    'required': param.default == inspect.Parameter.empty
                }
                parameters[param_name] = param_info
            
            # 获取返回类型
            return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else 'Any'
            
            # 获取源代码
            try:
                wrapper_code = inspect.getsource(wrapper_func)
                original_code = inspect.getsource(original_func)
                source_code = f"# 包装器函数\n{wrapper_code}\n\n# 原始函数\n{original_code}"
            except:
                source_code = f"# 包装器: {wrapper_name}\n# 原始函数: {original_func.__name__}"
            
            # 创建工具定义
            tool_def = ToolDefinition(
                name=wrapper_name,
                description=wrapper_doc,
                category=category,
                status=ToolStatus.ACTIVE,
                version="1.0.0",
                author="system",
                parameters=parameters,
                return_type=return_type,
                dependencies=self._extract_dependencies_from_source(source_code),
                tags=(tags or []) + ["wrapper", f"wraps:{original_func.__name__}"],
                source_code=source_code,
                is_builtin=False
            )
            
            # 注册工具
            if self.registry.register(tool_def):
                return ToolCreationResult(
                    success=True,
                    tool_definition=tool_def,
                    warnings=["包装器工具创建成功"]
                )
            else:
                return ToolCreationResult(
                    success=False,
                    error_message="包装器工具注册失败"
                )
                
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"创建包装器工具失败: {e}"
            )
    
    def create_batch_tools(self, func_list: List[Dict[str, Any]]) -> Dict[str, ToolCreationResult]:
        """
        批量创建工具
        
        Args:
            func_list: 函数列表，每个元素是包含函数和配置的字典
            
        Returns:
            创建结果字典，键为工具名，值为创建结果
        """
        results = {}
        
        for func_info in func_list:
            func = func_info.get('func')
            if not callable(func):
                results[func_info.get('name', 'unknown')] = ToolCreationResult(
                    success=False,
                    error_message="提供的对象不是可调用函数"
                )
                continue
            
            name = func_info.get('name')
            description = func_info.get('description')
            category = func_info.get('category', ToolCategory.UTILITY)
            tags = func_info.get('tags', [])
            is_builtin = func_info.get('is_builtin', False)
            
            result = self.create_from_function(
                func=func,
                name=name,
                description=description,
                category=category,
                tags=tags,
                is_builtin=is_builtin
            )
            
            tool_name = name or func.__name__
            results[tool_name] = result
        
        return results
    
    def _extract_dependencies_from_source(self, source_code: str) -> List[str]:
        """
        从源代码中提取依赖项
        
        Args:
            source_code: 源代码
            
        Returns:
            依赖项列表
        """
        dependencies = []
        
        try:
            tree = ast.parse(source_code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        dependencies.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        if module:
                            dependencies.append(f"{module}.{alias.name}")
                        else:
                            dependencies.append(alias.name)
            
            # 去重并排序
            dependencies = sorted(list(set(dependencies)))
            
        except:
            # 如果解析失败，返回空列表
            pass
        
        return dependencies
    
    def validate_tool_definition(self, tool_def: ToolDefinition) -> List[str]:
        """
        验证工具定义
        
        Args:
            tool_def: 工具定义
            
        Returns:
            验证错误列表，如果为空则表示验证通过
        """
        errors = []
        
        # 检查名称
        if not tool_def.name or not tool_def.name.strip():
            errors.append("工具名称不能为空")
        
        # 检查描述
        if not tool_def.description or not tool_def.description.strip():
            errors.append("工具描述不能为空")
        
        # 检查参数定义
        if not isinstance(tool_def.parameters, dict):
            errors.append("参数定义必须是字典类型")
        
        # 检查源代码
        if not tool_def.source_code or not tool_def.source_code.strip():
            errors.append("源代码不能为空")
        
        return errors
    
    def generate_tool_documentation(self, tool_def: ToolDefinition) -> str:
        """
        生成工具文档
        
        Args:
            tool_def: 工具定义
            
        Returns:
            工具文档字符串
        """
        doc_lines = []
        
        doc_lines.append(f"# {tool_def.name}")
        doc_lines.append("")
        doc_lines.append(f"**描述**: {tool_def.description}")
        doc_lines.append("")
        doc_lines.append(f"**类别**: {tool_def.category.value}")
        doc_lines.append(f"**状态**: {tool_def.status.value}")
        doc_lines.append(f"**版本**: {tool_def.version}")
        doc_lines.append(f"**作者**: {tool_def.author}")
        doc_lines.append("")
        
        if tool_def.parameters:
            doc_lines.append("## 参数")
            doc_lines.append("")
            for param_name, param_info in tool_def.parameters.items():
                param_type = param_info.get('type', 'Any')
                param_default = param_info.get('default')
                param_required = param_info.get('required', True)
                
                default_str = f" (默认: {param_default})" if param_default is not None else ""
                required_str = " [必需]" if param_required else " [可选]"
                doc_lines.append(f"- `{param_name}`: {param_type}{default_str}{required_str}")
            doc_lines.append("")
        
        doc_lines.append(f"**返回类型**: {tool_def.return_type}")
        doc_lines.append("")
        
        if tool_def.dependencies:
            doc_lines.append("## 依赖项")
            doc_lines.append("")
            for dep in tool_def.dependencies:
                doc_lines.append(f"- `{dep}`")
            doc_lines.append("")
        
        if tool_def.tags:
            doc_lines.append("## 标签")
            doc_lines.append("")
            doc_lines.append(", ".join([f"`{tag}`" for tag in tool_def.tags]))
            doc_lines.append("")
        
        doc_lines.append("## 使用统计")
        doc_lines.append("")
        doc_lines.append(f"- 总使用次数: {tool_def.usage_count}")
        doc_lines.append(f"- 成功次数: {tool_def.success_count}")
        doc_lines.append(f"- 错误次数: {tool_def.error_count}")
        doc_lines.append("")
        
        doc_lines.append("## 源代码")
        doc_lines.append("```python")
        doc_lines.append(tool_def.source_code)
        doc_lines.append("```")
        
        return "\n".join(doc_lines)
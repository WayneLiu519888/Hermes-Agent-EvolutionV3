"""
增强版工具创建器模块
负责从多种来源创建工具：函数、代码、API描述、配置文件等
"""

import ast
import inspect
import textwrap
import json
import yaml
import re
import logging
from typing import Dict, Any, Callable, Optional, List, Union, Tuple

log = logging.getLogger("hermes_evo.tools")
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tool_registry import ToolDefinition, ToolRegistry, ToolCategory, ToolStatus


class CreationSource(Enum):
    """工具创建来源枚举"""
    FUNCTION = "function"  # 从函数创建
    CODE = "code"  # 从代码字符串创建
    API_DESCRIPTION = "api_description"  # 从API描述创建
    CONFIG = "config"  # 从配置文件创建
    TEMPLATE = "template"  # 从模板创建
    ADAPTIVE = "adaptive"  # 自适应创建


class ToolQuality(Enum):
    """工具质量等级"""
    EXCELLENT = "excellent"  # 优秀
    GOOD = "good"  # 良好
    FAIR = "fair"  # 一般
    POOR = "poor"  # 较差


@dataclass
class ToolCreationResult:
    """工具创建结果"""
    success: bool
    tool_definition: Optional[ToolDefinition] = None
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    quality_score: float = 0.0  # 质量评分 0-1
    quality_level: ToolQuality = ToolQuality.FAIR
    creation_source: CreationSource = CreationSource.FUNCTION
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.metadata is None:
            self.metadata = {}


@dataclass
class CodeAnalysisResult:
    """代码分析结果"""
    has_docstring: bool = False
    has_type_hints: bool = False
    has_error_handling: bool = False
    has_logging: bool = False
    complexity_score: float = 0.0  # 复杂度评分
    quality_score: float = 0.0  # 质量评分
    issues: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class EnhancedToolCreator:
    """增强版工具创建器"""
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        初始化增强版工具创建器
        
        Args:
            registry: 工具注册表实例，如果为None则创建新的
        """
        self.registry = registry or ToolRegistry()
        self.creation_history: List[ToolCreationResult] = []
        
    def create_from_function(self, func: Callable, 
                           name: Optional[str] = None,
                           description: Optional[str] = None,
                           category: ToolCategory = ToolCategory.UTILITY,
                           tags: Optional[List[str]] = None,
                           is_builtin: bool = False) -> ToolCreationResult:
        """
        从函数创建工具（增强版）
        
        Args:
            func: 函数对象
            name: 工具名称，如果为None则使用函数名
            description: 工具描述，如果为None则使用函数文档字符串
            category: 工具类别
            tags: 标签列表
            is_builtin: 是否为内置工具
            
        Returns:
            ToolCreationResult: 创建结果
        """
        try:
            # 分析函数质量
            analysis = self._analyze_function(func)
            
            # 获取函数信息
            func_name = name or func.__name__
            func_doc = description or (func.__doc__ or f"Function: {func_name}")
            
            # 提取参数信息
            sig = inspect.signature(func)
            parameters = {}
            for param_name, param in sig.parameters.items():
                param_info = {
                    "name": param_name,
                    "type": str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any",
                    "default": param.default if param.default != inspect.Parameter.empty else None,
                    "required": param.default == inspect.Parameter.empty
                }
                parameters[param_name] = param_info
            
            # 提取返回类型
            return_type = str(sig.return_annotation) if sig.return_annotation != inspect.Signature.empty else "Any"
            
            # 获取源代码
            source_code = inspect.getsource(func)
            
            # 创建工具定义
            tool_def = ToolDefinition(
                name=func_name,
                description=func_doc,
                category=category,
                status=ToolStatus.ACTIVE,
                version="1.0.0",
                author="system",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                usage_count=0,
                success_count=0,
                error_count=0,
                parameters=parameters,
                return_type=return_type,
                dependencies=self._extract_dependencies(source_code),
                tags=tags or [],
                source_code=source_code,
                is_builtin=is_builtin
            )
            
            # 计算质量评分
            quality_score = self._calculate_quality_score(analysis)
            quality_level = self._determine_quality_level(quality_score)
            
            # 注册工具
            self.registry.register(tool_def)
            
            result = ToolCreationResult(
                success=True,
                tool_definition=tool_def,
                quality_score=quality_score,
                quality_level=quality_level,
                creation_source=CreationSource.FUNCTION,
                metadata={
                    "analysis": analysis,
                    "function_name": func.__name__,
                    "module": func.__module__
                }
            )
            
            self.creation_history.append(result)
            return result
            
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"Failed to create tool from function: {str(e)}"
            )
    
    def create_from_code(self, code: str, name: str, description: str,
                        category: ToolCategory = ToolCategory.CUSTOM,
                        tags: Optional[List[str]] = None,
                        creation_source: CreationSource = CreationSource.CODE) -> ToolCreationResult:
        """
        从代码字符串创建工具
        
        Args:
            code: 代码字符串
            name: 工具名称
            description: 工具描述
            category: 工具类别
            tags: 标签列表
            
        Returns:
            ToolCreationResult: 创建结果
        """
        try:
            # 分析代码质量
            analysis = self._analyze_code(code)
            
            # 解析代码获取函数信息
            func_info = self._extract_function_info_from_code(code, name)
            
            # 创建工具定义
            tool_def = ToolDefinition(
                name=name,
                description=description,
                category=category,
                status=ToolStatus.EXPERIMENTAL,  # 代码创建的工具默认为实验性
                version="1.0.0",
                author="system",
                created_at=datetime.now(),
                updated_at=datetime.now(),
                usage_count=0,
                success_count=0,
                error_count=0,
                parameters=func_info.get("parameters", {}),
                return_type=func_info.get("return_type", "Any"),
                dependencies=self._extract_dependencies(code),
                tags=tags or [],
                source_code=code,
                is_builtin=False
            )
            
            # 计算质量评分
            quality_score = self._calculate_quality_score(analysis)
            quality_level = self._determine_quality_level(quality_score)
            
            # 注册工具
            self.registry.register(tool_def)
            
            result = ToolCreationResult(
                success=True,
                tool_definition=tool_def,
                quality_score=quality_score,
                quality_level=quality_level,
                creation_source=creation_source,
                metadata={
                    "analysis": analysis,
                    "code_length": len(code),
                    "lines_of_code": code.count('\n') + 1
                }
            )
            
            self.creation_history.append(result)
            return result
            
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"Failed to create tool from code: {str(e)}"
            )
    
    def create_from_api_description(self, api_spec: Dict[str, Any],
                                  name: str,
                                  category: ToolCategory = ToolCategory.UTILITY) -> ToolCreationResult:
        """
        从API描述创建工具
        
        Args:
            api_spec: API规范字典
            name: 工具名称
            category: 工具类别
            
        Returns:
            ToolCreationResult: 创建结果
        """
        try:
            # 从API规范生成代码
            generated_code = self._generate_code_from_api_spec(api_spec, name)
            
            # 创建工具
            return self.create_from_code(
                code=generated_code,
                name=name,
                description=api_spec.get("description", f"API工具: {name}"),
                category=category,
                tags=["api", "generated"] + api_spec.get("tags", [])
            )
            
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"Failed to create tool from API description: {str(e)}"
            )
    
    def create_from_config(self, config_path: str) -> ToolCreationResult:
        """
        从配置文件创建工具
        
        Args:
            config_path: 配置文件路径
            
        Returns:
            ToolCreationResult: 创建结果
        """
        try:
            with open(config_path, 'r') as f:
                if config_path.endswith('.json'):
                    config = json.load(f)
                elif config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    config = yaml.safe_load(f)
                else:
                    return ToolCreationResult(
                        success=False,
                        error_message=f"Unsupported config format: {config_path}"
                    )
            
            # 从配置创建工具
            if config.get("type") == "function":
                # 从配置加载函数：支持 module_path + function_name 或 inline_code
                func_config = config.get("function", {})
                if "module_path" in func_config and "function_name" in func_config:
                    # 动态导入模块中的函数
                    import importlib
                    mod = importlib.import_module(func_config["module_path"])
                    func = getattr(mod, func_config["function_name"])
                elif "code" in func_config:
                    # 从配置中的 Python 代码动态创建函数
                    local_ns = {}
                    exec(func_config["code"], {"log": log, "__builtins__": __builtins__}, local_ns)
                    func_name = config.get("name", func_config.get("function_name", "config_tool"))
                    func = local_ns.get(func_name)
                    if func is None:
                        func = list(local_ns.values())[0] if local_ns else None
                else:
                    return ToolCreationResult(
                        success=False,
                        error_message="函数配置缺少 module_path/function_name 或 code"
                    )
                if func is None:
                    return ToolCreationResult(
                        success=False,
                        error_message="无法从配置加载函数"
                    )
                return self.create_from_function(
                    func=func,
                    name=config.get("name", func_config.get("function_name", "config_tool")),
                    description=config.get("description", func.__doc__ or ""),
                    category=ToolCategory[config.get("category", "UTILITY")],
                    tags=config.get("tags", [])
                )
            elif config.get("type") == "code":
                return self.create_from_code(
                    code=config["code"],
                    name=config["name"],
                    description=config.get("description", ""),
                    category=ToolCategory[config.get("category", "UTILITY")],
                    tags=config.get("tags", [])
                )
            
            return ToolCreationResult(
                success=False,
                error_message="Unsupported config type"
            )
            
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"Failed to create tool from config: {str(e)}"
            )
    
    def create_from_template(self, template_name: str,
                           template_params: Dict[str, Any]) -> ToolCreationResult:
        """
        从模板创建工具
        
        Args:
            template_name: 模板名称
            template_params: 模板参数
            
        Returns:
            ToolCreationResult: 创建结果
        """
        try:
            # 获取模板
            template_code = self._get_template(template_name)
            
            # 替换模板参数
            for key, value in template_params.items():
                placeholder = f"{{{{{key}}}}}"
                template_code = template_code.replace(placeholder, str(value))
            
            # 创建工具
            return self.create_from_code(
                code=template_code,
                name=template_params.get("name", f"template_{template_name}"),
                description=template_params.get("description", f"Generated from template: {template_name}"),
                category=ToolCategory[template_params.get("category", "UTILITY")],
                tags=["template"] + template_params.get("tags", []),
                creation_source=CreationSource.TEMPLATE
            )
            
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"Failed to create tool from template: {str(e)}"
            )
    
    def adaptive_create(self, requirements: str,
                       context: Optional[Dict[str, Any]] = None) -> ToolCreationResult:
        """
        自适应创建工具（智能创建）
        
        Args:
            requirements: 需求描述
            context: 上下文信息
            
        Returns:
            ToolCreationResult: 创建结果
        """
        try:
            # 分析需求
            analysis = self._analyze_requirements(requirements, context)
            
            # 根据分析结果选择创建方式
            if analysis.get("has_existing_function"):
                # 如果有现有函数，使用函数创建
                pass
            elif analysis.get("can_use_template"):
                # 如果可以使用模板，使用模板创建
                pass
            else:
                # 否则生成代码
                generated_code = self._generate_code_from_requirements(requirements, context)
                
                return self.create_from_code(
                    code=generated_code,
                    name=analysis.get("suggested_name", "adaptive_tool"),
                    description=f"Adaptively created tool for: {requirements[:100]}...",
                    category=ToolCategory.CUSTOM,
                    tags=["adaptive", "generated"]
                )
            
            return ToolCreationResult(
                success=False,
                error_message="Adaptive creation not fully implemented"
            )
            
        except Exception as e:
            return ToolCreationResult(
                success=False,
                error_message=f"Failed to create tool adaptively: {str(e)}"
            )
    
    def get_creation_history(self, limit: int = 10) -> List[ToolCreationResult]:
        """
        获取创建历史
        
        Args:
            limit: 返回的最大记录数
            
        Returns:
            List[ToolCreationResult]: 创建历史
        """
        return self.creation_history[-limit:] if self.creation_history else []
    
    def get_creation_stats(self) -> Dict[str, Any]:
        """
        获取创建统计
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        if not self.creation_history:
            return {}
        
        total = len(self.creation_history)
        successful = sum(1 for r in self.creation_history if r.success)
        failed = total - successful
        
        # 按来源统计
        by_source = {}
        for result in self.creation_history:
            source = result.creation_source.value
            by_source[source] = by_source.get(source, 0) + 1
        
        # 按质量统计
        by_quality = {}
        for result in self.creation_history:
            if result.success:
                quality = result.quality_level.value
                by_quality[quality] = by_quality.get(quality, 0) + 1
        
        return {
            "total_creations": total,
            "successful_creations": successful,
            "failed_creations": failed,
            "success_rate": successful / total if total > 0 else 0,
            "by_source": by_source,
            "by_quality": by_quality,
            "average_quality_score": sum(r.quality_score for r in self.creation_history if r.success) / successful if successful > 0 else 0
        }
    
    # ========== 私有方法 ==========
    
    def _analyze_function(self, func: Callable) -> CodeAnalysisResult:
        """分析函数质量"""
        result = CodeAnalysisResult()
        
        try:
            # 获取源代码
            source = inspect.getsource(func)
            
            # 检查文档字符串
            result.has_docstring = bool(func.__doc__)
            
            # 检查类型提示
            sig = inspect.signature(func)
            result.has_type_hints = any(
                p.annotation != inspect.Parameter.empty 
                for p in sig.parameters.values()
            ) or sig.return_annotation != inspect.Signature.empty
            
            # 检查错误处理
            result.has_error_handling = "try:" in source or "except" in source
            
            # 检查日志
            result.has_logging = "logging" in source or "logger" in source or "print(" in source
            
            # 计算复杂度（简化版）
            result.complexity_score = min(1.0, source.count('if') * 0.1 + source.count('for') * 0.15 + source.count('while') * 0.2)
            
            # 计算质量评分
            quality_factors = []
            if result.has_docstring:
                quality_factors.append(0.2)
            if result.has_type_hints:
                quality_factors.append(0.2)
            if result.has_error_handling:
                quality_factors.append(0.3)
            if result.has_logging:
                quality_factors.append(0.1)
            quality_factors.append(1.0 - result.complexity_score * 0.2)  # 复杂度越低越好
            
            result.quality_score = sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
            
            # 生成建议
            if not result.has_docstring:
                result.suggestions.append("Add docstring to improve documentation")
            if not result.has_type_hints:
                result.suggestions.append("Add type hints for better code clarity")
            if not result.has_error_handling:
                result.suggestions.append("Consider adding error handling")
            
        except Exception as e:
            result.issues.append(f"Analysis error: {str(e)}")
        
        return result
    
    def _analyze_code(self, code: str) -> CodeAnalysisResult:
        """分析代码质量"""
        result = CodeAnalysisResult()
        
        try:
            # 检查文档字符串
            docstring_markers = ['"""', "'''"]
            result.has_docstring = any(marker in code for marker in docstring_markers)
            
            # 检查类型提示
            type_hint_indicators = ["->", ": str", ": int", ": float", ": bool", ": List", ": Dict", ": Optional"]
            result.has_type_hints = any(indicator in code for indicator in type_hint_indicators)
            
            # 检查错误处理
            result.has_error_handling = "try:" in code or "except" in code
            
            # 检查日志
            result.has_logging = "logging" in code or "logger" in code or "print(" in code
            
            # 计算复杂度（简化版）
            result.complexity_score = min(1.0, 
                code.count('if') * 0.1 + 
                code.count('for') * 0.15 + 
                code.count('while') * 0.2 +
                code.count('def ') * 0.05
            )
            
            # 计算质量评分
            quality_factors = []
            if result.has_docstring:
                quality_factors.append(0.2)
            if result.has_type_hints:
                quality_factors.append(0.2)
            if result.has_error_handling:
                quality_factors.append(0.3)
            if result.has_logging:
                quality_factors.append(0.1)
            quality_factors.append(1.0 - result.complexity_score * 0.2)  # 复杂度越低越好
            
            result.quality_score = sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
            
            # 尝试解析代码检查语法
            try:
                ast.parse(code)
            except SyntaxError as e:
                result.issues.append(f"Syntax error: {str(e)}")
                result.quality_score *= 0.5  # 语法错误严重降低质量
            
        except Exception as e:
            result.issues.append(f"Analysis error: {str(e)}")
        
        return result
    
    def _extract_function_info_from_code(self, code: str, expected_name: str) -> Dict[str, Any]:
        """从代码中提取函数信息"""
        try:
            tree = ast.parse(code)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # 找到函数定义
                    func_name = node.name
                    
                    # 提取参数
                    parameters = {}
                    for arg in node.args.args:
                        param_name = arg.arg
                        # 尝试获取类型提示
                        param_type = "Any"
                        if arg.annotation:
                            try:
                                param_type = ast.unparse(arg.annotation)
                            except AttributeError:
                                param_type = str(arg.annotation)
                        
                        parameters[param_name] = {
                            "name": param_name,
                            "type": param_type,
                            "required": True
                        }
                    
                    # 提取返回类型
                    return_type = "Any"
                    if node.returns:
                        try:
                            return_type = ast.unparse(node.returns)
                        except AttributeError:
                            return_type = str(node.returns)
                    
                    return {
                        "function_name": func_name,
                        "parameters": parameters,
                        "return_type": return_type
                    }
            
            # 如果没有找到函数定义，创建默认信息
            return {
                "function_name": expected_name,
                "parameters": {},
                "return_type": "Any"
            }
            
        except Exception:
            # 解析失败，返回默认信息
            return {
                "function_name": expected_name,
                "parameters": {},
                "return_type": "Any"
            }
    
    def _extract_dependencies(self, code: str) -> List[str]:
        """从代码中提取依赖"""
        dependencies = []
        
        # 检查常见导入
        import_patterns = [
            (r'import\s+(\w+)', 1),
            (r'from\s+(\w+)\s+import', 1),
            (r'import\s+(\w+)\.', 1)
        ]
        
        for pattern, group in import_patterns:
            matches = re.findall(pattern, code)
            dependencies.extend(matches)
        
        # 去重并排序
        return sorted(set(dependencies))
    
    def _calculate_quality_score(self, analysis: CodeAnalysisResult) -> float:
        """计算质量评分"""
        return analysis.quality_score
    
    def _determine_quality_level(self, score: float) -> ToolQuality:
        """根据评分确定质量等级"""
        if score >= 0.8:
            return ToolQuality.EXCELLENT
        elif score >= 0.6:
            return ToolQuality.GOOD
        elif score >= 0.4:
            return ToolQuality.FAIR
        else:
            return ToolQuality.POOR
    
    def _generate_code_from_api_spec(self, api_spec: Dict[str, Any], name: str) -> str:
        """从API规范生成代码"""
        # 简化实现，实际应该更复杂
        params = api_spec.get("parameters", [])
        param_strs = []
        for param in params:
            param_name = param.get("name", "param")
            param_type = param.get("type", "Any")
            param_strs.append(f"{param_name}: {param_type}")
        
        param_list = ", ".join(param_strs) if param_strs else ""
        
        code = f'''def {name}({param_list}):
    """
    {api_spec.get("description", "API工具")}
    
    Args:
'''
        
        # 添加参数文档
        for param in params:
            param_name = param.get("name", "param")
            param_desc = param.get("description", "")
            code += f"        {param_name}: {param_desc}\n"
        
        code += f'''    
    Returns:
        {api_spec.get("return_type", "Any")}: {api_spec.get("return_description", "")}
    """
    import urllib.request
    import urllib.error
    import json as _json
    
    url = "{api_spec.get("endpoint", "")}"
    method = "{api_spec.get("method", "GET")}"
    headers = {api_spec.get("headers", {"Content-Type": "application/json"})}
    
    try:
        data = None
        if params:
            data = _json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return _json.loads(body) if body else None
    except urllib.error.HTTPError as e:
        log.error("API请求失败 [%d]: %s", e.code, e.reason)
        return None
    except Exception as e:
        log.error("API调用异常: %s", e)
        return None
'''
        
        return code
    
    def _get_template(self, template_name: str) -> str:
        """获取模板代码"""
        templates = {
            "file_operation": '''
def {name}(file_path: str, content: Optional[str] = None) -> bool:
    """
    文件操作工具
    
    Args:
        file_path: 文件路径
        content: 要写入的内容（如果为None则读取文件）
    
    Returns:
        bool: 操作是否成功
    """
    import os
    
    try:
        if content is None:
            # 读取文件
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            # 写入文件
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
    except Exception as e:
        log.error("文件操作失败: %s", e)
        return False
''',
            "data_processing": '''
def {name}(data: List[Any], operation: str = "sum") -> Any:
    """
    数据处理工具
    
    Args:
        data: 数据列表
        operation: 操作类型（sum, avg, max, min）
    
    Returns:
        Any: 处理结果
    """
    if not data:
        return None
    
    try:
        if operation == "sum":
            return sum(data)
        elif operation == "avg":
            return sum(data) / len(data)
        elif operation == "max":
            return max(data)
        elif operation == "min":
            return min(data)
        else:
            raise ValueError(f"不支持的操作: {{operation}}")
    except Exception as e:
        log.error("数据处理失败: %s", e)
        return None
''',
            "http_request": '''
def {name}(url: str, method: str = "GET", data: Optional[Dict] = None, 
          headers: Optional[Dict] = None) -> Optional[Dict]:
    """
    HTTP请求工具
    
    Args:
        url: 请求URL
        method: HTTP方法（GET, POST, PUT, DELETE）
        data: 请求数据
        headers: 请求头
    
    Returns:
        Optional[Dict]: 响应数据
    """
    import requests
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        elif method.upper() == "PUT":
            response = requests.put(url, json=data, headers=headers)
        elif method.upper() == "DELETE":
            response = requests.delete(url, headers=headers)
        else:
            raise ValueError(f"不支持的HTTP方法: {{method}}")
        
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log.error("HTTP请求失败: %s", e)
        return None
'''
        }
        
        return templates.get(template_name, '''\
def {name}(*args, **kwargs):
    """工具 {name} — 自动生成的通用工具

    Args:
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        处理结果
    """
    log.info("工具 %s 被调用: args=%s kwargs=%s", "{name}", args, kwargs)
    # 通用工具实现 — 尝试对参数进行基本处理
    if args and all(isinstance(a, (int, float)) for a in args):
        return sum(args)
    if kwargs:
        return kwargs
    return args[0] if len(args) == 1 else args if args else None
''')
    
    def _analyze_requirements(self, requirements: str, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """分析需求"""
        # 简化实现
        analysis = {
            "has_existing_function": False,
            "can_use_template": False,
            "suggested_name": self._generate_name_from_requirements(requirements),
            "complexity": "medium"
        }
        
        # 检查是否可以使用模板
        template_keywords = {
            "file": "file_operation",
            "数据": "data_processing",
            "http": "http_request",
            "请求": "http_request",
            "网络": "http_request"
        }
        
        for keyword, template in template_keywords.items():
            if keyword in requirements.lower():
                analysis["can_use_template"] = True
                analysis["suggested_template"] = template
                break
        
        return analysis
    
    def _generate_code_from_requirements(self, requirements: str, context: Optional[Dict[str, Any]]) -> str:
        """从需求生成代码"""
        # 简化实现
        name = self._generate_name_from_requirements(requirements)
        
        code = f'''def {name}():
    """
    根据需求生成的工具: {requirements[:50]}...
    """
    # 这是一个根据需求自动生成的工具
    # 需求: {requirements}
    
    log.info("工具已生成，但需要手动实现功能")
    return None
'''
        
        return code
    
    def _generate_name_from_requirements(self, requirements: str) -> str:
        """从需求生成工具名称"""
        # 提取关键词作为名称基础
        words = re.findall(r'\b\w+\b', requirements.lower())
        common_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by"}
        keywords = [w for w in words if w not in common_words and len(w) > 2]
        
        if keywords:
            # 使用前两个关键词
            name_parts = keywords[:2]
            name = "_".join(name_parts)
        else:
            # 使用默认名称
            name = "generated_tool"
        
        # 确保名称是有效的Python标识符
        name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
        if not name[0].isalpha():
            name = "tool_" + name
        
        return name


# 兼容性包装器，保持原有API
ToolCreator = EnhancedToolCreator
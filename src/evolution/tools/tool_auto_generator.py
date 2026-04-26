"""
工具自动生成模块
基于需求描述自动生成完整的工具代码
"""

import ast
import re
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .tool_registry import ToolDefinition, ToolRegistry, ToolCategory, ToolStatus


class GenerationStrategy(Enum):
    """生成策略枚举"""
    SIMPLE = "simple"  # 简单生成
    TEMPLATE = "template"  # 模板生成
    COMPOSITE = "composite"  # 组合生成
    ADAPTIVE = "adaptive"  # 自适应生成


@dataclass
class ToolGenerationResult:
    """工具生成结果"""
    success: bool
    tool_name: str = ""
    tool_code: str = ""
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)
    strategy: GenerationStrategy = GenerationStrategy.SIMPLE
    generation_time: float = 0.0
    estimated_quality: float = 0.0  # 0-1
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolAutoGenerator:
    """工具自动生成器"""
    
    # 内置工具模板库
    TEMPLATES = {
        "file_reader": {
            "name": "file_reader",
            "description": "读取文件内容",
            "category": ToolCategory.FILE_OPERATION,
            "tags": ["file", "read"],
            "code": '''def file_reader(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        encoding: 文件编码
    
    Returns:
        Optional[str]: 文件内容，失败返回None
    """
    import os
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception as e:
        print(f"读取文件失败: {e}")
        return None
'''
        },
        "file_writer": {
            "name": "file_writer",
            "description": "写入文件内容",
            "category": ToolCategory.FILE_OPERATION,
            "tags": ["file", "write"],
            "code": '''def file_writer(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    写入文件内容
    
    Args:
        file_path: 文件路径
        content: 写入内容
        encoding: 文件编码
    
    Returns:
        bool: 是否成功
    """
    import os
    
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception as e:
        print(f"写入文件失败: {e}")
        return False
'''
        },
        "data_filter": {
            "name": "data_filter",
            "description": "过滤数据列表",
            "category": ToolCategory.DATA_PROCESSING,
            "tags": ["data", "filter"],
            "code": '''def data_filter(data: List[Any], predicate: str = "lambda x: x") -> List[Any]:
    """
    过滤数据列表
    
    Args:
        data: 数据列表
        predicate: 过滤谓词（lambda表达式字符串）
    
    Returns:
        List[Any]: 过滤后的数据
    """
    if not data:
        return []
    
    try:
        pred = eval(predicate)
        return [item for item in data if pred(item)]
    except Exception as e:
        print(f"数据过滤失败: {e}")
        return data
'''
        },
        "data_transform": {
            "name": "data_transform",
            "description": "转换数据格式",
            "category": ToolCategory.DATA_PROCESSING,
            "tags": ["data", "transform"],
            "code": '''def data_transform(data: List[Dict], 
                       field_mapping: Dict[str, str],
                       drop_missing: bool = False) -> List[Dict]:
    """
    转换数据格式（字段映射）
    
    Args:
        data: 原始数据列表
        field_mapping: 字段映射 {新字段名: 原字段名}
        drop_missing: 是否丢弃缺失字段的记录
    
    Returns:
        List[Dict]: 转换后的数据
    """
    result = []
    for record in data:
        new_record = {}
        has_missing = False
        
        for new_key, old_key in field_mapping.items():
            if old_key in record:
                new_record[new_key] = record[old_key]
            else:
                has_missing = True
                if not drop_missing:
                    new_record[new_key] = None
        
        if not has_missing or not drop_missing:
            result.append(new_record)
    
    return result
'''
        },
        "http_get": {
            "name": "http_get",
            "description": "发送HTTP GET请求",
            "category": ToolCategory.NETWORK,
            "tags": ["http", "get", "network"],
            "code": '''def http_get(url: str, params: Optional[Dict] = None,
              headers: Optional[Dict] = None,
              timeout: int = 30) -> Optional[Dict]:
    """
    发送HTTP GET请求
    
    Args:
        url: 请求URL
        params: 查询参数
        headers: 请求头
        timeout: 超时时间（秒）
    
    Returns:
        Optional[Dict]: 响应JSON数据
    """
    import requests
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"请求超时: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
'''
        },
        "http_post": {
            "name": "http_post",
            "description": "发送HTTP POST请求",
            "category": ToolCategory.NETWORK,
            "tags": ["http", "post", "network"],
            "code": '''def http_post(url: str, data: Optional[Dict] = None,
               json_data: Optional[Dict] = None,
               headers: Optional[Dict] = None,
               timeout: int = 30) -> Optional[Dict]:
    """
    发送HTTP POST请求
    
    Args:
        url: 请求URL
        data: 表单数据
        json_data: JSON数据
        headers: 请求头
        timeout: 超时时间（秒）
    
    Returns:
        Optional[Dict]: 响应JSON数据
    """
    import requests
    
    try:
        response = requests.post(url, data=data, json=json_data, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print(f"请求超时: {url}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"请求失败: {e}")
        return None
'''
        },
        "text_search": {
            "name": "text_search",
            "description": "搜索文本内容",
            "category": ToolCategory.UTILITY,
            "tags": ["text", "search"],
            "code": '''def text_search(text: str, pattern: str,
               case_sensitive: bool = False) -> List[Dict]:
    """
    搜索文本内容
    
    Args:
        text: 要搜索的文本
        pattern: 搜索模式（支持正则）
        case_sensitive: 是否区分大小写
    
    Returns:
        List[Dict]: 匹配结果列表 [{匹配位置, 匹配内容}]
    """
    import re
    
    flags = 0 if case_sensitive else re.IGNORECASE
    
    try:
        matches = []
        for match in re.finditer(pattern, text, flags):
            matches.append({
                "start": match.start(),
                "end": match.end(),
                "content": match.group()
            })
        return matches
    except re.error as e:
        print(f"正则表达式错误: {e}")
        return []
'''
        },
        "json_validator": {
            "name": "json_validator",
            "description": "验证JSON数据",
            "category": ToolCategory.UTILITY,
            "tags": ["json", "validate"],
            "code": '''def json_validator(data: str, schema: Optional[Dict] = None) -> Dict:
    """
    验证JSON数据
    
    Args:
        data: JSON字符串
        schema: JSON Schema（可选）
    
    Returns:
        Dict: {is_valid: bool, parsed_data: Any, errors: List[str]}
    """
    import json
    
    result = {
        "is_valid": False,
        "parsed_data": None,
        "errors": []
    }
    
    try:
        parsed = json.loads(data)
        result["parsed_data"] = parsed
        result["is_valid"] = True
    except json.JSONDecodeError as e:
        result["errors"].append(f"JSON解析错误: {e}")
        return result
    
    if schema:
        try:
            import jsonschema
            jsonschema.validate(parsed, schema)
        except ImportError:
            result["errors"].append("jsonschema库未安装")
            result["is_valid"] = False
        except jsonschema.exceptions.ValidationError as e:
            result["errors"].append(f"Schema验证失败: {e}")
            result["is_valid"] = False
    
    return result
'''
        },
        "csv_reader": {
            "name": "csv_reader",
            "description": "读取CSV文件",
            "category": ToolCategory.DATA_PROCESSING,
            "tags": ["csv", "file", "data"],
            "code": '''def csv_reader(file_path: str, 
                delimiter: str = ",",
                has_header: bool = True) -> Optional[List[Dict]]:
    """
    读取CSV文件
    
    Args:
        file_path: CSV文件路径
        delimiter: 分隔符
        has_header: 是否有表头
    
    Returns:
        Optional[List[Dict]]: 数据列表
    """
    import csv
    import os
    
    if not os.path.exists(file_path):
        print(f"文件不存在: {file_path}")
        return None
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if has_header:
                reader = csv.DictReader(f, delimiter=delimiter)
                return list(reader)
            else:
                reader = csv.reader(f, delimiter=delimiter)
                rows = list(reader)
                if rows:
                    # 用列索引作为字段名
                    headers = [f"col_{i}" for i in range(len(rows[0]))]
                    return [dict(zip(headers, row)) for row in rows]
                return []
    except Exception as e:
        print(f"读取CSV失败: {e}")
        return None
'''
        }
    }
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        """
        初始化工具自动生成器
        
        Args:
            registry: 工具注册表实例
        """
        self.registry = registry
        self.generation_history: List[ToolGenerationResult] = []
        
    def generate_from_requirement(self, requirement: str) -> ToolGenerationResult:
        """
        根据需求描述生成工具
        
        Args:
            requirement: 需求描述
            
        Returns:
            ToolGenerationResult: 生成结果
        """
        start_time = __import__('time').time()
        
        try:
            # 分析需求
            analysis = self._analyze_requirement(requirement)
            
            if not analysis["matched"]:
                return ToolGenerationResult(
                    success=False,
                    tool_name="",
                    error_message=f"无法匹配到合适的工具模板: {requirement}",
                    strategy=GenerationStrategy.SIMPLE
                )
            
            # 检查是否需要组合生成
            if len(analysis.get("template_names", [])) > 1:
                return self._composite_generate(analysis, requirement)
            
            # 使用最佳匹配模板
            template_name = analysis["template_names"][0]
            template = self.TEMPLATES[template_name]
            
            result = ToolGenerationResult(
                success=True,
                tool_name=template["name"],
                tool_code=template["code"],
                strategy=GenerationStrategy.TEMPLATE,
                generation_time=__import__('time').time() - start_time,
                estimated_quality=analysis.get("confidence", 0.8),
                warnings=analysis.get("warnings", []),
                metadata={
                    "template_name": template_name,
                    "requirement": requirement,
                    "analysis": analysis
                }
            )
            
            self.generation_history.append(result)
            
            # 注册工具
            if self.registry:
                self._register_generated_tool(result, analysis)
            
            return result
            
        except Exception as e:
            return ToolGenerationResult(
                success=False,
                tool_name="",
                error_message=f"生成工具失败: {str(e)}",
                strategy=GenerationStrategy.SIMPLE
            )
    
    def generate_composite_workflow(self, requirements: List[str]) -> ToolGenerationResult:
        """
        组合多个工具生成工作流
        
        Args:
            requirements: 多个需求描述
            
        Returns:
            ToolGenerationResult: 生成结果
        """
        start_time = __import__('time').time()
        combined_code = ""
        combined_warnings = []
        tool_names = []
        
        for i, req in enumerate(requirements):
            result = self.generate_from_requirement(req)
            if result.success:
                # 重命名函数以避免冲突
                code = result.tool_code
                for original_name in tool_names:
                    code = code.replace(f"def {original_name}(", f"def {result.tool_name}_{i}(")
                
                combined_code += f"\n# Generated from: {req}\n{code}\n"
                tool_names.append(result.tool_name)
            else:
                combined_warnings.append(f"需求 '{req}' 生成失败: {result.error_message}")
        
        if not tool_names:
            return ToolGenerationResult(
                success=False,
                error_message="所有需求生成均失败",
                strategy=GenerationStrategy.COMPOSITE
            )
        
        # 创建组合工作流函数
        workflow_name = f"workflow_{'_'.join(tool_names[:3])}"
        # 构建工作流代码（不能使用f-string，因为包含反斜杠）
        workflow_lines = []
        workflow_lines.append(f'def {workflow_name}(**kwargs):')
        workflow_lines.append('    """')
        workflow_lines.append('    组合工作流（自动生成）')
        workflow_lines.append('')
        workflow_lines.append(f'    包含工具: {", ".join(tool_names)}')
        workflow_lines.append('    """')
        workflow_lines.append('    results = {}')
        workflow_lines.append('    # 按顺序执行每个工具')
        for name in tool_names[:5]:
            workflow_lines.append(f'    if "{name}" in kwargs:')
            workflow_lines.append(f'        args = kwargs["{name}_args"] if "{name}_args" in kwargs else {{}}')
            workflow_lines.append(f'        results["{name}"] = {name}(**args)')
        workflow_lines.append('    return results')
        workflow_code = '\n'.join(workflow_lines) + '\n\n' + combined_code
        
        result = ToolGenerationResult(
            success=True,
            tool_name=workflow_name,
            tool_code=workflow_code,
            strategy=GenerationStrategy.COMPOSITE,
            generation_time=__import__('time').time() - start_time,
            estimated_quality=0.7 if not combined_warnings else 0.5,
            warnings=combined_warnings,
            metadata={
                "requirements": requirements,
                "generated_tools": tool_names,
                "workflow_name": workflow_name
            }
        )
        
        self.generation_history.append(result)
        return result
    
    def list_available_templates(self) -> List[Dict[str, Any]]:
        """
        列出可用的生成模板
        
        Returns:
            List[Dict]: 模板列表
        """
        templates = []
        for name, template in self.TEMPLATES.items():
            templates.append({
                "name": name,
                "description": template["description"],
                "category": template["category"].value,
                "tags": template["tags"]
            })
        return templates
    
    def get_generation_history(self, limit: int = 10) -> List[ToolGenerationResult]:
        """
        获取生成历史
        
        Args:
            limit: 返回的最大记录数
            
        Returns:
            List[ToolGenerationResult]: 生成历史
        """
        return self.generation_history[-limit:] if self.generation_history else []
    
    def add_custom_template(self, name: str, description: str, 
                           category: ToolCategory, code: str,
                           tags: Optional[List[str]] = None) -> bool:
        """
        添加自定义模板
        
        Args:
            name: 模板名称
            description: 模板描述
            category: 工具类别
            code: 模板代码
            tags: 标签列表
            
        Returns:
            bool: 是否添加成功
        """
        try:
            # 验证代码语法
            ast.parse(code)
            
            self.TEMPLATES[name] = {
                "name": name,
                "description": description,
                "category": category,
                "tags": tags or [],
                "code": code
            }
            return True
        except SyntaxError as e:
            print(f"模板代码语法错误: {e}")
            return False
        except Exception as e:
            print(f"添加模板失败: {e}")
            return False
    
    # ========== 私有方法 ==========
    
    def _analyze_requirement(self, requirement: str) -> Dict[str, Any]:
        """分析需求，匹配最佳模板"""
        req_lower = requirement.lower()
        result = {
            "matched": False,
            "template_names": [],
            "confidence": 0.0,
            "warnings": [],
            "complexity": "low"
        }
        
        # 关键词匹配规则
        keyword_rules = {
            "file_reader": ["读取文件", "读文件", "文件内容", "read file", "file content", "打开文件"],
            "file_writer": ["写入文件", "写文件", "保存文件", "write file", "save file", "创建文件"],
            "data_filter": ["过滤数据", "筛选数据", "数据过滤", "filter data", "筛选条件"],
            "data_transform": ["转换数据", "数据转换", "字段映射", "transform", "数据格式"],
            "http_get": ["获取数据", "下载数据", "获取远程", "http get", "get请求", "请求数据", "拉取数据"],
            "http_post": ["提交数据", "发送数据", "http post", "post请求", "上传数据"],
            "text_search": ["搜索文本", "查找文本", "文本搜索", "正则", "search text"],
            "json_validator": ["验证json", "json验证", "解析json", "json解析", "validate json"],
            "csv_reader": ["读取csv", "csv文件", "解析csv", "read csv", "csv reader"]
        }
        
        # 计算匹配分数
        matches = []
        for template_name, keywords in keyword_rules.items():
            match_count = sum(1 for kw in keywords if kw in req_lower)
            if match_count > 0:
                confidence = match_count / len(keywords)
                matches.append((template_name, confidence))
        
        if matches:
            # 按置信度排序
            matches.sort(key=lambda x: x[1], reverse=True)
            result["matched"] = True
            result["template_names"] = [m[0] for m in matches[:3]]
            result["confidence"] = matches[0][1]
            
            # 判断复杂度
            if len(matches) > 2:
                result["complexity"] = "medium"
            if len(matches) > 4:
                result["complexity"] = "high"
        
        else:
            result["warnings"].append("未找到完全匹配的模板，尝试模糊匹配")
            
            # 模糊匹配
            for template_name, keywords in keyword_rules.items():
                # 检查是否有部分关键词匹配
                partial_matches = sum(1 for kw in keywords if any(word in req_lower for word in kw.split()))
                if partial_matches > 0:
                    result["matched"] = True
                    result["template_names"].append(template_name)
                    result["confidence"] = 0.3
            
            if not result["matched"]:
                result["warnings"].append("未找到任何匹配的模板，请明确描述需求")
        
        return result
    
    def _composite_generate(self, analysis: Dict[str, Any], requirement: str) -> ToolGenerationResult:
        """组合生成：使用多个模板生成复合工具"""
        start_time = __import__('time').time()
        template_names = analysis["template_names"][:3]  # 最多3个
        
        combined_code = ""
        combined_warnings = list(analysis.get("warnings", []))
        tool_names = []
        
        for i, tname in enumerate(template_names):
            template = self.TEMPLATES.get(tname)
            if template:
                code = template["code"]
                # 重命名避免冲突
                if i > 0:
                    old_func = template["name"]
                    new_func = f"{old_func}_{i}"
                    code = code.replace(f"def {old_func}(", f"def {new_func}(")
                    tool_names.append(new_func)
                else:
                    tool_names.append(template["name"])
                
                combined_code += code + "\n"
        
        # 创建主函数
        main_func_name = "composite_tool"
        combined_code += f'''
def {main_func_name}(**kwargs):
    """
    复合工具（自动生成）
    
    包含功能: {', '.join(template_names)}
    """
    results = {{}}
    errors = []
    
    for tool_name, tool_fn in [
{chr(10).join([f'        ("{tn}", {tn}),' for tn in tool_names])}
    ]:
        try:
            if tool_name in kwargs:
                results[tool_name] = tool_fn(**kwargs[tool_name])
            else:
                results[tool_name] = tool_fn()
        except Exception as e:
            errors.append(f"{{tool_name}} 执行失败: {{e}}")
            results[tool_name] = None
    
    return {{
        "results": results,
        "errors": errors,
        "success": len(errors) == 0
    }}
'''
        
        result = ToolGenerationResult(
            success=True,
            tool_name=main_func_name,
            tool_code=combined_code,
            strategy=GenerationStrategy.COMPOSITE,
            generation_time=__import__('time').time() - start_time,
            estimated_quality=0.7,
            warnings=combined_warnings,
            metadata={
                "template_names": template_names,
                "generated_tools": tool_names,
                "main_function": main_func_name,
                "requirement": requirement,
                "analysis": analysis
            }
        )
        
        self.generation_history.append(result)
        
        if self.registry:
            self._register_generated_tool(result, analysis)
        
        return result
    
    def _register_generated_tool(self, result: ToolGenerationResult, analysis: Dict[str, Any]):
        """注册生成的工具到注册表"""
        try:
            from .enhanced_tool_creator import EnhancedToolCreator
            creator = EnhancedToolCreator(self.registry)
            
            # 从代码创建
            category_str = analysis.get("category", "UTILITY")
            try:
                category = ToolCategory[category_str]
            except (KeyError, ValueError):
                category = ToolCategory.CUSTOM
            
            creator.create_from_code(
                code=result.tool_code,
                name=result.tool_name,
                description=f"Auto-generated tool: {analysis.get('requirement', '')}",
                category=category,
                tags=["auto_generated"]
            )
        except Exception as e:
            result.warnings.append(f"注册到工具表失败: {e}")

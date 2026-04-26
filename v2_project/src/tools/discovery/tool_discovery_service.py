"""
工具发现模块 - 动态发现和注册工具
支持自动扫描、元数据提取、分类和索引
"""

import os
import sys
import importlib
import inspect
import logging
from typing import Dict, Any, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime
from pathlib import Path
import hashlib

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """工具类别"""
    DATA_PROCESSING = "data_processing"
    FILE_OPERATIONS = "file_operations"
    NETWORK = "network"
    DATABASE = "database"
    ML_AI = "ml_ai"
    UTILITIES = "utilities"
    CUSTOM = "custom"


class ToolType(Enum):
    """工具类型"""
    FUNCTION = "function"
    CLASS = "class"
    MODULE = "module"
    SCRIPT = "script"
    API = "api"


@dataclass
class ToolParameter:
    """工具参数"""
    name: str
    type: str
    description: str = ""
    required: bool = False
    default: Any = None
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.type,
            "description": self.description,
            "required": self.required,
            "default": self.default,
            "constraints": self.constraints
        }


@dataclass
class ToolMetadata:
    """工具元数据"""
    tool_id: str
    name: str
    description: str
    tool_type: ToolType
    category: ToolCategory
    source_module: str
    source_path: str
    function_signature: Optional[str] = None
    parameters: List[ToolParameter] = field(default_factory=list)
    return_type: Optional[str] = None
    return_description: str = ""
    examples: List[Dict[str, Any]] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    version: str = "1.0.0"
    author: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    last_updated: datetime = field(default_factory=datetime.now)
    usage_count: int = 0
    success_rate: float = 0.0
    avg_execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "tool_type": self.tool_type.value,
            "category": self.category.value,
            "source_module": self.source_module,
            "source_path": self.source_path,
            "function_signature": self.function_signature,
            "parameters": [p.to_dict() for p in self.parameters],
            "return_type": self.return_type,
            "return_description": self.return_description,
            "examples": self.examples,
            "tags": self.tags,
            "version": self.version,
            "author": self.author,
            "created_at": self.created_at.isoformat(),
            "last_updated": self.last_updated.isoformat(),
            "usage_count": self.usage_count,
            "success_rate": self.success_rate,
            "avg_execution_time": self.avg_execution_time,
            "metadata": self.metadata
        }
    
    def update_usage_stats(self, success: bool, execution_time: float) -> None:
        """更新使用统计"""
        self.usage_count += 1
        self.last_updated = datetime.now()
        
        # 更新成功率
        if self.usage_count == 1:
            self.success_rate = 1.0 if success else 0.0
        else:
            total_success = self.success_rate * (self.usage_count - 1)
            total_success += 1 if success else 0
            self.success_rate = total_success / self.usage_count
        
        # 更新平均执行时间
        if self.usage_count == 1:
            self.avg_execution_time = execution_time
        else:
            total_time = self.avg_execution_time * (self.usage_count - 1)
            total_time += execution_time
            self.avg_execution_time = total_time / self.usage_count


class ToolScanner:
    """工具扫描器"""
    
    def __init__(self, scan_paths: List[str] = None):
        self.scan_paths = scan_paths or ["."]
        self.discovered_tools: Dict[str, ToolMetadata] = {}
        self.scan_history = []
        
        logger.info(f"工具扫描器初始化完成，扫描路径: {self.scan_paths}")
    
    def scan_directory(self, directory: str, recursive: bool = True) -> List[ToolMetadata]:
        """扫描目录中的工具"""
        tools = []
        dir_path = Path(directory)
        
        if not dir_path.exists():
            logger.warning(f"目录不存在: {directory}")
            return tools
        
        # 扫描Python文件
        pattern = "**/*.py" if recursive else "*.py"
        
        for py_file in dir_path.glob(pattern):
            if self._should_skip_file(py_file):
                continue
            
            try:
                file_tools = self._scan_python_file(py_file)
                tools.extend(file_tools)
            except Exception as e:
                logger.error(f"扫描文件失败 {py_file}: {e}")
        
        # 记录扫描历史
        scan_record = {
            "directory": directory,
            "timestamp": datetime.now().isoformat(),
            "tools_found": len(tools),
            "recursive": recursive
        }
        self.scan_history.append(scan_record)
        
        logger.info(f"扫描目录 {directory} 完成，发现 {len(tools)} 个工具")
        return tools
    
    def _should_skip_file(self, file_path: Path) -> bool:
        """判断是否应该跳过文件"""
        # 跳过测试文件
        if "test_" in file_path.name or "_test.py" in file_path.name:
            return True
        
        # 跳过隐藏文件和特殊目录
        if file_path.name.startswith(".") or file_path.name.startswith("_"):
            return True
        
        # 跳过某些目录
        skip_dirs = {"__pycache__", "venv", ".venv", "env", ".env", "node_modules"}
        for part in file_path.parts:
            if part in skip_dirs:
                return True
        
        return False
    
    def _scan_python_file(self, file_path: Path) -> List[ToolMetadata]:
        """扫描Python文件"""
        tools = []
        
        try:
            # 将文件路径转换为模块路径
            module_path = self._file_to_module_path(file_path)
            
            # 动态导入模块
            spec = importlib.util.spec_from_file_location(module_path, file_path)
            if spec is None or spec.loader is None:
                return tools
            
            module = importlib.util.module_from_spec(spec)
            sys.modules[module_path] = module
            
            try:
                spec.loader.exec_module(module)
            except Exception as e:
                logger.debug(f"模块导入失败 {module_path}: {e}")
                return tools
            
            # 扫描模块中的函数和类
            for name, obj in inspect.getmembers(module):
                if self._is_potential_tool(obj):
                    try:
                        tool_metadata = self._extract_tool_metadata(obj, name, module_path, str(file_path))
                        if tool_metadata:
                            tools.append(tool_metadata)
                    except Exception as e:
                        logger.error(f"提取工具元数据失败 {name}: {e}")
            
        except Exception as e:
            logger.error(f"扫描Python文件失败 {file_path}: {e}")
        
        return tools
    
    def _file_to_module_path(self, file_path: Path) -> str:
        """将文件路径转换为模块路径"""
        # 移除.py扩展名
        module_path = file_path.with_suffix('')
        
        # 将路径分隔符转换为点
        module_str = str(module_path).replace(os.sep, '.')
        
        # 清理路径
        if module_str.startswith('.'):
            module_str = module_str[1:]
        
        return module_str
    
    def _is_potential_tool(self, obj) -> bool:
        """判断对象是否可能是工具"""
        # 检查是否是函数或方法
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            # 跳过私有方法和特殊方法
            name = obj.__name__
            if name.startswith('_') and not name.startswith('__'):
                return False
            if name.startswith('__') and name.endswith('__'):
                return False
            
            # 检查是否有文档字符串
            if inspect.getdoc(obj):
                return True
            
            # 检查是否有参数注解
            sig = inspect.signature(obj)
            if any(param.annotation != inspect.Parameter.empty for param in sig.parameters.values()):
                return True
            
            return False
        
        # 检查是否是类
        elif inspect.isclass(obj):
            # 跳过私有类
            name = obj.__name__
            if name.startswith('_'):
                return False
            
            # 检查是否有文档字符串
            if inspect.getdoc(obj):
                return True
            
            # 检查是否有公共方法
            for method_name, method in inspect.getmembers(obj, predicate=inspect.isfunction):
                if not method_name.startswith('_'):
                    return True
            
            return False
        
        return False
    
    def _extract_tool_metadata(
        self,
        obj,
        name: str,
        module_path: str,
        source_path: str
    ) -> Optional[ToolMetadata]:
        """提取工具元数据"""
        import uuid
        
        # 生成工具ID
        tool_id = f"{module_path}.{name}_{str(uuid.uuid4())[:8]}"
        
        # 获取文档字符串
        docstring = inspect.getdoc(obj) or ""
        
        # 解析文档字符串
        description = self._extract_description(docstring)
        
        # 推断类别
        category = self._infer_category(name, description, module_path)
        
        # 推断工具类型
        if inspect.isfunction(obj) or inspect.ismethod(obj):
            tool_type = ToolType.FUNCTION
            function_signature = str(inspect.signature(obj))
        elif inspect.isclass(obj):
            tool_type = ToolType.CLASS
            function_signature = None
        else:
            tool_type = ToolType.MODULE
            function_signature = None
        
        # 提取参数信息
        parameters = []
        if tool_type == ToolType.FUNCTION:
            sig = inspect.signature(obj)
            for param_name, param in sig.parameters.items():
                param_type = str(param.annotation) if param.annotation != inspect.Parameter.empty else "Any"
                
                param_desc = self._extract_param_description(docstring, param_name)
                
                tool_param = ToolParameter(
                    name=param_name,
                    type=param_type,
                    description=param_desc,
                    required=param.default == inspect.Parameter.empty,
                    default=param.default if param.default != inspect.Parameter.empty else None
                )
                parameters.append(tool_param)
        
        # 提取返回类型
        return_type = None
        return_description = ""
        if tool_type == ToolType.FUNCTION:
            sig = inspect.signature(obj)
            if sig.return_annotation != inspect.Parameter.empty:
                return_type = str(sig.return_annotation)
            
            return_description = self._extract_return_description(docstring)
        
        # 提取示例
        examples = self._extract_examples(docstring)
        
        # 提取标签
        tags = self._extract_tags(name, description, category)
        
        # 创建工具元数据
        tool_metadata = ToolMetadata(
            tool_id=tool_id,
            name=name,
            description=description,
            tool_type=tool_type,
            category=category,
            source_module=module_path,
            source_path=source_path,
            function_signature=function_signature,
            parameters=parameters,
            return_type=return_type,
            return_description=return_description,
            examples=examples,
            tags=tags,
            version="1.0.0",
            author=self._extract_author(docstring),
            metadata={
                "docstring": docstring[:500] if docstring else "",  # 截断长文档字符串
                "line_number": inspect.getsourcelines(obj)[1] if hasattr(obj, '__code__') else None
            }
        )
        
        return tool_metadata
    
    def _extract_description(self, docstring: str) -> str:
        """从文档字符串提取描述"""
        if not docstring:
            return ""
        
        # 提取第一段非空行作为描述
        lines = docstring.strip().split('\n')
        description_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                break
            description_lines.append(line)
        
        return ' '.join(description_lines)
    
    def _extract_param_description(self, docstring: str, param_name: str) -> str:
        """提取参数描述"""
        if not docstring:
            return ""
        
        # 简单解析：查找 :param param_name: 格式
        lines = docstring.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith(f":param {param_name}:") or line.startswith(f":param {param_name} "):
                # 提取描述
                desc_start = line.find(':', line.find(param_name)) + 1
                description = line[desc_start:].strip()
                
                # 检查是否有续行
                for next_line in lines[i+1:]:
                    next_line = next_line.strip()
                    if next_line and not next_line.startswith(':'):
                        description += ' ' + next_line
                    else:
                        break
                
                return description
        
        return ""
    
    def _extract_return_description(self, docstring: str) -> str:
        """提取返回描述"""
        if not docstring:
            return ""
        
        lines = docstring.split('\n')
        for i, line in enumerate(lines):
            line = line.strip()
            if line.startswith(":return:") or line.startswith(":returns:"):
                # 提取描述
                desc_start = line.find(':') + 1
                description = line[desc_start:].strip()
                
                # 检查是否有续行
                for next_line in lines[i+1:]:
                    next_line = next_line.strip()
                    if next_line and not next_line.startswith(':'):
                        description += ' ' + next_line
                    else:
                        break
                
                return description
        
        return ""
    
    def _extract_examples(self, docstring: str) -> List[Dict[str, Any]]:
        """提取示例"""
        examples = []
        
        if not docstring:
            return examples
        
        lines = docstring.split('\n')
        in_example = False
        example_lines = []
        example_title = ""
        
        for line in lines:
            line = line.strip()
            
            if line.lower().startswith("example") or line.lower().startswith("examples:"):
                in_example = True
                example_title = line
                example_lines = []
            elif in_example and line and not line.startswith(':'):
                example_lines.append(line)
            elif in_example and (not line or line.startswith(':')):
                # 示例结束
                if example_lines:
                    examples.append({
                        "title": example_title,
                        "code": '\n'.join(example_lines)
                    })
                in_example = False
                example_lines = []
        
        # 处理最后一个示例
        if example_lines:
            examples.append({
                "title": example_title,
                "code": '\n'.join(example_lines)
            })
        
        return examples
    
    def _extract_tags(self, name: str, description: str, category: ToolCategory) -> List[str]:
        """提取标签"""
        tags = []
        
        # 添加类别标签
        tags.append(category.value)
        
        # 从名称提取标签
        name_parts = name.lower().split('_')
        tags.extend([p for p in name_parts if len(p) > 2])
        
        # 从描述提取关键词
        keywords = ["process", "analyze", "generate", "create", "update", "delete", 
                   "read", "write", "transform", "validate", "check", "verify"]
        
        desc_lower = description.lower()
        for keyword in keywords:
            if keyword in desc_lower:
                tags.append(keyword)
        
        # 去重
        tags = list(set(tags))
        
        return tags
    
    def _extract_author(self, docstring: str) -> str:
        """提取作者"""
        if not docstring:
            return ""
        
        lines = docstring.split('\n')
        for line in lines:
            line = line.strip().lower()
            if line.startswith("author:") or line.startswith("by:") or line.startswith("created by:"):
                parts = line.split(':', 1)
                if len(parts) > 1:
                    return parts[1].strip()
        
        return ""
    
    def _infer_category(self, name: str, description: str, module_path: str) -> ToolCategory:
        """推断类别"""
        name_lower = name.lower()
        desc_lower = description.lower()
        module_lower = module_path.lower()
        
        # 检查模块路径
        if any(keyword in module_lower for keyword in ["data", "process", "transform"]):
            return ToolCategory.DATA_PROCESSING
        elif any(keyword in module_lower for keyword in ["file", "io", "read", "write"]):
            return ToolCategory.FILE_OPERATIONS
        elif any(keyword in module_lower for keyword in ["network", "http", "api", "web"]):
            return ToolCategory.NETWORK
        elif any(keyword in module_lower for keyword in ["db", "database", "sql"]):
            return ToolCategory.DATABASE
        elif any(keyword in module_lower for keyword in ["ml", "ai", "model", "learn"]):
            return ToolCategory.ML_AI
        
        # 检查名称和描述
        if any(keyword in name_lower or keyword in desc_lower for keyword in ["file", "read", "write", "save", "load"]):
            return ToolCategory.FILE_OPERATIONS
        elif any(keyword in name_lower or keyword in desc_lower for keyword in ["data", "process", "transform", "clean"]):
            return ToolCategory.DATA_PROCESSING
        elif any(keyword in name_lower or keyword in desc_lower for keyword in ["http", "request", "api", "fetch"]):
            return ToolCategory.NETWORK
        elif any(keyword in name_lower or keyword in desc_lower for keyword in ["db", "sql", "query", "database"]):
            return ToolCategory.DATABASE
        elif any(keyword in name_lower or keyword in desc_lower for keyword in ["model", "train", "predict", "ai", "ml"]):
            return ToolCategory.ML_AI
        
        return ToolCategory.UTILITIES
    
    def scan_all(self) -> List[ToolMetadata]:
        """扫描所有配置的路径"""
        all_tools = []
        
        for scan_path in self.scan_paths:
            tools = self.scan_directory(scan_path, recursive=True)
            all_tools.extend(tools)
            
            # 添加到发现工具字典
            for tool in tools:
                self.discovered_tools[tool.tool_id] = tool
        
        logger.info(f"扫描完成，总共发现 {len(all_tools)} 个工具")
        return all_tools
    
    def get_tool_by_id(self, tool_id: str) -> Optional[ToolMetadata]:
        """根据ID获取工具"""
        return self.discovered_tools.get(tool_id)
    
    def search_tools(
        self,
        query: str = None,
        category: ToolCategory = None,
        tags: List[str] = None,
        min_success_rate: float = 0.0
    ) -> List[ToolMetadata]:
        """搜索工具"""
        results = list(self.discovered_tools.values())
        
        # 按查询过滤
        if query:
            query_lower = query.lower()
            results = [
                tool for tool in results
                if (query_lower in tool.name.lower() or
                    query_lower in tool.description.lower() or
                    any(query_lower in tag.lower() for tag in tool.tags))
            ]
        
        # 按类别过滤
        if category:
            results = [tool for tool in results if tool.category == category]
        
        # 按标签过滤
        if tags:
            results = [
                tool for tool in results
                if any(tag.lower() in [t.lower() for t in tool.tags] for tag in tags)
            ]
        
        # 按成功率过滤
        if min_success_rate > 0:
            results = [tool for tool in results if tool.success_rate >= min_success_rate]
        
        # 按使用次数排序（更常用的工具排前面）
        results.sort(key=lambda x: x.usage_count, reverse=True)
        
        return results
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        categories = {}
        for tool in self.discovered_tools.values():
            cat = tool.category.value
            categories[cat] = categories.get(cat, 0) + 1
        
        total_tools = len(self.discovered_tools)
        avg_success_rate = sum(tool.success_rate for tool in self.discovered_tools.values()) / total_tools if total_tools > 0 else 0
        
        return {
            "total_tools": total_tools,
            "categories": categories,
            "average_success_rate": avg_success_rate,
            "total_scans": len(self.scan_history),
            "last_scan": self.scan_history[-1] if self.scan_history else None
        }


class ToolDiscoveryService:
    """工具发现服务"""
    
    def __init__(self):
        self.scanner = ToolScanner()
        self.auto_scan_interval = 300  # 5分钟
        self.last_scan_time = None
        
        logger.info("工具发现服务初始化完成")
    
    async def scan_for_tools(self, scan_paths: List[str] = None) -> Dict[str, Any]:
        """扫描工具"""
        try:
            if scan_paths:
                self.scanner.scan_paths = scan_paths
            
            tools = self.scanner.scan_all()
            self.last_scan_time = datetime.now()
            
            stats = self.scanner.get_stats()
            
            return {
                "success": True,
                "tools_found": len(tools),
                "tools": [tool.to_dict() for tool in tools],
                "stats": stats,
                "scan_time": self.last_scan_time.isoformat()
            }
            
        except Exception as e:
            logger.error(f"工具扫描失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def search_tools(
        self,
        query: str = None,
        category: str = None,
        tags: List[str] = None,
        min_success_rate: float = 0.0,
        limit: int = 50
    ) -> Dict[str, Any]:
        """搜索工具"""
        try:
            # 转换类别
            category_enum = None
            if category:
                try:
                    category_enum = ToolCategory(category)
                except ValueError:
                    logger.warning(f"未知的类别: {category}")
            
            # 执行搜索
            tools = self.scanner.search_tools(
                query=query,
                category=category_enum,
                tags=tags,
                min_success_rate=min_success_rate
            )
            
            # 限制结果数量
            tools = tools[:limit]
            
            return {
                "success": True,
                "total_found": len(tools),
                "tools": [tool.to_dict() for tool in tools]
            }
            
        except Exception as e:
            logger.error(f"工具搜索失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_tool_details(self, tool_id: str) -> Dict[str, Any]:
        """获取工具详情"""
        try:
            tool = self.scanner.get_tool_by_id(tool_id)
            
            if not tool:
                return {
                    "success": False,
                    "error": f"工具不存在: {tool_id}"
                }
            
            return {
                "success": True,
                "tool": tool.to_dict()
            }
            
        except Exception as e:
            logger.error(f"获取工具详情失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_tool_stats(
        self,
        tool_id: str,
        success: bool,
        execution_time: float
    ) -> Dict[str, Any]:
        """更新工具统计"""
        try:
            tool = self.scanner.get_tool_by_id(tool_id)
            
            if not tool:
                return {
                    "success": False,
                    "error": f"工具不存在: {tool_id}"
                }
            
            tool.update_usage_stats(success, execution_time)
            
            return {
                "success": True,
                "updated_tool": tool.to_dict()
            }
            
        except Exception as e:
            logger.error(f"更新工具统计失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_discovery_stats(self) -> Dict[str, Any]:
        """获取发现统计"""
        try:
            stats = self.scanner.get_stats()
            
            return {
                "success": True,
                "stats": stats,
                "last_scan_time": self.last_scan_time.isoformat() if self.last_scan_time else None,
                "auto_scan_interval": self.auto_scan_interval
            }
            
        except Exception as e:
            logger.error(f"获取发现统计失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# 全局工具发现服务实例
tool_discovery_service = ToolDiscoveryService()
"""
工具组合模块 - 智能组合多个工具完成任务
支持工作流定义、依赖解析、并行执行、错误处理
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
import json
from datetime import datetime
import networkx as nx
from concurrent.futures import ThreadPoolExecutor
import uuid

logger = logging.getLogger(__name__)


class ToolCompositionType(Enum):
    """工具组合类型"""
    SEQUENTIAL = "sequential"      # 顺序执行
    PARALLEL = "parallel"          # 并行执行
    CONDITIONAL = "conditional"    # 条件执行
    LOOP = "loop"                  # 循环执行
    WORKFLOW = "workflow"          # 工作流


class ToolCompositionStatus(Enum):
    """工具组合状态"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ToolNode:
    """工具节点"""
    node_id: str
    tool_id: str
    tool_name: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    input_mapping: Dict[str, str] = field(default_factory=dict)  # 输入映射：参数名 -> 上游输出路径
    output_mapping: Dict[str, str] = field(default_factory=dict)  # 输出映射：工具输出 -> 节点输出
    condition: Optional[str] = None  # 执行条件
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "node_id": self.node_id,
            "tool_id": self.tool_id,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "input_mapping": self.input_mapping,
            "output_mapping": self.output_mapping,
            "condition": self.condition,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "metadata": self.metadata
        }


@dataclass
class ToolEdge:
    """工具边（依赖关系）"""
    source_node_id: str
    target_node_id: str
    data_mapping: Dict[str, str] = field(default_factory=dict)  # 数据映射：源输出 -> 目标输入
    condition: Optional[str] = None  # 边条件
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "data_mapping": self.data_mapping,
            "condition": self.condition,
            "metadata": self.metadata
        }


@dataclass
class CompositionResult:
    """组合执行结果"""
    composition_id: str
    status: ToolCompositionStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    node_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # 节点ID -> 执行结果
    final_output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_graph: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "composition_id": self.composition_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "node_results": self.node_results,
            "final_output": self.final_output,
            "error": self.error,
            "execution_graph": self.execution_graph,
            "metadata": self.metadata
        }


class ToolComposition:
    """工具组合"""
    
    def __init__(
        self,
        composition_id: str,
        name: str,
        description: str = "",
        composition_type: ToolCompositionType = ToolCompositionType.WORKFLOW
    ):
        self.composition_id = composition_id
        self.name = name
        self.description = description
        self.composition_type = composition_type
        
        self.nodes: Dict[str, ToolNode] = {}
        self.edges: List[ToolEdge] = []
        self.graph = nx.DiGraph()
        
        self.input_schema: Dict[str, Any] = {}
        self.output_schema: Dict[str, Any] = {}
        
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        
        self.execution_count = 0
        self.success_count = 0
        self.avg_execution_time = 0.0
        
        logger.debug(f"工具组合创建: {name} ({composition_id})")
    
    def add_node(self, node: ToolNode) -> bool:
        """添加节点"""
        if node.node_id in self.nodes:
            logger.warning(f"节点已存在: {node.node_id}")
            return False
        
        self.nodes[node.node_id] = node
        self.graph.add_node(node.node_id, node=node)
        
        self.updated_at = datetime.now()
        return True
    
    def add_edge(self, edge: ToolEdge) -> bool:
        """添加边"""
        # 检查节点是否存在
        if edge.source_node_id not in self.nodes:
            logger.error(f"源节点不存在: {edge.source_node_id}")
            return False
        
        if edge.target_node_id not in self.nodes:
            logger.error(f"目标节点不存在: {edge.target_node_id}")
            return False
        
        # 检查是否形成环
        self.graph.add_edge(edge.source_node_id, edge.target_node_id, edge=edge)
        
        try:
            # 检查是否有环
            if not nx.is_directed_acyclic_graph(self.graph):
                self.graph.remove_edge(edge.source_node_id, edge.target_node_id)
                logger.error(f"添加边会形成环: {edge.source_node_id} -> {edge.target_node_id}")
                return False
        except Exception as e:
            self.graph.remove_edge(edge.source_node_id, edge.target_node_id)
            logger.error(f"图检查失败: {e}")
            return False
        
        self.edges.append(edge)
        self.updated_at = datetime.now()
        return True
    
    def remove_node(self, node_id: str) -> bool:
        """移除节点"""
        if node_id not in self.nodes:
            return False
        
        # 移除相关边
        edges_to_remove = [
            edge for edge in self.edges 
            if edge.source_node_id == node_id or edge.target_node_id == node_id
        ]
        
        for edge in edges_to_remove:
            self.edges.remove(edge)
            if self.graph.has_edge(edge.source_node_id, edge.target_node_id):
                self.graph.remove_edge(edge.source_node_id, edge.target_node_id)
        
        # 移除节点
        del self.nodes[node_id]
        self.graph.remove_node(node_id)
        
        self.updated_at = datetime.now()
        return True
    
    def remove_edge(self, source_node_id: str, target_node_id: str) -> bool:
        """移除边"""
        edge_to_remove = None
        
        for edge in self.edges:
            if edge.source_node_id == source_node_id and edge.target_node_id == target_node_id:
                edge_to_remove = edge
                break
        
        if edge_to_remove:
            self.edges.remove(edge_to_remove)
            if self.graph.has_edge(source_node_id, target_node_id):
                self.graph.remove_edge(source_node_id, target_node_id)
            
            self.updated_at = datetime.now()
            return True
        
        return False
    
    def get_execution_order(self) -> List[List[str]]:
        """获取执行顺序（拓扑排序）"""
        try:
            if not nx.is_directed_acyclic_graph(self.graph):
                logger.error("图包含环，无法计算执行顺序")
                return []
            
            # 获取拓扑排序
            topological_order = list(nx.topological_sort(self.graph))
            
            # 分组：同一层级的节点可以并行执行
            levels = {}
            for node in topological_order:
                # 计算节点的层级（最长路径长度）
                if self.graph.in_degree(node) == 0:
                    levels[node] = 0
                else:
                    predecessors = list(self.graph.predecessors(node))
                    levels[node] = max(levels[p] for p in predecessors) + 1
            
            # 按层级分组
            level_groups = {}
            for node, level in levels.items():
                if level not in level_groups:
                    level_groups[level] = []
                level_groups[level].append(node)
            
            # 转换为列表
            execution_order = [level_groups[level] for level in sorted(level_groups.keys())]
            
            return execution_order
            
        except Exception as e:
            logger.error(f"计算执行顺序失败: {e}")
            return []
    
    def validate(self) -> Tuple[bool, List[str]]:
        """验证组合"""
        errors = []
        
        # 检查图是否有环
        try:
            if not nx.is_directed_acyclic_graph(self.graph):
                errors.append("组合包含环")
        except Exception as e:
            errors.append(f"图验证失败: {e}")
        
        # 检查节点
        for node_id, node in self.nodes.items():
            if not node.tool_id:
                errors.append(f"节点 {node_id} 缺少工具ID")
            
            # 检查输入映射
            for input_param, source_path in node.input_mapping.items():
                if not source_path:
                    errors.append(f"节点 {node_id} 输入映射 {input_param} 为空")
        
        # 检查边
        for edge in self.edges:
            if edge.source_node_id not in self.nodes:
                errors.append(f"边引用不存在的源节点: {edge.source_node_id}")
            if edge.target_node_id not in self.nodes:
                errors.append(f"边引用不存在的目标节点: {edge.target_node_id}")
        
        # 检查孤立节点
        for node_id in self.nodes:
            if self.graph.in_degree(node_id) == 0 and self.graph.out_degree(node_id) == 0:
                errors.append(f"孤立节点: {node_id}")
        
        return len(errors) == 0, errors
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        execution_order = self.get_execution_order()
        
        return {
            "composition_id": self.composition_id,
            "name": self.name,
            "description": self.description,
            "composition_type": self.composition_type.value,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "edges": [edge.to_dict() for edge in self.edges],
            "execution_order": execution_order,
            "input_schema": self.input_schema,
            "output_schema": self.output_schema,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "execution_count": self.execution_count,
            "success_count": self.success_count,
            "avg_execution_time": self.avg_execution_time
        }
    
    def update_stats(self, success: bool, execution_time: float) -> None:
        """更新统计信息"""
        self.execution_count += 1
        
        if success:
            self.success_count += 1
        
        # 更新平均执行时间
        if self.execution_count == 1:
            self.avg_execution_time = execution_time
        else:
            total_time = self.avg_execution_time * (self.execution_count - 1)
            total_time += execution_time
            self.avg_execution_time = total_time / self.execution_time


class ToolExecutor:
    """工具执行器"""
    
    def __init__(self, max_workers: int = 10):
        self.max_workers = max_workers
        self.thread_pool = ThreadPoolExecutor(max_workers=max_workers)
        
        # 工具执行函数映射
        self.tool_executors: Dict[str, Callable] = {}
        
        logger.info(f"工具执行器初始化完成，最大工作线程: {max_workers}")
    
    def register_tool_executor(self, tool_id: str, executor: Callable) -> None:
        """注册工具执行器"""
        self.tool_executors[tool_id] = executor
        logger.debug(f"工具执行器已注册: {tool_id}")
    
    async def execute_tool(
        self,
        tool_id: str,
        parameters: Dict[str, Any],
        timeout: Optional[float] = None
    ) -> Tuple[bool, Any, float, Optional[str]]:
        """执行单个工具"""
        start_time = datetime.now()
        
        try:
            # 获取执行器
            executor = self.tool_executors.get(tool_id)
            if not executor:
                error_msg = f"未找到工具执行器: {tool_id}"
                logger.error(error_msg)
                return False, None, 0.0, error_msg
            
            # 执行工具
            if timeout:
                # 带超时的执行
                try:
                    result = await asyncio.wait_for(
                        self._run_in_threadpool(executor, parameters),
                        timeout=timeout
                    )
                except asyncio.TimeoutError:
                    error_msg = f"工具执行超时: {tool_id}, 超时时间: {timeout}秒"
                    logger.error(error_msg)
                    execution_time = (datetime.now() - start_time).total_seconds()
                    return False, None, execution_time, error_msg
            else:
                # 无超时执行
                result = await self._run_in_threadpool(executor, parameters)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            logger.debug(f"工具执行成功: {tool_id}, 时间: {execution_time:.2f}秒")
            return True, result, execution_time, None
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            error_msg = f"工具执行失败: {tool_id}, 错误: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, execution_time, error_msg
    
    async def _run_in_threadpool(self, func: Callable, args: Dict[str, Any]) -> Any:
        """在线程池中运行函数"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(self.thread_pool, lambda: func(**args))
    
    def shutdown(self) -> None:
        """关闭执行器"""
        self.thread_pool.shutdown(wait=True)
        logger.info("工具执行器已关闭")


class ToolCompositionEngine:
    """工具组合引擎"""
    
    def __init__(self):
        self.compositions: Dict[str, ToolComposition] = {}
        self.executor = ToolExecutor()
        self.active_executions: Dict[str, asyncio.Task] = {}
        
        logger.info("工具组合引擎初始化完成")
    
    def create_composition(
        self,
        name: str,
        description: str = "",
        composition_type: str = "workflow"
    ) -> Optional[ToolComposition]:
        """创建组合"""
        try:
            composition_id = str(uuid.uuid4())
            type_enum = ToolCompositionType(composition_type)
            
            composition = ToolComposition(
                composition_id=composition_id,
                name=name,
                description=description,
                composition_type=type_enum
            )
            
            self.compositions[composition_id] = composition
            logger.info(f"工具组合创建成功: {name} ({composition_id})")
            
            return composition
            
        except ValueError as e:
            logger.error(f"无效的组合类型: {composition_type}")
            return None
        except Exception as e:
            logger.error(f"创建组合失败: {e}")
            return None
    
    def get_composition(self, composition_id: str) -> Optional[ToolComposition]:
        """获取组合"""
        return self.compositions.get(composition_id)
    
    def delete_composition(self, composition_id: str) -> bool:
        """删除组合"""
        if composition_id not in self.compositions:
            return False
        
        del self.compositions[composition_id]
        logger.info(f"工具组合已删除: {composition_id}")
        return True
    
    async def execute_composition(
        self,
        composition_id: str,
        input_data: Dict[str, Any] = None,
        timeout: float = None
    ) -> CompositionResult:
        """执行组合"""
        composition = self.get_composition(composition_id)
        if not composition:
            error_msg = f"组合不存在: {composition_id}"
            logger.error(error_msg)
            return CompositionResult(
                composition_id=composition_id,
                status=ToolCompositionStatus.FAILED,
                start_time=datetime.now(),
                error=error_msg
            )
        
        # 验证组合
        is_valid, errors = composition.validate()
        if not is_valid:
            error_msg = f"组合验证失败: {', '.join(errors)}"
            logger.error(error_msg)
            return CompositionResult(
                composition_id=composition_id,
                status=ToolCompositionStatus.FAILED,
                start_time=datetime.now(),
                error=error_msg
            )
        
        # 创建执行结果
        result = CompositionResult(
            composition_id=composition_id,
            status=ToolCompositionStatus.RUNNING,
            start_time=datetime.now(),
            execution_graph=composition.to_dict()
        )
        
        try:
            # 获取执行顺序
            execution_order = composition.get_execution_order()
            if not execution_order:
                error_msg = "无法计算执行顺序"
                logger.error(error_msg)
                result.status = ToolCompositionStatus.FAILED
                result.error = error_msg
                result.end_time = datetime.now()
                return result
            
            # 执行上下文
            execution_context = {"input": input_data or {}}
            node_outputs = {}
            
            # 按层级执行
            for level, node_ids in enumerate(execution_order):
                logger.info(f"执行层级 {level}: {node_ids}")
                
                # 准备本层节点的任务
                tasks = []
                for node_id in node_ids:
                    node = composition.nodes[node_id]
                    
                    # 准备参数
                    parameters = self._prepare_node_parameters(
                        node, execution_context, node_outputs
                    )
                    
                    # 检查条件
                    if node.condition:
                        if not self._evaluate_condition(node.condition, execution_context):
                            logger.info(f"节点 {node_id} 条件不满足，跳过执行")
                            node_outputs[node_id] = {"skipped": True, "reason": "condition_not_met"}
                            continue
                    
                    # 创建执行任务
                    task = self._execute_node_with_retry(node, parameters, timeout)
                    tasks.append((node_id, task))
                
                # 并行执行本层节点
                if tasks:
                    node_tasks = {node_id: task for node_id, task in tasks}
                    
                    # 等待所有节点完成
                    completed = await asyncio.gather(
                        *[task for _, task in tasks],
                        return_exceptions=True
                    )
                    
                    # 处理结果
                    for (node_id, _), node_result in zip(tasks, completed):
                        if isinstance(node_result, Exception):
                            # 执行失败
                            error_msg = f"节点 {node_id} 执行失败: {str(node_result)}"
                            logger.error(error_msg)
                            
                            node_outputs[node_id] = {
                                "success": False,
                                "error": str(node_result),
                                "execution_time": 0.0
                            }
                            
                            # 记录节点结果
                            result.node_results[node_id] = node_outputs[node_id]
                            
                            # 组合执行失败
                            result.status = ToolCompositionStatus.FAILED
                            result.error = error_msg
                            result.end_time = datetime.now()
                            
                            # 更新组合统计
                            execution_time = (result.end_time - result.start_time).total_seconds()
                            composition.update_stats(False, execution_time)
                            
                            return result
                        else:
                            # 执行成功
                            success, output, exec_time, error = node_result
                            
                            node_outputs[node_id] = {
                                "success": success,
                                "output": output,
                                "error": error,
                                "execution_time": exec_time
                            }
                            
                            # 记录节点结果
                            result.node_results[node_id] = node_outputs[node_id]
                            
                            # 更新执行上下文
                            if success and output is not None:
                                execution_context[node_id] = output
                
                # 检查是否有节点失败
                failed_nodes = [
                    node_id for node_id in node_ids
                    if node_id in node_outputs and not node_outputs[node_id].get("success", True)
                ]
                
                if failed_nodes:
                    error_msg = f"层级 {level} 节点执行失败: {failed_nodes}"
                    logger.error(error_msg)
                    
                    result.status = ToolCompositionStatus.FAILED
                    result.error = error_msg
                    result.end_time = datetime.now()
                    
                    # 更新组合统计
                    execution_time = (result.end_time - result.start_time).total_seconds()
                    composition.update_stats(False, execution_time)
                    
                    return result
            
            # 所有节点执行成功
            result.status = ToolCompositionStatus.COMPLETED
            result.end_time = datetime.now()
            
            # 构建最终输出
            final_output = self._build_final_output(composition, node_outputs)
            result.final_output = final_output
            
            # 更新组合统计
            execution_time = (result.end_time - result.start_time).total_seconds()
            composition.update_stats(True, execution_time)
            
            logger.info(f"组合执行成功: {composition_id}, 总时间: {execution_time:.2f}秒")
            
            return result
            
        except Exception as e:
            error_msg = f"组合执行异常: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            result.status = ToolCompositionStatus.FAILED
            result.error = error_msg
            result.end_time = datetime.now()
            
            # 更新组合统计
            execution_time = (result.end_time - result.start_time).total_seconds()
            composition.update_stats(False, execution_time)
            
            return result
    
    def _prepare_node_parameters(
        self,
        node: ToolNode,
        execution_context: Dict[str, Any],
        node_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """准备节点参数"""
        parameters = node.parameters.copy()
        
        # 应用输入映射
        for param_name, source_path in node.input_mapping.items():
            if source_path:
                # 解析源路径，例如: "node1.output.data" 或 "input.data"
                value = self._resolve_source_path(source_path, execution_context, node_outputs)
                if value is not None:
                    parameters[param_name] = value
        
        return parameters
    
    def _resolve_source_path(
        self,
        source_path: str,
        execution_context: Dict[str, Any],
        node_outputs: Dict[str, Any]
    ) -> Any:
        """解析源路径"""
        try:
            # 分割路径
            parts = source_path.split('.')
            
            # 检查是否是输入
            if parts[0] == "input":
                current = execution_context.get("input", {})
                for part in parts[1:]:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                return current
            
            # 检查是否是其他节点的输出
            elif parts[0] in node_outputs:
                node_output = node_outputs[parts[0]]
                if not node_output.get("success", False):
                    return None
                
                current = node_output.get("output", {})
                for part in parts[1:]:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                return current
            
            # 检查执行上下文
            elif parts[0] in execution_context:
                current = execution_context[parts[0]]
                for part in parts[1:]:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return None
                return current
            
            return None
            
        except Exception:
            return None
    
    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> bool:
        """评估条件"""
        try:
            # 简单条件评估：检查变量是否存在且为真
            # 实际实现可以使用更复杂的表达式引擎
            if condition.startswith("${") and condition.endswith("}"):
                var_name = condition[2:-1]
                value = self._resolve_source_path(var_name, context, {})
                return bool(value)
            else:
                # 直接作为Python表达式评估（简化实现）
                # 注意：实际生产环境应该使用安全的表达式引擎
                return bool(eval(condition, {"__builtins__": {}}, context))
        except Exception:
            return False
    
    async def _execute_node_with_retry(
        self,
        node: ToolNode,
        parameters: Dict[str, Any],
        global_timeout: Optional[float] = None
    ) -> Tuple[bool, Any, float, Optional[str]]:
        """带重试的节点执行"""
        retry_count = 0
        last_error = None
        
        while retry_count <= node.max_retries:
            try:
                # 使用节点超时或全局超时
                timeout = node.timeout or global_timeout
                
                success, output, exec_time, error = await self.executor.execute_tool(
                    node.tool_id,
                    parameters,
                    timeout=timeout
                )
                
                if success:
                    return success, output, exec_time, error
                else:
                    last_error = error
                    retry_count += 1
                    
                    if retry_count <= node.max_retries:
                        logger.warning(f"节点 {node.node_id} 执行失败，重试 {retry_count}/{node.max_retries}: {error}")
                        await asyncio.sleep(1)  # 重试前等待
                    else:
                        logger.error(f"节点 {node.node_id} 执行失败，达到最大重试次数: {error}")
                        return False, None, exec_time, error
                        
            except Exception as e:
                last_error = str(e)
                retry_count += 1
                
                if retry_count <= node.max_retries:
                    logger.warning(f"节点 {node.node_id} 执行异常，重试 {retry_count}/{node.max_retries}: {e}")
                    await asyncio.sleep(1)
                else:
                    logger.error(f"节点 {node.node_id} 执行异常，达到最大重试次数: {e}")
                    return False, None, 0.0, str(e)
        
        return False, None, 0.0, last_error
    
    def _build_final_output(
        self,
        composition: ToolComposition,
        node_outputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        """构建最终输出"""
        final_output = {}
        
        # 收集所有成功节点的输出
        for node_id, node_result in node_outputs.items():
            if node_result.get("success", False) and node_result.get("output") is not None:
                node = composition.nodes[node_id]
                
                # 应用输出映射
                if node.output_mapping:
                    for output_key, source_path in node.output_mapping.items():
                        value = self._resolve_source_path(
                            source_path,
                            {"input": {}},
                            {node_id: node_result}
                        )
                        if value is not None:
                            final_output[output_key] = value
                else:
                    # 如果没有输出映射，使用节点ID作为键
                    final_output[node_id] = node_result["output"]
        
        return final_output
    
    def get_composition_stats(self, composition_id: str) -> Optional[Dict[str, Any]]:
        """获取组合统计"""
        composition = self.get_composition(composition_id)
        if not composition:
            return None
        
        return {
            "composition_id": composition_id,
            "name": composition.name,
            "execution_count": composition.execution_count,
            "success_count": composition.success_count,
            "success_rate": composition.success_count / composition.execution_count if composition.execution_count > 0 else 0,
            "avg_execution_time": composition.avg_execution_time,
            "node_count": len(composition.nodes),
            "edge_count": len(composition.edges),
            "last_updated": composition.updated_at.isoformat()
        }
    
    def shutdown(self) -> None:
        """关闭引擎"""
        self.executor.shutdown()
        logger.info("工具组合引擎已关闭")


class ToolCompositionService:
    """工具组合服务"""
    
    def __init__(self):
        self.engine = ToolCompositionEngine()
        
        logger.info("工具组合服务初始化完成")
    
    async def create_composition(
        self,
        name: str,
        description: str = "",
        composition_type: str = "workflow"
    ) -> Dict[str, Any]:
        """创建组合"""
        try:
            composition = self.engine.create_composition(name, description, composition_type)
            
            if not composition:
                return {
                    "success": False,
                    "error": "创建组合失败"
                }
            
            return {
                "success": True,
                "composition": composition.to_dict()
            }
            
        except Exception as e:
            logger.error(f"创建组合失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def execute_composition(
        self,
        composition_id: str,
        input_data: Dict[str, Any] = None,
        timeout: float = None
    ) -> Dict[str, Any]:
        """执行组合"""
        try:
            result = await self.engine.execute_composition(composition_id, input_data, timeout)
            
            return {
                "success": result.status == ToolCompositionStatus.COMPLETED,
                "result": result.to_dict()
            }
            
        except Exception as e:
            logger.error(f"执行组合失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_composition_details(self, composition_id: str) -> Dict[str, Any]:
        """获取组合详情"""
        try:
            composition = self.engine.get_composition(composition_id)
            
            if not composition:
                return {
                    "success": False,
                    "error": f"组合不存在: {composition_id}"
                }
            
            return {
                "success": True,
                "composition": composition.to_dict()
            }
            
        except Exception as e:
            logger.error(f"获取组合详情失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_composition_stats(self, composition_id: str) -> Dict[str, Any]:
        """获取组合统计"""
        try:
            stats = self.engine.get_composition_stats(composition_id)
            
            if not stats:
                return {
                    "success": False,
                    "error": f"组合不存在: {composition_id}"
                }
            
            return {
                "success": True,
                "stats": stats
            }
            
        except Exception as e:
            logger.error(f"获取组合统计失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def list_compositions(self, limit: int = 50) -> Dict[str, Any]:
        """列出组合"""
        try:
            compositions = list(self.engine.compositions.values())
            compositions.sort(key=lambda x: x.updated_at, reverse=True)
            
            return {
                "success": True,
                "compositions": [comp.to_dict() for comp in compositions[:limit]],
                "total": len(compositions)
            }
            
        except Exception as e:
            logger.error(f"列出组合失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


# 全局工具组合服务实例
tool_composition_service = ToolCompositionService()
"""
多Agent编排引擎 - 工作流定义与执行

支持串行/并行步骤组合的工作流编排，集成TaskDispatcher进行任务分发，
集成MessageBus进行Agent间通信。
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .agent_registry import AgentRegistry
from .task_dispatcher import Task, TaskDispatcher, TaskPriority, TaskStatus
from .message_bus import CollaborationMessageBus, MessageType, MessagePriority

logger = logging.getLogger(__name__)


class StepType(Enum):
    """步骤类型"""
    SERIAL = "serial"       # 串行执行
    PARALLEL = "parallel"   # 并行执行
    CONDITIONAL = "conditional"  # 条件分支
    BROADCAST = "broadcast"  # 广播步骤


class WorkflowStatus(Enum):
    """工作流状态"""
    DRAFT = "draft"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowStep:
    """工作流步骤定义"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    step_type: StepType = StepType.SERIAL
    required_capability: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)

    # 并行执行：子步骤列表
    sub_steps: List["WorkflowStep"] = field(default_factory=list)

    # 条件执行
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None

    # 执行控制
    max_retries: int = 3
    timeout_seconds: Optional[float] = None
    depends_on: List[str] = field(default_factory=list)  # 依赖的step_id列表

    # 运行时状态
    _status: TaskStatus = TaskStatus.PENDING
    _result: Any = None
    _assigned_agent: Optional[str] = None
    _error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "name": self.name,
            "step_type": self.step_type.value,
            "required_capability": self.required_capability,
            "required_capabilities": self.required_capabilities,
            "status": self._status.value,
            "result": str(self._result)[:200] if self._result else None,
            "assigned_agent": self._assigned_agent,
            "error": self._error,
            "depends_on": self.depends_on,
            "sub_steps_count": len(self.sub_steps),
        }


@dataclass
class Workflow:
    """工作流定义"""
    workflow_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    context: Dict[str, Any] = field(default_factory=dict)

    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 执行追踪
    _step_results: Dict[str, Any] = field(default_factory=dict)
    _current_step_index: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_id": self.workflow_id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "step_count": len(self.steps),
            "current_step": self._current_step_index,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [s.to_dict() for s in self.steps],
        }


class AgentOrchestrator:
    """
    多Agent编排引擎

    定义和执行多Agent协作工作流，支持串行/并行步骤组合。

    使用示例:
        with AgentRegistry() as registry:
            registry.register("agent_1", ["search"])
            registry.register("agent_2", ["analyze"])

            with MessageBus(orchestrator.message_bus.db_path) as bus, \
                 TaskDispatcher(registry) as dispatcher, \
                 AgentOrchestrator(registry, dispatcher, bus) as orch:

                workflow_id = orch.create_workflow([
                    WorkflowStep(name="搜索", required_capability="search"),
                    WorkflowStep(name="分析", required_capability="analyze"),
                ])
                result = orch.execute_workflow(workflow_id)
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        task_dispatcher: TaskDispatcher,
        message_bus: CollaborationMessageBus,
        notifier: Any = None,
    ):
        """
        初始化编排引擎

        Args:
            agent_registry: Agent注册中心
            task_dispatcher: 任务分发器
            message_bus: 消息总线
            notifier: FeishuNotifier实例（可选）
        """
        self.agent_registry = agent_registry
        self.task_dispatcher = task_dispatcher
        self.message_bus = message_bus
        self.notifier = notifier

        self._workflows: Dict[str, Workflow] = {}
        self._lock = threading.RLock()
        self._active = False

    # ── 上下文管理器 ──────────────────────────────────────────

    def __enter__(self) -> "AgentOrchestrator":
        self._active = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._active = False
        return None

    # ── 工作流定义 ────────────────────────────────────────────

    def create_workflow(
        self,
        steps: List[WorkflowStep],
        name: str = "",
        description: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        定义Agent协作流水线

        Args:
            steps: 工作流步骤列表
            name: 工作流名称
            description: 工作流描述
            context: 初始上下文

        Returns:
            str: 工作流ID
        """
        workflow = Workflow(
            name=name or f"workflow_{uuid.uuid4().hex[:8]}",
            description=description,
            steps=steps,
            context=context or {},
            status=WorkflowStatus.READY,
        )

        with self._lock:
            self._workflows[workflow.workflow_id] = workflow

        logger.info(
            "工作流已创建: %s (%d 步骤)",
            workflow.workflow_id[:8], len(steps),
        )
        return workflow.workflow_id

    # ── 工作流执行 ────────────────────────────────────────────

    def execute_workflow(
        self,
        workflow_id: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        执行工作流

        Args:
            workflow_id: 工作流ID
            context: 额外上下文（会合并到工作流上下文）

        Returns:
            Dict: 执行结果 {workflow_id, status, step_results, ...}
        """
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                raise ValueError(f"工作流不存在: {workflow_id}")

            if workflow.status != WorkflowStatus.READY:
                raise ValueError(
                    f"工作流状态不可执行: {workflow.status.value}，"
                    f"需要 {WorkflowStatus.READY.value}"
                )

            workflow.status = WorkflowStatus.RUNNING
            workflow.started_at = datetime.now()

            if context:
                workflow.context.update(context)

        logger.info("开始执行工作流: %s", workflow_id[:8])

        # 广播工作流开始
        self.broadcast(
            message_type=MessageType.WORKFLOW_UPDATE,
            payload={
                "workflow_id": workflow_id,
                "status": "started",
                "name": workflow.name,
            },
            use_message_bus=True,
        )

        try:
            # 按步骤顺序执行
            for i, step in enumerate(workflow.steps):
                workflow._current_step_index = i
                logger.info(
                    "执行步骤 %d/%d: %s [%s]",
                    i + 1, len(workflow.steps),
                    step.name, step.step_type.value,
                )

                if step.step_type == StepType.PARALLEL:
                    self._execute_parallel_step(step, workflow)
                elif step.step_type == StepType.CONDITIONAL:
                    self._execute_conditional_step(step, workflow)
                elif step.step_type == StepType.BROADCAST:
                    self._execute_broadcast_step(step, workflow)
                else:  # SERIAL
                    self._execute_serial_step(step, workflow)

                # 检查步骤是否失败
                if step._status == TaskStatus.FAILED:
                    workflow.status = WorkflowStatus.FAILED
                    logger.error(
                        "工作流 %s 在步骤 %s 失败",
                        workflow_id[:8], step.name,
                    )
                    break

            else:
                # 所有步骤成功
                workflow.status = WorkflowStatus.COMPLETED
                logger.info("工作流 %s 完成", workflow_id[:8])

        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            logger.exception("工作流 %s 执行异常", workflow_id[:8])

        finally:
            workflow.completed_at = datetime.now()

        # 广播工作流结束
        self.broadcast(
            message_type=MessageType.WORKFLOW_UPDATE,
            payload={
                "workflow_id": workflow_id,
                "status": workflow.status.value,
                "name": workflow.name,
            },
            use_message_bus=True,
        )

        # 通知
        self._notify_workflow_completion(workflow)

        return {
            "workflow_id": workflow_id,
            "status": workflow.status.value,
            "step_results": workflow._step_results,
            "workflow": workflow.to_dict(),
        }

    def _execute_serial_step(self, step: WorkflowStep, workflow: Workflow) -> None:
        """执行串行步骤"""
        task = Task(
            name=step.name,
            description=f"Workflow step: {step.name}",
            priority=TaskPriority.MEDIUM,
            required_capability=step.required_capability,
            required_capabilities=list(step.required_capabilities),
            payload={**step.payload, "workflow_context": workflow.context},
            max_retries=step.max_retries,
            timeout_seconds=step.timeout_seconds,
        )

        task_id = self.task_dispatcher.submit_task(task)
        step._status = TaskStatus.RUNNING

        # 轮询等待任务完成（简化实现）—— 在实际场景中应使用回调或事件
        max_wait = step.timeout_seconds or 300.0
        poll_interval = 0.5
        waited = 0.0

        while waited < max_wait:
            status = self.task_dispatcher.task_status(task_id)
            if status is None:
                step._status = TaskStatus.FAILED
                step._error = "任务丢失"
                return

            current = TaskStatus(status["status"])
            if current == TaskStatus.COMPLETED:
                step._status = TaskStatus.COMPLETED
                step._result = status.get("result")
                step._assigned_agent = status.get("assigned_agent")
                workflow._step_results[step.step_id] = step._result
                workflow.context[f"step_{step.step_id[:8]}_result"] = step._result
                return
            elif current == TaskStatus.FAILED:
                step._status = TaskStatus.FAILED
                step._error = status.get("error_message", "未知错误")
                return
            elif current == TaskStatus.CANCELLED:
                step._status = TaskStatus.CANCELLED
                step._error = "任务已取消"
                return

            time_sleep = min(poll_interval, max_wait - waited)
            if time_sleep > 0:
                import time
                time.sleep(time_sleep)
            waited += poll_interval

        # 超时
        step._status = TaskStatus.FAILED
        step._error = f"步骤超时 ({max_wait}s)"

    def _execute_parallel_step(self, step: WorkflowStep, workflow: Workflow) -> None:
        """执行并行步骤（启动子步骤并等待全部完成）"""
        if not step.sub_steps:
            logger.warning("并行步骤 %s 无子步骤", step.name)
            step._status = TaskStatus.COMPLETED
            return

        import concurrent.futures

        step._status = TaskStatus.RUNNING
        errors = []

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=min(len(step.sub_steps), 10),
            thread_name_prefix="par-step",
        ) as executor:
            futures = {}
            for sub_step in step.sub_steps:
                sub_step._status = TaskStatus.RUNNING
                future = executor.submit(
                    self._execute_sub_step, sub_step, workflow
                )
                futures[future] = sub_step

            for future in concurrent.futures.as_completed(futures):
                sub_step = futures[future]
                try:
                    future.result()
                except Exception as e:
                    sub_step._status = TaskStatus.FAILED
                    sub_step._error = str(e)
                    errors.append(f"{sub_step.name}: {e}")

        if errors:
            step._status = TaskStatus.FAILED
            step._error = "; ".join(errors)
        else:
            step._status = TaskStatus.COMPLETED
            # 收集所有子步骤结果
            combined = {}
            for sub_step in step.sub_steps:
                combined[sub_step.step_id] = sub_step._result
            step._result = combined
            workflow._step_results[step.step_id] = combined

    def _execute_sub_step(self, sub_step: WorkflowStep, workflow: Workflow) -> None:
        """执行并行子步骤"""
        self._execute_serial_step(sub_step, workflow)

    def _execute_conditional_step(self, step: WorkflowStep, workflow: Workflow) -> None:
        """执行条件步骤"""
        if step.condition is None:
            step._status = TaskStatus.COMPLETED
            step._result = True
            return

        try:
            should_execute = step.condition(workflow.context)
            if should_execute:
                self._execute_serial_step(step, workflow)
            else:
                step._status = TaskStatus.COMPLETED
                step._result = "skipped"
                logger.info("条件步骤 %s 跳过", step.name)
        except Exception as e:
            step._status = TaskStatus.FAILED
            step._error = f"条件评估失败: {e}"

    def _execute_broadcast_step(self, step: WorkflowStep, workflow: Workflow) -> None:
        """执行广播步骤"""
        step._status = TaskStatus.RUNNING
        try:
            self.broadcast(
                message_type=MessageType.COMMAND,
                payload=step.payload,
                use_message_bus=True,
            )
            step._status = TaskStatus.COMPLETED
            step._result = "broadcasted"
            workflow._step_results[step.step_id] = "broadcasted"
        except Exception as e:
            step._status = TaskStatus.FAILED
            step._error = str(e)

    # ── 广播 ──────────────────────────────────────────────────

    def broadcast(
        self,
        message_type: MessageType = MessageType.BROADCAST,
        payload: Optional[Dict[str, Any]] = None,
        use_message_bus: bool = True,
        sender: str = "orchestrator",
    ) -> None:
        """
        向所有Agent广播消息

        Args:
            message_type: 消息类型
            payload: 消息载荷
            use_message_bus: 是否使用消息总线持久化
            sender: 发送者ID
        """
        payload = payload or {}

        if use_message_bus:
            self.message_bus.broadcast(
                sender=sender,
                message_type=message_type,
                payload=payload,
            )

        logger.info("广播消息: [%s] %s", message_type.value, sender)

    # ── 工作流管理 ────────────────────────────────────────────

    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                return None
            return workflow.to_dict()

    def cancel_workflow(self, workflow_id: str) -> bool:
        """取消工作流"""
        with self._lock:
            workflow = self._workflows.get(workflow_id)
            if workflow is None:
                return False
            if workflow.status not in (WorkflowStatus.RUNNING, WorkflowStatus.READY):
                return False
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now()

        logger.info("工作流 %s 已取消", workflow_id[:8])
        return True

    def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
    ) -> List[Dict[str, Any]]:
        """列出工作流"""
        with self._lock:
            workflows = list(self._workflows.values())
            if status:
                workflows = [w for w in workflows if w.status == status]
            return [w.to_dict() for w in workflows]

    # ── 通知 ──────────────────────────────────────────────────

    def _notify_workflow_completion(self, workflow: Workflow) -> None:
        """通知工作流完成"""
        if self.notifier:
            try:
                level = "success" if workflow.status == WorkflowStatus.COMPLETED else "error"
                self.notifier.send_notification(
                    title=f"[Orchestrator] 工作流 {workflow.status.value}",
                    content=(
                        f"工作流: {workflow.name} ({workflow.workflow_id[:8]})\n"
                        f"状态: {workflow.status.value}\n"
                        f"步骤数: {len(workflow.steps)}\n"
                        f"耗时: {(workflow.completed_at - workflow.started_at).total_seconds():.1f}s"
                        if workflow.started_at and workflow.completed_at
                        else f"工作流: {workflow.name}"
                    ),
                    level=level,
                )
            except Exception:
                logger.debug("通知发送失败")

    # ── 集成 SelfMonitor ──────────────────────────────────────

    def report_orchestration_stats(self) -> Dict[str, Any]:
        """上报编排统计信息"""
        with self._lock:
            stats = {
                "timestamp": datetime.now().isoformat(),
                "total_workflows": len(self._workflows),
                "status_breakdown": {
                    s.value: sum(
                        1 for w in self._workflows.values()
                        if w.status == s
                    )
                    for s in WorkflowStatus
                },
                "active_workflows": sum(
                    1 for w in self._workflows.values()
                    if w.status == WorkflowStatus.RUNNING
                ),
            }
        return stats

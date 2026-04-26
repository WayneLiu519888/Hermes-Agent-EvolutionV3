"""
任务分发器 - 任务分发/优先级队列/依赖管理

将任务提交到队列，通过AgentRegistry发现最佳Agent并分配执行。
支持优先级、任务依赖和失败重试。
"""

from __future__ import annotations

import logging
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

from .agent_registry import AgentRegistry, AgentInfo, AgentStatus

logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """任务优先级"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class TaskStatus(Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    BLOCKED = "blocked"  # 等待依赖


@dataclass
class Task:
    """任务数据类"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.MEDIUM
    required_capability: str = ""
    required_capabilities: List[str] = field(default_factory=list)
    payload: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING

    # 执行信息
    assigned_agent: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    result: Any = None

    # 依赖与重试
    dependencies: List[str] = field(default_factory=list)  # 依赖的task_id列表
    max_retries: int = 3
    retry_count: int = 0
    retry_delay: float = 1.0  # 重试延迟（秒）
    timeout_seconds: Optional[float] = None

    # 回调
    on_complete: Optional[Callable[["Task"], None]] = None
    on_fail: Optional[Callable[["Task"], None]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "description": self.description,
            "priority": self.priority.name,
            "required_capability": self.required_capability,
            "required_capabilities": self.required_capabilities,
            "status": self.status.value,
            "assigned_agent": self.assigned_agent,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error_message": self.error_message,
            "dependencies": self.dependencies,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        }

    def can_execute(self, completed_tasks: Set[str]) -> bool:
        """检查依赖是否已满足"""
        return all(dep in completed_tasks for dep in self.dependencies)


class TaskDispatcher:
    """
    任务分发器

    管理任务队列，将任务分配给最优Agent执行。
    支持优先级排序、依赖管理和失败重试。

    使用示例:
        with AgentRegistry() as registry, TaskDispatcher(registry) as dispatcher:
            registry.register("agent_1", ["search"])
            task = Task(name="搜索任务", required_capability="search")
            dispatcher.submit_task(task)
            status = dispatcher.task_status(task.task_id)
    """

    def __init__(
        self,
        agent_registry: AgentRegistry,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        notifier: Any = None,
    ):
        """
        初始化任务分发器

        Args:
            agent_registry: Agent注册中心实例
            max_retries: 默认最大重试次数
            retry_delay: 默认重试延迟
            notifier: FeishuNotifier实例（可选）
        """
        self.agent_registry = agent_registry
        self.default_max_retries = max_retries
        self.default_retry_delay = retry_delay
        self.notifier = notifier

        self._tasks: Dict[str, Task] = {}
        self._completed_task_ids: Set[str] = set()
        self._lock = threading.RLock()

        # 后台分发线程
        self._dispatch_thread: Optional[threading.Thread] = None
        self._stop_dispatch = threading.Event()
        self._active = False

    # ── 上下文管理器 ──────────────────────────────────────────

    def __enter__(self) -> "TaskDispatcher":
        self._active = True
        self._start_dispatch_thread()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._active = False
        self._stop_dispatch.set()
        if self._dispatch_thread and self._dispatch_thread.is_alive():
            self._dispatch_thread.join(timeout=5.0)
        self._dispatch_thread = None
        return None

    def _start_dispatch_thread(self) -> None:
        """启动后台分发线程"""
        if self._dispatch_thread is not None and self._dispatch_thread.is_alive():
            return
        self._stop_dispatch.clear()
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop,
            daemon=True,
            name="task-dispatcher",
        )
        self._dispatch_thread.start()

    def _dispatch_loop(self) -> None:
        """后台分发循环"""
        while not self._stop_dispatch.is_set():
            self._stop_dispatch.wait(0.5)
            if not self._stop_dispatch.is_set():
                self._process_pending_tasks()

    # ── 任务提交 ──────────────────────────────────────────────

    def submit_task(self, task: Task) -> str:
        """
        提交任务并尝试分配Agent

        Args:
            task: Task实例

        Returns:
            str: 任务ID
        """
        with self._lock:
            # 设置默认重试参数（仅在未显式设置时，即负值表示使用默认）
            if task.max_retries < 0:
                task.max_retries = self.default_max_retries
            if task.retry_delay <= 0:
                task.retry_delay = self.default_retry_delay

            # 检查依赖
            if task.dependencies and not task.can_execute(self._completed_task_ids):
                task.status = TaskStatus.BLOCKED
                logger.info(
                    "任务 %s 被阻塞，等待依赖: %s",
                    task.task_id[:8], task.dependencies,
                )

            self._tasks[task.task_id] = task
            logger.info(
                "任务已提交: %s [%s] %s",
                task.name, task.priority.name, task.task_id[:8],
            )

        # 立即尝试分配（不等待分发循环）
        if task.status in (TaskStatus.PENDING,):
            self._assign_task(task)

        return task.task_id

    # ── 任务分配 ──────────────────────────────────────────────

    def _process_pending_tasks(self) -> None:
        """处理待分配的任务（后台循环调用）"""
        # 收集需要处理的任务（加入排序）
        with self._lock:
            pending = [
                t for t in self._tasks.values()
                if t.status in (TaskStatus.PENDING, TaskStatus.BLOCKED)
            ]

        # 检查被阻塞的任务是否可以解除
        for task in pending:
            if task.status == TaskStatus.BLOCKED:
                if task.can_execute(self._completed_task_ids):
                    with self._lock:
                        task.status = TaskStatus.PENDING
                    logger.info("任务 %s 依赖已满足，重新排队", task.task_id[:8])

        # 按优先级排序
        with self._lock:
            ready = sorted(
                [t for t in self._tasks.values() if t.status == TaskStatus.PENDING],
                key=lambda t: t.priority.value,
            )

        for task in ready:
            self._assign_task(task)

    def _assign_task(self, task: Task) -> bool:
        """
        为任务分配最佳Agent

        Args:
            task: Task实例

        Returns:
            bool: 是否成功分配
        """
        # 构建能力列表
        all_caps = list(task.required_capabilities)
        if task.required_capability and task.required_capability not in all_caps:
            all_caps.append(task.required_capability)

        # 发现可用Agent
        agents = self.agent_registry.discover(
            required_capabilities=all_caps if all_caps else None,
            only_alive=True,
        )

        if not agents:
            logger.warning(
                "任务 %s 无可用的Agent (需要能力: %s)",
                task.task_id[:8], all_caps,
            )
            return False

        # 选择负载最低的Agent
        best_agent = agents[0]  # 已按负载因子排序

        with self._lock:
            task.assigned_agent = best_agent.agent_id
            task.status = TaskStatus.ASSIGNED
            task.started_at = datetime.now()

        # 更新Agent状态
        self.agent_registry.heartbeat(
            best_agent.agent_id,
            status=AgentStatus.BUSY,
            current_task=task.task_id,
        )

        logger.info(
            "任务 %s 分配给 Agent %s (负载: %.2f)",
            task.task_id[:8], best_agent.agent_id, best_agent.load_factor,
        )

        # 通知
        self._notify_assignment(task, best_agent)
        return True

    # ── 任务完成 / 失败 ──────────────────────────────────────

    def complete_task(
        self,
        task_id: str,
        result: Any = None,
        error: Optional[str] = None,
    ) -> bool:
        """
        标记任务完成（或失败）

        Args:
            task_id: 任务ID
            result: 任务结果
            error: 错误信息（如有表示失败）

        Returns:
            bool: 是否成功标记
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                logger.warning("任务不存在: %s", task_id)
                return False

            if error:
                # 处理失败
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.RETRYING
                    task.error_message = error
                    logger.info(
                        "任务 %s 失败，第 %d/%d 次重试",
                        task_id[:8], task.retry_count, task.max_retries,
                    )
                    # 在锁外安排重试
                    retry_delay = task.retry_delay
                    threading.Thread(
                        target=self._retry_task,
                        args=(task_id, retry_delay),
                        daemon=True,
                    ).start()
                else:
                    task.status = TaskStatus.FAILED
                    task.error_message = error
                    task.completed_at = datetime.now()
                    logger.error("任务 %s 最终失败: %s", task_id[:8], error)
                    if task.on_fail:
                        try:
                            task.on_fail(task)
                        except Exception:
                            logger.exception("on_fail回调异常")
            else:
                # 成功
                task.status = TaskStatus.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                self._completed_task_ids.add(task_id)
                logger.info("任务 %s 完成", task_id[:8])
                if task.on_complete:
                    try:
                        task.on_complete(task)
                    except Exception:
                        logger.exception("on_complete回调异常")

                # 解锁依赖此任务的其他任务
                self._unblock_dependents(task_id)

            # 释放Agent
            if task.assigned_agent:
                self.agent_registry.heartbeat(
                    task.assigned_agent,
                    status=AgentStatus.IDLE,
                    current_task=None,
                )

        return True

    def _retry_task(self, task_id: str, delay: float) -> None:
        """延迟重试任务"""
        time.sleep(delay)
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.RETRYING:
                task.status = TaskStatus.PENDING
                task.assigned_agent = None
                logger.info("任务 %s 重新排队", task_id[:8])

    def _unblock_dependents(self, completed_task_id: str) -> None:
        """解锁依赖已完成任务的其他任务"""
        with self._lock:
            unblocked = []
            for task in self._tasks.values():
                if task.status == TaskStatus.BLOCKED:
                    if task.can_execute(self._completed_task_ids):
                        task.status = TaskStatus.PENDING
                        unblocked.append(task.task_id)

        for tid in unblocked:
            logger.info("任务 %s 依赖已满足，解除阻塞", tid[:8])
            # 立即尝试分配
            with self._lock:
                task = self._tasks.get(tid)
            if task:
                self._assign_task(task)

    # ── 任务取消 ──────────────────────────────────────────────

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return False
            if task.status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                return False

            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()

            if task.assigned_agent:
                self.agent_registry.heartbeat(
                    task.assigned_agent,
                    status=AgentStatus.IDLE,
                    current_task=None,
                )

            logger.info("任务 %s 已取消", task_id[:8])
            return True

    # ── 状态查询 ──────────────────────────────────────────────

    def task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        查询任务状态

        Args:
            task_id: 任务ID

        Returns:
            Optional[Dict]: 任务状态字典，不存在返回None
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            return task.to_dict()

    def list_tasks(
        self,
        status: Optional[TaskStatus] = None,
        priority: Optional[TaskPriority] = None,
    ) -> List[Dict[str, Any]]:
        """
        列出任务

        Args:
            status: 按状态过滤
            priority: 按优先级过滤

        Returns:
            List[Dict]: 任务状态列表
        """
        with self._lock:
            tasks = list(self._tasks.values())
            if status:
                tasks = [t for t in tasks if t.status == status]
            if priority:
                tasks = [t for t in tasks if t.priority == priority]
            return [t.to_dict() for t in tasks]

    def get_queue_size(self) -> int:
        """获取待处理任务数量"""
        with self._lock:
            return sum(
                1 for t in self._tasks.values()
                if t.status in (TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRYING)
            )

    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        with self._lock:
            stats = {s.value: 0 for s in TaskStatus}
            for t in self._tasks.values():
                stats[t.status.value] += 1
            return stats

    # ── 通知 ──────────────────────────────────────────────────

    def _notify_assignment(self, task: Task, agent: AgentInfo) -> None:
        """通知任务分配"""
        if self.notifier:
            try:
                self.notifier.send_notification(
                    title=f"[TaskDispatcher] 任务分配",
                    content=(
                        f"任务 '{task.name}' ({task.task_id[:8]})\n"
                        f"分配给: {agent.agent_id}\n"
                        f"优先级: {task.priority.name}\n"
                        f"Agent负载: {agent.load_factor:.2f}"
                    ),
                    level="info",
                )
            except Exception:
                logger.debug("通知发送失败")

"""
协作引擎模块 - Hermes Agent Evolution 迭代4

提供多Agent协作的核心能力：
- Agent注册/发现/心跳管理
- 任务分发与优先级队列
- 多Agent编排引擎（串行/并行工作流）
- 跨Agent消息总线（SQLite持久化）

与以下模块集成：
- src/evolution/self_monitor.py  → Agent状态上报
- src/utils/feishu_notifier.py   → 协作事件通知
"""

from .agent_registry import AgentRegistry, AgentInfo, AgentStatus
from .task_dispatcher import (
    TaskDispatcher,
    Task,
    TaskPriority,
    TaskStatus as TaskState,
)
from .agent_orchestrator import (
    AgentOrchestrator,
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepType,
)
from .message_bus import (
    CollaborationMessageBus,
    Message,
    MessageType,
    MessagePriority,
)

__all__ = [
    # Agent注册中心
    "AgentRegistry",
    "AgentInfo",
    "AgentStatus",
    # 任务分发器
    "TaskDispatcher",
    "Task",
    "TaskPriority",
    "TaskState",
    # 编排引擎
    "AgentOrchestrator",
    "Workflow",
    "WorkflowStep",
    "WorkflowStatus",
    "StepType",
    # 消息总线
    "CollaborationMessageBus",
    "Message",
    "MessageType",
    "MessagePriority",
]

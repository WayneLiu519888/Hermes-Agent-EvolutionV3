"""
Agent注册中心 - Agent注册/发现/心跳管理

维护活跃Agent字典，支持注册、发现、心跳和自动超时移除。
与 self_monitor.py 集成以报告Agent状态变化。
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent状态枚举"""
    ONLINE = "online"
    BUSY = "busy"
    IDLE = "idle"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class AgentInfo:
    """Agent信息数据类"""
    agent_id: str
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: AgentStatus = AgentStatus.ONLINE
    registered_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    current_task: Optional[str] = None
    load_factor: float = 0.0  # 0.0 ~ 1.0, 负载因子
    version: str = "1.0.0"

    def is_alive(self, timeout_seconds: float = 30.0) -> bool:
        """检查Agent是否存活（基于心跳超时）"""
        return (datetime.now() - self.last_heartbeat) < timedelta(seconds=timeout_seconds)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典用于上报"""
        return {
            "agent_id": self.agent_id,
            "capabilities": self.capabilities,
            "metadata": self.metadata,
            "status": self.status.value,
            "registered_at": self.registered_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "current_task": self.current_task,
            "load_factor": self.load_factor,
            "version": self.version,
            "is_alive": self.is_alive(),
        }


class AgentRegistry:
    """
    Agent注册中心

    维护所有活跃Agent的注册信息，支持心跳检测和自动超时移除。
    集成 self_monitor 进行状态上报，集成 feishu_notifier 进行事件通知。

    使用示例:
        with AgentRegistry() as registry:
            registry.register("agent_1", ["search", "analyze"])
            agents = registry.discover("search")
            registry.heartbeat("agent_1")
    """

    def __init__(
        self,
        heartbeat_timeout: float = 30.0,
        cleanup_interval: float = 10.0,
        self_monitor: Any = None,
        notifier: Any = None,
    ):
        """
        初始化Agent注册中心

        Args:
            heartbeat_timeout: 心跳超时秒数（默认30秒）
            cleanup_interval: 清理检查间隔（默认10秒）
            self_monitor: SelfMonitor实例（可选，用于状态上报）
            notifier: FeishuNotifier实例（可选，用于事件通知）
        """
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = threading.RLock()
        self.heartbeat_timeout = heartbeat_timeout
        self.cleanup_interval = cleanup_interval
        self.self_monitor = self_monitor
        self.notifier = notifier

        # 后台清理线程
        self._cleanup_thread: Optional[threading.Thread] = None
        self._stop_cleanup = threading.Event()
        self._active = False

        # 事件回调
        self._callbacks: Dict[str, List[Callable]] = {
            "on_register": [],
            "on_unregister": [],
            "on_timeout": [],
            "on_heartbeat": [],
        }

    # ── 上下文管理器 ──────────────────────────────────────────

    def __enter__(self) -> "AgentRegistry":
        self._active = True
        self._start_cleanup_thread()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._active = False
        self._stop_cleanup.set()
        if self._cleanup_thread and self._cleanup_thread.is_alive():
            self._cleanup_thread.join(timeout=5.0)
        self._cleanup_thread = None
        # 自动清理不触发回调，仅清理资源
        return None

    # ── 后台清理线程 ──────────────────────────────────────────

    def _start_cleanup_thread(self) -> None:
        """启动后台清理线程"""
        if self._cleanup_thread is not None and self._cleanup_thread.is_alive():
            return
        self._stop_cleanup.clear()
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="agent-registry-cleanup",
        )
        self._cleanup_thread.start()

    def _cleanup_loop(self) -> None:
        """后台清理循环"""
        while not self._stop_cleanup.is_set():
            self._stop_cleanup.wait(self.cleanup_interval)
            if not self._stop_cleanup.is_set():
                self._purge_expired()

    # ── 注册 / 注销 ───────────────────────────────────────────

    def register(
        self,
        agent_id: str,
        capabilities: List[str],
        metadata: Optional[Dict[str, Any]] = None,
        version: str = "1.0.0",
    ) -> AgentInfo:
        """
        注册Agent

        Args:
            agent_id: Agent唯一标识
            capabilities: 能力列表
            metadata: 元数据
            version: 版本号

        Returns:
            AgentInfo: 注册后的Agent信息

        Raises:
            ValueError: agent_id已存在
        """
        with self._lock:
            if agent_id in self._agents:
                raise ValueError(f"Agent '{agent_id}' 已注册")

            info = AgentInfo(
                agent_id=agent_id,
                capabilities=list(capabilities),
                metadata=metadata or {},
                version=version,
            )
            self._agents[agent_id] = info

            logger.info(
                "Agent注册: %s (能力: %s)",
                agent_id,
                ", ".join(capabilities),
            )

        # 触发回调（锁外执行）
        self._trigger_callbacks("on_register", info)

        # 通知
        self._notify_event(
            "agent_registered",
            f"Agent {agent_id} 已注册",
            info.to_dict(),
        )

        return info

    def unregister(self, agent_id: str) -> bool:
        """
        注销Agent

        Args:
            agent_id: Agent唯一标识

        Returns:
            bool: 是否成功注销
        """
        with self._lock:
            if agent_id not in self._agents:
                logger.warning("尝试注销不存在的Agent: %s", agent_id)
                return False

            info = self._agents.pop(agent_id)

        logger.info("Agent注销: %s", agent_id)

        # 触发回调
        self._trigger_callbacks("on_unregister", info)

        # 通知
        self._notify_event(
            "agent_unregistered",
            f"Agent {agent_id} 已注销",
            info.to_dict(),
        )

        return True

    # ── 发现 ──────────────────────────────────────────────────

    def discover(
        self,
        required_capability: Optional[str] = None,
        required_capabilities: Optional[List[str]] = None,
        status: Optional[AgentStatus] = None,
        only_alive: bool = True,
    ) -> List[AgentInfo]:
        """
        发现匹配的Agent

        Args:
            required_capability: 单个必需能力（与required_capabilities二选一）
            required_capabilities: 多个必需能力列表（Agent需全部满足）
            status: 按状态过滤
            only_alive: 仅返回存活的Agent

        Returns:
            List[AgentInfo]: 匹配的Agent列表
        """
        # 构建能力集合
        if required_capability and required_capabilities:
            capabilities_needed = set(required_capabilities) | {required_capability}
        elif required_capability:
            capabilities_needed = {required_capability}
        elif required_capabilities:
            capabilities_needed = set(required_capabilities)
        else:
            capabilities_needed = None

        with self._lock:
            results = []
            for info in self._agents.values():
                # 存活检查
                if only_alive and not info.is_alive(self.heartbeat_timeout):
                    continue

                # 状态过滤
                if status is not None and info.status != status:
                    continue

                # 能力匹配
                if capabilities_needed is not None:
                    agent_caps = set(info.capabilities)
                    if not capabilities_needed.issubset(agent_caps):
                        continue

                results.append(info)

        # 按负载因子排序（负载低的优先）
        results.sort(key=lambda x: x.load_factor)
        return results

    # ── 心跳 ──────────────────────────────────────────────────

    def heartbeat(
        self,
        agent_id: str,
        status: Optional[AgentStatus] = None,
        load_factor: Optional[float] = None,
        current_task: Optional[str] = None,
    ) -> bool:
        """
        更新Agent心跳

        Args:
            agent_id: Agent唯一标识
            status: 新状态（可选）
            load_factor: 负载因子（可选，0.0~1.0）
            current_task: 当前任务ID（可选）

        Returns:
            bool: 是否成功更新
        """
        with self._lock:
            if agent_id not in self._agents:
                logger.warning("心跳更新失败，Agent不存在: %s", agent_id)
                return False

            info = self._agents[agent_id]
            info.last_heartbeat = datetime.now()

            if status is not None:
                info.status = status
            if load_factor is not None:
                info.load_factor = max(0.0, min(1.0, load_factor))
            if current_task is not None:
                info.current_task = current_task

        # 触发回调
        self._trigger_callbacks("on_heartbeat", info)
        return True

    def _purge_expired(self) -> int:
        """清理超时的Agent（内部方法）"""
        expired = []
        with self._lock:
            for agent_id, info in list(self._agents.items()):
                if not info.is_alive(self.heartbeat_timeout):
                    expired.append((agent_id, info))
                    del self._agents[agent_id]

        for agent_id, info in expired:
            logger.warning("Agent心跳超时，自动移除: %s", agent_id)
            self._trigger_callbacks("on_timeout", info)
            self._notify_event(
                "agent_timeout",
                f"Agent {agent_id} 心跳超时，已自动移除",
                info.to_dict(),
            )

        return len(expired)

    # ── 查询 ──────────────────────────────────────────────────

    def get_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """
        获取Agent状态

        Args:
            agent_id: Agent唯一标识

        Returns:
            Optional[Dict]: Agent状态字典，不存在返回None
        """
        with self._lock:
            info = self._agents.get(agent_id)
            if info is None:
                return None
            return info.to_dict()

    def list_all(self, only_alive: bool = False) -> List[Dict[str, Any]]:
        """
        返回所有已注册Agent

        Args:
            only_alive: 仅返回存活的Agent

        Returns:
            List[Dict]: Agent状态字典列表
        """
        with self._lock:
            if only_alive:
                return [
                    info.to_dict()
                    for info in self._agents.values()
                    if info.is_alive(self.heartbeat_timeout)
                ]
            return [info.to_dict() for info in self._agents.values()]

    def get_agent_count(self, only_alive: bool = True) -> int:
        """获取Agent数量"""
        with self._lock:
            if only_alive:
                return sum(
                    1 for info in self._agents.values()
                    if info.is_alive(self.heartbeat_timeout)
                )
            return len(self._agents)

    # ── 回调管理 ──────────────────────────────────────────────

    def on(self, event: str, callback: Callable) -> None:
        """注册事件回调

        Args:
            event: 事件名: 'on_register', 'on_unregister', 'on_timeout', 'on_heartbeat'
            callback: 回调函数，接收 AgentInfo 参数
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)
        else:
            raise ValueError(f"不支持的事件: {event}")

    def _trigger_callbacks(self, event: str, info: AgentInfo) -> None:
        """触发事件回调"""
        for cb in self._callbacks.get(event, []):
            try:
                cb(info)
            except Exception:
                logger.exception("回调执行异常: %s", event)

    # ── 通知 ──────────────────────────────────────────────────

    def _notify_event(self, event_type: str, message: str, data: Dict[str, Any]) -> None:
        """发送事件通知（通过飞书通知器）"""
        if self.notifier:
            try:
                self.notifier.send_notification(
                    title=f"[AgentRegistry] {event_type}",
                    content=f"{message}\n```json\n{data}\n```",
                    level="info",
                )
            except Exception:
                logger.debug("通知发送失败: %s", event_type)

    # ── 与 SelfMonitor 集成 ──────────────────────────────────

    def report_to_monitor(self) -> Dict[str, Any]:
        """向SelfMonitor报告Agent状态"""
        report = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": self.get_agent_count(only_alive=False),
            "alive_agents": self.get_agent_count(only_alive=True),
            "agent_statuses": {
                status.value: sum(
                    1 for info in self._agents.values()
                    if info.status == status
                )
                for status in AgentStatus
            },
            "agents": self.list_all(only_alive=False),
        }

        if self.self_monitor:
            try:
                # 将报告添加到监控历史
                self.self_monitor.monitoring_history.append({
                    "type": "agent_registry_report",
                    **report,
                })
            except Exception:
                logger.debug("状态上报到SelfMonitor失败")

        return report

"""
事件总线 - 事件驱动架构的核心组件
支持异步事件发布/订阅、事件过滤、优先级处理
"""

import asyncio
import logging
from typing import Dict, List, Callable, Any, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


class EventPriority(Enum):
    """事件优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    CRITICAL = 3


class EventType(Enum):
    """事件类型枚举"""
    # 系统事件
    SYSTEM_STARTUP = "system.startup"
    SYSTEM_SHUTDOWN = "system.shutdown"
    SYSTEM_ERROR = "system.error"
    
    # 学习事件
    LEARNING_STARTED = "learning.started"
    LEARNING_COMPLETED = "learning.completed"
    LEARNING_FAILED = "learning.failed"
    LEARNING_PROGRESS = "learning.progress"
    
    # 工具事件
    TOOL_EXECUTED = "tool.executed"
    TOOL_FAILED = "tool.failed"
    TOOL_DISCOVERED = "tool.discovered"
    TOOL_OPTIMIZED = "tool.optimized"
    
    # 任务事件
    TASK_RECEIVED = "task.received"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    
    # 监控事件
    METRIC_UPDATED = "metric.updated"
    ALERT_TRIGGERED = "alert.triggered"
    HEALTH_CHECK = "health.check"


@dataclass
class Event:
    """事件数据类"""
    event_type: EventType
    data: Dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    priority: EventPriority = EventPriority.NORMAL
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "data": self.data,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority.value,
            "metadata": self.metadata
        }


class EventBus:
    """事件总线"""
    
    def __init__(self):
        self._subscribers: Dict[EventType, List[Callable]] = {}
        self._wildcard_subscribers: List[Callable] = []
        self._event_history: List[Event] = []
        self._max_history: int = 1000
        self._lock = asyncio.Lock()
        
    async def publish(self, event: Event) -> None:
        """发布事件"""
        async with self._lock:
            # 记录事件历史
            self._event_history.append(event)
            if len(self._event_history) > self._max_history:
                self._event_history = self._event_history[-self._max_history:]
            
            # 通知特定类型的订阅者
            subscribers = self._subscribers.get(event.event_type, [])
            
            # 通知通配符订阅者
            all_subscribers = subscribers + self._wildcard_subscribers
            
            if not all_subscribers:
                logger.debug(f"事件 {event.event_type.value} 没有订阅者")
                return
            
            # 异步通知所有订阅者
            tasks = []
            for callback in all_subscribers:
                task = asyncio.create_task(self._safe_callback(callback, event))
                tasks.append(task)
            
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _safe_callback(self, callback: Callable, event: Event) -> None:
        """安全执行回调函数"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            logger.error(f"事件回调执行失败: {e}", exc_info=True)
    
    def subscribe(self, event_type: EventType, callback: Callable) -> None:
        """订阅特定类型的事件"""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        
        if callback not in self._subscribers[event_type]:
            self._subscribers[event_type].append(callback)
            logger.debug(f"订阅事件: {event_type.value}")
    
    def subscribe_all(self, callback: Callable) -> None:
        """订阅所有事件"""
        if callback not in self._wildcard_subscribers:
            self._wildcard_subscribers.append(callback)
            logger.debug("订阅所有事件")
    
    def unsubscribe(self, event_type: EventType, callback: Callable) -> None:
        """取消订阅"""
        if event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
                logger.debug(f"取消订阅事件: {event_type.value}")
    
    def unsubscribe_all(self, callback: Callable) -> None:
        """取消所有订阅"""
        if callback in self._wildcard_subscribers:
            self._wildcard_subscribers.remove(callback)
            logger.debug("取消所有事件订阅")
        
        for event_type in self._subscribers:
            if callback in self._subscribers[event_type]:
                self._subscribers[event_type].remove(callback)
    
    def get_event_history(self, limit: int = 100) -> List[Event]:
        """获取事件历史"""
        return self._event_history[-limit:] if self._event_history else []
    
    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()
    
    def get_subscriber_count(self) -> Dict[str, int]:
        """获取订阅者统计"""
        stats = {}
        for event_type, subscribers in self._subscribers.items():
            stats[event_type.value] = len(subscribers)
        stats["wildcard"] = len(self._wildcard_subscribers)
        return stats


class EventFilter:
    """事件过滤器"""
    
    @staticmethod
    def by_source(source: str) -> Callable[[Event], bool]:
        """按来源过滤"""
        return lambda event: event.source == source
    
    @staticmethod
    def by_priority(min_priority: EventPriority) -> Callable[[Event], bool]:
        """按优先级过滤"""
        return lambda event: event.priority.value >= min_priority.value
    
    @staticmethod
    def by_data_key(key: str, value: Any = None) -> Callable[[Event], bool]:
        """按数据键值过滤"""
        if value is not None:
            return lambda event: key in event.data and event.data[key] == value
        return lambda event: key in event.data
    
    @staticmethod
    def combine(*filters: Callable[[Event], bool]) -> Callable[[Event], bool]:
        """组合多个过滤器"""
        def combined_filter(event: Event) -> bool:
            return all(f(event) for f in filters)
        return combined_filter


# 全局事件总线实例
event_bus = EventBus()
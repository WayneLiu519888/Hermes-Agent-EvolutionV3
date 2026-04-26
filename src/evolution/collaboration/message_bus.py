"""
跨Agent消息总线 - 持久化消息队列

基于SQLite的消息持久化，支持点对点发送、订阅和广播。
参考 src/evolution/memory/database.py 的SQLite模式。
与 feishu_notifier.py 集成以通知关键事件。
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    COMMAND = "command"
    QUERY = "query"
    RESPONSE = "response"
    EVENT = "event"
    HEARTBEAT = "heartbeat"
    TASK_UPDATE = "task_update"
    WORKFLOW_UPDATE = "workflow_update"
    BROADCAST = "broadcast"
    ERROR = "error"


class MessagePriority(Enum):
    """消息优先级"""
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class Message:
    """消息数据类"""
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    receiver: str = ""  # 空字符串表示广播
    message_type: MessageType = MessageType.EVENT
    priority: MessagePriority = MessagePriority.MEDIUM
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    delivered: bool = False
    read: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "priority": self.priority.value,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "delivered": self.delivered,
            "read": self.read,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        msg = cls(
            message_id=data.get("message_id", ""),
            sender=data.get("sender", ""),
            receiver=data.get("receiver", ""),
            message_type=MessageType(data.get("message_type", "event")),
            priority=MessagePriority(data.get("priority", 3)),
            payload=data.get("payload", {}),
            delivered=data.get("delivered", False),
            read=data.get("read", False),
        )
        if "timestamp" in data:
            try:
                msg.timestamp = datetime.fromisoformat(data["timestamp"])
            except (ValueError, TypeError):
                pass
        return msg


class CollaborationMessageBus:
    """
    跨Agent消息总线

    支持：
    - 点对点消息发送
    - 消息类型订阅
    - 广播消息
    - SQLite持久化
    - 飞书通知集成
    - 上下文管理器

    使用示例:
        with CollaborationMessageBus() as bus:
            bus.send("agent_a", "agent_b", MessageType.COMMAND, {"cmd": "analyze"})
            messages = bus.receive("agent_b")
    """

    # SQLite DDL
    _DDL_MESSAGES = """
        CREATE TABLE IF NOT EXISTS collaboration_messages (
            message_id TEXT PRIMARY KEY,
            sender TEXT NOT NULL,
            receiver TEXT NOT NULL,
            message_type TEXT NOT NULL,
            priority INTEGER NOT NULL DEFAULT 3,
            payload TEXT NOT NULL DEFAULT '{}',
            timestamp DATETIME NOT NULL,
            delivered INTEGER NOT NULL DEFAULT 0,
            read INTEGER NOT NULL DEFAULT 0
        )
    """

    _DDL_SUBSCRIPTIONS = """
        CREATE TABLE IF NOT EXISTS collaboration_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            message_type TEXT NOT NULL,
            created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(agent_id, message_type)
        )
    """

    _DDL_INDEXES = [
        "CREATE INDEX IF NOT EXISTS idx_collab_msg_receiver ON collaboration_messages(receiver)",
        "CREATE INDEX IF NOT EXISTS idx_collab_msg_type ON collaboration_messages(message_type)",
        "CREATE INDEX IF NOT EXISTS idx_collab_msg_timestamp ON collaboration_messages(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_collab_sub_agent ON collaboration_subscriptions(agent_id)",
    ]

    def __init__(
        self,
        db_path: str = "collaboration_messages.db",
        notifier: Any = None,
        max_queue_size: int = 10_000,
    ):
        """
        初始化消息总线

        Args:
            db_path: SQLite数据库路径
            notifier: FeishuNotifier实例（可选）
            max_queue_size: 单个Agent最大未读消息数（用于内存队列）
        """
        self.db_path = db_path
        self.notifier = notifier
        self.max_queue_size = max_queue_size

        self._connection: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()

        # 内存中的消息回调（实时推送）
        self._subscribers: Dict[str, Dict[str, List[Callable]]] = {}
        # { agent_id: { message_type_value: [callback, ...] } }

        self._init_database()

    def _init_database(self) -> None:
        """初始化数据库表"""
        self._connection = sqlite3.connect(self.db_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

        try:
            cursor = self._connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute(self._DDL_MESSAGES)
            cursor.execute(self._DDL_SUBSCRIPTIONS)
            for idx_sql in self._DDL_INDEXES:
                cursor.execute(idx_sql)
            self._connection.commit()
            logger.info("消息总线数据库初始化完成: %s", self.db_path)
        except Exception:
            logger.exception("消息总线数据库初始化失败")
            raise

    # ── 上下文管理器 ──────────────────────────────────────────

    def __enter__(self) -> "CollaborationMessageBus":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        """关闭数据库连接"""
        if self._connection:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    # ── 发送 ──────────────────────────────────────────────────

    def send(
        self,
        sender: str,
        receiver: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.MEDIUM,
    ) -> str:
        """
        发送点对点消息

        Args:
            sender: 发送者Agent ID
            receiver: 接收者Agent ID
            message_type: 消息类型
            payload: 消息载荷
            priority: 优先级

        Returns:
            str: 消息ID
        """
        msg = Message(
            sender=sender,
            receiver=receiver,
            message_type=message_type,
            priority=priority,
            payload=payload,
        )

        # 持久化
        self._persist_message(msg)

        # 实时推送（如果接收者有回调订阅）
        self._push_to_subscriber(msg)

        logger.debug(
            "消息发送: %s -> %s [%s] %s",
            sender, receiver, message_type.value, msg.message_id[:8],
        )
        return msg.message_id

    def broadcast(
        self,
        sender: str,
        message_type: MessageType,
        payload: Dict[str, Any],
        priority: MessagePriority = MessagePriority.MEDIUM,
    ) -> str:
        """
        广播消息给所有Agent

        Args:
            sender: 发送者Agent ID
            message_type: 消息类型
            payload: 消息载荷
            priority: 优先级

        Returns:
            str: 消息ID
        """
        msg = Message(
            sender=sender,
            receiver="*",  # 广播标记
            message_type=message_type,
            priority=priority,
            payload=payload,
        )

        # 持久化
        self._persist_message(msg)

        # 广播给所有订阅者
        self._broadcast_to_subscribers(msg)

        logger.info(
            "广播消息: %s -> ALL [%s] %s",
            sender, message_type.value, msg.message_id[:8],
        )

        # 通知（仅关键消息）
        if priority in (MessagePriority.CRITICAL, MessagePriority.HIGH):
            self._notify_event(
                "message_broadcast",
                f"{sender} 广播了 {message_type.value} 消息",
            )

        return msg.message_id

    # ── 订阅 ──────────────────────────────────────────────────

    def subscribe(
        self,
        agent_id: str,
        message_types: List[MessageType],
        callback: Optional[Callable[[Message], None]] = None,
    ) -> None:
        """
        订阅消息类型

        Args:
            agent_id: Agent ID
            message_types: 订阅的消息类型列表
            callback: 实时回调（可选），收到消息时调用
        """
        with self._lock:
            # 持久化订阅
            cursor = self._connection.cursor()
            now = datetime.now().isoformat()
            for mt in message_types:
                try:
                    cursor.execute(
                        "INSERT OR IGNORE INTO collaboration_subscriptions (agent_id, message_type, created_at) VALUES (?, ?, ?)",
                        (agent_id, mt.value, now),
                    )
                except Exception:
                    logger.exception("持久化订阅失败: %s -> %s", agent_id, mt.value)
            self._connection.commit()

            # 内存回调
            if callback:
                if agent_id not in self._subscribers:
                    self._subscribers[agent_id] = {}
                for mt in message_types:
                    if mt.value not in self._subscribers[agent_id]:
                        self._subscribers[agent_id][mt.value] = []
                    self._subscribers[agent_id][mt.value].append(callback)

        logger.info("Agent %s 订阅了 %d 种消息类型", agent_id, len(message_types))

    def unsubscribe(
        self,
        agent_id: str,
        message_types: Optional[List[MessageType]] = None,
    ) -> None:
        """
        取消订阅

        Args:
            agent_id: Agent ID
            message_types: 要取消的消息类型（None表示全部取消）
        """
        with self._lock:
            if message_types is None:
                # 取消全部
                cursor = self._connection.cursor()
                cursor.execute(
                    "DELETE FROM collaboration_subscriptions WHERE agent_id = ?",
                    (agent_id,),
                )
                self._connection.commit()
                self._subscribers.pop(agent_id, None)
                logger.info("Agent %s 取消所有订阅", agent_id)
            else:
                # 取消指定类型
                cursor = self._connection.cursor()
                for mt in message_types:
                    cursor.execute(
                        "DELETE FROM collaboration_subscriptions WHERE agent_id = ? AND message_type = ?",
                        (agent_id, mt.value),
                    )
                self._connection.commit()
                if agent_id in self._subscribers:
                    for mt in message_types:
                        self._subscribers[agent_id].pop(mt.value, None)
                    if not self._subscribers[agent_id]:
                        del self._subscribers[agent_id]
                logger.info(
                    "Agent %s 取消订阅 %d 种类型",
                    agent_id, len(message_types),
                )

    # ── 接收 ──────────────────────────────────────────────────

    def receive(
        self,
        agent_id: str,
        message_types: Optional[List[MessageType]] = None,
        only_unread: bool = True,
        limit: int = 50,
    ) -> List[Message]:
        """
        接收消息

        Args:
            agent_id: 接收者Agent ID
            message_types: 过滤消息类型（None=所有）
            only_unread: 仅返回未读消息
            limit: 最大返回数量

        Returns:
            List[Message]: 消息列表
        """
        with self._lock:
            cursor = self._connection.cursor()

            conditions = ["(receiver = ? OR receiver = '*')"]
            params: List[Any] = [agent_id]

            if message_types:
                placeholders = ", ".join("?" for _ in message_types)
                conditions.append(f"message_type IN ({placeholders})")
                params.extend(mt.value for mt in message_types)

            if only_unread:
                conditions.append("read = 0")

            where = " AND ".join(conditions)
            sql = f"SELECT * FROM collaboration_messages WHERE {where} ORDER BY priority ASC, timestamp DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            messages = []
            message_ids_to_mark: List[str] = []
            for row in rows:
                data = dict(row)
                if data.get("payload") and isinstance(data["payload"], str):
                    try:
                        data["payload"] = json.loads(data["payload"])
                    except (json.JSONDecodeError, TypeError):
                        data["payload"] = {}
                msg = Message.from_dict(data)
                messages.append(msg)
                message_ids_to_mark.append(msg.message_id)

            # 标记为已读
            if message_ids_to_mark:
                placeholders = ", ".join("?" for _ in message_ids_to_mark)
                cursor.execute(
                    f"UPDATE collaboration_messages SET read = 1 WHERE message_id IN ({placeholders})",
                    message_ids_to_mark,
                )
                self._connection.commit()

            return messages

    def get_unread_count(self, agent_id: str) -> int:
        """获取未读消息数"""
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM collaboration_messages WHERE (receiver = ? OR receiver = '*') AND read = 0",
                (agent_id,),
            )
            row = cursor.fetchone()
            return row[0] if row else 0

    # ── 持久化 ────────────────────────────────────────────────

    def _persist_message(self, msg: Message) -> None:
        """持久化消息到SQLite"""
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                "INSERT INTO collaboration_messages (message_id, sender, receiver, message_type, priority, payload, timestamp, delivered, read) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    msg.message_id,
                    msg.sender,
                    msg.receiver,
                    msg.message_type.value,
                    msg.priority.value,
                    json.dumps(msg.payload, ensure_ascii=False, default=str),
                    msg.timestamp.isoformat(),
                    1 if msg.delivered else 0,
                    1 if msg.read else 0,
                ),
            )
            self._connection.commit()

    # ── 实时推送 ──────────────────────────────────────────────

    def _push_to_subscriber(self, msg: Message) -> None:
        """推送消息给订阅的回调"""
        # 检查目标Agent的回调
        target = msg.receiver
        if target in self._subscribers:
            callbacks = self._subscribers[target].get(msg.message_type.value, [])
            for cb in callbacks:
                try:
                    cb(msg)
                except Exception:
                    logger.exception("消息回调执行异常")

    def _broadcast_to_subscribers(self, msg: Message) -> None:
        """广播消息给所有订阅的回调"""
        mt_value = msg.message_type.value
        for agent_id, subscriptions in self._subscribers.items():
            if mt_value in subscriptions:
                for cb in subscriptions[mt_value]:
                    try:
                        cb(msg)
                    except Exception:
                        logger.exception("广播回调执行异常")

    # ── 通知 ──────────────────────────────────────────────────

    def _notify_event(self, event_type: str, description: str) -> None:
        """通过飞书发送通知"""
        if self.notifier:
            try:
                self.notifier.send_notification(
                    title=f"[MessageBus] {event_type}",
                    content=description,
                    level="info",
                )
            except Exception:
                logger.debug("通知发送失败")

    # ── 维护 ──────────────────────────────────────────────────

    def cleanup_old_messages(self, older_than_days: int = 7) -> int:
        """清理旧消息"""
        with self._lock:
            cursor = self._connection.cursor()
            cutoff = datetime.now().isoformat()
            cursor.execute(
                "DELETE FROM collaboration_messages WHERE timestamp < date(?, ?)",
                (cutoff, f"-{older_than_days} days"),
            )
            self._connection.commit()
            deleted = cursor.rowcount
            logger.info("清理了 %d 条旧消息", deleted)
            return deleted

    def get_message(self, message_id: str) -> Optional[Message]:
        """获取单条消息"""
        with self._lock:
            cursor = self._connection.cursor()
            cursor.execute(
                "SELECT * FROM collaboration_messages WHERE message_id = ?",
                (message_id,),
            )
            row = cursor.fetchone()
            if row:
                data = dict(row)
                if data.get("payload") and isinstance(data["payload"], str):
                    try:
                        data["payload"] = json.loads(data["payload"])
                    except (json.JSONDecodeError, TypeError):
                        data["payload"] = {}
                return Message.from_dict(data)
            return None

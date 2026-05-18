"""
V9.0.0 会话状态机 — 追踪当前session的对话状态

状态流转:
  idle → normal → error_recovery → normal → ...

在 pre_llm_call / post_llm_call / post_tool_call 中更新状态。
在 pre_llm_call 中根据状态决定注入策略。
"""

import hashlib
import logging
from datetime import datetime
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    """会话状态快照"""
    session_id: str = ""
    topics: List[str] = field(default_factory=list)
    message_count: int = 0
    error_count: int = 0
    recent_questions: List[str] = field(default_factory=list)
    question_hashes: List[str] = field(default_factory=list)
    key_decisions: List[str] = field(default_factory=list)
    last_tool_error: Optional[str] = None
    started_at: str = ""

    # 状态标识
    is_error_recovery: bool = False

    def to_dict(self) -> Dict:
        return {
            'session_id': self.session_id,
            'topics': self.topics,
            'message_count': self.message_count,
            'error_count': self.error_count,
            'recent_questions': self.recent_questions[-5:],
            'key_decisions': self.key_decisions[-5:],
            'last_tool_error': self.last_tool_error,
            'started_at': self.started_at,
        }


class SessionStateTracker:
    """会话状态追踪器（按session_id分实例）"""

    _instances: Dict[str, 'SessionStateTracker'] = {}

    @classmethod
    def for_session(cls, session_id: str) -> 'SessionStateTracker':
        if session_id not in cls._instances:
            cls._instances[session_id] = cls(session_id)
        return cls._instances[session_id]

    def __init__(self, session_id: str):
        self.state = SessionState(
            session_id=session_id,
            started_at=datetime.now().isoformat(),
        )

    # ── 状态更新 ──

    def record_user_message(self, message: str) -> None:
        """记录用户消息"""
        self.state.message_count += 1
        self.state.recent_questions.append(message[:200])
        if len(self.state.recent_questions) > 10:
            self.state.recent_questions = self.state.recent_questions[-10:]

        msg_hash = hashlib.md5(message.strip().lower().encode()).hexdigest()
        self.state.question_hashes.append(msg_hash)
        if len(self.state.question_hashes) > 20:
            self.state.question_hashes = self.state.question_hashes[-20:]

    def record_tool_error(self, tool_name: str, error: str) -> None:
        """记录工具调用失败"""
        self.state.error_count += 1
        self.state.last_tool_error = f"{tool_name}: {str(error)[:100]}"
        self.state.is_error_recovery = True

    def record_llm_reply(self, reply: str) -> None:
        """记录LLM回复，提取话题和关键决策"""
        import re

        # 话题提取
        topic_matches = re.findall(
            r'(?:项目|模块|配置|部署|测试|版本|bug|修复|性能|数据库|API|接口)'
            r'[：:\s]*(\w+)', reply
        )
        for kw in topic_matches[:3]:
            if kw not in self.state.topics:
                self.state.topics.append(kw)
                if len(self.state.topics) > 10:
                    self.state.topics = self.state.topics[-10:]

        # 关键决策提取
        decision_patterns = [
            r'决定[：:]\s*(.+?)(?:[。\n]|$)',
            r'最终选择[：:]\s*(.+?)(?:[。\n]|$)',
        ]
        for pattern in decision_patterns:
            for m in re.finditer(pattern, reply):
                dec = m.group(1).strip()[:100]
                if dec not in self.state.key_decisions:
                    self.state.key_decisions.append(dec)
                    if len(self.state.key_decisions) > 10:
                        self.state.key_decisions = self.state.key_decisions[-10:]

    def reset_error_state(self) -> None:
        """错误恢复后重置错误状态"""
        self.state.is_error_recovery = False

    # ── 注入决策 ──

    def is_repeat_question(self, message: str) -> bool:
        msg_hash = hashlib.md5(message.strip().lower().encode()).hexdigest()
        return self.state.question_hashes.count(msg_hash) >= 2

    def should_inject_summary(self) -> bool:
        return self.state.message_count > 10

    def should_inject_error_context(self) -> bool:
        return self.state.is_error_recovery

    def is_confusion(self, message: str) -> bool:
        confusion_kw = ['不对', '不是这个', '没懂', '什么意思', '搞错',
                        '不明白', '不理解', '？？', '?', 'wrong', 'confused']
        msg_lower = message.lower()
        return any(kw in msg_lower for kw in confusion_kw)

    def generate_injection(self, user_message: str,
                           existing_context: str = "") -> str:
        """根据当前状态生成应注入的上下文"""
        injections = []

        # 规则1: 重复提问
        if self.is_repeat_question(user_message):
            prev_q = None
            msg_hash = hashlib.md5(
                user_message.strip().lower().encode()
            ).hexdigest()
            for i, h in enumerate(self.state.question_hashes[:-1]):
                if h == msg_hash and i < len(self.state.recent_questions):
                    prev_q = self.state.recent_questions[i][:60]
                    break
            if prev_q:
                injections.append(
                    f"[状态感知] 你已问过类似问题：「{prev_q}」，"
                    f"可能需要更清晰的回答。"
                )

        # 规则2: 错误恢复
        if self.should_inject_error_context() and self.state.last_tool_error:
            injections.append(
                f"[状态感知] 上一轮工具失败：{self.state.last_tool_error}，"
                f"建议避免重复相同操作。"
            )
            self.reset_error_state()

        # 规则3: 长对话总结
        if self.should_inject_summary():
            topics_s = "、".join(self.state.topics[-5:]) or "暂无"
            decisions_s = "、".join(self.state.key_decisions[-3:]) or "暂无"
            injections.append(
                f"[状态感知] 对话已进行{self.state.message_count}轮。"
                f"话题: {topics_s}。决策: {decisions_s}。"
            )

        # 规则4: 困惑检测
        if self.is_confusion(user_message):
            if self.state.last_tool_error:
                injections.append(
                    f"[状态感知] 上次错误：{self.state.last_tool_error[:80]}"
                )
            if self.state.topics:
                injections.append(
                    f"当前话题: {', '.join(self.state.topics[-3:])}"
                )

        if not injections:
            return ""
        return " | ".join(injections)

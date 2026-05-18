"""
V9.0.0 自适应注入策略 — 根据 context_injection_logs 历史采纳率动态调整注入

- 采纳率 < 30% → 停止注入（避免噪声）
- 采纳率高 → 增加注入条数
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class AdaptiveInjectionPolicy:
    """基于历史反馈的自适应注入控制器"""

    def __init__(self, db_path: str):
        self._db_path = db_path
        self._cache = {}
        self._cache_ttl = 600  # 10分钟

    def should_inject(self, hook_name: str) -> bool:
        """判断是否应在此hook注入上下文"""
        rate = self._get_acceptance_rate(hook_name, days=7)
        return rate >= 0.3

    def get_max_injections(self) -> int:
        """根据采纳率动态计算最大注入条数"""
        rate = self._get_acceptance_rate("pre_llm_call", days=1)
        if rate < 0.2:
            return 1
        elif rate < 0.5:
            return 2
        elif rate < 0.8:
            return 3
        else:
            return 5

    def record_injection(self, hook_name: str, count: int) -> None:
        """记录一次注入事件"""
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            now = datetime.now().isoformat()
            conn.execute(
                "INSERT INTO context_injection_logs "
                "(hook_name, injected_at, injection_count) "
                "VALUES (?, ?, ?)",
                (hook_name, now, count)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def record_acceptance(self, accepted: bool) -> None:
        """记录注入是否被采纳"""
        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)
            conn.execute(
                "UPDATE context_injection_logs SET accepted=? "
                "WHERE id=(SELECT MAX(id) FROM context_injection_logs)",
                (1 if accepted else 0,)
            )
            conn.commit()
            conn.close()
        except Exception:
            pass

    def _get_acceptance_rate(self, hook_name: str, days: int = 7) -> float:
        """查询近N天的注入采纳率"""
        cache_key = (hook_name, days)
        cached = self._cache.get(cache_key)
        if cached:
            ts, rate = cached
            if (datetime.now().timestamp() - ts) < self._cache_ttl:
                return rate

        try:
            import sqlite3
            conn = sqlite3.connect(self._db_path)

            # 如果表不存在，返回默认值允许注入
            table_check = conn.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='context_injection_logs'"
            ).fetchone()
            if not table_check:
                conn.close()
                rate = 1.0
                self._cache[cache_key] = (datetime.now().timestamp(), rate)
                return rate

            cutoff = (datetime.now() - timedelta(days=days)).isoformat()
            row = conn.execute(
                "SELECT COUNT(*) as total, "
                "SUM(CASE WHEN accepted=1 THEN 1 ELSE 0 END) as accepted "
                "FROM context_injection_logs "
                "WHERE hook_name=? AND injected_at >= ?",
                (hook_name, cutoff)
            ).fetchone()
            conn.close()

            total, accepted = row
            if total and total > 0:
                rate = accepted / total if accepted else 0.0
            else:
                rate = 1.0

            self._cache[cache_key] = (datetime.now().timestamp(), rate)
            return rate
        except Exception:
            return 1.0

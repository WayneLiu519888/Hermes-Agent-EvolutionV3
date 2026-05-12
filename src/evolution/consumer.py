"""
V7 关联消费者模块

负责将 HAE 数据库中的关联和经验注入到 LLM 上下文中，
并在 LLM 回复后对关联质量进行打分反馈。

消费链：pre_llm_call → inject_context → LLM → post_llm_call → score_usage
V7.0.6: 三阶段智能匹配 — tags优先 → FTS5全文 → 最近记忆兜底
"""

import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AssociationConsumer:
    """关联消费者：从数据库读取关联，注入上下文，收集反馈"""

    def __init__(self, db_pool):
        self._db_pool = db_pool
        self._injected_ids: List[int] = []

    # ── 上下文注入（V7.0.6：三阶段智能匹配）─────────────────────

    def inject_context(self, user_message: str) -> str:
        """三阶段智能匹配：tags优先 → FTS5全文 → 最近记忆兜底

        不机械切词，让 SQLite 自己匹配。中英文混合消息原生支持。
        """
        if not user_message or len(user_message.strip()) < 3:
            return ""

        try:
            entry_ids = self._match_entries(user_message)
            if not entry_ids:
                return ""

            associations = self._get_associations(entry_ids, limit=3)
            if not associations:
                return ""

            lines = []
            for assoc in associations:
                src_title = assoc.get("src_content", assoc["source_id"])[:30]
                tgt_title = assoc.get("tgt_content", assoc["target_id"])[:30]
                strength = assoc.get("strength", 0.0)
                lines.append(
                    f"{src_title} ↔ {tgt_title}, 强度{strength:.1f}"
                )
                self._injected_ids.append(assoc["id"])

            if lines:
                return "[相关记忆] " + " | ".join(lines)
            return ""

        except Exception as exc:
            logger.warning("关联上下文注入失败: %s", exc)
            return ""

    def _match_entries(self, user_message: str) -> List[str]:
        """三阶段匹配：tags → FTS5 → 最近记忆，任一命中即停止"""
        msg = user_message.strip()

        # S1: tags 匹配（最精确）
        entry_ids = self._match_by_tags(msg)
        if entry_ids:
            logger.debug("S1 tags匹配: %d 条", len(entry_ids))
            return entry_ids

        # S2: FTS5 全文匹配
        entry_ids = self._match_by_fts(msg)
        if entry_ids:
            logger.debug("S2 FTS5匹配: %d 条", len(entry_ids))
            return entry_ids

        # S3: 最近记忆兜底
        entry_ids = self._match_by_recent(limit=5)
        if entry_ids:
            logger.debug("S3 最近记忆: %d 条", len(entry_ids))
            return entry_ids

        return []

    def _match_by_tags(self, message: str) -> List[str]:
        """S1: 用消息中潜在术语匹配 memory_entries.tags"""
        candidates = set(re.findall(r'[\w\u4e00-\u9fff]{2,4}', message.lower()))
        if not candidates:
            return []
        try:
            conn = self._db_pool.get_connection("associations.db")
            cursor = conn.cursor()
            all_ids, seen = [], set()
            for term in candidates:
                cursor.execute(
                    "SELECT id FROM memory_entries WHERE LOWER(tags) LIKE ? LIMIT 5",
                    (f"%{term}%",),
                )
                for row in cursor.fetchall():
                    eid = str(row[0])
                    if eid not in seen:
                        all_ids.append(eid)
                        seen.add(eid)
                        if len(all_ids) >= 15:
                            return all_ids
            return all_ids
        except Exception as exc:
            logger.debug("tags匹配失败: %s", exc)
            return []

    def _match_by_fts(self, message: str) -> List[str]:
        """S2: FTS5 全文匹配，取长度≥3的片段"""
        snippet = message[:200]
        terms = [t for t in re.findall(r'[\w\u4e00-\u9fff]{3,}', snippet)]
        if not terms:
            return []
        query = " OR ".join(f'"{t}"' for t in terms[:6])
        try:
            conn = self._db_pool.get_connection("associations.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM memory_entries_fts WHERE content MATCH ? LIMIT 15",
                (query,),
            )
            return [str(row[0]) for row in cursor.fetchall()]
        except Exception as exc:
            logger.debug("FTS5匹配失败: %s", exc)
            return []

    def _match_by_recent(self, limit: int = 5) -> List[str]:
        """S3: 最近更新的记忆兜底"""
        try:
            conn = self._db_pool.get_connection("associations.db")
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM memory_entries ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            )
            return [str(row[0]) for row in cursor.fetchall()]
        except Exception:
            return []

    # ── 质量反馈 ──────────────────────────────────────────────────

    def score_usage(self, llm_response: str) -> None:
        """LLM 回复后打分"""
        if not self._injected_ids or not llm_response:
            self._injected_ids = []
            return
        try:
            conn = self._db_pool.get_connection("associations.db")
            now = datetime.now().isoformat()
            for assoc_id in self._injected_ids:
                detail = self._get_assoc_detail(conn, assoc_id)
                if not detail:
                    continue
                src_content = detail.get("src_content", "")
                tgt_content = detail.get("tgt_content", "")
                referenced = self._is_referenced(llm_response, src_content, tgt_content)
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT usefulness_score FROM association_usage_stats "
                    "WHERE association_id = ? ORDER BY usage_time DESC LIMIT 1",
                    (assoc_id,),
                )
                row = cursor.fetchone()
                current_score = row[0] if row else 0.5
                new_score = min(1.0, current_score + 0.2) if referenced else max(0.1, current_score - 0.1)
                feedback = "referenced_by_llm" if referenced else "not_referenced"
                conn.execute(
                    "INSERT INTO association_usage_stats "
                    "(association_id, usage_context, usage_time, usefulness_score, feedback) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (assoc_id, json.dumps({"phase": "v7_consumer"}), now, round(new_score, 4), feedback),
                )
                conn.commit()
            logger.debug("已为 %d 条关联打分", len(self._injected_ids))
        except Exception as exc:
            logger.warning("关联打分失败: %s", exc)
        finally:
            self._injected_ids = []

    def cleanup(self) -> None:
        self._injected_ids = []

    # ── 教训召回 ──────────────────────────────────────────────────

    def recall_lessons(self, limit: int = 5, outcome: str = "all") -> List[Dict[str, Any]]:
        try:
            conn = self._db_pool.get_connection("learning_experiences.db")
            cursor = conn.cursor()
            sql = "SELECT id, content, outcome, lessons, metrics, created_at FROM experiences "
            params = []
            if outcome != "all":
                sql += "WHERE outcome = ? "
                params.append(outcome)
            sql += "ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [
                {"id": r[0], "content": r[1], "outcome": r[2], "lessons": r[3],
                 "metrics": r[4], "created_at": r[5]}
                for r in rows
            ]
        except Exception as exc:
            logger.warning("教训召回失败: %s", exc)
            return []

    # ── 私有辅助 ──────────────────────────────────────────────────

    def _get_associations(self, entry_ids: List[str], limit: int = 3) -> List[Dict[str, Any]]:
        try:
            conn = self._db_pool.get_connection("associations.db")
            placeholders = ",".join("?" * len(entry_ids))
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT a.id, a.source_id, a.target_id, a.strength, a.confidence,
                       me_src.content, me_tgt.content
                FROM associations a
                LEFT JOIN memory_entries me_src ON a.source_id = me_src.id
                LEFT JOIN memory_entries me_tgt ON a.target_id = me_tgt.id
                WHERE (a.source_id IN ({placeholders}) OR a.target_id IN ({placeholders}))
                ORDER BY a.strength DESC LIMIT ?
                """,
                entry_ids + entry_ids + [limit],
            )
            return [
                {"id": r[0], "source_id": r[1], "target_id": r[2], "strength": r[3],
                 "confidence": r[4], "src_content": r[5] or "", "tgt_content": r[6] or ""}
                for r in cursor.fetchall()
            ]
        except Exception as exc:
            logger.debug("查询关联失败: %s", exc)
            return []

    @staticmethod
    def _get_assoc_detail(conn, assoc_id: int) -> Optional[Dict[str, Any]]:
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT a.id, me_src.content, me_tgt.content "
                "FROM associations a "
                "LEFT JOIN memory_entries me_src ON a.source_id = me_src.id "
                "LEFT JOIN memory_entries me_tgt ON a.target_id = me_tgt.id "
                "WHERE a.id = ?", (assoc_id,),
            )
            row = cursor.fetchone()
            return {"id": row[0], "src_content": row[1] or "", "tgt_content": row[2] or ""} if row else None
        except Exception as exc:
            logger.debug("获取关联详情失败: %s", exc)
            return None

    @staticmethod
    def _is_referenced(response: str, src_content: str, tgt_content: str) -> bool:
        for kw in re.findall(r'[\w\u4e00-\u9fff]{3,}', src_content + tgt_content):
            if kw in response:
                return True
        return False

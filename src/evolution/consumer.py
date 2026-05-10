"""
V7 关联消费者模块

负责将 HAE 数据库中的关联和经验注入到 LLM 上下文中，
并在 LLM 回复后对关联质量进行打分反馈。

消费链：pre_llm_call → inject_context → LLM → post_llm_call → score_usage
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
        """
        Args:
            db_pool: DatabasePool 实例，用于访问 associations.db 和 memory_entries
        """
        self._db_pool = db_pool
        self._injected_ids: List[int] = []  # 本轮注入的关联ID

    # ── 上下文注入 ────────────────────────────────────────────────

    def inject_context(self, user_message: str) -> str:
        """从用户消息提取关键词，查找相关记忆和关联，生成注入文本

        Args:
            user_message: 用户最新消息

        Returns:
            注入文本（如 "[相关记忆: Python调试 → 异常处理, 强度0.7]"）
            或无匹配时返回空字符串
        """
        if not user_message or len(user_message.strip()) < 3:
            return ""

        try:
            keywords = self._extract_keywords(user_message)
            if not keywords:
                return ""

            # 1. FTS5 查找相关 memory_entries
            entry_ids = self._fts_search(keywords)
            if not entry_ids:
                return ""

            # 2. 查 associations 表，取关联
            associations = self._get_associations(entry_ids, limit=3)
            if not associations:
                return ""

            # 3. 格式化注入文本
            lines = []
            for assoc in associations:
                src_title = assoc.get("src_content", assoc["source_id"])[:30]
                tgt_title = assoc.get("tgt_content", assoc["target_id"])[:30]
                strength = assoc.get("strength", 0.0)
                lines.append(
                    f"# {src_title} ↔ {tgt_title}, 强度{strength:.1f}"
                )
                self._injected_ids.append(assoc["id"])

            if lines:
                return "[相关记忆] " + " | ".join(lines)
            return ""

        except Exception as exc:
            logger.warning("关联上下文注入失败: %s", exc)
            return ""

    # ── 质量反馈 ──────────────────────────────────────────────────

    def score_usage(self, llm_response: str) -> None:
        """LLM 回复后，检查是否引用了本轮注入的关联，更新质量分数

        Args:
            llm_response: LLM 生成的回复文本
        """
        if not self._injected_ids or not llm_response:
            self._injected_ids = []
            return

        try:
            conn = self._db_pool.get_connection("associations.db")
            now = datetime.now().isoformat()

            for assoc_id in self._injected_ids:
                # 获取关联详情判断是否被引用
                detail = self._get_assoc_detail(conn, assoc_id)
                if not detail:
                    continue

                # 检查 LLM 回复是否包含源/目标条目的关键词
                src_content = detail.get("src_content", "")
                tgt_content = detail.get("tgt_content", "")
                referenced = self._is_referenced(llm_response, src_content, tgt_content)

                # 获取当前分数并更新
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT usefulness_score FROM association_usage_stats "
                    "WHERE association_id = ? ORDER BY usage_time DESC LIMIT 1",
                    (assoc_id,),
                )
                row = cursor.fetchone()
                current_score = row[0] if row else 0.5  # 默认中性分

                if referenced:
                    new_score = min(1.0, current_score + 0.2)
                    feedback = "referenced_by_llm"
                else:
                    new_score = max(0.1, current_score - 0.1)
                    feedback = "not_referenced"

                # 写入 association_usage_stats
                conn.execute(
                    "INSERT INTO association_usage_stats "
                    "(association_id, usage_context, usage_time, usefulness_score, feedback) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (assoc_id, json.dumps({"phase": "v7_consumer"}), now,
                     round(new_score, 4), feedback),
                )
                conn.commit()

            logger.debug(
                "已为 %d 条关联打分（注入 %d 条）",
                len(self._injected_ids), len(self._injected_ids),
            )

        except Exception as exc:
            logger.warning("关联打分失败: %s", exc)
        finally:
            self._injected_ids = []

    def cleanup(self) -> None:
        """清理本轮注入ID列表"""
        self._injected_ids = []

    # ── 教训召回 ──────────────────────────────────────────────────

    def recall_lessons(self, limit: int = 5,
                       outcome: str = "all") -> List[Dict[str, Any]]:
        """查询学习经验数据库，返回教训列表

        Args:
            limit: 返回条数
            outcome: 筛选类型（failure/success/all）

        Returns:
            教训列表
        """
        try:
            conn = self._db_pool.get_connection("learning_experiences.db")
            cursor = conn.cursor()

            sql = ("SELECT id, content, outcome, lessons, metrics, created_at "
                   "FROM experiences ")
            params = []

            if outcome != "all":
                sql += "WHERE outcome = ? "
                params.append(outcome)

            sql += "ORDER BY created_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(sql, params)
            rows = cursor.fetchall()

            results = []
            for row in rows:
                entry = {
                    "id": row[0],
                    "content": row[1],
                    "outcome": row[2],
                    "lessons": row[3],
                    "metrics": row[4],
                    "created_at": row[5],
                }
                results.append(entry)

            return results

        except Exception as exc:
            logger.warning("教训召回失败: %s", exc)
            return []

    # ── 私有辅助方法 ──────────────────────────────────────────────

    @staticmethod
    def _extract_keywords(text: str, min_len: int = 2) -> List[str]:
        """从文本提取中文关键词"""
        if not text:
            return []
        segments = re.split(r'[，。！？；：、\s.,!?;:\n\t]+', text)
        keywords = []
        seen = set()
        for seg in segments:
            seg = seg.strip()
            if len(seg) >= min_len and seg not in seen:
                keywords.append(seg)
                seen.add(seg)
                if len(keywords) >= 8:
                    break
        return keywords

    def _fts_search(self, keywords: List[str]) -> List[str]:
        """FTS5 搜索 memory_entries，返回匹配的 entry id 列表"""
        try:
            conn = self._db_pool.get_connection("associations.db")
            # FTS5 表名 memory_entries_fts
            query = " OR ".join(f'"{kw}"' for kw in keywords[:5] if len(kw) >= 2)
            if not query:
                return []

            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM memory_entries_fts WHERE content MATCH ? LIMIT 15",
                (query,),
            )
            return [str(row[0]) for row in cursor.fetchall()]
        except Exception as exc:
            logger.debug("FTS5 搜索失败: %s", exc)
            return []

    def _get_associations(self, entry_ids: List[str],
                          limit: int = 3) -> List[Dict[str, Any]]:
        """根据 entry_ids 查询高质量关联"""
        try:
            conn = self._db_pool.get_connection("associations.db")
            placeholders = ",".join("?" * len(entry_ids))

            # 优先取 usefulness_score 高的关联
            cursor = conn.cursor()
            cursor.execute(
                f"""
                SELECT a.id, a.source_id, a.target_id, a.strength, a.confidence,
                       me_src.content as src_content, me_tgt.content as tgt_content
                FROM associations a
                LEFT JOIN memory_entries me_src ON a.source_id = me_src.id
                LEFT JOIN memory_entries me_tgt ON a.target_id = me_tgt.id
                WHERE (a.source_id IN ({placeholders})
                   OR a.target_id IN ({placeholders}))
                ORDER BY a.strength DESC
                LIMIT ?
                """,
                entry_ids + entry_ids + [limit],
            )

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "source_id": row[1],
                    "target_id": row[2],
                    "strength": row[3],
                    "confidence": row[4],
                    "src_content": row[5] or "",
                    "tgt_content": row[6] or "",
                })
            return results

        except Exception as exc:
            logger.debug("查询关联失败: %s", exc)
            return []

    @staticmethod
    def _get_assoc_detail(conn, assoc_id: int) -> Optional[Dict[str, Any]]:
        """获取单条关联详情"""
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT a.id, me_src.content, me_tgt.content
                FROM associations a
                LEFT JOIN memory_entries me_src ON a.source_id = me_src.id
                LEFT JOIN memory_entries me_tgt ON a.target_id = me_tgt.id
                WHERE a.id = ?
                """,
                (assoc_id,),
            )
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "src_content": row[1] or "", "tgt_content": row[2] or ""}
            return None
        except Exception as exc:
            logger.debug("获取关联详情失败: %s", exc)
            return None

    @staticmethod
    def _is_referenced(response: str, src_content: str,
                       tgt_content: str) -> bool:
        """检查 LLM 回复是否引用了关联的源/目标内容"""
        # 简单判断：回复中是否包含源或目标的关键词
        src_kw = AssociationConsumer._extract_keywords(src_content)
        tgt_kw = AssociationConsumer._extract_keywords(tgt_content)

        for kw in src_kw + tgt_kw:
            if len(kw) >= 3 and kw in response:
                return True
        return False

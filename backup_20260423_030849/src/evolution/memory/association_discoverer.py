"""
记忆系统关联发现器

基于多种算法自动发现记忆条目之间的潜在关联关系，
包括语义关联、时间关联和使用模式关联。
"""

import json
import logging
import math
from datetime import datetime
from itertools import combinations
from typing import Any, Dict, List, Optional, Set, Tuple

from .database import AssociationDatabase

logger = logging.getLogger(__name__)


class AssociationDiscoverer:
    """记忆关联发现器

    使用多种算法自动发现记忆条目之间的关联关系，
    并将发现的关联持久化到 AssociationDatabase 中。

    支持的发现算法：
        - semantic: 基于内容文本的 Jaccard 相似度 + 长度相似度
        - temporal: 基于时间邻近性
        - usage_pattern: 基于共现分析

    Attributes:
        db: AssociationDatabase 实例，用于数据存取
        semantic_threshold: 语义关联的最低强度阈值
        temporal_window_seconds: 时间关联的窗口大小（秒）
        usage_min_cooccurrence: 使用模式关联的最小共现次数
    """

    def __init__(
        self,
        db: AssociationDatabase,
        semantic_threshold: float = 0.15,
        temporal_window_seconds: int = 3600,
        usage_min_cooccurrence: int = 2,
    ) -> None:
        """初始化关联发现器

        Args:
            db: AssociationDatabase 实例
            semantic_threshold: 语义关联强度阈值，低于此值的关联将被忽略
            temporal_window_seconds: 时间邻近性窗口（秒），默认 1 小时
            usage_min_cooccurrence: 使用模式关联的最小共现次数
        """
        self.db = db
        self.semantic_threshold = semantic_threshold
        self.temporal_window_seconds = temporal_window_seconds
        self.usage_min_cooccurrence = usage_min_cooccurrence
        logger.info(
            "关联发现器初始化完成 (semantic_threshold=%.2f, "
            "temporal_window=%ds, usage_min_cooccurrence=%d)",
            semantic_threshold,
            temporal_window_seconds,
            usage_min_cooccurrence,
        )

    # ------------------------------------------------------------------
    # 公共接口
    # ------------------------------------------------------------------

    def discover_all(
        self,
        methods: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """批量发现所有记忆条目之间的关联

        对数据库中的全部记忆条目运行指定的发现算法，
        将新发现的关联写入数据库并记录发现日志。

        Args:
            methods: 要运行的算法列表，可选值为
                     ``'semantic'``、``'temporal'``、``'usage_pattern'``。
                     为 ``None`` 时运行全部三种算法。

        Returns:
            汇总结果字典，包含每种算法的发现数量和总计。
        """
        if methods is None:
            methods = ["semantic", "temporal", "usage_pattern"]

        entries = self._fetch_all_entries()
        logger.info("开始批量关联发现，共 %d 条记忆条目，算法: %s", len(entries), methods)

        results: Dict[str, Any] = {"total_associations": 0, "methods": {}}

        dispatch = {
            "semantic": self._discover_semantic,
            "temporal": self._discover_temporal,
            "usage_pattern": self._discover_usage_pattern,
        }

        for method in methods:
            func = dispatch.get(method)
            if func is None:
                logger.warning("未知的发现算法: %s，已跳过", method)
                continue

            start_time = datetime.now()
            try:
                discovered = func(entries)
                end_time = datetime.now()
                self._log_discovery(
                    method=method,
                    parameters=self._current_parameters(method),
                    start_time=start_time,
                    end_time=end_time,
                    entries_processed=len(entries),
                    associations_discovered=discovered,
                )
                results["methods"][method] = {
                    "associations_discovered": discovered,
                    "entries_processed": len(entries),
                    "duration_seconds": (end_time - start_time).total_seconds(),
                }
                results["total_associations"] += discovered
                logger.info(
                    "算法 [%s] 完成，发现 %d 条关联", method, discovered
                )
            except Exception as exc:
                end_time = datetime.now()
                self._log_discovery(
                    method=method,
                    parameters=self._current_parameters(method),
                    start_time=start_time,
                    end_time=end_time,
                    entries_processed=len(entries),
                    associations_discovered=0,
                    error_message=str(exc),
                )
                logger.error("算法 [%s] 执行失败: %s", method, exc, exc_info=True)
                results["methods"][method] = {"error": str(exc)}

        logger.info("批量关联发现完成，共发现 %d 条关联", results["total_associations"])
        return results

    def discover_for_entry(
        self,
        entry_id: str,
        methods: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """为单个记忆条目发现关联

        将指定条目与数据库中所有其他条目进行比较，
        运行指定的发现算法并写入新关联。

        Args:
            entry_id: 目标记忆条目 ID
            methods: 要运行的算法列表，为 ``None`` 时运行全部三种。

        Returns:
            汇总结果字典。

        Raises:
            ValueError: 当 entry_id 对应的条目不存在时抛出。
        """
        if methods is None:
            methods = ["semantic", "temporal", "usage_pattern"]

        target_entry = self.db.get_memory_entry(entry_id)
        if target_entry is None:
            raise ValueError(f"记忆条目不存在: {entry_id}")

        all_entries = self._fetch_all_entries()
        # 将目标条目与其余条目配对
        other_entries = [e for e in all_entries if e["id"] != entry_id]
        logger.info(
            "为条目 [%s] 发现关联，候选条目 %d 条，算法: %s",
            entry_id,
            len(other_entries),
            methods,
        )

        results: Dict[str, Any] = {"entry_id": entry_id, "total_associations": 0, "methods": {}}

        dispatch = {
            "semantic": self._discover_semantic_for_pair,
            "temporal": self._discover_temporal_for_pair,
            "usage_pattern": self._discover_usage_pattern_for_pair,
        }

        for method in methods:
            func = dispatch.get(method)
            if func is None:
                logger.warning("未知的发现算法: %s，已跳过", method)
                continue

            start_time = datetime.now()
            try:
                discovered = 0
                for other in other_entries:
                    discovered += func(target_entry, other)
                end_time = datetime.now()
                self._log_discovery(
                    method=method,
                    parameters=self._current_parameters(method),
                    start_time=start_time,
                    end_time=end_time,
                    entries_processed=len(other_entries) + 1,
                    associations_discovered=discovered,
                )
                results["methods"][method] = {
                    "associations_discovered": discovered,
                    "duration_seconds": (end_time - start_time).total_seconds(),
                }
                results["total_associations"] += discovered
                logger.info(
                    "算法 [%s] 为条目 [%s] 发现 %d 条关联",
                    method,
                    entry_id,
                    discovered,
                )
            except Exception as exc:
                end_time = datetime.now()
                self._log_discovery(
                    method=method,
                    parameters=self._current_parameters(method),
                    start_time=start_time,
                    end_time=end_time,
                    entries_processed=len(other_entries) + 1,
                    associations_discovered=0,
                    error_message=str(exc),
                )
                logger.error(
                    "算法 [%s] 为条目 [%s] 执行失败: %s",
                    method,
                    entry_id,
                    exc,
                    exc_info=True,
                )
                results["methods"][method] = {"error": str(exc)}

        return results

    # ------------------------------------------------------------------
    # 语义关联发现
    # ------------------------------------------------------------------

    def _discover_semantic(self, entries: List[Dict[str, Any]]) -> int:
        """对所有条目两两计算语义相似度并写入关联

        相似度 = 0.7 * jaccard_similarity + 0.3 * length_similarity

        Args:
            entries: 全部记忆条目列表

        Returns:
            新发现的关联数量
        """
        discovered = 0
        for entry_a, entry_b in combinations(entries, 2):
            discovered += self._discover_semantic_for_pair(entry_a, entry_b)
        return discovered

    def _discover_semantic_for_pair(
        self,
        entry_a: Dict[str, Any],
        entry_b: Dict[str, Any],
    ) -> int:
        """计算两个条目的语义相似度，满足阈值则写入关联

        Args:
            entry_a: 第一个记忆条目
            entry_b: 第二个记忆条目

        Returns:
            1 表示写入了新关联，0 表示未写入
        """
        content_a: str = entry_a.get("content", "")
        content_b: str = entry_b.get("content", "")

        jaccard = self._jaccard_similarity(content_a, content_b)
        length_sim = self._length_similarity(content_a, content_b)
        strength = 0.7 * jaccard + 0.3 * length_sim

        if strength < self.semantic_threshold:
            return 0

        confidence = min(1.0, strength * 1.2)
        try:
            self.db.add_association(
                source_id=entry_a["id"],
                target_id=entry_b["id"],
                association_type="semantic",
                strength=round(strength, 4),
                confidence=round(confidence, 4),
                metadata={
                    "jaccard_similarity": round(jaccard, 4),
                    "length_similarity": round(length_sim, 4),
                    "algorithm": "jaccard+length",
                },
            )
            return 1
        except Exception as exc:
            logger.debug(
                "写入语义关联失败 (%s -> %s): %s",
                entry_a["id"],
                entry_b["id"],
                exc,
            )
            return 0

    @staticmethod
    def _jaccard_similarity(text_a: str, text_b: str) -> float:
        """计算两段文本的 Jaccard 相似度（基于字符级 bigram）

        Args:
            text_a: 文本 A
            text_b: 文本 B

        Returns:
            Jaccard 相似度，范围 [0, 1]
        """
        if not text_a or not text_b:
            return 0.0

        def _bigrams(text: str) -> Set[str]:
            text = text.lower().strip()
            return {text[i: i + 2] for i in range(len(text) - 1)} if len(text) >= 2 else {text}

        set_a = _bigrams(text_a)
        set_b = _bigrams(text_b)
        intersection = set_a & set_b
        union = set_a | set_b
        if not union:
            return 0.0
        return len(intersection) / len(union)

    @staticmethod
    def _length_similarity(text_a: str, text_b: str) -> float:
        """计算两段文本的长度相似度

        使用公式: 1 - |len_a - len_b| / max(len_a, len_b)

        Args:
            text_a: 文本 A
            text_b: 文本 B

        Returns:
            长度相似度，范围 [0, 1]
        """
        len_a = len(text_a)
        len_b = len(text_b)
        if len_a == 0 and len_b == 0:
            return 1.0
        max_len = max(len_a, len_b)
        return 1.0 - abs(len_a - len_b) / max_len

    # ------------------------------------------------------------------
    # 时间关联发现
    # ------------------------------------------------------------------

    def _discover_temporal(self, entries: List[Dict[str, Any]]) -> int:
        """对所有条目两两计算时间邻近性并写入关联

        Args:
            entries: 全部记忆条目列表

        Returns:
            新发现的关联数量
        """
        discovered = 0
        for entry_a, entry_b in combinations(entries, 2):
            discovered += self._discover_temporal_for_pair(entry_a, entry_b)
        return discovered

    def _discover_temporal_for_pair(
        self,
        entry_a: Dict[str, Any],
        entry_b: Dict[str, Any],
    ) -> int:
        """计算两个条目的时间邻近性，满足窗口则写入关联

        使用指数衰减: strength = exp(-delta / window)

        Args:
            entry_a: 第一个记忆条目
            entry_b: 第二个记忆条目

        Returns:
            1 表示写入了新关联，0 表示未写入
        """
        time_a = self._parse_datetime(entry_a.get("created_at"))
        time_b = self._parse_datetime(entry_b.get("created_at"))
        if time_a is None or time_b is None:
            return 0

        delta_seconds = abs((time_a - time_b).total_seconds())
        if delta_seconds > self.temporal_window_seconds:
            return 0

        # 指数衰减，窗口内越近强度越高
        strength = math.exp(-delta_seconds / self.temporal_window_seconds)
        confidence = strength  # 时间关联的置信度与强度一致

        try:
            self.db.add_association(
                source_id=entry_a["id"],
                target_id=entry_b["id"],
                association_type="temporal",
                strength=round(strength, 4),
                confidence=round(confidence, 4),
                metadata={
                    "delta_seconds": round(delta_seconds, 2),
                    "window_seconds": self.temporal_window_seconds,
                    "algorithm": "exponential_decay",
                },
            )
            return 1
        except Exception as exc:
            logger.debug(
                "写入时间关联失败 (%s -> %s): %s",
                entry_a["id"],
                entry_b["id"],
                exc,
            )
            return 0

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        """安全地将字符串解析为 datetime

        Args:
            value: 日期时间字符串或 None

        Returns:
            解析后的 datetime 对象，解析失败返回 None
        """
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(str(value))
        except (ValueError, TypeError):
            return None

    # ------------------------------------------------------------------
    # 使用模式关联发现
    # ------------------------------------------------------------------

    def _discover_usage_pattern(self, entries: List[Dict[str, Any]]) -> int:
        """基于共现分析发现使用模式关联

        共现定义：两个条目在同一使用上下文（usage_context）中被使用过。
        当共现次数 >= usage_min_cooccurrence 时建立关联。

        Args:
            entries: 全部记忆条目列表

        Returns:
            新发现的关联数量
        """
        cooccurrence = self._build_cooccurrence_map()
        if not cooccurrence:
            logger.info("未发现使用模式共现数据")
            return 0

        discovered = 0
        for (id_a, id_b), count in cooccurrence.items():
            if count < self.usage_min_cooccurrence:
                continue
            # 强度与共现次数正相关，使用对数缩放避免过大
            strength = min(1.0, math.log1p(count) / math.log1p(10))
            confidence = min(1.0, count / (count + 2))  # 贝叶斯平滑

            try:
                self.db.add_association(
                    source_id=id_a,
                    target_id=id_b,
                    association_type="usage_pattern",
                    strength=round(strength, 4),
                    confidence=round(confidence, 4),
                    metadata={
                        "cooccurrence_count": count,
                        "algorithm": "cooccurrence_analysis",
                    },
                )
                discovered += 1
            except Exception as exc:
                logger.debug(
                    "写入使用模式关联失败 (%s -> %s): %s", id_a, id_b, exc
                )
        return discovered

    def _discover_usage_pattern_for_pair(
        self,
        entry_a: Dict[str, Any],
        entry_b: Dict[str, Any],
    ) -> int:
        """检查两个条目是否存在使用模式共现关联

        Args:
            entry_a: 第一个记忆条目
            entry_b: 第二个记忆条目

        Returns:
            1 表示写入了新关联，0 表示未写入
        """
        id_a = entry_a["id"]
        id_b = entry_b["id"]
        count = self._count_cooccurrence(id_a, id_b)
        if count < self.usage_min_cooccurrence:
            return 0

        strength = min(1.0, math.log1p(count) / math.log1p(10))
        confidence = min(1.0, count / (count + 2))

        try:
            self.db.add_association(
                source_id=id_a,
                target_id=id_b,
                association_type="usage_pattern",
                strength=round(strength, 4),
                confidence=round(confidence, 4),
                metadata={
                    "cooccurrence_count": count,
                    "algorithm": "cooccurrence_analysis",
                },
            )
            return 1
        except Exception as exc:
            logger.debug(
                "写入使用模式关联失败 (%s -> %s): %s", id_a, id_b, exc
            )
            return 0

    def _build_cooccurrence_map(self) -> Dict[Tuple[str, str], int]:
        """从 association_usage_stats 构建共现计数映射

        同一 usage_context 下被使用的不同关联所涉及的条目视为共现。

        Returns:
            键为 (entry_id_a, entry_id_b) 的共现次数字典（id 按字典序排列）
        """
        try:
            cursor = self.db.connection.cursor()
            # 获取每个 usage_context 下涉及的所有条目 ID
            cursor.execute(
                """
                SELECT aus.usage_context, a.source_id, a.target_id
                FROM association_usage_stats aus
                JOIN associations a ON aus.association_id = a.id
                ORDER BY aus.usage_context
                """
            )
            rows = cursor.fetchall()
        except Exception as exc:
            logger.error("查询共现数据失败: %s", exc)
            return {}

        # 按 usage_context 分组收集涉及的条目 ID
        context_entries: Dict[str, Set[str]] = {}
        for row in rows:
            ctx = row[0] if isinstance(row, (tuple, list)) else row["usage_context"]
            src = row[1] if isinstance(row, (tuple, list)) else row["source_id"]
            tgt = row[2] if isinstance(row, (tuple, list)) else row["target_id"]
            context_entries.setdefault(ctx, set()).update([src, tgt])

        # 统计共现
        cooccurrence: Dict[Tuple[str, str], int] = {}
        for entry_ids in context_entries.values():
            for id_a, id_b in combinations(sorted(entry_ids), 2):
                pair = (id_a, id_b)
                cooccurrence[pair] = cooccurrence.get(pair, 0) + 1

        return cooccurrence

    def _count_cooccurrence(self, id_a: str, id_b: str) -> int:
        """计算两个条目的共现次数

        Args:
            id_a: 条目 A 的 ID
            id_b: 条目 B 的 ID

        Returns:
            共现次数
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                SELECT COUNT(DISTINCT aus1.usage_context) AS cnt
                FROM association_usage_stats aus1
                JOIN associations a1 ON aus1.association_id = a1.id
                JOIN association_usage_stats aus2 ON aus1.usage_context = aus2.usage_context
                    AND aus1.id != aus2.id
                JOIN associations a2 ON aus2.association_id = a2.id
                WHERE (a1.source_id = ? OR a1.target_id = ?)
                  AND (a2.source_id = ? OR a2.target_id = ?)
                """,
                (id_a, id_a, id_b, id_b),
            )
            row = cursor.fetchone()
            return row[0] if row else 0
        except Exception as exc:
            logger.error("查询共现次数失败 (%s, %s): %s", id_a, id_b, exc)
            return 0

    # ------------------------------------------------------------------
    # 内部工具方法
    # ------------------------------------------------------------------

    def _fetch_all_entries(self) -> List[Dict[str, Any]]:
        """从数据库获取全部记忆条目

        Returns:
            记忆条目字典列表
        """
        try:
            cursor = self.db.connection.cursor()
            cursor.execute("SELECT * FROM memory_entries")
            rows = cursor.fetchall()
            return [self.db._row_to_dict(row) for row in rows]
        except Exception as exc:
            logger.error("获取全部记忆条目失败: %s", exc)
            return []

    def _current_parameters(self, method: str) -> Dict[str, Any]:
        """返回当前算法参数快照

        Args:
            method: 算法名称

        Returns:
            参数字典
        """
        params: Dict[str, Any] = {"method": method}
        if method == "semantic":
            params["threshold"] = self.semantic_threshold
        elif method == "temporal":
            params["window_seconds"] = self.temporal_window_seconds
        elif method == "usage_pattern":
            params["min_cooccurrence"] = self.usage_min_cooccurrence
        return params

    def _log_discovery(
        self,
        method: str,
        parameters: Dict[str, Any],
        start_time: datetime,
        end_time: datetime,
        entries_processed: int,
        associations_discovered: int,
        error_message: Optional[str] = None,
    ) -> None:
        """将发现过程记录到 association_discovery_logs 表

        Args:
            method: 发现算法名称
            parameters: 算法参数
            start_time: 开始时间
            end_time: 结束时间
            entries_processed: 处理的条目数
            associations_discovered: 发现的关联数
            error_message: 错误信息（如有）
        """
        success_rate = 0.0
        if entries_processed > 0 and error_message is None:
            # 成功率 = 发现数 / 可能的配对数（至少为 1 避免除零）
            possible_pairs = max(1, entries_processed * (entries_processed - 1) // 2)
            success_rate = round(associations_discovered / possible_pairs, 4)

        try:
            cursor = self.db.connection.cursor()
            cursor.execute(
                """
                INSERT INTO association_discovery_logs
                    (discovery_method, parameters, start_time, end_time,
                     memory_entries_processed, associations_discovered,
                     success_rate, error_message, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    method,
                    json.dumps(parameters, ensure_ascii=False),
                    start_time.isoformat(),
                    end_time.isoformat(),
                    entries_processed,
                    associations_discovered,
                    success_rate,
                    error_message,
                    json.dumps({}, ensure_ascii=False),
                ),
            )
            self.db.connection.commit()
        except Exception as exc:
            logger.error("写入发现日志失败: %s", exc)

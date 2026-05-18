"""
V9.0.0 Embedding语义匹配器 — TF-IDF向量化 + 余弦相似度

为 inject_context() 提供语义向量匹配，增强"那个报错"→"NullPointerException"的召回。
numpy不可用时自动降级为纯文本匹配，不影响现有功能。
"""

import logging
import re
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

_HAS_NUMPY = False
try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    pass


class EmbeddingMatcher:
    """TF-IDF向量语义匹配（零外部依赖，numpy加速可选）"""

    def __init__(self):
        self._memory_texts: List[Tuple[int, str]] = []
        self._vectors: Optional[List] = None
        self._vocab: dict = {}
        self._idf: Optional[List] = None

    def index_entries(self, entries: List[Tuple[int, str]]) -> None:
        """索引 memory_entries 文本"""
        if not entries:
            return

        try:
            self._memory_texts = entries

            # 构建词表
            word_to_idx = {}
            docs = []
            for _, text in entries:
                words = self._tokenize(text)
                doc = {}
                for w in words:
                    if w not in word_to_idx:
                        word_to_idx[w] = len(word_to_idx)
                    doc[word_to_idx[w]] = doc.get(word_to_idx[w], 0) + 1
                docs.append(doc)

            self._vocab = word_to_idx

            if not _HAS_NUMPY or not docs:
                return

            n_docs = len(docs)
            n_vocab = len(word_to_idx)
            vectors = np.zeros((n_docs, n_vocab))

            # IDF
            df = np.zeros(n_vocab)
            for doc in docs:
                for idx in doc:
                    df[idx] += 1
            idf = np.log((n_docs + 1) / (df + 1)) + 1

            # TF-IDF
            for i, doc in enumerate(docs):
                for idx, tf in doc.items():
                    vectors[i, idx] = tf * idf[idx]

            # L2归一化
            norms = np.linalg.norm(vectors, axis=1, keepdims=True)
            norms[norms == 0] = 1
            vectors = vectors / norms

            self._vectors = vectors
            self._idf = idf
            logger.debug("Embedding索引: %d条目, %d词", n_docs, n_vocab)
        except Exception as e:
            logger.debug("Embedding索引降级: %s", e)

    def search(self, query: str, top_k: int = 5) -> List[Tuple[int, float]]:
        """搜索最相似的条目 → [(entry_id, similarity), ...]"""
        if not self._memory_texts:
            return []

        # numpy模式
        if _HAS_NUMPY and self._vectors is not None:
            return self._search_numpy(query, top_k)

        # 纯文本模式（降级）
        return self._search_text(query, top_k)

    def _search_numpy(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        try:
            words = self._tokenize(query)
            q_vec = np.zeros(len(self._vocab))
            for w in words:
                if w in self._vocab:
                    q_vec[self._vocab[w]] += 1

            norm = np.linalg.norm(q_vec)
            if norm > 0:
                q_vec /= norm

            similarities = self._vectors.dot(q_vec)
            top_indices = np.argsort(similarities)[::-1][:top_k]

            results = []
            for idx in top_indices:
                sim = float(similarities[idx])
                if sim > 0.1:
                    entry_id, _ = self._memory_texts[idx]
                    results.append((entry_id, sim))
            return results
        except Exception:
            return []

    def _search_text(self, query: str, top_k: int) -> List[Tuple[int, float]]:
        """纯文本匹配降级：Jaccard相似度"""
        q_words = set(self._tokenize(query))
        if not q_words:
            return []

        scored = []
        for entry_id, text in self._memory_texts:
            t_words = set(self._tokenize(text))
            if not t_words:
                continue
            intersection = q_words & t_words
            union = q_words | t_words
            jaccard = len(intersection) / len(union) if union else 0
            if jaccard > 0.05:
                scored.append((entry_id, jaccard))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def _tokenize(self, text: str) -> List[str]:
        """分词：英文单词 + 中文双字组合 + 数字"""
        tokens = []
        # 英文单词
        tokens.extend(re.findall(r'[a-zA-Z_]\w+', text.lower()))
        # 中文双字
        chinese = ''.join(re.findall(r'[\u4e00-\u9fff]', text))
        for i in range(len(chinese) - 1):
            tokens.append(chinese[i:i + 2])
        # 单字
        tokens.extend(list(chinese))
        # 数字
        tokens.extend(re.findall(r'\d+', text))
        return tokens[:100]

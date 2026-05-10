# src/evolution/memory/memory_tier.py

from collections import OrderedDict
from typing import Optional, Any, Dict, List
import time

class MemoryTier:
    """分层记忆管理器
    
    L1 (热): 内存 OrderedDict，LRU 淘汰，容量 1000
    L2 (温): SQLite 主库，全量存储
    L3 (冷): 定期归档清理（低于阈值的关联/经验）
    """
    
    def __init__(self, max_hot: int = 1000, cold_threshold_days: int = 30):
        self._hot = OrderedDict()
        self._max_hot = max_hot
        self._cold_threshold_days = cold_threshold_days
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
    
    def get(self, key: str) -> Optional[Any]:
        if key in self._hot:
            self._hot.move_to_end(key)
            self._stats["hits"] += 1
            return self._hot[key]
        self._stats["misses"] += 1
        return None
    
    def put(self, key: str, value: Any):
        if key in self._hot:
            self._hot.move_to_end(key)
        else:
            if len(self._hot) >= self._max_hot:
                self._hot.popitem(last=False)
                self._stats["evictions"] += 1
        self._hot[key] = value
    
    def invalidate(self, key: str):
        self._hot.pop(key, None)
    
    def stats(self) -> Dict[str, int]:
        return {**self._stats, "size": len(self._hot), "max": self._max_hot}
    
    def warm_to_cold_query(self, cutoff_timestamp: str) -> str:
        """生成查询 L2→L3 归档的 SQL 条件"""
        return f"timestamp < '{cutoff_timestamp}' AND (quality_score IS NULL OR quality_score < 0.3)"

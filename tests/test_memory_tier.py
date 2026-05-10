import pytest
from evolution.memory.memory_tier import MemoryTier


def test_put_get():
    tier = MemoryTier(max_hot=10)
    tier.put("k1", "v1")
    assert tier.get("k1") == "v1"


def test_lru_eviction():
    tier = MemoryTier(max_hot=3)
    for i in range(5):
        tier.put(f"k{i}", f"v{i}")
    assert tier.get("k0") is None  # 被淘汰
    assert tier.get("k4") == "v4"  # 最新保留

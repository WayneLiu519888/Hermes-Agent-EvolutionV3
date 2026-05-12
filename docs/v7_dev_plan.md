# V7 开发计划

## 任务总览

| 组 | 任务 | 文件 | 预计 |
|----|------|------|------|
| A | 重写关联算法 | `association_discoverer.py` | 80行 |
| B | 新建消费者模块 | `consumer.py`（新文件） | 250行 |
| C | Hook集成+新工具 | `plugin_core.py` | 120行 |
| D | 测试+验证 | `tests/` | 200行 |

每组完成暂停，等你确认再继续。

---

## A组：重写关联算法

### A1. 删除旧代码
- 删除 `_jaccard_similarity()` 方法
- 删除 `_length_similarity()` 方法
- 保留 `_discover_semantic()` 方法签名，重写实现

### A2. 实现 `_discover_semantic_v2`
三路匹配，批量写入：

```python
def _discover_semantic(self, entries: List[Dict], limit_per_source: int = 100) -> int:
```

**路1：tags交集（weight 0.5）**
- 解析每条 entry 的 `tags` 字段（逗号分隔或 JSON 数组）
- 两两计算 `交集大小 / max(len_a, len_b)`
- 得分 = 交集率 × 0.5

**路2：content_type匹配（weight 0.3）**
- 直接字符串比较 `entry_a["content_type"] == entry_b["content_type"]`
- 相同得 0.3

**路3：FTS5关键词共现（weight 0.2）**
- 对 entry_a 的 content 取前5个最长的词作为关键词
- 用 FTS5 查询 `SELECT id FROM memory_entries_fts WHERE content MATCH ?`
- 对匹配到的 entry_b 检查关键词重叠率
- 得分 = 重叠率 × 0.2

**合并阈值**：总分 ≥ 0.2 写入，confidence = min(1.0, 总分 × 1.3)

**分批策略**：每批50条为一个事务，复用 `executemany` 批量插入

### A3. 验证
```bash
# 用少量数据测试，确认生成的关联有意义
python3 -c "
from evolution.memory.association_discoverer import AssociationDiscoverer
# 模拟10条中文记忆，检查关联质量
"
```

---

## B组：新建消费者模块

### B1. 创建 `src/evolution/consumer.py`

```python
class AssociationConsumer:
    def __init__(self, db_pool):
        self.db = db_pool        # 访问 associations.db
        self._injected_ids = []  # 本轮注入的关联ID

    def inject_context(self, user_message: str) -> str:
        """
        1. 从用户消息提取中文关键词（按字符数≥2的无标点片段）
        2. 用 FTS5 查 memory_entries 找相关记忆
        3. 根据 entry_id 查 associations，按 usefulness_score 降序
        4. 取 top 3，生成注入文本
        返回: "[相关记忆: #123 Python调试 → #456 异常处理, 强度0.7]..."
        或空字符串（无匹配时）
        """

    def score_usage(self, llm_response: str) -> None:
        """
        检查 LLM 回复是否引用了本轮注入的关联
        对每条注入的关联：
        - 回复包含对应条目关键词 → usefulness_score += 0.2
        - 回复完全无关 → usefulness_score -= 0.1
        写入 association_usage_stats 表
        """

    def cleanup(self):
        """清理本轮注入ID列表"""
        self._injected_ids = []
```

### B2. 关键词提取（不引入 jieba 依赖）

```python
def _extract_keywords(text: str, min_len: int = 2) -> List[str]:
    """简单的中文关键词提取：按标点切分，取长度≥2的片段"""
    import re
    segments = re.split(r'[，。！？；：、\s]+', text)
    keywords = []
    for seg in segments:
        if len(seg) >= min_len:
            keywords.append(seg)
    return keywords[:10]  # 最多10个
```

### B3. FTS5 查询

```python
def _fts_search(self, keywords: List[str]) -> List[str]:
    """对每个关键词做 FTS5 匹配，返回匹配的 entry_id 列表"""
    # memory_entries 表已建 FTS5 虚拟表 memory_entries_fts
    query = " OR ".join(f'"{kw}"' for kw in keywords[:5])
    cursor = self.db.connection.execute(
        "SELECT id FROM memory_entries_fts WHERE content MATCH ? LIMIT 20",
        (query,)
    )
    return [row[0] for row in cursor.fetchall()]
```

---

## C组：Hook集成

### C1. 在 `plugin_core.py` 中注册三个新 Hook

**on_session_start**（新增）
```python
def _on_session_start(session_id, model, platform, **kwargs):
    """会话启动：注入最近失败教训到 hermes memory"""
    # 1. 查 learning_experiences.db，outcome='failure', 最近7天, 取3条
    # 2. 每条压缩到 ≤100字
    # 3. 写入 hermes memory（直接操作 hermes_state.db 的 memory 表
    #    或通过 ~/.hermes/memory/ 目录）
    # key = f"hae_lessons_{session_id[:8]}", 24h TTL
```

**pre_llm_call**（新增）
```python
def _on_pre_llm_call(messages, model, **kwargs):
    """LLM 调用前：注入关联上下文到用户消息"""
    # 1. 取最后一条 user 消息
    # 2. consumer.inject_context(user_msg)
    # 3. 如果有注入内容，追加到 user 消息尾部
    # 4. 记录 injected_ids
    return messages
```

**post_llm_call**（注册新hook，不修改现有 post_tool_call）
```python
def _on_post_llm_call(response, messages, model, **kwargs):
    """LLM 回复后：打分"""
    # 1. consumer.score_usage(response)
    # 2. consumer.cleanup()
```

### C2. 注册新工具 `evolution_recall_lessons`

Schema 已在设计文档中定义。Handler 实现：
```python
def _handle_recall_lessons(params, **kwargs):
    limit = params.get("limit", 5)
    outcome = params.get("outcome", "all")
    # 查 learning_experiences.db
    # 返回 JSON 格式的教训列表
```

### C3. 在 `register()` 函数中注册

```python
ctx.register_hook("on_session_start", _on_session_start)
ctx.register_hook("pre_llm_call", _on_pre_llm_call)
ctx.register_hook("post_llm_call", _on_post_llm_call)
# ... 现有 post_tool_call 不变
# ... 新增 evolution_recall_lessons 工具注册
```

---

## D组：测试+验证

### D1. 单元测试 `tests/test_v7_consumer.py`
- test_extract_keywords：提取中文关键词
- test_fts_search：FTS5 匹配
- test_inject_context：生成注入文本
- test_score_usage_up：引用后加分
- test_score_usage_down：未引用降分

### D2. 集成测试
- test_session_start_hook：on_session_start 写入教训
- test_pre_llm_call_hook：pre_llm_call 注入上下文
- test_post_llm_call_hook：post_llm_call 打分
- test_recall_lessons_tool：evolution_recall_lessons 返回数据

### D3. 全量回归
```bash
python3 -m pytest tests/ -q --tb=short --ignore=tests/test_cli.py
# 目标：566 passed，无新增失败
```

---

## 执行顺序

```
A组（算法）→ B组（消费者）→ C组（Hook）→ D组（测试）
```

每组完成后：
1. 运行相关测试
2. 暂停，等你确认
3. 继续下一组

---

## 开发后优化记录

### V7.0.6：三阶段智能匹配

原 B 组的 `consumer.py` 设计为 `_extract_keywords` + `_fts_search`，开发后暴露出问题：
- 机械切词仅限中文，英文消息匹配失败
- FTS5 索引配置错误（content_rowid='id'）导致 S2 从未生效

**实际优化实现**（迭代于 V7.0.6）：
- `inject_context` 重写为 `_match_entries` 三阶段
- S1: tags LIKE（公式 `[\w\u4e00-\u9fff]{2,4}` 支持混合语言）
- S2: FTS5 MATCH
- S3: ORDER BY updated_at DESC 兜底

### V7.0.7：FTS5 修复 + 采纳日志

- `database.py` FTS5 content_rowid 从 'id' 改为 'rowid'
- 旧表自动检测 DROP + REBUILD
- 新增 `context_injection_logs` 表，score_usage 写入采纳记录

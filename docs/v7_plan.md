# V7 设计方案：HAE数据消费闭环

## 一、架构设计

### 1.1 现状问题

```
写入层（已有）                    消费层（缺失）
─────────────────────────────────────────────────
evolution_learn      ───→  learning_experiences.db    ✗ 从未被 LLM 读取
evolution_memory_discover ─→  associations.db          ✗ 从未在 thinking 中用到
evolution_self_monitor ───→  health score             ✗ 从未触发自动修复
```

**V6的修复**：加了 `max_entries` 防止 OOM，但数据依然是"写了没人读"的死数据。

### 1.2 V7 架构目标

```
写入层                          消费层（V7新建）
───────────────────────────────────────────────
evolution_learn     ───→  learning_experiences.db  ───→  on_session_start hook
                                                         注入最近失败教训到 memory
evolution_memory_discover ─→  associations.db        ───→  pre_llm_call hook
                                                         查关联+注入上下文
                                                            ↓
                             post_llm_call hook ───────── 打分+反馈
                                                            ↓
                             association_usage_stats ──── 质量筛选正循环
```

### 1.3 模块边界

| 层 | 模块 | 改动类型 |
|----|------|----------|
| **算法层** | `memory/association_discoverer.py` | 重写 `_discover_semantic` |
| **Hook层** | `plugin_core.py` | 新增3个hook注册 + 消费逻辑 |
| **工具层** | `plugin_core.py` | 新增 `evolution_recall_lessons` 工具 |

---

## 二、概要设计

### 2.1 数据流总览

```
会话开始 ──→ on_session_start: 查学习经验DB → 注入3条教训到hermes memory
    ↓
用户消息到达
    ↓
pre_llm_call: 对用户消息FTS5匹配 → 查memory_entries → 查associations
             → 取top3关联 → 追加到消息尾部(≤200字)
    ↓
LLM生成回复
    ↓
post_llm_call: 检测回复是否引用了注入的关联
             → 写入 usefulness_score 到 association_usage_stats
```

### 2.2 上下文预算

| 注入点 | 内容 | 字数 |
|--------|------|------|
| on_session_start | 3条失败教训 | ≤300字 |
| pre_llm_call | top3关联上下文 | ≤200字 |
| **合计** | | **≤500字/轮** |

### 2.3 关联质量体系

```
高质量(score≥0.7)：每轮优先注入
中质(0.3-0.7)：每3轮注入一次
低质(<0.3)：不注入，定期清理
```

---

## 三、详细设计

### 3.1 算法替换（association_discoverer.py）

#### 删除
- `_jaccard_similarity()` — 中文下无效
- `_length_similarity()` — 辅助指标，无独立价值
- `_discover_semantic()` 中的 combinations(N,2) 全量配对逻辑

#### 新增：`_discover_semantic_v2(entries, limit=200)`

三路并行匹配，每路取 top N：

**路1：tags交集匹配（weight=0.5）**
```python
# 两条记忆的 tags 字段取交集，交集越大分越高
intersection = set(tags_a) & set(tags_b)
strength = len(intersection) / max(len(tags_a), len(tags_b), 1) * 0.5
```

**路2：content_type匹配（weight=0.3）**
```python
# 同类型记忆天然关联
if entry_a["content_type"] == entry_b["content_type"]:
    strength += 0.3
```

**路3：FTS5关键词共现（weight=0.2）**
```sql
-- 对 content_a 提取前5个稀有词，查 FTS5 匹配
SELECT id FROM memory_entries_fts WHERE content MATCH ? LIMIT 20
```
```python
# 两两计算关键词重叠率
overlap = len(words_a & words_b) / max(len(words_a), len(words_b), 1)
strength += overlap * 0.2
```

**合并阈值**：strength ≥ 0.2 才写入关联，confidence = min(1.0, strength * 1.3)

**分批策略**：每批50条entries，每批一次COMMIT，复用现有 `max_entries` 和 `_enforce_association_limit`。

### 3.2 消费链实现（plugin_core.py 新增）

#### 3.2.1 新增模块：`src/evolution/consumer.py`（~250行）

```python
class AssociationConsumer:
    """关联消费者：注入上下文 + 打分"""
    
    def inject_context(self, user_message: str) -> str:
        """从用户消息提取关键词 → 查FTS5 → 查associations → 生成注入文本"""
        # 1. FTS5 匹配 memory_entries
        # 2. 根据匹配到的 entry_id 查 associations
        # 3. 按 usefulness_score 排序取 top 3
        # 4. 返回格式化的注入文本
        
    def score_usage(self, injected_ids: List[int], llm_response: str) -> None:
        """LLM回复后，检查是否引用注入的关联，更新分数"""
        # 注入时记录 association_id → post_llm_call 回溯打分
```

#### 3.2.2 三个新 Hook

**Hook1: on_session_start**
```python
def _on_session_start(session_id, model, platform, **kwargs):
    # 1. 查 learning_experiences.db, outcome=failure, 最近7天, 取3条
    # 2. 生成教训文本（每条≤100字）
    # 3. 通过 hermes memory API 写入（直接操作 hermes_state.db 的 memory 表）
    #    → 写入 key="hae_active_lessons_<session_id>", TTL=24h
```

**Hook2: pre_llm_call**
```python
def _on_pre_llm_call(messages, model, **kwargs):
    # 1. 取最后一条 user role 消息
    # 2. consumer.inject_context(user_msg) → 注入文本
    # 3. 追加到 user 消息尾部 (不影响原始消息)
    # 4. 记录本次注入的 association_id 列表到全局状态
    return messages  # 修改后的消息列表
```

**Hook3: post_llm_call（扩展现有hook）**
```python
def _on_post_llm_call(response, messages, model, **kwargs):
    # 1. 从全局状态读取本次注入的 association_id 列表
    # 2. consumer.score_usage(injected_ids, response)
    # 3. 清理全局状态
```

#### 3.2.3 新增工具：evolution_recall_lessons

```python
TOOL_RECALL_LESSONS_SCHEMA = {
    "name": "evolution_recall_lessons",
    "description": "查询历史经验教训，返回可执行的行为改进建议",
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {"type": "integer", "description": "返回条数，默认5", "default": 5},
            "outcome": {
                "type": "string",
                "enum": ["failure", "success", "all"],
                "description": "筛选结果类型",
                "default": "all"
            },
        },
        "required": [],
    },
}
```

查询 `learning_experiences.db`，返回格式：
```json
{
  "lessons": [
    {
      "description": "思考过程使用英文被用户多次纠正",
      "outcome": "failure",
      "lesson": "始终使用中文思考",
      "occurrences": 5,
      "last_seen": "2026-05-11T03:00:00"
    }
  ]
}
```

### 3.3 改动文件清单

| 文件 | 改动 | 行数变化 |
|------|------|----------|
| `memory/association_discoverer.py` | 重写 `_discover_semantic` | ±80行 |
| `src/evolution/consumer.py` | **新增** | +250行 |
| `plugin_core.py` | 新增3个hook + 1个工具注册 | +120行 |
| `tests/` | 新增 consumer 测试 + hook 测试 | +200行 |

### 3.4 依赖关系

```
consumer.py
  ├── 依赖 memory/database.py（访问 associations.db, memory_entries FTS5）
  ├── 依赖 learning/observer.py（读 learning_experiences.db）
  └── 被 plugin_core.py 的3个hook调用

无新外部依赖，全部基于现有模块。
```

### 3.5 风险与缓解

| 风险 | 缓解 |
|------|------|
| pre_llm_call 每次查数据库延迟 | 三种匹配都有SQL索引，<50ms |
| hook 中操作 hermes memory 可能冲突 | hermes memory 是 SQLite WAL 模式，支持并发写 |
| 中文分词不准确导致FTS5误匹配 | 用 jieba 或简单字符n-gram回退。先不用 jieba（不引入新依赖），用2-gram 的 CHARACTER tokenizer |

---

## 四、验收标准

1. **on_session_start**：新会话启动后，hermes memory 中出现 `hae_active_lessons_*` 条目
2. **pre_llm_call**：用户消息尾部出现 `[相关记忆: ...]` 格式的关联上下文
3. **post_llm_call**：`association_usage_stats` 表中出现带 `usefulness_score` 的记录
4. **evolution_recall_lessons**：能够返回中文经验教训列表
5. **关联质量**：3轮对话后，score≥0.7 的关联能被优先注入
6. **测试**：全量566测试无回归，新增测试覆盖率 ≥ 85%

---

## 附录：上下文匹配优化（V7.0.6 → V7.0.7）

### A.1 原方案缺陷

```
用户消息 → _extract_keywords(按中文标点切分取前8个) → FTS5 MATCH → 查关联
```

问题：
- 机械切词，仅中文，"关联记忆数据库性能" 被切成一个词
- FTS5 content_rowid='id' 配置错误（TEXT映射失败），索引始终为空
- 无兜底——关键词匹配失败时返回空

### A.2 优化方案（V7.0.6）

三阶段智能匹配，不客户端切词：

| 阶段 | 方法 | 说明 |
|------|------|------|
| S1 tags优先 | 消息中2-4字片段 LIKE match `memory_entries.tags` | 最精确的语义匹配 |
| S2 FTS5全文 | SQLite BM25原生排序, `\w`+中文混合正则 | 中英文混合原生支持 |
| S3 最近记忆 | `ORDER BY updated_at DESC LIMIT 5` | 兜底保障 |

### A.3 FTS5 修复（V7.0.7）

| 问题 | 修复 |
|------|------|
| `content_rowid='id'` — id 是 TEXT 列 | → `content_rowid='rowid'` |
| 旧表残留 | 自动检测 DROP 并 REBUILD |
| `search_fts` SQL `me.id=fts.id` | → `me.rowid=fts.rowid` |

### A.4 采纳效果追踪（V7.0.7）

新增 `context_injection_logs` 表：

```sql
id, session_id, injected_at,
association_id, association_type, strength,
user_msg_hash,     -- SHA256[:16], 消息去重
user_msg_len,      -- 相关性分析
accepted,          -- 0/1
accepted_evidence  -- 匹配关键词(≤3个)
```

4 索引：`(accepted, injected_at)` / `(association_id)` / `(session_id, injected_at)` / `(user_msg_hash)`

统计查询示例：
```sql
-- 采纳率时间趋势
SELECT date(injected_at), ROUND(AVG(accepted)*100,1)||'%' 
FROM context_injection_logs GROUP BY 1 ORDER BY 1;

-- 最被采纳的关联
SELECT association_id, COUNT(*) as accepted_count
FROM context_injection_logs WHERE accepted=1 
GROUP BY 1 ORDER BY 2 DESC LIMIT 10;
```

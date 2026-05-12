# hermes memory → HAE memory_entries 同步方案

## 一、问题诊断

两套系统割裂：

```
hermes memory 工具 (40条实际记忆)
    ↓ 注入到 system prompt
    ↓
   LLM 可用 —— 但 HAE 完全不知道这些数据的存在

HAE memory_entries (4593条测试垃圾)
    ↓ evolution_memory_discover 建关联
    ↓ consumer.py 注入上下文
    ↓
   空转 —— 关联的是测试数据，不是真实知识
```

## 二、方案：post_tool_call 拦截同步

不修改 hermes 的存储层，在 HAE 的 `post_tool_call` hook 中截获 `memory` 工具调用。

### 2.1 触发时机

```
用户: "记住这个：OOM根因是discover_all的N×N组合爆炸"
  → memory tool 被调用 (action=add, content="OOM根因...")
  → hermes 写入自己的 memory 存储
  → post_tool_call hook 触发
  → 检测到 tool_name == "memory" 且 action == "add"
  → HAE 自动写入 memory_entries
```

### 2.2 数据映射

| hermes memory 字段 | → | HAE memory_entries 字段 |
|---------------------|---|------------------------|
| content | → | content（原文） |
| target ("memory"/"user") | → | content_type |
| content 关键词分析 | → | tags（自动提取） |
| SHA256(content)[:16] | → | content_hash（去重） |

### 2.3 Tags 自动提取

从 content 中提取有意义的关键词作为 tags：

```python
def _auto_tags(content: str) -> List[str]:
    # 1. 提取长度≥2的非停用词片段
    candidates = re.findall(r'[\w\u4e00-\u9fff]{2,8}', content)
    # 2. 过滤纯数字、纯标点
    # 3. 按词频排序取 top 5
    return top_5
```

### 2.4 去重机制

写入前检查 `content_hash` 是否已存在，存在则更新 `updated_at` 而非重复插入。

### 2.5 一次性回填

方案发布时，扫描当前已注入到 system prompt 的 40 条 hermes memory，批量导入 memory_entries。

---

## 三、实现细节

### 3.1 修改 `plugin_core.py` 的 `_on_post_tool_call`

在现有 hook 中增加 memory 同步逻辑：

```python
def _on_post_tool_call(ctx, tool_name, params, result, duration_ms, error):
    # ── 原有逻辑：记录 tool execution experience ──
    # ... (不变)

    # ── V7.0.8 新增：hermes memory 同步到 HAE ──
    if tool_name == "memory" and not error:
        _sync_hermes_memory_to_hae(params, result)
```

### 3.2 新增 `_sync_hermes_memory_to_hae()`

```python
def _sync_hermes_memory_to_hae(params, result):
    action = params.get("action", "")
    if action not in ("add", "replace"):
        return
    content = params.get("content", "")
    target = params.get("target", "memory")
    if not content or len(content) < 10:
        return

    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    tags = _auto_tags(content)

    try:
        conn = _get_association_db()
        # 去重检查
        existing = conn.execute(
            "SELECT id FROM memory_entries WHERE content_hash = ?",
            (content_hash,)
        ).fetchone()

        if existing:
            conn.execute(
                "UPDATE memory_entries SET updated_at = ?, tags = ? WHERE id = ?",
                (datetime.now().isoformat(), ",".join(tags), existing[0])
            )
        else:
            entry_id = f"hmem_{content_hash}"
            conn.execute(
                "INSERT INTO memory_entries (id, content, content_type, content_hash, tags, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (entry_id, content, target, content_hash,
                 ",".join(tags), datetime.now().isoformat(), datetime.now().isoformat())
            )
        conn.commit()
    except Exception as e:
        logger.warning("hermes memory 同步失败: %s", e)
```

### 3.3 `_auto_tags()` 实现

```python
def _auto_tags(content: str) -> List[str]:
    """从内容自动提取标签"""
    import re
    # 提取中文+英文混合词段
    words = re.findall(r'[\w\u4e00-\u9fff]{2,8}', content)
    # 停用词过滤
    stop = {'的','是','在','和','了','有','不','这','也','就','都','要','一个',
            '可以','使用','需要','没有','如果','这个','那个','什么','怎么','为什么',
            'the','is','in','and','to','of','for','with','that','this','not','be','are'}
    words = [w for w in words if w.lower() not in stop]
    # 排序取 top 5（按词频+长度）
    from collections import Counter
    freq = Counter(words)
    sorted_words = sorted(freq, key=lambda w: (freq[w], len(w)), reverse=True)
    return sorted_words[:5]
```

---

## 四、影响范围

| 改动 | 文件 | 行数 |
|------|------|------|
| memory 同步拦截 | `plugin_core.py` _on_post_tool_call | +10 |
| 同步函数 + tags提取 | `plugin_core.py` 新增 | +50 |
| 一次性回填 | 启动脚本（手动执行一次） | +15 |
| 测试 | `tests/` | +30 |

**无新依赖，无 schema 变更，现有功能不受影响。**

---

## 五、验收

1. 调用 `memory add` 一条记录 → 验证 `memory_entries` 表中出现对应条目
2. 调用 `memory replace` 更新 → 验证 `memory_entries` 中对应条目 updated_at 更新
3. 运行 `evolution_memory_discover(max_entries=50)` → 能看到新记忆之间的关联
4. 回填后 memory_entries 中至少有 40 条真实数据（不再全是测试垃圾）

---

## 六、补充：主动知识收集（第2层）

### 6.1 问题

当前完全依赖 LLM 主动调用 `memory` 工具。如果 LLM 没调用，对话内容就丢失了。用户需求是"尽可能收集"。

### 6.2 方案：post_llm_call 自动提取知识点

在每次 LLM 回复后，自动分析本轮对话，提取可复用的知识点：

```
用户消息 + LLM回复
    ↓ _extract_knowledge()
    ↓
  候选知识点（≤3条，每条≤100字）
    ↓ 去重检查
    ↓
  写入 memory_entries（content_type="auto_session", importance=0.3）
```

### 6.3 提取规则

不引入 NLP 模型，基于规则：

| 模式 | 正则 | 示例 |
|------|------|------|
| 定义句式 | `(\w{2,})是(\w{2,})` | "OOM是Out of Memory" |
| 配置句式 | `(\w+)路径.*[:：]\s*(\S+)` | "配置文件位置: /root/.hermes/config.yaml" |
| 命令句式 | `(\w+)\s+(\S+).*命令` | "hermes config set 命令" |
| 版本号 | `v?(\d+\.\d+\.\d+)` | "v7.0.7" |
| 因果句式 | `(\w+).{0,5}因为(\w+)` | "OOM因为N×N组合爆炸" |
| 文件路径 | `(/[\w/.-]+)` | "/root/.hermes/config.yaml" |

如果 LLM 回复太长（>500字），只提取前500字中的候选。

### 6.4 去重与合并

- 写入前用 content_hash 检查是否已存在
- 如果相似度 > 0.8（通过 Jaccard 关键词重叠），合并更新
- 自动知识点 importance=0.3（低于手动 memory 的 0.5），后续可被手动升级

### 6.5 存储控制

- 每次会话最多自动收集 **1000** 条
- 自动知识点总数上限 **10000** 条，超出时清除最旧的（`ORDER BY created_at ASC LIMIT excess DELETE`）
- content_type="auto_session" 标记，可区分手动/自动
- 定期更新、审计、清理 → 留到后续版本优化

---

## 七、更新后改动范围

| 层次 | 文件 | 改动 |
|------|------|------|
| 第1层 memory 拦截 | `plugin_core.py` _on_post_tool_call | +10 行 |
| 第1层 同步写入 | `plugin_core.py` 新增函数 | +50 行 |
| 第2层 知识点提取 | `plugin_core.py` _on_post_llm_call 修改 | +15 行 |
| 第2层 提取规则 | `plugin_core.py` 新增 _extract_knowledge | +40 行 |
| 自动去重 | consumer.py 或 database.py | +20 行 |
| 一次性回填 | 启动脚本 | +15 行 |
| 测试 | tests/ | +40 行 |

总计约 190 行，无新外部依赖。

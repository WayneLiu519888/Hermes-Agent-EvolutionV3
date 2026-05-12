"""
V7.0.9 后台知识整理 Agent

基于 MemGPT 架构理念：主对话只缓存，异步 Agent 独立提取。
由 hermes cronjob 或其他定时机制触发，每 5 分钟扫描一次。
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Agent 配置
BATCH_SIZE = 5           # 每次最多处理 5 条对话缓存
MAX_RETRIES = 2          # LLM 调用重试次数


def run_knowledge_agent(db_path: str = None) -> Dict[str, Any]:
    """知识整理 Agent 主入口

    Args:
        db_path: associations.db 路径，默认使用环境自动解析

    Returns:
        {"status": "ok"|"idle"|"error", "extracted": N, "processed": N}
    """
    if db_path is None:
        from evolution.db_utils import get_data_dir
        db_path = str(get_data_dir() / "associations.db")

    import sqlite3
    conn = sqlite3.connect(db_path)

    # 1. 读取未处理的对话缓存
    rows = conn.execute(
        "SELECT id, user_summary, reply_summary FROM conversation_cache "
        "WHERE processed = 0 ORDER BY cached_at ASC LIMIT ?",
        (BATCH_SIZE,)
    ).fetchall()

    if not rows:
        conn.close()
        return {"status": "idle", "message": "无待处理对话", "extracted": 0, "processed": 0}

    # 2. 组装提取 prompt
    prompt = _build_prompt(rows)

    # 3. 调 LLM 提取知识点
    items = _call_llm_extract(prompt)
    if not items:
        conn.close()
        return {"status": "error", "message": "LLM 提取返回空", "extracted": 0, "processed": 0}

    # 4. 写入 memory_entries
    stored = _store_knowledge(conn, items)

    # 5. 标记已处理
    now = datetime.now().isoformat()
    ids = [r[0] for r in rows]
    placeholders = ",".join("?" * len(ids))
    conn.execute(
        f"UPDATE conversation_cache SET processed=1, processed_at=?, extracted_count=? "
        f"WHERE id IN ({placeholders})",
        [now, stored] + ids
    )
    conn.commit()
    conn.close()

    logger.info("知识Agent: 提取 %d 条知识点, 处理 %d 条对话缓存", stored, len(rows))
    return {"status": "ok", "extracted": stored, "processed": len(rows)}


def _build_prompt(rows: List[tuple]) -> str:
    """组装 LLM 提取 prompt"""
    lines = []
    for i, row in enumerate(rows, 1):
        user = row[1][:5000] if row[1] else ""
        reply = row[2][:5000] if row[2] else ""
        lines.append(f"{i}. 用户: {user}")

    dialogue = "\n".join(lines)

    return f"""你是一个知识提取器。从以下对话中提取 3-5 条可复用的知识点。

规则：
- 只提取有长期价值的信息（工具用法、项目约定、配置、调试经验、设计决策）
- 每条 20-100 字，包含足够上下文能独立理解
- 不要提取临时讨论、进度汇报、闲聊
- 不要提取明显无意义的片段（如纯数字、单字、问候语）
- 格式：纯文本，每行一条，以 " - " 开头

对话记录（共{len(rows)}条）：
{chr(10).join(['='*50])}
{dialogue}
{chr(10).join(['='*50])}

提取的知识点："""


def _call_llm_extract(prompt: str) -> List[str]:
    """调用 LLM 提取知识点

    用 hermes 辅助 LLM 接口，不走 tool loop。
    失败时用内置规则兜底。
    """
    for attempt in range(MAX_RETRIES):
        try:
            from hermes_cli.aux import call_aux_llm
            result = call_aux_llm(
                provider="auto",
                model="auto",
                messages=[{"role": "user", "content": prompt}],
                timeout=60,
            )
            # 解析返回内容
            text = result if isinstance(result, str) else result.get("content", "")
            items = _parse_items(text)
            if items:
                return items
        except ImportError:
            # hermes_cli.aux 不可用，用内置规则兜底
            logger.debug("hermes_cli.aux 不可用，使用内置规则")
            break
        except Exception as e:
            logger.debug("LLM 提取失败 (尝试 %d/%d): %s", attempt + 1, MAX_RETRIES, e)

    # 兜底：内置规则提取
    return _fallback_extract(prompt)


def _parse_items(text: str) -> List[str]:
    """解析 LLM 返回的知识点列表"""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        # 匹配 " - xxx" 或 "- xxx" 或 "1. xxx"
        if line.startswith("- ") or line.startswith(" - "):
            item = line.lstrip("- ").strip()
            if 15 <= len(item) <= 200:
                items.append(item)
        elif line and line[0].isdigit() and ". " in line[:4]:
            item = line.split(". ", 1)[1].strip()
            if 15 <= len(item) <= 200:
                items.append(item)
    return items[:5]


def _fallback_extract(prompt: str) -> List[str]:
    """兜底提取：从 prompt 中找"用户:"后面的关键信息"""
    import re
    items = []
    # 找用户消息中的关键句式
    for match in re.finditer(r'用户: (.+?)(?=\n\d+\.|\n===|$)', prompt, re.DOTALL):
        text = match.group(1).strip()
        # 提取定义/配置/命令等
        for pattern in [
            r'([\w\u4e00-\u9fff]{3,})是([\w\u4e00-\u9fff]{3,})',
            r'v?(\d+\.\d+\.\d+)',
        ]:
            for m in re.finditer(pattern, text):
                item = m.group(0)
                if 15 <= len(item) <= 200:
                    items.append(item)
    return items[:3]


def _store_knowledge(conn, items: List[str]) -> int:
    """写入知识点到 memory_entries，去重"""
    now = datetime.now().isoformat()
    stored = 0

    # 检查总量
    total = conn.execute(
        "SELECT COUNT(*) FROM memory_entries WHERE content_type='llm_extract'"
    ).fetchone()[0]

    for item in items:
        if total + stored >= 10000:
            break

        ch = hashlib.sha256(item.encode()).hexdigest()[:16]
        if conn.execute(
            "SELECT 1 FROM memory_entries WHERE content_hash = ?", (ch,)
        ).fetchone():
            continue

        # 自动提取标签
        import re
        from collections import Counter
        words = re.findall(r'[\w\u4e00-\u9fff]{2,8}', item)
        stop = {'的','是','在','和','了','有','不','这','也','就','都','要','一个',
                '可以','使用','需要','没有','如果','这个','那个','什么','怎么','为什么'}
        words = [w for w in words if w.lower() not in stop]
        tags = []
        if words:
            freq = Counter(words)
            tags = [w for w, _ in sorted(freq.items(), key=lambda x: (x[1], len(x[0])), reverse=True)[:5]]

        entry_id = f"llm_{ch}"
        conn.execute(
            "INSERT INTO memory_entries "
            "(id, content, content_type, content_hash, tags, created_at, updated_at, importance_score) "
            "VALUES (?, ?, 'llm_extract', ?, ?, ?, ?, 0.4)",
            (entry_id, item, ch, ",".join(tags), now, now)
        )
        stored += 1

    conn.commit()
    return stored

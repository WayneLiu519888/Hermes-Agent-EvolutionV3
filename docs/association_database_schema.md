# 记忆系统关联数据库Schema

## 概述
关联发现系统用于自动发现记忆条目之间的关联关系，包括内容相似性、使用模式、时间关联等。

## 数据库表设计

### 1. 记忆条目表 (memory_entries)
存储所有记忆条目的基本信息。

```sql
CREATE TABLE memory_entries (
    id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    content_type TEXT NOT NULL,  -- 'text', 'code', 'image', 'audio', 'video'
    content_hash TEXT NOT NULL,  -- 内容哈希，用于去重
    embedding BLOB,              -- 向量嵌入（可选）
    metadata TEXT,               -- JSON格式的元数据
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    access_count INTEGER DEFAULT 0,
    last_accessed DATETIME,
    importance_score REAL DEFAULT 0.5,
    confidence_score REAL DEFAULT 0.5,
    tags TEXT                    -- JSON数组格式的标签
);
```

### 2. 关联关系表 (associations)
存储记忆条目之间的关联关系。

```sql
CREATE TABLE associations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,      -- 源记忆条目ID
    target_id TEXT NOT NULL,      -- 目标记忆条目ID
    association_type TEXT NOT NULL,  -- 关联类型: 'semantic', 'temporal', 'usage', 'co_occurrence', 'manual'
    strength REAL NOT NULL,       -- 关联强度 (0.0-1.0)
    confidence REAL NOT NULL,     -- 置信度 (0.0-1.0)
    discovered_by TEXT NOT NULL,  -- 发现方式: 'algorithm', 'user', 'system'
    discovery_time DATETIME NOT NULL,
    last_used DATETIME,
    usage_count INTEGER DEFAULT 0,
    metadata TEXT,                -- JSON格式的附加信息
    UNIQUE(source_id, target_id, association_type)
);
```

### 3. 关联发现记录表 (association_discovery_logs)
记录关联发现的过程和结果。

```sql
CREATE TABLE association_discovery_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discovery_method TEXT NOT NULL,  -- 发现方法: 'semantic_similarity', 'temporal_proximity', 'usage_pattern', 'co_occurrence'
    parameters TEXT NOT NULL,        -- JSON格式的参数
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    memory_entries_processed INTEGER DEFAULT 0,
    associations_discovered INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    error_message TEXT,
    metadata TEXT
);
```

### 4. 关联使用统计表 (association_usage_stats)
记录关联关系的使用情况。

```sql
CREATE TABLE association_usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    association_id INTEGER NOT NULL,
    usage_context TEXT NOT NULL,     -- 使用上下文: 'retrieval', 'reasoning', 'learning', 'creation'
    usage_time DATETIME NOT NULL,
    usefulness_score REAL,           -- 有用性评分 (0.0-1.0)
    feedback TEXT,                   -- 用户反馈
    FOREIGN KEY (association_id) REFERENCES associations(id) ON DELETE CASCADE
);
```

### 5. 关联模式表 (association_patterns)
存储发现的关联模式。

```sql
CREATE TABLE association_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_type TEXT NOT NULL,      -- 模式类型: 'temporal_sequence', 'semantic_cluster', 'usage_chain'
    pattern_data TEXT NOT NULL,      -- JSON格式的模式数据
    confidence REAL NOT NULL,
    support_count INTEGER NOT NULL,  -- 支持该模式的关联数量
    discovered_at DATETIME NOT NULL,
    last_verified DATETIME,
    is_active BOOLEAN DEFAULT 1
);
```

## 索引设计

```sql
-- 记忆条目表索引
CREATE INDEX idx_memory_entries_content_hash ON memory_entries(content_hash);
CREATE INDEX idx_memory_entries_created_at ON memory_entries(created_at);
CREATE INDEX idx_memory_entries_importance ON memory_entries(importance_score);
CREATE INDEX idx_memory_entries_tags ON memory_entries(tags);

-- 关联关系表索引
CREATE INDEX idx_associations_source_target ON associations(source_id, target_id);
CREATE INDEX idx_associations_type_strength ON associations(association_type, strength);
CREATE INDEX idx_associations_confidence ON associations(confidence);
CREATE INDEX idx_associations_discovery_time ON associations(discovery_time);

-- 关联使用统计表索引
CREATE INDEX idx_association_usage_association_id ON association_usage_stats(association_id);
CREATE INDEX idx_association_usage_time ON association_usage_stats(usage_time);

-- 关联发现记录表索引
CREATE INDEX idx_discovery_logs_time ON association_discovery_logs(start_time);
CREATE INDEX idx_discovery_logs_method ON association_discovery_logs(discovery_method);
```

## 视图设计

### 1. 强关联视图
```sql
CREATE VIEW strong_associations AS
SELECT a.*, 
       m1.content as source_content,
       m2.content as target_content
FROM associations a
JOIN memory_entries m1 ON a.source_id = m1.id
JOIN memory_entries m2 ON a.target_id = m2.id
WHERE a.strength >= 0.7 AND a.confidence >= 0.8
ORDER BY a.strength DESC;
```

### 2. 最近发现的关联视图
```sql
CREATE VIEW recent_associations AS
SELECT a.*, 
       m1.content as source_content,
       m2.content as target_content
FROM associations a
JOIN memory_entries m1 ON a.source_id = m1.id
JOIN memory_entries m2 ON a.target_id = m2.id
WHERE a.discovery_time >= datetime('now', '-7 days')
ORDER BY a.discovery_time DESC;
```

### 3. 高频使用关联视图
```sql
CREATE VIEW frequently_used_associations AS
SELECT a.*, 
       COUNT(aus.id) as usage_count,
       AVG(aus.usefulness_score) as avg_usefulness
FROM associations a
LEFT JOIN association_usage_stats aus ON a.id = aus.association_id
GROUP BY a.id
HAVING usage_count >= 5
ORDER BY usage_count DESC;
```

## 触发器

### 1. 自动更新关联使用统计
```sql
CREATE TRIGGER update_association_usage_count
AFTER INSERT ON association_usage_stats
FOR EACH ROW
BEGIN
    UPDATE associations 
    SET usage_count = usage_count + 1,
        last_used = NEW.usage_time
    WHERE id = NEW.association_id;
END;
```

### 2. 自动更新记忆条目访问统计
```sql
CREATE TRIGGER update_memory_entry_access
AFTER INSERT ON association_usage_stats
FOR EACH ROW
BEGIN
    -- 更新源记忆条目的访问统计
    UPDATE memory_entries 
    SET access_count = access_count + 1,
        last_accessed = NEW.usage_time
    WHERE id IN (
        SELECT source_id FROM associations WHERE id = NEW.association_id
        UNION
        SELECT target_id FROM associations WHERE id = NEW.association_id
    );
END;
```

## 示例数据

### 记忆条目示例
```sql
INSERT INTO memory_entries (id, content, content_type, content_hash, created_at, updated_at, tags)
VALUES 
    ('mem_001', 'Python中的列表推导式语法', 'text', 'hash1', '2024-01-01 10:00:00', '2024-01-01 10:00:00', '["python", "programming", "syntax"]'),
    ('mem_002', '机器学习中的梯度下降算法', 'text', 'hash2', '2024-01-02 11:00:00', '2024-01-02 11:00:00', '["machine_learning", "algorithm", "optimization"]'),
    ('mem_003', '使用pandas进行数据分析', 'text', 'hash3', '2024-01-03 12:00:00', '2024-01-03 12:00:00', '["python", "data_analysis", "pandas"]');
```

### 关联关系示例
```sql
INSERT INTO associations (source_id, target_id, association_type, strength, confidence, discovered_by, discovery_time)
VALUES 
    ('mem_001', 'mem_003', 'semantic', 0.85, 0.9, 'algorithm', '2024-01-04 10:00:00'),
    ('mem_002', 'mem_003', 'usage', 0.75, 0.8, 'algorithm', '2024-01-04 11:00:00'),
    ('mem_001', 'mem_002', 'temporal', 0.6, 0.7, 'algorithm', '2024-01-04 12:00:00');
```

## 性能优化建议

1. **分区策略**：对于大型数据集，可以考虑按时间分区
2. **定期清理**：定期清理低置信度、低使用率的关联
3. **缓存机制**：对高频查询的关联结果进行缓存
4. **批量操作**：支持批量插入和更新操作
5. **异步处理**：关联发现过程支持异步执行
"""
关联发现数据库操作封装
"""

import sqlite3
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import hashlib

logger = logging.getLogger(__name__)

class AssociationDatabase:
    """关联发现数据库"""
    
    def __init__(self, db_path: str = "associations.db"):
        """初始化数据库"""
        self.db_path = db_path
        self.connection = None
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表结构"""
        try:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row
            
            cursor = self.connection.cursor()
            
            # 创建所有表
            tables = [
                # 记忆条目表
                "CREATE TABLE IF NOT EXISTS memory_entries (id TEXT PRIMARY KEY, content TEXT NOT NULL, content_type TEXT NOT NULL, content_hash TEXT NOT NULL, embedding BLOB, metadata TEXT, created_at DATETIME NOT NULL, updated_at DATETIME NOT NULL, access_count INTEGER DEFAULT 0, last_accessed DATETIME, importance_score REAL DEFAULT 0.5, confidence_score REAL DEFAULT 0.5, tags TEXT)",
                
                # 关联关系表
                "CREATE TABLE IF NOT EXISTS associations (id INTEGER PRIMARY KEY AUTOINCREMENT, source_id TEXT NOT NULL, target_id TEXT NOT NULL, association_type TEXT NOT NULL, strength REAL NOT NULL, confidence REAL NOT NULL, discovered_by TEXT NOT NULL, discovery_time DATETIME NOT NULL, last_used DATETIME, usage_count INTEGER DEFAULT 0, metadata TEXT, UNIQUE(source_id, target_id, association_type))",
                
                # 关联发现记录表
                "CREATE TABLE IF NOT EXISTS association_discovery_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, discovery_method TEXT NOT NULL, parameters TEXT NOT NULL, start_time DATETIME NOT NULL, end_time DATETIME NOT NULL, memory_entries_processed INTEGER DEFAULT 0, associations_discovered INTEGER DEFAULT 0, success_rate REAL DEFAULT 0.0, error_message TEXT, metadata TEXT)",
                
                # 关联使用统计表
                "CREATE TABLE IF NOT EXISTS association_usage_stats (id INTEGER PRIMARY KEY AUTOINCREMENT, association_id INTEGER NOT NULL, usage_context TEXT NOT NULL, usage_time DATETIME NOT NULL, usefulness_score REAL, feedback TEXT, FOREIGN KEY (association_id) REFERENCES associations(id) ON DELETE CASCADE)",
                
                # 关联模式表
                "CREATE TABLE IF NOT EXISTS association_patterns (id INTEGER PRIMARY KEY AUTOINCREMENT, pattern_type TEXT NOT NULL, pattern_data TEXT NOT NULL, confidence REAL NOT NULL, support_count INTEGER NOT NULL, discovered_at DATETIME NOT NULL, last_verified DATETIME, is_active BOOLEAN DEFAULT 1)"
            ]
            
            for table_sql in tables:
                cursor.execute(table_sql)
            
            # 创建索引
            self._create_indexes(cursor)
            
            self.connection.commit()
            logger.info(f"数据库初始化完成: {self.db_path}")
            
        except Exception as e:
            logger.error(f"数据库初始化失败: {e}")
            raise
            
    def _create_indexes(self, cursor):
        """创建索引"""
        indexes = [
            # 记忆条目表索引
            "CREATE INDEX IF NOT EXISTS idx_memory_entries_content_hash ON memory_entries(content_hash)",
            "CREATE INDEX IF NOT EXISTS idx_memory_entries_created_at ON memory_entries(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_memory_entries_importance ON memory_entries(importance_score)",
            
            # 关联关系表索引
            "CREATE INDEX IF NOT EXISTS idx_associations_source_target ON associations(source_id, target_id)",
            "CREATE INDEX IF NOT EXISTS idx_associations_type_strength ON associations(association_type, strength)",
            "CREATE INDEX IF NOT EXISTS idx_associations_confidence ON associations(confidence)",
            "CREATE INDEX IF NOT EXISTS idx_associations_discovery_time ON associations(discovery_time)",
            
            # 关联使用统计表索引
            "CREATE INDEX IF NOT EXISTS idx_association_usage_association_id ON association_usage_stats(association_id)",
            "CREATE INDEX IF NOT EXISTS idx_association_usage_time ON association_usage_stats(usage_time)",
            
            # 关联发现记录表索引
            "CREATE INDEX IF NOT EXISTS idx_discovery_logs_time ON association_discovery_logs(start_time)",
            "CREATE INDEX IF NOT EXISTS idx_discovery_logs_method ON association_discovery_logs(discovery_method)"
        ]
        
        for index_sql in indexes:
            cursor.execute(index_sql)
            
    def add_memory_entry(self, content: str, content_type: str = "text", 
                        metadata: Dict[str, Any] = None, tags: List[str] = None) -> str:
        """添加记忆条目
        
        Args:
            content: 内容
            content_type: 内容类型
            metadata: 元数据
            tags: 标签
            
        Returns:
            str: 记忆条目ID
        """
        try:
            cursor = self.connection.cursor()
            
            # 生成ID和哈希
            entry_id = f"mem_{datetime.now().timestamp()}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            content_hash = hashlib.md5(content.encode()).hexdigest()
            now = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO memory_entries (id, content, content_type, content_hash, metadata, created_at, updated_at, tags) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry_id, content, content_type, content_hash,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now, now,
                    json.dumps(tags or [], ensure_ascii=False)
                )
            )
            
            self.connection.commit()
            logger.debug(f"添加记忆条目: {entry_id}")
            return entry_id
            
        except Exception as e:
            logger.error(f"添加记忆条目失败: {e}")
            raise
            
    def add_association(self, source_id: str, target_id: str, 
                       association_type: str, strength: float = 0.5, 
                       confidence: float = 0.5, metadata: Dict[str, Any] = None) -> int:
        """添加关联关系
        
        Args:
            source_id: 源记忆条目ID
            target_id: 目标记忆条目ID
            association_type: 关联类型
            strength: 关联强度
            confidence: 置信度
            metadata: 元数据
            
        Returns:
            int: 关联ID
        """
        try:
            cursor = self.connection.cursor()
            now = datetime.now().isoformat()
            
            cursor.execute(
                "INSERT OR REPLACE INTO associations (source_id, target_id, association_type, strength, confidence, discovered_by, discovery_time, metadata) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    source_id, target_id, association_type, strength, confidence,
                    'algorithm', now,
                    json.dumps(metadata or {}, ensure_ascii=False)
                )
            )
            
            association_id = cursor.lastrowid
            self.connection.commit()
            logger.debug(f"添加关联: {source_id} -> {target_id} (ID: {association_id})")
            return association_id
            
        except Exception as e:
            logger.error(f"添加关联失败: {e}")
            raise
            
    def get_memory_entry(self, entry_id: str) -> Optional[Dict[str, Any]]:
        """获取记忆条目
        
        Args:
            entry_id: 记忆条目ID
            
        Returns:
            Optional[Dict]: 记忆条目数据
        """
        try:
            cursor = self.connection.cursor()
            cursor.execute('SELECT * FROM memory_entries WHERE id = ?', (entry_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_dict(row)
            return None
            
        except Exception as e:
            logger.error(f"获取记忆条目失败: {e}")
            return None
            
    def _row_to_dict(self, row) -> Dict[str, Any]:
        """将数据库行转换为字典"""
        result = {}
        for key in row.keys():
            value = row[key]
            
            # 处理JSON字段
            if key in ['metadata', 'tags', 'pattern_data', 'parameters'] and value:
                try:
                    value = json.loads(value)
                except:
                    pass
                    
            result[key] = value
            
        return result
        
    def close(self):
        """关闭数据库连接"""
        if self.connection:
            self.connection.close()
            self.connection = None
            
    def __enter__(self):
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

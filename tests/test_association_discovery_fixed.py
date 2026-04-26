"""
测试关联发现系统
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.evolution.memory.database import AssociationDatabase

class TestAssociationDatabase(unittest.TestCase):
    """测试数据库操作"""
    
    def setUp(self):
        """测试前准备"""
        # 使用临时数据库文件
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = AssociationDatabase(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        # 删除临时数据库文件
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def test_database_creation(self):
        """测试数据库创建"""
        # 验证数据库文件已创建
        self.assertTrue(os.path.exists(self.db_path))
        
        # 验证表已创建
        cursor = self.db.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        expected_tables = [
            'memory_entries', 
            'associations', 
            'association_discovery_logs',
            'association_usage_stats',
            'association_patterns'
        ]
        
        for table in expected_tables:
            self.assertIn(table, tables)
    
    def test_memory_entry_crud(self):
        """测试记忆条目CRUD操作"""
        # 创建记忆条目
        entry_id = self.db.add_memory_entry(
            content="测试记忆内容",
            content_type="text",
            metadata={"source": "test"}
        )
        
        self.assertIsNotNone(entry_id)
        
        # 读取记忆条目
        entry = self.db.get_memory_entry(entry_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['content'], "测试记忆内容")
        
        # 通过重新添加相同content_hash来更新（INSERT OR REPLACE行为）
        # 注: add_memory_entry 使用 INSERT OR REPLACE，相同content可更新
        new_entry_id = self.db.add_memory_entry(
            content="更新后的内容",
            content_type="text", 
            metadata={"source": "test", "updated": True}
        )
        self.assertIsNotNone(new_entry_id)
        
        # 读取新条目验证
        new_entry = self.db.get_memory_entry(new_entry_id)
        self.assertIsNotNone(new_entry)
        
        # 删除记忆条目
        self.db.delete_memory_entry(entry_id)
        self.db.delete_memory_entry(new_entry_id)
        
        # 验证删除
        deleted_entry = self.db.get_memory_entry(entry_id)
        self.assertIsNone(deleted_entry)
    
    def test_association_crud(self):
        """测试关联关系CRUD操作"""
        # 创建两个记忆条目
        entry1_id = self.db.add_memory_entry("内容1", "text")
        entry2_id = self.db.add_memory_entry("内容2", "text")
        
        # 创建关联
        assoc_id = self.db.add_association(
            source_id=entry1_id,
            target_id=entry2_id,
            association_type="semantic",
            strength=0.8,
            confidence=0.9,
            metadata={"discovered_by": "test"}
        )
        
        self.assertIsNotNone(assoc_id)
        
        # 获取关联
        association = self.db.get_association(assoc_id)
        self.assertIsNotNone(association)
        self.assertEqual(association['strength'], 0.8)
        
        # 更新关联
        self.db.update_association(
            assoc_id,
            strength=0.9,
            confidence=0.95
        )
        
        # 验证更新
        updated_assoc = self.db.get_association(assoc_id)
        self.assertEqual(updated_assoc['strength'], 0.9)
        
        # 删除关联
        self.db.delete_association(assoc_id)
        
        # 验证删除
        deleted_assoc = self.db.get_association(assoc_id)
        self.assertIsNone(deleted_assoc)

if __name__ == '__main__':
    unittest.main()
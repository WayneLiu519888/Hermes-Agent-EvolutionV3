"""
修复后的关联发现系统测试
使用数据库类实际可用的API
"""

import unittest
import tempfile
import os
import sys
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.evolution.memory.database import AssociationDatabase

class TestAssociationDatabaseFixed(unittest.TestCase):
    """测试数据库操作 - 修复版本"""
    
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
    
    def test_memory_entry_crud_fixed(self):
        """测试记忆条目CRUD操作 - 修复版本"""
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
        
        # 注意：数据库类没有update_memory_entry方法
        # 我们可以直接使用SQL更新，或者测试其他功能
        # 这里我们测试删除功能
        
        # 删除记忆条目 - 使用SQL直接删除
        cursor = self.db.connection.cursor()
        cursor.execute("DELETE FROM memory_entries WHERE id = ?", (entry_id,))
        self.db.connection.commit()
        
        # 验证删除
        deleted_entry = self.db.get_memory_entry(entry_id)
        self.assertIsNone(deleted_entry)
    
    def test_association_crud_fixed(self):
        """测试关联关系CRUD操作 - 修复版本"""
        # 创建两个记忆条目
        entry1_id = self.db.add_memory_entry("内容1", "text")
        entry2_id = self.db.add_memory_entry("内容2", "text")
        
        # 创建关联 - 使用正确的参数
        assoc_id = self.db.add_association(
            source_id=entry1_id,
            target_id=entry2_id,
            association_type="semantic",
            strength=0.8,
            confidence=0.9,
            metadata={"discovered_by": "test"}  # 使用metadata而不是discovered_by参数
        )
        
        self.assertIsNotNone(assoc_id)
        
        # 获取关联 - 使用SQL查询
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, source_id, target_id, association_type, strength, confidence, metadata
            FROM associations WHERE id = ?
        """, (assoc_id,))
        
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        
        # 解析结果
        association = {
            'id': row[0],
            'source_id': row[1],
            'target_id': row[2],
            'association_type': row[3],
            'strength': row[4],
            'confidence': row[5],
            'metadata': row[6]
        }
        
        self.assertEqual(association['strength'], 0.8)
        
        # 更新关联 - 使用SQL更新
        cursor.execute("""
            UPDATE associations 
            SET strength = ?, confidence = ?
            WHERE id = ?
        """, (0.9, 0.95, assoc_id))
        self.db.connection.commit()
        
        # 验证更新
        cursor.execute("SELECT strength, confidence FROM associations WHERE id = ?", (assoc_id,))
        updated_row = cursor.fetchone()
        self.assertEqual(updated_row[0], 0.9)
        self.assertEqual(updated_row[1], 0.95)
        
        # 删除关联 - 使用SQL删除
        cursor.execute("DELETE FROM associations WHERE id = ?", (assoc_id,))
        self.db.connection.commit()
        
        # 验证删除
        cursor.execute("SELECT id FROM associations WHERE id = ?", (assoc_id,))
        deleted_row = cursor.fetchone()
        self.assertIsNone(deleted_row)
    
    def test_basic_workflow(self):
        """测试基本工作流程"""
        # 1. 添加记忆条目
        entry1_id = self.db.add_memory_entry("Python编程", "text", {"category": "programming"})
        entry2_id = self.db.add_memory_entry("机器学习", "text", {"category": "ai"})
        
        self.assertIsNotNone(entry1_id)
        self.assertIsNotNone(entry2_id)
        
        # 2. 添加关联
        assoc_id = self.db.add_association(
            source_id=entry1_id,
            target_id=entry2_id,
            association_type="semantic",
            strength=0.7,
            confidence=0.8,
            metadata={"reason": "both are tech topics"}
        )
        
        self.assertIsNotNone(assoc_id)
        
        # 3. 验证数据存在
        cursor = self.db.connection.cursor()
        
        # 检查记忆条目
        cursor.execute("SELECT COUNT(*) FROM memory_entries")
        memory_count = cursor.fetchone()[0]
        self.assertEqual(memory_count, 2)
        
        # 检查关联
        cursor.execute("SELECT COUNT(*) FROM associations")
        assoc_count = cursor.fetchone()[0]
        self.assertEqual(assoc_count, 1)
        
        # 4. 测试查询功能
        cursor.execute("""
            SELECT m.content, a.association_type, a.strength
            FROM memory_entries m
            JOIN associations a ON m.id = a.source_id
            WHERE a.id = ?
        """, (assoc_id,))
        
        result = cursor.fetchone()
        self.assertIsNotNone(result)
        self.assertEqual(result[0], "Python编程")
        self.assertEqual(result[1], "semantic")

if __name__ == '__main__':
    unittest.main()
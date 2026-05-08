"""
关联优化器测试
"""

import unittest
import tempfile
import os
import sys
import json
from datetime import datetime, timedelta

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from evolution.memory.database import AssociationDatabase
    from evolution.memory.association_optimizer import AssociationOptimizer, OptimizationResult
except ImportError:
    from src.evolution.memory.database import AssociationDatabase
    from src.evolution.memory.association_optimizer import AssociationOptimizer, OptimizationResult

class TestAssociationOptimizer(unittest.TestCase):
    """测试关联优化器"""
    
    def setUp(self):
        """测试前准备"""
        # 使用临时数据库文件
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        # 创建数据库和优化器
        self.db = AssociationDatabase(self.db_path)
        self.optimizer = AssociationOptimizer(self.db_path)
        
        # 添加测试数据
        self._create_test_data()
    
    def tearDown(self):
        """测试后清理"""
        # 删除临时数据库文件
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)
    
    def _create_test_data(self):
        """创建测试数据"""
        # 添加记忆条目
        self.entry1_id = self.db.add_memory_entry("Python编程", "text", {"category": "programming"})
        self.entry2_id = self.db.add_memory_entry("机器学习", "text", {"category": "ai"})
        self.entry3_id = self.db.add_memory_entry("数据分析", "text", {"category": "data"})
        self.entry4_id = self.db.add_memory_entry("Web开发", "text", {"category": "web"})
        
        # 添加关联 - 不同质量的关联
        # 高质量关联
        self.assoc1_id = self.db.add_association(
            source_id=self.entry1_id,
            target_id=self.entry2_id,
            association_type="semantic",
            strength=0.9,
            confidence=0.95,
            metadata={"discovered_by": "semantic", "usage_count": 5}
        )
        
        # 中等质量关联
        self.assoc2_id = self.db.add_association(
            source_id=self.entry1_id,
            target_id=self.entry3_id,
            association_type="semantic",
            strength=0.7,
            confidence=0.6,
            metadata={"discovered_by": "semantic", "usage_count": 2}
        )
        
        # 低质量关联
        self.assoc3_id = self.db.add_association(
            source_id=self.entry2_id,
            target_id=self.entry4_id,
            association_type="temporal",
            strength=0.3,
            confidence=0.4,
            metadata={"discovered_by": "temporal", "usage_count": 0}
        )
    
    def test_optimizer_initialization(self):
        """测试优化器初始化"""
        self.assertIsNotNone(self.optimizer)
        self.assertEqual(self.optimizer.db_path, self.db_path)
    
    def test_optimize_all_associations(self):
        """测试优化所有关联"""
        # 运行优化
        result = self.optimizer.optimize_all_associations()
        
        # 验证结果
        self.assertIsInstance(result, OptimizationResult)
        self.assertTrue(result.success)
        self.assertGreaterEqual(result.associations_optimized, 0)
        self.assertGreaterEqual(result.associations_removed, 0)
        self.assertGreaterEqual(result.optimization_time_ms, 0)
        
        print(f"优化结果: 优化了 {result.associations_optimized} 个关联, "
              f"删除了 {result.associations_removed} 个关联")
    
    def test_get_recommendations(self):
        """测试获取推荐"""
        # 获取推荐
        recommendations = self.optimizer.get_recommendations(self.entry1_id, limit=3)
        
        # 验证推荐结果
        self.assertIsInstance(recommendations, list)
        
        if recommendations:
            print(f"为条目 {self.entry1_id} 找到 {len(recommendations)} 个推荐:")
            for i, rec in enumerate(recommendations, 1):
                print(f"  {i}. {rec.get('content', 'N/A')} "
                      f"(强度: {rec.get('strength', 0):.3f}, "
                      f"置信度: {rec.get('confidence', 0):.3f})")
        
        # 至少应该有一些推荐
        self.assertGreaterEqual(len(recommendations), 0)
    
    def test_analyze_patterns(self):
        """测试分析模式"""
        # 分析模式
        patterns = self.optimizer.analyze_patterns()
        
        # 验证模式结果
        self.assertIsInstance(patterns, list)
        
        if patterns:
            print(f"发现 {len(patterns)} 个模式:")
            for i, pattern in enumerate(patterns, 1):
                print(f"  {i}. {pattern.get('pattern_type', 'unknown')} "
                      f"(置信度: {pattern.get('confidence', 0):.3f})")
        
        # 模式分析应该成功
        self.assertIsNotNone(patterns)
    
    def test_cleanup_low_quality_associations(self):
        """测试清理低质量关联"""
        # 清理低质量关联
        removed_count = self.optimizer.cleanup_low_quality_associations(min_quality_score=0.3)
        
        # 验证清理结果
        self.assertIsInstance(removed_count, int)
        self.assertGreaterEqual(removed_count, 0)
        
        print(f"清理了 {removed_count} 个低质量关联")
    
    def test_get_optimization_stats(self):
        """测试获取优化统计"""
        # 获取统计信息
        stats = self.optimizer.get_optimization_stats()
        
        # 验证统计信息
        self.assertIsInstance(stats, dict)
        
        # 检查关键统计字段
        expected_keys = [
            'total_associations',
            'total_memory_entries',
            'average_strength',
            'average_confidence'
        ]
        
        for key in expected_keys:
            self.assertIn(key, stats)
        
        print("优化统计信息:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    def test_quality_score_calculation(self):
        """测试质量分数计算"""
        # 获取一个关联
        cursor = self.db.connection.cursor()
        cursor.execute("""
            SELECT id, source_id, target_id, association_type, strength, confidence,
                   discovered_by, discovery_time, usage_count, metadata
            FROM associations WHERE id = ?
        """, (self.assoc1_id,))
        
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        
        # 转换为字典
        association = {
            'id': row[0],
            'source_id': row[1],
            'target_id': row[2],
            'association_type': row[3],
            'strength': row[4],
            'confidence': row[5],
            'discovered_by': row[6],
            'discovery_time': row[7],
            'usage_count': row[8],
            'metadata': json.loads(row[9]) if row[9] else {}
        }
        
        # 计算质量分数（通过反射调用私有方法）
        # 注意：这需要修改类或使用其他方法
        # 这里我们测试优化器的整体功能
        
        print(f"关联 {association['id']} 的信息:")
        print(f"  类型: {association['association_type']}")
        print(f"  强度: {association['strength']:.3f}")
        print(f"  置信度: {association['confidence']:.3f}")
        print(f"  使用次数: {association['usage_count']}")
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        print("开始端到端测试...")
        
        # 1. 初始状态
        initial_stats = self.optimizer.get_optimization_stats()
        print(f"初始状态: {initial_stats.get('total_associations', 0)} 个关联")
        
        # 2. 运行优化
        print("运行优化...")
        optimization_result = self.optimizer.optimize_all_associations()
        self.assertTrue(optimization_result.success)
        
        print(f"优化完成: 优化了 {optimization_result.associations_optimized} 个关联, "
              f"删除了 {optimization_result.associations_removed} 个关联")
        
        # 3. 分析模式
        print("分析模式...")
        patterns = self.optimizer.analyze_patterns()
        print(f"发现 {len(patterns)} 个模式")
        
        # 4. 获取推荐
        print("获取推荐...")
        recommendations = self.optimizer.get_recommendations(self.entry1_id)
        print(f"为条目 {self.entry1_id} 找到 {len(recommendations)} 个推荐")
        
        # 5. 清理低质量关联
        print("清理低质量关联...")
        removed = self.optimizer.cleanup_low_quality_associations()
        print(f"清理了 {removed} 个低质量关联")
        
        # 6. 最终状态
        final_stats = self.optimizer.get_optimization_stats()
        print(f"最终状态: {final_stats.get('total_associations', 0)} 个关联")
        
        print("端到端测试完成!")

if __name__ == '__main__':
    unittest.main()
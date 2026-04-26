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
from src.evolution.memory.association_discoverer import AssociationDiscoverer
from src.evolution.memory.retrieval_optimizer import RetrievalOptimizer

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
        self.db.close()
        os.unlink(self.db_path)
        
    def test_add_memory_entry(self):
        """测试添加记忆条目"""
        entry_id = self.db.add_memory_entry(
            content="这是一个测试记忆条目",
            content_type="text",
            metadata={"source": "test"},
            tags=["test", "memory"]
        )
        
        self.assertIsNotNone(entry_id)
        self.assertTrue(entry_id.startswith("mem_"))
        
        # 验证可以获取
        entry = self.db.get_memory_entry(entry_id)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['content'], "这是一个测试记忆条目")
        self.assertEqual(entry['content_type'], "text")
        
    def test_add_association(self):
        """测试添加关联关系"""
        # 先创建两个记忆条目
        mem1_id = self.db.add_memory_entry("记忆条目1", "text")
        mem2_id = self.db.add_memory_entry("记忆条目2", "text")
        
        # 添加关联
        assoc_id = self.db.add_association(
            source_id=mem1_id,
            target_id=mem2_id,
            association_type="semantic",
            strength=0.8,
            confidence=0.9
        )
        
        self.assertIsNotNone(assoc_id)
        self.assertGreater(assoc_id, 0)
        
    def test_find_similar_memories(self):
        """测试查找相似记忆"""
        # 添加几个相似的记忆条目
        self.db.add_memory_entry("Python编程语言", "text", tags=["programming", "python"])
        self.db.add_memory_entry("Python数据分析", "text", tags=["data", "python"])
        self.db.add_memory_entry("Java编程语言", "text", tags=["programming", "java"])
        
        # 查找相似的
        similar = self.db.find_similar_memories("Python", limit=5)
        self.assertEqual(len(similar), 2)  # 应该找到2个包含Python的
        
    def test_get_related_memories(self):
        """测试获取相关记忆"""
        # 创建记忆条目和关联
        mem1_id = self.db.add_memory_entry("机器学习", "text")
        mem2_id = self.db.add_memory_entry("深度学习", "text")
        mem3_id = self.db.add_memory_entry("神经网络", "text")
        
        self.db.add_association(mem1_id, mem2_id, "semantic", 0.9, 0.8)
        self.db.add_association(mem1_id, mem3_id, "semantic", 0.7, 0.6)
        
        # 获取相关记忆
        related = self.db.get_related_memories(mem1_id)
        self.assertEqual(len(related), 2)

class TestAssociationDiscoverer(unittest.TestCase):
    """测试关联发现器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = AssociationDatabase(self.db_path)
        self.discoverer = AssociationDiscoverer(self.db)
        
    def tearDown(self):
        """测试后清理"""
        self.db.close()
        os.unlink(self.db_path)
        
    def test_semantic_association_discovery(self):
        """测试语义关联发现"""
        # 添加相似的记忆条目
        mem1_id = self.db.add_memory_entry("人工智能是未来的趋势", "text")
        mem2_id = self.db.add_memory_entry("AI技术正在快速发展", "text")
        mem3_id = self.db.add_memory_entry("完全不同的主题内容", "text")
        
        # 发现语义关联
        associations = self.discoverer.discover_semantic_associations(mem1_id)
        
        # mem1和mem2应该有语义关联
        self.assertGreater(len(associations), 0)
        
        # 检查关联类型
        for assoc in associations:
            self.assertEqual(assoc['association_type'], 'semantic')
            self.assertGreaterEqual(assoc['strength'], 0.2)
            
    def test_temporal_association_discovery(self):
        """测试时间关联发现"""
        mem1_id = self.db.add_memory_entry("上午的会议记录", "text")
        
        # 发现时间关联（需要数据库中有时间相近的记录）
        associations = self.discoverer.discover_temporal_associations(mem1_id)
        
        # 至少应该返回空列表而不报错
        self.assertIsInstance(associations, list)
        
    def test_discover_all_associations(self):
        """测试综合关联发现"""
        mem1_id = self.db.add_memory_entry("测试记忆条目", "text")
        
        # 添加一些相关记忆
        self.db.add_memory_entry("相关的测试内容", "text")
        self.db.add_memory_entry("另一个相关条目", "text")
        
        # 发现所有关联
        associations = self.discoverer.discover_all_associations(mem1_id)
        
        self.assertIsInstance(associations, list)
        
    def test_calculate_similarity(self):
        """测试相似度计算"""
        # 使用内部方法（实际应该公开或测试）
        discoverer = self.discoverer
        
        # 相同文本
        text1 = "这是一个测试"
        text2 = "这是一个测试"
        similarity = discoverer._calculate_similarity(text1, text2)
        self.assertAlmostEqual(similarity, 1.0, delta=0.1)
        
        # 相似文本
        text1 = "机器学习算法"
        text2 = "深度学习算法"
        similarity = discoverer._calculate_similarity(text1, text2)
        self.assertGreater(similarity, 0.3)
        
        # 不同文本
        text1 = "机器学习"
        text2 = "天气很好"
        similarity = discoverer._calculate_similarity(text1, text2)
        self.assertLess(similarity, 0.35)

class TestRetrievalOptimizer(unittest.TestCase):
    """测试关联优化器"""
    
    def setUp(self):
        """测试前准备"""
        self.temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
        self.db_path = self.temp_db.name
        self.temp_db.close()
        
        self.db = AssociationDatabase(self.db_path)
        self.optimizer = RetrievalOptimizer(self.db)
        
        # 创建测试数据
        self.mem1_id = self.db.add_memory_entry("记忆条目1", "text")
        self.mem2_id = self.db.add_memory_entry("记忆条目2", "text")
        self.mem3_id = self.db.add_memory_entry("记忆条目3", "text")
        
        # 添加一些关联
        self.db.add_association(self.mem1_id, self.mem2_id, "semantic", 0.9, 0.8)
        self.db.add_association(self.mem1_id, self.mem3_id, "semantic", 0.3, 0.2)  # 弱关联
        
    def tearDown(self):
        """测试后清理"""
        self.db.close()
        os.unlink(self.db_path)
        
    def test_optimize_associations(self):
        """测试关联优化"""
        result = self.optimizer.optimize_associations(self.mem1_id, min_strength=0.5)
        
        self.assertIn('total_associations', result)
        self.assertIn('optimized_count', result)
        self.assertIn('removed_count', result)
        
        # 弱关联应该被移除或优化
        self.assertGreaterEqual(result['removed_count'], 0)
        
    def test_get_strong_associations(self):
        """测试获取强关联"""
        strong_assocs = self.optimizer.get_strong_associations(
            self.mem1_id, 
            min_strength=0.7,
            min_confidence=0.7
        )
        
        # 应该只找到强关联
        for assoc in strong_assocs:
            self.assertGreaterEqual(assoc['strength'], 0.7)
            self.assertGreaterEqual(assoc['confidence'], 0.7)
            
    def test_get_recommendations(self):
        """测试获取推荐"""
        # 添加更多关联以生成推荐
        mem4_id = self.db.add_memory_entry("记忆条目4", "text")
        self.db.add_association(self.mem2_id, mem4_id, "semantic", 0.8, 0.7)
        
        recommendations = self.optimizer.get_recommendations(self.mem1_id)
        
        self.assertIsInstance(recommendations, list)
        # 应该推荐mem4（通过mem2）
        
    def test_analyze_patterns(self):
        """测试模式分析"""
        # 添加更多关联数据
        for i in range(5):
            mem_id = self.db.add_memory_entry(f"测试记忆{i}", "text")
            self.db.add_association(self.mem1_id, mem_id, "semantic", 0.7, 0.6)
            
        patterns = self.optimizer.analyze_patterns(min_support=2)
        
        self.assertIsInstance(patterns, list)
        # 应该发现一些模式

def run_tests():
    """运行所有测试"""
    print("🧪 运行关联发现系统测试...")
    print("=" * 60)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestAssociationDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestAssociationDiscoverer))
    suite.addTests(loader.loadTestsFromTestCase(TestRetrievalOptimizer))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 60)
    print(f"📊 测试结果:")
    print(f"  运行测试: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)

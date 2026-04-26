"""
检索优化器测试模块
"""

import unittest
import tempfile
import os
import json
import time
from src.evolution.memory.retrieval_optimizer import (
    RetrievalOptimizer,
    RetrievalConfig,
    RetrievalFeedback,
    create_feedback_from_query
)


class TestRetrievalConfig(unittest.TestCase):
    """测试检索配置类"""
    
    def test_default_config(self):
        """测试默认配置"""
        config = RetrievalConfig()
        self.assertEqual(config.similarity_threshold, 0.7)
        self.assertEqual(config.max_results, 10)
        self.assertEqual(config.time_decay_factor, 0.1)
        
    def test_custom_config(self):
        """测试自定义配置"""
        config = RetrievalConfig(
            similarity_threshold=0.8,
            max_results=15,
            time_decay_factor=0.2
        )
        self.assertEqual(config.similarity_threshold, 0.8)
        self.assertEqual(config.max_results, 15)
        self.assertEqual(config.time_decay_factor, 0.2)


class TestRetrievalFeedback(unittest.TestCase):
    """测试检索反馈类"""
    
    def test_feedback_creation(self):
        """测试反馈创建"""
        feedback = RetrievalFeedback(
            query="test query",
            retrieved_ids=["doc1", "doc2", "doc3"],
            selected_ids=["doc1", "doc2"],
            relevance_scores={"doc1": 0.9, "doc2": 0.8, "doc3": 0.3},
            response_time=0.5,
            timestamp=time.time()
        )
        
        self.assertEqual(feedback.query, "test query")
        self.assertEqual(len(feedback.retrieved_ids), 3)
        self.assertEqual(len(feedback.selected_ids), 2)
        self.assertAlmostEqual(feedback.relevance_scores["doc1"], 0.9)


class TestRetrievalOptimizer(unittest.TestCase):
    """测试检索优化器"""
    
    def setUp(self):
        """测试前准备"""
        # 创建临时数据库文件
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_retrieval.db")
        self.optimizer = RetrievalOptimizer(self.db_path)
        
    def tearDown(self):
        """测试后清理"""
        # 删除临时文件
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.optimizer.current_config)
        self.assertEqual(len(self.optimizer.feedback_history), 0)
        
    def test_save_config(self):
        """测试保存配置"""
        # 保存配置
        self.optimizer.save_config(performance_score=0.8)
        
        # 验证数据库中有记录
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM config_history")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 1)
        
    def test_record_feedback(self):
        """测试记录反馈"""
        feedback = RetrievalFeedback(
            query="test query",
            retrieved_ids=["doc1", "doc2"],
            selected_ids=["doc1"],
            relevance_scores={"doc1": 0.9, "doc2": 0.3},
            response_time=0.3,
            timestamp=time.time()
        )
        
        self.optimizer.record_feedback(feedback)
        
        # 验证反馈历史
        self.assertEqual(len(self.optimizer.feedback_history), 1)
        self.assertEqual(self.optimizer.feedback_history[0].query, "test query")
        
        # 验证数据库记录
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM retrieval_feedback")
        count = cursor.fetchone()[0]
        conn.close()
        
        self.assertEqual(count, 1)
        
    def test_calculate_performance_metrics_empty(self):
        """测试空数据时的性能指标计算"""
        metrics = self.optimizer.calculate_performance_metrics()
        
        self.assertEqual(metrics['precision'], 0.0)
        self.assertEqual(metrics['recall'], 0.0)
        self.assertEqual(metrics['f1_score'], 0.0)
        self.assertEqual(metrics['mean_response_time'], 0.0)
        
    def test_calculate_performance_metrics_with_data(self):
        """测试有数据时的性能指标计算"""
        # 添加一些测试反馈
        for i in range(5):
            feedback = RetrievalFeedback(
                query=f"query_{i}",
                retrieved_ids=[f"doc_{j}" for j in range(5)],
                selected_ids=[f"doc_{j}" for j in range(3)],  # 前3个被选中
                relevance_scores={f"doc_{j}": 0.9 if j < 3 else 0.2 for j in range(5)},
                response_time=0.1 + i * 0.05,
                timestamp=time.time() - i * 3600
            )
            self.optimizer.record_feedback(feedback)
        
        metrics = self.optimizer.calculate_performance_metrics()
        
        # 验证指标在合理范围内
        self.assertGreaterEqual(metrics['precision'], 0.0)
        self.assertLessEqual(metrics['precision'], 1.0)
        self.assertGreaterEqual(metrics['recall'], 0.0)
        self.assertLessEqual(metrics['recall'], 1.0)
        self.assertGreaterEqual(metrics['f1_score'], 0.0)
        self.assertLessEqual(metrics['f1_score'], 1.0)
        self.assertGreater(metrics['mean_response_time'], 0.0)
        
    def test_optimize_parameters_insufficient_data(self):
        """测试数据不足时的参数优化"""
        # 只有少量数据时应该返回当前配置
        original_config = self.optimizer.current_config
        new_config = self.optimizer.optimize_parameters()
        
        # 应该返回相同的配置（因为数据不足）
        self.assertEqual(original_config.similarity_threshold, new_config.similarity_threshold)
        
    def test_optimize_parameters_with_enough_data(self):
        """测试有足够数据时的参数优化"""
        # 添加足够的测试反馈
        for i in range(15):
            feedback = RetrievalFeedback(
                query=f"query_{i}",
                retrieved_ids=[f"doc_{j}" for j in range(8)],
                selected_ids=[f"doc_{j}" for j in range(4)],  # 一半被选中
                relevance_scores={f"doc_{j}": 0.8 if j < 4 else 0.3 for j in range(8)},
                response_time=0.2,
                timestamp=time.time() - i * 3600
            )
            self.optimizer.record_feedback(feedback)
        
        original_config = self.optimizer.current_config
        new_config = self.optimizer.optimize_parameters()
        
        # 验证配置已更新
        self.assertIsNotNone(new_config)
        # 参数应该在合理范围内
        self.assertGreaterEqual(new_config.similarity_threshold, 0.5)
        self.assertLessEqual(new_config.similarity_threshold, 1.0)
        self.assertGreaterEqual(new_config.max_results, 5)
        self.assertLessEqual(new_config.max_results, 20)
        
    def test_get_optimal_config(self):
        """测试获取最优配置"""
        # 初始时应该返回当前配置
        optimal_config = self.optimizer.get_optimal_config()
        self.assertEqual(optimal_config.similarity_threshold, 
                        self.optimizer.current_config.similarity_threshold)
        
    def test_analyze_trends_insufficient_data(self):
        """测试数据不足时的趋势分析"""
        trends = self.optimizer.analyze_trends()
        
        self.assertEqual(trends['trend'], 'insufficient_data')
        self.assertEqual(trends['suggestion'], '收集更多反馈数据')
        
    def test_reset_to_default(self):
        """测试重置为默认配置"""
        # 修改当前配置
        self.optimizer.current_config.similarity_threshold = 0.9
        self.optimizer.current_config.max_results = 15
        
        # 重置
        self.optimizer.reset_to_default()
        
        # 验证已重置为默认值
        self.assertEqual(self.optimizer.current_config.similarity_threshold, 0.7)
        self.assertEqual(self.optimizer.current_config.max_results, 10)


class TestUtilityFunctions(unittest.TestCase):
    """测试工具函数"""
    
    def test_create_feedback_from_query(self):
        """测试从查询创建反馈"""
        retrieved_docs = [
            {"id": "doc1", "score": 0.9, "content": "content1"},
            {"id": "doc2", "score": 0.8, "content": "content2"},
            {"id": "doc3", "score": 0.7, "content": "content3"}
        ]
        
        selected_docs = [
            {"id": "doc1", "score": 0.9, "content": "content1"},
            {"id": "doc2", "score": 0.8, "content": "content2"}
        ]
        
        feedback = create_feedback_from_query(
            query="test query",
            retrieved_docs=retrieved_docs,
            selected_docs=selected_docs,
            response_time=0.3
        )
        
        self.assertEqual(feedback.query, "test query")
        self.assertEqual(len(feedback.retrieved_ids), 3)
        self.assertEqual(len(feedback.selected_ids), 2)
        self.assertIn("doc1", feedback.relevance_scores)
        self.assertAlmostEqual(feedback.response_time, 0.3)


if __name__ == '__main__':
    unittest.main()
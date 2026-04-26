"""
记忆系统检索策略自优化模块
实现基于反馈的检索策略动态优化
"""

import sqlite3
import json
import time
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """检索配置参数"""
    similarity_threshold: float = 0.7
    max_results: int = 10
    time_decay_factor: float = 0.1
    relevance_boost: float = 1.0
    diversity_penalty: float = 0.3
    freshness_weight: float = 0.2
    context_weight: float = 0.4
    semantic_weight: float = 0.4


@dataclass
class RetrievalFeedback:
    """检索反馈数据"""
    query: str
    retrieved_ids: List[str]
    selected_ids: List[str]
    relevance_scores: Dict[str, float]
    response_time: float
    timestamp: float


class RetrievalOptimizer:
    """检索策略优化器"""
    
    def __init__(self, db_path: str = "data/retrieval_optimization.db"):
        """
        初始化优化器
        
        Args:
            db_path: SQLite数据库路径
        """
        self.db_path = db_path
        self.current_config = RetrievalConfig()
        self.feedback_history: List[RetrievalFeedback] = []
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建配置历史表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS config_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                config_json TEXT NOT NULL,
                performance_score REAL
            )
        ''')
        
        # 创建反馈数据表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS retrieval_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                query TEXT NOT NULL,
                retrieved_ids_json TEXT NOT NULL,
                selected_ids_json TEXT NOT NULL,
                relevance_scores_json TEXT NOT NULL,
                response_time REAL NOT NULL
            )
        ''')
        
        # 创建性能指标表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS performance_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL NOT NULL,
                precision REAL,
                recall REAL,
                f1_score REAL,
                mean_response_time REAL,
                config_id INTEGER,
                FOREIGN KEY (config_id) REFERENCES config_history(id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def save_config(self, performance_score: Optional[float] = None):
        """保存当前配置到历史"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        config_json = json.dumps(asdict(self.current_config))
        cursor.execute(
            'INSERT INTO config_history (timestamp, config_json, performance_score) VALUES (?, ?, ?)',
            (time.time(), config_json, performance_score)
        )
        
        conn.commit()
        conn.close()
        
    def record_feedback(self, feedback: RetrievalFeedback):
        """记录检索反馈"""
        self.feedback_history.append(feedback)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            '''INSERT INTO retrieval_feedback 
               (timestamp, query, retrieved_ids_json, selected_ids_json, relevance_scores_json, response_time)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (feedback.timestamp, feedback.query,
             json.dumps(feedback.retrieved_ids),
             json.dumps(feedback.selected_ids),
             json.dumps(feedback.relevance_scores),
             feedback.response_time)
        )
        
        conn.commit()
        conn.close()
        
    def calculate_performance_metrics(self, config_id: Optional[int] = None) -> Dict[str, float]:
        """计算性能指标"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取最近的反馈数据
        cursor.execute('''
            SELECT retrieved_ids_json, selected_ids_json, relevance_scores_json, response_time
            FROM retrieval_feedback
            ORDER BY timestamp DESC LIMIT 100
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        if not results:
            return {
                'precision': 0.0,
                'recall': 0.0,
                'f1_score': 0.0,
                'mean_response_time': 0.0
            }
        
        precisions = []
        recalls = []
        response_times = []
        
        for row in results:
            retrieved_ids = json.loads(row[0])
            selected_ids = json.loads(row[1])
            relevance_scores = json.loads(row[2])
            response_time = row[3]
            
            # 计算精度和召回率
            if retrieved_ids:
                relevant_retrieved = [id_ for id_ in retrieved_ids if id_ in selected_ids]
                precision = len(relevant_retrieved) / len(retrieved_ids) if retrieved_ids else 0.0
                recall = len(relevant_retrieved) / len(selected_ids) if selected_ids else 0.0
                
                precisions.append(precision)
                recalls.append(recall)
                response_times.append(response_time)
        
        # 计算平均指标
        mean_precision = np.mean(precisions) if precisions else 0.0
        mean_recall = np.mean(recalls) if recalls else 0.0
        mean_response_time = np.mean(response_times) if response_times else 0.0
        
        # 计算F1分数
        f1_score = 0.0
        if mean_precision + mean_recall > 0:
            f1_score = 2 * mean_precision * mean_recall / (mean_precision + mean_recall)
        
        metrics = {
            'precision': float(mean_precision),
            'recall': float(mean_recall),
            'f1_score': float(f1_score),
            'mean_response_time': float(mean_response_time)
        }
        
        # 保存性能指标
        if config_id is not None:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO performance_metrics 
                   (timestamp, precision, recall, f1_score, mean_response_time, config_id)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (time.time(), metrics['precision'], metrics['recall'], 
                 metrics['f1_score'], metrics['mean_response_time'], config_id)
            )
            conn.commit()
            conn.close()
        
        return metrics
    
    def optimize_parameters(self) -> RetrievalConfig:
        """基于反馈优化检索参数"""
        if len(self.feedback_history) < 10:
            logger.info("反馈数据不足，使用默认配置")
            return self.current_config
        
        # 分析反馈数据
        metrics = self.calculate_performance_metrics()
        
        # 根据性能指标调整参数
        new_config = RetrievalConfig()
        
        # 调整相似度阈值
        if metrics['precision'] > 0.8:
            # 高精度，可以降低阈值获取更多结果
            new_config.similarity_threshold = max(0.5, self.current_config.similarity_threshold - 0.05)
        elif metrics['recall'] < 0.3:
            # 低召回率，降低阈值
            new_config.similarity_threshold = max(0.5, self.current_config.similarity_threshold - 0.1)
        else:
            new_config.similarity_threshold = self.current_config.similarity_threshold
        
        # 调整最大结果数
        if metrics['mean_response_time'] < 0.5:
            # 响应时间快，可以增加结果数
            new_config.max_results = min(20, self.current_config.max_results + 2)
        else:
            # 响应时间慢，减少结果数
            new_config.max_results = max(5, self.current_config.max_results - 1)
        
        # 调整时间衰减因子
        if metrics['f1_score'] < 0.5:
            # 性能不佳，增加新鲜度权重
            new_config.time_decay_factor = min(0.3, self.current_config.time_decay_factor + 0.05)
            new_config.freshness_weight = min(0.5, self.current_config.freshness_weight + 0.1)
        
        # 调整多样性惩罚
        if metrics['precision'] < 0.6:
            # 精度低，增加多样性惩罚
            new_config.diversity_penalty = min(0.5, self.current_config.diversity_penalty + 0.05)
        
        # 保存新配置
        self.current_config = new_config
        performance_score = metrics['f1_score'] * 0.7 + (1 - metrics['mean_response_time'] / 2) * 0.3
        self.save_config(performance_score)
        
        logger.info(f"优化完成: F1={metrics['f1_score']:.3f}, 响应时间={metrics['mean_response_time']:.3f}s")
        logger.info(f"新配置: {asdict(new_config)}")
        
        return new_config
    
    def get_optimal_config(self) -> RetrievalConfig:
        """获取最优配置"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 查找性能最好的配置
        cursor.execute('''
            SELECT ch.config_json, pm.f1_score
            FROM config_history ch
            LEFT JOIN performance_metrics pm ON ch.id = pm.config_id
            WHERE pm.f1_score IS NOT NULL
            ORDER BY pm.f1_score DESC
            LIMIT 1
        ''')
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            config_dict = json.loads(result[0])
            return RetrievalConfig(**config_dict)
        
        return self.current_config
    
    def analyze_trends(self) -> Dict[str, Any]:
        """分析性能趋势"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 获取最近的性能数据
        cursor.execute('''
            SELECT timestamp, f1_score, mean_response_time
            FROM performance_metrics
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        
        results = cursor.fetchall()
        conn.close()
        
        if len(results) < 2:
            return {'trend': 'insufficient_data', 'suggestion': '收集更多反馈数据'}
        
        timestamps = [r[0] for r in results]
        f1_scores = [r[1] for r in results]
        response_times = [r[2] for r in results]
        
        # 计算趋势
        f1_trend = np.polyfit(range(len(f1_scores)), f1_scores, 1)[0]
        rt_trend = np.polyfit(range(len(response_times)), response_times, 1)[0]
        
        analysis = {
            'f1_score_trend': 'improving' if f1_trend > 0.001 else 'declining' if f1_trend < -0.001 else 'stable',
            'response_time_trend': 'improving' if rt_trend < -0.001 else 'worsening' if rt_trend > 0.001 else 'stable',
            'avg_f1_score': float(np.mean(f1_scores)),
            'avg_response_time': float(np.mean(response_times)),
            'data_points': len(results)
        }
        
        # 生成建议
        suggestions = []
        if analysis['f1_score_trend'] == 'declining':
            suggestions.append("考虑降低相似度阈值以提高召回率")
        if analysis['response_time_trend'] == 'worsening':
            suggestions.append("考虑减少最大返回结果数以降低响应时间")
        if analysis['avg_f1_score'] < 0.5:
            suggestions.append("当前性能较低，建议重新评估检索策略")
        
        analysis['suggestions'] = suggestions
        
        return analysis
    
    def reset_to_default(self):
        """重置为默认配置"""
        self.current_config = RetrievalConfig()
        logger.info("已重置为默认配置")


# 工具函数
def create_feedback_from_query(
    query: str,
    retrieved_docs: List[Dict],
    selected_docs: List[Dict],
    response_time: float
) -> RetrievalFeedback:
    """
    从查询结果创建反馈数据
    
    Args:
        query: 查询文本
        retrieved_docs: 检索到的文档列表
        selected_docs: 用户选择的文档列表
        response_time: 响应时间
        
    Returns:
        RetrievalFeedback对象
    """
    retrieved_ids = [doc.get('id', str(i)) for i, doc in enumerate(retrieved_docs)]
    selected_ids = [doc.get('id', str(i)) for i, doc in enumerate(selected_docs)]
    
    # 计算相关性分数（简化版本）
    relevance_scores = {}
    for doc in retrieved_docs:
        doc_id = doc.get('id', 'unknown')
        # 这里可以根据实际需求计算更复杂的相关性分数
        relevance_scores[doc_id] = doc.get('score', 0.5) if doc_id in selected_ids else 0.2
    
    return RetrievalFeedback(
        query=query,
        retrieved_ids=retrieved_ids,
        selected_ids=selected_ids,
        relevance_scores=relevance_scores,
        response_time=response_time,
        timestamp=time.time()
    )
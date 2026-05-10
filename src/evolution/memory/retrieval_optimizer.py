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
import os

from ..db_utils import get_evolution_db, retry_on_db_error

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
    
    def __init__(self, association_db=None, db_path: str = "retrieval_optimization.db"):
        """
        初始化优化器
        
        Args:
            association_db: AssociationDatabase实例（可选），或字符串路径（向后兼容）
            db_path: SQLite数据库路径（用于内部优化数据存储）
        """
        # 向后兼容：如果第一个参数是字符串，当作db_path
        if isinstance(association_db, str):
            db_path = association_db
            association_db = None
        
        self.association_db = association_db
        self.db_path = db_path
        self.current_config = RetrievalConfig()
        self.feedback_history: List[RetrievalFeedback] = []
        self._init_database()
        
    def _init_database(self):
        """初始化数据库表"""
        conn = get_evolution_db(self.db_path)
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
        # V5-P0: 连接由 DatabasePool 管理，不 close
        
    def save_config(self, performance_score: Optional[float] = None):
        """保存当前配置到历史"""
        conn = get_evolution_db(self.db_path)
        cursor = conn.cursor()
        
        config_json = json.dumps(asdict(self.current_config))
        cursor.execute(
            'INSERT INTO config_history (timestamp, config_json, performance_score) VALUES (?, ?, ?)',
            (time.time(), config_json, performance_score)
        )
        
        conn.commit()
        # V5-P0: 连接由 DatabasePool 管理，不 close
        
    @retry_on_db_error(max_attempts=3)
    def record_feedback(self, feedback: RetrievalFeedback):
        """记录检索反馈"""
        self.feedback_history.append(feedback)
        
        conn = get_evolution_db(self.db_path)
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
        # V5-P0: 连接由 DatabasePool 管理，不 close
        
    def calculate_performance_metrics(self, config_id: Optional[int] = None) -> Dict[str, float]:
        """计算性能指标"""
        conn = get_evolution_db(self.db_path)
        cursor = conn.cursor()
        
        # 获取最近的反馈数据
        cursor.execute('''
            SELECT retrieved_ids_json, selected_ids_json, relevance_scores_json, response_time
            FROM retrieval_feedback
            ORDER BY timestamp DESC LIMIT 100
        ''')
        
        results = cursor.fetchall()
        # V5-P0: 连接由 DatabasePool 管理，不 close
        
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
            conn = get_evolution_db(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                '''INSERT INTO performance_metrics 
                   (timestamp, precision, recall, f1_score, mean_response_time, config_id)
                   VALUES (?, ?, ?, ?, ?, ?)''',
                (time.time(), metrics['precision'], metrics['recall'], 
                 metrics['f1_score'], metrics['mean_response_time'], config_id)
            )
            conn.commit()
            # V5-P0: 连接由 DatabasePool 管理，不 close
        
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
        conn = get_evolution_db(self.db_path)
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
        # V5-P0: 连接由 DatabasePool 管理，不 close
        
        if result:
            config_dict = json.loads(result[0])
            return RetrievalConfig(**config_dict)
        
        return self.current_config
    
    def analyze_trends(self) -> Dict[str, Any]:
        """分析性能趋势"""
        conn = get_evolution_db(self.db_path)
        cursor = conn.cursor()
        
        # 获取最近的性能数据
        cursor.execute('''
            SELECT timestamp, f1_score, mean_response_time
            FROM performance_metrics
            ORDER BY timestamp DESC
            LIMIT 50
        ''')
        
        results = cursor.fetchall()
        # V5-P0: 连接由 DatabasePool 管理，不 close
        
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
    
    # ------------------------------------------------------------------
    # 关联优化方法（供测试调用）
    # ------------------------------------------------------------------

    def optimize_associations(self, memory_id: str, min_strength: float = 0.5) -> Dict[str, Any]:
        """优化指定条目的关联关系
        
        移除弱关联，强化强关联。
        
        Args:
            memory_id: 记忆条目ID
            min_strength: 最小强度阈值
            
        Returns:
            优化结果字典
        """
        if self.association_db is None:
            return {"total_associations": 0, "optimized_count": 0, "removed_count": 0}
        
        # 获取所有关联
        cursor = self.association_db.connection.cursor()
        cursor.execute(
            'SELECT * FROM associations WHERE source_id = ?',
            (memory_id,)
        )
        rows = cursor.fetchall()
        total = len(rows)
        removed = 0
        optimized = 0
        
        # 批量事务：消除 N+1 问题，所有 UPDATE/DELETE 共用事务
        self.association_db.connection.execute("BEGIN TRANSACTION")
        try:
            for row in rows:
                assoc = self.association_db._row_to_dict(row)
                if assoc['strength'] < min_strength:
                    # 删除弱关联
                    self.association_db.connection.execute(
                        'DELETE FROM associations WHERE id = ?', (assoc['id'],)
                    )
                    removed += 1
                else:
                    # 强化强关联
                    new_strength = min(1.0, assoc['strength'] * 1.1)
                    self.association_db.connection.execute(
                        'UPDATE associations SET strength = ? WHERE id = ?',
                        (new_strength, assoc['id'])
                    )
                    optimized += 1
            self.association_db.connection.commit()
        except Exception:
            self.association_db.connection.rollback()
            raise
        
        return {
            "total_associations": total,
            "optimized_count": optimized,
            "removed_count": removed
        }

    def get_strong_associations(self, memory_id: str, min_strength: float = 0.7,
                                 min_confidence: float = 0.7) -> List[Dict[str, Any]]:
        """获取强关联列表
        
        Args:
            memory_id: 记忆条目ID
            min_strength: 最小强度阈值
            min_confidence: 最小置信度阈值
            
        Returns:
            强关联列表
        """
        if self.association_db is None:
            return []
        
        cursor = self.association_db.connection.cursor()
        cursor.execute(
            'SELECT * FROM associations WHERE source_id = ? AND strength >= ? AND confidence >= ?',
            (memory_id, min_strength, min_confidence)
        )
        rows = cursor.fetchall()
        return [self.association_db._row_to_dict(row) for row in rows]

    def get_recommendations(self, memory_id: str) -> List[Dict[str, Any]]:
        """获取推荐关联（基于关联链的传递推荐）
        
        Args:
            memory_id: 记忆条目ID
            
        Returns:
            推荐列表
        """
        if self.association_db is None:
            return []
        
        # 找到与 memory_id 关联的记忆
        cursor = self.association_db.connection.cursor()
        cursor.execute(
            'SELECT target_id FROM associations WHERE source_id = ?',
            (memory_id,)
        )
        related_ids = [row[0] for row in cursor.fetchall()]
        
        recommendations = []
        seen = set(related_ids) | {memory_id}
        
        # 通过关联链发现更多推荐
        for rel_id in related_ids:
            cursor.execute(
                'SELECT target_id, strength, confidence FROM associations WHERE source_id = ? AND target_id NOT IN ({}) ORDER BY strength DESC LIMIT 3'.format(
                    ','.join('?' * len(seen))
                ),
                [rel_id] + list(seen)
            )
            for row in cursor.fetchall():
                recommendations.append({
                    "memory_id": row[0],
                    "via": rel_id,
                    "strength": row[1],
                    "confidence": row[2]
                })
                seen.add(row[0])
        
        return recommendations

    def analyze_patterns(self, min_support: int = 2) -> List[Dict[str, Any]]:
        """分析关联模式
        
        Args:
            min_support: 最小支持度
            
        Returns:
            发现的模式列表
        """
        if self.association_db is None:
            return []
        
        cursor = self.association_db.connection.cursor()
        
        # 统计各类型关联的分布
        cursor.execute(
            '''SELECT association_type, COUNT(*) as cnt, 
                      AVG(strength) as avg_strength, 
                      AVG(confidence) as avg_confidence
               FROM associations 
               GROUP BY association_type 
               HAVING cnt >= ?''',
            (min_support,)
        )
        rows = cursor.fetchall()
        
        patterns = []
        for row in rows:
            patterns.append({
                "association_type": row[0],
                "count": row[1],
                "avg_strength": round(row[2], 3) if row[2] else 0,
                "avg_confidence": round(row[3], 3) if row[3] else 0
            })
        
        return patterns

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
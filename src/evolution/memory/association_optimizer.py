"""
关联优化器 - 智能优化关联关系的质量和效果
"""

import sqlite3
import json
import logging
import math
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
import statistics

from ..db_utils import get_evolution_db

logger = logging.getLogger(__name__)

@dataclass
class OptimizationResult:
    """优化结果"""
    associations_optimized: int = 0
    associations_removed: int = 0
    average_strength_change: float = 0.0
    average_confidence_change: float = 0.0
    optimization_time_ms: float = 0.0
    success: bool = False
    error_message: Optional[str] = None

class AssociationOptimizer:
    """关联优化器"""
    
    def __init__(self, db_path: str = "associations.db"):
        """初始化优化器
        
        Args:
            db_path: 数据库路径
        """
        self.db_path = db_path
        self.connection = None
        self._connect()
        
    def _connect(self):
        """连接到数据库"""
        try:
            self.connection = get_evolution_db(os.path.basename(self.db_path))
            self.connection.row_factory = sqlite3.Row
            logger.info(f"连接到数据库: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def optimize_all_associations(self) -> OptimizationResult:
        """优化所有关联关系
        
        Returns:
            OptimizationResult: 优化结果
        """
        result = OptimizationResult()
        start_time = datetime.now()
        
        try:
            # 1. 收集所有关联
            associations = self._get_all_associations()
            if not associations:
                result.success = True
                result.optimization_time_ms = (datetime.now() - start_time).total_seconds() * 1000
                return result
            
            # 2. 分析关联质量
            quality_scores = self._analyze_association_quality(associations)
            
            # 3. 应用优化策略
            optimized_count = 0
            removed_count = 0
            strength_changes = []
            confidence_changes = []
            
            for assoc_id, quality_score in quality_scores.items():
                original_assoc = next(a for a in associations if a['id'] == assoc_id)
                
                # 根据质量分数决定操作
                if quality_score < 0.2:  # 质量太差，删除
                    self._remove_association(assoc_id)
                    removed_count += 1
                    logger.debug(f"删除低质量关联: {assoc_id}, 质量分数: {quality_score:.3f}")
                    
                elif quality_score < 0.6:  # 需要优化
                    new_strength, new_confidence = self._optimize_association(
                        original_assoc, quality_score
                    )
                    
                    # 更新关联
                    self._update_association(
                        assoc_id,
                        new_strength,
                        new_confidence,
                        {"last_optimized": datetime.now().isoformat()}
                    )
                    
                    strength_changes.append(new_strength - original_assoc['strength'])
                    confidence_changes.append(new_confidence - original_assoc['confidence'])
                    optimized_count += 1
                    logger.debug(f"优化关联: {assoc_id}, 强度: {original_assoc['strength']:.3f} -> {new_strength:.3f}, "
                               f"置信度: {original_assoc['confidence']:.3f} -> {new_confidence:.3f}")
            
            # 4. 更新结果
            result.associations_optimized = optimized_count
            result.associations_removed = removed_count
            result.average_strength_change = statistics.mean(strength_changes) if strength_changes else 0.0
            result.average_confidence_change = statistics.mean(confidence_changes) if confidence_changes else 0.0
            result.success = True
            
        except Exception as e:
            result.success = False
            result.error_message = str(e)
            logger.error(f"优化过程中出错: {e}")
        
        finally:
            result.optimization_time_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return result
    
    def _get_all_associations(self) -> List[Dict[str, Any]]:
        """获取所有关联关系"""
        cursor = self.connection.cursor()
        cursor.execute("""
            SELECT id, source_id, target_id, association_type, strength, confidence,
                   discovered_by, discovery_time, last_used, usage_count, metadata
            FROM associations
        """)
        
        associations = []
        for row in cursor.fetchall():
            assoc = dict(row)
            # 解析元数据
            if assoc['metadata']:
                assoc['metadata'] = json.loads(assoc['metadata'])
            else:
                assoc['metadata'] = {}
            associations.append(assoc)
        
        return associations
    
    def _analyze_association_quality(self, associations: List[Dict[str, Any]]) -> Dict[int, float]:
        """分析关联质量
        
        Args:
            associations: 关联列表
            
        Returns:
            Dict[int, float]: 关联ID到质量分数的映射
        """
        quality_scores = {}
        
        for assoc in associations:
            score = self._calculate_quality_score(assoc)
            quality_scores[assoc['id']] = score
        
        return quality_scores
    
    def _calculate_quality_score(self, association: Dict[str, Any]) -> float:
        """计算单个关联的质量分数
        
        质量分数基于:
        1. 使用频率 (权重: 0.4)
        2. 时间衰减 (权重: 0.3) 
        3. 置信度 (权重: 0.2)
        4. 发现方法可信度 (权重: 0.1)
        
        Returns:
            float: 质量分数 (0.0-1.0)
        """
        # 1. 使用频率分数
        usage_score = min(association['usage_count'] / 10.0, 1.0)  # 最多10次使用
        
        # 2. 时间衰减分数
        discovery_time = datetime.fromisoformat(association['discovery_time'])
        time_diff_days = (datetime.now() - discovery_time).days
        time_score = math.exp(-time_diff_days / 30.0)  # 30天半衰期
        
        # 3. 置信度分数
        confidence_score = association['confidence']
        
        # 4. 发现方法可信度
        method_score = self._get_discovery_method_score(association['discovered_by'])
        
        # 加权平均
        quality_score = (
            usage_score * 0.4 +
            time_score * 0.3 +
            confidence_score * 0.2 +
            method_score * 0.1
        )
        
        return max(0.0, min(1.0, quality_score))
    
    def _get_discovery_method_score(self, method: str) -> float:
        """获取发现方法的可信度分数"""
        method_scores = {
            "semantic": 0.9,    # 语义分析
            "temporal": 0.8,    # 时间关联
            "usage": 0.7,       # 使用模式
            "manual": 1.0,      # 手动添加
            "test": 0.5,        # 测试
            "auto": 0.6,        # 自动发现
        }
        return method_scores.get(method.lower(), 0.5)
    
    def _optimize_association(self, association: Dict[str, Any], quality_score: float) -> Tuple[float, float]:
        """优化单个关联
        
        Args:
            association: 关联信息
            quality_score: 质量分数
            
        Returns:
            Tuple[float, float]: (新强度, 新置信度)
        """
        original_strength = association['strength']
        original_confidence = association['confidence']
        
        # 基于质量分数调整
        if quality_score < 0.4:
            # 低质量，降低强度和置信度
            new_strength = original_strength * 0.7
            new_confidence = original_confidence * 0.6
        elif quality_score < 0.7:
            # 中等质量，小幅调整
            new_strength = original_strength * 0.9
            new_confidence = original_confidence * 0.8
        else:
            # 高质量，保持或小幅提升
            new_strength = min(original_strength * 1.1, 1.0)
            new_confidence = min(original_confidence * 1.05, 1.0)
        
        # 确保在有效范围内
        new_strength = max(0.1, min(1.0, new_strength))
        new_confidence = max(0.1, min(1.0, new_confidence))
        
        return new_strength, new_confidence
    
    def _remove_association(self, association_id: int):
        """删除关联"""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM associations WHERE id = ?", (association_id,))
        self.connection.commit()
    
    def _update_association(self, association_id: int, strength: float, 
                          confidence: float, metadata_update: Dict[str, Any]):
        """更新关联"""
        cursor = self.connection.cursor()
        
        # 获取现有元数据
        cursor.execute("SELECT metadata FROM associations WHERE id = ?", (association_id,))
        row = cursor.fetchone()
        existing_metadata = {}
        if row and row[0]:
            existing_metadata = json.loads(row[0])
        
        # 合并元数据
        existing_metadata.update(metadata_update)
        
        # 更新关联
        cursor.execute("""
            UPDATE associations 
            SET strength = ?, confidence = ?, metadata = ?, last_used = ?
            WHERE id = ?
        """, (
            strength,
            confidence,
            json.dumps(existing_metadata),
            datetime.now().isoformat(),
            association_id
        ))
        self.connection.commit()
    
    def get_recommendations(self, memory_entry_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """获取智能推荐
        
        Args:
            memory_entry_id: 记忆条目ID
            limit: 推荐数量限制
            
        Returns:
            List[Dict[str, Any]]: 推荐列表
        """
        try:
            cursor = self.connection.cursor()
            
            # 查询相关关联，按质量和强度排序
            cursor.execute("""
                SELECT a.id, a.target_id, a.association_type, a.strength, a.confidence,
                       m.content, m.content_type, m.importance_score
                FROM associations a
                JOIN memory_entries m ON a.target_id = m.id
                WHERE a.source_id = ?
                ORDER BY (a.strength * a.confidence * (a.usage_count + 1)) DESC
                LIMIT ?
            """, (memory_entry_id, limit))
            
            recommendations = []
            for row in cursor.fetchall():
                rec = {
                    'association_id': row[0],
                    'memory_entry_id': row[1],
                    'association_type': row[2],
                    'strength': row[3],
                    'confidence': row[4],
                    'content': row[5],
                    'content_type': row[6],
                    'importance_score': row[7],
                    'relevance_score': row[3] * row[4]  # 综合相关性分数
                }
                recommendations.append(rec)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"获取推荐失败: {e}")
            return []
    
    def analyze_patterns(self) -> List[Dict[str, Any]]:
        """分析关联模式
        
        Returns:
            List[Dict[str, Any]]: 发现的模式列表
        """
        patterns = []
        
        try:
            # 1. 分析关联类型分布
            cursor = self.connection.cursor()
            cursor.execute("""
                SELECT association_type, COUNT(*) as count, 
                       AVG(strength) as avg_strength, AVG(confidence) as avg_confidence
                FROM associations
                GROUP BY association_type
                HAVING COUNT(*) >= 3
            """)
            
            for row in cursor.fetchall():
                pattern = {
                    'pattern_type': 'association_type_distribution',
                    'pattern_data': {
                        'association_type': row[0],
                        'count': row[1],
                        'average_strength': row[2],
                        'average_confidence': row[3]
                    },
                    'confidence': min(row[3] * 0.8, 1.0),  # 基于平均置信度
                    'support_count': row[1],
                    'discovered_at': datetime.now().isoformat(),
                    'is_active': True
                }
                patterns.append(pattern)
            
            # 2. 分析强关联对
            cursor.execute("""
                SELECT source_id, target_id, association_type, strength, confidence
                FROM associations
                WHERE strength >= 0.8 AND confidence >= 0.7
                ORDER BY strength DESC
                LIMIT 10
            """)
            
            strong_pairs = []
            for row in cursor.fetchall():
                strong_pairs.append({
                    'source_id': row[0],
                    'target_id': row[1],
                    'association_type': row[2],
                    'strength': row[3],
                    'confidence': row[4]
                })
            
            if strong_pairs:
                pattern = {
                    'pattern_type': 'strong_association_pairs',
                    'pattern_data': strong_pairs,
                    'confidence': 0.85,
                    'support_count': len(strong_pairs),
                    'discovered_at': datetime.now().isoformat(),
                    'is_active': True
                }
                patterns.append(pattern)
            
            # 保存模式到数据库
            self._save_patterns(patterns)
            
        except Exception as e:
            logger.error(f"模式分析失败: {e}")
        
        return patterns
    
    def _save_patterns(self, patterns: List[Dict[str, Any]]):
        """保存模式到数据库"""
        cursor = self.connection.cursor()
        
        for pattern in patterns:
            cursor.execute("""
                INSERT INTO association_patterns 
                (pattern_type, pattern_data, confidence, support_count, discovered_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                pattern['pattern_type'],
                json.dumps(pattern['pattern_data']),
                pattern['confidence'],
                pattern['support_count'],
                pattern['discovered_at'],
                pattern.get('is_active', True)
            ))
        
        self.connection.commit()
    
    def cleanup_low_quality_associations(self, min_quality_score: float = 0.3) -> int:
        """清理低质量关联
        
        Args:
            min_quality_score: 最低质量分数阈值
            
        Returns:
            int: 清理的关联数量
        """
        try:
            associations = self._get_all_associations()
            removed_count = 0
            
            for assoc in associations:
                quality_score = self._calculate_quality_score(assoc)
                if quality_score < min_quality_score:
                    self._remove_association(assoc['id'])
                    removed_count += 1
                    logger.info(f"清理低质量关联: {assoc['id']}, 质量分数: {quality_score:.3f}")
            
            return removed_count
            
        except Exception as e:
            logger.error(f"清理低质量关联失败: {e}")
            return 0
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """获取优化统计信息
        
        Returns:
            Dict[str, Any]: 统计信息
        """
        stats = {}
        
        try:
            cursor = self.connection.cursor()
            
            # 基本统计
            cursor.execute("SELECT COUNT(*) FROM associations")
            stats['total_associations'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM memory_entries")
            stats['total_memory_entries'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT AVG(strength), AVG(confidence) FROM associations")
            row = cursor.fetchone()
            stats['average_strength'] = row[0] if row[0] else 0.0
            stats['average_confidence'] = row[1] if row[1] else 0.0
            
            # 质量分布
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN strength >= 0.8 AND confidence >= 0.8 THEN 1 END) as high_quality,
                    COUNT(CASE WHEN strength >= 0.6 AND confidence >= 0.6 THEN 1 END) as medium_quality,
                    COUNT(CASE WHEN strength < 0.6 OR confidence < 0.6 THEN 1 END) as low_quality
                FROM associations
            """)
            row = cursor.fetchone()
            stats['high_quality_count'] = row[0]
            stats['medium_quality_count'] = row[1]
            stats['low_quality_count'] = row[2]
            
            # 最近优化
            cursor.execute("""
                SELECT COUNT(*) as optimized_count,
                       MAX(end_time) as last_optimization
                FROM association_discovery_logs
                WHERE discovery_method = 'optimization'
                ORDER BY end_time DESC
                LIMIT 1
            """)
            row = cursor.fetchone()
            stats['last_optimized_count'] = row[0] if row[0] else 0
            stats['last_optimization_time'] = row[1] if row[1] else None
            
        except Exception as e:
            logger.error(f"获取统计信息失败: {e}")
            stats['error'] = str(e)
        
        return stats
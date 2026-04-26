"""
学习能力观察器，用于记录和分析学习经验
"""
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import uuid

from .experience import Experience, ExperienceType, Outcome


class LearningObserver:
    """学习能力观察器"""
    
    def __init__(self, db_path: Optional[str] = None):
        """
        初始化观察器
        
        Args:
            db_path: SQLite数据库路径，如果为None则使用默认路径
        """
        if db_path is None:
            # 默认数据库路径
            base_dir = Path(__file__).parent.parent.parent.parent / "data"
            base_dir.mkdir(exist_ok=True)
            db_path = str(base_dir / "learning_experiences.db")
        
        self.db_path = db_path
        self._init_database()
        
        # 内存缓存
        self._experiences_cache: Dict[str, Experience] = {}
        self._statistics_cache: Optional[Dict[str, Any]] = None
    
    def _init_database(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建经验表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiences (
                id TEXT PRIMARY KEY,
                experience_type TEXT NOT NULL,
                task_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                description TEXT,
                context TEXT,
                actions TEXT,
                reasoning_steps TEXT,
                outcome TEXT NOT NULL,
                result TEXT,
                metrics TEXT,
                lessons_learned TEXT,
                tags TEXT,
                confidence REAL,
                importance REAL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_experience_type ON experiences(experience_type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_id ON experiences(task_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_outcome ON experiences(outcome)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_timestamp ON experiences(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON experiences(tags)')
        
        conn.commit()
        conn.close()
    
    def _generate_id(self, data: Dict[str, Any]) -> str:
        """生成经验ID"""
        # 基于时间戳、任务ID和经验类型生成唯一ID
        timestamp_str = datetime.now().isoformat()
        content = f"{timestamp_str}_{data.get('task_id', '')}_{data.get('experience_type', '')}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def record_experience(self, experience: Experience) -> str:
        """
        记录经验
        
        Args:
            experience: 经验对象
            
        Returns:
            经验ID
        """
        # 确保ID存在
        if not experience.id:
            experience.id = str(uuid.uuid4())
        
        # 更新置信度
        experience.confidence = experience.calculate_confidence()
        
        # 保存到数据库
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO experiences 
            (id, experience_type, task_id, timestamp, description, context, 
             actions, reasoning_steps, outcome, result, metrics, lessons_learned, 
             tags, confidence, importance)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            experience.id,
            experience.experience_type.value,
            experience.task_id,
            experience.timestamp.isoformat(),
            experience.description,
            json.dumps(experience.context, ensure_ascii=False),
            json.dumps(experience.actions, ensure_ascii=False),
            json.dumps(experience.reasoning_steps, ensure_ascii=False),
            experience.outcome.value,
            json.dumps(experience.result, ensure_ascii=False) if experience.result else None,
            json.dumps(experience.metrics, ensure_ascii=False),
            json.dumps(experience.lessons_learned, ensure_ascii=False),
            json.dumps(experience.tags, ensure_ascii=False),
            experience.confidence,
            experience.importance
        ))
        
        conn.commit()
        conn.close()
        
        # 更新缓存
        self._experiences_cache[experience.id] = experience
        self._statistics_cache = None  # 使统计缓存失效
        
        return experience.id
    
    def get_experience(self, experience_id: str) -> Optional[Experience]:
        """
        获取经验
        
        Args:
            experience_id: 经验ID
            
        Returns:
            经验对象，如果不存在则返回None
        """
        # 检查缓存
        if experience_id in self._experiences_cache:
            return self._experiences_cache[experience_id]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM experiences WHERE id = ?', (experience_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        # 解析数据库行
        experience = self._row_to_experience(row)
        self._experiences_cache[experience_id] = experience
        return experience
    
    def _row_to_experience(self, row) -> Experience:
        """将数据库行转换为Experience对象"""
        return Experience.from_dict({
            "id": row[0],
            "experience_type": row[1],
            "task_id": row[2],
            "timestamp": row[3],
            "description": row[4],
            "context": json.loads(row[5]) if row[5] else {},
            "actions": json.loads(row[6]) if row[6] else [],
            "reasoning_steps": json.loads(row[7]) if row[7] else [],
            "outcome": row[8],
            "result": json.loads(row[9]) if row[9] else None,
            "metrics": json.loads(row[10]) if row[10] else {},
            "lessons_learned": json.loads(row[11]) if row[11] else [],
            "tags": json.loads(row[12]) if row[12] else [],
            "confidence": row[13],
            "importance": row[14]
        })
    
    def query_experiences(self, 
                         experience_type: Optional[ExperienceType] = None,
                         task_id: Optional[str] = None,
                         outcome: Optional[Outcome] = None,
                         tags: Optional[List[str]] = None,
                         start_time: Optional[datetime] = None,
                         end_time: Optional[datetime] = None,
                         min_confidence: Optional[float] = None,
                         limit: int = 100,
                         offset: int = 0) -> List[Experience]:
        """
        查询经验
        
        Args:
            experience_type: 经验类型过滤
            task_id: 任务ID过滤
            outcome: 结果过滤
            tags: 标签过滤
            start_time: 开始时间
            end_time: 结束时间
            min_confidence: 最小置信度
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            经验列表
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if experience_type:
            conditions.append("experience_type = ?")
            params.append(experience_type.value)
        
        if task_id:
            conditions.append("task_id = ?")
            params.append(task_id)
        
        if outcome:
            conditions.append("outcome = ?")
            params.append(outcome.value)
        
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f'%"{tag}"%')
        
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time.isoformat())
        
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time.isoformat())
        
        if min_confidence is not None:
            conditions.append("confidence >= ?")
            params.append(min_confidence)
        
        # 构建查询语句
        query = "SELECT * FROM experiences"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        # 转换为Experience对象
        experiences = []
        for row in rows:
            experience = self._row_to_experience(row)
            experiences.append(experience)
            # 更新缓存
            self._experiences_cache[experience.id] = experience
        
        return experiences
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        # 检查缓存
        if self._statistics_cache is not None:
            return self._statistics_cache.copy()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        statistics = {}
        
        # 总经验数
        cursor.execute("SELECT COUNT(*) FROM experiences")
        statistics["total_experiences"] = cursor.fetchone()[0]
        
        # 按类型统计
        cursor.execute("SELECT experience_type, COUNT(*) FROM experiences GROUP BY experience_type")
        statistics["by_type"] = dict(cursor.fetchall())
        
        # 按结果统计
        cursor.execute("SELECT outcome, COUNT(*) FROM experiences GROUP BY outcome")
        statistics["by_outcome"] = dict(cursor.fetchall())
        
        # 平均置信度
        cursor.execute("SELECT AVG(confidence) FROM experiences")
        statistics["avg_confidence"] = cursor.fetchone()[0] or 0.0
        
        # 最近24小时经验数
        yesterday = datetime.now() - timedelta(days=1)
        cursor.execute("SELECT COUNT(*) FROM experiences WHERE timestamp >= ?", 
                      (yesterday.isoformat(),))
        statistics["recent_24h"] = cursor.fetchone()[0]
        
        # 最常见的标签
        cursor.execute('''
            SELECT value, COUNT(*) as count
            FROM (
                SELECT json_each.value as value
                FROM experiences, json_each(experiences.tags)
            )
            GROUP BY value
            ORDER BY count DESC
            LIMIT 10
        ''')
        statistics["top_tags"] = dict(cursor.fetchall())
        
        conn.close()
        
        # 缓存结果
        self._statistics_cache = statistics
        return statistics.copy()
    
    def analyze_learning_patterns(self, 
                                 window_days: int = 7) -> Dict[str, Any]:
        """
        分析学习模式
        
        Args:
            window_days: 分析窗口天数
            
        Returns:
            学习模式分析结果
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        start_time = datetime.now() - timedelta(days=window_days)
        
        analysis = {
            "window_days": window_days,
            "start_time": start_time.isoformat(),
            "end_time": datetime.now().isoformat()
        }
        
        # 成功率趋势
        cursor.execute('''
            SELECT DATE(timestamp) as date, 
                   outcome,
                   COUNT(*) as count
            FROM experiences
            WHERE timestamp >= ?
            GROUP BY DATE(timestamp), outcome
            ORDER BY date
        ''', (start_time.isoformat(),))
        
        success_trend = {}
        for row in cursor.fetchall():
            date_str, outcome, count = row
            if date_str not in success_trend:
                success_trend[date_str] = {"success": 0, "total": 0}
            
            success_trend[date_str]["total"] += count
            if outcome == Outcome.SUCCESS.value:
                success_trend[date_str]["success"] += count
        
        # 计算每日成功率
        daily_success_rates = {}
        for date_str, counts in success_trend.items():
            if counts["total"] > 0:
                daily_success_rates[date_str] = counts["success"] / counts["total"]
        
        analysis["daily_success_rates"] = daily_success_rates
        
        # 工具使用频率
        cursor.execute('''
            SELECT json_extract(actions.value, '$.tool_name') as tool_name,
                   COUNT(*) as usage_count
            FROM experiences, json_each(experiences.actions) as actions
            WHERE timestamp >= ?
            GROUP BY tool_name
            ORDER BY usage_count DESC
            LIMIT 10
        ''', (start_time.isoformat(),))
        
        analysis["tool_usage_frequency"] = dict(cursor.fetchall())
        
        # 问题解决时间分析（如果有持续时间指标）
        cursor.execute('''
            SELECT experience_type,
                   AVG(json_extract(metrics, '$.duration')) as avg_duration
            FROM experiences
            WHERE timestamp >= ? 
                  AND json_extract(metrics, '$.duration') IS NOT NULL
            GROUP BY experience_type
        ''', (start_time.isoformat(),))
        
        analysis["avg_duration_by_type"] = dict(cursor.fetchall())
        
        conn.close()
        
        return analysis
    
    def export_experiences(self, 
                          file_path: str,
                          format: str = "json") -> bool:
        """
        导出经验数据
        
        Args:
            file_path: 导出文件路径
            format: 导出格式，支持"json"和"csv"
            
        Returns:
            是否成功
        """
        try:
            experiences = self.query_experiences(limit=1000)
            
            if format.lower() == "json":
                data = [exp.to_dict() for exp in experiences]
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            
            elif format.lower() == "csv":
                import csv
                # 获取所有可能的字段
                all_fields = set()
                for exp in experiences:
                    all_fields.update(exp.to_dict().keys())
                
                with open(file_path, 'w', encoding='utf-8', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=sorted(all_fields))
                    writer.writeheader()
                    for exp in experiences:
                        writer.writerow(exp.to_dict())
            
            else:
                raise ValueError(f"不支持的格式: {format}")
            
            return True
            
        except Exception as e:
            print(f"导出失败: {e}")
            return False
    
    def clear_cache(self):
        """清空缓存"""
        self._experiences_cache.clear()
        self._statistics_cache = None
    
    def __del__(self):
        """析构函数，确保数据库连接关闭"""
        pass
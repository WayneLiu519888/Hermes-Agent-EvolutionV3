"""
工具注册表模块
负责工具的注册、查询、统计和管理
"""

import json
import os
import sqlite3
from dataclasses import dataclass, asdict

from ..db_utils import get_evolution_db
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
from enum import Enum


class ToolCategory(Enum):
    """工具类别枚举"""
    UTILITY = "utility"  # 实用工具
    DATA_PROCESSING = "data_processing"  # 数据处理
    FILE_OPERATION = "file_operation"  # 文件操作
    NETWORK = "network"  # 网络操作
    AI = "ai"  # AI相关
    CUSTOM = "custom"  # 自定义


class ToolStatus(Enum):
    """工具状态枚举"""
    ACTIVE = "active"  # 活跃可用
    DEPRECATED = "deprecated"  # 已弃用
    EXPERIMENTAL = "experimental"  # 实验性
    DISABLED = "disabled"  # 已禁用


@dataclass
class ToolDefinition:
    """工具定义数据类"""
    name: str  # 工具名称
    description: str  # 工具描述
    category: ToolCategory  # 工具类别
    status: ToolStatus = ToolStatus.ACTIVE  # 工具状态
    version: str = "1.0.0"  # 版本号
    author: str = "system"  # 作者
    created_at: datetime = None  # 创建时间
    updated_at: datetime = None  # 更新时间
    usage_count: int = 0  # 使用次数
    success_count: int = 0  # 成功次数
    error_count: int = 0  # 错误次数
    parameters: Dict[str, Any] = None  # 参数定义
    return_type: str = "Any"  # 返回类型
    dependencies: List[str] = None  # 依赖项
    tags: List[str] = None  # 标签
    source_code: str = ""  # 源代码
    is_builtin: bool = False  # 是否为内置工具
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()
        if self.parameters is None:
            self.parameters = {}
        if self.dependencies is None:
            self.dependencies = []
        if self.tags is None:
            self.tags = []
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 处理枚举类型
        data['category'] = self.category.value
        data['status'] = self.status.value
        # 处理时间类型
        data['created_at'] = self.created_at.isoformat()
        data['updated_at'] = self.updated_at.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ToolDefinition':
        """从字典创建实例"""
        # 处理枚举类型
        data['category'] = ToolCategory(data['category'])
        data['status'] = ToolStatus(data['status'])
        # 处理时间类型
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self, db_path: str = "data/tools.db"):
        """
        初始化工具注册表
        
        Args:
            db_path: 数据库文件路径（使用 ":memory:" 创建内存数据库）
        """
        self.db_path = db_path
        self._memory_conn = sqlite3.connect(":memory:") if db_path == ":memory:" else None
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接（支持内存数据库）"""
        if self._memory_conn:
            return self._memory_conn
        return get_evolution_db('tools.db')
    
    def _init_database(self):
        """初始化数据库"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 创建工具表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                status TEXT NOT NULL,
                version TEXT NOT NULL,
                author TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                usage_count INTEGER DEFAULT 0,
                success_count INTEGER DEFAULT 0,
                error_count INTEGER DEFAULT 0,
                parameters TEXT NOT NULL,
                return_type TEXT NOT NULL,
                dependencies TEXT NOT NULL,
                tags TEXT NOT NULL,
                source_code TEXT NOT NULL,
                is_builtin BOOLEAN DEFAULT 0
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_name ON tools(name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON tools(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_status ON tools(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_tags ON tools(tags)')
        
        conn.commit()
        if not self._memory_conn:
            conn.close()
    
    def register(self, tool: ToolDefinition) -> bool:
        """
        注册工具
        
        Args:
            tool: 工具定义
            
        Returns:
            是否注册成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 检查是否已存在
            cursor.execute('SELECT id FROM tools WHERE name = ?', (tool.name,))
            existing = cursor.fetchone()
            
            tool.updated_at = datetime.now()
            tool_dict = tool.to_dict()
            
            if existing:
                # 更新现有工具
                cursor.execute('''
                    UPDATE tools SET
                        description = ?,
                        category = ?,
                        status = ?,
                        version = ?,
                        author = ?,
                        updated_at = ?,
                        parameters = ?,
                        return_type = ?,
                        dependencies = ?,
                        tags = ?,
                        source_code = ?,
                        is_builtin = ?
                    WHERE name = ?
                ''', (
                    tool_dict['description'],
                    tool_dict['category'],
                    tool_dict['status'],
                    tool_dict['version'],
                    tool_dict['author'],
                    tool_dict['updated_at'],
                    json.dumps(tool_dict['parameters']),
                    tool_dict['return_type'],
                    json.dumps(tool_dict['dependencies']),
                    json.dumps(tool_dict['tags']),
                    tool_dict['source_code'],
                    1 if tool_dict['is_builtin'] else 0,
                    tool_dict['name']
                ))
            else:
                # 插入新工具
                cursor.execute('''
                    INSERT INTO tools (
                        name, description, category, status, version, author,
                        created_at, updated_at, parameters, return_type,
                        dependencies, tags, source_code, is_builtin
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    tool_dict['name'],
                    tool_dict['description'],
                    tool_dict['category'],
                    tool_dict['status'],
                    tool_dict['version'],
                    tool_dict['author'],
                    tool_dict['created_at'],
                    tool_dict['updated_at'],
                    json.dumps(tool_dict['parameters']),
                    tool_dict['return_type'],
                    json.dumps(tool_dict['dependencies']),
                    json.dumps(tool_dict['tags']),
                    tool_dict['source_code'],
                    1 if tool_dict['is_builtin'] else 0
                ))
            
            conn.commit()
            if not self._memory_conn:
                conn.close()
            return True
            
        except Exception as e:
            print(f"注册工具失败: {e}")
            return False
    
    def get(self, name: str) -> Optional[ToolDefinition]:
        """
        获取工具定义
        
        Args:
            name: 工具名称
            
        Returns:
            工具定义，如果不存在则返回None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM tools WHERE name = ?', (name,))
            row = cursor.fetchone()
            
            if not self._memory_conn:
                conn.close()
            
            if not row:
                return None
            
            # 解析数据库行
            tool_dict = {
                'name': row[1],
                'description': row[2],
                'category': row[3],
                'status': row[4],
                'version': row[5],
                'author': row[6],
                'created_at': row[7],
                'updated_at': row[8],
                'usage_count': row[9],
                'success_count': row[10],
                'error_count': row[11],
                'parameters': json.loads(row[12]),
                'return_type': row[13],
                'dependencies': json.loads(row[14]),
                'tags': json.loads(row[15]),
                'source_code': row[16],
                'is_builtin': bool(row[17])
            }
            
            return ToolDefinition.from_dict(tool_dict)
            
        except Exception as e:
            print(f"获取工具失败: {e}")
            return None
    
    def list_all(self, category: Optional[str] = None, 
                 status: Optional[str] = None,
                 tag: Optional[str] = None) -> List[ToolDefinition]:
        """
        列出所有工具
        
        Args:
            category: 按类别过滤
            status: 按状态过滤
            tag: 按标签过滤
            
        Returns:
            工具定义列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            query = 'SELECT * FROM tools WHERE 1=1'
            params = []
            
            if category:
                query += ' AND category = ?'
                params.append(category)
            
            if status:
                query += ' AND status = ?'
                params.append(status)
            
            if tag:
                query += ' AND tags LIKE ?'
                params.append(f'%"{tag}"%')
            
            query += ' ORDER BY name'
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not self._memory_conn:
                conn.close()
            
            tools = []
            for row in rows:
                tool_dict = {
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'status': row[4],
                    'version': row[5],
                    'author': row[6],
                    'created_at': row[7],
                    'updated_at': row[8],
                    'usage_count': row[9],
                    'success_count': row[10],
                    'error_count': row[11],
                    'parameters': json.loads(row[12]),
                    'return_type': row[13],
                    'dependencies': json.loads(row[14]),
                    'tags': json.loads(row[15]),
                    'source_code': row[16],
                    'is_builtin': bool(row[17])
                }
                tools.append(ToolDefinition.from_dict(tool_dict))
            
            return tools
            
        except Exception as e:
            print(f"列出工具失败: {e}")
            return []
    
    def update_usage_stats(self, name: str, success: bool = True):
        """
        更新工具使用统计
        
        Args:
            name: 工具名称
            success: 是否成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tools SET
                    usage_count = usage_count + 1,
                    success_count = success_count + ?,
                    error_count = error_count + ?,
                    updated_at = ?
                WHERE name = ?
            ''', (
                1 if success else 0,
                0 if success else 1,
                datetime.now().isoformat(),
                name
            ))
            
            conn.commit()
            if not self._memory_conn:
                conn.close()
            
        except Exception as e:
            print(f"更新使用统计失败: {e}")
    
    def delete(self, name: str) -> bool:
        """
        删除工具
        
        Args:
            name: 工具名称
            
        Returns:
            是否删除成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM tools WHERE name = ?', (name,))
            conn.commit()
            
            deleted = cursor.rowcount > 0
            
            if not self._memory_conn:
                conn.close()
            
            return deleted
            
        except Exception as e:
            print(f"删除工具失败: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 总数统计
            cursor.execute('SELECT COUNT(*) FROM tools')
            total = cursor.fetchone()[0]
            
            # 按类别统计
            cursor.execute('SELECT category, COUNT(*) FROM tools GROUP BY category')
            by_category = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 按状态统计
            cursor.execute('SELECT status, COUNT(*) FROM tools GROUP BY status')
            by_status = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 使用统计
            cursor.execute('SELECT SUM(usage_count), SUM(success_count), SUM(error_count) FROM tools')
            usage_stats = cursor.fetchone()
            
            # 最近更新
            cursor.execute('SELECT name, updated_at FROM tools ORDER BY updated_at DESC LIMIT 5')
            recent_updates = cursor.fetchall()
            
            if not self._memory_conn:
                conn.close()
            
            return {
                'total_tools': total,
                'by_category': by_category,
                'by_status': by_status,
                'total_usage': usage_stats[0] or 0,
                'total_success': usage_stats[1] or 0,
                'total_error': usage_stats[2] or 0,
                'recent_updates': recent_updates
            }
            
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            return {}
    
    def search(self, query: str) -> List[ToolDefinition]:
        """
        搜索工具
        
        Args:
            query: 搜索关键词
            
        Returns:
            匹配的工具列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            search_pattern = f'%{query}%'
            cursor.execute('''
                SELECT * FROM tools 
                WHERE name LIKE ? 
                   OR description LIKE ? 
                   OR tags LIKE ?
                ORDER BY name
            ''', (search_pattern, search_pattern, search_pattern))
            
            rows = cursor.fetchall()
            
            if not self._memory_conn:
                conn.close()
            
            tools = []
            for row in rows:
                tool_dict = {
                    'name': row[1],
                    'description': row[2],
                    'category': row[3],
                    'status': row[4],
                    'version': row[5],
                    'author': row[6],
                    'created_at': row[7],
                    'updated_at': row[8],
                    'usage_count': row[9],
                    'success_count': row[10],
                    'error_count': row[11],
                    'parameters': json.loads(row[12]),
                    'return_type': row[13],
                    'dependencies': json.loads(row[14]),
                    'tags': json.loads(row[15]),
                    'source_code': row[16],
                    'is_builtin': bool(row[17])
                }
                tools.append(ToolDefinition.from_dict(tool_dict))
            
            return tools
            
        except Exception as e:
            print(f"搜索工具失败: {e}")
            return []

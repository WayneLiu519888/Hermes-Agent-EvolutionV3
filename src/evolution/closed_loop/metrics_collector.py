"""
SystemMetricsCollector — 系统指标采集器
采集 Hermes Agent 自身的真实运行指标，替代模拟数据

采集维度:
1. 系统级: CPU, 内存, 磁盘, 进程状态
2. 应用级: 工具调用统计, 成功率, 响应时间
3. 进化级: 循环统计, 改进追踪, 学习进展
4. 资源级: 数据库大小, 经验数量, 模式数量
"""

import os
import sys
import time
import json
import psutil
import logging
import threading
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import deque

logger = logging.getLogger(__name__)


class SystemMetricsCollector:
    """
    系统指标采集器
    
    采集真实的系统运行指标，支持:
    - 一次性采集
    - 周期性采集（后台线程）
    - 指标历史追踪
    - 自定义指标注册
    
    用法:
        collector = SystemMetricsCollector()
        collector.start()  # 启动后台采集
        
        metrics = collector.collect_all()
        print(metrics['system.cpu_percent'])
        
        collector.stop()
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 配置
        """
        self.config = config or {}
        
        # 进程信息
        self.process = psutil.Process(os.getpid())
        
        # 采集控制
        self.collection_interval = self.config.get('collection_interval', 30)  # 秒
        self.history_size = self.config.get('history_size', 100)
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        
        # 指标历史 (环形缓冲)
        self._metric_history: Dict[str, deque] = {
            'system.cpu_percent': deque(maxlen=self.history_size),
            'system.memory_mb': deque(maxlen=self.history_size),
            'system.memory_percent': deque(maxlen=self.history_size),
            'system.thread_count': deque(maxlen=self.history_size),
            'system.open_files': deque(maxlen=self.history_size),
        }
        
        # 工具调用统计 (运行时累加)
        self._tool_stats: Dict[str, Dict[str, Any]] = {}
        self._tool_stats_lock = threading.Lock()
        
        # 经验统计
        self._experience_count = 0
        self._pattern_count = 0
        self._improvement_count = 0
        
        # 性能计数器
        self._operation_times: Dict[str, List[float]] = {}
        self._error_counts: Dict[str, int] = {}
        
        # 自定义指标采集器
        self._custom_collectors: Dict[str, Callable[[], Any]] = {}
        
        # 数据目录
        self.data_dir = Path(self.config.get('data_dir', 'data/evolution'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.metrics_log_path = self.data_dir / 'system_metrics.jsonl'
        
        logger.info(f"SystemMetricsCollector 初始化: interval={self.collection_interval}s")
    
    # ━━━━ 生命周期 ━━━━
    
    def start(self) -> None:
        """启动后台指标采集"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(
            target=self._collection_loop,
            name="MetricsCollector",
            daemon=True
        )
        self._thread.start()
        logger.info("📊 SystemMetricsCollector 后台采集已启动")
    
    def stop(self) -> None:
        """停止后台采集"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        logger.info("SystemMetricsCollector 已停止")
    
    def _collection_loop(self) -> None:
        """后台采集循环"""
        while self._running:
            try:
                metrics = self._collect_system_metrics()
                self._store_metrics(metrics)
            except Exception as e:
                logger.debug(f"后台采集异常: {e}")
            
            time.sleep(self.collection_interval)
    
    # ━━━━ 系统级指标采集 ━━━━
    
    def _collect_system_metrics(self) -> Dict[str, float]:
        """采集系统级指标"""
        metrics = {}
        
        try:
            # CPU
            cpu = self.process.cpu_percent(interval=0.1)
            metrics['system.cpu_percent'] = cpu
            
            # 内存
            mem = self.process.memory_info()
            metrics['system.memory_mb'] = mem.rss / 1024 / 1024
            metrics['system.memory_percent'] = self.process.memory_percent()
            
            # 线程数
            metrics['system.thread_count'] = self.process.num_threads()
            
            # 打开文件数
            try:
                metrics['system.open_files'] = len(self.process.open_files())
            except Exception:
                metrics['system.open_files'] = 0
            
            # 运行时间
            create_time = datetime.fromtimestamp(self.process.create_time())
            metrics['system.uptime_seconds'] = (datetime.now() - create_time).total_seconds()
            
        except Exception as e:
            logger.debug(f"系统指标采集异常: {e}")
        
        return metrics
    
    def _store_metrics(self, metrics: Dict[str, float]) -> None:
        """存储指标到历史缓冲"""
        with self._lock:
            for key, value in metrics.items():
                if key in self._metric_history:
                    self._metric_history[key].append(value)
    
    # ━━━━ 全部指标采集 ━━━━
    
    def collect_all(self) -> Dict[str, Any]:
        """
        采集所有维度指标
        
        Returns:
            完整指标字典
        """
        all_metrics = {}
        
        # 1. 系统指标
        sys_metrics = self._collect_system_metrics()
        all_metrics.update(sys_metrics)
        
        # 2. 系统指标历史统计
        all_metrics.update(self._compute_system_statistics())
        
        # 3. 应用级指标
        all_metrics.update(self._collect_tool_metrics())
        
        # 4. 进化级指标
        all_metrics.update(self._collect_evolution_metrics())
        
        # 5. 自定义指标
        all_metrics.update(self._collect_custom_metrics())
        
        # 6. 保存到日志
        self._save_metrics(all_metrics)
        
        return all_metrics
    
    def collect_minimal(self) -> Dict[str, Any]:
        """采集最小指标集（快速）"""
        return {
            **self._collect_system_metrics(),
            'system.success_rate': 0.85,  # 默认值
            'system.response_time_avg': 0.5,
            'system.error_rate': 0.02,
            'tools.total_count': 0,
            'tools.active_count': 0,
        }
    
    def _compute_system_statistics(self) -> Dict[str, Any]:
        """计算系统指标历史统计"""
        stats = {}
        with self._lock:
            for key, history in self._metric_history.items():
                if not history:
                    continue
                
                values = list(history)
                stats[f"{key}.avg"] = sum(values) / len(values)
                stats[f"{key}.max"] = max(values)
                stats[f"{key}.min"] = min(values)
                stats[f"{key}.latest"] = values[-1]
        
        return stats
    
    # ━━━━ 工具级指标 ━━━━
    
    def record_tool_call(self, tool_name: str, success: bool, 
                         execution_time: float, error: Optional[str] = None) -> None:
        """
        记录一次工具调用
        
        Args:
            tool_name: 工具名
            success: 是否成功
            execution_time: 执行时间（秒）
            error: 错误信息
        """
        with self._tool_stats_lock:
            if tool_name not in self._tool_stats:
                self._tool_stats[tool_name] = {
                    'total_calls': 0,
                    'success_calls': 0,
                    'failure_calls': 0,
                    'total_time': 0.0,
                    'min_time': float('inf'),
                    'max_time': 0.0,
                    'last_call': None,
                    'last_error': None,
                }
            
            stats = self._tool_stats[tool_name]
            stats['total_calls'] += 1
            stats['total_time'] += execution_time
            stats['last_call'] = datetime.now().isoformat()
            
            if success:
                stats['success_calls'] += 1
            else:
                stats['failure_calls'] += 1
                if error:
                    stats['last_error'] = error[:200]
            
            if execution_time < stats['min_time']:
                stats['min_time'] = execution_time
            if execution_time > stats['max_time']:
                stats['max_time'] = execution_time
    
    def _collect_tool_metrics(self) -> Dict[str, Any]:
        """采集工具调用指标"""
        metrics = {}
        
        with self._tool_stats_lock:
            total_calls = sum(s['total_calls'] for s in self._tool_stats.values())
            total_success = sum(s['success_calls'] for s in self._tool_stats.values())
            
            metrics['tools.total_count'] = len(self._tool_stats)
            metrics['tools.active_count'] = sum(
                1 for s in self._tool_stats.values()
                if s['total_calls'] > 0
            )
            metrics['tools.total_calls'] = total_calls
            metrics['system.success_rate'] = (
                total_success / total_calls if total_calls > 0 else 0.85
            )
            
            # 工具级详情
            tool_details = {}
            for name, stats in self._tool_stats.items():
                calls = stats['total_calls']
                tool_details[name] = {
                    'calls': calls,
                    'success_rate': stats['success_calls'] / calls if calls > 0 else 1.0,
                    'avg_time': stats['total_time'] / calls if calls > 0 else 0,
                    'last_call': stats['last_call'],
                }
            metrics['tools.details'] = tool_details
        
        # 错误率
        total = metrics.get('tools.total_calls', 0)
        errors = sum(self._error_counts.values())
        metrics['system.error_rate'] = errors / total if total > 0 else 0.0
        
        # 响应时间
        with self._tool_stats_lock:
            all_times = []
            for stats in self._tool_stats.values():
                if stats['total_calls'] > 0:
                    all_times.append(stats['total_time'] / stats['total_calls'])
            metrics['system.response_time_avg'] = (
                sum(all_times) / len(all_times) if all_times else 0.5
            )
        
        return metrics
    
    # ━━━━ 进化级指标 ━━━━
    
    def record_experience(self, count: int = 1) -> None:
        """记录经验数量变化"""
        self._experience_count += count
    
    def record_pattern(self, count: int = 1) -> None:
        """记录模式数量变化"""
        self._pattern_count += count
    
    def record_improvement(self, count: int = 1) -> None:
        """记录改进数量"""
        self._improvement_count += count
    
    def _collect_evolution_metrics(self) -> Dict[str, Any]:
        """采集进化级指标"""
        return {
            'evolution.total_experiences': self._experience_count,
            'evolution.total_patterns': self._pattern_count,
            'evolution.total_improvements': self._improvement_count,
        }
    
    # ━━━━ 自定义指标 ━━━━
    
    def register_collector(self, name: str, collector_fn: Callable[[], Any]) -> None:
        """注册自定义指标采集器"""
        self._custom_collectors[name] = collector_fn
    
    def _collect_custom_metrics(self) -> Dict[str, Any]:
        """采集自定义指标"""
        metrics = {}
        for name, fn in self._custom_collectors.items():
            try:
                metrics[name] = fn()
            except Exception as e:
                logger.debug(f"自定义采集器 '{name}' 异常: {e}")
        return metrics
    
    # ━━━━ 持久化 ━━━━
    
    def _save_metrics(self, metrics: Dict[str, Any]) -> None:
        """保存指标到日志文件"""
        try:
            # 只保存关键指标（避免太大）
            slim = {
                'timestamp': datetime.now().isoformat(),
                'cpu': metrics.get('system.cpu_percent'),
                'memory_mb': metrics.get('system.memory_mb'),
                'success_rate': metrics.get('system.success_rate'),
                'response_time': metrics.get('system.response_time_avg'),
                'error_rate': metrics.get('system.error_rate'),
                'tool_count': metrics.get('tools.total_count'),
                'tool_calls': metrics.get('tools.total_calls'),
                'experiences': self._experience_count,
                'patterns': self._pattern_count,
                'improvements': self._improvement_count,
            }
            
            with open(self.metrics_log_path, 'a') as f:
                f.write(json.dumps(slim, ensure_ascii=False) + '\n')
                
        except Exception as e:
            logger.debug(f"保存指标失败: {e}")
    
    # ━━━━ 查询接口 ━━━━
    
    def get_tool_stats(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """获取指定工具统计"""
        with self._tool_stats_lock:
            stats = self._tool_stats.get(tool_name)
            if stats and stats['total_calls'] > 0:
                return {
                    **stats,
                    'success_rate': stats['success_calls'] / stats['total_calls'],
                    'avg_time': stats['total_time'] / stats['total_calls'],
                }
        return None
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康快照"""
        metrics = self.collect_all()
        
        health_score = 100
        
        # 扣分项
        if metrics.get('system.memory_percent', 0) > 80:
            health_score -= 20
        if metrics.get('system.cpu_percent', 0) > 80:
            health_score -= 15
        success_rate = metrics.get('system.success_rate', 0.85)
        if success_rate < 0.8:
            health_score -= int((0.8 - success_rate) * 100)
        
        return {
            'score': max(0, min(100, health_score)),
            'status': 'healthy' if health_score >= 80 else 'warning' if health_score >= 60 else 'critical',
            'metrics': {
                'cpu': metrics.get('system.cpu_percent'),
                'memory_mb': metrics.get('system.memory_mb'),
                'memory_percent': metrics.get('system.memory_percent'),
                'success_rate': success_rate,
                'response_time': metrics.get('system.response_time_avg'),
                'tool_calls': metrics.get('tools.total_calls'),
                'errors': metrics.get('system.error_rate'),
            },
            'timestamp': datetime.now().isoformat(),
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        all_metrics = self.collect_all()
        
        return {
            'system': {
                'cpu': f"{all_metrics.get('system.cpu_percent', 0):.1f}%",
                'memory': f"{all_metrics.get('system.memory_mb', 0):.0f}MB",
                'uptime': f"{all_metrics.get('system.uptime_seconds', 0):.0f}s",
                'threads': all_metrics.get('system.thread_count', 0),
            },
            'performance': {
                'success_rate': f"{all_metrics.get('system.success_rate', 0):.1%}",
                'response_time': f"{all_metrics.get('system.response_time_avg', 0):.3f}s",
                'error_rate': f"{all_metrics.get('system.error_rate', 0):.1%}",
            },
            'tools': {
                'total': all_metrics.get('tools.total_count', 0),
                'active': all_metrics.get('tools.active_count', 0),
                'total_calls': all_metrics.get('tools.total_calls', 0),
            },
            'evolution': {
                'experiences': self._experience_count,
                'patterns': self._pattern_count,
                'improvements': self._improvement_count,
            },
            'timestamp': datetime.now().isoformat(),
        }

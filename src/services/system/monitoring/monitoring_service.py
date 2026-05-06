"""
监控和可观测性模块 - 系统健康监控、性能指标、日志聚合
支持Prometheus指标、结构化日志、分布式追踪
"""

import logging
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import asyncio
from collections import defaultdict, deque
import json
import psutil
import socket
import threading

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"      # 计数器，只增不减
    GAUGE = "gauge"          # 仪表，可增可减
    HISTOGRAM = "histogram"  # 直方图，统计分布
    SUMMARY = "summary"      # 摘要，分位数统计


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"      # 健康
    DEGRADED = "degraded"    # 降级
    UNHEALTHY = "unhealthy"  # 不健康
    UNKNOWN = "unknown"      # 未知


@dataclass
class Metric:
    """指标"""
    name: str
    metric_type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    description: str = ""
    
    def to_prometheus(self) -> str:
        """转换为Prometheus格式"""
        # 构建标签字符串
        label_str = ""
        if self.labels:
            label_parts = [f'{k}="{v}"' for k, v in self.labels.items()]
            label_str = "{" + ",".join(label_parts) + "}"
        
        # 构建指标行
        metric_name = self.name.replace(".", "_").replace("-", "_")
        return f'{metric_name}{label_str} {self.value} {int(self.timestamp.timestamp() * 1000)}'
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "type": self.metric_type.value,
            "value": self.value,
            "labels": self.labels,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description
        }


@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    status: HealthStatus
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class MetricsCollector:
    """指标收集器"""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.max_metrics_per_name = 1000
        self.lock = threading.RLock()
        
        # 系统指标收集
        self.system_metrics_enabled = True
        self.collection_interval = 60  # 秒
        
        logger.info("指标收集器初始化完成")
    
    def record_metric(
        self,
        name: str,
        value: float,
        metric_type: MetricType = MetricType.GAUGE,
        labels: Dict[str, str] = None,
        description: str = ""
    ) -> None:
        """记录指标"""
        with self.lock:
            metric = Metric(
                name=name,
                metric_type=metric_type,
                value=value,
                labels=labels or {},
                description=description
            )
            
            self.metrics[name].append(metric)
            
            # 限制存储数量
            if len(self.metrics[name]) > self.max_metrics_per_name:
                self.metrics[name] = self.metrics[name][-self.max_metrics_per_name:]
    
    def increment_counter(
        self,
        name: str,
        increment: float = 1.0,
        labels: Dict[str, str] = None,
        description: str = ""
    ) -> None:
        """增加计数器"""
        with self.lock:
            # 获取当前值
            current_value = 0.0
            if self.metrics[name]:
                current_value = self.metrics[name][-1].value
            
            # 记录新值
            self.record_metric(
                name=name,
                value=current_value + increment,
                metric_type=MetricType.COUNTER,
                labels=labels,
                description=description
            )
    
    def set_gauge(
        self,
        name: str,
        value: float,
        labels: Dict[str, str] = None,
        description: str = ""
    ) -> None:
        """设置仪表值"""
        self.record_metric(
            name=name,
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels,
            description=description
        )
    
    def record_histogram(
        self,
        name: str,
        value: float,
        buckets: List[float] = None,
        labels: Dict[str, str] = None,
        description: str = ""
    ) -> None:
        """记录直方图"""
        # 记录原始值
        self.record_metric(
            name=f"{name}_raw",
            value=value,
            metric_type=MetricType.GAUGE,
            labels=labels,
            description=f"Raw value for {name}"
        )
        
        # 记录桶统计
        if buckets:
            for bucket in buckets:
                bucket_name = f"{name}_bucket"
                bucket_labels = (labels or {}).copy()
                bucket_labels["le"] = str(bucket)
                
                self.record_metric(
                    name=bucket_name,
                    value=1.0 if value <= bucket else 0.0,
                    metric_type=MetricType.COUNTER,
                    labels=bucket_labels,
                    description=f"Bucket counter for {name}"
                )
        
        # 记录总和
        self.record_metric(
            name=f"{name}_sum",
            value=value,
            metric_type=MetricType.COUNTER,
            labels=labels,
            description=f"Sum for {name}"
        )
        
        # 记录计数
        self.record_metric(
            name=f"{name}_count",
            value=1.0,
            metric_type=MetricType.COUNTER,
            labels=labels,
            description=f"Count for {name}"
        )
    
    def get_metric(self, name: str, limit: int = 100) -> List[Metric]:
        """获取指标"""
        with self.lock:
            metrics = self.metrics.get(name, [])
            return metrics[-limit:] if limit else metrics
    
    def get_latest_metric(self, name: str) -> Optional[Metric]:
        """获取最新指标"""
        with self.lock:
            metrics = self.metrics.get(name, [])
            return metrics[-1] if metrics else None
    
    def get_metric_stats(
        self,
        name: str,
        time_window: timedelta = None
    ) -> Dict[str, Any]:
        """获取指标统计"""
        with self.lock:
            metrics = self.metrics.get(name, [])
            
            if time_window:
                cutoff_time = datetime.now() - time_window
                metrics = [m for m in metrics if m.timestamp >= cutoff_time]
            
            if not metrics:
                return {}
            
            values = [m.value for m in metrics]
            
            return {
                "count": len(values),
                "min": min(values),
                "max": max(values),
                "mean": sum(values) / len(values),
                "latest": values[-1],
                "timestamp_range": {
                    "start": metrics[0].timestamp.isoformat(),
                    "end": metrics[-1].timestamp.isoformat()
                }
            }
    
    def collect_system_metrics(self) -> None:
        """收集系统指标"""
        if not self.system_metrics_enabled:
            return
        
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=None)
            self.set_gauge(
                "system_cpu_percent",
                cpu_percent,
                description="CPU使用率百分比"
            )
            
            # 内存使用
            memory = psutil.virtual_memory()
            self.set_gauge(
                "system_memory_total",
                memory.total,
                description="总内存（字节）"
            )
            self.set_gauge(
                "system_memory_available",
                memory.available,
                description="可用内存（字节）"
            )
            self.set_gauge(
                "system_memory_percent",
                memory.percent,
                description="内存使用率百分比"
            )
            
            # 磁盘使用
            disk = psutil.disk_usage('/')
            self.set_gauge(
                "system_disk_total",
                disk.total,
                description="总磁盘空间（字节）"
            )
            self.set_gauge(
                "system_disk_free",
                disk.free,
                description="可用磁盘空间（字节）"
            )
            self.set_gauge(
                "system_disk_percent",
                disk.percent,
                description="磁盘使用率百分比"
            )
            
            # 网络IO
            net_io = psutil.net_io_counters()
            self.set_gauge(
                "system_network_bytes_sent",
                net_io.bytes_sent,
                description="发送的网络字节数"
            )
            self.set_gauge(
                "system_network_bytes_recv",
                net_io.bytes_recv,
                description="接收的网络字节数"
            )
            
            # 进程信息
            process = psutil.Process()
            self.set_gauge(
                "process_memory_rss",
                process.memory_info().rss,
                description="进程常驻内存大小（字节）"
            )
            self.set_gauge(
                "process_cpu_percent",
                process.cpu_percent(interval=None),
                description="进程CPU使用率百分比"
            )
            
            logger.debug("系统指标收集完成")
            
        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
    
    async def start_periodic_collection(self) -> None:
        """启动定期收集"""
        while True:
            try:
                self.collect_system_metrics()
                await asyncio.sleep(self.collection_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定期收集失败: {e}")
                await asyncio.sleep(self.collection_interval)
    
    def export_prometheus(self) -> str:
        """导出为Prometheus格式"""
        lines = []
        
        with self.lock:
            for name, metrics in self.metrics.items():
                if not metrics:
                    continue
                
                # 只导出最新的指标
                latest_metric = metrics[-1]
                
                # 添加帮助文本
                if latest_metric.description:
                    lines.append(f"# HELP {name} {latest_metric.description}")
                
                # 添加类型
                lines.append(f"# TYPE {name} {latest_metric.metric_type.value}")
                
                # 添加指标值
                lines.append(latest_metric.to_prometheus())
        
        return "\n".join(lines)
    
    def export_json(self) -> Dict[str, Any]:
        """导出为JSON格式"""
        with self.lock:
            export_data = {}
            
            for name, metrics in self.metrics.items():
                if metrics:
                    # 只导出最新的10个指标
                    latest_metrics = metrics[-10:]
                    export_data[name] = [m.to_dict() for m in latest_metrics]
            
            return {
                "timestamp": datetime.now().isoformat(),
                "metrics": export_data
            }
    
    def clear_old_metrics(self, older_than: timedelta) -> int:
        """清理旧指标"""
        cutoff_time = datetime.now() - older_than
        cleared_count = 0
        
        with self.lock:
            for name in list(self.metrics.keys()):
                original_count = len(self.metrics[name])
                self.metrics[name] = [
                    m for m in self.metrics[name]
                    if m.timestamp >= cutoff_time
                ]
                cleared_count += original_count - len(self.metrics[name])
                
                # 如果指标列表为空，删除键
                if not self.metrics[name]:
                    del self.metrics[name]
        
        logger.info(f"清理了 {cleared_count} 个旧指标")
        return cleared_count


class HealthMonitor:
    """健康监控器"""
    
    def __init__(self):
        self.health_checks: Dict[str, HealthCheck] = {}
        self.check_functions: Dict[str, Callable] = {}
        self.check_interval = 30  # 秒
        
        # 默认健康检查
        self._register_default_checks()
        
        logger.info("健康监控器初始化完成")
    
    def _register_default_checks(self) -> None:
        """注册默认健康检查"""
        # 系统健康检查
        self.register_check("system_memory", self._check_system_memory)
        self.register_check("system_disk", self._check_system_disk)
        self.register_check("process_alive", self._check_process_alive)
    
    def register_check(self, name: str, check_function: Callable) -> None:
        """注册健康检查"""
        self.check_functions[name] = check_function
        logger.debug(f"健康检查已注册: {name}")
    
    async def run_check(self, name: str) -> HealthCheck:
        """运行健康检查"""
        check_function = self.check_functions.get(name)
        
        if not check_function:
            return HealthCheck(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"未找到健康检查函数: {name}"
            )
        
        try:
            # 运行检查函数
            if asyncio.iscoroutinefunction(check_function):
                result = await check_function()
            else:
                result = check_function()
            
            # 处理结果
            if isinstance(result, tuple) and len(result) == 2:
                status, message = result
                details = {}
            elif isinstance(result, tuple) and len(result) == 3:
                status, message, details = result
            elif isinstance(result, HealthCheck):
                return result
            else:
                status = HealthStatus.UNKNOWN
                message = f"无效的检查结果格式: {type(result)}"
                details = {}
            
            # 创建健康检查结果
            health_check = HealthCheck(
                name=name,
                status=status,
                message=message,
                details=details
            )
            
            # 更新状态
            self.health_checks[name] = health_check
            
            return health_check
            
        except Exception as e:
            error_msg = f"健康检查执行失败: {str(e)}"
            logger.error(error_msg, exc_info=True)
            
            health_check = HealthCheck(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=error_msg,
                details={"error": str(e)}
            )
            
            self.health_checks[name] = health_check
            return health_check
    
    async def run_all_checks(self) -> Dict[str, HealthCheck]:
        """运行所有健康检查"""
        results = {}
        
        for name in self.check_functions:
            health_check = await self.run_check(name)
            results[name] = health_check
        
        return results
    
    def _check_system_memory(self) -> tuple:
        """检查系统内存"""
        try:
            memory = psutil.virtual_memory()
            
            if memory.percent > 90:
                return (
                    HealthStatus.UNHEALTHY,
                    f"内存使用率过高: {memory.percent}%",
                    {
                        "total": memory.total,
                        "available": memory.available,
                        "used": memory.used,
                        "percent": memory.percent
                    }
                )
            elif memory.percent > 80:
                return (
                    HealthStatus.DEGRADED,
                    f"内存使用率较高: {memory.percent}%",
                    {
                        "total": memory.total,
                        "available": memory.available,
                        "used": memory.used,
                        "percent": memory.percent
                    }
                )
            else:
                return (
                    HealthStatus.HEALTHY,
                    f"内存使用正常: {memory.percent}%",
                    {
                        "total": memory.total,
                        "available": memory.available,
                        "used": memory.used,
                        "percent": memory.percent
                    }
                )
        except Exception as e:
            return (
                HealthStatus.UNKNOWN,
                f"内存检查失败: {str(e)}",
                {"error": str(e)}
            )
    
    def _check_system_disk(self) -> tuple:
        """检查系统磁盘"""
        try:
            disk = psutil.disk_usage('/')
            
            if disk.percent > 95:
                return (
                    HealthStatus.UNHEALTHY,
                    f"磁盘使用率过高: {disk.percent}%",
                    {
                        "total": disk.total,
                        "free": disk.free,
                        "used": disk.used,
                        "percent": disk.percent
                    }
                )
            elif disk.percent > 90:
                return (
                    HealthStatus.DEGRADED,
                    f"磁盘使用率较高: {disk.percent}%",
                    {
                        "total": disk.total,
                        "free": disk.free,
                        "used": disk.used,
                        "percent": disk.percent
                    }
                )
            else:
                return (
                    HealthStatus.HEALTHY,
                    f"磁盘使用正常: {disk.percent}%",
                    {
                        "total": disk.total,
                        "free": disk.free,
                        "used": disk.used,
                        "percent": disk.percent
                    }
                )
        except Exception as e:
            return (
                HealthStatus.UNKNOWN,
                f"磁盘检查失败: {str(e)}",
                {"error": str(e)}
            )
    
    def _check_process_alive(self) -> tuple:
        """检查进程是否存活"""
        try:
            process = psutil.Process()
            
            if process.is_running():
                return (
                    HealthStatus.HEALTHY,
                    "进程运行正常",
                    {
                        "pid": process.pid,
                        "name": process.name(),
                        "status": process.status()
                    }
                )
            else:
                return (
                    HealthStatus.UNHEALTHY,
                    "进程未运行",
                    {"pid": process.pid}
                )
        except Exception as e:
            return (
                HealthStatus.UNHEALTHY,
                f"进程检查失败: {str(e)}",
                {"error": str(e)}
            )
    
    async def start_periodic_checks(self) -> None:
        """启动定期检查"""
        while True:
            try:
                await self.run_all_checks()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"定期健康检查失败: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_overall_status(self) -> HealthStatus:
        """获取整体状态"""
        if not self.health_checks:
            return HealthStatus.UNKNOWN
        
        statuses = [check.status for check in self.health_checks.values()]
        
        if HealthStatus.UNHEALTHY in statuses:
            return HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            return HealthStatus.DEGRADED
        elif all(s == HealthStatus.HEALTHY for s in statuses):
            return HealthStatus.HEALTHY
        else:
            return HealthStatus.UNKNOWN
    
    def get_health_report(self) -> Dict[str, Any]:
        """获取健康报告"""
        overall_status = self.get_overall_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": overall_status.value,
            "checks": {
                name: check.to_dict()
                for name, check in self.health_checks.items()
            }
        }


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str = "hermes"):
        self.logger = logging.getLogger(name)
        self.service_name = name
        
        # 配置结构化格式
        self._configure_structured_logging()
        
        logger.info(f"结构化日志记录器初始化完成: {name}")
    
    def _configure_structured_logging(self) -> None:
        """配置结构化日志"""
        # 如果已经有处理器，跳过
        if self.logger.handlers:
            return
        
        # 创建JSON格式化器
        class JsonFormatter(logging.Formatter):
            def format(self, record):
                log_record = {
                    "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "service": self.service_name
                }
                
                # 添加额外字段
                if hasattr(record, 'extra_fields'):
                    log_record.update(record.extra_fields)
                
                # 添加异常信息
                if record.exc_info:
                    log_record["exception"] = self.formatException(record.exc_info)
                
                return json.dumps(log_record)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(JsonFormatter())
        
        # 配置日志记录器
        self.logger.addHandler(console_handler)
        self.logger.setLevel(logging.INFO)
    
    def _log_with_fields(
        self,
        level: int,
        message: str,
        extra_fields: Dict[str, Any] = None,
        exc_info: bool = False
    ) -> None:
        """带字段的日志记录"""
        extra = extra_fields or {}
        
        # 创建日志记录
        record = self.logger.makeRecord(
            name=self.logger.name,
            level=level,
            fn=None,
            lno=0,
            msg=message,
            args=(),
            exc_info=exc_info,
            extra={'extra_fields': extra}
        )
        
        self.logger.handle(record)
    
    def info(self, message: str, **kwargs) -> None:
        """信息级别日志"""
        self._log_with_fields(logging.INFO, message, kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """警告级别日志"""
        self._log_with_fields(logging.WARNING, message, kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """错误级别日志"""
        self._log_with_fields(logging.ERROR, message, kwargs, exc_info=True)
    
    def debug(self, message: str, **kwargs) -> None:
        """调试级别日志"""
        self._log_with_fields(logging.DEBUG, message, kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """严重级别日志"""
        self._log_with_fields(logging.CRITICAL, message, kwargs, exc_info=True)
    
    def metric(self, name: str, value: float, **kwargs) -> None:
        """记录指标日志"""
        extra = kwargs.copy()
        extra.update({
            "metric_name": name,
            "metric_value": value,
            "log_type": "metric"
        })
        self.info(f"Metric: {name} = {value}", **extra)
    
    def event(self, event_type: str, **kwargs) -> None:
        """记录事件日志"""
        extra = kwargs.copy()
        extra.update({
            "event_type": event_type,
            "log_type": "event"
        })
        self.info(f"Event: {event_type}", **extra)


class MonitoringService:
    """监控服务"""
    
    def __init__(self):
        self.metrics_collector = MetricsCollector()
        self.health_monitor = HealthMonitor()
        self.logger = StructuredLogger("hermes_monitoring")
        
        # 监控任务
        self.monitoring_tasks = []
        self.is_running = False
        
        logger.info("监控服务初始化完成")
    
    async def start(self) -> None:
        """启动监控服务"""
        if self.is_running:
            logger.warning("监控服务已在运行")
            return
        
        self.is_running = True
        
        # 启动指标收集
        metrics_task = asyncio.create_task(
            self.metrics_collector.start_periodic_collection()
        )
        self.monitoring_tasks.append(metrics_task)
        
        # 启动健康检查
        health_task = asyncio.create_task(
            self.health_monitor.start_periodic_checks()
        )
        self.monitoring_tasks.append(health_task)
        
        self.logger.info("监控服务已启动")
    
    async def stop(self) -> None:
        """停止监控服务"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        # 取消所有任务
        for task in self.monitoring_tasks:
            task.cancel()
        
        # 等待任务完成
        if self.monitoring_tasks:
            await asyncio.gather(*self.monitoring_tasks, return_exceptions=True)
        
        self.monitoring_tasks.clear()
        self.logger.info("监控服务已停止")
    
    async def get_metrics(self, format: str = "json") -> Dict[str, Any]:
        """获取指标"""
        try:
            if format == "prometheus":
                prometheus_data = self.metrics_collector.export_prometheus()
                return {
                    "success": True,
                    "format": "prometheus",
                    "data": prometheus_data
                }
            else:
                json_data = self.metrics_collector.export_json()
                return {
                    "success": True,
                    "format": "json",
                    "data": json_data
                }
        except Exception as e:
            self.logger.error("获取指标失败", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_health(self) -> Dict[str, Any]:
        """获取健康状态"""
        try:
            health_report = self.health_monitor.get_health_report()
            return {
                "success": True,
                "health": health_report
            }
        except Exception as e:
            self.logger.error("获取健康状态失败", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def record_custom_metric(
        self,
        name: str,
        value: float,
        metric_type: str = "gauge",
        labels: Dict[str, str] = None,
        description: str = ""
    ) -> Dict[str, Any]:
        """记录自定义指标"""
        try:
            metric_type_enum = MetricType(metric_type)
            self.metrics_collector.record_metric(
                name=name,
                value=value,
                metric_type=metric_type_enum,
                labels=labels,
                description=description
            )
            
            self.logger.metric(name, value, labels=labels)
            
            return {
                "success": True,
                "metric": {
                    "name": name,
                    "value": value,
                    "type": metric_type
                }
            }
        except Exception as e:
            self.logger.error("记录自定义指标失败", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    async def run_health_check(self, check_name: str) -> Dict[str, Any]:
        """运行特定健康检查"""
        try:
            health_check = await self.health_monitor.run_check(check_name)
            
            return {
                "success": True,
                "health_check": health_check.to_dict()
            }
        except Exception as e:
            self.logger.error("运行健康检查失败", error=str(e))
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        return {
            "is_running": self.is_running,
            "active_tasks": len(self.monitoring_tasks),
            "metrics_count": len(self.metrics_collector.metrics),
            "health_checks_count": len(self.health_monitor.health_checks)
        }


# 全局监控服务实例
monitoring_service = MonitoringService()
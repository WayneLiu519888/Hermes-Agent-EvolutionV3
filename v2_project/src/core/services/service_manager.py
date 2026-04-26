"""
服务管理器 - 管理微服务的生命周期
支持服务注册、发现、健康检查、负载均衡
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
import time
import uuid
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    """服务状态"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"
    DEGRADED = "degraded"


class ServiceType(Enum):
    """服务类型"""
    CORE = "core"          # 核心服务
    LEARNING = "learning"  # 学习服务
    TOOL = "tool"          # 工具服务
    MONITORING = "monitoring"  # 监控服务
    STORAGE = "storage"    # 存储服务
    API = "api"            # API服务


@dataclass
class ServiceInfo:
    """服务信息"""
    service_id: str
    service_type: ServiceType
    name: str
    version: str = "1.0.0"
    description: str = ""
    endpoints: Dict[str, str] = field(default_factory=dict)  # API端点
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: ServiceStatus = ServiceStatus.STOPPED
    health_score: float = 100.0  # 健康分数 0-100
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "service_id": self.service_id,
            "service_type": self.service_type.value,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "endpoints": self.endpoints,
            "metadata": self.metadata,
            "status": self.status.value,
            "health_score": self.health_score,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }


class ServiceManager:
    """服务管理器"""
    
    def __init__(self, heartbeat_interval: int = 30, health_check_interval: int = 60):
        self.services: Dict[str, ServiceInfo] = {}
        self.heartbeat_interval = heartbeat_interval  # 心跳间隔(秒)
        self.health_check_interval = health_check_interval  # 健康检查间隔(秒)
        self._lock = asyncio.Lock()
        self._running = False
        self._health_check_task: Optional[asyncio.Task] = None
        
    async def start(self) -> None:
        """启动服务管理器"""
        if self._running:
            return
        
        self._running = True
        self._health_check_task = asyncio.create_task(self._health_check_loop())
        logger.info("服务管理器已启动")
    
    async def stop(self) -> None:
        """停止服务管理器"""
        self._running = False
        
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass
        
        # 停止所有服务
        async with self._lock:
            for service_id, service in self.services.items():
                if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
                    await self._stop_service(service_id)
        
        logger.info("服务管理器已停止")
    
    async def register_service(
        self,
        service_type: ServiceType,
        name: str,
        version: str = "1.0.0",
        description: str = "",
        endpoints: Optional[Dict[str, str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """注册服务"""
        service_id = f"{service_type.value}_{name}_{str(uuid.uuid4())[:8]}"
        
        service_info = ServiceInfo(
            service_id=service_id,
            service_type=service_type,
            name=name,
            version=version,
            description=description,
            endpoints=endpoints or {},
            metadata=metadata or {},
            status=ServiceStatus.STARTING
        )
        
        async with self._lock:
            self.services[service_id] = service_info
        
        logger.info(f"服务已注册: {name} ({service_id})")
        return service_id
    
    async def update_service_status(
        self,
        service_id: str,
        status: ServiceStatus,
        health_score: Optional[float] = None
    ) -> bool:
        """更新服务状态"""
        async with self._lock:
            if service_id not in self.services:
                logger.warning(f"服务不存在: {service_id}")
                return False
            
            service = self.services[service_id]
            service.status = status
            service.last_heartbeat = datetime.now()
            service.updated_at = datetime.now()
            
            if health_score is not None:
                service.health_score = max(0.0, min(100.0, health_score))
            
            logger.debug(f"服务状态更新: {service.name} -> {status.value}")
            return True
    
    async def heartbeat(self, service_id: str) -> bool:
        """服务心跳"""
        return await self.update_service_status(
            service_id,
            ServiceStatus.RUNNING,
            health_score=100.0
        )
    
    async def deregister_service(self, service_id: str) -> bool:
        """注销服务"""
        async with self._lock:
            if service_id not in self.services:
                return False
            
            service = self.services[service_id]
            await self._stop_service(service_id)
            del self.services[service_id]
            
            logger.info(f"服务已注销: {service.name} ({service_id})")
            return True
    
    async def get_service(self, service_id: str) -> Optional[ServiceInfo]:
        """获取服务信息"""
        async with self._lock:
            return self.services.get(service_id)
    
    async def list_services(
        self,
        service_type: Optional[ServiceType] = None,
        status: Optional[ServiceStatus] = None,
        min_health_score: float = 0.0
    ) -> List[ServiceInfo]:
        """列出服务"""
        async with self._lock:
            services = list(self.services.values())
            
            # 过滤
            if service_type:
                services = [s for s in services if s.service_type == service_type]
            if status:
                services = [s for s in services if s.status == status]
            if min_health_score > 0:
                services = [s for s in services if s.health_score >= min_health_score]
            
            return services
    
    async def discover_service(
        self,
        service_type: ServiceType,
        strategy: str = "healthiest"
    ) -> Optional[ServiceInfo]:
        """发现服务（负载均衡）"""
        services = await self.list_services(service_type=service_type)
        
        if not services:
            return None
        
        # 过滤运行中的服务
        running_services = [s for s in services if s.status == ServiceStatus.RUNNING]
        
        if not running_services:
            return None
        
        # 选择策略
        if strategy == "healthiest":
            # 选择最健康的服务
            return max(running_services, key=lambda s: s.health_score)
        elif strategy == "round_robin":
            # 轮询
            return running_services[0]  # 简化实现
        elif strategy == "random":
            # 随机
            import random
            return random.choice(running_services)
        else:
            # 默认选择第一个
            return running_services[0]
    
    async def _stop_service(self, service_id: str) -> None:
        """停止服务（内部方法）"""
        service = self.services.get(service_id)
        if not service:
            return
        
        if service.status in [ServiceStatus.RUNNING, ServiceStatus.STARTING]:
            service.status = ServiceStatus.STOPPING
            # 这里可以调用服务的停止方法
            service.status = ServiceStatus.STOPPED
            logger.info(f"服务已停止: {service.name}")
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self._running:
            try:
                await asyncio.sleep(self.health_check_interval)
                await self._perform_health_checks()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查失败: {e}", exc_info=True)
    
    async def _perform_health_checks(self) -> None:
        """执行健康检查"""
        async with self._lock:
            now = datetime.now()
            for service_id, service in self.services.items():
                # 检查心跳超时
                if service.last_heartbeat:
                    time_since_heartbeat = (now - service.last_heartbeat).total_seconds()
                    if time_since_heartbeat > self.heartbeat_interval * 3:  # 3倍心跳间隔
                        service.health_score = max(0.0, service.health_score - 20.0)
                        if service.health_score < 50.0:
                            service.status = ServiceStatus.DEGRADED
                        logger.warning(f"服务心跳超时: {service.name}")
                
                # 更新服务状态
                service.updated_at = now


# 全局服务管理器实例
service_manager = ServiceManager()
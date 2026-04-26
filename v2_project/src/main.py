"""
HermesAgentEvolution V2 - 主应用程序
事件驱动微服务架构的入口点
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any, Optional
from pathlib import Path

# 导入核心组件
from src.core.events.event_bus import event_bus, Event, EventType, EventPriority
from src.core.services.service_manager import service_manager, ServiceType, ServiceStatus
from src.core.config.config_manager import config_manager

logger = logging.getLogger(__name__)


class HermesAgentEvolutionV2:
    """HermesAgentEvolution V2 主应用程序"""
    
    def __init__(self):
        self.running = False
        self.startup_time = None
        self.services = {}
        
        # 设置日志
        self._setup_logging()
        
    def _setup_logging(self) -> None:
        """设置日志"""
        log_level = config_manager.get("logging.level", "INFO")
        log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        
        logging.basicConfig(
            level=getattr(logging, log_level),
            format=log_format,
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler("logs/hermes_v2.log")
            ]
        )
        
        # 创建日志目录
        Path("logs").mkdir(exist_ok=True)
        
        logger.info(f"日志系统已初始化，级别: {log_level}")
    
    async def startup(self) -> None:
        """启动应用程序"""
        if self.running:
            logger.warning("应用程序已在运行中")
            return
        
        logger.info("🚀 HermesAgentEvolution V2 正在启动...")
        self.startup_time = asyncio.get_event_loop().time()
        self.running = True
        
        try:
            # 1. 发布系统启动事件
            await event_bus.publish(Event(
                event_type=EventType.SYSTEM_STARTUP,
                data={"version": "2.0.0", "timestamp": self.startup_time},
                priority=EventPriority.HIGH
            ))
            
            # 2. 启动服务管理器
            await service_manager.start()
            logger.info("服务管理器已启动")
            
            # 3. 注册核心服务
            await self._register_core_services()
            
            # 4. 启动事件监听器
            await self._start_event_listeners()
            
            # 5. 启动健康检查
            asyncio.create_task(self._health_check_loop())
            
            logger.info("✅ HermesAgentEvolution V2 启动完成")
            
            # 发布启动完成事件
            await event_bus.publish(Event(
                event_type=EventType.SYSTEM_STARTUP,
                data={"status": "completed", "services": len(self.services)},
                priority=EventPriority.NORMAL
            ))
            
        except Exception as e:
            logger.error(f"应用程序启动失败: {e}", exc_info=True)
            await self.shutdown()
            raise
    
    async def _register_core_services(self) -> None:
        """注册核心服务"""
        core_services = [
            {
                "type": ServiceType.CORE,
                "name": "EventBus",
                "description": "事件总线服务",
                "endpoints": {"status": "/api/events/status"}
            },
            {
                "type": ServiceType.CORE,
                "name": "ServiceManager",
                "description": "服务管理器",
                "endpoints": {"discover": "/api/services/discover"}
            },
            {
                "type": ServiceType.CORE,
                "name": "ConfigManager",
                "description": "配置管理器",
                "endpoints": {"config": "/api/config"}
            },
            {
                "type": ServiceType.LEARNING,
                "name": "LearningOrchestrator",
                "description": "学习协调器",
                "endpoints": {"learn": "/api/learning/start"}
            },
            {
                "type": ServiceType.TOOL,
                "name": "ToolManager",
                "description": "工具管理器",
                "endpoints": {"tools": "/api/tools"}
            },
            {
                "type": ServiceType.MONITORING,
                "name": "MonitoringService",
                "description": "监控服务",
                "endpoints": {"metrics": "/api/metrics"}
            }
        ]
        
        for service_info in core_services:
            service_id = await service_manager.register_service(
                service_type=service_info["type"],
                name=service_info["name"],
                description=service_info["description"],
                endpoints=service_info.get("endpoints", {})
            )
            
            # 更新服务状态为运行中
            await service_manager.update_service_status(
                service_id,
                ServiceStatus.RUNNING,
                health_score=100.0
            )
            
            self.services[service_id] = service_info["name"]
            
            logger.info(f"核心服务已注册: {service_info['name']}")
    
    async def _start_event_listeners(self) -> None:
        """启动事件监听器"""
        
        # 系统事件监听器
        async def handle_system_events(event: Event) -> None:
            if event.event_type == EventType.SYSTEM_ERROR:
                logger.error(f"系统错误: {event.data}")
            elif event.event_type == EventType.ALERT_TRIGGERED:
                logger.warning(f"系统告警: {event.data}")
        
        event_bus.subscribe(EventType.SYSTEM_ERROR, handle_system_events)
        event_bus.subscribe(EventType.ALERT_TRIGGERED, handle_system_events)
        
        # 学习事件监听器
        async def handle_learning_events(event: Event) -> None:
            if event.event_type == EventType.LEARNING_STARTED:
                logger.info(f"学习任务开始: {event.data.get('task_id')}")
            elif event.event_type == EventType.LEARNING_COMPLETED:
                logger.info(f"学习任务完成: {event.data.get('task_id')}")
            elif event.event_type == EventType.LEARNING_FAILED:
                logger.error(f"学习任务失败: {event.data.get('task_id')}")
        
        event_bus.subscribe(EventType.LEARNING_STARTED, handle_learning_events)
        event_bus.subscribe(EventType.LEARNING_COMPLETED, handle_learning_events)
        event_bus.subscribe(EventType.LEARNING_FAILED, handle_learning_events)
        
        # 工具事件监听器
        async def handle_tool_events(event: Event) -> None:
            if event.event_type == EventType.TOOL_EXECUTED:
                logger.debug(f"工具执行: {event.data.get('tool_name')}")
            elif event.event_type == EventType.TOOL_FAILED:
                logger.warning(f"工具执行失败: {event.data.get('tool_name')}")
            elif event.event_type == EventType.TOOL_DISCOVERED:
                logger.info(f"新工具发现: {event.data.get('tool_name')}")
        
        event_bus.subscribe(EventType.TOOL_EXECUTED, handle_tool_events)
        event_bus.subscribe(EventType.TOOL_FAILED, handle_tool_events)
        event_bus.subscribe(EventType.TOOL_DISCOVERED, handle_tool_events)
        
        logger.info("事件监听器已启动")
    
    async def _health_check_loop(self) -> None:
        """健康检查循环"""
        while self.running:
            try:
                await asyncio.sleep(60)  # 每分钟检查一次
                
                # 检查服务健康状态
                services = await service_manager.list_services()
                unhealthy_services = [
                    s for s in services 
                    if s.health_score < 70.0 or s.status == ServiceStatus.FAILED
                ]
                
                if unhealthy_services:
                    await event_bus.publish(Event(
                        event_type=EventType.ALERT_TRIGGERED,
                        data={
                            "type": "service_health",
                            "unhealthy_services": [
                                {"name": s.name, "health": s.health_score, "status": s.status.value}
                                for s in unhealthy_services
                            ]
                        },
                        priority=EventPriority.HIGH
                    ))
                
                # 发送心跳
                for service_id in self.services.keys():
                    await service_manager.heartbeat(service_id)
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
    
    async def shutdown(self, signal: Optional[signal.Signals] = None) -> None:
        """关闭应用程序"""
        if not self.running:
            return
        
        logger.info("🛑 HermesAgentEvolution V2 正在关闭...")
        self.running = False
        
        try:
            # 发布系统关闭事件
            await event_bus.publish(Event(
                event_type=EventType.SYSTEM_SHUTDOWN,
                data={"signal": signal.name if signal else "manual"},
                priority=EventPriority.HIGH
            ))
            
            # 停止服务管理器
            await service_manager.stop()
            
            # 注销所有服务
            for service_id in list(self.services.keys()):
                await service_manager.deregister_service(service_id)
            
            logger.info("✅ HermesAgentEvolution V2 已关闭")
            
        except Exception as e:
            logger.error(f"应用程序关闭失败: {e}", exc_info=True)
    
    async def run(self) -> None:
        """运行应用程序主循环"""
        # 设置信号处理
        loop = asyncio.get_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda s=sig: asyncio.create_task(self.shutdown(s))
            )
        
        try:
            await self.startup()
            
            # 保持运行
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("收到键盘中断信号")
        except Exception as e:
            logger.error(f"应用程序运行异常: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    def get_status(self) -> Dict[str, Any]:
        """获取应用程序状态"""
        return {
            "running": self.running,
            "startup_time": self.startup_time,
            "services_count": len(self.services),
            "config_hash": config_manager.get_config_hash(),
            "event_bus_stats": event_bus.get_subscriber_count()
        }


async def main():
    """主函数"""
    app = HermesAgentEvolutionV2()
    
    try:
        await app.run()
    except Exception as e:
        logger.error(f"应用程序异常退出: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    # 创建必要的目录
    Path("logs").mkdir(exist_ok=True)
    Path("data").mkdir(exist_ok=True)
    
    # 运行应用程序
    asyncio.run(main())
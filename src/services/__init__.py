"""
HermesAgentEvolution V2 微服务层

事件驱动微服务架构：
  - core/: 核心基础设施（事件总线、服务管理器、配置管理）
  - learning/: 学习服务（元学习、反思、强化学习）
  - tools/: 工具服务（工具发现、工具组合）
  - system/: 系统服务（部署、监控、测试）

用法：
    from services.core.events import event_bus
    from services.core.services import service_manager
"""

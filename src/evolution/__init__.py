"""
Hermes Agent Evolution - AI助手自我进化系统 V1/V2/V3 融合版

架构：
  - src/evolution/ — V1 单体模块 (记忆/学习/工具/安全/协作/闭环进化)
  - src/services/   — V2 微服务层 (事件总线/服务管理/学习服务/工具服务)
  - src/utils/      — 共享工具 (飞书通知/进度报告)
  
使AI助手能够从经验中学习并持续改进自身能力。
"""

__version__ = "8.0.8"
__author__ = "HermesAgentEvolution Team"
__description__ = "AI助手自我进化系统 - V1/V2/V3融合版"

# Re-export key classes that plugins import directly from the evolution package
from .self_monitor import SelfMonitor

"""
V1/V2 融合模块 - HermesAgentEvolution 架构桥接层

核心思路：V1 是单体模块化架构（src/evolution/），V2 是微服务架构（v2_project/src/）。
融合层让两者无缝协作，支持三种运行模式：
  - V1_ONLY: 仅使用V1单体模块
  - V2_ONLY: 仅使用V2微服务
  - HYBRID:  融合模式，V1和V2协同工作
"""

from .bridge import (
    V1V2Bridge,
    ServiceMapping,
    V1_STATUS_ENUM,
    V2_SERVICE_TYPE,
    SERVICE_MAP_V1_TO_V2,
    SERVICE_MAP_V2_TO_V1,
)

from .unified_entry import (
    UnifiedAgent,
    RunMode,
    CapabilityRequest,
    CapabilityResponse,
    UnifiedStatusReport,
)

from .compatibility import (
    CompatibilityLayer,
    StatusMapper,
    EnumMapper,
    APIGateway,
    DegradationHandler,
    VersionDetector,
    v1_status_to_v2_status,
    v2_status_to_v1_status,
    v1_outcome_to_v2_priority,
    v2_priority_to_v1_confidence,
)

__all__ = [
    # bridge.py
    'V1V2Bridge',
    'ServiceMapping',
    'V1_STATUS_ENUM',
    'V2_SERVICE_TYPE',
    'SERVICE_MAP_V1_TO_V2',
    'SERVICE_MAP_V2_TO_V1',

    # unified_entry.py
    'UnifiedAgent',
    'RunMode',
    'CapabilityRequest',
    'CapabilityResponse',
    'UnifiedStatusReport',

    # compatibility.py
    'CompatibilityLayer',
    'StatusMapper',
    'EnumMapper',
    'APIGateway',
    'DegradationHandler',
    'VersionDetector',
    'v1_status_to_v2_status',
    'v2_status_to_v1_status',
    'v1_outcome_to_v2_priority',
    'v2_priority_to_v1_confidence',
]

__version__ = "1.0.0"
__author__ = "HermesAgentEvolution Team"

"""
经验数据类，用于记录学习过程中的各种经验
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json


class ExperienceType(Enum):
    """经验类型枚举"""
    TOOL_USAGE = "tool_usage"  # 工具使用经验
    REASONING = "reasoning"    # 推理过程经验
    PROBLEM_SOLVING = "problem_solving"  # 问题解决经验
    ERROR_RECOVERY = "error_recovery"    # 错误恢复经验
    PATTERN_RECOGNITION = "pattern_recognition"  # 模式识别经验
    ADAPTATION = "adaptation"  # 适应调整经验


class Outcome(Enum):
    """结果状态枚举"""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    UNCERTAIN = "uncertain"


@dataclass
class Experience:
    """经验数据类"""
    
    # 基础信息
    id: str
    experience_type: ExperienceType
    task_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    
    # 内容信息
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    actions: List[Dict[str, Any]] = field(default_factory=list)
    reasoning_steps: List[str] = field(default_factory=list)
    
    # 结果信息
    outcome: Outcome = Outcome.UNCERTAIN
    result: Optional[Any] = None
    metrics: Dict[str, float] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    
    # 元数据
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    importance: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "experience_type": self.experience_type.value,
            "task_id": self.task_id,
            "timestamp": self.timestamp.isoformat(),
            "description": self.description,
            "context": self.context,
            "actions": self.actions,
            "reasoning_steps": self.reasoning_steps,
            "outcome": self.outcome.value,
            "result": self.result,
            "metrics": self.metrics,
            "lessons_learned": self.lessons_learned,
            "tags": self.tags,
            "confidence": self.confidence,
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Experience':
        """从字典创建实例"""
        # 处理枚举类型
        data = data.copy()
        data["experience_type"] = ExperienceType(data["experience_type"])
        data["outcome"] = Outcome(data["outcome"])
        
        # 处理时间戳
        if isinstance(data["timestamp"], str):
            data["timestamp"] = datetime.fromisoformat(data["timestamp"])
        
        return cls(**data)
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> 'Experience':
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_action(self, tool_name: str, parameters: Dict[str, Any], 
                   result: Any, duration: float = 0.0):
        """添加工具使用动作"""
        self.actions.append({
            "tool_name": tool_name,
            "parameters": parameters,
            "result": result,
            "duration": duration,
            "timestamp": datetime.now().isoformat()
        })
    
    def add_reasoning_step(self, step: str):
        """添加推理步骤"""
        self.reasoning_steps.append(step)
    
    def add_lesson_learned(self, lesson: str):
        """添加学到的经验教训"""
        self.lessons_learned.append(lesson)
    
    def add_metric(self, name: str, value: float):
        """添加指标"""
        self.metrics[name] = value
    
    def add_tag(self, tag: str):
        """添加标签"""
        if tag not in self.tags:
            self.tags.append(tag)
    
    def calculate_confidence(self) -> float:
        """计算置信度"""
        # 基于结果、指标和重要性计算置信度
        base_confidence = 0.5
        
        # 结果影响
        if self.outcome == Outcome.SUCCESS:
            base_confidence += 0.3
        elif self.outcome == Outcome.PARTIAL_SUCCESS:
            base_confidence += 0.1
        elif self.outcome == Outcome.FAILURE:
            base_confidence -= 0.2
        
        # 指标影响（如果有成功指标）
        if "success_rate" in self.metrics:
            base_confidence += self.metrics["success_rate"] * 0.2
        
        # 重要性影响
        base_confidence += self.importance * 0.1
        
        # 确保在0-1范围内
        return max(0.0, min(1.0, base_confidence))
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Experience(id={self.id}, type={self.experience_type.value}, " \
               f"task={self.task_id}, outcome={self.outcome.value})"
"""
ActionExecutor — 改进动作执行器
负责将改进计划中的动作实际执行，产生真实效果

支持的动作类型:
- strategy_switch: 切换工具选择策略
- tool_optimization: 优化工具参数/性能
- parameter_tuning: 调整系统参数
- tool_creation: 创建新工具
- tool_deprecation: 废弃低效工具
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    改进动作执行器
    
    接收改进动作定义，执行实际系统变更。
    每个动作类型有对应的执行器方法。
    
    用法:
        executor = ActionExecutor(strategy_learner, tool_engine, registry)
        result = executor.execute(action)
    """
    
    def __init__(self,
                 strategy_learner=None,
                 tool_evolution_engine=None,
                 tool_registry=None,
                 tool_performance_analyzer=None,
                 pattern_recognizer=None,
                 config: Optional[Dict[str, Any]] = None):
        """
        Args:
            strategy_learner: 工具策略学习器
            tool_evolution_engine: 工具进化引擎
            tool_registry: 工具注册表
            tool_performance_analyzer: 工具性能分析器
            pattern_recognizer: 模式识别器
            config: 配置
        """
        self.strategy_learner = strategy_learner
        self.tool_evolution_engine = tool_evolution_engine
        self.tool_registry = tool_registry
        self.tool_performance_analyzer = tool_performance_analyzer
        self.pattern_recognizer = pattern_recognizer
        self.config = config or {}
        
        # 执行历史
        self.execution_history: List[Dict[str, Any]] = []
        
        # 安全模式 — dry_run 时不执行实际变更
        self.dry_run = self.config.get('dry_run', False)
        
        logger.info(f"ActionExecutor 初始化 (dry_run={self.dry_run})")
    
    def execute(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """
        执行单个改进动作
        
        Args:
            action: 改进动作
            
        Returns:
            {'success': bool, 'message': str, 'output': dict}
        """
        logger.info(f"执行动作: {action.action_type} → {action.target} [{action.priority}]")
        
        handlers = {
            'strategy_switch': self._execute_strategy_switch,
            'tool_optimization': self._execute_tool_optimization,
            'parameter_tuning': self._execute_parameter_tuning,
            'tool_creation': self._execute_tool_creation,
            'tool_deprecation': self._execute_tool_deprecation,
        }
        
        handler = handlers.get(action.action_type)
        if not handler:
            return {
                'success': False,
                'message': f"未知动作类型: {action.action_type}",
                'output': {},
            }
        
        try:
            if self.dry_run:
                result = self._simulate_action(action)
            else:
                result = handler(action)
            
            # 记录历史
            self.execution_history.append({
                'timestamp': datetime.now().isoformat(),
                'action': {
                    'type': action.action_type,
                    'target': action.target,
                    'priority': action.priority,
                },
                'result': result,
            })
            
            return result
            
        except Exception as e:
            logger.error(f"执行动作失败 [{action.action_type}→{action.target}]: {e}")
            return {
                'success': False,
                'message': str(e),
                'output': {},
            }
    
    # ═══════════════════════════════════════════
    # 动作执行器
    # ═══════════════════════════════════════════
    
    def _execute_strategy_switch(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """
        切换工具选择策略
        
        当检测到当前策略表现不佳时，切换到更优策略
        """
        if not self.strategy_learner:
            return {'success': False, 'message': '策略学习器未初始化', 'output': {}}
        
        try:
            current = self.strategy_learner.get_current_strategy()
            
            # 策略学习器在 record_tool_usage 内部已有 _consider_strategy_update，
            # 不需要外部伪造数据触发
            
            new_strategy = self.strategy_learner.get_current_strategy()
            changed = new_strategy != current
            
            return {
                'success': True,
                'message': (
                    f"策略评估完成: {current.value} → {new_strategy.value}"
                    if changed else
                    f"策略保持 {current.value}（无需切换）"
                ),
                'output': {
                    'previous_strategy': current.value,
                    'new_strategy': new_strategy.value,
                    'changed': changed,
                },
            }
        except Exception as e:
            return {'success': False, 'message': f"策略切换失败: {e}", 'output': {}}
    
    def _execute_tool_optimization(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """
        优化工具性能
        
        通过工具进化引擎优化指定工具
        """
        if not self.tool_evolution_engine:
            return {'success': False, 'message': '工具进化引擎未初始化', 'output': {}}
        
        try:
            tool_name = action.parameters.get('tool_name', action.target)
            
            # 运行工具进化周期
            result = self.tool_evolution_engine.run_evolution_cycle()
            
            # 检查是否对目标工具有改进
            tool_optimized = any(
                opt.get('tool_name') == tool_name
                for opt in result.get('optimizations', [])
            )
            
            return {
                'success': result.get('success', False),
                'message': (
                    f"工具 '{tool_name}' 进化完成"
                    if tool_optimized else
                    f"工具 '{tool_name}' 当前不需要优化"
                ),
                'output': {
                    'tool_name': tool_name,
                    'evolution_success': result.get('success', False),
                    'optimizations_count': len(result.get('optimizations', [])),
                    'deprecated_count': len(result.get('deprecated_tools', [])),
                },
            }
        except Exception as e:
            return {'success': False, 'message': f"工具优化失败: {e}", 'output': {}}
    
    def _execute_parameter_tuning(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """
        调整系统参数
        
        根据分析结果调整系统运行参数
        """
        params = action.parameters
        changes = []
        
        # 调整探索率（如果策略学习器支持）
        if self.strategy_learner and 'exploration_rate' in params:
            try:
                new_rate = params['exploration_rate']
                if hasattr(self.strategy_learner, 'set_exploration_rate'):
                    self.strategy_learner.set_exploration_rate(new_rate)
                    changes.append(f"探索率 → {new_rate}")
            except Exception as e:
                logger.debug(f"调整探索率失败: {e}")
        
        # 调整性能阈值
        if self.tool_evolution_engine and 'min_performance_score' in params:
            try:
                new_threshold = params['min_performance_score']
                if hasattr(self.tool_evolution_engine, 'config'):
                    old = self.tool_evolution_engine.config.min_performance_score
                    self.tool_evolution_engine.config.min_performance_score = new_threshold
                    changes.append(f"性能阈值 {old} → {new_threshold}")
            except Exception as e:
                logger.debug(f"调整性能阈值失败: {e}")
        
        if changes:
            return {
                'success': True,
                'message': f"参数已调整: {', '.join(changes)}",
                'output': {'changes': changes},
            }
        else:
            return {
                'success': True,
                'message': '无可调参数（参数调优暂未实现）',
                'output': {'changes': []},
            }
    
    def _execute_tool_creation(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """
        创建新工具
        
        根据需求描述自动生成新工具
        """
        if not self.tool_evolution_engine:
            return {'success': False, 'message': '工具进化引擎未初始化', 'output': {}}
        
        try:
            requirement = action.description
            
            result = self.tool_evolution_engine.auto_generate_tool(requirement)
            
            return {
                'success': result.success if hasattr(result, 'success') else False,
                'message': f"工具生成: {getattr(result, 'tool_name', 'unknown')}",
                'output': {
                    'tool_name': getattr(result, 'tool_name', ''),
                    'success': getattr(result, 'success', False),
                },
            }
        except Exception as e:
            return {'success': False, 'message': f"工具创建失败: {e}", 'output': {}}
    
    def _execute_tool_deprecation(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """
        废弃低效工具
        
        将使用率低、性能差的工具标记为废弃
        """
        if not self.tool_registry:
            return {'success': False, 'message': '工具注册表未初始化', 'output': {}}
        
        try:
            tool_name = action.parameters.get('tool_name', action.target)
            
            tool = self.tool_registry.get(tool_name)
            if not tool:
                return {'success': False, 'message': f"工具 '{tool_name}' 不存在", 'output': {}}
            
            # 标记为废弃
            from ..tools.tool_registry import ToolStatus
            tool.status = ToolStatus.DEPRECATED
            self.tool_registry.register(tool)
            
            return {
                'success': True,
                'message': f"工具 '{tool_name}' 已标记为废弃",
                'output': {'tool_name': tool_name},
            }
        except Exception as e:
            return {'success': False, 'message': f"工具废弃失败: {e}", 'output': {}}
    
    # ═══════════════════════════════════════════
    # Dry Run 模式
    # ═══════════════════════════════════════════
    
    def _simulate_action(self, action: 'ImprovementAction') -> Dict[str, Any]:
        """模拟执行（不对系统做任何实际变更）"""
        return {
            'success': True,
            'message': f"[DRY-RUN] 将执行: {action.action_type} → {action.target}",
            'output': {
                'simulated': True,
                'action_type': action.action_type,
                'target': action.target,
                'priority': action.priority,
                'expected_benefit': action.expected_benefit,
                'risk': action.risk,
            },
        }
    
    # ═══════════════════════════════════════════
    # 便捷方法
    # ═══════════════════════════════════════════
    
    def execute_batch(self, actions: List['ImprovementAction']) -> List[Dict[str, Any]]:
        """
        批量执行动作
        
        Args:
            actions: 动作列表
            
        Returns:
            执行结果列表
        """
        results = []
        for action in actions:
            result = self.execute(action)
            results.append(result)
        return results
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        total = len(self.execution_history)
        if total == 0:
            return {'total': 0}
        
        success_count = sum(
            1 for r in self.execution_history
            if r.get('result', {}).get('success', False)
        )
        
        return {
            'total_executions': total,
            'success_count': success_count,
            'failure_count': total - success_count,
            'success_rate': f"{success_count/total:.1%}",
            'last_execution': self.execution_history[-1]['timestamp'] if self.execution_history else None,
        }

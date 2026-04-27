"""
EvolutionDaemon — 持续进化守护进程
核心闭环引擎：Monitor → Analyze → Plan → Execute → Verify → Feedback

这是 HermesAgentEvolution 持续进化机制的心脏。
负责以守护进程方式运行进化循环，协调所有子系统。
"""

import os
import sys
import json
import time
import signal
import logging
import threading
from enum import Enum
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class EvolutionPhase(Enum):
    """进化闭环的 6 个阶段"""
    MONITOR = "monitor"       # 采集指标
    ANALYZE = "analyze"       # 分析数据
    PLAN = "plan"             # 生成计划
    EXECUTE = "execute"       # 执行变更
    VERIFY = "verify"         # 验证效果
    FEEDBACK = "feedback"     # 反馈学习
    IDLE = "idle"             # 空闲


class LoopState(Enum):
    """循环状态"""
    RUNNING = "running"
    PAUSED = "paused"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class EvolutionSnapshot:
    """进化快照 — 单次循环的完整记录"""
    cycle_id: int
    timestamp: str
    phases_completed: List[str]
    metrics_before: Dict[str, Any]
    metrics_after: Optional[Dict[str, Any]] = None
    actions_taken: List[Dict[str, Any]] = field(default_factory=list)
    improvements_detected: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    success: bool = True


class EvolutionDaemon:
    """
    持续进化守护进程
    
    以独立线程运行，周期性执行进化闭环，持续优化系统。
    
    用法:
        daemon = EvolutionDaemon(orchestrator, config)
        daemon.start()
        # ... 系统运行中，进化自动进行 ...
        daemon.stop()
    """
    
    def __init__(self, 
                 orchestrator: 'ClosedLoopOrchestrator',
                 config: Optional[Dict[str, Any]] = None):
        """
        Args:
            orchestrator: 闭环编排器
            config: 配置字典
        """
        self.orchestrator = orchestrator
        self.config = config or {}
        
        # 循环控制
        self._state = LoopState.STOPPED
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        
        # 循环参数
        self.cycle_interval = self.config.get('cycle_interval', 300)  # 默认 5 分钟
        self.adaptive_interval = self.config.get('adaptive_interval', False)
        self.min_interval = self.config.get('min_interval', 60)
        self.max_interval = self.config.get('max_interval', 3600)
        
        # 历史记录
        self.snapshots: List[EvolutionSnapshot] = []
        self.cycle_count = 0
        self.consecutive_failures = 0
        self.max_consecutive_failures = self.config.get('max_consecutive_failures', 5)
        
        # 回调
        self._on_cycle_complete: List[Callable] = []
        self._on_improvement: List[Callable] = []
        self._on_error: List[Callable] = []
        
        # 持久化
        self.state_path = Path(self.config.get('state_path', 'data/evolution/daemon_state.json'))
        
        logger.info(f"EvolutionDaemon 初始化: interval={self.cycle_interval}s, adaptive={self.adaptive_interval}")
    
    # ━━━━ 生命周期管理 ━━━━
    
    def start(self) -> bool:
        """启动守护进程"""
        with self._lock:
            if self._state == LoopState.RUNNING:
                logger.warning("EvolutionDaemon 已在运行中")
                return False
            
            self._state = LoopState.RUNNING
            self._stop_event.clear()
            
            self._thread = threading.Thread(
                target=self._run_loop,
                name="EvolutionDaemon",
                daemon=True
            )
            self._thread.start()
            
            logger.info("🚀 EvolutionDaemon 启动成功")
            return True
    
    def stop(self, timeout: float = 30.0) -> bool:
        """停止守护进程（优雅关闭）"""
        with self._lock:
            if self._state != LoopState.RUNNING:
                logger.warning("EvolutionDaemon 未在运行")
                return True
            
            self._state = LoopState.STOPPING
        
        self._stop_event.set()
        
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=timeout)
            
            if self._thread.is_alive():
                logger.error(f"EvolutionDaemon 停止超时 ({timeout}s)")
                self._state = LoopState.ERROR
                return False
        
        self._state = LoopState.STOPPED
        logger.info("🛑 EvolutionDaemon 已停止")
        return True
    
    def pause(self) -> bool:
        """暂停进化循环"""
        with self._lock:
            if self._state != LoopState.RUNNING:
                return False
            self._state = LoopState.PAUSED
            logger.info("⏸️ EvolutionDaemon 已暂停")
            return True
    
    def resume(self) -> bool:
        """恢复进化循环"""
        with self._lock:
            if self._state != LoopState.PAUSED:
                return False
            self._state = LoopState.RUNNING
            logger.info("▶️ EvolutionDaemon 已恢复")
            return True
    
    @property
    def state(self) -> LoopState:
        return self._state
    
    @property
    def is_running(self) -> bool:
        return self._state == LoopState.RUNNING
    
    # ━━━━ 核心循环 ━━━━
    
    def _run_loop(self) -> None:
        """主循环 — 在独立线程中运行"""
        logger.info("EvolutionDaemon 主循环开始")
        
        # 注册信号处理（仅主线程需要，daemon线程用stop_event）
        while not self._stop_event.is_set():
            try:
                # 检查是否暂停
                if self._state == LoopState.PAUSED:
                    time.sleep(1)
                    continue
                
                # 执行单次进化循环
                self._execute_single_cycle()
                
                # 自适应间隔调整
                interval = self._calculate_next_interval()
                
                # 等待下次循环（可中断）
                self._stop_event.wait(timeout=interval)
                
            except Exception as e:
                logger.error(f"进化循环异常: {e}", exc_info=True)
                self.consecutive_failures += 1
                
                if self.consecutive_failures >= self.max_consecutive_failures:
                    logger.critical(f"连续失败 {self.consecutive_failures} 次，停止进化循环")
                    self._state = LoopState.ERROR
                    self._notify_error(e)
                    break
                
                # 失败后增加等待时间
                self._stop_event.wait(timeout=min(60, interval * 2))
        
        logger.info("EvolutionDaemon 主循环退出")
    
    def _execute_single_cycle(self) -> EvolutionSnapshot:
        """
        执行一次完整的进化闭环
        
        Returns:
            EvolutionSnapshot: 本次循环快照
        """
        cycle_start = time.time()
        self.cycle_count += 1
        cycle_id = self.cycle_count
        
        snapshot = EvolutionSnapshot(
            cycle_id=cycle_id,
            timestamp=datetime.now().isoformat(),
            phases_completed=[],
            metrics_before={},
        )
        
        logger.info(f"\n{'='*60}")
        logger.info(f"🔄 进化循环 #{cycle_id} 开始")
        logger.info(f"{'='*60}")
        
        try:
            # ━━━ Phase 1: Monitor ━━━
            logger.info(f"[#{cycle_id}] Phase 1/6: MONITOR — 采集系统指标")
            metrics = self.orchestrator.monitor()
            snapshot.metrics_before = metrics
            snapshot.phases_completed.append(EvolutionPhase.MONITOR.value)
            logger.info(f"[#{cycle_id}]   采集到 {len(metrics)} 个指标")
            
            # ━━━ Phase 2: Analyze ━━━
            logger.info(f"[#{cycle_id}] Phase 2/6: ANALYZE — 分析数据模式")
            analysis = self.orchestrator.analyze(metrics)
            snapshot.phases_completed.append(EvolutionPhase.ANALYZE.value)
            logger.info(f"[#{cycle_id}]   发现 {len(analysis.get('patterns', []))} 个模式, "
                       f"{len(analysis.get('issues', []))} 个问题")
            
            # ━━━ Phase 3: Plan ━━━
            logger.info(f"[#{cycle_id}] Phase 3/6: PLAN — 生成改进计划")
            plan = self.orchestrator.plan(analysis)
            snapshot.phases_completed.append(EvolutionPhase.PLAN.value)
            logger.info(f"[#{cycle_id}]   生成 {len(plan.get('actions', []))} 个改进动作")
            
            # ━━━ Phase 4: Execute ━━━
            logger.info(f"[#{cycle_id}] Phase 4/6: EXECUTE — 执行改进动作")
            results = self.orchestrator.execute(plan)
            snapshot.actions_taken = results.get('actions', [])
            snapshot.phases_completed.append(EvolutionPhase.EXECUTE.value)
            logger.info(f"[#{cycle_id}]   执行了 {len(snapshot.actions_taken)} 个动作, "
                       f"成功 {results.get('success_count', 0)}, "
                       f"失败 {results.get('failure_count', 0)}")
            
            # ━━━ Phase 5: Verify ━━━
            logger.info(f"[#{cycle_id}] Phase 5/6: VERIFY — 验证改进效果")
            verification = self.orchestrator.verify(snapshot.metrics_before, snapshot.actions_taken)
            snapshot.metrics_after = verification.get('metrics_after', {})
            snapshot.improvements_detected = verification.get('improvements', [])
            snapshot.phases_completed.append(EvolutionPhase.VERIFY.value)
            logger.info(f"[#{cycle_id}]   检测到 {len(snapshot.improvements_detected)} 项改进")
            
            # ━━━ Phase 6: Feedback ━━━
            logger.info(f"[#{cycle_id}] Phase 6/6: FEEDBACK — 记录学习经验")
            feedback = self.orchestrator.feedback(snapshot)
            snapshot.phases_completed.append(EvolutionPhase.FEEDBACK.value)
            
            # 记录成功
            snapshot.success = True
            self.consecutive_failures = 0
            
            duration = time.time() - cycle_start
            snapshot.duration_seconds = round(duration, 2)
            
            # 保存快照
            self.snapshots.append(snapshot)
            self._save_state()
            
            logger.info(f"[#{cycle_id}] ✅ 进化循环完成 ({duration:.1f}s)")
            
            # 触发回调
            self._notify_cycle_complete(snapshot)
            if snapshot.improvements_detected:
                self._notify_improvement(snapshot)
            
        except Exception as e:
            snapshot.success = False
            snapshot.errors.append(str(e))
            logger.error(f"[#{cycle_id}] ❌ 进化循环失败: {e}", exc_info=True)
            
            self.snapshots.append(snapshot)
            self.consecutive_failures += 1
            self._notify_error(e)
        
        return snapshot
    
    # ━━━ 自适应间隔 ━━━
    
    def _calculate_next_interval(self) -> float:
        """
        计算下次循环间隔
        
        自适应策略:
        - 检测到改进 → 缩短间隔（加速优化）
        - 连续无改进 → 延长间隔（减少开销）
        - 检测到问题 → 缩短间隔（快速响应）
        """
        if not self.adaptive_interval:
            return self.cycle_interval
        
        base_interval = self.cycle_interval
        
        # 最近 3 个周期中有改进 → 加速
        recent = self.snapshots[-3:] if len(self.snapshots) >= 3 else self.snapshots
        improvements_count = sum(
            len(s.improvements_detected) for s in recent
        )
        issues_count = sum(
            len(s.metrics_before.get('issues', [])) for s in recent if s.success
        )
        
        if issues_count > 0:
            # 有问题，加速检查
            interval = max(self.min_interval, base_interval * 0.5)
        elif improvements_count > 0:
            # 有改进，保持或略微缩短
            interval = max(self.min_interval, base_interval * 0.8)
        else:
            # 无变化，延长
            interval = min(self.max_interval, base_interval * 1.5)
        
        logger.debug(f"自适应间隔: {interval:.0f}s (改进数={improvements_count}, 问题数={issues_count})")
        return interval
    
    # ━━━ 持久化 ━━━
    
    def _save_state(self) -> None:
        """保存守护进程状态"""
        try:
            self.state_path.parent.mkdir(parents=True, exist_ok=True)
            state = {
                'cycle_count': self.cycle_count,
                'consecutive_failures': self.consecutive_failures,
                'last_cycle': datetime.now().isoformat(),
                'recent_snapshots': [
                    {
                        'cycle_id': s.cycle_id,
                        'timestamp': s.timestamp,
                        'success': s.success,
                        'actions_count': len(s.actions_taken),
                        'improvements_count': len(s.improvements_detected),
                        'duration_seconds': s.duration_seconds,
                    }
                    for s in self.snapshots[-10:]
                ]
            }
            
            with open(self.state_path, 'w') as f:
                json.dump(state, f, indent=2, ensure_ascii=False)
                
        except Exception as e:
            logger.warning(f"保存状态失败: {e}")
    
    def _load_state(self) -> Optional[Dict[str, Any]]:
        """加载之前的守护进程状态"""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        return None
    
    # ━━━ 回调系统 ━━━
    
    def on_cycle_complete(self, fn: Callable) -> None:
        """注册循环完成回调"""
        self._on_cycle_complete.append(fn)
    
    def on_improvement(self, fn: Callable) -> None:
        """注册改进发现回调"""
        self._on_improvement.append(fn)
    
    def on_error(self, fn: Callable) -> None:
        """注册错误回调"""
        self._on_error.append(fn)
    
    def _notify_cycle_complete(self, snapshot: EvolutionSnapshot) -> None:
        for fn in self._on_cycle_complete:
            try:
                fn(snapshot)
            except Exception as e:
                logger.error(f"循环完成回调异常: {e}")
    
    def _notify_improvement(self, snapshot: EvolutionSnapshot) -> None:
        for fn in self._on_improvement:
            try:
                fn(snapshot)
            except Exception as e:
                logger.error(f"改进回调异常: {e}")
    
    def _notify_error(self, error: Exception) -> None:
        for fn in self._on_error:
            try:
                fn(error)
            except Exception as e:
                logger.error(f"错误回调异常: {e}")
    
    # ━━━ 查询接口 ━━━
    
    def get_status(self) -> Dict[str, Any]:
        """获取守护进程状态"""
        return {
            'state': self._state.value,
            'cycle_count': self.cycle_count,
            'consecutive_failures': self.consecutive_failures,
            'interval': self.cycle_interval,
            'adaptive_interval': self.adaptive_interval,
            'last_cycle': self.snapshots[-1].timestamp if self.snapshots else None,
            'total_improvements': sum(len(s.improvements_detected) for s in self.snapshots),
            'total_actions': sum(len(s.actions_taken) for s in self.snapshots),
        }
    
    def get_recent_snapshots(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的进化快照"""
        return [
            {
                'cycle_id': s.cycle_id,
                'timestamp': s.timestamp,
                'success': s.success,
                'phases': s.phases_completed,
                'actions': len(s.actions_taken),
                'improvements': s.improvements_detected[:5],
                'duration': s.duration_seconds,
            }
            for s in self.snapshots[-limit:]
        ]
    
    def get_evolution_summary(self) -> Dict[str, Any]:
        """获取进化总结"""
        total = len(self.snapshots)
        if total == 0:
            return {'status': 'no_data'}
        
        successful = sum(1 for s in self.snapshots if s.success)
        total_actions = sum(len(s.actions_taken) for s in self.snapshots)
        total_improvements = sum(len(s.improvements_detected) for s in self.snapshots)
        avg_duration = sum(s.duration_seconds for s in self.snapshots) / total if total > 0 else 0
        
        return {
            'total_cycles': total,
            'successful_cycles': successful,
            'success_rate': f"{successful/total:.1%}",
            'total_actions_executed': total_actions,
            'total_improvements_detected': total_improvements,
            'avg_cycle_duration': f"{avg_duration:.1f}s",
            'current_state': self._state.value,
        }

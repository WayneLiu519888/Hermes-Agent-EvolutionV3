#!/usr/bin/env python3
"""
HermesAgentEvolution 持续进化守护进程入口
═══════════════════════════════════════════════════════
将全部 4 个迭代的组件连接成持续进化闭环

运行方式:
    python hermes_daemon.py                    # 前台运行
    python hermes_daemon.py --daemon           # 后台守护进程
    python hermes_daemon.py --dry-run          # 模拟运行（不实际变更）
    python hermes_daemon.py --once             # 只执行一次循环
    python hermes_daemon.py --status           # 查看状态
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
import atexit
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

# 确保项目路径
sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from evolution.learning.observer import LearningObserver
    from evolution.learning.analyzer import ExperienceAnalyzer
    from evolution.learning.experience import Experience, ExperienceType, Outcome
    from evolution.learning.tool_strategy_learner import ToolStrategyLearner
    from evolution.learning.pattern_recognizer import PatternRecognizer
    from evolution.memory.database import AssociationDatabase
    from evolution.self_monitor import SelfMonitor
    from evolution.tools.tool_registry import ToolRegistry
    from evolution.tools.tool_integration import ToolEvolutionEngine, EvolutionConfig
    from evolution.closed_loop.daemon import EvolutionDaemon, EvolutionPhase
    from evolution.closed_loop.orchestrator import ClosedLoopOrchestrator
    from evolution.closed_loop.metrics_collector import SystemMetricsCollector
    from evolution.closed_loop.action_executor import ActionExecutor
except ImportError:
    from src.evolution.learning.observer import LearningObserver
    from src.evolution.learning.analyzer import ExperienceAnalyzer
    from src.evolution.learning.experience import Experience, ExperienceType, Outcome
    from src.evolution.learning.tool_strategy_learner import ToolStrategyLearner
    from src.evolution.learning.pattern_recognizer import PatternRecognizer
    from src.evolution.memory.database import AssociationDatabase
    from src.evolution.self_monitor import SelfMonitor
    from src.evolution.tools.tool_registry import ToolRegistry
    from src.evolution.tools.tool_integration import ToolEvolutionEngine, EvolutionConfig
    from src.evolution.closed_loop.daemon import EvolutionDaemon, EvolutionPhase
    from src.evolution.closed_loop.orchestrator import ClosedLoopOrchestrator
    from src.evolution.closed_loop.metrics_collector import SystemMetricsCollector
    from src.evolution.closed_loop.action_executor import ActionExecutor

# 飞书通知（可选）
try:
    from src.utils.feishu_notifier import get_notifier
    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('data/evolution/daemon.log'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("HermesDaemon")


# ── 优雅关闭：atexit 触发 WAL checkpoint + 关闭所有连接 ──
def _shutdown():
    from evolution.db_pool import db_pool
    db_pool.checkpoint_all(max_wal_mb=0)  # 强制清空所有WAL
    db_pool.close_all()
atexit.register(_shutdown)


class HermesEvolutionDaemon:
    """
    Hermes 持续进化守护进程
    
    整合所有进化组件，运行完整的 Monitor→Analyze→Plan→Execute→Verify→Feedback 闭环
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or {}
        self.data_dir = Path(self.config.get('data_dir', 'data/evolution'))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # 组件引用
        self.daemon: Optional[EvolutionDaemon] = None
        self.orchestrator: Optional[ClosedLoopOrchestrator] = None
        self.metrics_collector: Optional[SystemMetricsCollector] = None
        self.action_executor: Optional[ActionExecutor] = None
        
        # 学习组件
        self.observer: Optional[LearningObserver] = None
        self.analyzer: Optional[ExperienceAnalyzer] = None
        self.strategy_learner: Optional[ToolStrategyLearner] = None
        self.pattern_recognizer: Optional[PatternRecognizer] = None
        
        # 工具组件
        self.tool_registry: Optional[ToolRegistry] = None
        self.tool_engine: Optional[ToolEvolutionEngine] = None
        
        # 自我监控
        self.self_monitor: Optional[SelfMonitor] = None
        
        # 飞书
        self.feishu_notifier = None
        if FEISHU_AVAILABLE:
            try:
                self.feishu_notifier = get_notifier()
            except Exception:
                pass
        
        self._running = False
        self._stop_event = threading.Event()
        
        logger.info("HermesEvolutionDaemon 初始化")
    
    # ━━━━ 初始化组件 ━━━━
    
    def initialize_components(self) -> bool:
        """
        初始化所有进化组件
        
        Returns:
            是否全部初始化成功
        """
        logger.info("=" * 60)
        logger.info("初始化进化系统组件...")
        logger.info("=" * 60)
        
        success = True
        
        # 1. 系统指标采集器
        try:
            self.metrics_collector = SystemMetricsCollector({
                'collection_interval': 30,
                'history_size': 200,
                'data_dir': str(self.data_dir),
            })
            self.metrics_collector.start()
            logger.info("✅ SystemMetricsCollector 就绪")
        except Exception as e:
            logger.error(f"❌ SystemMetricsCollector 失败: {e}")
            success = False
        
        # 2. 学习观察器
        try:
            db_path = str(self.data_dir / "learning_experiences.db")
            self.observer = LearningObserver(db_path=db_path)
            logger.info("✅ LearningObserver 就绪")
        except Exception as e:
            logger.error(f"❌ LearningObserver 失败: {e}")
            success = False
        
        # 3. 经验分析器
        try:
            if self.observer:
                self.analyzer = ExperienceAnalyzer(self.observer)
                logger.info("✅ ExperienceAnalyzer 就绪")
        except Exception as e:
            logger.error(f"❌ ExperienceAnalyzer 失败: {e}")
            success = False
        
        # 4. 工具策略学习器
        try:
            self.strategy_learner = ToolStrategyLearner()
            logger.info("✅ ToolStrategyLearner 就绪")
        except Exception as e:
            logger.error(f"❌ ToolStrategyLearner 失败: {e}")
            success = False
        
        # 5. 模式识别器
        try:
            self.pattern_recognizer = PatternRecognizer()
            logger.info("✅ PatternRecognizer 就绪")
        except Exception as e:
            logger.error(f"❌ PatternRecognizer 失败: {e}")
            # 非关键组件，不标记failed
            self.pattern_recognizer = None
        
        # 6. 自我监控器
        try:
            if self.observer and self.analyzer and self.strategy_learner:
                self.self_monitor = SelfMonitor(
                    observer=self.observer,
                    analyzer=self.analyzer,
                    strategy_learner=self.strategy_learner,
                )
                logger.info("✅ SelfMonitor 就绪")
        except Exception as e:
            logger.error(f"❌ SelfMonitor 失败: {e}")
            success = False
        
        # 7. 工具注册表
        try:
            self.tool_registry = ToolRegistry(
                db_path=str(self.data_dir / "tools.db")
            )
            logger.info("✅ ToolRegistry 就绪")
        except Exception as e:
            logger.error(f"❌ ToolRegistry 失败: {e}")
            # 非关键
            self.tool_registry = None
        
        # 8. 工具进化引擎
        try:
            if self.tool_registry:
                self.tool_engine = ToolEvolutionEngine(
                    registry=self.tool_registry,
                    config=EvolutionConfig(
                        auto_evolve=True,
                        evolution_interval=300,
                        enable_auto_registration=True,
                        enable_performance_monitoring=True,
                        enable_optimization=True,
                    )
                )
                logger.info("✅ ToolEvolutionEngine 就绪")
        except Exception as e:
            logger.error(f"❌ ToolEvolutionEngine 失败: {e}")
            self.tool_engine = None
        
        # 9. 动作执行器
        try:
            self.action_executor = ActionExecutor(
                strategy_learner=self.strategy_learner,
                tool_evolution_engine=self.tool_engine,
                tool_registry=self.tool_registry,
                pattern_recognizer=self.pattern_recognizer,
                config={'dry_run': self.config.get('dry_run', False)},
            )
            logger.info("✅ ActionExecutor 就绪")
        except Exception as e:
            logger.error(f"❌ ActionExecutor 失败: {e}")
            success = False
        
        # 10. 闭环编排器
        try:
            self.orchestrator = ClosedLoopOrchestrator(
                metrics_collector=self.metrics_collector,
                self_monitor=self.self_monitor,
                experience_analyzer=self.analyzer,
                pattern_recognizer=self.pattern_recognizer,
                strategy_learner=self.strategy_learner,
                action_executor=self.action_executor,
                learning_observer=self.observer,
                tool_evolution_engine=self.tool_engine,
                config={
                    'success_rate_threshold': 0.6,
                    'tool_performance_threshold': 60.0,
                    'max_actions_per_cycle': 5,
                },
            )
            logger.info("✅ ClosedLoopOrchestrator 就绪")
        except Exception as e:
            logger.error(f"❌ ClosedLoopOrchestrator 失败: {e}")
            success = False
        
        # 11. 进化守护进程
        try:
            if self.orchestrator:
                self.daemon = EvolutionDaemon(
                    orchestrator=self.orchestrator,
                    config={
                        'cycle_interval': self.config.get('cycle_interval', 300),
                        'adaptive_interval': self.config.get('adaptive_interval', True),
                        'min_interval': 60,
                        'max_interval': 3600,
                        'state_path': str(self.data_dir / 'daemon_state.json'),
                    },
                )
                
                # 注册回调
                self.daemon.on_cycle_complete(self._on_cycle_complete)
                self.daemon.on_improvement(self._on_improvement_detected)
                self.daemon.on_error(self._on_evolution_error)
                
                logger.info("✅ EvolutionDaemon 就绪")
        except Exception as e:
            logger.error(f"❌ EvolutionDaemon 失败: {e}")
            success = False
        
        logger.info("=" * 60)
        if success:
            logger.info("✅ 所有组件初始化完成")
        else:
            logger.warning("⚠️ 部分组件初始化失败，系统可能功能受限")
        logger.info("=" * 60)
        
        return success
    
    # ━━━━ 生命周期 ━━━━
    
    def start(self) -> None:
        """启动持续进化"""
        if not self.daemon:
            logger.error("守护进程未初始化")
            return
        
        self._running = True
        
        # 发送启动通知
        self._notify("🚀 HermesAgentEvolution 持续进化已启动", 
                    f"**模式**: {'模拟' if self.config.get('dry_run') else '生产'}\n"
                    f"**循环间隔**: {self.config.get('cycle_interval', 300)}s\n"
                    f"**自适应间隔**: {self.config.get('adaptive_interval', True)}")
        
        # 启动守护进程
        self.daemon.start()
        
        # 主线程等待（可被信号中断）
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        logger.info("持续进化运行中... (Ctrl+C 停止)")
        
        round_count = 0
        try:
            while self._running and not self._stop_event.is_set():
                # 定期输出状态
                self._stop_event.wait(timeout=60)
                if self._running:
                    round_count += 1
                    status = self.daemon.get_status()
                    logger.info(
                        f"❤️ 心跳: 循环#{status['cycle_count']} | "
                        f"状态={status['state']} | "
                        f"改进总数={status['total_improvements']} | "
                        f"动作总数={status['total_actions']}"
                    )
                    # WAL checkpoint 全覆盖: 每5轮清理一次
                    if round_count % 5 == 0:
                        from evolution.db_pool import db_pool
                        db_pool.checkpoint_all(max_wal_mb=100)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()
    
    def stop(self) -> None:
        """停止持续进化"""
        self._running = False
        self._stop_event.set()
        
        if self.daemon:
            self.daemon.stop(timeout=10)
        
        if self.metrics_collector:
            self.metrics_collector.stop()
        
        # 发送停止通知
        summary = self.get_summary()
        self._notify("🛑 HermesAgentEvolution 已停止", 
                    f"**运行总结**:\n"
                    f"  循环数: {summary.get('total_cycles', 0)}\n"
                    f"  成功率: {summary.get('success_rate', 'N/A')}\n"
                    f"  改进总数: {summary.get('total_improvements', 0)}\n"
                    f"  执行动作: {summary.get('total_actions', 0)}")
        
        logger.info("🛑 HermesAgentEvolution 已停止")
    
    def run_once(self) -> dict:
        """执行单次进化循环（用于测试/手动触发）"""
        if not self.orchestrator:
            logger.error("编排器未初始化")
            return {'error': 'not_initialized'}
        
        logger.info("执行单次进化循环...")
        result = self.orchestrator.run_full_cycle()
        
        logger.info(f"单次循环完成: {result.get('summary', '')}")
        return result
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        logger.info(f"收到信号 {signum}，准备停止...")
        self._running = False
        self._stop_event.set()
    
    # ━━━━ 回调 ━━━━
    
    def _on_cycle_complete(self, snapshot):
        """循环完成回调"""
        status = "✅" if snapshot.success else "❌"
        logger.info(
            f"{status} 循环 #{snapshot.cycle_id} 完成: "
            f"{len(snapshot.actions_taken)} 动作, "
            f"{len(snapshot.improvements_detected)} 改进, "
            f"{snapshot.duration_seconds:.1f}s"
        )
    
    def _on_improvement_detected(self, snapshot):
        """改进发现回调"""
        for improvement in snapshot.improvements_detected[:3]:
            logger.info(f"  📈 改进: {improvement}")
        
        # 飞书通知
        if self.feishu_notifier and len(snapshot.improvements_detected) > 0:
            try:
                improvements_text = '\n'.join(
                    f"  • {imp}" for imp in snapshot.improvements_detected[:5]
                )
                self.feishu_notifier.send_notification(
                    f"📈 进化循环 #{snapshot.cycle_id} — 检测到改进",
                    f"**改进项**:\n{improvements_text}\n\n"
                    f"**执行动作**: {len(snapshot.actions_taken)} 个\n"
                    f"**耗时**: {snapshot.duration_seconds:.1f}s",
                    "info"
                )
            except Exception:
                pass
    
    def _on_evolution_error(self, error):
        """进化错误回调"""
        logger.error(f"进化错误: {error}")
    
    # ━━━━ 通知 ━━━━
    
    def _notify(self, title: str, content: str) -> None:
        """发送通知（飞书 + 日志）"""
        logger.info(f"📢 {title}\n{content}")
        
        if self.feishu_notifier:
            try:
                self.feishu_notifier.send_notification(title, content, "info")
            except Exception as e:
                logger.debug(f"飞书通知失败: {e}")
    
    # ━━━━ 查询 ━━━━
    
    def get_status(self) -> dict:
        """获取系统状态"""
        status = {
            'running': self._running,
            'timestamp': datetime.now().isoformat(),
        }
        
        if self.daemon:
            status.update(self.daemon.get_status())
        
        if self.metrics_collector:
            status['health'] = self.metrics_collector.get_system_health()
        
        return status
    
    def get_summary(self) -> dict:
        """获取进化总结"""
        if self.daemon:
            return self.daemon.get_evolution_summary()
        return {'status': 'not_running'}
    
    def get_recent_cycles(self, limit: int = 10) -> list:
        """获取最近的进化循环"""
        if self.daemon:
            return self.daemon.get_recent_snapshots(limit)
        return []
    
    def get_metrics(self) -> dict:
        """获取当前系统指标"""
        if self.metrics_collector:
            return self.metrics_collector.get_metrics_summary()
        return {}


# ═══════════════════════════════════════════════════════
# CLI 入口
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="HermesAgentEvolution 持续进化守护进程",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                    前台运行持续进化
  %(prog)s --once             只执行一次循环
  %(prog)s --dry-run          模拟运行（不实际变更系统）
  %(prog)s --status           查看运行状态
  %(prog)s --interval 600     每 10 分钟进化一次
        """
    )
    parser.add_argument('--interval', type=int, default=300,
                       help='进化循环间隔（秒，默认 300）')
    parser.add_argument('--no-adaptive', action='store_true',
                       help='禁用自适应间隔')
    parser.add_argument('--dry-run', action='store_true',
                       help='模拟运行（不执行实际变更）')
    parser.add_argument('--once', action='store_true',
                       help='只执行一次循环后退出')
    parser.add_argument('--status', action='store_true',
                       help='查看当前状态')
    parser.add_argument('--data-dir', type=str, default='data/evolution',
                       help='数据目录')
    
    args = parser.parse_args()
    
    # 配置
    config = {
        'cycle_interval': args.interval,
        'adaptive_interval': not args.no_adaptive,
        'dry_run': args.dry_run,
        'data_dir': args.data_dir,
    }
    
    if args.dry_run:
        logger.info("⚠️ DRY-RUN 模式：不会执行任何实际系统变更")
    
    # 创建守护进程
    hermes_daemon = HermesEvolutionDaemon(config)
    
    if args.status:
        # 查看状态
        print("\n📊 HermesAgentEvolution 状态")
        print("=" * 50)
        
        # 尝试加载历史状态
        state_path = Path(args.data_dir) / 'daemon_state.json'
        if state_path.exists():
            with open(state_path) as f:
                state = json.load(f)
            print(f"  上次循环数: {state.get('cycle_count', 0)}")
            print(f"  上次运行: {state.get('last_cycle', 'unknown')}")
            recent = state.get('recent_snapshots', [])
            if recent:
                print(f"  最近 {len(recent)} 次循环:")
                for s in recent[-5:]:
                    icon = "✅" if s.get('success') else "❌"
                    print(f"    {icon} #{s['cycle_id']}: "
                          f"{s.get('actions_count', 0)} 动作, "
                          f"{s.get('improvements_count', 0)} 改进, "
                          f"{s.get('duration_seconds', 0):.1f}s")
        else:
            print("  尚无运行记录")
        print()
        return
    
    # 初始化组件
    if not hermes_daemon.initialize_components():
        logger.error("组件初始化失败，退出")
        sys.exit(1)
    
    if args.once:
        # 单次执行
        result = hermes_daemon.run_once()
        print(f"\n📊 单次循环结果:")
        print(f"  ID: {result.get('cycle_id')}")
        print(f"  摘要: {result.get('summary')}")
        print(f"  耗时: {result.get('duration', 0)}s")
        
        phases = result.get('phases', {})
        print(f"  Monitor: {phases.get('monitor', {}).get('metrics_count', 0)} 指标")
        print(f"  Analyze: {phases.get('analyze', {}).get('issues', 0)} 问题")
        print(f"  Plan: {phases.get('plan', {}).get('actions', 0)} 动作")
        print(f"  Execute: {phases.get('execute', {}).get('success', 0)} 成功")
        print(f"  Verify: {phases.get('verify', {}).get('score', 0):.2f} 验证分")
        
        hermes_daemon.metrics_collector.stop()
    else:
        # 启动持续进化
        hermes_daemon.start()


if __name__ == '__main__':
    main()

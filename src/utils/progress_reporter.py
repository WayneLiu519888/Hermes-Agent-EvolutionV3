import os
import sys
import time
import json
from datetime import datetime, timedelta
import threading
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.feishu_notifier import FeishuNotifier

class ProgressReporter:
    """进度汇报器 - 每2小时自动汇报"""
    
    def __init__(self, config_path: str = None):
        self.notifier = FeishuNotifier(config_path)
        self.report_interval = 7200  # 2小时（秒）
        self.is_running = False
        self.report_thread = None
        self.task_progress = {}
        self.start_time = datetime.now()
        
    def start_reporting(self):
        """开始定时汇报"""
        if self.is_running:
            print("⚠️ 汇报器已在运行中")
            return
            
        self.is_running = True
        self.start_time = datetime.now()
        
        # 启动汇报线程
        self.report_thread = threading.Thread(target=self._report_loop, daemon=True)
        self.report_thread.start()
        
        print(f"✅ 定时汇报系统已启动")
        print(f"   • 汇报间隔: 每2小时")
        print(f"   • 开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 发送启动通知
        self.send_start_notification()
        
    def stop_reporting(self):
        """停止定时汇报"""
        self.is_running = False
        if self.report_thread:
            self.report_thread.join(timeout=5)
        print("⏹️ 定时汇报系统已停止")
        
    def _report_loop(self):
        """汇报循环"""
        while self.is_running:
            try:
                # 等待2小时
                time.sleep(self.report_interval)
                
                if self.is_running:
                    self.send_progress_report()
                    
            except Exception as e:
                print(f"❌ 汇报循环出错: {e}")
                time.sleep(60)  # 出错后等待1分钟重试
                
    def update_task_progress(self, task_name: str, status: str, 
                           details: Dict[str, Any] = None):
        """更新任务进度"""
        self.task_progress[task_name] = {
            "status": status,  # pending, in_progress, completed, failed
            "details": details or {},
            "updated_at": datetime.now().isoformat()
        }
        
    def send_start_notification(self):
        """发送启动通知"""
        content = f"""
**🚀 迭代1执行开始**

**开始时间:** {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
**汇报间隔:** 每2小时
**预计完成:** 本周内

**🎯 迭代1任务清单:**
1. **记忆系统检索策略自优化** - 待执行
2. **学习能力观察模块实现** - 待执行  
3. **工具能力创建框架建立** - 待执行

**📊 执行策略:**
• 使用subagent-driven-development技能
• 每2小时自动汇报进展
• 所有代码变更实时提交
• 测试驱动开发

**🔔 下次汇报:** { (datetime.now() + timedelta(seconds=self.report_interval)).strftime('%Y-%m-%d %H:%M:%S') }
"""
        
        self.notifier.send_notification(
            title="迭代1执行开始",
            content=content,
            level="success"
        )
        
    def send_progress_report(self):
        """发送进度报告"""
        elapsed = datetime.now() - self.start_time
        elapsed_hours = elapsed.total_seconds() / 3600
        
        # 统计任务状态
        task_stats = {
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "total": len(self.task_progress)
        }
        
        for task in self.task_progress.values():
            status = task.get("status", "pending")
            if status in task_stats:
                task_stats[status] += 1
                
        # 构建任务详情
        task_details = []
        for task_name, task_info in self.task_progress.items():
            status = task_info.get("status", "pending")
            status_icon = {
                "pending": "⏳",
                "in_progress": "🔄",
                "completed": "✅",
                "failed": "❌"
            }.get(status, "❓")
            
            task_details.append(f"{status_icon} **{task_name}** - {status}")
            
            # 添加详细信息
            details = task_info.get("details", {})
            if details:
                for key, value in details.items():
                    if isinstance(value, (int, float)):
                        task_details.append(f"   • {key}: {value}")
                    else:
                        task_details.append(f"   • {key}: {str(value)[:50]}...")
                        
        task_details_text = "\n".join(task_details) if task_details else "暂无任务详情"
        
        content = f"""
**📊 迭代1进度报告**

**报告时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**已运行时间:** {elapsed_hours:.1f}小时
**下次汇报:** {(datetime.now() + timedelta(seconds=self.report_interval)).strftime('%Y-%m-%d %H:%M:%S')}

**📈 任务统计:**
• 总计: {task_stats['total']}
• 待执行: {task_stats['pending']}
• 进行中: {task_stats['in_progress']}
• 已完成: {task_stats['completed']}
• 已失败: {task_stats['failed']}

**📋 任务详情:**
{task_details_text}

**🎯 当前重点:**
继续推进迭代1的3个核心任务，确保代码质量和测试覆盖率。

**⚠️ 注意事项:**
• 每完成一个任务立即提交代码
• 确保所有测试通过
• 更新相关文档
• 记录遇到的问题和解决方案
"""
        
        self.notifier.send_notification(
            title=f"迭代1进度报告 ({datetime.now().strftime('%H:%M')})",
            content=content,
            level="info"
        )
        
    def send_task_complete_notification(self, task_name: str, 
                                      completion_details: Dict[str, Any]):
        """发送任务完成通知"""
        content = f"""
**✅ 任务完成通知**

**任务名称:** {task_name}
**完成时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**完成详情:**
"""
        
        for key, value in completion_details.items():
            if isinstance(value, (int, float)):
                content += f"• **{key}:** {value}\n"
            elif isinstance(value, list):
                content += f"• **{key}:** {', '.join(map(str, value[:5]))}"
                if len(value) > 5:
                    content += f" ... (共{len(value)}项)"
                content += "\n"
            else:
                content += f"• **{key}:** {str(value)[:100]}\n"
                
        # 更新任务进度
        self.update_task_progress(task_name, "completed", completion_details)
        
        self.notifier.send_notification(
            title=f"任务完成: {task_name}",
            content=content,
            level="success"
        )
        
    def send_error_notification(self, task_name: str, error_message: str,
                              recovery_steps: List[str] = None):
        """发送错误通知"""
        content = f"""
**❌ 任务错误通知**

**任务名称:** {task_name}
**错误时间:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**错误信息:**
{error_message}

**恢复步骤:**
"""
        
        if recovery_steps:
            for step in recovery_steps:
                content += f"• {step}\n"
        else:
            content += "• 正在分析问题原因\n• 将尝试自动恢复\n"
            
        # 更新任务进度
        self.update_task_progress(task_name, "failed", {
            "error": error_message,
            "recovery_steps": recovery_steps or []
        })
        
        self.notifier.send_notification(
            title=f"任务错误: {task_name}",
            content=content,
            level="error"
        )

# 全局汇报器实例
_reporter = None

def get_reporter(webhook_url: str = None) -> ProgressReporter:
    """获取全局汇报器"""
    global _reporter
    if _reporter is None:
        _reporter = ProgressReporter(webhook_url)
    return _reporter

if __name__ == "__main__":
    # 测试汇报系统
    reporter = get_reporter()
    
    # 模拟任务进度
    reporter.update_task_progress("任务1", "in_progress", {"进度": "50%", "文件": "retrieval_optimizer.py"})
    reporter.update_task_progress("任务2", "pending", {})
    reporter.update_task_progress("任务3", "pending", {})
    
    # 发送测试报告
    reporter.send_progress_report()
    
    print("✅ 进度汇报系统测试完成")

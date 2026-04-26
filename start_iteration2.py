#!/usr/bin/env python3
"""
迭代2执行启动脚本
每2小时通过飞书汇报进展
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent
sys.path.append(str(project_root))

from src.utils.feishu_notifier import FeishuNotifier
from src.utils.progress_reporter import ProgressReporter

class Iteration2Executor:
    """迭代2执行器"""
    
    def __init__(self):
        self.notifier = FeishuNotifier()
        self.reporter = ProgressReporter()
        self.start_time = datetime.now()
        self.tasks = [
            {
                "id": "task1",
                "name": "记忆系统关联发现自动化",
                "priority": "high",
                "status": "pending",
                "progress": 0,
                "start_time": None,
                "end_time": None
            },
            {
                "id": "task2", 
                "name": "学习能力分析算法实现",
                "priority": "high",
                "status": "pending",
                "progress": 0,
                "start_time": None,
                "end_time": None
            },
            {
                "id": "task3",
                "name": "工具能力策略学习开始",
                "priority": "medium",
                "status": "pending",
                "progress": 0,
                "start_time": None,
                "end_time": None
            }
        ]
        
    def start_iteration(self):
        """开始迭代2"""
        print(f"🚀 开始迭代2: 能力增强")
        print(f"开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"任务数量: {len(self.tasks)}")
        print("-" * 50)
        
        # 发送开始通知
        self.notifier.send_notification(
            title="🚀 迭代2开始执行",
            content=f"""迭代2: 能力增强 已开始执行

开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
任务数量: 3个
预计时长: 3-4天

任务列表:
1. 🧠 记忆系统关联发现自动化 (高优先级)
2. 📚 学习能力分析算法实现 (高优先级)
3. 🔧 工具能力策略学习开始 (中优先级)

汇报机制: 每2小时汇报进展
""",
            level="success"
        )
        
        # 启动定时汇报
        self.start_progress_reporting()
        
        return True
        
    def start_progress_reporting(self):
        """启动定时进度汇报"""
        print("⏰ 启动定时进度汇报 (每2小时)")
        
        # 创建汇报线程
        import threading
        
        def report_progress():
            while True:
                try:
                    self.send_progress_report()
                    time.sleep(7200)  # 2小时
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"汇报错误: {e}")
                    time.sleep(300)  # 5分钟后重试
                    
        # 启动汇报线程
        report_thread = threading.Thread(target=report_progress, daemon=True)
        report_thread.start()
        
        print("✅ 定时汇报已启动")
        
    def send_progress_report(self):
        """发送进度报告"""
        current_time = datetime.now()
        elapsed = current_time - self.start_time
        
        # 计算总体进度
        total_progress = sum(task["progress"] for task in self.tasks) / len(self.tasks)
        completed_tasks = sum(1 for task in self.tasks if task["status"] == "completed")
        
        report_content = f"""**迭代2进度报告**

报告时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}
已运行时间: {str(elapsed).split('.')[0]}
总体进度: {total_progress:.1f}%
完成任务: {completed_tasks}/{len(self.tasks)}

**任务状态:**
"""
        
        for task in self.tasks:
            status_icon = "✅" if task["status"] == "completed" else "🔄" if task["status"] == "in_progress" else "⏳"
            report_content += f"{status_icon} {task['name']}: {task['progress']}% ({task['status']})\n"
            
        report_content += f"""
**下次汇报:** {(current_time + timedelta(hours=2)).strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        self.notifier.send_notification(
            title=f"📊 迭代2进度: {total_progress:.1f}%",
            content=report_content,
            level="info"
        )
        
        print(f"📊 进度报告已发送: {total_progress:.1f}%")
        
    def update_task_progress(self, task_id, progress, status=None):
        """更新任务进度"""
        for task in self.tasks:
            if task["id"] == task_id:
                task["progress"] = progress
                if status:
                    task["status"] = status
                    if status == "in_progress" and not task["start_time"]:
                        task["start_time"] = datetime.now()
                    elif status == "completed" and not task["end_time"]:
                        task["end_time"] = datetime.now()
                        
                # 发送任务更新通知
                if status in ["in_progress", "completed"]:
                    self.send_task_update_notification(task)
                    
                break
                
    def send_task_update_notification(self, task):
        """发送任务更新通知"""
        if task["status"] == "in_progress":
            title = f"🔄 开始执行: {task['name']}"
            content = f"开始执行任务: {task['name']}\n开始时间: {task['start_time'].strftime('%Y-%m-%d %H:%M:%S')}"
            level = "info"
        elif task["status"] == "completed":
            title = f"✅ 完成: {task['name']}"
            duration = task["end_time"] - task["start_time"] if task["start_time"] else timedelta(0)
            content = f"完成任务: {task['name']}\n完成时间: {task['end_time'].strftime('%Y-%m-%d %H:%M:%S')}\n耗时: {str(duration).split('.')[0]}"
            level = "success"
        else:
            return
            
        self.notifier.send_notification(
            title=title,
            content=content,
            level=level
        )
        
    def complete_iteration(self):
        """完成迭代"""
        end_time = datetime.now()
        duration = end_time - self.start_time
        
        # 计算统计
        completed_tasks = sum(1 for task in self.tasks if task["status"] == "completed")
        total_progress = sum(task["progress"] for task in self.tasks) / len(self.tasks)
        
        summary_content = f"""**🎉 迭代2完成总结**

开始时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}
完成时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}
总耗时: {str(duration).split('.')[0]}

**完成情况:**
任务完成率: {completed_tasks}/{len(self.tasks)} ({total_progress:.1f}%)

**任务详情:**
"""
        
        for task in self.tasks:
            duration_str = ""
            if task["start_time"] and task["end_time"]:
                task_duration = task["end_time"] - task["start_time"]
                duration_str = f" ({str(task_duration).split('.')[0]})"
                
            status_icon = "✅" if task["status"] == "completed" else "❌"
            summary_content += f"{status_icon} {task['name']}: {task['progress']}%{duration_str}\n"
            
        self.notifier.send_notification(
            title=f"🎉 迭代2完成: {completed_tasks}/{len(self.tasks)} 任务完成",
            content=summary_content,
            level="success"
        )
        
        print(f"🎉 迭代2完成总结已发送")
        
def main():
    """主函数"""
    executor = Iteration2Executor()
    
    try:
        # 开始迭代
        executor.start_iteration()
        
        print("迭代2执行系统已启动")
        print("按 Ctrl+C 停止")
        
        # 保持主线程运行
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n停止迭代2执行系统")
        executor.complete_iteration()
        
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
启动迭代1执行和定时汇报
"""

import os
import sys
import time
from datetime import datetime

# 添加项目路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.progress_reporter import get_reporter

def main():
    print("🚀 HermesAgentEvolution 迭代1执行启动")
    print("=" * 50)
    
    # 获取汇报器
    reporter = get_reporter()
    
    # 启动定时汇报
    reporter.start_reporting()
    
    print("\n📋 迭代1任务清单:")
    print("1. 记忆系统检索策略自优化")
    print("2. 学习能力观察模块实现")
    print("3. 工具能力创建框架建立")
    
    print("\n⏰ 汇报设置:")
    print("• 每2小时自动汇报进展")
    print("• 任务完成时立即通知")
    print("• 遇到错误时立即告警")
    
    print("\n✅ 系统已启动，开始执行迭代1...")
    print("\n📢 注意: 所有进展将通过飞书通知")
    
    # 保持主线程运行
    try:
        while True:
            time.sleep(60)  # 每分钟检查一次
    except KeyboardInterrupt:
        print("\n⏹️ 收到停止信号，正在停止汇报系统...")
        reporter.stop_reporting()
        print("✅ 系统已安全停止")

if __name__ == "__main__":
    main()

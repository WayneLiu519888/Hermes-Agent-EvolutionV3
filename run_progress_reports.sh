#!/bin/bash
# 每2小时运行一次进展报告
while true; do
    cd /mnt/c/Users/1/hermes_agent_evolution && python3 send_progress_report.py
    sleep 7200  # 2小时 = 7200秒
done

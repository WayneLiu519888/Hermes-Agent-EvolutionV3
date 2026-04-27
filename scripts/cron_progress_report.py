#!/usr/bin/env python3
"""
Cron-driven progress report script for HermesAgentEvolution.
Runs every 2 hours, collects project status, and sends via Feishu.
"""
import os
import sys
import subprocess
import json
from datetime import datetime, timedelta
from pathlib import Path

# Ensure project root is in path
PROJECT_ROOT = Path("/mnt/c/Users/1/hermes_agent_evolution")
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

from src.utils.feishu_notifier import FeishuNotifier


def run_cmd(cmd, timeout=30):
    """Run a shell command and return its output."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True,
                                text=True, timeout=timeout, cwd=PROJECT_ROOT)
        return result.stdout.strip()[:500] or result.stderr.strip()[:500]
    except Exception as e:
        return f"Error: {e}"


def collect_project_status():
    """Collect comprehensive project status."""
    status = {}
    
    # Git status
    status["git_branch"] = run_cmd("git branch --show-current")
    status["git_status_short"] = run_cmd("git status --short")
    
    # Recent commits (last 4)
    status["recent_commits"] = run_cmd(
        "git log --oneline -4 --format='%h %s (%ar)'"
    )
    
    # File changes
    status["modified_files_count"] = run_cmd(
        "git diff --name-only | wc -l"
    ).strip()
    status["untracked_files_count"] = run_cmd(
        "git ls-files --others --exclude-standard | wc -l"
    ).strip()
    
    # Evolution data
    data_dir = PROJECT_ROOT / "data"
    if data_dir.exists():
        status["data_files"] = run_cmd(
            f"find {data_dir} -type f -name '*.db' -o -name '*.json' 2>/dev/null | wc -l"
        ).strip()
    
    # Log tail (last notable lines)
    log_file = PROJECT_ROOT / "feishu_notifications.log"
    if log_file.exists():
        status["last_notification"] = run_cmd(
            f"tail -1 {log_file}"
        )[:200]
    
    # Python tests summary
    test_dir = PROJECT_ROOT / "tests"
    if test_dir.exists():
        test_count = len(list(test_dir.glob("test_*.py")))
        status["test_files"] = str(test_count)
    
    # Disk usage of project
    status["project_size"] = run_cmd(
        f"du -sh {PROJECT_ROOT} 2>/dev/null | cut -f1"
    )
    
    return status


def build_report(status):
    """Build a formatted Feishu markdown report."""
    now = datetime.now()
    next_report = now + timedelta(hours=2)
    
    report = f"""**📊 HermesAgentEvolution 定期状态报告**

**报告时间:** {now.strftime('%Y-%m-%d %H:%M:%S')}
**下次报告:** {next_report.strftime('%Y-%m-%d %H:%M:%S')}

**🔧 Git 状态:**
• 分支: `{status.get('git_branch', 'N/A')}`
• 未提交变更: {status.get('modified_files_count', '?')} 文件修改, {status.get('untracked_files_count', '?')} 未跟踪

**📝 最近提交:**
{chr(10).join(['• ' + c for c in status.get('recent_commits', '').split(chr(10))[:4]])}

**📦 项目概况:**
• 测试文件: {status.get('test_files', 'N/A')} 个
• 数据文件: {status.get('data_files', 'N/A')} 个
• 项目大小: {status.get('project_size', 'N/A')}

**🔔 通知模式:** OpenAPI (飞书)
**⏰ 报告频率:** 每2小时自动生成
"""
    return report


def main():
    notifier = FeishuNotifier(config_path=str(PROJECT_ROOT / "config/feishu_config.json"))
    
    # Collect status
    status = collect_project_status()
    
    # Build and send report
    report = build_report(status)
    
    success = notifier.send_notification(
        title=f"🕐 HermesAgentEvolution 状态报告 ({datetime.now().strftime('%m/%d %H:%M')})",
        content=report,
        level="info"
    )
    
    # Also log locally
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "success": success,
        "status_summary": {
            "branch": status.get("git_branch"),
            "modified": status.get("modified_files_count"),
            "untracked": status.get("untracked_files_count"),
        }
    }
    
    log_path = PROJECT_ROOT / "cron_reports.log"
    with open(log_path, "a") as f:
        f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    print(f"[{datetime.now().isoformat()}] Report sent: {'OK' if success else 'FAILED'}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

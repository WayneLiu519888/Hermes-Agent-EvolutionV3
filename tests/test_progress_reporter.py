"""
progress_reporter 模块测试

覆盖:
- ProgressReporter 初始化
- start_reporting / stop_reporting 状态转换
- update_task_progress 更新任务进度
- send_start_notification 启动通知
- send_progress_report 进度报告各种场景
- send_task_complete_notification 任务完成通知
- send_error_notification 错误通知
- _report_loop 但不真的等2小时
- get_reporter 全局实例
"""

import os
import sys
import time
import threading
from unittest.mock import patch, MagicMock, call

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.utils.progress_reporter import ProgressReporter, get_reporter, _reporter


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clean_global_reporter():
    """每个测试后重置全局 reporter"""
    global _reporter
    _reporter = None
    yield
    _reporter = None


@pytest.fixture
def mock_notifier():
    """Mock FeishuNotifier 避免真实通知"""
    with patch("src.utils.progress_reporter.FeishuNotifier") as mock_cls:
        mock_instance = MagicMock()
        mock_instance.send_notification.return_value = True
        mock_cls.return_value = mock_instance
        yield mock_cls, mock_instance


@pytest.fixture
def reporter(mock_notifier):
    """创建一个已 mock 的 ProgressReporter"""
    _, notifier = mock_notifier
    rep = ProgressReporter()
    rep.notifier = notifier
    return rep


# ── 初始化测试 ────────────────────────────────────────────────────────────────

class TestInit:
    """测试 ProgressReporter 初始化"""

    def test_default_initialization(self, mock_notifier):
        """默认初始化状态"""
        _, _ = mock_notifier
        rep = ProgressReporter()
        assert rep.is_running is False
        assert rep.report_thread is None
        assert rep.report_interval == 7200
        assert rep.task_progress == {}
        assert rep.start_time is not None

    def test_init_with_config_path(self, mock_notifier):
        """带配置文件路径初始化"""
        mock_cls, _ = mock_notifier
        rep = ProgressReporter(config_path="/fake/config.json")
        mock_cls.assert_called_once_with("/fake/config.json")


# ── start_reporting / stop_reporting 测试 ────────────────────────────────────

class TestStartStopReporting:
    """测试 start_reporting 和 stop_reporting"""

    def test_start_reporting_initial(self, reporter, mock_notifier):
        """首次启动汇报"""
        _, notifier = mock_notifier
        reporter.start_reporting()
        assert reporter.is_running is True
        assert reporter.report_thread is not None
        assert isinstance(reporter.report_thread, threading.Thread)
        notifier.send_notification.assert_called_once()

    def test_start_reporting_already_running(self, reporter, mock_notifier):
        """已在运行中再次启动"""
        _, notifier = mock_notifier
        reporter.start_reporting()
        notifier.send_notification.reset_mock()
        reporter.start_reporting()  # 第二次启动
        # 不应再发送通知
        notifier.send_notification.assert_not_called()

    def test_stop_reporting(self, reporter):
        """停止汇报"""
        reporter.start_reporting()
        assert reporter.is_running is True
        reporter.stop_reporting()
        assert reporter.is_running is False

    def test_stop_reporting_not_running(self, reporter):
        """停止未运行的汇报器"""
        reporter.stop_reporting()
        assert reporter.is_running is False

    def test_stop_reporting_waits_for_thread(self, reporter):
        """停止时等待线程结束"""
        reporter.start_reporting()
        reporter.stop_reporting()
        assert reporter.is_running is False

    def test_start_sets_start_time(self, reporter):
        """启动时重置开始时间"""
        from datetime import datetime, timedelta
        old_start = reporter.start_time
        reporter.start_reporting()
        # 时间不应相差太大（最多1秒）
        assert abs((reporter.start_time - datetime.now()).total_seconds()) < 5


# ── update_task_progress 测试 ────────────────────────────────────────────────

class TestUpdateTaskProgress:
    """测试 update_task_progress"""

    def test_create_new_task(self, reporter):
        """创建新任务进度"""
        reporter.update_task_progress("任务A", "in_progress", {"progress": "50%"})
        assert "任务A" in reporter.task_progress
        assert reporter.task_progress["任务A"]["status"] == "in_progress"
        assert reporter.task_progress["任务A"]["details"]["progress"] == "50%"
        assert "updated_at" in reporter.task_progress["任务A"]

    def test_update_existing_task(self, reporter):
        """更新已有任务"""
        reporter.update_task_progress("任务A", "pending", {})
        reporter.update_task_progress("任务A", "completed", {"done": True})
        assert reporter.task_progress["任务A"]["status"] == "completed"
        assert reporter.task_progress["任务A"]["details"]["done"] is True

    def test_details_default_to_empty_dict(self, reporter):
        """details 默认为空字典"""
        reporter.update_task_progress("任务B", "pending")
        assert reporter.task_progress["任务B"]["details"] == {}

    def test_multiple_tasks(self, reporter):
        """多个任务同时追踪"""
        reporter.update_task_progress("T1", "pending")
        reporter.update_task_progress("T2", "in_progress")
        reporter.update_task_progress("T3", "completed")
        assert len(reporter.task_progress) == 3


# ── send_start_notification 测试 ─────────────────────────────────────────────

class TestSendStartNotification:
    """测试 send_start_notification"""

    def test_sends_notification(self, reporter, mock_notifier):
        """发送启动通知"""
        _, notifier = mock_notifier
        reporter.send_start_notification()
        notifier.send_notification.assert_called_once()
        call_args = notifier.send_notification.call_args
        kwargs = call_args[1]
        assert kwargs["level"] == "success"
        assert "迭代1执行开始" in kwargs["title"]

    def test_content_has_key_sections(self, reporter, mock_notifier):
        """通知内容包含关键部分"""
        _, notifier = mock_notifier
        reporter.send_start_notification()
        content = notifier.send_notification.call_args[1]["content"]
        assert "记忆系统检索策略自优化" in content
        assert "学习能力观察模块实现" in content
        assert "工具能力创建框架建立" in content


# ── send_progress_report 测试 ────────────────────────────────────────────────

class TestSendProgressReport:
    """测试 send_progress_report"""

    def test_empty_tasks_report(self, reporter, mock_notifier):
        """无任务时的进度报告"""
        _, notifier = mock_notifier
        reporter.send_progress_report()
        notifier.send_notification.assert_called_once()
        content = notifier.send_notification.call_args[1]["content"]
        assert "暂无任务详情" in content
        assert "总计: 0" in content

    def test_report_with_tasks(self, reporter, mock_notifier):
        """有任务进度时的报告"""
        _, notifier = mock_notifier
        reporter.update_task_progress("Task1", "completed", {"files": 5})
        reporter.update_task_progress("Task2", "in_progress",
                                       {"progress": "60%", "lines": 120})
        reporter.send_progress_report()
        content = notifier.send_notification.call_args[1]["content"]
        assert "总计: 2" in content
        assert "已完成: 1" in content
        assert "进行中: 1" in content
        assert "Task1" in content
        assert "Task2" in content

    def test_report_includes_elapsed_time(self, reporter, mock_notifier):
        """报告包含已运行时间"""
        _, notifier = mock_notifier
        reporter.send_progress_report()
        content = notifier.send_notification.call_args[1]["content"]
        assert "已运行时间:" in content

    def test_all_status_counts(self, reporter, mock_notifier):
        """所有状态都被正确统计"""
        _, notifier = mock_notifier
        reporter.update_task_progress("A", "pending")
        reporter.update_task_progress("B", "in_progress")
        reporter.update_task_progress("C", "completed")
        reporter.update_task_progress("D", "failed")
        reporter.send_progress_report()
        content = notifier.send_notification.call_args[1]["content"]
        assert "待执行: 1" in content
        assert "进行中: 1" in content
        assert "已完成: 1" in content
        assert "已失败: 1" in content

    def test_details_truncation(self, reporter, mock_notifier):
        """长详情值被截断"""
        _, notifier = mock_notifier
        long_val = "x" * 100
        reporter.update_task_progress("T", "in_progress", {"long_key": long_val})
        reporter.send_progress_report()
        content = notifier.send_notification.call_args[1]["content"]
        # 字符串值应该被截断到 ~50 字符
        assert long_val[:45] in content  # some portion

    def test_numeric_details_not_truncated(self, reporter, mock_notifier):
        """数字类型详情不被截断"""
        _, notifier = mock_notifier
        reporter.update_task_progress("T", "completed", {"lines": 12345})
        reporter.send_progress_report()
        content = notifier.send_notification.call_args[1]["content"]
        assert "12345" in content


# ── send_task_complete_notification 测试 ─────────────────────────────────────

class TestSendTaskComplete:
    """测试 send_task_complete_notification"""

    def test_sends_completion_notification(self, reporter, mock_notifier):
        """发送任务完成通知"""
        _, notifier = mock_notifier
        reporter.send_task_complete_notification(
            "记忆系统优化",
            {"files_changed": 3, "tests_passed": 25, "coverage": "95%"}
        )
        notifier.send_notification.assert_called_once()
        kwargs = notifier.send_notification.call_args[1]
        assert kwargs["level"] == "success"
        assert "记忆系统优化" in kwargs["title"]
        assert "3" in kwargs["content"]
        assert "25" in kwargs["content"]

    def test_updates_task_progress(self, reporter):
        """发送完成通知后更新任务进度"""
        reporter.send_task_complete_notification(
            "TaskX", {"done": True}
        )
        assert "TaskX" in reporter.task_progress
        assert reporter.task_progress["TaskX"]["status"] == "completed"

    def test_list_details_handling(self, reporter, mock_notifier):
        """列表类型详情处理"""
        _, notifier = mock_notifier
        reporter.send_task_complete_notification(
            "TaskL",
            {"files": ["a.py", "b.py", "c.py"]}
        )
        content = notifier.send_notification.call_args[1]["content"]
        assert "a.py" in content

    def test_long_list_truncated(self, reporter, mock_notifier):
        """长列表截断显示"""
        _, notifier = mock_notifier
        long_list = [f"f{i}.py" for i in range(10)]
        reporter.send_task_complete_notification("TaskT", {"files": long_list})
        content = notifier.send_notification.call_args[1]["content"]
        assert "共10项" in content

    def test_long_string_truncated_in_details(self, reporter, mock_notifier):
        """长字符串被截断到100字符"""
        _, notifier = mock_notifier
        long_str = "x" * 200
        reporter.send_task_complete_notification("T", {"desc": long_str})
        content = notifier.send_notification.call_args[1]["content"]
        # 应包含截断后的值
        assert long_str[:90] in content


# ── send_error_notification 测试 ─────────────────────────────────────────────

class TestSendErrorNotification:
    """测试 send_error_notification"""

    def test_sends_error_notification(self, reporter, mock_notifier):
        """发送错误通知"""
        _, notifier = mock_notifier
        reporter.send_error_notification(
            "数据库写入",
            "Connection refused",
            ["检查网络连接", "重启数据库服务"]
        )
        notifier.send_notification.assert_called_once()
        kwargs = notifier.send_notification.call_args[1]
        assert kwargs["level"] == "error"
        assert "数据库写入" in kwargs["title"]
        assert "Connection refused" in kwargs["content"]
        assert "检查网络连接" in kwargs["content"]
        assert "重启数据库服务" in kwargs["content"]

    def test_no_recovery_steps(self, reporter, mock_notifier):
        """无恢复步骤时使用默认步骤"""
        _, notifier = mock_notifier
        reporter.send_error_notification("任务X", "出错了")
        content = notifier.send_notification.call_args[1]["content"]
        assert "正在分析问题原因" in content
        assert "将尝试自动恢复" in content

    def test_updates_task_progress_on_error(self, reporter):
        """错误通知更新任务进度为 failed"""
        reporter.send_error_notification(
            "FailedTask", "fatal error", ["step1", "step2"]
        )
        assert reporter.task_progress["FailedTask"]["status"] == "failed"
        details = reporter.task_progress["FailedTask"]["details"]
        assert details["error"] == "fatal error"
        assert details["recovery_steps"] == ["step1", "step2"]


# ── _report_loop 测试 ────────────────────────────────────────────────────────

class TestReportLoop:
    """测试 _report_loop 方法（不真的sleep 2小时）"""

    def test_loop_exits_when_stopped(self, reporter):
        """停止汇报后循环退出"""
        # 使用一个极短的 interval 来加速测试
        reporter.report_interval = 0.01
        reporter.is_running = True
        thread = threading.Thread(target=reporter._report_loop, daemon=True)
        thread.start()
        # 给一点时间让循环开始
        time.sleep(0.05)
        reporter.is_running = False
        thread.join(timeout=2)
        assert not thread.is_alive()

    def test_loop_sends_report(self, reporter, mock_notifier):
        """循环会调用 send_progress_report"""
        _, notifier = mock_notifier
        reporter.report_interval = 0.01
        reporter.is_running = True
        # 只允许 sleep 一次就停止
        call_count = [0]

        def limited_sleep(seconds):
            call_count[0] += 1
            if call_count[0] >= 2:
                reporter.is_running = False

        with patch("src.utils.progress_reporter.time.sleep", side_effect=limited_sleep):
            thread = threading.Thread(target=reporter._report_loop, daemon=True)
            thread.start()
            thread.join(timeout=5)

        # 应该至少调用了一次 send_progress_report
        assert notifier.send_notification.call_count >= 1

    def test_loop_handles_exception(self, reporter):
        """循环处理异常不崩溃"""
        reporter.report_interval = 0.01
        reporter.is_running = True
        call_count = [0]

        def raise_then_stop(seconds):
            call_count[0] += 1
            if call_count[0] == 1:
                raise Exception("Test error in loop")
            elif call_count[0] >= 3:
                reporter.is_running = False

        with patch("src.utils.progress_reporter.time.sleep",
                   side_effect=raise_then_stop):
            thread = threading.Thread(target=reporter._report_loop, daemon=True)
            thread.start()
            thread.join(timeout=5)

        assert not thread.is_alive()


# ── get_reporter 测试 ────────────────────────────────────────────────────────

class TestGetReporter:
    """测试 get_reporter 函数"""

    def test_returns_progress_reporter(self):
        """返回 ProgressReporter 实例"""
        rep = get_reporter()
        assert isinstance(rep, ProgressReporter)

    def test_singleton_behavior(self, mock_notifier):
        """多次调用返回同一实例"""
        rep1 = get_reporter()
        rep2 = get_reporter()
        assert rep1 is rep2

"""TUI 模块测试。"""

import pytest
import time

from dailycheck_agent.lib.tui import (
    TaskTUI,
    SimpleTUI,
    TaskStatus,
    TUIState,
    STATUS_SYMBOLS,
    SPINNER_FRAMES,
)


class TestTaskStatus:
    """测试 TaskStatus 数据类。"""

    def test_task_status_init(self):
        """测试 TaskStatus 初始化。"""
        task = TaskStatus(
            name="test_task",
            display_name="Test Task",
            app="TestApp",
        )

        assert task.name == "test_task"
        assert task.display_name == "Test Task"
        assert task.app == "TestApp"
        assert task.status == "pending"
        assert task.current_step == 0

    def test_task_status_update(self):
        """测试 TaskStatus 更新。"""
        task = TaskStatus(name="test", display_name="Test", app="App")
        task.status = "running"
        task.current_step = 5
        task.current_action = "Clicking button"

        assert task.status == "running"
        assert task.current_step == 5
        assert task.current_action == "Clicking button"


class TestTUIState:
    """测试 TUIState 数据类。"""

    def test_tui_state_init(self):
        """测试 TUIState 初始化。"""
        state = TUIState()

        assert state.total_tasks == 0
        assert state.completed_tasks == 0
        assert state.failed_tasks == 0
        assert state.current_task == ""
        assert state.tasks == {}


class TestStatusSymbols:
    """测试状态符号。"""

    def test_status_symbols_exist(self):
        """测试状态符号存在。"""
        assert "pending" in STATUS_SYMBOLS
        assert "running" in STATUS_SYMBOLS
        assert "success" in STATUS_SYMBOLS
        assert "failure" in STATUS_SYMBOLS

    def test_status_symbols_not_empty(self):
        """测试状态符号不为空。"""
        for symbol in STATUS_SYMBOLS.values():
            assert len(symbol) > 0


class TestSpinnerFrames:
    """测试转圈动画帧。"""

    def test_spinner_frames_not_empty(self):
        """测试转圈动画帧不为空。"""
        assert len(SPINNER_FRAMES) > 0

    def test_spinner_frames_are_unicode(self):
        """测试转圈动画帧为 Unicode 字符。"""
        for frame in SPINNER_FRAMES:
            assert frame.isprintable() or ord(frame[0]) > 127


class TestSimpleTUI:
    """测试 SimpleTUI 类。"""

    def test_simple_tui_init(self):
        """测试 SimpleTUI 初始化。"""
        tui = SimpleTUI(total_tasks=3, total_steps=50)

        assert tui.total_tasks == 3
        assert tui.total_steps == 50
        assert tui.completed == 0
        assert tui.failed == 0

    def test_simple_tui_print_header(self, capsys):
        """测试 SimpleTUI 打印头部。"""
        tui = SimpleTUI(total_tasks=2, total_steps=50)
        tui.print_header()

        captured = capsys.readouterr()
        assert "DailyCheck Agent" in captured.out
        assert "█" in captured.out or "░" in captured.out

    def test_simple_tui_print_task_list(self, capsys):
        """测试 SimpleTUI 打印任务列表。"""
        tui = SimpleTUI(total_tasks=2)
        tasks = {
            "task1": {"status": "success", "display_name": "Task 1"},
            "task2": {"status": "pending", "display_name": "Task 2"},
        }
        tui.print_task_list(tasks)

        captured = capsys.readouterr()
        assert "Task 1" in captured.out
        assert "Task 2" in captured.out

    def test_simple_tui_print_step(self, capsys):
        """测试 SimpleTUI 打印步骤。"""
        tui = SimpleTUI(total_tasks=1, total_steps=50)
        tui.print_step(5, "Clicking button")

        captured = capsys.readouterr()
        assert "5/50" in captured.out
        assert "Clicking button" in captured.out


class TestTaskTUI:
    """测试 TaskTUI 类。"""

    def test_task_tui_init(self):
        """测试 TaskTUI 初始化。"""
        tui = TaskTUI(total_tasks=3, total_steps=50)

        assert tui.total_tasks == 3
        assert tui.total_steps == 50
        assert tui.state.total_tasks == 3
        assert not tui.state.running

    def test_task_tui_add_task(self):
        """测试 TaskTUI 添加任务。"""
        tui = TaskTUI(total_tasks=2)
        tui.add_task("task1", "Task 1", "App1")

        assert "task1" in tui.state.tasks
        assert tui.state.tasks["task1"].display_name == "Task 1"
        assert tui.state.tasks["task1"].app == "App1"

    def test_task_tui_start_task(self):
        """测试 TaskTUI 启动任务。"""
        tui = TaskTUI(total_tasks=1)
        tui.add_task("task1", "Task 1")
        tui.start_task("task1")

        assert tui.state.tasks["task1"].status == "running"
        assert tui.state.current_task == "task1"

    def test_task_tui_update_step(self):
        """测试 TaskTUI 更新步骤。"""
        tui = TaskTUI(total_tasks=1, total_steps=50)
        tui.add_task("task1", "Task 1")
        tui.start_task("task1")
        tui.update_step(5, "Clicking button", "Log message")

        assert tui.state.tasks["task1"].current_step == 5
        assert tui.state.tasks["task1"].current_action == "Clicking button"
        # Log message is prefixed with step number
        assert any("Log message" in log for log in tui.state.logs)

    def test_task_tui_complete_task_success(self):
        """测试 TaskTUI 完成任务（成功）。"""
        tui = TaskTUI(total_tasks=1)
        tui.add_task("task1", "Task 1")
        tui.start_task("task1")
        tui.complete_task("task1", success=True)

        assert tui.state.tasks["task1"].status == "success"
        assert tui.state.completed_tasks == 1
        assert tui.state.current_task == ""

    def test_task_tui_complete_task_failure(self):
        """测试 TaskTUI 完成任务（失败）。"""
        tui = TaskTUI(total_tasks=1)
        tui.add_task("task1", "Task 1")
        tui.start_task("task1")
        tui.complete_task("task1", success=False, error="Test error")

        assert tui.state.tasks["task1"].status == "failure"
        assert tui.state.failed_tasks == 1
        assert tui.state.tasks["task1"].error_message == "Test error"

    def test_task_tui_log(self):
        """测试 TaskTUI 日志。"""
        tui = TaskTUI(total_tasks=1)
        tui.log("Test log 1")
        tui.log("Test log 2")

        assert len(tui.state.logs) == 2
        assert "Test log 1" in tui.state.logs
        assert "Test log 2" in tui.state.logs

    def test_task_tui_log_max_limit(self):
        """测试 TaskTUI 日志最大限制。"""
        tui = TaskTUI(total_tasks=1)

        # 添加超过 20 条日志
        for i in range(25):
            tui.log(f"Log {i}")

        assert len(tui.state.logs) == 20

    def test_task_tui_context_manager(self):
        """测试 TaskTUI 上下文管理器。"""
        tui = TaskTUI(total_tasks=1)

        with tui:
            assert tui.state.running
            tui.add_task("task1", "Task 1")

        assert not tui.state.running

    def test_task_tui_set_error(self):
        """测试 TaskTUI 设置错误。"""
        tui = TaskTUI(total_tasks=1)
        tui.add_task("task1", "Task 1")
        tui.start_task("task1")
        tui.set_error("Critical error")

        assert tui.state.tasks["task1"].status == "failure"
        assert tui.state.tasks["task1"].error_message == "Critical error"
        assert tui.state.failed_tasks == 1

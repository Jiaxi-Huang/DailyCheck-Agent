"""TUI (Text User Interface) module for real-time task visualization.

This module provides a claude-code style terminal UI for displaying
task execution progress with spinner animation and detailed information.

Example:
    >>> tui = TaskTUI(total_tasks=5, total_steps=50)
    >>> tui.start()
    >>> tui.update_step(1, "Tap the icon")
    >>> tui.complete_task("task1", success=True)
    >>> tui.stop()
"""

from __future__ import annotations

import sys
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

# ANSI color codes
COLORS = {
    "reset": "\033[0m",
    "bold": "\033[1m",
    "dim": "\033[2m",
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    "white": "\033[37m",
    "bright_black": "\033[90m",
    "bright_red": "\033[91m",
    "bright_green": "\033[92m",
    "bright_yellow": "\033[93m",
    "bright_blue": "\033[94m",
    "bright_magenta": "\033[95m",
    "bright_cyan": "\033[96m",
    "bright_white": "\033[97m",
}

# Spinner characters
SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

# Status symbols
STATUS_SYMBOLS = {
    "pending": "○",
    "running": "●",
    "success": "✅",
    "failure": "❌",
    "warning": "⚠️",
}


@dataclass
class TaskStatus:
    """Task status information."""

    name: str
    display_name: str
    app: str
    status: str = "pending"  # pending, running, success, failure
    current_step: int = 0
    total_steps: int = 0
    current_action: str = ""
    last_log: str = ""
    error_message: str = ""


@dataclass
class TUIState:
    """TUI state information."""

    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    current_task: str = ""
    current_step: int = 0
    total_steps: int = 50
    current_action: str = ""
    spinner_index: int = 0
    tasks: Dict[str, TaskStatus] = field(default_factory=dict)
    running: bool = False
    logs: List[str] = field(default_factory=list)


class TaskTUI:
    """Task Text User Interface for real-time visualization.

    Displays a claude-code style interface with:
    - Spinner animation
    - Task progress (e.g., 2/50 steps)
    - Current action description
    - Task list with status

    Attributes:
        total_tasks: Total number of tasks to execute
        total_steps: Maximum steps per task
        refresh_rate: Screen refresh rate in seconds

    Example:
        >>> tui = TaskTUI(total_tasks=3, total_steps=50)
        >>> with tui:
        ...     tui.start_task("task1")
        ...     tui.update_step(5, "Tapping button")
        ...     tui.complete_task("task1", success=True)
    """

    def __init__(
        self,
        total_tasks: int = 1,
        total_steps: int = 50,
        refresh_rate: float = 0.1,
        show_logs: bool = True,
    ):
        """Initialize TaskTUI.

        Args:
            total_tasks: Total number of tasks to execute
            total_steps: Maximum steps per task
            refresh_rate: Screen refresh rate in seconds
            show_logs: Whether to show log output
        """
        self.total_tasks = total_tasks
        self.total_steps = total_steps
        self.refresh_rate = refresh_rate
        self.show_logs = show_logs
        self.state = TUIState()
        self.state.total_tasks = total_tasks
        self.state.total_steps = total_steps
        self._spinner_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._output_lock = threading.Lock()
        self._cursor_hidden = False

    def __enter__(self) -> "TaskTUI":
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()

    def start(self) -> None:
        """Start the TUI display."""
        self.state.running = True
        self._hide_cursor()
        self._clear_screen()
        # Start spinner thread
        self._stop_event.clear()
        self._spinner_thread = threading.Thread(
            target=self._spinner_loop, daemon=True
        )
        self._spinner_thread.start()

    def stop(self) -> None:
        """Stop the TUI display."""
        self.state.running = False
        self._stop_event.set()
        if self._spinner_thread:
            self._spinner_thread.join(timeout=1.0)
        self._show_cursor()
        print(COLORS["reset"], end="")
        sys.stdout.flush()

    def _hide_cursor(self) -> None:
        """Hide the terminal cursor."""
        if not self._cursor_hidden:
            print("\033[?25l", end="", flush=True)
            self._cursor_hidden = True

    def _show_cursor(self) -> None:
        """Show the terminal cursor."""
        if self._cursor_hidden:
            print("\033[?25h", end="", flush=True)
            self._cursor_hidden = False

    def _clear_screen(self) -> None:
        """Clear the terminal screen."""
        print("\033[2J\033[H", end="", flush=True)

    def _clear_line(self) -> None:
        """Clear the current line."""
        print("\033[2K", end="", flush=True)

    def _spinner_loop(self) -> None:
        """Spinner animation loop."""
        while not self._stop_event.is_set():
            with self._output_lock:
                self.state.spinner_index += 1
                self._render()
            time.sleep(self.refresh_rate)

    def _render(self) -> None:
        """Render the current state to terminal."""
        # Clear screen and move cursor to home position
        print("\033[2J\033[H", end="", flush=True)

        # Header
        self._render_header()

        # Task list
        self._render_task_list()

        # Current task detail
        self._render_current_task()

        # Logs
        if self.show_logs:
            self._render_logs()

        # Clear remaining lines from previous render
        print("\033[J", end="", flush=True)

        sys.stdout.flush()

    def _render_header(self) -> None:
        """Render the header section."""
        completed = self.state.completed_tasks
        failed = self.state.failed_tasks
        total = self.state.total_tasks
        progress = completed + failed

        # Progress bar
        bar_width = 30
        if total > 0:
            filled = int(bar_width * progress / total)
            bar = "█" * filled + "░" * (bar_width - filled)
        else:
            bar = "░" * bar_width

        print(f"{COLORS['bold']}DailyCheck Agent{COLORS['reset']}\n")
        print(
            f"[{COLORS['green']}{bar}{COLORS['reset']}] "
            f"{COLORS['bright_green']}{completed}{COLORS['reset']}/"
            f"{COLORS['bright_red']}{failed}{COLORS['reset']}/"
            f"{COLORS['dim']}{total}{COLORS['reset']}\n"
        )

    def _render_task_list(self) -> None:
        """Render the task list section."""
        print(f"{COLORS['bold']}Tasks:{COLORS['reset']}")

        for task_name, task in self.state.tasks.items():
            symbol = STATUS_SYMBOLS.get(task.status, "○")
            color = self._get_status_color(task.status)

            if task_name == self.state.current_task:
                # Highlight current task
                print(
                    f"  {COLORS['bold']}{COLORS['cyan']}▶ {symbol} {task.display_name}{COLORS['reset']}"
                )
                if task.current_action:
                    print(
                        f"    {COLORS['dim']}  {task.current_action[:60]}{COLORS['reset']}"
                    )
            else:
                print(f"  {color}{symbol} {task.display_name}{COLORS['reset']}")

        print()

    def _render_current_task(self) -> None:
        """Render the current task detail section."""
        if not self.state.current_task:
            return

        task = self.state.tasks.get(self.state.current_task)
        if not task or task.status != "running":
            return

        spinner = SPINNER_FRAMES[self.state.spinner_index % len(SPINNER_FRAMES)]
        step = task.current_step
        total = self.state.total_steps

        print(f"{COLORS['bold']}Progress:{COLORS['reset']}")
        action_display = task.current_action[:80] if task.current_action else ""
        print(
            f"  {COLORS['yellow']}{spinner}{COLORS['reset']} "
            f"{COLORS['bright_cyan']}{step}/{total}{COLORS['reset']} "
            f"{COLORS['bold']}{action_display}{COLORS['reset']}"
        )

        if task.last_log:
            print(f"  {COLORS['dim']}  {task.last_log[:80]}{COLORS['reset']}")

        print()

    def _render_logs(self) -> None:
        """Render the logs section."""
        if not self.state.logs:
            return

        print(f"{COLORS['bold']}Logs:{COLORS['reset']}")
        # Show last 5 logs
        for log in self.state.logs[-5:]:
            print(f"  {COLORS['dim']}│{COLORS['reset']} {log[:90]}")
        print()

    def _get_status_color(self, status: str) -> str:
        """Get color code for status."""
        colors = {
            "pending": COLORS["dim"],
            "running": COLORS["yellow"],
            "success": COLORS["green"],
            "failure": COLORS["red"],
            "warning": COLORS["yellow"],
        }
        return colors.get(status, COLORS["reset"])

    def add_task(
        self,
        task_name: str,
        display_name: str = "",
        app: str = "",
    ) -> None:
        """Add a task to the TUI.

        Args:
            task_name: Internal task name
            display_name: Display name for the task
            app: Target application name
        """
        task = TaskStatus(
            name=task_name,
            display_name=display_name or task_name,
            app=app or "Unknown",
        )
        self.state.tasks[task_name] = task

    def start_task(self, task_name: str) -> None:
        """Mark a task as running.

        Args:
            task_name: Task name to start
        """
        if task_name in self.state.tasks:
            self.state.tasks[task_name].status = "running"
            self.state.current_task = task_name

    def update_step(
        self, step: int, action: str = "", log: str = ""
    ) -> None:
        """Update the current step and action.

        Args:
            step: Current step number
            action: Current action description
            log: Optional log message
        """
        self.state.current_step = step
        if self.state.current_task and self.state.current_task in self.state.tasks:
            task = self.state.tasks[self.state.current_task]
            task.current_step = step
            if action:
                task.current_action = action
            if log:
                task.last_log = log
                self.state.logs.append(f"Step {step}: {log}")
                # Keep only last 20 logs
                self.state.logs = self.state.logs[-20:]

    def complete_task(
        self, task_name: str, success: bool, error: str = ""
    ) -> None:
        """Mark a task as completed.

        Args:
            task_name: Task name to complete
            success: Whether the task succeeded
            error: Error message if failed
        """
        if task_name in self.state.tasks:
            task = self.state.tasks[task_name]
            task.status = "success" if success else "failure"
            task.error_message = error
            if success:
                self.state.completed_tasks += 1
            else:
                self.state.failed_tasks += 1

        if self.state.current_task == task_name:
            self.state.current_task = ""

        # Trigger immediate render to update display
        if self.state.running:
            with self._output_lock:
                self.state.spinner_index += 1
                self._render()

    def log(self, message: str) -> None:
        """Add a log message.

        Args:
            message: Log message
        """
        self.state.logs.append(message)
        self.state.logs = self.state.logs[-20:]

    def set_error(self, error: str) -> None:
        """Set the current error message.

        Args:
            error: Error message
        """
        if self.state.current_task and self.state.current_task in self.state.tasks:
            self.state.tasks[self.state.current_task].error_message = error
            self.state.tasks[self.state.current_task].status = "failure"
            self.state.failed_tasks += 1
            self.state.current_task = ""


class SimpleTUI:
    """Simple TUI for basic progress display without threading.

    This is a simpler version that doesn't use a separate thread
    for rendering, suitable for environments where threading is problematic.

    Example:
        >>> tui = SimpleTUI(total_tasks=3)
        >>> tui.print_header()
        >>> tui.print_task_list(tasks)
        >>> tui.print_step(5, 50, "Tapping button")
    """

    def __init__(self, total_tasks: int = 1, total_steps: int = 50):
        """Initialize SimpleTUI.

        Args:
            total_tasks: Total number of tasks
            total_steps: Maximum steps per task
        """
        self.total_tasks = total_tasks
        self.total_steps = total_steps
        self.completed = 0
        self.failed = 0
        self.current_task = ""
        self.current_step = 0

    def print_header(self) -> None:
        """Print the header section."""
        progress = self.completed + self.failed
        bar_width = 30
        filled = (
            int(bar_width * progress / self.total_tasks)
            if self.total_tasks > 0
            else 0
        )
        bar = "█" * filled + "░" * (bar_width - filled)

        print(
            f"\n{COLORS['bold']}DailyCheck Agent{COLORS['reset']}\n"
            f"[{COLORS['green']}{bar}{COLORS['reset']}] "
            f"{COLORS['bright_green']}{self.completed}{COLORS['reset']}/"
            f"{COLORS['bright_red']}{self.failed}{COLORS['reset']}/"
            f"{COLORS['dim']}{self.total_tasks}{COLORS['reset']}\n"
        )

    def print_task_list(
        self, tasks: Dict[str, Dict[str, Any]]
    ) -> None:
        """Print the task list.

        Args:
            tasks: Dictionary of task statuses
        """
        print(f"{COLORS['bold']}Tasks:{COLORS['reset']}")
        for name, info in tasks.items():
            status = info.get("status", "pending")
            symbol = STATUS_SYMBOLS.get(status, "○")
            color = self._get_status_color(status)
            display = info.get("display_name", name)

            marker = "▶ " if name == self.current_task else "  "
            print(f"  {marker}{color}{symbol} {display}{COLORS['reset']}")
        print()

    def print_step(self, step: int, action: str = "") -> None:
        """Print the current step.

        Args:
            step: Current step number
            action: Current action description
        """
        self.current_step = step
        spinner = SPINNER_FRAMES[step % len(SPINNER_FRAMES)]
        print(
            f"{COLORS['bold']}Progress:{COLORS['reset']} "
            f"{COLORS['yellow']}{spinner}{COLORS['reset']} "
            f"{COLORS['bright_cyan']}{step}/{self.total_steps}{COLORS['reset']} "
            f"{COLORS['bold']}{action}{COLORS['reset']}\n"
        )

    def _get_status_color(self, status: str) -> str:
        """Get color code for status."""
        colors = {
            "pending": COLORS["dim"],
            "running": COLORS["yellow"],
            "success": COLORS["green"],
            "failure": COLORS["red"],
        }
        return colors.get(status, COLORS["reset"])

    def clear_lines(self, n: int = 10) -> None:
        """Clear n lines from cursor position.

        Args:
            n: Number of lines to clear
        """
        for _ in range(n):
            print("\033[2K\033[E", end="", flush=True)
        print("\033[F" * n, end="", flush=True)

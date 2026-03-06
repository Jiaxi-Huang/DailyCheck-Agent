"""DailyCheck-Agent 命令行入口."""

import argparse
import logging
import sys
import time
from pathlib import Path

import yaml

from dailycheck_agent.lib.config_loader import (
    APIProviderNotFoundError,
    ConfigLoader,
    ConfigValidationError,
)
from dailycheck_agent.lib.tui import COLORS, TaskTUI
from dailycheck_agent.main import DailyCheckAgent


# Configure logging to file during TUI execution
LOG_FILE = Path.home() / ".dailycheck" / "logs" / "dailycheck.log"
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)


def load_yaml(file_path: str) -> dict:
    """加载 YAML 文件。

    Args:
        file_path: 文件路径

    Returns:
        配置字典，如果路径为空或文件不存在返回空字典
    """
    if not file_path:
        return {}

    file_obj = Path(file_path)
    if not file_obj.exists():
        return {}

    with open(file_obj, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_config_value(config: dict, key: str, default: str = "") -> str:
    """获取配置值，优先级：配置文件 > 默认值。

    Args:
        config: 配置字典
        key: 配置键名
        default: 默认值

    Returns:
        配置值
    """
    if key in config:
        return str(config[key])
    return default


def load_tasks_config(config_dir: str) -> dict:
    """加载任务配置文件。

    Args:
        config_dir: 配置文件目录

    Returns:
        任务配置字典
    """
    try:
        loader = ConfigLoader(config_dir=config_dir if config_dir else None)
        return loader.get_all_tasks()
    except Exception:
        package_tasks = Path(__file__).parent.parent / "config" / "tasks.yml"
        if package_tasks.exists():
            with open(package_tasks, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                return data.get("tasks", {})
        return {}


def main():
    """命令行入口函数."""
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "--config", "-c", default="", help="配置文件路径（YAML 格式）"
    )
    args, remaining = config_parser.parse_known_args()

    parser = argparse.ArgumentParser(
        prog="dailycheck",
        description="DailyCheck-Agent - 自动化打卡任务代理",
        parents=[config_parser],
    )
    parser.add_argument(
        "task_name",
        nargs="?",
        default="",
        help="任务名称（在 tasks.yml 中定义），不指定则执行所有任务",
    )
    parser.add_argument(
        "--api-provider", "-a", dest="api_provider", default="open-router",
        help="API 提供商名称，默认：open-router"
    )
    parser.add_argument(
        "--device-serial", "-d", dest="device_serial", default="",
        help="设备序列号，默认：自动检测"
    )
    parser.add_argument(
        "--adb-path", dest="adb_path", default=f"{Path.cwd()}/scrcpy/adb",
        help="ADB 可执行文件路径"
    )
    parser.add_argument(
        "--max-steps", "-m", dest="max_steps", type=int, default=50,
        help="最大执行步骤数，默认：50"
    )
    parser.add_argument(
        "--config-dir", dest="config_dir", default=f"{Path.cwd()}/config/",
        help="配置文件目录"
    )
    parser.add_argument(
        "--list-tasks", "-l", action="store_true", help="列出所有可用任务"
    )
    parser.add_argument(
        "--version", "-v", action="version", version="dailycheck-agent 0.1.0"
    )

    args = parser.parse_args(remaining)

    config_dir = args.config_dir
    tasks_config = load_tasks_config(config_dir)

    # List tasks
    if args.list_tasks:
        task_names = []
        app_names = []
        for task_id, task_info in tasks_config.items():
            task_names.append(task_info.get("name", "未知"))
            app_names.append(task_info.get("app", "未知"))
        print_task_list_tui(task_names, app_names)
        sys.exit(0)

    # Get config values
    api_provider = args.api_provider
    device_serial = args.device_serial
    adb_path = args.adb_path
    max_steps = args.max_steps

    # Check ADB path
    if not Path(adb_path).exists():
        adb_path = "adb"

    # Determine tasks to run
    if args.task_name:
        task_names = [args.task_name]
    else:
        task_names = list(tasks_config.keys())

    if not task_names:
        print("❌ 错误：没有找到任何任务")
        print("  请确保 config/tasks.yml 中存在任务定义")
        sys.exit(1)

    # Create TUI
    tui = TaskTUI(total_tasks=len(task_names), total_steps=max_steps)

    # Add tasks to TUI
    for name in task_names:
        task_info = tasks_config.get(name, {})
        tui.add_task(
            task_name=name,
            display_name=task_info.get("name", name),
            app=task_info.get("app", "Unknown"),
        )

    # TUI callback
    def tui_callback(event_type: str, data: dict):
        if event_type == "task_start":
            task_name = data.get("task_name")
            if task_name:
                tui.start_task(task_name)
        elif event_type == "step_update":
            tui.update_step(step=data.get("step", 0), action=data.get("action", ""))
        elif event_type == "action_executed":
            tool = data.get("tool", "")
            args_data = data.get("args", {})
            # Format args as a simple string, not raw dict
            if args_data:
                args_str = ", ".join(f"{k}={v}" for k, v in args_data.items() if not k.startswith("_"))
                action_text = f"{tool}({args_str})"
            else:
                action_text = f"{tool}()"
            tui.update_step(
                step=tui.state.current_step,
                action=action_text,
                log=f"Executed {tool}",
            )
        elif event_type == "task_error":
            tui.set_error(data.get("error", "Unknown error"))

    # Print banner
    print_banner()
    print()

    # Configure logging to file (only if not already configured)
    if not logging.getLogger().handlers:
        # File handler - all logs
        file_handler = logging.FileHandler(str(LOG_FILE), mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        
        # Console handler - only errors
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.ERROR)
        console_handler.setFormatter(logging.Formatter(
            "%(levelname)s: %(message)s"
        ))
        
        logging.root.setLevel(logging.DEBUG)
        logging.root.addHandler(file_handler)
        logging.root.addHandler(console_handler)
        
    logger = logging.getLogger("dailycheck")
    logger.info(f"Starting DailyCheck-Agent, task: {task_names}")

    # Validate API configuration before starting TUI
    try:
        loader = ConfigLoader(config_dir=config_dir)
        _ = loader.get_api_key(api_provider)
    except ValueError as e:
        # API key not configured
        print(f"\n{COLORS['red']}❌ 错误：{e}{COLORS['reset']}\n")
        sys.exit(1)
    except APIProviderNotFoundError as e:
        print(f"\n{COLORS['red']}❌ 错误：{e}{COLORS['reset']}\n")
        sys.exit(1)
    except ConfigValidationError as e:
        print(f"\n{COLORS['red']}❌ 错误：配置文件验证失败{COLORS['reset']}")
        print(f"   {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n{COLORS['red']}❌ 错误：无法加载 API 配置：{e}{COLORS['reset']}\n")
        sys.exit(1)

    # Start TUI
    tui.start()

    results = []
    for task_name in task_names:
        if task_name not in tasks_config:
            tui.complete_task(task_name, success=False, error="Task not found")
            results.append((task_name, False))
            continue

        try:
            agent = DailyCheckAgent(
                task_name=task_name,
                adb_path=adb_path,
                device_serial=device_serial if device_serial else None,
                api_provider=api_provider,
                config_dir=config_dir,
                max_steps=max_steps,
                callback=tui_callback,
            )
            success = agent.run()
            results.append((task_name, success))

            # Mark task as complete (success or failure)
            tui.complete_task(task_name, success=success, error="" if success else "Agent run failed")

        except ValueError as e:
            # API configuration error during agent initialization
            error_msg = f"API 配置错误：{e}"
            tui.complete_task(task_name, success=False, error=error_msg)
            results.append((task_name, False))
            # Stop processing remaining tasks on API config error
            print(f"\n{COLORS['red']}❌ {error_msg}{COLORS['reset']}")
            break
        except Exception as e:
            tui.complete_task(task_name, success=False, error=str(e))
            results.append((task_name, False))

    # Brief pause to allow final render to complete
    time.sleep(0.2)

    # Stop TUI
    tui.stop()

    # Print summary
    print_summary(results)

    sys.exit(0 if sum(1 for _, s in results if s) == len(results) else 1)


def print_banner():
    """打印欢迎横幅."""
    BOLD = "\033[1m"
    WHITE = "\033[0;37m"
    NC = "\033[0m"

    banner = (
        f"{WHITE}{BOLD} ██████╗  █████╗ ██╗██╗  ██╗   ██╗ ██████╗██╗  ██╗███████╗ ██████╗██╗  ██╗     █████╗  ██████╗ ███████╗███╗   ██╗████████╗{NC}\n"
        f"{WHITE}{BOLD} ██╔══██╗██╔══██╗██║██║  ╚██╗ ██╔╝██╔════╝██║  ██║██╔════╝██╔════╝██║ ██╔╝    ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝{NC}\n"
        f"{WHITE}{BOLD} ██║  ██║███████║██║██║   ╚████╔╝ ██║     ███████║█████╗  ██║     █████╔╝     ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║   {NC}\n"
        f"{WHITE}{BOLD} ██║  ██║██╔══██║██║██║    ╚██╔╝  ██║     ██╔══██║██╔══╝  ██║     ██╔═██╗     ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║   {NC}\n"
        f"{WHITE}{BOLD} ██████╔╝██║  ██║██║███████╗██║   ╚██████╗██║  ██║███████╗╚██████╗██║  ██╗    ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║   {NC}\n"
        f"{WHITE}{BOLD} ╚═════╝ ╚═╝  ╚═╝╚═╝╚══════╝╚═╝    ╚═════╝╚═╝  ╚═╝╚══════╝ ╚═════╝╚═╝  ╚═╝    ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝   {NC}"
    )
    print(banner)


def print_task_list_tui(task_names, app_names):
    """打印任务列表（TUI 风格）."""
    BOLD = "\033[1m"
    BLUE = "\033[0;34m"
    NC = "\033[0m"

    print(f"{BOLD}任务列表:{NC}\n")
    for task_name, app_name in zip(task_names, app_names):
        print(f"  {BLUE}●{NC} {task_name} ({app_name})")
    print()


def print_summary(results):
    """打印执行总结。"""
    BOLD = "\033[1m"
    GREEN = "\033[0;32m"
    RED = "\033[0;31m"
    DIM = "\033[2m"
    NC = "\033[0m"

    print(f"\n{BOLD}{'='*60}{NC}")
    print(f"{BOLD}任务执行总结{NC}")
    print(f"{BOLD}{'='*60}{NC}\n")

    success_count = sum(1 for _, success in results if success)
    total_count = len(results)

    for task_name, success in results:
        status = f"{GREEN}✅{NC}" if success else f"{RED}❌{NC}"
        print(f"  {status} {task_name}")

    print(f"\n{BOLD}总计：{NC}{success_count}/{total_count} 任务成功")

    if success_count == total_count:
        print(f"\n{GREEN}🎉 所有任务执行成功!{NC}")
    elif success_count > 0:
        print(f"\n{DIM}部分任务失败，请检查日志{NC}")
    else:
        print(f"\n{RED}所有任务执行失败{NC}")
    print()


if __name__ == "__main__":
    main()

"""DailyCheck-Agent 命令行入口."""

import argparse
import os
import sys
from pathlib import Path

import yaml


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


def get_config_value(config: dict, key: str, env_var: str, default: str = "") -> str:
    """获取配置值，优先级：环境变量 > 配置文件 > 默认值。

    Args:
        config: 配置字典
        key: 配置键名
        env_var: 环境变量名
        default: 默认值

    Returns:
        配置值
    """
    # 环境变量优先级最高
    env_value = os.environ.get(env_var)
    if env_value:
        return env_value

    # 其次从配置文件读取
    if key in config:
        return str(config[key])

    # 返回默认值
    return default


def load_tasks_config(config_dir: str) -> dict:
    """加载任务配置文件。

    Args:
        config_dir: 配置文件目录

    Returns:
        任务配置字典
    """
    tasks_file = Path(config_dir) / "tasks.yml" if config_dir else Path("config") / "tasks.yml"
    if not tasks_file.exists():
        # 尝试从包目录查找
        package_tasks = Path(__file__).parent.parent / "config" / "tasks.yml"
        if package_tasks.exists():
            tasks_file = package_tasks
        else:
            return {}

    with open(tasks_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
        return data.get("tasks", {})


def main():
    """命令行入口函数."""
    # 先解析 --config 参数，用于指定配置文件路径
    config_parser = argparse.ArgumentParser(add_help=False)
    config_parser.add_argument(
        "--config",
        "-c",
        default="",
        help="配置文件路径（YAML 格式）",
    )
    args, remaining = config_parser.parse_known_args()

    # 加载用户配置文件
    config_path = args.config if args.config else os.environ.get("DAILYCHECK_CONFIG", "")
    if not config_path:
        # 默认在当前目录或项目目录查找 config.yml
        default_config_paths = [
            Path.cwd() / "config.yml",
            Path.cwd() / ".dailycheck.yml",
            Path.home() / ".dailycheck" / "config.yml",
        ]
        for p in default_config_paths:
            if p.exists():
                config_path = str(p)
                break

    user_config = load_yaml(config_path) if config_path else {}

    # 主参数解析器
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
        "--api-provider",
        "-a",
        dest="api_provider",
        default="",
        help="API 提供商名称，默认：open-router",
    )
    parser.add_argument(
        "--device-serial",
        "-d",
        dest="device_serial",
        default="",
        help="设备序列号，默认：自动检测",
    )
    parser.add_argument(
        "--adb-path",
        dest="adb_path",
        default="",
        help="ADB 可执行文件路径",
    )
    parser.add_argument(
        "--max-steps",
        "-m",
        dest="max_steps",
        type=int,
        default=0,
        help="最大执行步骤数，默认：50",
    )
    parser.add_argument(
        "--config-dir",
        dest="config_dir",
        default="",
        help="配置文件目录（tasks.yml 和 api.yml 所在目录）",
    )
    parser.add_argument(
        "--list-tasks",
        "-l",
        action="store_true",
        help="列出所有可用任务",
    )
    parser.add_argument(
        "--version",
        "-v",
        action="version",
        version="dailycheck-agent 0.1.0",
    )

    args = parser.parse_args(remaining)

    # 确定配置目录
    config_dir = args.config_dir if args.config_dir else get_config_value(user_config, "config_dir", "DAILYCHECK_CONFIG_DIR", "")
    if not config_dir:
        # 默认使用项目 config 目录
        config_dir = str(Path(__file__).parent.parent / "config")

    # 加载任务配置
    tasks_config = load_tasks_config(config_dir)

    # 列出所有任务
    if args.list_tasks:
        print("可用任务列表:")
        for task_name, task_info in tasks_config.items():
            app_name = task_info.get("app", "未知")
            print(f"  - {task_name} ({app_name})")
        sys.exit(0)

    # 获取配置值，优先级：命令行参数 > 环境变量 > 配置文件 > 默认值
    api_provider = args.api_provider if args.api_provider else get_config_value(user_config, "api_provider", "DAILYCHECK_API_PROVIDER", "open-router")
    device_serial = args.device_serial if args.device_serial else get_config_value(user_config, "device_serial", "DAILYCHECK_DEVICE_SERIAL", "")
    adb_path = args.adb_path if args.adb_path else get_config_value(user_config, "adb_path", "ADB_PATH", "")
    max_steps = args.max_steps if args.max_steps > 0 else int(get_config_value(user_config, "max_steps", "MAX_STEPS", "50"))

    # 获取脚本所在目录（用于查找默认的 ADB 路径）
    script_dir = Path(__file__).parent.parent
    default_adb_path = script_dir / "scrcpy" / "adb"

    # 确定 ADB 路径优先级：命令行参数 > 配置文件/环境变量 > 默认路径 > 系统 adb
    if not adb_path:
        if default_adb_path.exists():
            adb_path = str(default_adb_path)
        else:
            adb_path = "adb"

    # 打印欢迎信息
    print_banner()

    # 检查 ADB 路径
    if not Path(adb_path).exists():
        print(f"⚠ 警告：ADB 文件不存在：{adb_path}")
        print("  将尝试使用系统 PATH 中的 adb")
        adb_path = "adb"

    # 检查 API 密钥
    if not os.environ.get("DAILYCHECK_API_KEY"):
        print("⚠ 警告：未设置 DAILYCHECK_API_KEY 环境变量")
        print("  请确保在 config/api.yml 中配置了有效的 API 密钥")

    # 确定要执行的任务
    if args.task_name:
        # 指定了单个任务
        task_names = [args.task_name]
    else:
        # 未指定任务，执行所有任务
        task_names = list(tasks_config.keys())

    if not task_names:
        print("❌ 错误：没有找到任何任务")
        print("  请确保 config/tasks.yml 中存在任务定义")
        sys.exit(1)

    # 打印配置信息
    print_config(task_names, api_provider, device_serial or "自动检测", adb_path, max_steps)

    # 导入并运行代理
    from dailycheck_agent.main import DailyCheckAgent

    results = []
    for task_name in task_names:
        # 验证任务是否存在
        if task_name not in tasks_config:
            print(f"❌ 错误：任务 '{task_name}' 不存在")
            print(f"  可用任务：{', '.join(tasks_config.keys())}")
            continue

        print(f"\n{'='*60}")
        print(f"开始执行任务：{task_name}")
        print(f"{'='*60}\n")

        try:
            agent = DailyCheckAgent(
                task_name=task_name,
                adb_path=adb_path,
                device_serial=device_serial if device_serial else None,
                api_provider=api_provider,
                config_dir=config_dir,
                max_steps=max_steps,
            )
            success = agent.run()
            results.append((task_name, success))

            if success:
                print(f"✅ 任务完成：{task_name}")
            else:
                print(f"❌ 任务失败：{task_name}")

        except Exception as e:
            print(f"❌ 运行失败：{task_name} - {e}")
            results.append((task_name, False))

    # 打印总结
    print(f"\n{'='*60}")
    print("任务执行总结")
    print(f"{'='*60}")
    success_count = sum(1 for _, success in results if success)
    total_count = len(results)
    for task_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {task_name}")
    print(f"\n总计：{success_count}/{total_count} 任务成功")

    sys.exit(0 if success_count == total_count else 1)


def print_banner():
    """打印欢迎横幅."""
    BOLD = "\033[1m"
    CYAN = "\033[0;36m"
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


def print_config(task_names, api_provider, device_serial, adb_path, max_steps):
    """打印配置信息."""
    BOLD = "\033[1m"
    BLUE = "\033[0;34m"
    DIM = "\033[2m"
    NC = "\033[0m"

    print(f"{BOLD}配置信息:{NC}")
    if len(task_names) == 1:
        print(f"  {BLUE}●{NC} 任务名称：{BOLD}{task_names[0]}{NC}")
    else:
        print(f"  {BLUE}●{NC} 任务列表：{BOLD}{', '.join(task_names)}{NC}")
    print(f"  {BLUE}●{NC} API 提供商：{api_provider}")
    print(f"  {BLUE}●{NC} 设备序列号：{DIM}{device_serial}{NC}")
    print(f"  {BLUE}●{NC} ADB 路径：{DIM}{adb_path}{NC}")
    print(f"  {BLUE}●{NC} 最大步骤数：{max_steps}")
    print()


if __name__ == "__main__":
    main()

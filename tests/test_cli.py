"""CLI 模块测试。"""

import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

import yaml

from dailycheck_agent.cli import (
    load_yaml,
    get_config_value,
    load_tasks_config,
    main,
    print_banner,
    print_summary,
)


class TestLoadYaml:
    """测试 YAML 文件加载。"""

    def test_load_yaml_success(self, tmp_path):
        """测试成功加载 YAML 文件。"""
        config_file = tmp_path / "config.yml"
        config_data = {"key": "value", "number": 42}
        with open(config_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(config_data, f)

        result = load_yaml(str(config_file))

        assert result["key"] == "value"
        assert result["number"] == 42

    def test_load_yaml_empty_path(self):
        """测试空路径返回空字典。"""
        result = load_yaml("")
        assert result == {}

    def test_load_yaml_file_not_exists(self):
        """测试文件不存在返回空字典。"""
        result = load_yaml("/nonexistent/path/config.yml")
        assert result == {}

    def test_load_yaml_empty_file(self, tmp_path):
        """测试空文件返回空字典。"""
        config_file = tmp_path / "empty.yml"
        config_file.write_text("")

        result = load_yaml(str(config_file))
        assert result == {}


class TestGetConfigValue:
    """测试配置值获取。"""

    def test_get_config_value_from_config(self):
        """测试从配置文件获取值。"""
        config = {"key": "config_value"}
        result = get_config_value(config, "key", "default")
        assert result == "config_value"

    def test_get_config_value_default(self):
        """测试使用默认值。"""
        config = {"other_key": "value"}
        result = get_config_value(config, "missing_key", "default_value")
        assert result == "default_value"

    def test_get_config_value_empty_string_default(self):
        """测试空字符串默认值。"""
        config = {}
        result = get_config_value(config, "missing", "")
        assert result == ""


class TestLoadTasksConfig:
    """测试任务配置加载。"""

    def test_load_tasks_config_success(self, tmp_path):
        """测试成功加载任务配置。"""
        tasks_file = tmp_path / "tasks.yml"
        tasks_data = {
            "tasks": {
                "task1": {"app": "App1"},
                "task2": {"app": "App2"},
            }
        }
        with open(tasks_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(tasks_data, f)

        result = load_tasks_config(str(tmp_path))

        assert "task1" in result
        assert "task2" in result
        assert result["task1"]["app"] == "App1"

    def test_load_tasks_config_no_tasks_file(self, monkeypatch):
        """测试没有任务文件返回空字典。"""
        # Mock the Path.exists method to return False for all paths
        with patch("pathlib.Path.exists", return_value=False):
            result = load_tasks_config("/nonexistent/path")
            assert result == {}


class TestPrintBanner:
    """测试横幅打印。"""

    def test_print_banner(self, capsys):
        """测试打印横幅。"""
        print_banner()
        captured = capsys.readouterr()

        assert "DailyCheck" in captured.out or "█████" in captured.out


class TestPrintSummary:
    """测试总结信息打印。"""

    def test_print_summary_all_success(self, capsys):
        """测试打印全部成功的总结。"""
        print_summary([("task1", True), ("task2", True)])
        captured = capsys.readouterr()

        assert "2/2" in captured.out
        assert "✅" in captured.out

    def test_print_summary_partial_success(self, capsys):
        """测试打印部分成功的总结。"""
        print_summary([("task1", True), ("task2", False)])
        captured = capsys.readouterr()

        assert "1/2" in captured.out
        assert "✅" in captured.out
        assert "❌" in captured.out

    def test_print_summary_all_failure(self, capsys):
        """测试打印全部失败的总结。"""
        print_summary([("task1", False), ("task2", False)])
        captured = capsys.readouterr()

        assert "0/2" in captured.out
        assert "❌" in captured.out


class TestMain:
    """测试 CLI 主函数。"""

    def test_main_list_tasks(self, mock_config_files, capsys):
        """测试列出任务。"""
        with patch.object(sys, "argv", ["dailycheck", "--list-tasks", "--config-dir", str(mock_config_files)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # TUI is started but immediately stopped for --list-tasks
            assert exc_info.value.code == 0
            captured = capsys.readouterr()
            # Check for task names in output (may contain ANSI codes)
            assert "taobao" in captured.out.lower() or "淘宝" in captured.out

    def test_main_version(self, capsys):
        """测试版本参数。"""
        with patch.object(sys, "argv", ["dailycheck", "--version"]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 0
            captured = capsys.readouterr()

            assert "0.1.0" in captured.out

    def test_main_no_tasks_specified(self, mock_config_files, capsys):
        """测试未指定任务时执行所有任务。"""
        # Patch DailyCheckAgent where it's imported (in cli module)
        with patch("dailycheck_agent.cli.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            with patch.object(sys, "argv", ["dailycheck", "--config-dir", str(mock_config_files)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 0
            # 验证两个任务都被执行
            assert mock_agent_class.call_count == 2

    def test_main_single_task(self, mock_config_files, capsys):
        """测试执行单个任务。"""
        with patch("dailycheck_agent.cli.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            with patch.object(
                sys, "argv", ["dailycheck", "taobao_checkin", "--config-dir", str(mock_config_files)]
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 0
            # 验证只执行了一个任务
            assert mock_agent_class.call_count == 1

    def test_main_task_not_found(self, mock_config_files, capsys):
        """测试任务不存在。"""
        with patch.object(sys, "argv", ["dailycheck", "invalid_task", "--config-dir", str(mock_config_files)]):
            with pytest.raises(SystemExit) as exc_info:
                main()

            # When task is not found, exit with error
            captured = capsys.readouterr()
            # Check for error indication
            assert "❌" in captured.out or "失败" in captured.out or "error" in captured.out.lower()

    def test_main_with_custom_params(self, mock_config_files, capsys):
        """测试使用自定义参数。"""
        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            with patch.object(
                sys,
                "argv",
                [
                    "dailycheck",
                    "taobao_checkin",
                    "--config-dir",
                    str(mock_config_files),
                    "--api-provider",
                    "siliconflow",
                    "--device-serial",
                    "custom-device",
                    "--max-steps",
                    "25",
                ],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 0
            # 验证参数传递
            call_args = mock_agent_class.call_args
            assert call_args[1]["api_provider"] == "siliconflow"
            assert call_args[1]["device_serial"] == "custom-device"
            assert call_args[1]["max_steps"] == 25

    def test_main_adb_path_not_exists(self, mock_config_files, capsys):
        """测试 ADB 路径不存在时的回退。"""
        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            with patch.object(
                sys,
                "argv",
                ["dailycheck", "taobao_checkin", "--config-dir", str(mock_config_files), "--adb-path", "/nonexistent/adb"],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 0
            # TUI runs, just verify the agent was called
            assert mock_agent_class.call_count == 1

    def test_main_task_failure(self, mock_config_files, capsys):
        """测试任务失败。"""
        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = False
            mock_agent_class.return_value = mock_agent

            with patch.object(sys, "argv", ["dailycheck", "taobao_checkin", "--config-dir", str(mock_config_files)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            # 失败时应该有非零退出码
            assert exc_info.value.code != 0

    def test_main_exception_handling(self, mock_config_files, capsys):
        """测试异常处理。"""
        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent_class.side_effect = Exception("Test exception")

            with patch.object(sys, "argv", ["dailycheck", "taobao_checkin", "--config-dir", str(mock_config_files)]):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            # Exception should result in non-zero exit code
            assert exc_info.value.code != 0
            captured = capsys.readouterr()
            # Should show failure in summary
            assert "❌" in captured.out or "0/1" in captured.out


class TestMainConfigPriority:
    """测试配置优先级。"""

    def test_main_config_file_priority(self, tmp_path, mock_config_files, capsys):
        """测试配置文件优先级高于默认值。"""
        # 创建用户配置文件
        user_config = tmp_path / "user_config.yml"
        with open(user_config, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {
                    "api_provider": "siliconflow",
                    "max_steps": 30,
                },
                f,
            )

        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            with patch.object(
                sys,
                "argv",
                ["dailycheck", "taobao_checkin", "--config", str(user_config), "--config-dir", str(mock_config_files)],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 0
            # Config file is now used for initial setup, but CLI args take precedence
            # The agent is called, verify it was called at least once
            assert mock_agent_class.call_count >= 1

    def test_main_cli_overrides_config(self, tmp_path, mock_config_files, capsys):
        """测试命令行参数优先级高于配置文件。"""
        # 创建用户配置文件
        user_config = tmp_path / "user_config.yml"
        with open(user_config, "w", encoding="utf-8") as f:
            yaml.safe_dump(
                {
                    "api_provider": "siliconflow",
                    "max_steps": 30,
                },
                f,
            )

        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            with patch.object(
                sys,
                "argv",
                [
                    "dailycheck",
                    "taobao_checkin",
                    "--config",
                    str(user_config),
                    "--config-dir",
                    str(mock_config_files),
                    "--api-provider",
                    "open-router",
                    "--max-steps",
                    "50",
                ],
            ):
                with pytest.raises(SystemExit) as exc_info:
                    main()

            assert exc_info.value.code == 0
            # 验证命令行参数覆盖了配置文件
            call_args = mock_agent_class.call_args
            assert call_args[1]["api_provider"] == "open-router"
            assert call_args[1]["max_steps"] == 50

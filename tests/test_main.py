"""DailyCheckAgent 主模块测试。"""

import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch, call

from dailycheck_agent.main import DailyCheckAgent, run_agent


class TestDailyCheckAgentInit:
    """测试 DailyCheckAgent 初始化。"""

    def test_init_success(self, mock_config_files):
        """测试成功初始化。"""
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    max_steps=10,
                )

                assert agent.task_name == "taobao_checkin"
                assert agent.max_steps == 10
                assert agent.app_name == "淘宝"
                assert len(agent.task_steps) == 2

    def test_init_with_custom_params(self, mock_config_files, tmp_path):
        """测试使用自定义参数初始化。"""
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    adb_path="/custom/adb",
                    device_serial="custom-serial",
                    api_provider="siliconflow",
                    max_steps=20,
                    log_dir=str(log_dir),
                )

                assert agent.adb_path == "/custom/adb"
                assert agent.renderer is not None
                assert agent.api_provider == "siliconflow"

    def test_init_task_not_found(self, mock_config_files):
        """测试任务不存在时的异常。"""
        with pytest.raises(KeyError, match="invalid_task"):
            DailyCheckAgent(
                task_name="invalid_task",
                config_dir=str(mock_config_files),
            )

    def test_init_default_adb_path_from_scrcpy(self, mock_config_files, monkeypatch):
        """测试默认 ADB 路径从 scrcpy 目录获取。"""
        # 模拟 scrcpy/adb 存在
        mock_adb = Path(__file__).parent.parent / "scrcpy" / "adb"
        mock_adb.parent.mkdir(parents=True, exist_ok=True)
        mock_adb.touch(exist_ok=True)

        try:
            with patch("dailycheck_agent.main.ScreenRenderer"):
                with patch("dailycheck_agent.main.create_llm_client"):
                    agent = DailyCheckAgent(
                        task_name="taobao_checkin",
                        config_dir=str(mock_config_files),
                    )
                    # 验证使用了 scrcpy 目录的 adb
                    assert "scrcpy" in agent.adb_path or agent.adb_path == "adb"
        finally:
            # 清理
            if mock_adb.exists():
                mock_adb.unlink()
            if mock_adb.parent.exists():
                try:
                    mock_adb.parent.rmdir()
                except OSError:
                    pass


class TestBuildTaskDescription:
    """测试任务描述构建。"""

    def test_build_task_description(self, mock_config_files):
        """测试构建任务描述。"""
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                desc = agent._build_task_description()

                assert "淘宝" in desc
                assert "打开淘宝" in desc
                assert "签到" in desc

    def test_build_task_description_empty_steps(self, mock_config_files):
        """测试空步骤的任务描述。"""
        # 创建一个没有步骤的任务
        import yaml
        task_file = mock_config_files / "tasks.yml"
        with open(task_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({
                "tasks": {
                    "empty_task": {"app": "Test", "steps": []}
                }
            }, f)

        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="empty_task",
                    config_dir=str(mock_config_files),
                )
                desc = agent._build_task_description()

                assert "Test" in desc


class TestExecuteTool:
    """测试工具执行。"""

    def test_execute_tool_tap_screen(self, mock_config_files):
        """测试执行 tap_screen 工具。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.tap.return_value = "Clicked"
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "tap_screen",
                    {"x": 100, "y": 200},
                    "call_123",
                )

                assert "Clicked" in result
                mock_renderer_instance.tap.assert_called_once_with(100, 200)

    def test_execute_tool_slide_screen(self, mock_config_files):
        """测试执行 slide_screen 工具。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.slide.return_value = "Slid"
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "slide_screen",
                    {"start_x": 0, "start_y": 0, "end_x": 100, "end_y": 100, "duration": 300},
                    "call_123",
                )

                assert "Slid" in result

    def test_execute_tool_press_key_string(self, mock_config_files):
        """测试执行 press_key 工具（字符串按键）。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.press_key.return_value = "Pressed"
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "press_key",
                    {"key_code": "HOME"},
                    "call_123",
                )

                mock_renderer_instance.press_key.assert_called_once_with(3)  # HOME key code

    def test_execute_tool_press_key_int(self, mock_config_files):
        """测试执行 press_key 工具（整数按键）。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.press_key.return_value = "Pressed"
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "press_key",
                    {"key_code": 4},  # BACK key
                    "call_123",
                )

                mock_renderer_instance.press_key.assert_called_once_with(4)

    def test_execute_tool_input_text(self, mock_config_files):
        """测试执行 input_text 工具。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.input_text.return_value = "Input"
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "input_text",
                    {"text": "Hello World"},
                    "call_123",
                )

                assert "Input" in result

    def test_execute_tool_task_complete(self, mock_config_files):
        """测试执行 task_complete 工具。"""
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "task_complete",
                    {"summary": "Task completed successfully"},
                    "call_123",
                )

                assert "任务已完成" in result
                assert "Task completed successfully" in result

    def test_execute_tool_unknown(self, mock_config_files):
        """测试执行未知工具。"""
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                result = agent._execute_tool(
                    "unknown_tool",
                    {},
                    "call_123",
                )

                assert "未知工具" in result


class TestSaveLog:
    """测试日志保存。"""

    def test_save_log(self, mock_config_files, tmp_path):
        """测试保存日志。"""
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    log_dir=str(tmp_path),
                )

                messages = [{"role": "user", "content": "test"}]
                agent._save_log(messages, "Test summary")

                # 验证日志文件被创建
                log_files = list(tmp_path.glob("*.json"))
                assert len(log_files) == 1

                # 验证日志内容
                with open(log_files[0], "r", encoding="utf-8") as f:
                    log_data = json.load(f)

                assert log_data["task_name"] == "taobao_checkin"
                assert log_data["summary"] == "Test summary"
                assert log_data["messages"] == messages


class TestRun:
    """测试代理运行。"""

    def test_run_success(self, mock_config_files):
        """测试成功运行代理。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client") as mock_client:
                mock_client_instance = MagicMock()
                # 第一次调用返回工具调用，第二次返回 task_complete
                mock_client_instance.chat_with_tools.side_effect = [
                    {
                        "role": "assistant",
                        "content": "Clicking button",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "function": {
                                    "name": "tap_screen",
                                    "arguments": '{"x": 100, "y": 100}',
                                },
                            }
                        ],
                    },
                    {
                        "role": "assistant",
                        "content": "Task complete",
                        "tool_calls": [
                            {
                                "id": "call_2",
                                "function": {
                                    "name": "task_complete",
                                    "arguments": '{"summary": "Done"}',
                                },
                            }
                        ],
                    },
                ]
                mock_client.return_value = mock_client_instance

                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    max_steps=5,
                )
                result = agent.run()

                assert result is True
                assert agent._running is False

    def test_run_max_steps_reached(self, mock_config_files):
        """测试达到最大步骤数。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client") as mock_client:
                mock_client_instance = MagicMock()
                # 总是返回 tap_screen，永远不会完成
                mock_client_instance.chat_with_tools.return_value = {
                    "role": "assistant",
                    "content": "Clicking",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "tap_screen",
                                "arguments": '{"x": 100, "y": 100}',
                            },
                        }
                    ],
                }
                mock_client.return_value = mock_client_instance

                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    max_steps=3,
                )
                result = agent.run()

                assert result is False
                assert agent._current_step == 3

    def test_run_no_tool_calls(self, mock_config_files):
        """测试 AI 没有调用工具。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client") as mock_client:
                mock_client_instance = MagicMock()
                # 返回空工具调用
                mock_client_instance.chat_with_tools.return_value = {
                    "role": "assistant",
                    "content": "Thinking...",
                    "tool_calls": [],
                }
                mock_client.return_value = mock_client_instance

                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    max_steps=2,
                )
                result = agent.run()

                assert result is False

    def test_run_exception_handling(self, mock_config_files):
        """测试异常处理。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.get_screen_info.side_effect = Exception("Screen error")
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    max_steps=2,
                )
                result = agent.run()

                assert result is False

    def test_run_press_home_on_complete(self, mock_config_files):
        """测试任务完成后按 HOME 键。"""
        with patch("dailycheck_agent.main.ScreenRenderer") as mock_renderer:
            mock_renderer_instance = MagicMock()
            mock_renderer_instance.get_screen_info.return_value = "screen info"
            mock_renderer_instance.press_key.return_value = "Pressed HOME"
            mock_renderer.return_value = mock_renderer_instance

            with patch("dailycheck_agent.main.create_llm_client") as mock_client:
                mock_client_instance = MagicMock()
                mock_client_instance.chat_with_tools.return_value = {
                    "role": "assistant",
                    "content": "Complete",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "task_complete",
                                "arguments": '{"summary": "Done"}',
                            },
                        }
                    ],
                }
                mock_client.return_value = mock_client_instance

                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                    max_steps=5,
                )
                agent.run()

                # 验证按了 HOME 键
                mock_renderer_instance.press_key.assert_any_call(3)


class TestStop:
    """测试停止代理。"""

    def test_stop(self, mock_config_files):
        """测试停止代理。"""
        with patch("dailycheck_agent.main.ScreenRenderer"):
            with patch("dailycheck_agent.main.create_llm_client"):
                agent = DailyCheckAgent(
                    task_name="taobao_checkin",
                    config_dir=str(mock_config_files),
                )
                agent._running = True
                agent.stop()

                assert agent._running is False


class TestRunAgent:
    """测试 run_agent 便捷函数。"""

    def test_run_agent(self, mock_config_files):
        """测试 run_agent 函数。"""
        with patch("dailycheck_agent.main.DailyCheckAgent") as mock_agent_class:
            mock_agent = MagicMock()
            mock_agent.run.return_value = True
            mock_agent_class.return_value = mock_agent

            result = run_agent(
                task_name="taobao_checkin",
                max_steps=10,
            )

            assert result is True
            mock_agent_class.assert_called_once()
            mock_agent.run.assert_called_once()

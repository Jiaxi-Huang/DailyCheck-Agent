"""PromptBuilder 模块测试。"""

import pytest
import yaml

from dailycheck_agent.lib.prompt import PromptBuilder


class TestPromptBuilderInit:
    """测试 PromptBuilder 初始化。"""

    def test_init_with_defaults(self, mock_config_files):
        """测试使用默认参数初始化。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)

        assert builder.system_prompt is not None
        assert builder.task_description is None
        assert builder.app_name is None

    def test_init_with_task_description(self, mock_config_files):
        """测试使用任务描述初始化。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        task_desc = "Complete the daily check-in task"
        builder = PromptBuilder(task_description=task_desc, config_loader=loader)

        assert builder.task_description == task_desc

    def test_init_with_app_name(self, mock_config_files):
        """测试使用应用名称初始化。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(app_name="淘宝", config_loader=loader)

        assert builder.app_name == "淘宝"
        assert "淘宝" in builder.system_prompt

    def test_init_with_custom_system_prompt(self, mock_config_files):
        """测试使用自定义系统提示词初始化。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        custom_prompt = "Custom system prompt"
        builder = PromptBuilder(system_prompt=custom_prompt, config_loader=loader)

        assert builder.system_prompt == custom_prompt


class TestBuildSystemMessage:
    """测试系统消息构建。"""

    def test_build_system_message(self, mock_config_files):
        """测试构建系统消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        message = builder.build_system_message()

        assert message["role"] == "system"
        assert len(message["content"]) > 0

    def test_system_message_with_app_name(self, mock_config_files):
        """测试系统消息包含应用名称。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(app_name="京东", config_loader=loader)
        message = builder.build_system_message()

        assert "京东" in message["content"]


class TestBuildUserMessage:
    """测试用户消息构建。"""

    def test_build_user_message_basic(self, mock_config_files):
        """测试构建基本用户消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        screen_info = "Screen elements: button at (100, 200)"
        message = builder.build_user_message(screen_info=screen_info)

        assert message["role"] == "user"
        assert screen_info in message["content"]

    def test_build_user_message_with_step(self, mock_config_files):
        """测试构建带步骤的用户消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        message = builder.build_user_message(screen_info="screen info", step=5)

        assert "第 5 回合" in message["content"]

    def test_build_user_message_with_error(self, mock_config_files):
        """测试构建带错误的用户消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        message = builder.build_user_message(
            screen_info="screen info",
            error_message="Previous action failed",
        )

        assert "上一步操作失败" in message["content"]
        assert "Previous action failed" in message["content"]

    def test_build_user_message_with_task_description(self, mock_config_files):
        """测试构建带任务描述的用户消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        task_desc = "Complete sign-in task"
        builder = PromptBuilder(task_description=task_desc, config_loader=loader)
        message = builder.build_user_message(screen_info="screen info")

        assert task_desc in message["content"]

    def test_build_user_message_combined(self, mock_config_files):
        """测试构建组合信息的用户消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(task_description="Sign in", config_loader=loader)
        message = builder.build_user_message(
            screen_info="screen elements",
            step=3,
            error_message="Timeout",
        )

        content = message["content"]
        assert "第 3 回合" in content
        assert "上一步操作失败" in content
        assert "Timeout" in content
        assert "screen elements" in content
        assert "Sign in" in content


class TestBuildToolResultMessage:
    """测试工具结果消息构建。"""

    def test_build_tool_result_message(self, mock_config_files):
        """测试构建工具结果消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        message = builder.build_tool_result_message(
            tool_name="tap_screen",
            tool_call_id="call_123",
            result="Clicked at (100, 200)",
        )

        assert message["role"] == "tool"
        assert message["tool_call_id"] == "call_123"
        assert message["name"] == "tap_screen"
        assert message["content"] == "Clicked at (100, 200)"


class TestBuildFallbackMessage:
    """测试兜底消息构建。"""

    def test_build_fallback_message(self, mock_config_files):
        """测试构建兜底消息。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        message = builder.build_fallback_message()

        assert message["role"] == "user"
        assert "工具" in message["content"]


class TestGetTools:
    """测试获取工具定义。"""

    def test_get_tools(self, mock_config_files):
        """测试获取工具列表。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        tools = builder.get_tools()

        assert len(tools) == 5
        tool_names = [t["function"]["name"] for t in tools]
        assert "tap_screen" in tool_names
        assert "task_complete" in tool_names


class TestGetKeyCode:
    """测试获取按键代码。"""

    def test_get_key_code_home(self, mock_config_files):
        """测试获取 HOME 键代码。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        assert builder.get_key_code("HOME") == 3

    def test_get_key_code_back(self, mock_config_files):
        """测试获取 BACK 键代码。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        assert builder.get_key_code("BACK") == 4

    def test_get_key_code_case_insensitive(self, mock_config_files):
        """测试按键代码大小写不敏感。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        assert builder.get_key_code("home") == 3
        assert builder.get_key_code("Home") == 3

    def test_get_key_code_invalid(self, mock_config_files):
        """测试获取不存在的按键代码。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(config_loader=loader)
        assert builder.get_key_code("INVALID_KEY") is None


class TestReloadPrompts:
    """测试提示词重新加载。"""

    def test_reload_prompts(self, mock_config_files):
        """测试重新加载提示词。"""
        from dailycheck_agent.lib.config_loader import ConfigLoader
        loader = ConfigLoader(str(mock_config_files))
        builder = PromptBuilder(app_name="淘宝", config_loader=loader)

        # 修改配置
        prompt_config = loader.load_prompt_config()
        prompt_config["system_prompt"]["template"] = "Custom template: {app_info}"
        prompt_file = mock_config_files / "prompts.yml"
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(prompt_config, f)

        # 重新加载
        builder.reload_prompts()

        # 验证新提示词
        assert "Custom template" in builder.system_prompt or "淘宝" in builder.system_prompt

"""PromptBuilder 模块测试。"""

import pytest

from dailycheck_agent.lib.prompt import (
    KEY_CODES,
    PromptBuilder,
    TOOLS,
)


class TestToolsDefinition:
    """测试工具定义。"""

    def test_tools_list_not_empty(self):
        """测试工具列表不为空。"""
        assert len(TOOLS) > 0

    def test_tool_structure(self):
        """测试工具结构完整性。"""
        for tool in TOOLS:
            assert "type" in tool
            assert "function" in tool
            assert "name" in tool["function"]
            assert "description" in tool["function"]
            assert "parameters" in tool["function"]

    def test_all_required_tools_present(self):
        """测试所有必需的工具都存在。"""
        tool_names = [tool["function"]["name"] for tool in TOOLS]
        required_tools = ["tap_screen", "slide_screen", "press_key", "input_text", "task_complete"]

        for tool_name in required_tools:
            assert tool_name in tool_names

    def test_key_codes_not_empty(self):
        """测试按键代码映射不为空。"""
        assert len(KEY_CODES) > 0
        assert "HOME" in KEY_CODES
        assert "BACK" in KEY_CODES


class TestPromptBuilderInit:
    """测试 PromptBuilder 初始化。"""

    def test_init_with_defaults(self):
        """测试使用默认参数初始化。"""
        builder = PromptBuilder()

        assert builder.system_prompt is not None
        assert builder.task_description is None
        assert builder.app_name is None

    def test_init_with_task_description(self):
        """测试使用任务描述初始化。"""
        task_desc = "Complete the daily check-in task"
        builder = PromptBuilder(task_description=task_desc)

        assert builder.task_description == task_desc

    def test_init_with_app_name(self):
        """测试使用应用名称初始化。"""
        builder = PromptBuilder(app_name="淘宝")

        assert builder.app_name == "淘宝"
        assert "淘宝" in builder.system_prompt

    def test_init_with_custom_system_prompt(self):
        """测试使用自定义系统提示词初始化。"""
        custom_prompt = "Custom system prompt"
        builder = PromptBuilder(system_prompt=custom_prompt)

        assert builder.system_prompt == custom_prompt


class TestBuildSystemMessage:
    """测试系统消息构建。"""

    def test_build_system_message(self):
        """测试构建系统消息。"""
        builder = PromptBuilder()
        message = builder.build_system_message()

        assert message["role"] == "system"
        assert len(message["content"]) > 0

    def test_system_message_contains_tools_info(self):
        """测试系统消息包含工具信息。"""
        builder = PromptBuilder()
        message = builder.build_system_message()

        assert "tap_screen" in message["content"]
        assert "slide_screen" in message["content"]
        assert "press_key" in message["content"]

    def test_system_message_with_app_name(self):
        """测试系统消息包含应用名称。"""
        builder = PromptBuilder(app_name="京东")
        message = builder.build_system_message()

        assert "京东" in message["content"]


class TestBuildUserMessage:
    """测试用户消息构建。"""

    def test_build_user_message_basic(self):
        """测试构建基本用户消息。"""
        builder = PromptBuilder()
        screen_info = "Screen elements: button at (100, 200)"
        message = builder.build_user_message(screen_info=screen_info)

        assert message["role"] == "user"
        assert screen_info in message["content"]

    def test_build_user_message_with_step(self):
        """测试构建带步骤的用户消息。"""
        builder = PromptBuilder()
        message = builder.build_user_message(screen_info="screen info", step=5)

        assert "第 5 回合" in message["content"]

    def test_build_user_message_with_error(self):
        """测试构建带错误的用户消息。"""
        builder = PromptBuilder()
        message = builder.build_user_message(
            screen_info="screen info",
            error_message="Previous action failed",
        )

        assert "上一步操作失败" in message["content"]
        assert "Previous action failed" in message["content"]

    def test_build_user_message_with_task_description(self):
        """测试构建带任务描述的用户消息。"""
        task_desc = "Complete sign-in task"
        builder = PromptBuilder(task_description=task_desc)
        message = builder.build_user_message(screen_info="screen info")

        assert task_desc in message["content"]

    def test_build_user_message_combined(self):
        """测试构建组合信息的用户消息。"""
        builder = PromptBuilder(task_description="Sign in")
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

    def test_build_tool_result_message(self):
        """测试构建工具结果消息。"""
        builder = PromptBuilder()
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

    def test_build_fallback_message(self):
        """测试构建兜底消息。"""
        builder = PromptBuilder()
        message = builder.build_fallback_message()

        assert message["role"] == "user"
        assert "工具" in message["content"]
        assert "tap_screen" in message["content"]
        assert "task_complete" in message["content"]


class TestGetTools:
    """测试获取工具定义。"""

    def test_get_tools(self):
        """测试获取工具列表。"""
        builder = PromptBuilder()
        tools = builder.get_tools()

        assert tools == TOOLS
        assert len(tools) == 5


class TestGetKeyCode:
    """测试获取按键代码。"""

    def test_get_key_code_home(self):
        """测试获取 HOME 键代码。"""
        builder = PromptBuilder()
        assert builder.get_key_code("HOME") == KEY_CODES["HOME"]

    def test_get_key_code_back(self):
        """测试获取 BACK 键代码。"""
        builder = PromptBuilder()
        assert builder.get_key_code("BACK") == KEY_CODES["BACK"]

    def test_get_key_code_case_insensitive(self):
        """测试按键代码大小写不敏感。"""
        builder = PromptBuilder()
        assert builder.get_key_code("home") == KEY_CODES["HOME"]
        assert builder.get_key_code("Home") == KEY_CODES["HOME"]

    def test_get_key_code_invalid(self):
        """测试获取不存在的按键代码。"""
        builder = PromptBuilder()
        assert builder.get_key_code("INVALID_KEY") is None


class TestSystemPromptContent:
    """测试系统提示词内容。"""

    def test_system_prompt_mentions_workflow(self):
        """测试系统提示词包含工作流程。"""
        builder = PromptBuilder()
        prompt = builder.system_prompt

        assert "工作流程" in prompt or "流程" in prompt

    def test_system_prompt_mentions_coordinates(self):
        """测试系统提示词包含坐标系统说明。"""
        builder = PromptBuilder()
        prompt = builder.system_prompt

        assert "坐标" in prompt

    def test_system_prompt_mentions_task_complete(self):
        """测试系统提示词包含任务完成说明。"""
        builder = PromptBuilder()
        prompt = builder.system_prompt

        assert "task_complete" in prompt or "任务完成" in prompt

    def test_system_prompt_mentions_home_key(self):
        """测试系统提示词包含 HOME 键说明。"""
        builder = PromptBuilder()
        prompt = builder.system_prompt

        assert "HOME" in prompt or "HOME 键" in prompt or "主页" in prompt

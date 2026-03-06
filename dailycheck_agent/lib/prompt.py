"""提示词构建模块 - 构建 LLM 的系统提示词和工具定义。

This module provides the PromptBuilder class which uses external prompt
configurations loaded via ConfigLoader. Prompts are defined in config/prompts.yml
instead of being hardcoded.

Example:
    >>> builder = PromptBuilder(app_name="WeChat")
    >>> system_msg = builder.build_system_message()
    >>> user_msg = builder.build_user_message(screen_info="...", step=1)
"""

from typing import Any, Dict, List, Optional

from dailycheck_agent.lib.config_loader import ConfigLoader


class PromptBuilder:
    """提示词构建器，负责生成系统提示词和格式化用户消息。

    Uses ConfigLoader to load prompts from external configuration files.

    Attributes:
        task_description: Task description string
        app_name: Target application name
        config_loader: ConfigLoader instance
        vl_mode: Whether to use VL (Vision-Language) mode for image input

    Example:
        >>> builder = PromptBuilder(app_name="WeChat", task_description="Sign in")
        >>> tools = builder.get_tools()
        >>> print(builder.build_system_message()["content"][:100])
    """

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        task_description: Optional[str] = None,
        app_name: Optional[str] = None,
        config_loader: Optional[ConfigLoader] = None,
        vl_mode: bool = False,
    ):
        """初始化提示词构建器。

        Args:
            system_prompt: 自定义系统提示词，如果为 None 则使用配置文件中的模板
            task_description: 任务描述
            app_name: 目标应用名称
            config_loader: ConfigLoader 实例，如果为 None 则创建新实例
            vl_mode: 是否启用 VL 模式（支持图像输入）

        Example:
            >>> # Use default config loader
            >>> builder = PromptBuilder(app_name="WeChat")
            >>> # Use custom config loader
            >>> loader = ConfigLoader(config_dir="/custom/config")
            >>> builder = PromptBuilder(config_loader=loader)
        """
        self.task_description = task_description
        self.app_name = app_name
        self.config_loader = config_loader or ConfigLoader()
        self.vl_mode = vl_mode

        # Build or use custom system prompt
        if system_prompt:
            self.system_prompt = system_prompt
        else:
            self.system_prompt = self.config_loader.build_system_prompt(app_name)

    def build_system_message(self) -> Dict[str, str]:
        """构建系统消息。

        Returns:
            系统消息字典 {"role": "system", "content": "..."}

        Example:
            >>> builder = PromptBuilder(app_name="WeChat")
            >>> msg = builder.build_system_message()
            >>> print(msg["role"])
            system
        """
        return {"role": "system", "content": self.system_prompt}

    def build_user_message(
        self,
        screen_info: str,
        step: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, str]:
        """构建用户消息。

        Args:
            screen_info: 屏幕信息字符串
            step: 当前步骤编号（可选）
            error_message: 错误信息（如果上一步操作失败）

        Returns:
            用户消息字典 {"role": "user", "content": "..."}

        Example:
            >>> builder = PromptBuilder(task_description="Sign in")
            >>> msg = builder.build_user_message(
            ...     screen_info="button: (100, 200)",
            ...     step=1,
            ...     error_message="Element not found"
            ... )
            >>> print(msg["content"])
        """
        content = self.config_loader.format_user_message(
            screen_info=screen_info,
            step=step,
            error_message=error_message,
            task_description=self.task_description,
        )
        return {"role": "user", "content": content}

    def build_vl_user_message(
        self,
        screen_info: str,
        screenshot_url: str,
        step: Optional[int] = None,
        error_message: Optional[str] = None,
    ) -> Dict[str, Any]:
        """构建 VL 模型用户消息（包含截图图像）。

        Args:
            screen_info: 屏幕信息字符串
            screenshot_url: 屏幕截图的 URL（可以是 http:// 或 file:// 协议）
            step: 当前步骤编号（可选）
            error_message: 错误信息（如果上一步操作失败）

        Returns:
            用户消息字典，包含图像和文本内容：
            {
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": "https://..."}},
                    {"type": "text", "text": "..."}
                ]
            }

        Example:
            >>> builder = PromptBuilder(task_description="Sign in", vl_mode=True)
            >>> msg = builder.build_vl_user_message(
            ...     screen_info="button: (100, 200)",
            ...     screenshot_url="https://example.com/screenshot.png",
            ...     step=1
            ... )
        """
        text_content = self.config_loader.format_vl_user_message(
            screen_info=screen_info,
            step=step,
            error_message=error_message,
            task_description=self.task_description,
        )

        # 记录图像 URL（不记录 base64 数据）
        import logging
        logger = logging.getLogger("dailycheck")
        logger.debug(f"VL 模式：图像 URL = {screenshot_url[:80]}...")

        return {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": screenshot_url
                    }
                },
                {
                    "type": "text",
                    "text": text_content
                }
            ]
        }

    def build_tool_result_message(
        self, tool_name: str, tool_call_id: str, result: str
    ) -> Dict[str, str]:
        """构建工具执行结果消息。

        Args:
            tool_name: 工具名称
            tool_call_id: 工具调用 ID
            result: 执行结果描述

        Returns:
            工具结果消息字典 {"role": "tool", "tool_call_id": "...", "name": "...", "content": "..."}

        Example:
            >>> builder = PromptBuilder()
            >>> msg = builder.build_tool_result_message(
            ...     tool_name="tap_screen",
            ...     tool_call_id="call_123",
            ...     result="Clicked at (100, 200)"
            ... )
        """
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        }

    def build_fallback_message(self) -> Dict[str, str]:
        """构建兜底提示消息（当 LLM 忘记调用工具时使用）。

        Returns:
            兜底消息字典 {"role": "user", "content": "..."}

        Example:
            >>> builder = PromptBuilder()
            >>> msg = builder.build_fallback_message()
            >>> print(msg["content"][:50])
        """
        return {
            "role": "user",
            "content": self.config_loader.get_prompt_fallback_message(),
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具定义列表。

        Returns:
            工具定义列表

        Example:
            >>> builder = PromptBuilder()
            >>> tools = builder.get_tools()
            >>> print(len(tools))
            5
        """
        return self.config_loader.get_prompt_tools()

    def get_key_code(self, key_name: str) -> Optional[int]:
        """获取按键代码。

        Args:
            key_name: 按键名称（如 "HOME", "BACK"）

        Returns:
            按键代码，如果不存在返回 None

        Example:
            >>> builder = PromptBuilder()
            >>> print(builder.get_key_code("HOME"))
            3
        """
        key_codes = self.config_loader.get_prompt_key_codes()
        return key_codes.get(key_name.upper())

    def reload_prompts(self):
        """重新加载提示词配置。

        This is useful when the prompt configuration file has been modified
        and you want to apply the changes without restarting the application.

        Example:
            >>> builder = PromptBuilder(app_name="WeChat")
            >>> # After modifying prompts.yml
            >>> builder.reload_prompts()
        """
        self.config_loader.reload()
        # Rebuild system prompt
        self.system_prompt = self.config_loader.build_system_prompt(self.app_name)

    def get_tool_names(self) -> List[str]:
        """获取所有工具名称列表。

        Returns:
            工具名称列表

        Example:
            >>> builder = PromptBuilder()
            >>> print(builder.get_tool_names())
            ['tap_screen', 'slide_screen', 'press_key', 'input_text', 'task_complete']
        """
        tools = self.get_tools()
        return [tool.get("function", {}).get("name", "") for tool in tools]

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息。

        Returns:
            配置摘要字典

        Example:
            >>> builder = PromptBuilder()
            >>> summary = builder.get_config_summary()
            >>> print(summary['tool_count'])
        """
        return {
            "tool_count": len(self.get_tools()),
            "tool_names": self.get_tool_names(),
            "key_codes_count": len(self.config_loader.get_prompt_key_codes()),
            "has_system_prompt": bool(self.system_prompt),
        }

    def __repr__(self) -> str:
        """返回提示词构建器的字符串表示。

        Returns:
            提示词构建器的字符串表示
        """
        summary = self.get_config_summary()
        return (
            f"PromptBuilder(app_name='{self.app_name}', "
            f"tools={summary['tool_count']}, "
            f"key_codes={summary['key_codes_count']})"
        )

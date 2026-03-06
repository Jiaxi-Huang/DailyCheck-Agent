"""配置加载模块 - 从 YAML 文件加载 API、任务和提示词配置。

This module provides the ConfigLoader class for loading and managing
API, task, and prompt configurations from external YAML files.

Features:
    - Lazy loading with caching
    - Runtime reload for hot updates
    - Multiple config file locations with fallback strategy
    - Configuration validation
    - Unified configuration management

Example:
    >>> loader = ConfigLoader()
    >>> task_config = loader.load_task_config("taobao_checkin")
    >>> api_config = loader.load_api_config("siliconflow")
    >>> prompt_config = loader.load_prompt_config()
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


class ConfigLoaderError(Exception):
    """Base exception for ConfigLoader errors."""

    pass


class ConfigFileNotFoundError(ConfigLoaderError):
    """Raised when configuration file is not found."""

    pass


class ConfigValidationError(ConfigLoaderError):
    """Raised when configuration validation fails."""

    pass


class TaskNotFoundError(ConfigLoaderError):
    """Raised when specified task is not found."""

    pass


class APIProviderNotFoundError(ConfigLoaderError):
    """Raised when specified API provider is not found."""

    pass


class ConfigLoader:
    """配置加载器，负责从 YAML 文件加载和解析配置。

    This loader supports:
    - Lazy loading of configuration with caching
    - Runtime reload for hot updates
    - Multiple config file locations with fallback strategy
    - Configuration validation
    - Unified management for api.yml, tasks.yml, and prompts.yml

    Attributes:
        config_dir: Directory containing configuration files
        cache_enabled: Whether caching is enabled

    Example:
        >>> loader = ConfigLoader()
        >>> tasks = loader.load_task_config()  # Load all tasks
        >>> task = loader.load_task_config("taobao_checkin")  # Load specific task
    """

    CONFIG_FILES = {
        "api": "api.yml",
        "tasks": "tasks.yml",
        "prompts": "prompts.yml",
    }

    def __init__(
        self,
        config_dir: Optional[str] = None,
        cache_enabled: bool = True,
        validate_on_load: bool = True,
    ):
        """初始化配置加载器。

        Args:
            config_dir: 配置文件目录，默认为项目根目录的 config 文件夹
            cache_enabled: 是否启用配置缓存
            validate_on_load: 加载时是否验证配置完整性

        The config directory resolution follows this priority:
            1. Explicitly provided config_dir
            2. Current working directory's config folder
            3. Package directory's config folder
            4. User home directory's .dailycheck/config
        """
        self._config_dir: Optional[str] = config_dir
        self._resolved_config_dir: Optional[Path] = None
        self.cache_enabled = cache_enabled
        self.validate_on_load = validate_on_load

        # Cached configurations
        self._api_config: Optional[Dict[str, Any]] = None
        self._task_config: Optional[Dict[str, Any]] = None
        self._prompt_config: Optional[Dict[str, Any]] = None
        self._loaded = False
        self._validation_errors: List[str] = []

    @property
    def config_dir(self) -> Path:
        """Get the resolved configuration directory."""
        if self._resolved_config_dir is None:
            self._resolved_config_dir = self._resolve_config_dir()
        return self._resolved_config_dir

    def _resolve_config_dir(self) -> Path:
        """解析配置文件目录。

        Returns:
            配置文件目录路径

        Raises:
            ConfigFileNotFoundError: 当所有可能的路径都不存在时
        """
        candidates: List[Tuple[str, Path]] = []

        # 1. Explicitly provided directory
        if self._config_dir:
            provided_dir = Path(self._config_dir)
            if provided_dir.exists():
                return provided_dir
            candidates.append(("Provided directory", provided_dir))

        # 2. Current working directory's config folder
        cwd_config = Path.cwd() / "config"
        if cwd_config.exists() and (cwd_config / "tasks.yml").exists():
            logger.debug(f"Found config in current directory: {cwd_config}")
            return cwd_config
        candidates.append(("Current directory", cwd_config))

        # 3. Package directory's config folder
        try:
            import importlib.util

            spec = importlib.util.find_spec("dailycheck_agent")
            if spec and spec.origin:
                package_dir = Path(spec.origin).parent
                dev_config = package_dir.parent / "config"
                if dev_config.exists() and (dev_config / "tasks.yml").exists():
                    logger.debug(f"Found config in package directory: {dev_config}")
                    return dev_config
                candidates.append(("Package directory", dev_config))
        except Exception:
            pass

        # 4. User home directory's .dailycheck/config
        home_config = Path.home() / ".dailycheck" / "config"
        candidates.append(("Home directory", home_config))

        # Check if any candidate exists
        for source, config_dir in candidates:
            if config_dir.exists():
                logger.debug(f"Using config directory from {source}: {config_dir}")
                return config_dir

        # No valid directory found
        paths_list = "\n".join([f"  - {path}" for _, path in candidates])
        raise ConfigFileNotFoundError(
            f"配置文件目录不存在。\n"
            f"请确保 config 目录位于以下位置之一：\n{paths_list}"
        )

    def _get_config_file(self, config_type: str) -> Path:
        """Get the path to a configuration file.

        Args:
            config_type: Type of configuration ("api", "tasks", or "prompts")

        Returns:
            Path to the configuration file

        Raises:
            ConfigFileNotFoundError: If the configuration file doesn't exist
        """
        if config_type not in self.CONFIG_FILES:
            raise ConfigValidationError(f"Unknown config type: {config_type}")

        config_file = self.config_dir / self.CONFIG_FILES[config_type]

        if not config_file.exists():
            raise ConfigFileNotFoundError(
                f"配置文件不存在：{config_file}\n"
                f"请确保 {self.CONFIG_FILES[config_type]} 存在于 {self.config_dir}"
            )

        return config_file

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load a YAML file.

        Args:
            file_path: Path to the YAML file

        Returns:
            Parsed YAML content as dictionary

        Raises:
            ConfigFileNotFoundError: If file doesn't exist
            ConfigValidationError: If YAML parsing fails
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigValidationError(
                f"配置文件 YAML 解析失败：{file_path}\n错误：{e}"
            )

        if content is None:
            raise ConfigValidationError(f"配置文件为空：{file_path}")

        if not isinstance(content, dict):
            raise ConfigValidationError(
                f"配置文件格式无效，应为 YAML 字典：{file_path}"
            )

        return content

    def _load_api_config(self) -> Dict[str, Any]:
        """Load API configuration from file.

        Returns:
            API configuration dictionary
        """
        config_file = self._get_config_file("api")
        content = self._load_yaml_file(config_file)
        return content.get("api", {})

    def _load_task_config(self) -> Dict[str, Any]:
        """Load task configuration from file.

        Returns:
            Task configuration dictionary
        """
        config_file = self._get_config_file("tasks")
        content = self._load_yaml_file(config_file)
        return content.get("tasks", {})

    def _load_prompt_config(self) -> Dict[str, Any]:
        """Load prompt configuration from file.

        Returns:
            Prompt configuration dictionary
        """
        config_file = self._get_config_file("prompts")
        content = self._load_yaml_file(config_file)
        return content

    def _validate_api_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate API configuration.

        Args:
            config: API configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        if not isinstance(config, dict):
            errors.append("api 配置必须是字典格式")
            return errors

        for provider, provider_config in config.items():
            if not isinstance(provider_config, dict):
                errors.append(f"API 提供商 '{provider}' 的配置必须是字典格式")
                continue

            if "model" not in provider_config:
                errors.append(f"API 提供商 '{provider}' 缺少 model 字段")

            if "api-key" not in provider_config:
                errors.append(f"API 提供商 '{provider}' 缺少 api-key 字段")

        return errors

    def _validate_task_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate task configuration.

        Args:
            config: Task configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        if not isinstance(config, dict):
            errors.append("tasks 配置必须是字典格式")
            return errors

        for task_name, task_config in config.items():
            if not isinstance(task_config, dict):
                errors.append(f"任务 '{task_name}' 的配置必须是字典格式")
                continue

            if "name" not in task_config:
                errors.append(f"任务 '{task_name}' 缺少 name 字段")

            if "app" not in task_config:
                errors.append(f"任务 '{task_name}' 缺少 app 字段")

            if "steps" not in task_config:
                errors.append(f"任务 '{task_name}' 缺少 steps 字段")
            elif not isinstance(task_config["steps"], list):
                errors.append(f"任务 '{task_name}' 的 steps 必须是列表格式")
            else:
                for i, step in enumerate(task_config["steps"]):
                    if not isinstance(step, dict):
                        errors.append(f"任务 '{task_name}' 的步骤 {i} 必须是字典格式")
                    elif "name" not in step or "description" not in step:
                        errors.append(
                            f"任务 '{task_name}' 的步骤 {i} 缺少 name 或 description 字段"
                        )

        return errors

    def _validate_prompt_config(self, config: Dict[str, Any]) -> List[str]:
        """Validate prompt configuration.

        Args:
            config: Prompt configuration dictionary

        Returns:
            List of validation error messages
        """
        errors = []

        if not isinstance(config, dict):
            errors.append("prompts 配置必须是字典格式")
            return errors

        # Check required sections
        required_sections = ["system_prompt", "tools", "key_codes", "messages"]
        for section in required_sections:
            if section not in config:
                errors.append(f"缺少必需的配置项：{section}")

        # Validate system_prompt section
        if "system_prompt" in config:
            sp = config["system_prompt"]
            if not isinstance(sp, dict):
                errors.append("system_prompt 必须是字典格式")
            elif "template" not in sp:
                errors.append("system_prompt 缺少 template 字段")

        # Validate tools section
        if "tools" in config:
            tools = config["tools"]
            if not isinstance(tools, list):
                errors.append("tools 必须是列表格式")
            else:
                for i, tool in enumerate(tools):
                    if not isinstance(tool, dict):
                        errors.append(f"工具 {i} 必须是字典格式")
                    elif "function" not in tool:
                        errors.append(f"工具 {i} 缺少 function 字段")
                    else:
                        func = tool["function"]
                        if "name" not in func:
                            errors.append(f"工具 {i} 缺少 name 字段")
                        if "description" not in func:
                            errors.append(f"工具 {i} 缺少 description 字段")

        return errors

    def _validate_config(self) -> None:
        """Validate all loaded configurations.

        Raises:
            ConfigValidationError: If validation fails
        """
        self._validation_errors = []

        # Validate API config if loaded
        if self._api_config is not None:
            self._validation_errors.extend(self._validate_api_config(self._api_config))

        # Validate task config if loaded
        if self._task_config is not None:
            self._validation_errors.extend(
                self._validate_task_config(self._task_config)
            )

        # Validate prompt config if loaded
        if self._prompt_config is not None:
            self._validation_errors.extend(
                self._validate_prompt_config(self._prompt_config)
            )

        # Raise if there are validation errors
        if self._validation_errors:
            errors_str = "\n".join([f"  - {err}" for err in self._validation_errors])
            raise ConfigValidationError(
                f"配置验证失败：{self.config_dir}\n{errors_str}"
            )

        logger.debug("配置验证通过")

    def load_api_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """加载 API 配置。

        Args:
            provider: API 提供商名称，如 'open-router' 或 'siliconflow'。
                     如果为 None，返回所有提供商配置。

        Returns:
            API 配置字典

        Raises:
            ConfigFileNotFoundError: 当 api.yml 文件不存在时
            APIProviderNotFoundError: 当指定的 provider 不存在时
            ConfigValidationError: 当配置验证失败时
        """
        if self._api_config is None or not self.cache_enabled:
            self._api_config = self._load_api_config()
            self._loaded = True

        if provider:
            if provider not in self._api_config:
                available = ", ".join(self._api_config.keys())
                raise APIProviderNotFoundError(
                    f"API 提供商 '{provider}' 未在配置中定义。\n"
                    f"可用的提供商：{available}"
                )
            return self._api_config[provider]

        return self._api_config

    def load_task_config(self, task_name: Optional[str] = None) -> Dict[str, Any]:
        """加载任务配置。

        Args:
            task_name: 任务名称，如 'taobao_checkin'。
                      如果为 None，返回所有任务配置。

        Returns:
            任务配置字典

        Raises:
            ConfigFileNotFoundError: 当 tasks.yml 文件不存在时
            TaskNotFoundError: 当指定的 task_name 不存在时
            ConfigValidationError: 当配置验证失败时
        """
        if self._task_config is None or not self.cache_enabled:
            self._task_config = self._load_task_config()
            self._loaded = True

        if task_name:
            if task_name not in self._task_config:
                available = ", ".join(self._task_config.keys())
                raise TaskNotFoundError(
                    f"任务 '{task_name}' 未在配置中定义。\n"
                    f"可用的任务：{available}"
                )
            return self._task_config[task_name]

        return self._task_config

    def load_prompt_config(self) -> Dict[str, Any]:
        """加载提示词配置。

        Returns:
            提示词配置字典

        Raises:
            ConfigFileNotFoundError: 当 prompts.yml 文件不存在时
            ConfigValidationError: 当配置验证失败时
        """
        if self._prompt_config is None or not self.cache_enabled:
            self._prompt_config = self._load_prompt_config()
            self._loaded = True

        return self._prompt_config

    def get_api_key(self, provider: str) -> str:
        """获取 API 密钥。

        Args:
            provider: API 提供商名称

        Returns:
            API 密钥字符串

        Raises:
            APIProviderNotFoundError: 当 provider 不存在时
            ValueError: 当 API 密钥未设置时
        """
        config = self.load_api_config(provider)
        api_key = config.get("api-key", "")

        if not api_key:
            raise ValueError(
                f"API 密钥未设置。请在配置文件 {self.config_dir / 'api.yml'} 中填写有效的 api-key"
            )

        if api_key == "{{ api_key }}":
            raise ValueError(
                f"API 密钥未配置。检测到配置文件 {self.config_dir / 'api.yml'} 中使用占位符 '{{{{ api_key }}}}'，\n"
                f"请替换为实际的 API 密钥。"
            )

        # 检查是否为常见的占位符格式
        if api_key.startswith("{{") and api_key.endswith("}}"):
            raise ValueError(
                f"API 密钥未配置。配置文件 {self.config_dir / 'api.yml'} 中的 api-key 为占位符：{api_key}\n"
                f"请替换为实际的 API 密钥。"
            )

        return api_key

    def get_all_tasks(self) -> Dict[str, Any]:
        """获取所有任务配置。

        Returns:
            所有任务配置字典
        """
        return self.load_task_config()

    def get_task_names(self) -> List[str]:
        """获取所有任务名称列表。

        Returns:
            任务名称列表
        """
        return list(self.load_task_config().keys())

    def get_task_list_summary(self) -> str:
        """获取任务列表的格式化摘要。

        Returns:
            格式化的任务列表字符串
        """
        tasks = self.load_task_config()
        lines = []
        for name, config in tasks.items():
            app = config.get("app", "Unknown")
            steps_count = len(config.get("steps", []))
            lines.append(f"  - {name}: {app} ({steps_count} steps)")
        return "\n".join(lines)

    def get_prompt_tools(self) -> List[Dict[str, Any]]:
        """获取提示词中的工具定义列表。

        Returns:
            工具定义列表
        """
        prompt_config = self.load_prompt_config()
        return prompt_config.get("tools", [])

    def get_prompt_tool_by_name(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """根据名称获取工具定义。

        Args:
            tool_name: 工具名称

        Returns:
            工具定义字典，如果不存在则返回 None
        """
        tools = self.get_prompt_tools()
        for tool in tools:
            func = tool.get("function", {})
            if func.get("name") == tool_name:
                return tool
        return None

    def get_prompt_key_codes(self) -> Dict[str, int]:
        """获取提示词中的按键代码映射。

        Returns:
            按键代码字典
        """
        prompt_config = self.load_prompt_config()
        return prompt_config.get("key_codes", {})

    def get_prompt_system_template(self) -> str:
        """获取系统提示词模板。

        Returns:
            系统提示词模板字符串
        """
        prompt_config = self.load_prompt_config()
        return prompt_config.get("system_prompt", {}).get("template", "")

    def get_prompt_fallback_message(self) -> str:
        """获取兜底消息模板。

        Returns:
            兜底消息字符串
        """
        prompt_config = self.load_prompt_config()
        return prompt_config.get("messages", {}).get("fallback_message", "")

    def build_system_prompt(self, app_name: Optional[str] = None) -> str:
        """构建完整的系统提示词。

        Args:
            app_name: 目标应用名称

        Returns:
            完整的系统提示词字符串
        """
        template = self.get_prompt_system_template()
        prompt_config = self.load_prompt_config()

        # Get app info template
        app_info_templates = prompt_config.get("system_prompt", {}).get(
            "app_info_templates", {}
        )
        if app_name:
            app_info_template = app_info_templates.get(
                "with_app", "目标应用是【{app_name}】"
            )
            app_info = app_info_template.format(app_name=app_name)
        else:
            app_info_template = app_info_templates.get(
                "without_app", "目标应用由任务决定"
            )
            app_info = app_info_template

        # Build tools description
        tools = self.get_prompt_tools()
        tools_description = self._format_tools_description(tools)

        # Format template
        try:
            prompt = template.format(
                app_info=app_info,
                tools_description=tools_description,
            )
        except KeyError as e:
            raise ConfigValidationError(
                f"系统提示词模板包含未定义的变量：{e}"
            )

        return prompt

    def _format_tools_description(self, tools: List[Dict[str, Any]]) -> str:
        """格式化工具描述。

        Args:
            tools: 工具定义列表

        Returns:
            格式化的工具描述字符串
        """
        descriptions = []
        for tool in tools:
            func = tool.get("function", {})
            name = func.get("name", "unknown")
            desc = func.get("description", "")
            descriptions.append(f"- {name}: {desc}")
        return "\n".join(descriptions)

    def format_user_message(
        self,
        screen_info: str,
        step: Optional[int] = None,
        error_message: Optional[str] = None,
        task_description: Optional[str] = None,
    ) -> str:
        """格式化用户消息。

        Args:
            screen_info: 屏幕信息
            step: 步骤编号
            error_message: 错误信息
            task_description: 任务描述

        Returns:
            格式化的用户消息字符串
        """
        prompt_config = self.load_prompt_config()
        templates = prompt_config.get("messages", {}).get("user_message", {})
        parts: List[str] = []

        if step is not None:
            step_prefix = templates.get("step_prefix", "【第 {step} 回合】")
            try:
                parts.append(step_prefix.format(step=step))
            except (KeyError, ValueError):
                parts.append(f"【第 {step} 回合】")

        if error_message:
            error_prefix = templates.get(
                "error_prefix", "⚠️ 上一步操作失败：{error_message}"
            )
            try:
                parts.append(error_prefix.format(error_message=error_message))
            except (KeyError, ValueError):
                parts.append(f"⚠️ 上一步操作失败：{error_message}")

        screen_prefix = templates.get(
            "screen_info_prefix",
            "当前屏幕上的可用元素如下，请分析并采取下一步操作：",
        )
        parts.append(f"{screen_prefix}\n{screen_info}")

        if task_description:
            task_prefix = templates.get("task_prefix", "当前任务：")
            parts.append(f"\n{task_prefix}{task_description}")

        return "\n".join(parts)

    def format_vl_user_message(
        self,
        screen_info: str,
        step: Optional[int] = None,
        error_message: Optional[str] = None,
        task_description: Optional[str] = None,
    ) -> str:
        """格式化 VL 模型用户消息（包含截图和 UI 信息）。

        Args:
            screen_info: 屏幕信息
            step: 步骤编号
            error_message: 错误信息
            task_description: 任务描述

        Returns:
            格式化的用户消息字符串
        """
        prompt_config = self.load_prompt_config()
        templates = prompt_config.get("messages", {}).get("vl_user_message", {})
        parts: List[str] = []

        if step is not None:
            step_prefix = templates.get("step_prefix", "【第 {step} 回合】")
            try:
                parts.append(step_prefix.format(step=step))
            except (KeyError, ValueError):
                parts.append(f"【第 {step} 回合】")

        if error_message:
            error_prefix = templates.get(
                "error_prefix", "⚠️ 上一步操作失败：{error_message}"
            )
            try:
                parts.append(error_prefix.format(error_message=error_message))
            except (KeyError, ValueError):
                parts.append(f"⚠️ 上一步操作失败：{error_message}")

        # VL model instruction
        text_instruction = templates.get(
            "text_instruction",
            "请分析这张手机屏幕截图，并结合下方的 UI 元素信息，采取下一步操作。",
        )
        parts.append(text_instruction)

        # Screen info (as reference)
        screen_prefix = templates.get(
            "screen_info_prefix",
            "当前屏幕上的可用元素如下（供参考）：",
        )
        parts.append(f"\n{screen_prefix}\n{screen_info}")

        if task_description:
            task_prefix = templates.get("task_prefix", "当前任务：")
            parts.append(f"\n{task_prefix}{task_description}")

        return "\n".join(parts)

    def reload(self, force: bool = False) -> None:
        """重新加载所有配置。

        Args:
            force: 强制重新解析配置目录

        Raises:
            ConfigFileNotFoundError: 配置文件不存在
            ConfigValidationError: 配置验证失败
        """
        if force:
            self._resolved_config_dir = None

        self._api_config = None
        self._task_config = None
        self._prompt_config = None
        self._loaded = False
        self._validation_errors = []

        try:
            # Trigger reload
            _ = self.load_api_config()
            _ = self.load_task_config()
            _ = self.load_prompt_config()
            logger.info(f"配置已重新加载：{self.config_dir}")
        except Exception as e:
            logger.error(f"配置重新加载失败：{e}")
            raise

    def is_loaded(self) -> bool:
        """检查配置是否已加载。

        Returns:
            True 如果配置已加载
        """
        return self._loaded

    def get_validation_errors(self) -> List[str]:
        """获取验证错误列表。

        Returns:
            验证错误字符串列表
        """
        return self._validation_errors.copy()

    def get_config_summary(self) -> Dict[str, Any]:
        """获取配置摘要信息。

        Returns:
            配置摘要字典
        """
        return {
            "config_dir": str(self.config_dir),
            "loaded": self._loaded,
            "api_providers": list(self._api_config.keys()) if self._api_config else [],
            "task_count": len(self._task_config) if self._task_config else 0,
            "task_names": self.get_task_names() if self._task_config else [],
            "has_prompt_config": self._prompt_config is not None,
            "tool_count": len(self.get_prompt_tools()) if self._prompt_config else 0,
            "validation_errors": self.get_validation_errors(),
        }

    def __repr__(self) -> str:
        """返回配置加载器的字符串表示。

        Returns:
            配置加载器的字符串表示
        """
        return (
            f"ConfigLoader(config_dir='{self.config_dir}', "
            f"loaded={self._loaded}, cache_enabled={self.cache_enabled})"
        )

    def __str__(self) -> str:
        """返回用户友好的字符串表示。

        Returns:
            用户友好的字符串表示
        """
        summary = self.get_config_summary()
        tools_info = ""
        if summary["has_prompt_config"]:
            tools_info = f"\n  Tools: {summary['tool_count']}"
        return (
            f"ConfigLoader:\n"
            f"  Directory: {summary['config_dir']}\n"
            f"  Loaded: {summary['loaded']}\n"
            f"  API Providers: {', '.join(summary['api_providers'])}\n"
            f"  Tasks: {summary['task_count']} ({', '.join(summary['task_names'][:3])}...)"
            f"{tools_info}"
        )

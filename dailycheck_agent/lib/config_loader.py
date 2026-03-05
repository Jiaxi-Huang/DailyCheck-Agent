"""配置加载模块 - 从 YAML 文件加载 API 和任务配置。"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional


class ConfigLoader:
    """配置加载器，负责从 YAML 文件加载和解析配置。"""

    def __init__(self, config_dir: Optional[str] = None):
        """初始化配置加载器。

        Args:
            config_dir: 配置文件目录，默认为项目根目录的 config 文件夹
        """
        if config_dir is None:
            # 默认配置目录为项目根目录的 config 文件夹
            # 使用 Path(__file__).parent.parent.parent 定位到项目根目录
            self.config_dir = Path(__file__).parent.parent.parent / "config"
        else:
            self.config_dir = Path(config_dir)

        self._api_config: Optional[Dict[str, Any]] = None
        self._task_config: Optional[Dict[str, Any]] = None

    def load_api_config(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """加载 API 配置。

        Args:
            provider: API 提供商名称，如 'open-router' 或 'siliconflow'。
                     如果为 None，返回所有提供商配置。

        Returns:
            API 配置字典

        Raises:
            FileNotFoundError: 当 api.yml 文件不存在时
            KeyError: 当指定的 provider 不存在时
        """
        if self._api_config is None:
            api_file = self.config_dir / "api.yml"
            if not api_file.exists():
                raise FileNotFoundError(f"API 配置文件不存在：{api_file}")

            with open(api_file, "r", encoding="utf-8") as f:
                self._api_config = yaml.safe_load(f).get("api", {})

        if provider:
            if provider not in self._api_config:
                raise KeyError(f"API 提供商 '{provider}' 未在配置中定义")
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
            FileNotFoundError: 当 tasks.yml 文件不存在时
            KeyError: 当指定的 task_name 不存在时
        """
        if self._task_config is None:
            task_file = self.config_dir / "tasks.yml"
            if not task_file.exists():
                raise FileNotFoundError(f"任务配置文件不存在：{task_file}")

            with open(task_file, "r", encoding="utf-8") as f:
                self._task_config = yaml.safe_load(f).get("tasks", {})

        if task_name:
            if task_name not in self._task_config:
                raise KeyError(f"任务 '{task_name}' 未在配置中定义")
            return self._task_config[task_name]

        return self._task_config

    def get_api_key(self, provider: str, env_var: Optional[str] = None) -> str:
        """获取 API 密钥，支持从环境变量覆盖。

        Args:
            provider: API 提供商名称
            env_var: 环境变量名称，用于覆盖配置文件中的 api-key。
                    如果为 None，使用默认的 DAILYCHECK_API_KEY

        Returns:
            API 密钥字符串

        Raises:
            ValueError: 当 API 密钥未设置时
        """
        if env_var is None:
            env_var = "DAILYCHECK_API_KEY"

        # 优先从环境变量获取
        api_key = os.environ.get(env_var)
        if api_key:
            return api_key

        # 从配置文件获取（支持 {{ api_key }} 占位符提示）
        config = self.load_api_config(provider)
        api_key = config.get("api-key", "")

        if not api_key or api_key == "{{ api_key }}":
            raise ValueError(
                f"API 密钥未设置。请设置环境变量 {env_var} 或在配置文件中填写有效的 api-key"
            )

        return api_key

    def reload(self):
        """重新加载所有配置（用于配置热更新）。"""
        self._api_config = None
        self._task_config = None

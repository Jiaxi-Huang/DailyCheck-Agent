"""ConfigLoader 模块测试。"""

import pytest
from pathlib import Path
import yaml

from dailycheck_agent.lib.config_loader import (
    ConfigLoader,
    ConfigFileNotFoundError,
    ConfigValidationError,
    TaskNotFoundError,
    APIProviderNotFoundError,
)


class TestConfigLoaderInit:
    """测试 ConfigLoader 初始化。"""

    def test_init_with_default_dir(self, mock_config_files):
        """测试使用默认配置目录初始化。"""
        loader = ConfigLoader(str(mock_config_files))
        assert loader.config_dir == Path(mock_config_files)

    def test_init_with_none_uses_cwd_config(self, monkeypatch, tmp_path):
        """测试 config_dir 为 None 时的回退行为。"""
        # 创建临时配置
        config_dir = tmp_path / "config"
        config_dir.mkdir()
        (config_dir / "tasks.yml").write_text("tasks: {}")
        (config_dir / "api.yml").write_text("api: {}")
        (config_dir / "prompts.yml").write_text("system_prompt:\n  template: test\ntools: []\nkey_codes: {}\nmessages: {}")

        monkeypatch.chdir(tmp_path)
        loader = ConfigLoader()
        assert loader.config_dir == config_dir


class TestLoadApiConfig:
    """测试 API 配置加载。"""

    def test_load_api_config_with_provider(self, mock_config_files):
        """测试加载指定提供商的 API 配置。"""
        loader = ConfigLoader(str(mock_config_files))
        config = loader.load_api_config("open-router")

        assert config["api-key"] == "test-api-key-123"
        assert config["model"] == "test-model"

    def test_load_api_config_all_providers(self, mock_config_files):
        """测试加载所有 API 提供商配置。"""
        loader = ConfigLoader(str(mock_config_files))
        config = loader.load_api_config()

        assert "open-router" in config
        assert "siliconflow" in config

    def test_load_api_config_provider_not_found(self, mock_config_files):
        """测试指定不存在的 API 提供商。"""
        loader = ConfigLoader(str(mock_config_files))

        with pytest.raises(APIProviderNotFoundError, match="invalid-provider"):
            loader.load_api_config("invalid-provider")


class TestLoadTaskConfig:
    """测试任务配置加载。"""

    def test_load_task_config_with_name(self, mock_config_files):
        """测试加载指定任务的配置。"""
        loader = ConfigLoader(str(mock_config_files))
        config = loader.load_task_config("taobao_checkin")

        assert config["app"] == "淘宝"
        assert len(config["steps"]) == 2
        assert config["steps"][0]["name"] == "打开淘宝"

    def test_load_task_config_all_tasks(self, mock_config_files):
        """测试加载所有任务配置。"""
        loader = ConfigLoader(str(mock_config_files))
        config = loader.load_task_config()

        assert "taobao_checkin" in config
        assert "jd_checkin" in config

    def test_load_task_config_task_not_found(self, mock_config_files):
        """测试指定不存在的任务。"""
        loader = ConfigLoader(str(mock_config_files))

        with pytest.raises(TaskNotFoundError, match="invalid_task"):
            loader.load_task_config("invalid_task")


class TestLoadPromptConfig:
    """测试提示词配置加载。"""

    def test_load_prompt_config(self, mock_config_files):
        """测试加载提示词配置。"""
        loader = ConfigLoader(str(mock_config_files))
        config = loader.load_prompt_config()

        assert "system_prompt" in config
        assert "tools" in config
        assert "key_codes" in config
        assert "messages" in config

    def test_get_prompt_tools(self, mock_config_files):
        """测试获取提示词工具。"""
        loader = ConfigLoader(str(mock_config_files))
        tools = loader.get_prompt_tools()

        assert len(tools) > 0
        assert tools[0]["function"]["name"] == "tap_screen"

    def test_get_prompt_key_codes(self, mock_config_files):
        """测试获取按键代码。"""
        loader = ConfigLoader(str(mock_config_files))
        key_codes = loader.get_prompt_key_codes()

        assert "HOME" in key_codes
        assert key_codes["HOME"] == 3

    def test_build_system_prompt(self, mock_config_files):
        """测试构建系统提示词。"""
        loader = ConfigLoader(str(mock_config_files))
        prompt = loader.build_system_prompt(app_name="淘宝")

        assert "淘宝" in prompt
        assert "tap_screen" in prompt


class TestGetApiKey:
    """测试 API 密钥获取。"""

    def test_get_api_key_success(self, mock_config_files):
        """测试成功获取 API 密钥。"""
        loader = ConfigLoader(str(mock_config_files))
        api_key = loader.get_api_key("open-router")

        assert api_key == "test-api-key-123"

    def test_get_api_key_empty(self, temp_config_dir):
        """测试 API 密钥为空时的异常。"""
        api_config = {"api": {"open-router": {"api-key": ""}}}
        api_file = temp_config_dir / "api.yml"
        with open(api_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(api_config, f)

        task_file = temp_config_dir / "tasks.yml"
        with open(task_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({"tasks": {}}, f)

        prompt_file = temp_config_dir / "prompts.yml"
        with open(prompt_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({"system_prompt": {"template": "test"}, "tools": [], "key_codes": {}, "messages": {}}, f)

        loader = ConfigLoader(str(temp_config_dir))

        with pytest.raises(ValueError, match="API 密钥未设置"):
            loader.get_api_key("open-router")


class TestReload:
    """测试配置重新加载。"""

    def test_reload_clears_cache(self, mock_config_files):
        """测试 reload 方法清除缓存。"""
        loader = ConfigLoader(str(mock_config_files))

        # 首次加载
        loader.load_api_config()
        loader.load_task_config()

        # 修改配置文件
        api_config = {
            "api": {
                "open-router": {
                    "api-key": "new-api-key",
                    "model": "new-model",
                }
            }
        }
        api_file = mock_config_files / "api.yml"
        with open(api_file, "w", encoding="utf-8") as f:
            yaml.safe_dump(api_config, f)

        # 重新加载
        loader.reload()

        # 验证新配置
        new_config = loader.load_api_config("open-router")
        assert new_config["api-key"] == "new-api-key"
        assert new_config["model"] == "new-model"


class TestGetConfigSummary:
    """测试配置摘要获取。"""

    def test_get_config_summary(self, mock_config_files):
        """测试获取配置摘要。"""
        loader = ConfigLoader(str(mock_config_files))
        # 先加载配置
        loader.load_task_config()
        loader.load_api_config()
        
        summary = loader.get_config_summary()

        assert "config_dir" in summary
        assert "api_providers" in summary
        assert "task_count" in summary
        assert "task_names" in summary
        assert len(summary["task_names"]) == 2

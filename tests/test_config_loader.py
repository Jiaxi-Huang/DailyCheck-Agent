"""ConfigLoader 模块测试。"""

import pytest
from pathlib import Path

from dailycheck_agent.lib.config_loader import ConfigLoader


class TestConfigLoaderInit:
    """测试 ConfigLoader 初始化。"""

    def test_init_with_default_dir(self, mock_config_files):
        """测试使用默认配置目录初始化。"""
        loader = ConfigLoader(str(mock_config_files))
        assert loader.config_dir == Path(mock_config_files)

    def test_init_with_none_uses_cwd_config(self, monkeypatch):
        """测试 config_dir 为 None 时的回退行为。"""
        # 创建一个临时配置目录
        with pytest.MonkeyPatch().context() as mp:
            # 模拟当前工作目录存在 config 文件夹
            mock_config = Path.cwd() / "config"
            mock_config.mkdir(exist_ok=True)
            (mock_config / "tasks.yml").write_text("tasks: {}")
            (mock_config / "api.yml").write_text("api: {}")

            loader = ConfigLoader()
            assert loader.config_dir == mock_config

            # 清理
            (mock_config / "tasks.yml").unlink()
            (mock_config / "api.yml").unlink()
            mock_config.rmdir()


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

    def test_load_api_config_file_not_found(self, temp_config_dir):
        """测试 API 配置文件不存在时的异常。"""
        loader = ConfigLoader(str(temp_config_dir))

        with pytest.raises(FileNotFoundError):
            loader.load_api_config()

    def test_load_api_config_provider_not_found(self, mock_config_files):
        """测试指定不存在的 API 提供商。"""
        loader = ConfigLoader(str(mock_config_files))

        with pytest.raises(KeyError, match="invalid-provider"):
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

    def test_load_task_config_file_not_found(self, temp_config_dir):
        """测试任务配置文件不存在时的异常。"""
        loader = ConfigLoader(str(temp_config_dir))

        with pytest.raises(FileNotFoundError):
            loader.load_task_config()

    def test_load_task_config_task_not_found(self, mock_config_files):
        """测试指定不存在的任务。"""
        loader = ConfigLoader(str(mock_config_files))

        with pytest.raises(KeyError, match="invalid_task"):
            loader.load_task_config("invalid_task")


class TestGetApiKey:
    """测试 API 密钥获取。"""

    def test_get_api_key_success(self, mock_config_files):
        """测试成功获取 API 密钥。"""
        loader = ConfigLoader(str(mock_config_files))
        api_key = loader.get_api_key("open-router")

        assert api_key == "test-api-key-123"

    def test_get_api_key_empty(self, temp_config_dir):
        """测试 API 密钥为空时的异常。"""
        # 创建配置但 API 密钥为空
        api_config = {"api": {"open-router": {"api-key": ""}}}
        api_file = temp_config_dir / "api.yml"
        with open(api_file, "w", encoding="utf-8") as f:
            import yaml
            yaml.safe_dump(api_config, f)

        # 创建空的任务配置
        task_file = temp_config_dir / "tasks.yml"
        with open(task_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({"tasks": {}}, f)

        loader = ConfigLoader(str(temp_config_dir))

        with pytest.raises(ValueError, match="API 密钥未设置"):
            loader.get_api_key("open-router")

    def test_get_api_key_placeholder(self, temp_config_dir):
        """测试 API 密钥为占位符时的异常。"""
        # 创建配置但 API 密钥为占位符
        api_config = {"api": {"open-router": {"api-key": "{{ api_key }}"}}}
        api_file = temp_config_dir / "api.yml"
        with open(api_file, "w", encoding="utf-8") as f:
            import yaml
            yaml.safe_dump(api_config, f)

        # 创建空的任务配置
        task_file = temp_config_dir / "tasks.yml"
        with open(task_file, "w", encoding="utf-8") as f:
            yaml.safe_dump({"tasks": {}}, f)

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
            import yaml
            yaml.safe_dump(api_config, f)

        # 重新加载
        loader.reload()

        # 验证新配置
        new_config = loader.load_api_config("open-router")
        assert new_config["api-key"] == "new-api-key"
        assert new_config["model"] == "new-model"

"""API 请求模块测试。"""

import pytest
from unittest.mock import MagicMock, patch

from dailycheck_agent.lib.api_request import (
    APIError,
    LLMClient,
    create_llm_client,
)


class TestLLMClientInit:
    """测试 LLMClient 初始化。"""

    def test_init_success(self):
        """测试成功初始化。"""
        client = LLMClient(
            api_url="https://test.api/chat/completions",
            api_key="test-key",
            model="test-model",
        )

        assert client.api_url == "https://test.api/chat/completions"
        assert client.api_key == "test-key"
        assert client.model == "test-model"
        assert client.max_retries == 3
        assert client.retry_delay == 1.0
        assert client.timeout == 60

    def test_init_with_custom_params(self):
        """测试使用自定义参数初始化。"""
        client = LLMClient(
            api_url="https://test.api/chat/completions",
            api_key="test-key",
            model="test-model",
            max_retries=5,
            retry_delay=2.0,
            timeout=120,
        )

        assert client.max_retries == 5
        assert client.retry_delay == 2.0
        assert client.timeout == 120


class TestLLMClientChat:
    """测试 LLMClient 聊天功能。"""

    def test_chat_success(self, mock_requests_session):
        """测试成功的聊天请求。"""
        client = LLMClient(
            api_url="https://test.api/chat/completions",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Hello"}]
        content, tool_calls = client.chat(messages)

        assert content == "Test response"
        assert tool_calls == []
        mock_requests_session.post.assert_called_once()

    def test_chat_with_tools(self, mock_requests_session):
        """测试带工具的聊天请求。"""
        client = LLMClient(
            api_url="https://test.api/chat/completions",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Click the button"}]
        tools = [{"type": "function", "function": {"name": "tap_screen"}}]

        content, tool_calls = client.chat(messages, tools=tools)

        # 验证请求中包含 tools
        call_args = mock_requests_session.post.call_args
        assert "tools" in call_args[1]["json"]
        assert "tool_choice" in call_args[1]["json"]

    def test_chat_with_temperature_and_max_tokens(self, mock_requests_session):
        """测试带温度和 max_tokens 的请求。"""
        client = LLMClient(
            api_url="https://test.api/chat/completions",
            api_key="test-key",
            model="test-model",
        )

        messages = [{"role": "user", "content": "Hello"}]
        client.chat(messages, temperature=0.5, max_tokens=100)

        call_args = mock_requests_session.post.call_args
        payload = call_args[1]["json"]
        assert payload["temperature"] == 0.5
        assert payload["max_tokens"] == 100

    def test_chat_http_error(self):
        """测试 HTTP 错误处理。"""
        with patch("requests.Session") as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.json.return_value = {"error": "Unauthorized"}
            mock_session_instance = mock_session.return_value
            mock_session_instance.post.return_value = mock_response

            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="invalid-key",
                model="test-model",
            )

            with pytest.raises(APIError, match="API 请求失败：401"):
                client.chat([{"role": "user", "content": "Hello"}])

    def test_chat_api_error_in_response(self):
        """测试 API 返回错误信息的处理。"""
        with patch("requests.Session") as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "error": {"message": "Rate limit exceeded"}
            }
            mock_session_instance = mock_session.return_value
            mock_session_instance.post.return_value = mock_response

            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
            )

            with pytest.raises(APIError, match="API 返回错误"):
                client.chat([{"role": "user", "content": "Hello"}])

    def test_chat_empty_response(self):
        """测试空响应的处理。"""
        with patch("requests.Session") as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"choices": []}
            mock_session_instance = mock_session.return_value
            mock_session_instance.post.return_value = mock_response

            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
            )

            with pytest.raises(APIError, match="API 返回空响应"):
                client.chat([{"role": "user", "content": "Hello"}])

    def test_chat_timeout_retry(self):
        """测试超时重试。"""
        with patch("requests.Session") as mock_session:
            mock_session_instance = mock_session.return_value
            mock_session_instance.post.side_effect = [
                Exception("Timeout"),  # 第一次失败
                Exception("Timeout"),  # 第二次失败
                MagicMock(  # 第三次成功
                    status_code=200,
                    json=lambda: {
                        "choices": [{"message": {"content": "Success", "tool_calls": []}}]
                    },
                ),
            ]

            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
                max_retries=3,
                retry_delay=0.01,  # 缩短测试延迟
            )

            content, _ = client.chat([{"role": "user", "content": "Hello"}])
            assert content == "Success"
            assert mock_session_instance.post.call_count == 3

    def test_chat_all_retries_fail(self):
        """测试所有重试都失败。"""
        with patch("requests.Session") as mock_session:
            mock_session_instance = mock_session.return_value
            mock_session_instance.post.side_effect = Exception("Connection error")

            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
                max_retries=2,
                retry_delay=0.01,
            )

            with pytest.raises(APIError):
                client.chat([{"role": "user", "content": "Hello"}])


class TestLLMClientChatWithTools:
    """测试 LLMClient 带工具的聊天功能。"""

    def test_chat_with_tools_success(self):
        """测试成功的带工具聊天请求。"""
        with patch("requests.Session") as mock_session:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [
                    {
                        "message": {
                            "content": "I'll click the button",
                            "tool_calls": [
                                {
                                    "id": "call_123",
                                    "type": "function",
                                    "function": {
                                        "name": "tap_screen",
                                        "arguments": '{"x": 100, "y": 200}',
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
            mock_session_instance = mock_session.return_value
            mock_session_instance.post.return_value = mock_response

            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
            )

            messages = [{"role": "user", "content": "Click the button"}]
            tools = [{"type": "function", "function": {"name": "tap_screen"}}]

            response = client.chat_with_tools(messages, tools)

            assert response["role"] == "assistant"
            assert response["content"] == "I'll click the button"
            assert len(response["tool_calls"]) == 1
            assert response["tool_calls"][0]["function"]["name"] == "tap_screen"


class TestLLMClientContextManager:
    """测试 LLMClient 上下文管理器。"""

    def test_context_manager(self):
        """测试上下文管理器。"""
        with patch("requests.Session"):
            with LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
            ) as client:
                assert client is not None
                assert hasattr(client, "_session")

    def test_close_method(self):
        """测试 close 方法。"""
        with patch("requests.Session") as mock_session:
            client = LLMClient(
                api_url="https://test.api/chat/completions",
                api_key="test-key",
                model="test-model",
            )
            client.close()
            mock_session.return_value.close.assert_called_once()


class TestCreateLLMClient:
    """测试 create_llm_client 工厂函数。"""

    def test_create_open_router_client(self):
        """测试创建 OpenRouter 客户端。"""
        client = create_llm_client(
            provider="open-router",
            api_key="test-key",
            model="custom-model",
        )

        assert client.api_url == "https://openrouter.ai/api/v1/chat/completions"
        assert client.model == "custom-model"

    def test_create_siliconflow_client(self):
        """测试创建 SiliconFlow 客户端。"""
        client = create_llm_client(
            provider="siliconflow",
            api_key="test-key",
            model="custom-model",
        )

        assert client.api_url == "https://api.siliconflow.cn/v1/chat/completions"
        assert client.model == "custom-model"

    def test_create_client_default_model(self):
        """测试使用默认模型创建客户端。"""
        client = create_llm_client(
            provider="open-router",
            api_key="test-key",
        )

        assert client.model == "z-ai/glm-4.7-flash"

    def test_create_client_invalid_provider(self):
        """测试使用不支持的提供商。"""
        with pytest.raises(ValueError, match="不支持的 API 提供商"):
            create_llm_client(
                provider="invalid-provider",
                api_key="test-key",
            )

    def test_create_client_with_custom_params(self):
        """测试使用自定义参数创建客户端。"""
        client = create_llm_client(
            provider="open-router",
            api_key="test-key",
            max_retries=10,
            timeout=30,
        )

        assert client.max_retries == 10
        assert client.timeout == 30

"""API 请求模块 - 与 LLM API 进行通信。"""

import json
import time
from typing import Any, Dict, List, Optional, Tuple

import requests


class APIError(Exception):
    """API 请求异常。"""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Dict] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class LLMClient:
    """LLM API 客户端，负责与 LLM 服务进行通信。"""

    def __init__(
        self,
        api_url: str,
        api_key: str,
        model: str,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: int = 60,
    ):
        """初始化 LLM 客户端。

        Args:
            api_url: API 端点 URL
            api_key: API 密钥
            model: 模型名称
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时时间（秒）
        """
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        )

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: str = "auto",
        temperature: float = 0.1,
        max_tokens: Optional[int] = None,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """发送聊天请求。

        Args:
            messages: 消息历史列表
            tools: 工具定义列表
            tool_choice: 工具选择策略 ("auto", "none", "required", 或具体工具名)
            temperature: 温度参数
            max_tokens: 最大生成 token 数

        Returns:
            (content, tool_calls) 元组：
            - content: 文本回复内容（可能为 None）
            - tool_calls: 工具调用列表

        Raises:
            APIError: 当 API 请求失败时
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice

        if max_tokens:
            payload["max_tokens"] = max_tokens

        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = self._session.post(
                    self.api_url,
                    json=payload,
                    timeout=self.timeout,
                )

                # 处理 HTTP 错误
                if response.status_code >= 400:
                    error_data = response.json() if response.content else {}
                    raise APIError(
                        message=f"API 请求失败：{response.status_code}",
                        status_code=response.status_code,
                        response=error_data,
                    )

                # 解析响应
                result = response.json()

                # 检查 API 错误
                if "error" in result:
                    error_info = result["error"]
                    raise APIError(
                        message=f"API 返回错误：{error_info.get('message', '未知错误')}",
                        status_code=response.status_code,
                        response=result,
                    )

                # 提取回复内容
                choices = result.get("choices", [])
                if not choices:
                    raise APIError(message="API 返回空响应", status_code=response.status_code, response=result)

                ai_msg = choices[0]["message"]
                content = ai_msg.get("content")
                tool_calls = ai_msg.get("tool_calls", [])

                return (content, tool_calls)

            except requests.exceptions.Timeout:
                last_error = APIError(message="请求超时")
            except requests.exceptions.ConnectionError as e:
                last_error = APIError(message=f"连接错误：{e}")
            except APIError:
                raise
            except Exception as e:
                last_error = APIError(message=f"未知错误：{e}")

            # 重试前等待
            if attempt < self.max_retries - 1:
                time.sleep(self.retry_delay * (attempt + 1))

        # 所有重试失败
        raise last_error or APIError(message="API 请求失败，已达最大重试次数")

    def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
    ) -> Dict[str, Any]:
        """发送聊天请求并返回完整响应。

        Args:
            messages: 消息历史列表
            tools: 工具定义列表
            tool_choice: 工具选择策略

        Returns:
            完整的 AI 响应消息字典

        Raises:
            APIError: 当 API 请求失败时
        """
        content, tool_calls = self.chat(messages, tools, tool_choice)

        return {
            "role": "assistant",
            "content": content,
            "tool_calls": tool_calls,
        }

    def close(self):
        """关闭会话。"""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def create_llm_client(
    provider: str,
    api_key: str,
    model: Optional[str] = None,
    **kwargs,
) -> LLMClient:
    """创建 LLM 客户端。

    Args:
        provider: API 提供商名称 ('open-router', 'siliconflow' 等)
        api_key: API 密钥
        model: 模型名称
        **kwargs: 其他参数传递给 LLMClient

    Returns:
        LLMClient 实例

    Raises:
        ValueError: 当提供商不支持时
    """
    # 提供商配置
    PROVIDERS = {
        "open-router": "https://openrouter.ai/api/v1/chat/completions",
        "siliconflow": "https://api.siliconflow.cn/v1/chat/completions",
    }

    if provider not in PROVIDERS:
        raise ValueError(f"不支持的 API 提供商：{provider}。支持的提供商：{list(PROVIDERS.keys())}")

    api_url = PROVIDERS[provider]

    # 默认模型配置
    DEFAULT_MODELS = {
        "open-router": "z-ai/glm-4.7-flash",
        "siliconflow": "Pro/zai-org/GLM-4.7",
    }

    if model is None:
        model = DEFAULT_MODELS.get(provider, DEFAULT_MODELS["open-router"])

    return LLMClient(api_url=api_url, api_key=api_key, model=model, **kwargs)

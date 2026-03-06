"""Pytest 配置文件 - 提供共享的 fixtures 和 mocks。"""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml


@pytest.fixture
def temp_config_dir():
    """创建临时配置目录用于测试。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_dir = Path(tmpdir)
        yield config_dir


@pytest.fixture
def sample_api_config():
    """示例 API 配置。"""
    return {
        "api": {
            "open-router": {
                "api-key": "test-api-key-123",
                "model": "test-model",
            },
            "siliconflow": {
                "api-key": "test-silicon-key",
                "model": "Pro/test-model",
            },
        }
    }


@pytest.fixture
def sample_task_config():
    """示例任务配置。"""
    return {
        "tasks": {
            "taobao_checkin": {
                "app": "淘宝",
                "steps": [
                    {"name": "打开淘宝", "description": "启动淘宝应用"},
                    {"name": "签到", "description": "点击签到按钮"},
                ],
            },
            "jd_checkin": {
                "app": "京东",
                "steps": [
                    {"name": "打开京东", "description": "启动京东应用"},
                    {"name": "签到", "description": "点击签到按钮"},
                ],
            },
        }
    }


@pytest.fixture
def sample_prompt_config():
    """示例提示词配置。"""
    return {
        "system_prompt": {
            "template": "你是一个安卓手机自动化打卡助手，{app_info}。\n\n## 可用工具\n{tools_description}\n\n## 工作流程\n1. 分析当前屏幕\n2. 决策下一步操作\n3. 调用工具执行\n\n请根据屏幕信息做出正确的决策。",
            "app_info_templates": {
                "with_app": "目标应用是【{app_name}】",
                "without_app": "目标应用由任务决定",
            },
        },
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "tap_screen",
                    "description": "点击屏幕上的指定坐标",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "integer", "description": "水平坐标"},
                            "y": {"type": "integer", "description": "垂直坐标"},
                        },
                        "required": ["x", "y"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "slide_screen",
                    "description": "在屏幕上从一个坐标滑动到另一个坐标",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "start_x": {"type": "integer"},
                            "start_y": {"type": "integer"},
                            "end_x": {"type": "integer"},
                            "end_y": {"type": "integer"},
                        },
                        "required": ["start_x", "start_y", "end_x", "end_y"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "press_key",
                    "description": "按下系统按键",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "key_code": {"type": "string"},
                        },
                        "required": ["key_code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "input_text",
                    "description": "输入文本",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"},
                        },
                        "required": ["text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "task_complete",
                    "description": "标记任务完成",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "summary": {"type": "string"},
                        },
                        "required": [],
                    },
                },
            },
        ],
        "key_codes": {
            "HOME": 3,
            "BACK": 4,
            "ENTER": 66,
            "APP_SWITCH": 187,
        },
        "messages": {
            "user_message": {
                "step_prefix": "【第 {step} 回合】",
                "error_prefix": "⚠️ 上一步操作失败：{error_message}",
                "screen_info_prefix": "当前屏幕上的可用元素如下：",
                "task_prefix": "当前任务：",
            },
            "fallback_message": "你刚才只是回复了文本而没有调用任何工具。请使用工具进行下一步操作。",
            "tool_result": {
                "success_prefix": "执行成功：",
                "new_screen_prefix": "。当前最新的屏幕元素如下：\n",
            },
        },
    }


@pytest.fixture
def mock_config_files(temp_config_dir, sample_api_config, sample_task_config, sample_prompt_config):
    """创建模拟配置文件。"""
    # 写入 API 配置
    api_file = temp_config_dir / "api.yml"
    with open(api_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_api_config, f)

    # 写入任务配置
    task_file = temp_config_dir / "tasks.yml"
    with open(task_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_task_config, f)

    # 写入提示词配置
    prompt_file = temp_config_dir / "prompts.yml"
    with open(prompt_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(sample_prompt_config, f)

    return temp_config_dir


@pytest.fixture
def mock_adb_path():
    """模拟 ADB 路径。"""
    return "/mock/adb/path"


@pytest.fixture
def mock_device_serial():
    """模拟设备序列号。"""
    return "mock-device-serial-123"


@pytest.fixture
def mock_screen_info():
    """模拟屏幕信息。"""
    return """屏幕分辨率：1080x1920
文本：'签到', 坐标：(540, 960), 区域：[500,900][580,1020]
文本：'首页', 坐标：(200, 1800), 区域：[150,1750][250,1850]"""


@pytest.fixture
def mock_llm_response():
    """模拟 LLM 响应。"""
    return {
        "role": "assistant",
        "content": "我将点击签到按钮",
        "tool_calls": [
            {
                "id": "call_123",
                "type": "function",
                "function": {
                    "name": "tap_screen",
                    "arguments": '{"x": 540, "y": 960}',
                },
            }
        ],
    }


@pytest.fixture
def mock_subprocess():
    """模拟 subprocess 运行。"""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            stdout=b"mock output",
            stderr=b"",
            returncode=0,
        )
        yield mock_run


@pytest.fixture
def mock_requests_session():
    """模拟 requests Session。"""
    with patch("requests.Session") as mock_session:
        mock_session_instance = MagicMock()
        mock_session.return_value = mock_session_instance

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "Test response",
                        "tool_calls": [],
                    }
                }
            ]
        }
        mock_session_instance.post.return_value = mock_response

        yield mock_session_instance


@pytest.fixture
def env_vars_clean():
    """清理环境变量，确保测试隔离。"""
    # 保存当前环境变量
    original_env = os.environ.copy()
    yield
    # 恢复原始环境变量
    os.environ.clear()
    os.environ.update(original_env)


@pytest.fixture
def sample_xml_ui():
    """示例 UI 层次结构 XML。"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<hierarchy rotation="0">
  <node index="0" text="签到" resource-id="com.taobao.taobao:id/sign_in_button" class="android.widget.Button" bounds="[500,900][580,1020]" />
  <node index="1" text="首页" resource-id="com.taobao.taobao:id/home_button" class="android.widget.Button" bounds="[150,1750][250,1850]" />
  <node index="2" text="" resource-id="" class="android.view.View" bounds="[0,0][1080,1920]" />
</hierarchy>"""

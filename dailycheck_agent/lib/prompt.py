"""提示词构建模块 - 构建 LLM 的系统提示词和工具定义。"""

from typing import Any, Dict, List, Optional


# 工具定义列表（遵循 SKILLS.md 规范）
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "tap_screen",
            "description": "点击屏幕上的指定坐标",
            "parameters": {
                "type": "object",
                "properties": {
                    "x": {"type": "integer", "description": "水平坐标（X 轴）"},
                    "y": {"type": "integer", "description": "垂直坐标（Y 轴）"},
                },
                "required": ["x", "y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "slide_screen",
            "description": "在屏幕上从一个坐标滑动到另一个坐标，用于滚动或解锁",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_x": {"type": "integer", "description": "起始 X 坐标"},
                    "start_y": {"type": "integer", "description": "起始 Y 坐标"},
                    "end_x": {"type": "integer", "description": "结束 X 坐标"},
                    "end_y": {"type": "integer", "description": "结束 Y 坐标"},
                    "duration": {
                        "type": "integer",
                        "description": "滑动持续时间（毫秒）",
                        "default": 300,
                    },
                },
                "required": ["start_x", "start_y", "end_x", "end_y"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "press_key",
            "description": "按下系统按键（如 Home、Back、Enter 等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "key_code": {
                        "type": "string",
                        "description": "按键名称，如 HOME、BACK、ENTER、APP_SWITCH",
                    }
                },
                "required": ["key_code"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "input_text",
            "description": "在当前聚焦的输入框中输入文本",
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "要输入的文本内容"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "task_complete",
            "description": "标记当前任务已成功完成",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {
                        "type": "string",
                        "description": "简要描述完成的任务和达成的结果",
                    }
                },
                "required": [],
            },
        },
    },
]

# 常用按键代码映射
KEY_CODES = {
    "HOME": 3,
    "BACK": 4,
    "ENTER": 66,
    "APP_SWITCH": 187,
    "MENU": 82,
    "VOLUME_UP": 24,
    "VOLUME_DOWN": 25,
    "POWER": 26,
}


class PromptBuilder:
    """提示词构建器，负责生成系统提示词和格式化用户消息。"""

    def __init__(
        self,
        system_prompt: Optional[str] = None,
        task_description: Optional[str] = None,
        app_name: Optional[str] = None,
    ):
        """初始化提示词构建器。

        Args:
            system_prompt: 自定义系统提示词，如果为 None 则使用默认
            task_description: 任务描述
            app_name: 目标应用名称
        """
        self.system_prompt = system_prompt or self._build_default_system_prompt(app_name)
        self.task_description = task_description
        self.app_name = app_name

    def _build_default_system_prompt(self, app_name: Optional[str] = None) -> str:
        """构建默认系统提示词。

        Args:
            app_name: 目标应用名称

        Returns:
            系统提示词字符串
        """
        app_info = f"目标应用是【{app_name}】" if app_name else "目标应用由任务决定"

        return f"""你是一个安卓手机自动化打卡助手，{app_info}。
你一开始在手机主页。

## 可用工具
你可以使用以下工具与设备交互：
- tap_screen: 点击屏幕指定坐标
- slide_screen: 滑动屏幕（用于滚动或解锁）
- press_key: 按下系统按键（HOME、BACK、ENTER 等）
- input_text: 输入文本
- task_complete: 任务完成时调用

## 工作流程
1. 分析当前屏幕上的 UI 元素信息（文本、描述、坐标等）
2. 根据任务目标决策下一步操作
3. 调用相应的工具执行操作
4. 等待操作结果和新屏幕信息
5. 重复上述步骤直到任务完成

## 任务完成判定
- 当你认为已经完成了打卡任务的核心操作（如点击了签到按钮、领取了奖励等），即使当前页面跳转到了其他页面（如活动详情页、奖励页等），也视为任务已完成
- 任务完成后，先按 HOME 键回到手机主页
- 然后调用 task_complete 工具报告任务完成

## 注意事项
- 坐标系统：(0, 0) 是屏幕左上角
- 每次操作后屏幕会更新，请根据最新屏幕信息决策
- 如果找不到目标元素，可以尝试滑动屏幕或返回上一页
- 任务完成后务必先按 HOME 键回到主页，再调用 task_complete 工具

请根据屏幕信息中的元素坐标做出正确的决策，必须调用工具来执行动作。"""

    def build_system_message(self) -> Dict[str, str]:
        """构建系统消息。

        Returns:
            系统消息字典
        """
        return {"role": "system", "content": self.system_prompt}

    def build_user_message(
        self, screen_info: str, step: Optional[int] = None, error_message: Optional[str] = None
    ) -> Dict[str, str]:
        """构建用户消息。

        Args:
            screen_info: 屏幕信息字符串
            step: 当前步骤编号（可选）
            error_message: 错误信息（如果上一步操作失败）

        Returns:
            用户消息字典
        """
        content_parts = []

        # 添加步骤信息（如果有）
        if step is not None:
            content_parts.append(f"【第 {step} 回合】")

        # 添加错误提示（如果有）
        if error_message:
            content_parts.append(f"⚠️ 上一步操作失败：{error_message}")

        # 添加屏幕信息
        content_parts.append(f"当前屏幕上的可用元素如下，请分析并采取下一步操作：\n{screen_info}")

        # 添加任务描述（如果有）
        if self.task_description:
            content_parts.append(f"\n当前任务：{self.task_description}")

        content = "\n".join(content_parts)
        return {"role": "user", "content": content}

    def build_tool_result_message(
        self, tool_name: str, tool_call_id: str, result: str
    ) -> Dict[str, str]:
        """构建工具执行结果消息。

        Args:
            tool_name: 工具名称
            tool_call_id: 工具调用 ID
            result: 执行结果描述

        Returns:
            工具结果消息字典
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
            兜底消息字典
        """
        return {
            "role": "user",
            "content": "你刚才只是回复了文本而没有调用任何工具。"
            "请务必使用 tap_screen、slide_screen、press_key 或 input_text 进行下一步操作，"
            "或者使用 task_complete 结束任务。",
        }

    def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具定义列表。

        Returns:
            工具定义列表
        """
        return TOOLS

    def get_key_code(self, key_name: str) -> Optional[int]:
        """获取按键代码。

        Args:
            key_name: 按键名称

        Returns:
            按键代码，如果不存在返回 None
        """
        return KEY_CODES.get(key_name.upper())

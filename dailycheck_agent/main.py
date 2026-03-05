"""DailyCheck-Agent 主模块 - 代理循环和任务执行。"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from dailycheck_agent.lib.api_request import LLMClient, create_llm_client
from dailycheck_agent.lib.config_loader import ConfigLoader
from dailycheck_agent.lib.prompt import KEY_CODES, PromptBuilder
from dailycheck_agent.lib.render import ScreenRenderer

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DailyCheckAgent:
    """DailyCheck 代理，负责执行自动化打卡任务。"""

    def __init__(
        self,
        task_name: str,
        adb_path: Optional[str] = None,
        device_serial: Optional[str] = None,
        api_provider: Optional[str] = None,
        config_dir: Optional[str] = None,
        max_steps: int = 50,
        log_dir: Optional[str] = None,
    ):
        """初始化 DailyCheck 代理。

        Args:
            task_name: 任务名称（在 tasks.yml 中定义）
            adb_path: ADB 可执行文件路径
            device_serial: 设备序列号
            api_provider: API 提供商名称
            config_dir: 配置文件目录
            max_steps: 最大执行步骤数
            log_dir: 日志目录
        """
        self.task_name = task_name
        self.max_steps = max_steps

        # 加载配置
        self.config_loader = ConfigLoader(config_dir)

        # 加载任务配置
        task_config = self.config_loader.load_task_config(task_name)
        self.task_config = task_config
        self.app_name = task_config.get("app", "")
        self.task_steps = task_config.get("steps", [])

        # 构建任务描述
        task_description = self._build_task_description()

        # 初始化屏幕渲染器
        self.adb_path = adb_path or self._get_default_adb_path()
        self.renderer = ScreenRenderer(
            adb_path=self.adb_path,
            device_serial=device_serial,
            wait_time=2.0,
        )

        # 初始化提示词构建器
        self.prompt_builder = PromptBuilder(
            task_description=task_description,
            app_name=self.app_name,
        )

        # 初始化 LLM 客户端
        self.api_provider = api_provider or "open-router"
        self._init_llm_client()

        # 消息历史
        self.messages: List[Dict[str, Any]] = []

        # 日志目录
        self.log_dir = Path(log_dir) if log_dir else Path.home() / ".dailycheck" / "logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 运行状态
        self._running = False
        self._current_step = 0

    def _get_default_adb_path(self) -> str:
        """获取默认 ADB 路径。"""
        # 尝试从环境变量获取
        adb_path = os.environ.get("ADB_PATH")
        if adb_path:
            return adb_path

        # 默认路径：项目根目录的 scrcpy/adb
        default_path = Path(__file__).parent.parent / "scrcpy" / "adb"
        if default_path.exists():
            return str(default_path)

        # 回退到系统 PATH 中的 adb
        return "adb"

    def _init_llm_client(self):
        """初始化 LLM 客户端。"""
        try:
            api_config = self.config_loader.load_api_config(self.api_provider)
            api_key = self.config_loader.get_api_key(self.api_provider)
            model = api_config.get("model", "")

            self.llm_client = create_llm_client(
                provider=self.api_provider,
                api_key=api_key,
                model=model if model else None,
            )
            logger.info(f"LLM 客户端已初始化：{self.api_provider} / {model or 'default'}")
        except Exception as e:
            logger.warning(f"LLM 客户端初始化失败：{e}")
            raise

    def _build_task_description(self) -> str:
        """构建任务描述字符串。"""
        if not self.task_steps:
            return f"完成 {self.app_name} 的打卡任务"

        steps_desc = []
        for i, step in enumerate(self.task_steps, 1):
            step_name = step.get("name", f"步骤 {i}")
            step_desc = step.get("description", "")
            steps_desc.append(f"{i}. {step_name}: {step_desc}")

        return f"完成 {self.app_name} 的打卡任务，步骤如下：\n" + "\n".join(steps_desc)

    def _save_log(self, messages: List[Dict[str, Any]], summary: Optional[str] = None):
        """保存会话日志。"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = self.log_dir / f"{self.task_name}_{timestamp}.json"

        log_data = {
            "task_name": self.task_name,
            "timestamp": timestamp,
            "summary": summary,
            "steps": self._current_step,
            "messages": messages,
        }

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(log_data, f, ensure_ascii=False, indent=2)

        logger.info(f"会话日志已保存：{log_file}")

    def _execute_tool(self, tool_name: str, args: Dict[str, Any], tool_call_id: str) -> str:
        """执行工具调用。

        Args:
            tool_name: 工具名称
            args: 工具参数
            tool_call_id: 工具调用 ID

        Returns:
            执行结果字符串
        """
        logger.info(f"执行工具：{tool_name}, 参数：{args}")

        if tool_name == "tap_screen":
            x = args.get("x", 0)
            y = args.get("y", 0)
            result = self.renderer.tap(x, y)
            # 获取新屏幕信息
            new_screen = self.renderer.get_screen_info()
            return f"{result}。当前最新的屏幕元素如下：\n{new_screen}"

        elif tool_name == "slide_screen":
            start_x = args.get("start_x", 0)
            start_y = args.get("start_y", 0)
            end_x = args.get("end_x", 0)
            end_y = args.get("end_y", 0)
            duration = args.get("duration", 300)
            result = self.renderer.slide(start_x, start_y, end_x, end_y, duration)
            new_screen = self.renderer.get_screen_info()
            return f"{result}。当前最新的屏幕元素如下：\n{new_screen}"

        elif tool_name == "press_key":
            key_code = args.get("key_code", "HOME")
            # 支持字符串或整数
            if isinstance(key_code, str):
                key_code = KEY_CODES.get(key_code.upper(), 3)
            result = self.renderer.press_key(key_code)
            new_screen = self.renderer.get_screen_info()
            return f"{result}。当前最新的屏幕元素如下：\n{new_screen}"

        elif tool_name == "input_text":
            text = args.get("text", "")
            result = self.renderer.input_text(text)
            new_screen = self.renderer.get_screen_info()
            return f"{result}。当前最新的屏幕元素如下：\n{new_screen}"

        elif tool_name == "task_complete":
            summary = args.get("summary", "任务已完成")
            logger.info(f"任务完成：{summary}")
            return f"任务已完成：{summary}"

        else:
            return f"未知工具：{tool_name}"

    def run(self) -> bool:
        """运行代理执行任务。

        Returns:
            任务是否成功完成
        """
        logger.info(f"开始执行任务：{self.task_name}")
        logger.info(f"目标应用：{self.app_name}")
        logger.info(f"最大步骤数：{self.max_steps}")

        self._running = True
        self._current_step = 0

        # 初始化消息历史
        self.messages = [self.prompt_builder.build_system_message()]

        # 获取初始屏幕信息
        try:
            initial_screen = self.renderer.get_screen_info()
        except Exception as e:
            logger.error(f"获取初始屏幕信息失败：{e}")
            return False

        self.messages.append(
            self.prompt_builder.build_user_message(
                screen_info=initial_screen,
                step=0,
            )
        )

        # 主循环
        task_completed = False
        last_error = None

        while self._running and self._current_step < self.max_steps:
            self._current_step += 1
            logger.info(f"\n{'='*20} 第 {self._current_step} 回合 {'='*20}")

            # 打印当前消息摘要
            last_msg = self.messages[-1]
            msg_preview = last_msg["content"][:200] if len(last_msg.get("content", "")) > 200 else last_msg.get("content", "")
            logger.info(f"当前提示词：{msg_preview}...")

            try:
                # 调用 LLM
                ai_msg = self.llm_client.chat_with_tools(
                    messages=self.messages,
                    tools=self.prompt_builder.get_tools(),
                )

                # 保存 AI 回复到历史
                self.messages.append(ai_msg)

                # 打印 AI 思考内容
                if ai_msg.get("content"):
                    logger.info(f"AI 回复：{ai_msg['content']}")

                # 处理工具调用
                tool_calls = ai_msg.get("tool_calls", [])

                if not tool_calls:
                    logger.warning("AI 没有调用任何工具")
                    self.messages.append(self.prompt_builder.build_fallback_message())
                    continue

                # 执行第一个工具调用（单工具执行模式）
                tool = tool_calls[0]
                tool_name = tool["function"]["name"]
                tool_call_id = tool["id"]
                tool_args = json.loads(tool["function"]["arguments"])

                logger.info(f"AI 决定调用工具：{tool_name}, 参数：{tool_args}")

                # 执行工具
                tool_result = self._execute_tool(tool_name, tool_args, tool_call_id)

                # 保存工具结果
                self.messages.append(
                    self.prompt_builder.build_tool_result_message(
                        tool_name=tool_name,
                        tool_call_id=tool_call_id,
                        result=tool_result,
                    )
                )

                # 检查是否完成任务
                if tool_name == "task_complete":
                    task_completed = True
                    summary = tool_args.get("summary", "任务已完成")
                    logger.info(f"✅ 任务完成：{summary}")
                    break

            except Exception as e:
                logger.error(f"执行失败：{e}")
                last_error = str(e)
                # 继续尝试
                self.messages.append(
                    self.prompt_builder.build_user_message(
                        screen_info="错误：" + str(e),
                        step=self._current_step,
                        error_message=str(e),
                    )
                )

        # 循环结束检查
        if not task_completed:
            if self._current_step >= self.max_steps:
                logger.warning(f"⚠️ 已达最大步骤数 ({self.max_steps})，任务强制结束")
            else:
                logger.warning("⚠️ 任务未正常完成")

        # 保存日志
        summary = "任务完成" if task_completed else f"任务未完成（步骤：{self._current_step}, 错误：{last_error})"
        self._save_log(self.messages, summary)

        self._running = False
        return task_completed

    def stop(self):
        """停止代理运行。"""
        logger.info("停止代理运行...")
        self._running = False

    def __del__(self):
        """析构函数，清理资源。"""
        if hasattr(self, "llm_client"):
            self.llm_client.close()


def run_agent(
    task_name: str,
    adb_path: Optional[str] = None,
    device_serial: Optional[str] = None,
    api_provider: Optional[str] = None,
    max_steps: int = 50,
):
    """便捷函数，运行代理执行指定任务。

    Args:
        task_name: 任务名称
        adb_path: ADB 路径
        device_serial: 设备序列号
        api_provider: API 提供商
        max_steps: 最大步骤数

    Returns:
        任务是否成功完成
    """
    agent = DailyCheckAgent(
        task_name=task_name,
        adb_path=adb_path,
        device_serial=device_serial,
        api_provider=api_provider,
        max_steps=max_steps,
    )
    return agent.run()

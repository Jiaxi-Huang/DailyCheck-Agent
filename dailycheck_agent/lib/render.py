"""屏幕信息渲染模块 - 从 ADB 获取并渲染屏幕 UI 信息。"""

import subprocess
import time
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple


class ScreenRenderer:
    """屏幕渲染器，负责从 Android 设备获取 UI 层次结构信息。"""

    def __init__(
        self,
        adb_path: str,
        device_serial: Optional[str] = None,
        wait_time: float = 2.0,
    ):
        """初始化屏幕渲染器。

        Args:
            adb_path: ADB 可执行文件路径
            device_serial: 设备序列号，如果为 None 则使用默认连接设备
            wait_time: 执行操作后的等待时间（秒）
        """
        self.adb_path = adb_path
        self.device_serial = device_serial
        self.wait_time = wait_time
        self._screen_bounds: Optional[Tuple[int, int]] = None

    def _run_adb(self, command: List[str], shell: bool = False) -> subprocess.CompletedProcess:
        """运行 ADB 命令。

        Args:
            command: 命令参数列表
            shell: 是否使用 shell 模式

        Returns:
            CompletedProcess 实例
        """
        if self.device_serial:
            cmd = [self.adb_path, "-s", self.device_serial] + command
        else:
            cmd = [self.adb_path] + command

        return subprocess.run(cmd, capture_output=True, check=True, shell=shell)

    def get_screen_bounds(self) -> Tuple[int, int]:
        """获取屏幕分辨率。

        Returns:
            (width, height) 元组

        Raises:
            RuntimeError: 当无法获取屏幕分辨率时
        """
        if self._screen_bounds is not None:
            return self._screen_bounds

        try:
            result = self._run_adb(["shell", "wm size"])
            output = result.stdout.decode("utf-8", errors="ignore")
            # 解析 "Physical size: 1080x1920"
            for line in output.split("\n"):
                if "size:" in line:
                    parts = line.split(":")[-1].strip()
                    if "x" in parts:
                        w, h = parts.split("x")
                        self._screen_bounds = (int(w), int(h))
                        return self._screen_bounds
        except Exception as e:
            raise RuntimeError(f"无法获取屏幕分辨率：{e}")

        raise RuntimeError("无法解析屏幕分辨率")

    def get_screen_info(self) -> str:
        """快速获取屏幕 UI 元素信息。

        通过 uiautomator dump 获取当前屏幕的 UI 层次结构，
        提取所有带文本或描述的可交互元素。

        Returns:
            格式化的屏幕元素信息字符串

        Raises:
            RuntimeError: 当获取屏幕信息失败时
        """
        try:
            # 合并指令：dump 到临时文件 -> cat 输出 -> 清理
            cmd = [
                "shell",
                "uiautomator dump /data/local/tmp/v.xml > /dev/null && cat /data/local/tmp/v.xml",
            ]
            result = self._run_adb(cmd, shell=True)
            xml_str = result.stdout.decode("utf-8", errors="ignore")

            # 从第一个 '<' 开始解析，防止 dump 提示信息干扰
            start_idx = xml_str.find("<")
            if start_idx == -1:
                return "当前屏幕没有找到带文本的可交互元素。"

            root = ET.fromstring(xml_str[start_idx:])

            elements = []
            for node in root.iter():
                text = node.get("text", "")
                desc = node.get("content-desc", "")
                bounds = node.get("bounds", "")
                resource_id = node.get("resource-id", "")
                class_name = node.get("class", "")

                # 过滤：必须有文本/描述，且有坐标
                if (text or desc) and bounds:
                    # 解析坐标并计算中心点
                    center_x, center_y = self._parse_bounds(bounds)
                    if center_x is not None and center_y is not None:
                        element_info = self._format_element(
                            text, desc, resource_id, class_name, center_x, center_y, bounds
                        )
                        elements.append(element_info)

            if not elements:
                return "当前屏幕没有找到带文本的可交互元素。"

            # 获取屏幕分辨率用于参考
            try:
                width, height = self.get_screen_bounds()
                header = f"屏幕分辨率：{width}x{height}\n"
            except RuntimeError:
                header = ""

            return header + "\n".join(elements)

        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            raise RuntimeError(f"ADB 命令执行失败：{error_msg}")
        except ET.ParseError as e:
            raise RuntimeError(f"XML 解析失败：{e}")
        except Exception as e:
            raise RuntimeError(f"获取屏幕信息失败：{e}")

    def _parse_bounds(self, bounds: str) -> Tuple[Optional[int], Optional[int]]:
        """解析 bounds 字符串并返回中心坐标。

        Args:
            bounds: 格式为 "[x1,y1][x2,y2]" 的字符串

        Returns:
            (center_x, center_y) 元组，如果解析失败返回 (None, None)
        """
        try:
            # 解析 "[x1,y1][x2,y2]" 格式
            cleaned = bounds.replace("][", ",").replace("[", "").replace("]", "")
            x1, y1, x2, y2 = map(int, cleaned.split(","))
            center_x = (x1 + x2) // 2
            center_y = (y1 + y2) // 2
            return (center_x, center_y)
        except (ValueError, IndexError):
            return (None, None)

    def _format_element(
        self,
        text: str,
        desc: str,
        resource_id: str,
        class_name: str,
        center_x: int,
        center_y: int,
        bounds: str,
    ) -> str:
        """格式化单个元素信息。

        Args:
            text: 元素文本
            desc: 内容描述
            resource_id: 资源 ID
            class_name: 类名
            center_x: 中心 X 坐标
            center_y: 中心 Y 坐标
            bounds: 原始 bounds 字符串

        Returns:
            格式化的元素信息字符串
        """
        parts = []
        if text:
            parts.append(f"文本：'{text}'")
        if desc:
            parts.append(f"描述：'{desc}'")
        if resource_id:
            # 简化资源 ID，只保留最后一部分
            short_id = resource_id.split("/")[-1] if "/" in resource_id else resource_id
            parts.append(f"ID: {short_id}")
        if class_name:
            # 简化类名，只保留类名部分
            short_class = class_name.split(".")[-1] if "." in class_name else class_name
            parts.append(f"类型：{short_class}")

        parts.append(f"坐标：({center_x}, {center_y})")
        parts.append(f"区域：{bounds}")

        return ", ".join(parts)

    def tap(self, x: int, y: int) -> str:
        """执行屏幕点击操作。

        Args:
            x: X 坐标
            y: Y 坐标

        Returns:
            操作结果信息
        """
        try:
            self._run_adb(["shell", "input", "tap", str(x), str(y)])
            time.sleep(self.wait_time)
            return f"已点击坐标 ({x}, {y})"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            return f"点击失败：{error_msg}"

    def slide(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 300) -> str:
        """执行滑动操作。

        Args:
            start_x: 起始 X 坐标
            start_y: 起始 Y 坐标
            end_x: 结束 X 坐标
            end_y: 结束 Y 坐标
            duration: 滑动持续时间（毫秒）

        Returns:
            操作结果信息
        """
        try:
            self._run_adb(
                ["shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(duration)]
            )
            time.sleep(self.wait_time)
            return f"已从 ({start_x}, {start_y}) 滑动到 ({end_x}, {end_y})"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            return f"滑动失败：{error_msg}"

    def press_key(self, key_code: int) -> str:
        """按下系统按键。

        Args:
            key_code: 按键代码

        Returns:
            操作结果信息
        """
        try:
            self._run_adb(["shell", "input", "keyevent", str(key_code)])
            time.sleep(self.wait_time)
            return f"已按下按键 (code={key_code})"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            return f"按键失败：{error_msg}"

    def input_text(self, text: str) -> str:
        """输入文本。

        Args:
            text: 要输入的文本

        Returns:
            操作结果信息
        """
        try:
            # 使用 input text 命令输入文本（注意：不支持空格和特殊字符）
            # 对于复杂文本，可能需要使用 ime 输入
            escaped_text = text.replace(" ", "%s").replace("'", "\\'").replace('"', '\\"')
            self._run_adb(["shell", "input", "text", escaped_text])
            time.sleep(self.wait_time)
            return f"已输入文本：{text}"
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode("utf-8", errors="ignore") if e.stderr else str(e)
            return f"输入失败：{error_msg}"

    def get_screen_info_dict(self) -> Dict[str, Any]:
        """获取屏幕信息字典格式（用于更复杂的处理）。

        Returns:
            包含屏幕信息的字典
        """
        try:
            cmd = [
                "shell",
                "uiautomator dump /data/local/tmp/v.xml > /dev/null && cat /data/local/tmp/v.xml",
            ]
            result = self._run_adb(cmd, shell=True)
            xml_str = result.stdout.decode("utf-8", errors="ignore")

            start_idx = xml_str.find("<")
            if start_idx == -1:
                return {"elements": [], "resolution": self.get_screen_bounds()}

            root = ET.fromstring(xml_str[start_idx:])

            elements = []
            for node in root.iter():
                text = node.get("text", "")
                desc = node.get("content-desc", "")
                bounds = node.get("bounds", "")
                resource_id = node.get("resource-id", "")
                class_name = node.get("class", "")

                if (text or desc) and bounds:
                    center_x, center_y = self._parse_bounds(bounds)
                    if center_x is not None and center_y is not None:
                        elements.append(
                            {
                                "text": text,
                                "description": desc,
                                "resource_id": resource_id,
                                "class": class_name,
                                "bounds": bounds,
                                "center_x": center_x,
                                "center_y": center_y,
                            }
                        )

            return {"elements": elements, "resolution": self.get_screen_bounds()}

        except Exception:
            return {"elements": [], "resolution": (0, 0)}

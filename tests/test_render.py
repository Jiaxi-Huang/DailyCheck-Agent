"""ScreenRenderer 模块测试。"""

import pytest
from unittest.mock import MagicMock, patch, call

from dailycheck_agent.lib.render import ScreenRenderer


class TestScreenRendererInit:
    """测试 ScreenRenderer 初始化。"""

    def test_init_success(self):
        """测试成功初始化。"""
        renderer = ScreenRenderer(
            adb_path="/mock/adb",
            device_serial="test-serial",
            wait_time=1.5,
        )

        assert renderer.adb_path == "/mock/adb"
        assert renderer.device_serial == "test-serial"
        assert renderer.wait_time == 1.5
        assert renderer._screen_bounds is None

    def test_init_with_defaults(self):
        """测试使用默认参数初始化。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")

        assert renderer.device_serial is None
        assert renderer.wait_time == 2.0
        assert renderer._screen_bounds is None


class TestRunAdb:
    """测试 ADB 命令执行。"""

    def test_run_adb_without_serial(self, mock_subprocess):
        """测试不带设备序列号的 ADB 命令。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        renderer._run_adb(["shell", "echo", "test"])

        mock_subprocess.assert_called_once_with(
            ["/mock/adb", "shell", "echo", "test"],
            capture_output=True,
            check=True,
            shell=False,
        )

    def test_run_adb_with_serial(self, mock_subprocess):
        """测试带设备序列号的 ADB 命令。"""
        renderer = ScreenRenderer(
            adb_path="/mock/adb",
            device_serial="test-serial",
        )
        renderer._run_adb(["shell", "echo", "test"])

        mock_subprocess.assert_called_once_with(
            ["/mock/adb", "-s", "test-serial", "shell", "echo", "test"],
            capture_output=True,
            check=True,
            shell=False,
        )


class TestGetScreenBounds:
    """测试获取屏幕分辨率。"""

    def test_get_screen_bounds_success(self, mock_subprocess):
        """测试成功获取屏幕分辨率。"""
        mock_subprocess.return_value.stdout = b"Physical size: 1080x1920\n"

        renderer = ScreenRenderer(adb_path="/mock/adb")
        bounds = renderer.get_screen_bounds()

        assert bounds == (1080, 1920)

    def test_get_screen_bounds_cached(self, mock_subprocess):
        """测试屏幕分辨率缓存。"""
        mock_subprocess.return_value.stdout = b"Physical size: 1080x1920\n"

        renderer = ScreenRenderer(adb_path="/mock/adb")
        bounds1 = renderer.get_screen_bounds()
        bounds2 = renderer.get_screen_bounds()

        assert bounds1 == bounds2
        # 只调用了一次 ADB（使用了缓存）
        mock_subprocess.assert_called_once()

    def test_get_screen_bounds_alternative_format(self, mock_subprocess):
        """测试解析不同格式的输出。"""
        mock_subprocess.return_value.stdout = b"Some info\nPhysical size: 720x1280\nMore info\n"

        renderer = ScreenRenderer(adb_path="/mock/adb")
        bounds = renderer.get_screen_bounds()

        assert bounds == (720, 1280)

    def test_get_screen_bounds_failure(self, mock_subprocess):
        """测试获取屏幕分辨率失败。"""
        mock_subprocess.return_value.stdout = b"Invalid output\n"

        renderer = ScreenRenderer(adb_path="/mock/adb")

        with pytest.raises(RuntimeError, match="无法解析屏幕分辨率"):
            renderer.get_screen_bounds()


class TestGetScreenInfo:
    """测试获取屏幕 UI 信息。"""

    def test_get_screen_info_success(self, mock_subprocess, sample_xml_ui):
        """测试成功获取屏幕信息。"""
        mock_subprocess.return_value.stdout = sample_xml_ui.encode("utf-8")

        renderer = ScreenRenderer(adb_path="/mock/adb")
        # Mock get_screen_bounds 返回固定值
        renderer._screen_bounds = (1080, 1920)

        info = renderer.get_screen_info()

        assert "签到" in info
        assert "首页" in info
        assert "坐标" in info
        assert mock_subprocess.call_count == 2  # dump 和 cat

    def test_get_screen_info_empty(self, mock_subprocess):
        """测试空屏幕信息。"""
        mock_subprocess.return_value.stdout = b'<?xml version="1.0"?><hierarchy></hierarchy>'

        renderer = ScreenRenderer(adb_path="/mock/adb")
        info = renderer.get_screen_info()

        assert "没有找到带文本的可交互元素" in info

    def test_get_screen_info_invalid_xml(self, mock_subprocess):
        """测试无效 XML 的处理。"""
        # Return XML that starts with '<' but has invalid structure
        # This will cause ET.ParseError
        mock_subprocess.return_value.stdout = b'<?xml version="1.0"?><invalid><unclosed_tag></invalid>'

        renderer = ScreenRenderer(adb_path="/mock/adb")

        # ET.ParseError is caught and re-raised as RuntimeError
        with pytest.raises(RuntimeError):
            renderer.get_screen_info()

    def test_get_screen_info_adb_error(self, mock_subprocess):
        """测试 ADB 命令错误的处理。"""
        mock_subprocess.side_effect = Exception("ADB command failed")

        renderer = ScreenRenderer(adb_path="/mock/adb")

        with pytest.raises(RuntimeError):
            renderer.get_screen_info()


class TestParseBounds:
    """测试 bounds 解析。"""

    def test_parse_bounds_valid(self):
        """测试解析有效的 bounds。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        center = renderer._parse_bounds("[100,200][300,400]")

        assert center == (200, 300)

    def test_parse_bounds_invalid_format(self):
        """测试解析无效格式的 bounds。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        center = renderer._parse_bounds("invalid")

        assert center == (None, None)

    def test_parse_bounds_invalid_numbers(self):
        """测试解析包含无效数字的 bounds。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        center = renderer._parse_bounds("[a,b][c,d]")

        assert center == (None, None)


class TestFormatElement:
    """测试元素格式化。"""

    def test_format_element_basic(self):
        """测试基本元素格式化。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer._format_element(
            text="Click me",
            desc="",
            resource_id="com.test:id/button",
            class_name="android.widget.Button",
            center_x=100,
            center_y=200,
            bounds="[50,150][150,250]",
        )

        assert "文本：'Click me'" in result
        assert "坐标：(100, 200)" in result

    def test_format_element_with_description(self):
        """测试带描述的元素格式化。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer._format_element(
            text="",
            desc="A button",
            resource_id="",
            class_name="",
            center_x=50,
            center_y=100,
            bounds="[0,0][100,200]",
        )

        assert "描述：'A button'" in result

    def test_format_element_simplified_id(self):
        """测试简化资源 ID。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer._format_element(
            text="Test",
            desc="",
            resource_id="com.test:id/sign_in",
            class_name="",
            center_x=0,
            center_y=0,
            bounds="[0,0][0,0]",
        )

        assert "ID: sign_in" in result
        assert "com.test:id" not in result

    def test_format_element_simplified_class(self):
        """测试简化类名。"""
        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer._format_element(
            text="Test",
            desc="",
            resource_id="",
            class_name="android.widget.Button",
            center_x=0,
            center_y=0,
            bounds="[0,0][0,0]",
        )

        assert "类型：Button" in result
        assert "android.widget" not in result


class TestTap:
    """测试点击操作。"""

    def test_tap_success(self, mock_subprocess):
        """测试成功的点击操作。"""
        renderer = ScreenRenderer(adb_path="/mock/adb", wait_time=0.01)
        result = renderer.tap(100, 200)

        assert "已点击坐标 (100, 200)" in result
        mock_subprocess.assert_called_once_with(
            ["/mock/adb", "shell", "input", "tap", "100", "200"],
            capture_output=True,
            check=True,
            shell=False,
        )

    def test_tap_failure(self, mock_subprocess):
        """测试失败的点击操作。"""
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "tap", output=b"", stderr=b"Tap failed")

        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer.tap(100, 200)

        assert "点击失败" in result


class TestSlide:
    """测试滑动操作。"""

    def test_slide_success(self, mock_subprocess):
        """测试成功的滑动操作。"""
        renderer = ScreenRenderer(adb_path="/mock/adb", wait_time=0.01)
        result = renderer.slide(100, 200, 300, 400, duration=500)

        assert "已从 (100, 200) 滑动到 (300, 400)" in result
        mock_subprocess.assert_called_once_with(
            ["/mock/adb", "shell", "input", "swipe", "100", "200", "300", "400", "500"],
            capture_output=True,
            check=True,
            shell=False,
        )

    def test_slide_default_duration(self, mock_subprocess):
        """测试默认滑动持续时间。"""
        renderer = ScreenRenderer(adb_path="/mock/adb", wait_time=0.01)
        renderer.slide(0, 0, 100, 100)

        call_args = mock_subprocess.call_args[0][0]
        assert call_args[-1] == "300"  # 默认 duration

    def test_slide_failure(self, mock_subprocess):
        """测试失败的滑动操作。"""
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "slide", output=b"", stderr=b"Slide failed")

        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer.slide(0, 0, 100, 100)

        assert "滑动失败" in result


class TestPressKey:
    """测试按键操作。"""

    def test_press_key_success(self, mock_subprocess):
        """测试成功的按键操作。"""
        renderer = ScreenRenderer(adb_path="/mock/adb", wait_time=0.01)
        result = renderer.press_key(3)  # HOME key

        assert "已按下按键 (code=3)" in result
        mock_subprocess.assert_called_once_with(
            ["/mock/adb", "shell", "input", "keyevent", "3"],
            capture_output=True,
            check=True,
            shell=False,
        )

    def test_press_key_failure(self, mock_subprocess):
        """测试失败的按键操作。"""
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "keyevent", output=b"", stderr=b"Key press failed")

        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer.press_key(3)

        assert "按键失败" in result


class TestInputText:
    """测试文本输入操作。"""

    def test_input_text_success(self, mock_subprocess):
        """测试成功的文本输入。"""
        renderer = ScreenRenderer(adb_path="/mock/adb", wait_time=0.01)
        result = renderer.input_text("Hello")

        assert "已输入文本：Hello" in result
        mock_subprocess.assert_called_once()

    def test_input_text_with_spaces(self, mock_subprocess):
        """测试带空格的文本输入。"""
        renderer = ScreenRenderer(adb_path="/mock/adb", wait_time=0.01)
        renderer.input_text("Hello World")

        # 验证空格被转义
        call_args = mock_subprocess.call_args[0][0]
        assert "%s" in call_args[-1]  # 空格被替换为 %s

    def test_input_text_failure(self, mock_subprocess):
        """测试失败的文本输入。"""
        import subprocess
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "text", output=b"", stderr=b"Input failed")

        renderer = ScreenRenderer(adb_path="/mock/adb")
        result = renderer.input_text("Test")

        assert "输入失败" in result


class TestGetScreenInfoDict:
    """测试获取屏幕信息字典。"""

    def test_get_screen_info_dict_success(self, mock_subprocess, sample_xml_ui):
        """测试成功获取屏幕信息字典。"""
        mock_subprocess.return_value.stdout = sample_xml_ui.encode("utf-8")

        renderer = ScreenRenderer(adb_path="/mock/adb")
        renderer._screen_bounds = (1080, 1920)

        info = renderer.get_screen_info_dict()

        assert "elements" in info
        assert "resolution" in info
        assert len(info["elements"]) > 0

    def test_get_screen_info_dict_empty(self, mock_subprocess):
        """测试空屏幕信息字典。"""
        mock_subprocess.return_value.stdout = b'<?xml version="1.0"?><hierarchy></hierarchy>'

        renderer = ScreenRenderer(adb_path="/mock/adb")
        info = renderer.get_screen_info_dict()

        assert info["elements"] == []

"""
桌面悬浮窗划词解释工具 - 主入口

启动流程：
1. 创建 PyQt 应用
2. 初始化系统托盘图标
3. 启动全局热键监听
4. 等待用户划词 + 按 Shift → 弹出悬浮窗 → 调用 LLM → 流式渲染
"""

import sys
import pyautogui
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QObject, pyqtSignal

from config import load_config
from hotkey_listener import HotkeyListener
from llm_client import LLMStreamWorker
from floating_window import FloatingWindow
from settings_dialog import SettingsDialog
from tray_icon import TrayIcon, create_app_icon
from toast import ToastNotification


class AppController(QObject):
    """
    应用控制器 - 把所有模块串联起来的"总指挥"。

    标准解释：
    AppController 协调热键监听器、悬浮窗、LLM 客户端和系统托盘。
    现在额外支持将页面上下文一起传给 LLM，让解释更贴合语境。

    小学生解释：
    接线员升级了！以前只转达"用户选了什么字"，
    现在他还会附上一封信说"用户正在看这篇文章"，
    这样 AI 老爷爷就能结合文章给出更准确的解释了。
    """

    def __init__(self):
        super().__init__()

        self._floating_window = FloatingWindow()
        self._toast = ToastNotification()
        self._tray = TrayIcon()
        self._hotkey_listener = HotkeyListener()
        self._llm_worker = None

        self._connect_signals()

        self._hotkey_listener.start()
        self._tray.show()
        self._tray.showMessage(
            "悬浮词典已启动 ✨",
            "划选文字后按 Shift 键即可获取 AI 解释（已启用上下文感知）",
            self._tray.MessageIcon.Information,
            3000,
        )

    def _connect_signals(self):
        self._hotkey_listener.text_extracted.connect(self._on_text_extracted)
        self._hotkey_listener.no_text_selected.connect(self._on_no_text)
        self._tray.settings_requested.connect(self._show_settings)
        self._tray.quit_requested.connect(self._quit)
        self._floating_window.closed.connect(self._cancel_current_request)

    def _on_text_extracted(self, text: str, context: str, mouse_x: int, mouse_y: int):
        """收到提取的文本和上下文后，弹出悬浮窗并请求 LLM"""
        self._cancel_current_request()

        config = load_config()
        api_key = config.get("api_key", "").strip()

        if not api_key:
            self._floating_window.show_at(mouse_x, mouse_y)
            self._floating_window.show_error(
                "还没有配置 API Key 哦！<br>"
                "请右键点击右下角托盘图标 → 设置 → 填写 API Key 🔑"
            )
            return

        self._floating_window.show_at(mouse_x, mouse_y)

        self._llm_worker = LLMStreamWorker(
            api_key=api_key,
            api_base_url=config.get("api_base_url", "https://api.deepseek.com"),
            model_name=config.get("model_name", "deepseek-chat"),
            prompt=config.get("default_prompt", "请简明扼要地解释以下内容：\n\n{text}"),
            user_text=text,
            context=context,  # 传入上下文
        )

        self._llm_worker.token_received.connect(self._floating_window.append_token)
        self._llm_worker.stream_finished.connect(self._floating_window.finish_stream)
        self._llm_worker.error_occurred.connect(self._floating_window.show_error)
        self._llm_worker.start()

    def _on_no_text(self):
        mouse_x, mouse_y = pyautogui.position()
        self._toast.show_at(mouse_x, mouse_y)

    def _cancel_current_request(self):
        if self._llm_worker and self._llm_worker.isRunning():
            self._llm_worker.cancel()
            self._llm_worker.quit()
            self._llm_worker.wait(2000)
            self._llm_worker = None

    def _show_settings(self):
        dialog = SettingsDialog()
        dialog.exec()

    def _quit(self):
        self._hotkey_listener.stop()
        self._cancel_current_request()
        self._tray.hide()
        QApplication.instance().quit()


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(create_app_icon())
    controller = AppController()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

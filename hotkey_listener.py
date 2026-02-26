"""
全局热键监听 + 文本提取 + 上下文获取模块
监听 Shift 键释放事件，提取选中文本，并获取当前页面的上下文

上下文获取策略（多层回退）：
  1. Windows UI Automation (TextPattern / ValuePattern)
  2. Ctrl+A → Ctrl+C 剪贴板回退（适用于浏览器等 UIA 不生效的场景）
  3. 窗口标题兜底
"""

import time
import threading
import ctypes
import ctypes.wintypes
import keyboard
import pyautogui
from PyQt6.QtCore import QObject, pyqtSignal

# uiautomation 是可选依赖，导入失败时走剪贴板回退
try:
    import uiautomation as auto

    HAS_UIA = True
except ImportError:
    HAS_UIA = False


class HotkeyListener(QObject):
    """
    全局热键监听器（带上下文感知）。

    标准解释：
    1. 监听 Shift 键释放
    2. 模拟 Ctrl+C 提取选中文本
    3. 通过 UI Automation 或 Ctrl+A 剪贴板回退获取页面上下文
    4. 将（选中文本, 上下文, 鼠标坐标）一起发送给主线程

    小学生解释：
    小特工现在有两招获取你正在看的内容：
    - 第一招：用"透视眼"（UI Automation）直接读取屏幕上的文字
    - 第二招：如果透视眼不管用（比如微信文章页面），
      他就用"全选大法"——偷偷按 Ctrl+A 全选，再按 Ctrl+C 复制，
      这样就能拿到整篇文章了！然后再悄悄恢复原样。

    信号：
      text_extracted(str, str, int, int) - (选中文本, 上下文, 鼠标X, 鼠标Y)
      no_text_selected()                 - 未选中文字时发射
    """

    text_extracted = pyqtSignal(str, str, int, int)
    no_text_selected = pyqtSignal()

    # 上下文最短有效长度（低于此值视为获取失败，触发回退）
    MIN_CONTEXT_LENGTH = 30
    # 上下文最大长度（截断，避免 token 爆炸）
    MAX_CONTEXT_LENGTH = 5000

    def __init__(self, hotkey: str = "shift", parent=None):
        super().__init__(parent)
        self.hotkey = hotkey
        self._running = False
        self._last_trigger = 0
        self._cooldown = 0.6

    def start(self):
        self._running = True
        keyboard.on_release_key(self.hotkey, self._on_hotkey_released, suppress=False)

    def stop(self):
        self._running = False
        keyboard.unhook_all()

    def update_hotkey(self, new_hotkey: str):
        self.stop()
        self.hotkey = new_hotkey
        self.start()

    def _on_hotkey_released(self, event):
        if not self._running:
            return
        now = time.time()
        if now - self._last_trigger < self._cooldown:
            return
        self._last_trigger = now
        thread = threading.Thread(target=self._extract_text, daemon=True)
        thread.start()

    def _extract_text(self):
        """主提取流程：选中文本 + 上下文"""
        mouse_x, mouse_y = pyautogui.position()

        # ===== 第一步：获取选中文本 =====
        old_clipboard = self._get_clipboard_text()
        self._set_clipboard_text("")
        time.sleep(0.05)
        keyboard.send("ctrl+c")
        time.sleep(0.2)
        selected_text = self._get_clipboard_text()
        selected_text = selected_text.strip() if selected_text else ""

        if not selected_text:
            # 恢复剪贴板
            if old_clipboard:
                self._set_clipboard_text(old_clipboard)
            self.no_text_selected.emit()
            return

        # ===== 第二步：获取上下文 =====
        context = ""

        # 策略1：尝试 UI Automation
        if HAS_UIA:
            context = self._get_context_via_uia()

        # 策略2：如果 UIA 拿到的上下文太短，用 Ctrl+A 剪贴板回退
        if len(context) < self.MIN_CONTEXT_LENGTH:
            context = self._get_context_via_clipboard()

        # 策略3：兜底，至少返回窗口标题
        if len(context) < self.MIN_CONTEXT_LENGTH:
            context = self._get_window_title_context()

        # 截断
        if len(context) > self.MAX_CONTEXT_LENGTH:
            context = context[: self.MAX_CONTEXT_LENGTH] + "\n...(上下文已截断)"

        # 恢复剪贴板
        if old_clipboard:
            self._set_clipboard_text(old_clipboard)

        self.text_extracted.emit(selected_text, context.strip(), mouse_x, mouse_y)

    # ==================== 上下文获取策略 ====================

    def _get_context_via_uia(self) -> str:
        """策略1：通过 Windows UI Automation 获取上下文"""
        try:
            focused = auto.GetFocusedControl()
            if not focused:
                return ""

            # 尝试 TextPattern
            try:
                tp = focused.GetTextPattern()
                if tp:
                    text = tp.DocumentRange.GetText(self.MAX_CONTEXT_LENGTH)
                    if text and len(text) >= self.MIN_CONTEXT_LENGTH:
                        return text
            except Exception:
                pass

            # 尝试 ValuePattern
            try:
                vp = focused.GetValuePattern()
                if vp and vp.Value:
                    return vp.Value
            except Exception:
                pass

            # 尝试父控件
            try:
                parent = focused.GetParentControl()
                if parent:
                    tp = parent.GetTextPattern()
                    if tp:
                        text = tp.DocumentRange.GetText(self.MAX_CONTEXT_LENGTH)
                        if text and len(text) >= self.MIN_CONTEXT_LENGTH:
                            return text
            except Exception:
                pass

        except Exception:
            pass

        return ""

    def _get_context_via_clipboard(self) -> str:
        """
        策略2：通过 Ctrl+A → Ctrl+C 获取全页文本（剪贴板回退）。

        标准解释：
        保存当前剪贴板 → 模拟 Ctrl+A 全选 → Ctrl+C 复制 → 读取剪贴板
        → 按右方向键取消选择 → 恢复原始状态。

        小学生解释：
        小特工的"全选大法"：
        1. 先把剪贴板里的东西藏好
        2. 偷偷按 Ctrl+A 把整页文字都选上（全变蓝了）
        3. 再按 Ctrl+C 复制到剪贴板
        4. 把复制到的文字偷偷记下来
        5. 按一下右箭头键取消选择（页面恢复正常）
        6. 整个过程快到你根本看不见！
        """
        try:
            # 清空剪贴板
            self._set_clipboard_text("")
            time.sleep(0.05)

            # Ctrl+A 全选
            keyboard.send("ctrl+a")
            time.sleep(0.1)

            # Ctrl+C 复制
            keyboard.send("ctrl+c")
            time.sleep(0.25)

            # 读取全页文本
            full_text = self._get_clipboard_text()

            # 取消选择（按右箭头键，不会造成副作用）
            keyboard.send("right")
            time.sleep(0.05)

            return full_text.strip() if full_text else ""

        except Exception:
            return ""

    def _get_window_title_context(self) -> str:
        """策略3：获取当前窗口标题"""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buf = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buf, length + 1)
                return f"[当前窗口: {buf.value}]"
        except Exception:
            pass
        return ""

    # ==================== 剪贴板操作 ====================

    @staticmethod
    def _get_clipboard_text() -> str:
        CF_UNICODETEXT = 13
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return ""
        try:
            handle = user32.GetClipboardData(CF_UNICODETEXT)
            if not handle:
                return ""
            ptr = kernel32.GlobalLock(handle)
            if not ptr:
                return ""
            try:
                return ctypes.wstring_at(ptr)
            finally:
                kernel32.GlobalUnlock(handle)
        finally:
            user32.CloseClipboard()

    @staticmethod
    def _set_clipboard_text(text: str):
        CF_UNICODETEXT = 13
        GMEM_MOVEABLE = 0x0002
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        if not user32.OpenClipboard(0):
            return
        try:
            user32.EmptyClipboard()
            if text:
                byte_count = (len(text) + 1) * ctypes.sizeof(ctypes.c_wchar)
                handle = kernel32.GlobalAlloc(GMEM_MOVEABLE, byte_count)
                if not handle:
                    return
                ptr = kernel32.GlobalLock(handle)
                if not ptr:
                    return
                ctypes.memmove(ptr, text, byte_count)
                kernel32.GlobalUnlock(handle)
                user32.SetClipboardData(CF_UNICODETEXT, handle)
        finally:
            user32.CloseClipboard()

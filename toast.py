"""
Toast 通知模块
当用户未选中文字就按下热键时，显示一个轻量提示
"""

from PyQt6.QtWidgets import QLabel
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QColor, QPainter, QPainterPath, QBrush, QGuiApplication


class ToastNotification(QLabel):
    """
    轻量级 Toast 提示。

    就像手机上那种底部弹出来的小提示，
    告诉你"哎，你还没选文字呢"，然后 2 秒后自己消失。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFont(QFont("Microsoft YaHei UI", 11))
        self.setFixedSize(260, 44)
        self.setStyleSheet("color: transparent;")  # 由 paintEvent 控制

        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self.hide)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            0.0, 0.0, float(self.width()), float(self.height()), 12.0, 12.0
        )

        painter.fillPath(path, QBrush(QColor(40, 35, 60, 210)))
        painter.setPen(QColor(120, 100, 255, 60))
        painter.drawPath(path)

        # 绘制文字
        painter.setPen(QColor(220, 215, 240))
        painter.setFont(self.font())
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.text())

        painter.end()

    def show_at(
        self,
        x: int,
        y: int,
        message: str = "未检测到选中内容 📋",
        duration_ms: int = 2000,
    ):
        """在指定位置显示 Toast"""
        self.setText(message)

        # 调整位置避开屏幕边缘
        screen = QGuiApplication.primaryScreen()
        if screen:
            sr = screen.availableGeometry()
            pos_x = min(x, sr.right() - self.width())
            pos_y = min(y + 10, sr.bottom() - self.height())
            pos_x = max(sr.left(), pos_x)
            pos_y = max(sr.top(), pos_y)
        else:
            pos_x, pos_y = x, y + 10

        self.move(pos_x, pos_y)
        self.show()
        self._auto_hide_timer.start(duration_ms)

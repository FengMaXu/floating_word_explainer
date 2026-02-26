"""
系统托盘图标模块
在系统托盘显示图标，右键菜单提供设置和退出功能
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QBrush, QRadialGradient, QFont
from PyQt6.QtCore import Qt, QPoint, pyqtSignal


def create_app_icon() -> QIcon:
    """
    动态生成应用图标（紫色渐变圆形 + 文字）。
    就像画一个漂亮的紫色小徽章！
    """
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(0, 0, 0, 0))  # 透明背景

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # 紫色渐变圆
    gradient = QRadialGradient(size / 2, size / 2, size / 2)
    gradient.setColorAt(0, QColor(140, 120, 255))
    gradient.setColorAt(1, QColor(80, 60, 200))
    painter.setBrush(QBrush(gradient))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawEllipse(2, 2, size - 4, size - 4)

    # 文字 "词"
    painter.setPen(QColor(255, 255, 255))
    painter.setFont(QFont("Microsoft YaHei UI", 28, QFont.Weight.Bold))
    painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "词")

    painter.end()
    return QIcon(pixmap)


class TrayIcon(QSystemTrayIcon):
    """
    系统托盘图标。

    想象成任务栏右下角的一个小徽章：
    - 它安静地待在那里，告诉你程序在运行
    - 右键点击它，可以打开设置或退出程序
    """

    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setIcon(create_app_icon())
        self.setToolTip("悬浮词典 - 划词即解释")
        self._setup_menu()

    def _setup_menu(self):
        """创建右键菜单"""
        menu = QMenu()

        settings_action = menu.addAction("⚙️ 设置")
        settings_action.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()

        quit_action = menu.addAction("❌ 退出")
        quit_action.triggered.connect(self.quit_requested.emit)

        self.setContextMenu(menu)

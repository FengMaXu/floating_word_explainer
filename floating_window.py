"""
悬浮窗 UI 模块
毛玻璃效果、Markdown 渲染、跟随鼠标、可拖动、关闭按钮、自动隐藏
"""

import markdown
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextBrowser,
    QLabel,
    QPushButton,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, QPoint, pyqtSignal, QEvent
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QBrush,
    QPainterPath,
    QFont,
    QGuiApplication,
    QCursor,
)


class FloatingWindow(QWidget):
    """
    毛玻璃悬浮窗。

    标准解释：
    无边框置顶窗口，带圆角半透明背景、Markdown渲染、可拖动、关闭按钮，
    通过定时器检测焦点丢失实现自动关闭。

    小学生解释：
    一个半透明的魔法小窗口：
    - 你可以拖着它到处跑
    - 右上角有个 × 可以关掉它
    - 你点别的地方它就自己消失了
    - 文字会像打字机一样蹦出来
    """

    closed = pyqtSignal()

    WINDOW_WIDTH = 420
    WINDOW_MIN_HEIGHT = 100
    WINDOW_MAX_HEIGHT = 450
    CORNER_RADIUS = 16
    MARGIN = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_window_flags()
        self._setup_ui()
        self._accumulated_text = ""
        self._loading = False

        # 拖动相关
        self._dragging = False
        self._drag_start_pos = QPoint()

        # 呼吸灯动画
        self._breathing_opacity = 0.5
        self._breathing_direction = 1
        self._breathing_timer = QTimer(self)
        self._breathing_timer.timeout.connect(self._update_breathing)

        # 焦点检测定时器
        self._focus_timer = QTimer(self)
        self._focus_timer.timeout.connect(self._check_focus)

    def _setup_window_flags(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(self.WINDOW_WIDTH)
        self.setMinimumHeight(self.WINDOW_MIN_HEIGHT)
        self.setMaximumHeight(self.WINDOW_MAX_HEIGHT)

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 12, 20, 16)
        main_layout.setSpacing(6)

        # ===== 顶部栏 =====
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        title_label = QLabel("✨ 悬浮词典")
        title_label.setFont(QFont("Microsoft YaHei UI", 9))
        title_label.setStyleSheet("color: #9a90c8;")
        top_bar.addWidget(title_label)
        top_bar.addStretch()

        # 关闭按钮
        self._close_btn = QPushButton("✕")
        self._close_btn.setFixedSize(24, 24)
        self._close_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._close_btn.setStyleSheet(
            """
            QPushButton {
                background: transparent;
                color: #a09ad2;
                border: none;
                border-radius: 12px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #cc4444;
                color: white;
            }
        """
        )
        self._close_btn.clicked.connect(self._close)
        top_bar.addWidget(self._close_btn)
        main_layout.addLayout(top_bar)

        # ===== 加载提示 =====
        self._loading_label = QLabel("正在思考...")
        self._loading_label.setFont(QFont("Microsoft YaHei UI", 10))
        self._loading_label.setStyleSheet("color: #b4b4dc;")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self._loading_label)

        # ===== Markdown 内容区 =====
        self._text_browser = QTextBrowser()
        self._text_browser.setOpenExternalLinks(True)
        self._text_browser.setFont(QFont("Microsoft YaHei UI", 10))
        self._text_browser.setStyleSheet(
            """
            QTextBrowser {
                background: transparent;
                border: none;
                color: #e6e6f5;
            }
            QScrollBar:vertical {
                background: transparent;
                width: 6px;
                margin: 4px 1px;
            }
            QScrollBar::handle:vertical {
                background: #6650c8;
                border-radius: 3px;
                min-height: 20px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        """
        )
        self._text_browser.hide()
        main_layout.addWidget(self._text_browser)

    # ==================== 绘制 ====================

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        path = QPainterPath()
        path.addRoundedRect(
            0.0,
            0.0,
            float(self.width()),
            float(self.height()),
            self.CORNER_RADIUS,
            self.CORNER_RADIUS,
        )
        # 深色半透明背景
        painter.fillPath(path, QBrush(QColor(25, 22, 40, 225)))
        # 边框
        painter.setPen(QColor(100, 80, 200, 50))
        painter.drawPath(path)
        painter.end()

    # ==================== 拖动 ====================

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._dragging = True
            self._drag_start_pos = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )
            event.accept()

    def mouseMoveEvent(self, event):
        if self._dragging and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_start_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._dragging = False
        event.accept()

    # ==================== 显示与内容 ====================

    def show_at(self, x: int, y: int):
        self._accumulated_text = ""
        self._text_browser.clear()
        self._text_browser.hide()
        self._loading_label.show()
        self._loading = True
        self.setFixedHeight(self.WINDOW_MIN_HEIGHT)

        screen = QGuiApplication.primaryScreen()
        if screen:
            sr = screen.availableGeometry()
            pos_x = x + self.MARGIN
            pos_y = y + self.MARGIN
            if pos_x + self.WINDOW_WIDTH > sr.right():
                pos_x = x - self.WINDOW_WIDTH - self.MARGIN
            if pos_y + self.WINDOW_MIN_HEIGHT > sr.bottom():
                pos_y = y - self.WINDOW_MIN_HEIGHT - self.MARGIN
            pos_x = max(sr.left(), pos_x)
            pos_y = max(sr.top(), pos_y)
        else:
            pos_x, pos_y = x + self.MARGIN, y + self.MARGIN

        self.move(pos_x, pos_y)
        self.show()
        self.raise_()
        self.activateWindow()
        self._start_breathing()
        self._focus_timer.start(300)

    def append_token(self, token: str):
        if self._loading:
            self._loading = False
            self._loading_label.hide()
            self._text_browser.show()
            self._stop_breathing()

        self._accumulated_text += token
        html = self._render_markdown(self._accumulated_text)
        self._text_browser.setHtml(html)

        scrollbar = self._text_browser.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self._adjust_height()

    def show_error(self, error_msg: str):
        self._loading = False
        self._loading_label.hide()
        self._text_browser.show()
        self._stop_breathing()
        self._text_browser.setHtml(
            f'<div style="color: #ff6b6b; font-size: 13px; '
            f'line-height: 1.6;">{error_msg}</div>'
        )
        self._adjust_height()

    def finish_stream(self):
        self._stop_breathing()

    # ==================== Markdown ====================

    def _render_markdown(self, text: str) -> str:
        html = markdown.markdown(text, extensions=["fenced_code", "tables", "nl2br"])
        return f"""
        <style>
            body {{
                font-family: 'Microsoft YaHei UI', sans-serif;
                font-size: 13px;
                line-height: 1.7;
                color: #e6e6f5;
            }}
            code {{
                background: #2e2650;
                padding: 2px 6px;
                border-radius: 4px;
                font-family: 'Cascadia Code', 'Consolas', monospace;
                font-size: 12px;
                color: #c8b6ff;
            }}
            pre {{
                background: #0f0c1e;
                padding: 12px;
                border-radius: 8px;
                overflow-x: auto;
            }}
            pre code {{ background: transparent; padding: 0; }}
            strong {{ color: #b8a9ff; }}
            h1, h2, h3 {{ color: #d4c8ff; margin: 8px 0 4px 0; }}
            a {{ color: #8b7bff; }}
            blockquote {{
                border-left: 3px solid #6450c8;
                padding-left: 12px;
                color: #c8c8dc;
                margin: 8px 0;
            }}
            table {{ border-collapse: collapse; width: 100%; }}
            th, td {{
                border: 1px solid #3c3264;
                padding: 6px 10px;
                text-align: left;
            }}
            th {{ background: #2e2450; }}
        </style>
        {html}
        """

    # ==================== 工具方法 ====================

    def _adjust_height(self):
        doc_height = self._text_browser.document().size().height()
        desired = int(doc_height) + 60
        desired = max(self.WINDOW_MIN_HEIGHT, min(desired, self.WINDOW_MAX_HEIGHT))
        self.setFixedHeight(desired)

    def _start_breathing(self):
        self._breathing_timer.start(50)

    def _stop_breathing(self):
        self._breathing_timer.stop()
        self._loading_label.setStyleSheet("color: #b4b4dc;")

    def _update_breathing(self):
        self._breathing_opacity += 0.03 * self._breathing_direction
        if self._breathing_opacity >= 1.0:
            self._breathing_direction = -1
        elif self._breathing_opacity <= 0.3:
            self._breathing_direction = 1
        alpha = int(self._breathing_opacity * 255)
        alpha = max(0, min(255, alpha))
        self._loading_label.setStyleSheet(f"color: rgba(180, 180, 220, {alpha});")

    # ==================== 关闭与焦点 ====================

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._close()
        super().keyPressEvent(event)

    def _check_focus(self):
        if self.isVisible() and not self.isActiveWindow():
            self._close()

    def _close(self):
        self._focus_timer.stop()
        self._stop_breathing()
        self.hide()
        self.closed.emit()

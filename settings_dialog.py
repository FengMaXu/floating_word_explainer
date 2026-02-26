"""
设置面板模块
API Key、Base URL、模型名称配置对话框
"""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QGroupBox,
    QFormLayout,
    QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from config import load_config, save_config


class SettingsDialog(QDialog):
    """
    设置面板。

    就像游戏里的"设置菜单"：
    - 你在这里填写 AI 的"地址"和"密码"（API Key）
    - 告诉程序你想用哪个 AI 模型
    - 还可以自定义你想让 AI 怎么回答你
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ 设置 - 悬浮词典")
        self.setFixedSize(500, 520)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)

        self._setup_ui()
        self._load_current_config()

    def _setup_ui(self):
        """构建设置界面"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(24, 20, 24, 20)

        # ===== AI 接口配置 =====
        api_group = QGroupBox("🤖 AI 接口配置")
        api_group.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        api_layout = QFormLayout()
        api_layout.setSpacing(12)
        api_layout.setContentsMargins(16, 20, 16, 16)

        self._api_key_input = QLineEdit()
        self._api_key_input.setPlaceholderText("sk-xxxxxxxxxxxxxxxx")
        self._api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        api_layout.addRow("API Key：", self._api_key_input)

        self._base_url_input = QLineEdit()
        self._base_url_input.setPlaceholderText("https://api.deepseek.com")
        api_layout.addRow("接口地址：", self._base_url_input)

        self._model_input = QLineEdit()
        self._model_input.setPlaceholderText("deepseek-chat")
        api_layout.addRow("模型名称：", self._model_input)

        api_group.setLayout(api_layout)
        main_layout.addWidget(api_group)

        # ===== Prompt 模板 =====
        prompt_group = QGroupBox("📝 提示词模板")
        prompt_group.setFont(QFont("Microsoft YaHei UI", 10, QFont.Weight.Bold))
        prompt_layout = QVBoxLayout()
        prompt_layout.setContentsMargins(16, 20, 16, 16)

        hint_label = QLabel("使用 {text} 作为选中文字的占位符")
        hint_label.setStyleSheet("color: gray; font-size: 11px;")
        prompt_layout.addWidget(hint_label)

        self._prompt_input = QTextEdit()
        self._prompt_input.setFont(QFont("Microsoft YaHei UI", 9))
        self._prompt_input.setMaximumHeight(120)
        prompt_layout.addWidget(self._prompt_input)

        prompt_group.setLayout(prompt_layout)
        main_layout.addWidget(prompt_group)

        # ===== 按钮区 =====
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton("取消")
        cancel_btn.setFixedSize(90, 36)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton("💾 保存")
        save_btn.setFixedSize(90, 36)
        save_btn.setDefault(True)
        save_btn.setStyleSheet(
            """
            QPushButton {
                background-color: #6c5ce7;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7d6ff0;
            }
        """
        )
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        main_layout.addLayout(btn_layout)

        # ===== 整体样式 =====
        self.setStyleSheet(
            """
            QDialog {
                background-color: #1e1e2e;
                color: #cdd6f4;
            }
            QGroupBox {
                border: 1px solid rgba(120, 100, 255, 60);
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 8px;
                color: #cdd6f4;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 6px;
            }
            QLineEdit, QTextEdit {
                background-color: #2a2a3e;
                border: 1px solid rgba(120, 100, 255, 40);
                border-radius: 6px;
                padding: 8px;
                color: #cdd6f4;
                font-size: 13px;
            }
            QLineEdit:focus, QTextEdit:focus {
                border-color: #6c5ce7;
            }
            QLabel {
                color: #bac2de;
                font-size: 13px;
            }
            QPushButton {
                background-color: #313244;
                color: #cdd6f4;
                border: 1px solid rgba(120, 100, 255, 40);
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #45475a;
            }
        """
        )

    def _load_current_config(self):
        """加载当前配置到表单"""
        config = load_config()
        self._api_key_input.setText(config.get("api_key", ""))
        self._base_url_input.setText(config.get("api_base_url", ""))
        self._model_input.setText(config.get("model_name", ""))
        self._prompt_input.setPlainText(config.get("default_prompt", ""))

    def _save(self):
        """保存配置"""
        api_key = self._api_key_input.text().strip()
        if not api_key:
            QMessageBox.warning(self, "提示", "请填写 API Key 哦！")
            return

        config = load_config()
        config["api_key"] = api_key
        config["api_base_url"] = (
            self._base_url_input.text().strip() or "https://api.deepseek.com"
        )
        config["model_name"] = self._model_input.text().strip() or "deepseek-chat"
        config["default_prompt"] = (
            self._prompt_input.toPlainText().strip() or config["default_prompt"]
        )

        save_config(config)
        self.accept()

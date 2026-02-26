"""
配置管理模块
负责读取和保存用户配置（API Key、模型地址、Prompt 等）
"""

import json
import os
from pathlib import Path

from default_config import DEFAULT_CONFIG

# 配置文件路径：用户目录下的 .floating_word_explainer/config.json
CONFIG_DIR = Path.home() / ".floating_word_explainer"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    """加载配置文件，不存在则返回默认配置"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            # 合并默认值（防止新增配置项缺失）
            merged = {**DEFAULT_CONFIG, **saved}
            return merged
        except (json.JSONDecodeError, IOError):
            return DEFAULT_CONFIG.copy()
    return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """保存配置到文件"""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

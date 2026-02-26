"""
默认配置常量
所有可配置项的默认值集中管理在这里

敏感信息（API Key 等）从 .env 文件加载
系统提示词从 system_prompt.txt 加载
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv(Path(__file__).parent / ".env")

# 加载系统提示词
_prompt_file = Path(__file__).parent / "system_prompt.txt"
if _prompt_file.exists():
    _default_prompt = _prompt_file.read_text(encoding="utf-8").strip()
else:
    _default_prompt = "请简明扼要地解释以下内容：\n\n{text}"

# 默认配置
DEFAULT_CONFIG = {
    "api_key": os.getenv("API_KEY", ""),
    "api_base_url": os.getenv("API_BASE_URL", "https://api.deepseek.com"),
    "model_name": os.getenv("MODEL_NAME", "deepseek-chat"),
    "default_prompt": _default_prompt,
    "hotkey": "shift",
    "theme": "auto",  # auto / dark / light
}

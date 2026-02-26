"""
LLM 流式调用客户端
使用 httpx 发送 OpenAI 兼容格式的流式请求，支持传入上下文
"""

import json
import httpx
from PyQt6.QtCore import QThread, pyqtSignal


class LLMStreamWorker(QThread):
    """
    在后台线程中调用 LLM API，逐 token 发送给 UI。

    信号：
      token_received(str)  - 每收到一段新文本时发射
      stream_finished()    - 流式输出完成
      error_occurred(str)  - 出错时发射错误信息
    """

    token_received = pyqtSignal(str)
    stream_finished = pyqtSignal()
    error_occurred = pyqtSignal(str)

    def __init__(
        self,
        api_key: str,
        api_base_url: str,
        model_name: str,
        prompt: str,
        user_text: str,
        context: str = "",
        parent=None,
    ):
        super().__init__(parent)
        self.api_key = api_key
        self.api_base_url = api_base_url.rstrip("/")
        self.model_name = model_name
        self.prompt = prompt
        self.user_text = user_text
        self.context = context
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        # 组装 Prompt：替换占位符
        full_prompt = self.prompt.replace("{text}", self.user_text)
        full_prompt = full_prompt.replace("{context}", self.context)

        messages = [{"role": "user", "content": full_prompt}]

        url = f"{self.api_base_url}/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model_name,
            "messages": messages,
            "stream": True,
        }

        try:
            with httpx.Client(timeout=60.0) as client:
                with client.stream(
                    "POST", url, headers=headers, json=payload
                ) as response:
                    if response.status_code != 200:
                        error_body = response.read().decode("utf-8", errors="replace")
                        if response.status_code == 401:
                            self.error_occurred.emit(
                                "API 密钥好像填错了哦，请去右下角设置里检查一下 🔑"
                            )
                        elif response.status_code == 404:
                            self.error_occurred.emit(
                                f"模型 '{self.model_name}' 不存在，请在设置中检查模型名称 🤔"
                            )
                        else:
                            self.error_occurred.emit(
                                f"请求失败 (HTTP {response.status_code})：{error_body[:200]}"
                            )
                        return

                    for line in response.iter_lines():
                        if self._cancelled:
                            return
                        if not line or not line.startswith("data: "):
                            continue
                        data_str = line[6:]
                        if data_str.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                self.token_received.emit(content)
                        except json.JSONDecodeError:
                            continue

            if not self._cancelled:
                self.stream_finished.emit()

        except httpx.ConnectError:
            self.error_occurred.emit(
                "无法连接到 AI 服务器，请检查网络或 API 地址是否正确 🌐"
            )
        except httpx.TimeoutException:
            self.error_occurred.emit("请求超时，AI 服务器响应太慢了 ⏱️")
        except Exception as e:
            self.error_occurred.emit(f"发生未知错误：{str(e)}")

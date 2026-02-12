import os
from typing import Optional, Tuple

import requests


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str) -> None:
        self.token = token
        self.chat_id = chat_id

    @classmethod
    def from_env(cls) -> "TelegramNotifier":
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")
        if not token or not chat_id:
            raise RuntimeError("TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set")
        return cls(token, chat_id)

    def send_open_alert(self, country: str, source_url: str, status: str) -> Tuple[str, Optional[str]]:
        text = f"{country} WHV 462 status: {status}\nLink: {source_url}"
        provider, message_id = self._send_text(text)
        login_url = os.environ.get("LOGIN_URL")
        self._send_text(login_url)
        return provider, message_id

    def send_test_alert(self, country: str, source_url: str, status: str, test_run_id: str) -> Tuple[str, Optional[str]]:
        text = (
            f"[TESTE SUPABASE CRON {test_run_id}]\n"
            f"{country} WHV 462 status: {status}\n"
            f"Link: {source_url}"
        )
        return self._send_text(text)

    def _send_text(self, text: str) -> Tuple[str, Optional[str]]:
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        r = requests.post(url, json=payload, timeout=20)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            raise RuntimeError(f"Telegram API error {r.status_code}: {r.text}")
        data = r.json()
        message_id = None
        if isinstance(data, dict):
            result = data.get("result")
            if isinstance(result, dict):
                message_id = str(result.get("message_id")) if result.get("message_id") is not None else None
        return "telegram", message_id

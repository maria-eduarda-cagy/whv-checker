import os
from typing import Optional, Tuple

import requests


class ResendNotifier:
    def __init__(self, api_key: str, recipient: str, sender: Optional[str] = None) -> None:
        self.api_key = api_key
        self.recipient = recipient
        self.sender = sender or "WHV 462 Monitor <onboarding@resend.dev>"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    @classmethod
    def from_env(cls) -> "ResendNotifier":
        api_key = os.environ.get("EMAIL_PROVIDER_API_KEY")
        recipient = os.environ.get("ALERT_RECIPIENT_EMAIL")
        sender = os.environ.get("ALERT_SENDER_EMAIL")
        if not api_key or not recipient:
            raise RuntimeError("EMAIL_PROVIDER_API_KEY and ALERT_RECIPIENT_EMAIL must be set")
        return cls(api_key, recipient, sender)

    def send_open_alert(self, country: str, source_url: str, current_status: str) -> Tuple[str, Optional[str]]:
        subject = f"{country} está {current_status.upper()} para WHV 462"
        text = (
            f"Status atualizado: {country} -> {current_status}\n\n"
            f"Fonte: {source_url}\n"
            f"Este alerta foi enviado automaticamente quando o status mudou para OPEN."
        )
        payload = {"from": self.sender, "to": [self.recipient], "subject": subject, "text": text}
        r = self.session.post("https://api.resend.com/emails", json=payload, timeout=20)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            try:
                err_json = r.json()
                err_msg = err_json.get("error") or err_json
            except Exception:
                err_msg = r.text
            raise RuntimeError(f"Resend error {r.status_code}: {err_msg}")
        data = r.json()
        message_id = data.get("id")
        provider = "resend"
        return provider, message_id

    def send_test_email(self, subject: Optional[str] = None, text: Optional[str] = None) -> Tuple[str, Optional[str]]:
        subject = subject or "Teste de conexão WHV 462"
        text = text or "Este é um e-mail de teste para verificar a integração com o provedor de e-mail."
        payload = {"from": self.sender, "to": [self.recipient], "subject": subject, "text": text}
        r = self.session.post("https://api.resend.com/emails", json=payload, timeout=20)
        try:
            r.raise_for_status()
        except requests.HTTPError:
            try:
                err_json = r.json()
                err_msg = err_json.get("error") or err_json
            except Exception:
                err_msg = r.text
            raise RuntimeError(f"Resend error {r.status_code}: {err_msg}")
        data = r.json()
        message_id = data.get("id")
        provider = "resend"
        return provider, message_id

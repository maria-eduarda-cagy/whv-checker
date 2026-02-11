import os
import json
import time
from typing import Dict, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from .parser import parse_country_status


STATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")
SOURCE_URL = "https://immi.homeaffairs.gov.au/what-we-do/whm-program/status-of-country-caps"
TARGET_COUNTRY = "Brazil"


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(total=2, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504], allowed_methods=["GET"])
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9,pt-BR;q=0.8",
            "Referer": "https://immi.homeaffairs.gov.au/what-we-do/whm-program/",
        }
    )
    return s


def _load_state() -> Dict[str, Optional[str]]:
    if not os.path.exists(STATE_PATH):
        return {"last_status": None, "last_checked_at": None, "last_notified_status": None}
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except Exception:
            return {"last_status": None, "last_checked_at": None, "last_notified_status": None}


def _save_state(state: Dict[str, Optional[str]]) -> None:
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _normalize(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    t = s.strip().lower().replace("*", "")
    if "open" in t:
        return "open"
    if "paused" in t or "pause" in t:
        return "paused"
    if "closed" in t or "close" in t:
        return "closed"
    return None


def send_telegram(status: str, timestamp_iso: str) -> bool:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Aviso: TELEGRAM_BOT_TOKEN/TELEGRAM_CHAT_ID ausentes, nenhuma notificação enviada")
        return False
    text = f"Brazil WHV 462 status: {status}\nTime: {timestamp_iso}\nLink: {SOURCE_URL}"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.ok:
            return True
        print(f"Erro Telegram: {r.status_code} {r.text}")
        return False
    except Exception as e:
        print(f"Erro Telegram: {e}")
        return False


def main() -> int:
    state = _load_state()
    session = _session()
    try:
        resp = session.get(SOURCE_URL, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        print(f"Erro HTTP: {e}")
        return 1
    status, raw, err = parse_country_status(html, TARGET_COUNTRY)
    if err or not status:
        print(f"Erro parsing: {err or 'status vazio'}")
        return 1
    status = _normalize(status)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    print(f"Status atual: {status}")
    notified = False
    if status == "open" and state.get("last_notified_status") != "open":
        notified = send_telegram(status, ts)
        if notified:
            state["last_notified_status"] = "open"
    state["last_status"] = status
    state["last_checked_at"] = ts
    _save_state(state)
    print(f"Notificou: {str(notified).lower()}")
    return 0


if __name__ == "__main__":
    exit(main())

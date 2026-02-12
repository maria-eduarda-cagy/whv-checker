import os
import uuid
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .db import SupabaseClient
from .notify import TelegramNotifier
from .parser import parse_country_status

def _session_with_retries() -> requests.Session:
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


def run_check(force_notify_test: bool = False) -> Dict[str, Optional[str]]:
    source_url = os.environ.get(
        "SOURCE_URL",
        "https://immi.homeaffairs.gov.au/what-we-do/whm-program/status-of-country-caps",
    )
    target_country = os.environ.get("TARGET_COUNTRY", "Brazil")
    session = _session_with_retries()

    html = None
    fetch_error = None
    try:
        resp = session.get(source_url, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        fetch_error = f"HTTP error: {e}"

    status, raw_excerpt, parse_error = (None, None, None)
    if html:
        status, raw_excerpt, parse_error = parse_country_status(html, target_country)

    # Required for global dedupe across GitHub Actions and Supabase Scheduler.
    sb = SupabaseClient.from_env()
    sb.insert_status_check(
        country=target_country,
        status=status,
        source_url=source_url,
        raw_excerpt=raw_excerpt,
        error=parse_error or fetch_error,
    )

    if fetch_error or parse_error or not status:
        return {
            "status": status,
            "action": "logged_error",
            "error": parse_error or fetch_error or "status_empty",
            "mode": "live",
        }

    last = sb.get_last_state(target_country)
    previous_status = last["status"] if last and "status" in last else None
    last_notified_status = last["last_notified_status"] if last else None

    sb.upsert_last_state(target_country, status, last_notified_status=last_notified_status)

    notified = False
    provider = None
    provider_message_id = None
    if force_notify_test:
        notifier = TelegramNotifier.from_env()
        test_run_id = uuid.uuid4().hex[:8]
        provider, provider_message_id = notifier.send_test_alert(target_country, source_url, status, test_run_id)
        notified = True
        sb.insert_notification(
            country=target_country,
            status=status,
            recipient=notifier.chat_id,
            provider=provider,
            provider_message_id=provider_message_id,
        )
    elif status == "open" and (previous_status != "open" or last_notified_status != "open"):
        notifier = TelegramNotifier.from_env()
        provider, provider_message_id = notifier.send_open_alert(target_country, source_url, status)
        notified = True
        sb.insert_notification(
            country=target_country,
            status=status,
            recipient=notifier.chat_id,
            provider=provider,
            provider_message_id=provider_message_id,
        )
        sb.upsert_last_state(target_country, status, last_notified_status="open")

    return {
        "status": status,
        "previous_status": previous_status,
        "changed": str(previous_status != status).lower(),
        "notified": str(notified).lower(),
        "provider": provider,
        "provider_message_id": provider_message_id,
        "raw_excerpt": raw_excerpt,
        "mode": "live",
        "test_mode": str(force_notify_test).lower(),
    }


def main() -> int:
    result = run_check()
    print(result)
    return 0 if result.get("action") != "logged_error" else 1


if __name__ == "__main__":
    exit(main())

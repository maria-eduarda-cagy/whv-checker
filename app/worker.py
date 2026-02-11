import os
from typing import Dict, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .parser import parse_country_status
from .db import SupabaseClient
from .notify import ResendNotifier


def _session_with_retries() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=0.5,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-AU,en;q=0.9,pt-BR;q=0.8",
            "Referer": "https://immi.homeaffairs.gov.au/what-we-do/whm-program/",
        }
    )
    return session


def run_check() -> Dict[str, Optional[str]]:
    session = _session_with_retries()

    source_url = os.environ.get(
        "SOURCE_URL",
        "https://immi.homeaffairs.gov.au/what-we-do/whm-program/status-of-country-caps",
    )
    target_country = os.environ.get("TARGET_COUNTRY", "Brazil")

    # 1) Fetch HTML
    html = None
    fetch_error = None
    try:
        resp = session.get(source_url, timeout=10)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        fetch_error = f"HTTP error: {e}"

    # 2) Parse status
    status, raw_excerpt, parse_error = (None, None, None)
    if html:
        status, raw_excerpt, parse_error = parse_country_status(html, target_country)

    # 3) Persist check log (if Supabase env está presente)
    sb = None
    try:
        sb = SupabaseClient.from_env()
        sb.insert_status_check(
            country=target_country,
            status=status,
            source_url=source_url,
            raw_excerpt=raw_excerpt,
            error=parse_error or fetch_error,
        )
    except Exception:
        sb = None

    if fetch_error or parse_error or not status:
        return {
            "status": status,
            "action": "logged_error" if sb else "dry_run_error",
            "error": parse_error or fetch_error,
        }

    # 4) Compare with last state
    previous_status = None
    last_notified_status = None
    if sb:
        last = sb.get_last_state(target_country)
        previous_status = last["status"] if last and "status" in last else None
        last_notified_status = last["last_notified_status"] if last else None

    # 5) Update last state (idempotent upsert)
    if sb:
        sb.upsert_last_state(target_country, status, last_notified_status=last_notified_status)

    changed = previous_status != status

    # 6) Deduped notification logic
    sent_notification = False
    provider = None
    provider_message_id = None
    if status == "open" and (previous_status != "open" or last_notified_status != "open"):
        try:
            notifier = ResendNotifier.from_env()
            provider, provider_message_id = notifier.send_open_alert(target_country, source_url, status)
            sent_notification = True
            if sb:
                sb.insert_notification(
                    country=target_country,
                    status=status,
                    recipient=notifier.recipient,
                    provider=provider,
                    provider_message_id=provider_message_id,
                )
                # Update last_notified_status to 'open'
                sb.upsert_last_state(target_country, status, last_notified_status="open")
        except Exception:
            # Sem variáveis de email em ambiente local: apenas reporta que não notificou
            sent_notification = False

    return {
        "status": status,
        "previous_status": previous_status,
        "changed": str(changed).lower(),
        "notified": str(sent_notification).lower(),
        "provider": provider,
        "provider_message_id": provider_message_id,
        "raw_excerpt": raw_excerpt,
        "mode": "live" if sb else "dry_run",
    }

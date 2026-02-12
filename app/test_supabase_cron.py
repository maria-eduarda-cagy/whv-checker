import os
import time
from datetime import datetime, timezone
from typing import Optional

import requests


def _required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required env: {name}")
    return value


def _parse_ts(ts: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except Exception:
        return None


def main() -> int:
    supabase_url = _required_env("SUPABASE_URL").rstrip("/")
    service_key = _required_env("SUPABASE_SERVICE_ROLE_KEY")
    project_ref = _required_env("SUPABASE_PROJECT_REF")
    test_notify_token = _required_env("TEST_NOTIFY_TOKEN")

    fn_url = f"https://{project_ref}.supabase.co/functions/v1/check_caps_proxy"
    start = datetime.now(timezone.utc)

    print("1) Invoking Supabase function check_caps_proxy in TEST mode...")
    invoke = requests.post(
        fn_url,
        json={"force_notify_test": True, "test_notify_token": test_notify_token},
        timeout=30,
    )
    print(f"   Function status: {invoke.status_code}")
    if invoke.status_code >= 300:
        print(f"   Body: {invoke.text[:500]}")
        return 1

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    print("2) Waiting for DB records (status_checks + notifications)...")
    deadline = time.time() + 45
    found_status_check = False
    found_notification = False
    while time.time() < deadline:
        checks = requests.get(
            f"{supabase_url}/rest/v1/status_checks",
            params={"select": "checked_at", "order": "checked_at.desc", "limit": "1"},
            headers=headers,
            timeout=15,
        )
        checks.raise_for_status()
        checks_rows = checks.json()
        if checks_rows:
            checked_at = _parse_ts(checks_rows[0].get("checked_at", ""))
            if checked_at and checked_at >= start:
                found_status_check = True

        notifs = requests.get(
            f"{supabase_url}/rest/v1/notifications",
            params={"select": "sent_at,provider,provider_message_id", "order": "sent_at.desc", "limit": "3"},
            headers=headers,
            timeout=15,
        )
        notifs.raise_for_status()
        notif_rows = notifs.json()
        for row in notif_rows:
            sent_at = _parse_ts(row.get("sent_at", ""))
            if sent_at and sent_at >= start and row.get("provider") == "telegram":
                found_notification = True
                break

        if found_status_check and found_notification:
            break
        time.sleep(3)

    print(f"   status_checks updated: {found_status_check}")
    print(f"   telegram notification recorded: {found_notification}")

    if found_status_check and found_notification:
        print("3) PASS: Supabase path is working and Telegram send was recorded.")
        return 0

    print("3) FAIL: missing expected records after function invocation.")
    print("   Check Supabase function logs, WORKER_URL/WORKER_AUTH, and Telegram secrets.")
    return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Error: {exc}")
        raise SystemExit(1)

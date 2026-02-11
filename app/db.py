import os
import time
from typing import Any, Dict, Optional

import requests 


class SupabaseClient:
    def __init__(self, base_url: str, service_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.service_key = service_key
        self.session = requests.Session()
        self.session.headers.update(
            {
                "apikey": self.service_key,
                "Authorization": f"Bearer {self.service_key}",
                "Content-Type": "application/json",
            }
        )

    @classmethod
    def from_env(cls) -> "SupabaseClient":
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
        if not url or not key:
            raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
        return cls(url, key)

    def _rest(self, table: str) -> str:
        return f"{self.base_url}/rest/v1/{table}"

    def get_last_state(self, country: str) -> Optional[Dict[str, Any]]:
        # GET row by country
        url = self._rest("country_last_state")
        params = {"select": "*", "country": f"eq.{country}"}
        r = self.session.get(url, params=params, timeout=15)
        r.raise_for_status()
        rows = r.json()
        if rows:
            return rows[0]
        return None

    def upsert_last_state(self, country: str, status: str, last_notified_status: Optional[str] = None) -> Dict[str, Any]:
        url = self._rest("country_last_state")
        params = {"on_conflict": "country"}
        payload = {
            "country": country,
            "status": status,
            "last_checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        if last_notified_status is not None:
            payload["last_notified_status"] = last_notified_status
        headers = {"Prefer": "resolution=merge-duplicates,return=representation"}
        r = self.session.post(url, params=params, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if isinstance(rows, list) and rows else rows

    def insert_status_check(
        self,
        country: str,
        status: Optional[str],
        source_url: str,
        raw_excerpt: Optional[str],
        error: Optional[str],
    ) -> Dict[str, Any]:
        url = self._rest("status_checks")
        payload = {
            "country": country,
            "status": status,
            "source_url": source_url,
            "raw_excerpt": raw_excerpt,
            "error": error,
            "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        headers = {"Prefer": "return=representation"}
        r = self.session.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if isinstance(rows, list) and rows else rows

    def insert_notification(
        self,
        country: str,
        status: str,
        recipient: str,
        provider: str,
        provider_message_id: Optional[str],
    ) -> Dict[str, Any]:
        url = self._rest("notifications")
        payload = {
            "country": country,
            "status": status,
            "recipient": recipient,
            "provider": provider,
            "provider_message_id": provider_message_id,
            "sent_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        headers = {"Prefer": "return=representation"}
        r = self.session.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        rows = r.json()
        return rows[0] if isinstance(rows, list) and rows else rows

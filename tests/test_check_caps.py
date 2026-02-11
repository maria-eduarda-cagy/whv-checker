from app import check_caps


class _Resp:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _Session:
    def get(self, _url: str, timeout: int = 10) -> _Resp:
        return _Resp("<html></html>")


class _Sb:
    def __init__(self, last_state):
        self.last_state = last_state
        self.notifications = []

    def insert_status_check(self, **_kwargs):
        return {}

    def get_last_state(self, _country):
        return self.last_state

    def upsert_last_state(self, _country, _status, last_notified_status=None):
        return {"last_notified_status": last_notified_status}

    def insert_notification(self, **kwargs):
        self.notifications.append(kwargs)
        return kwargs


class _Notifier:
    def __init__(self):
        self.chat_id = "123"

    def send_open_alert(self, _country, _source_url, _status):
        return "telegram", "42"


def test_run_check_notifies_when_transition_to_open(monkeypatch):
    sb = _Sb({"status": "paused", "last_notified_status": "paused"})
    monkeypatch.setattr(check_caps, "_session_with_retries", lambda: _Session())
    monkeypatch.setattr(check_caps, "parse_country_status", lambda _html, _country: ("open", "raw", None))
    monkeypatch.setattr(check_caps.SupabaseClient, "from_env", classmethod(lambda cls: sb))
    monkeypatch.setattr(check_caps.TelegramNotifier, "from_env", classmethod(lambda cls: _Notifier()))

    result = check_caps.run_check()

    assert result["status"] == "open"
    assert result["notified"] == "true"
    assert len(sb.notifications) == 1


def test_run_check_dedupes_when_already_notified_open(monkeypatch):
    sb = _Sb({"status": "open", "last_notified_status": "open"})
    monkeypatch.setattr(check_caps, "_session_with_retries", lambda: _Session())
    monkeypatch.setattr(check_caps, "parse_country_status", lambda _html, _country: ("open", "raw", None))
    monkeypatch.setattr(check_caps.SupabaseClient, "from_env", classmethod(lambda cls: sb))
    monkeypatch.setattr(check_caps.TelegramNotifier, "from_env", classmethod(lambda cls: _Notifier()))

    result = check_caps.run_check()

    assert result["status"] == "open"
    assert result["notified"] == "false"
    assert len(sb.notifications) == 0

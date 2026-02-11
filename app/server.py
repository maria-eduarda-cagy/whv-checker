from fastapi import FastAPI, Request, HTTPException
from dotenv import load_dotenv
import os

from .worker import run_check
from .notify import ResendNotifier

load_dotenv()
app = FastAPI(title="WHV 462 Country Caps Monitor")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/check")
def check(request: Request):
    token = os.environ.get("WORKER_AUTH")
    if token:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="Unauthorized")
    result = run_check()
    return result


@app.get("/config")
def config():
    def present(key: str) -> bool:
        return bool(os.environ.get(key))

    return {
        "SOURCE_URL_present": present("SOURCE_URL"),
        "TARGET_COUNTRY_present": present("TARGET_COUNTRY"),
        "SUPABASE_URL_present": present("SUPABASE_URL"),
        "SUPABASE_SERVICE_ROLE_KEY_present": present("SUPABASE_SERVICE_ROLE_KEY"),
        "EMAIL_PROVIDER_API_KEY_present": present("EMAIL_PROVIDER_API_KEY"),
        "ALERT_RECIPIENT_EMAIL_present": present("ALERT_RECIPIENT_EMAIL"),
        "ALERT_SENDER_EMAIL_present": present("ALERT_SENDER_EMAIL"),
    }


@app.post("/notify-test")
def notify_test():
    try:
        notifier = ResendNotifier.from_env()
        provider, message_id = notifier.send_test_email()
        return {"provider": provider, "provider_message_id": message_id}
    except Exception as e:
        return {"error": str(e)}

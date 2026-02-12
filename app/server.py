import os

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request

from .check_caps import run_check

load_dotenv()
app = FastAPI(title="WHV 462 Country Caps Monitor")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/check")
async def check(request: Request) -> dict:
    token = os.environ.get("WORKER_AUTH")
    if token:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="Unauthorized")
    force_notify_test = False
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    if isinstance(payload, dict):
        force_notify_test = bool(payload.get("force_notify_test", False))
        if force_notify_test:
            expected = os.environ.get("TEST_NOTIFY_TOKEN")
            provided = str(payload.get("test_notify_token", ""))
            if not expected or provided != expected:
                raise HTTPException(status_code=401, detail="Unauthorized test notify")
    return run_check(force_notify_test=force_notify_test)

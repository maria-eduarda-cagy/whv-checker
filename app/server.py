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
def check(request: Request) -> dict:
    token = os.environ.get("WORKER_AUTH")
    if token:
        auth = request.headers.get("Authorization")
        if auth != f"Bearer {token}":
            raise HTTPException(status_code=401, detail="Unauthorized")
    return run_check()

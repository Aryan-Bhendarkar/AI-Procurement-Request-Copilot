from __future__ import annotations

import os
import threading
import time
from urllib.parse import quote

import requests

from src.policy_engine import RISK_NOT_FOUND, RISK_OK, RISK_UNAVAILABLE

DEFAULT_BASE_URL = "http://127.0.0.1:8001"


def _base_url() -> str:
    return os.getenv("VENDOR_RISK_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def get_vendor_risk(vendor_name: str, timeout_seconds: float = 3.0) -> dict:
    """Low-level API client (raises on any non-2xx). Prefer `fetch_vendor_risk`."""
    url = f"{_base_url()}/vendor-risk/{quote(vendor_name, safe='')}"
    response = requests.get(url, timeout=timeout_seconds)
    response.raise_for_status()
    return response.json()


def fetch_vendor_risk(vendor_name: str, timeout_seconds: float = 3.0) -> dict:
    """Typed, never-raising wrapper used by the tools.

    Returns {"status": "ok", "data": {...}} for 200, {"status": "not_found"} for 404 (no record),
    and {"status": "unavailable", "reason": ...} for 5xx, timeout, connection error or bad payload.
    """
    url = f"{_base_url()}/vendor-risk/{quote(vendor_name, safe='')}"
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.Timeout:
        return {"status": RISK_UNAVAILABLE, "reason": f"timeout after {timeout_seconds:g}s"}
    except requests.RequestException as exc:
        return {"status": RISK_UNAVAILABLE, "reason": f"connection error: {type(exc).__name__}"}
    if response.status_code == 404:
        return {"status": RISK_NOT_FOUND}
    if response.status_code != 200:
        detail = ""
        try:
            detail = str(response.json().get("detail", ""))[:200]
        except ValueError:
            pass
        return {"status": RISK_UNAVAILABLE, "reason": f"HTTP {response.status_code} {detail}".strip()}
    try:
        return {"status": RISK_OK, "data": response.json()}
    except ValueError:
        return {"status": RISK_UNAVAILABLE, "reason": "invalid JSON from vendor-risk service"}


_autostart_lock = threading.Lock()
_autostarted = False


def ensure_local_mock_api(wait_seconds: float = 10.0) -> bool:
    """Start the bundled mock API in a background thread if the default local URL is not reachable.

    Lets `evals/` and `handle_request` work without `run_local.py`. Does nothing when
    VENDOR_RISK_BASE_URL points elsewhere, VENDOR_RISK_AUTOSTART=0, or the API is already up.
    Returns True when the API is reachable afterwards.
    """
    global _autostarted
    base = _base_url()

    def healthy() -> bool:
        try:
            return requests.get(f"{base}/health", timeout=0.5).ok
        except requests.RequestException:
            return False

    if healthy():
        return True
    if base != DEFAULT_BASE_URL or os.getenv("VENDOR_RISK_AUTOSTART", "1") == "0":
        return False
    with _autostart_lock:
        if not _autostarted:
            _autostarted = True
            import uvicorn
            from mock_api.app import app

            server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8001, log_level="warning"))
            threading.Thread(target=server.run, daemon=True, name="mock-vendor-api").start()
        deadline = time.monotonic() + wait_seconds
        while time.monotonic() < deadline:
            if healthy():
                return True
            time.sleep(0.2)
    return False

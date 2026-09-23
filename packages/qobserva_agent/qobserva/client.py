from __future__ import annotations

from typing import Any, Dict, Optional
import httpx

# Connecting to a healthy collector is near-instant; cap the connect phase so an
# unreachable host fails fast instead of waiting out the full request timeout.
_MAX_CONNECT_TIMEOUT_S = 3.0

class QObservaClient:
    def __init__(self, endpoint: str, api_key: Optional[str] = None, timeout_s: float = 10.0):
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout_s = timeout_s

    def ingest(self, event: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        timeout = httpx.Timeout(self.timeout_s, connect=min(self.timeout_s, _MAX_CONNECT_TIMEOUT_S))
        with httpx.Client(timeout=timeout) as client:
            r = client.post(self.endpoint, headers=headers, json=event)
            r.raise_for_status()
            return r.json()

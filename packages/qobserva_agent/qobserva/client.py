from __future__ import annotations

from typing import Any, Dict, Optional
from urllib.parse import urlparse
import httpx

# Connecting to a healthy collector is near-instant; cap the connect phase so an
# unreachable collector fails fast instead of waiting out the full request timeout.
# Windows retries refused connections for several seconds, so the local cap is short.
_MAX_CONNECT_TIMEOUT_S = 3.0
_MAX_LOCAL_CONNECT_TIMEOUT_S = 1.0
_LOCAL_HOSTS = {"127.0.0.1", "localhost", "::1"}

class QObservaClient:
    def __init__(self, endpoint: str, api_key: Optional[str] = None, timeout_s: float = 10.0):
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout_s = timeout_s

    def _connect_timeout(self) -> float:
        host = (urlparse(self.endpoint).hostname or "").lower()
        cap = _MAX_LOCAL_CONNECT_TIMEOUT_S if host in _LOCAL_HOSTS else _MAX_CONNECT_TIMEOUT_S
        return min(self.timeout_s, cap)

    def ingest(self, event: Dict[str, Any]) -> Dict[str, Any]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        timeout = httpx.Timeout(self.timeout_s, connect=self._connect_timeout())
        # Loading the TLS certificate bundle costs over a second on some machines; plain
        # http:// endpoints (the local collector) never use it. https:// keeps full verification.
        is_https = urlparse(self.endpoint).scheme.lower() == "https"
        with httpx.Client(timeout=timeout, verify=True if is_https else False) as client:
            r = client.post(self.endpoint, headers=headers, json=event)
            r.raise_for_status()
            return r.json()

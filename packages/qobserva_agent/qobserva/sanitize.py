from __future__ import annotations

import hashlib
import os
import re
import socket
from typing import Any, Dict

REDACTED = "[REDACTED]"

# Key names whose values are treated as secrets in "key=value" / "key: value" / "key": "value" text.
_SECRET_KEY = (
    r"(?:api[_-]?key|apikey|api[_-]?token|access[_-]?key(?:[_-]?id)?|secret(?:[_-]?access)?[_-]?key|"
    r"secret|client[_-]?secret|private[_-]?key|password|passwd|pwd|token|access[_-]?token|"
    r"refresh[_-]?token|auth[_-]?token|session[_-]?token|authorization|credentials?)"
)

_PATTERNS = [
    # Authorization headers: "Bearer <token>", "Basic <creds>". Runs before key=value, which would consume "Bearer".
    (re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}"), rf"\1 {REDACTED}"),
    # key=value, key: value, "key": "value", key = 'value'
    (re.compile(
        rf"""(?ix)
        (["']?\b[\w.-]*{_SECRET_KEY}["']?\s*[:=]\s*)   # key and separator (kept)
        (?:"[^"]*"|'[^']*'|[^\s,;&)}}\]]+)              # value (redacted)
        """),
     rf"\1{REDACTED}"),
    # Credentials embedded in URLs: scheme://user:pass@host
    (re.compile(r"(?i)\b([a-z][a-z0-9+.-]*://[^\s:/@]+:)[^\s@/]+@"), rf"\1{REDACTED}@"),
    # AWS access key IDs
    (re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b"), REDACTED),
    # JSON Web Tokens
    (re.compile(r"\beyJ[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\.[A-Za-z0-9_-]{5,}\b"), REDACTED),
    # Long hex/base64-like tokens (e.g. IBM Quantum API tokens are 128 hex chars)
    (re.compile(r"\b[A-Fa-f0-9]{40,}\b"), REDACTED),
    (re.compile(r"\b(?=[A-Za-z0-9_-]*\d)(?=[A-Za-z0-9_-]*[A-Za-z])[A-Za-z0-9_-]{48,}\b"), REDACTED),
]

def sanitize_error_message(msg: str, max_len: int = 500) -> str:
    """Redact secret values from an exception message before it leaves the process."""
    s = msg or ""
    for pattern, repl in _PATTERNS:
        s = pattern.sub(repl, s)
    # Truncate after redaction so a secret straddling the limit is never half-kept.
    return s[:max_len]

def host_identity() -> Dict[str, Any]:
    """
    Machine identity recorded on each run, controlled by QOBSERVA_HOST_MODE:
      - "hash" (default): stable short hash, so runs still group by machine without exposing its name
      - "raw": the plain hostname
      - "none": omitted
    """
    mode = (os.getenv("QOBSERVA_HOST_MODE") or "hash").strip().lower()
    if mode == "none":
        return {}
    host = socket.gethostname()
    if mode == "raw":
        return {"host": host}
    return {"host_hash": hashlib.sha256(host.encode("utf-8")).hexdigest()[:12]}

from __future__ import annotations

import re

_PATTERNS = [
    re.compile(r"AKIA[0-9A-Z]{16}"),
    re.compile(r"(?i)secret"),
    re.compile(r"(?i)token"),
    re.compile(r"(?i)apikey"),
]

def sanitize_error_message(msg: str, max_len: int = 500) -> str:
    s = (msg or "")[:max_len]
    for p in _PATTERNS:
        s = p.sub("[REDACTED]", s)
    return s

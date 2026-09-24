from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from platformdirs import user_data_dir

# Browser origins allowed by default: pages served from this machine on any port.
LOCAL_ORIGIN_REGEX = r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?"

@dataclass(frozen=True)
class CollectorConfig:
    data_dir: str
    require_token: bool
    token: str | None
    # Explicit browser origins from QOBSERVA_CORS_ORIGINS (comma-separated).
    # Empty means "local origins only".
    cors_origins: list[str] = field(default_factory=list)

def is_allowed_origin(origin: str, cors_origins: list[str]) -> bool:
    if cors_origins:
        return "*" in cors_origins or origin in cors_origins
    return re.fullmatch(LOCAL_ORIGIN_REGEX, origin) is not None

def load_config() -> CollectorConfig:
    data_dir = os.getenv("QOBSERVA_DATA_DIR") or user_data_dir("qobserva", "qobserva")
    token = os.getenv("QOBSERVA_LOCAL_TOKEN")
    cors_origins = [o.strip() for o in os.getenv("QOBSERVA_CORS_ORIGINS", "").split(",") if o.strip()]
    return CollectorConfig(
        data_dir=data_dir,
        require_token=bool(token),
        token=token,
        cors_origins=cors_origins,
    )

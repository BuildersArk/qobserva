from __future__ import annotations

from typing import Any, Dict, Optional
import datetime

from .config import load_config
from .client import QObservaClient
from .schema import validate_event_dict

def iso_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def report_run(event: Dict[str, Any], *, endpoint: str | None = None, api_key: str | None = None) -> Dict[str, Any]:
    errs = validate_event_dict(event)
    if errs:
        raise ValueError(f"Event schema validation failed: {errs[:3]} (and {max(0, len(errs)-3)} more)")
    cfg = load_config(endpoint=endpoint, api_key=api_key)
    client = QObservaClient(cfg.endpoint, api_key=cfg.api_key, timeout_s=cfg.timeout_s)
    return client.ingest(event)

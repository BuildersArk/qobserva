from __future__ import annotations

import os
from dataclasses import dataclass

DEFAULT_ENDPOINT_LOCAL = "http://127.0.0.1:8080/v1/ingest/run-event"

@dataclass(frozen=True)
class AgentConfig:
    endpoint: str
    api_key: str | None
    capture_program: str
    timeout_s: float

def load_config(endpoint: str | None = None, api_key: str | None = None, capture_program: str | None = None) -> AgentConfig:
    final_endpoint = endpoint or os.getenv("QOBSERVA_ENDPOINT") or DEFAULT_ENDPOINT_LOCAL
    final_key = api_key or os.getenv("QOBSERVA_API_KEY")
    final_capture = capture_program or os.getenv("QOBSERVA_CAPTURE_PROGRAM") or "hash"
    timeout_s = float(os.getenv("QOBSERVA_TIMEOUT_S", "10"))
    return AgentConfig(endpoint=final_endpoint, api_key=final_key, capture_program=final_capture, timeout_s=timeout_s)

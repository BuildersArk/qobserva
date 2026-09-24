from __future__ import annotations

import socket
import threading
import time

import httpx
import pytest
import uvicorn

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]

@pytest.fixture
def collector(tmp_path, monkeypatch):
    """A real collector (uvicorn + the collector app) on a free local port."""
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(tmp_path / "data"))
    from qobserva_collector.api import create_app

    port = free_port()
    server = uvicorn.Server(uvicorn.Config(create_app(), host="127.0.0.1", port=port, log_level="error"))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{port}"
    for _ in range(100):
        try:
            if httpx.get(f"{base}/v1/health").status_code == 200:
                break
        except httpx.HTTPError:
            time.sleep(0.05)
    yield base
    server.should_exit = True
    t.join(timeout=5)


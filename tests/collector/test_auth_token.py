from __future__ import annotations

from fastapi.testclient import TestClient
from qobserva_collector.api import create_app

def test_auth_token_enforced(tmp_path, monkeypatch):
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("QOBSERVA_LOCAL_TOKEN", "abc")

    client = TestClient(create_app())
    r = client.get("/v1/runs")
    assert r.status_code in (401, 403)

    r2 = client.get("/v1/runs", headers={"Authorization": "Bearer abc"})
    assert r2.status_code == 200

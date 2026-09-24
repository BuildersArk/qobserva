from __future__ import annotations

import copy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from qobserva_collector.api import create_app
from qobserva_collector.storage import safe_path_component

EVENT = {
    "schema_version": "0.1.0",
    "event_id": "e-1",
    "run_id": "r-1",
    "created_at": "2026-01-06T00:00:00Z",
    "project": "demo",
    "backend": {"provider": "local_sim", "name": "sim"},
    "execution": {"shots": 10, "status": "success"},
    "artifacts": {"result_type": "counts", "counts": {"histogram": {"00": 10}}},
}

def _event(project: str, run_id: str) -> dict:
    ev = copy.deepcopy(EVENT)
    ev["project"], ev["run_id"], ev["event_id"] = project, run_id, run_id
    return ev

@pytest.fixture
def data_dir(tmp_path, monkeypatch) -> Path:
    d = tmp_path / "data"
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(d))
    monkeypatch.delenv("QOBSERVA_CORS_ORIGINS", raising=False)
    return d

@pytest.mark.parametrize("project,run_id", [
    ("../../../escape", "r1"),
    ("demo", "../../escape"),
    ("..", "r2"),
    ("a/b\\c", "r3"),
    ("C:\\Windows\\escape", "r4"),
    ("/etc/escape", "r5"),
    ("CON", "r6"),
])
def test_untrusted_names_stay_inside_artifacts_dir(data_dir, tmp_path, project, run_id):
    client = TestClient(create_app())
    r = client.post("/v1/ingest/run-event", json=_event(project, run_id))
    assert r.status_code == 200, r.text

    artifacts = (data_dir / "artifacts").resolve()
    written = [p.resolve() for p in tmp_path.rglob("bundle.json.gz")]
    assert written and all(artifacts in p.parents for p in written)
    # The run is still stored under its original project name and readable via the API.
    runs = client.get("/v1/runs", params={"project": project}).json()
    assert [x["run_id"] for x in runs] == [run_id]
    assert runs[0]["project"] == project

def test_safe_names_are_unchanged_so_existing_layout_is_kept():
    for name in ["qiskit_test", "my project", "exp-1.v2", "VQE H2"]:
        assert safe_path_component(name) == name

def test_distinct_unsafe_names_do_not_collide():
    assert safe_path_component("a/b") != safe_path_component("a_b")
    assert safe_path_component("a/b") != safe_path_component("a\\b")

def test_foreign_browser_origin_cannot_write(data_dir):
    client = TestClient(create_app())
    r = client.post("/v1/ingest/run-event", json=_event("demo", "x1"), headers={"Origin": "https://evil.example"})
    assert r.status_code == 403
    # Preflight from a foreign site gets no CORS approval.
    pre = client.options("/v1/ingest/run-event", headers={
        "Origin": "https://evil.example", "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"})
    assert pre.headers.get("access-control-allow-origin") is None
    assert client.get("/v1/runs").json() == []

def test_local_origins_and_non_browser_clients_can_write(data_dir):
    client = TestClient(create_app())
    assert client.post("/v1/ingest/run-event", json=_event("demo", "a1")).status_code == 200
    r = client.post("/v1/ingest/run-event", json=_event("demo", "a2"), headers={"Origin": "http://localhost:3000"})
    assert r.status_code == 200
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"

def test_dashboard_reads_still_work_from_any_origin(data_dir):
    # Reading (e.g. dashboard opened via a LAN address) is not affected by the write guard.
    client = TestClient(create_app())
    assert client.get("/v1/runs", headers={"Origin": "http://192.168.1.20:3000"}).status_code == 200

def test_cors_origins_can_be_configured(data_dir, monkeypatch):
    monkeypatch.setenv("QOBSERVA_CORS_ORIGINS", "https://lab.example.org")
    client = TestClient(create_app())
    ok = client.post("/v1/ingest/run-event", json=_event("demo", "c1"), headers={"Origin": "https://lab.example.org"})
    assert ok.status_code == 200
    denied = client.post("/v1/ingest/run-event", json=_event("demo", "c2"), headers={"Origin": "http://localhost:3000"})
    assert denied.status_code == 403

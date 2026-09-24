from __future__ import annotations

from fastapi.testclient import TestClient
from qobserva_collector.api import create_app

def test_ingest_and_analysis(tmp_path, monkeypatch):
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(tmp_path))

    client = TestClient(create_app())

    event = {
        "schema_version": "0.1.0",
        "event_id": "11111111-1111-1111-1111-111111111111",
        "run_id": "22222222-2222-2222-2222-222222222222",
        "created_at": "2026-01-06T00:00:00Z",
        "project": "demo",
        "backend": {"provider": "local_sim", "name": "sim"},
        "execution": {"shots": 10, "status": "success", "runtime_ms": 5},
        "artifacts": {"result_type": "counts", "counts": {"bit_order": "little", "histogram": {"00": 5, "11": 5}, "mapping": {}}},
        "software": {"agent_version": "0.1.0", "sdk": {"name": "test", "version": "0"}, "python_version": "3.11"},
        "program": {"kind": "circuit", "benchmark_id": "b1", "benchmark_params": {"target_bitstrings": ["00"]}, "program_hash": "abc", "circuit_metrics": {}},
        "tags": {}
    }

    r = client.post("/v1/ingest/run-event", json=event)
    assert r.status_code == 200, r.text

    runs = client.get("/v1/runs").json()
    assert len(runs) == 1

    analysis = client.get(f"/v1/runs/{event['run_id']}/analysis").json()
    assert analysis["metrics"]["qc.quality.success_probability"] == 0.5

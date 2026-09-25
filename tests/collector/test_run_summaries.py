"""Run summaries and the algorithm index that let the dashboard avoid per-run requests."""

from __future__ import annotations

import copy
import os
import sqlite3

import pytest
from fastapi.testclient import TestClient
from qobserva_collector.api import create_app

def _event(run_id: str, algorithm: str | None = None, sdk: str | None = "qiskit", **extra) -> dict:
    ev = {
        "schema_version": "0.1.0",
        "event_id": f"e-{run_id}",
        "run_id": run_id,
        "created_at": "2026-01-06T00:00:00Z",
        "project": "demo",
        "backend": {"provider": "local_sim", "name": "sim"},
        "execution": {"shots": 10, "status": "success", "runtime_ms": 12},
        "artifacts": {"result_type": "counts", "counts": {"histogram": {"00": 8, "11": 2}}},
        "software": {"sdk": {"name": sdk, "version": "1"}} if sdk else {},
        "program": {
            "benchmark_params": {"target_bitstrings": ["00"], "energy": -1.5},
            "circuit_metrics": {"depth_post": 7},
        },
        "tags": {"algorithm": algorithm} if algorithm else {},
    }
    ev.update(copy.deepcopy(extra))
    return ev

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(tmp_path / "data"))
    return TestClient(create_app())

def test_summary_is_opt_in(client):
    assert client.post("/v1/ingest/run-event", json=_event("r1", "grover")).status_code == 200
    plain = client.get("/v1/runs").json()[0]
    assert "summary" not in plain and "algorithm" not in plain

    run = client.get("/v1/runs", params={"include_summary": "true"}).json()[0]
    assert run["algorithm"] == "grover"
    assert run["summary"] == {
        "sdk": "qiskit",
        "runtime_ms": 12,
        "metrics": {"qc.circuit.depth_post": 7, "qc.quality.success_probability": 0.8},
        "benchmark_params": {"energy": -1.5},
    }

def test_summary_matches_run_analysis(client):
    client.post("/v1/ingest/run-event", json=_event("r1", "grover"))
    run = client.get("/v1/runs", params={"include_summary": "true"}).json()[0]
    analysis = client.get("/v1/runs/r1/analysis").json()
    for key, value in run["summary"]["metrics"].items():
        assert analysis["metrics"][key] == value

def test_sdk_falls_back_to_sdk_tag(client):
    ev = _event("r1", sdk=None)
    ev["tags"] = {"sdk": "cirq"}
    client.post("/v1/ingest/run-event", json=ev)
    run = client.get("/v1/runs", params={"include_summary": "true"}).json()[0]
    assert run["summary"]["sdk"] == "cirq" and run["algorithm"] is None

def test_algorithm_filter_and_counts(client):
    for i, algo in enumerate(["grover", "vqe", "grover", None, "grover"]):
        client.post("/v1/ingest/run-event", json=_event(f"r{i}", algo))

    grover = client.get("/v1/runs", params={"algorithm": "grover"}).json()
    assert [r["run_id"] for r in grover] == ["r4", "r2", "r0"]
    assert [r["run_id"] for r in client.get("/v1/runs", params={"algorithm": "grover", "limit": 2}).json()] == ["r4", "r2"]

    assert client.get("/v1/algorithms").json() == {
        "algorithms": [{"name": "grover", "count": 3}, {"name": "vqe", "count": 1}]
    }
    # Counts only consider the latest `limit` runs, as before.
    assert client.get("/v1/algorithms", params={"limit": 2}).json() == {
        "algorithms": [{"name": "grover", "count": 1}]
    }

def test_health_reports_collector_pid(client):
    assert client.get("/v1/health").json() == {"status": "ok", "pid": os.getpid()}

def test_database_from_older_collector_is_upgraded(tmp_path, monkeypatch):
    """A data folder written by collector 0.1.4 (no algorithm/summary columns) keeps working."""
    data = tmp_path / "data"
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(data))
    client = TestClient(create_app())
    client.post("/v1/ingest/run-event", json=_event("old1", "grover"))
    client.post("/v1/ingest/run-event", json=_event("old2", None, sdk="braket"))

    # Recreate the 0.1.4 table layout, keeping the rows and the stored bundles.
    db = sqlite3.connect(data / "qobserva.sqlite3")
    db.executescript("""
        CREATE TABLE runs_old AS SELECT id, run_id, event_id, created_at, project, provider,
            backend_name, status, shots, artifact_ref, analysis_ref FROM runs;
        DROP TABLE runs;
        ALTER TABLE runs_old RENAME TO runs;
    """)
    db.close()

    client = TestClient(create_app())
    runs = {r["run_id"]: r for r in client.get("/v1/runs", params={"include_summary": "true"}).json()}
    assert runs["old1"]["algorithm"] == "grover"
    assert runs["old1"]["summary"]["metrics"]["qc.quality.success_probability"] == 0.8
    assert runs["old2"]["summary"]["sdk"] == "braket"
    assert client.get("/v1/algorithms").json() == {"algorithms": [{"name": "grover", "count": 1}]}
    # New runs are still accepted after the upgrade.
    assert client.post("/v1/ingest/run-event", json=_event("new1", "vqe")).status_code == 200

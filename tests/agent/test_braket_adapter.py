"""Braket adapter against the real Braket LocalSimulator (skipped when Braket is not installed)."""

from __future__ import annotations

import httpx
import pytest

pytest.importorskip("braket.circuits")
from braket.circuits import Circuit  # noqa: E402
from braket.devices import LocalSimulator  # noqa: E402

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        observe_run(project="braket", tags={"sdk": "braket"},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def test_local_simulator_counts_and_backend(record):
    bell = Circuit().h(0).cnot(0, 1)
    ev = record(lambda: LocalSimulator().run(bell, shots=1024).result())

    hist = ev["artifacts"]["counts"]["histogram"]
    assert set(hist) <= {"00", "11"} and sum(hist.values()) == 1024
    assert ev["execution"]["shots"] == 1024
    assert ev["execution"]["status"] == "success"
    assert ev["backend"]["provider"] == "local_sim"
    assert ev["backend"]["name"] == "LocalSimulator"

"""PennyLane adapter against real PennyLane devices (skipped when PennyLane is not installed)."""

from __future__ import annotations

import httpx
import pytest

qml = pytest.importorskip("pennylane")

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        observe_run(project="pennylane", tags={"sdk": "pennylane"},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def test_counts_are_recorded(record):
    dev = qml.device("default.qubit", wires=2, shots=1024)

    @qml.qnode(dev)
    def bell():
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        return qml.counts()

    ev = record(bell)
    hist = ev["artifacts"]["counts"]["histogram"]
    assert set(hist) <= {"00", "11"} and sum(hist.values()) == 1024
    assert ev["execution"]["shots"] == 1024

def test_expectation_value_is_recorded(record):
    dev = qml.device("default.qubit", wires=1)

    @qml.qnode(dev)
    def expval():
        qml.RX(0.0, wires=0)
        return qml.expval(qml.PauliZ(0))

    ev = record(expval)
    assert ev["artifacts"]["result_type"] == "energies"
    assert ev["artifacts"]["energies"]["value"] == pytest.approx(1.0)

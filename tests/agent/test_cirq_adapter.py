"""Cirq adapter against the real Cirq simulator (skipped when Cirq is not installed)."""

from __future__ import annotations

import httpx
import pytest

cirq = pytest.importorskip("cirq")

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        observe_run(project="cirq", tags={"sdk": "cirq"},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return (httpx.get(f"{collector}/v1/runs/{run['run_id']}").json(),
                httpx.get(f"{collector}/v1/runs/{run['run_id']}/analysis").json())
    return _record

def test_bitstrings_keep_leading_zeros(record):
    q0, q1, q2 = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1, q2, key="result"))
    ev, analysis = record(lambda: cirq.Simulator().run(circuit, repetitions=1000),
                          measurement_key="result",
                          benchmark_params={"target_bitstrings": ["000", "110"]})
    hist = ev["artifacts"]["counts"]["histogram"]
    assert set(hist) == {"000", "110"} and sum(hist.values()) == 1000
    assert analysis["metrics"]["qc.quality.success_probability"] == 1.0

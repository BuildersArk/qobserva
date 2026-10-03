"""
PennyLane through its device plugins (pennylane-qiskit, amazon-braket-pennylane-plugin): the backend is
the device the plugin ran, and plugin result shapes are read. Found in the 2026-10-03 PennyLane dry runs.
Skipped unless the plugins are installed (they pin older Qiskit versions, so they live in their own venv).
"""

from __future__ import annotations

import httpx
import pytest

qml = pytest.importorskip("pennylane")

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(qnode):
        observe_run(project="plugins", tags={"sdk": "pennylane"},
                    endpoint=f"{collector}/v1/ingest/run-event")(qnode)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def _bell_counts(dev):
    @qml.set_shots(shots=50)
    @qml.qnode(dev)
    def bell():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        return qml.counts()
    return bell

def test_braket_local_plugin_counts_and_label(record):
    pytest.importorskip("braket.pennylane_plugin")
    ev = record(_bell_counts(qml.device("braket.local.qubit", wires=2)))
    assert ev["backend"] == {"provider": "local_sim", "name": "braket.local.qubit"}  # was aws_braket
    hist = ev["artifacts"]["counts"]["histogram"]  # a 0-d object array holding the dict; was dropped
    assert sum(hist.values()) == 50 and set(hist) <= {"00", "11"}

def test_qiskit_aer_plugin_is_local(record):
    pytest.importorskip("pennylane_qiskit")
    pytest.importorskip("qiskit_aer")
    ev = record(_bell_counts(qml.device("qiskit.aer", wires=2)))
    assert ev["backend"] == {"provider": "local_sim", "name": "aer_simulator"}  # was ibm / qiskit.aer
    assert sum(ev["artifacts"]["counts"]["histogram"].values()) == 50

def test_qiskit_remote_plugin_uses_the_backend_name(record):
    pytest.importorskip("pennylane_qiskit")
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    ev = record(_bell_counts(qml.device("qiskit.remote", wires=2, backend=FakeManilaV2())))
    # A fake IBM backend simulates locally; a real IBM backend is labeled ibm / <its name> the same way.
    assert ev["backend"] == {"provider": "local_sim", "name": "fake_manila"}
    assert sum(ev["artifacts"]["counts"]["histogram"].values()) == 50

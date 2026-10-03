"""
Runs computed exactly (no shots sampled) are flagged execution.exact and listed with 0 shots, instead
of looking like 1-shot runs. Each case runs the real SDK, once exact and once sampled.
"""

from __future__ import annotations

import warnings

import httpx
import pytest

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(sdk, fn, **decorator_kwargs):
        observe_run(project="exact", tags={"sdk": sdk},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        row = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        ev = httpx.get(f"{collector}/v1/runs/{row['run_id']}").json()
        analysis = httpx.get(f"{collector}/v1/runs/{row['run_id']}/analysis").json()
        return row, ev, analysis["metrics"]
    return _record

def _assert_exact(row, ev, metrics):
    assert ev["execution"].get("exact") is True
    assert ev["execution"]["shots"] == 1  # schema minimum, kept for older collectors
    assert row["shots"] == 0 and metrics["qc.shots"] == 0 and metrics.get("qc.exact") is True

def _assert_sampled(row, ev, shots):
    assert "exact" not in ev["execution"]
    assert row["shots"] == ev["execution"]["shots"] == shots

def test_qiskit_statevector_estimator(record):
    pytest.importorskip("qiskit")
    from qiskit import QuantumCircuit
    from qiskit.primitives import StatevectorEstimator
    from qiskit.quantum_info import SparsePauliOp
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    _assert_exact(*record("qiskit", lambda: StatevectorEstimator().run([(qc, SparsePauliOp("ZZ"))]).result()))
    # precision > 0 adds sampling noise to the estimate, so it is not exact
    row, ev, _ = record("qiskit", lambda: StatevectorEstimator().run([(qc, SparsePauliOp("ZZ"))], precision=0.01).result())
    assert "exact" not in ev["execution"]

def test_qiskit_sampler_is_not_exact(record):
    pytest.importorskip("qiskit")
    from qiskit import QuantumCircuit
    from qiskit.primitives import StatevectorSampler
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    row, ev, _ = record("qiskit", lambda: StatevectorSampler().run([qc], shots=50).result())
    _assert_sampled(row, ev, 50)

def test_pennylane_analytic_and_shots(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev)
    def bell_zz():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        return qml.expval(qml.PauliZ(0) @ qml.PauliZ(1))

    _assert_exact(*record("pennylane", bell_zz))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sampled = qml.set_shots(bell_zz, shots=100)
    row, ev, _ = record("pennylane", sampled)
    _assert_sampled(row, ev, 100)

def test_cirq_expectation_values_and_run(record):
    cirq = pytest.importorskip("cirq")
    q = cirq.LineQubit.range(2)
    c = cirq.Circuit(cirq.H(q[0]), cirq.CNOT(*q))
    _assert_exact(*record("cirq", lambda: cirq.Simulator().simulate_expectation_values(c, [cirq.Z(q[0]) * cirq.Z(q[1])])))
    measured = c + cirq.measure(*q, key="m")
    row, ev, _ = record("cirq", lambda: cirq.Simulator().run(measured, repetitions=40), measurement_key="m")
    _assert_sampled(row, ev, 40)

def test_braket_shots_zero_and_sampled(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit, Observable
    from braket.devices import LocalSimulator
    circ = Circuit().h(0).cnot(0, 1).expectation(Observable.Z() @ Observable.Z(), target=[0, 1])
    _assert_exact(*record("braket", lambda: LocalSimulator().run(circ, shots=0).result()))
    row, ev, _ = record("braket", lambda: LocalSimulator().run(Circuit().h(0).cnot(0, 1), shots=30).result())
    _assert_sampled(row, ev, 30)

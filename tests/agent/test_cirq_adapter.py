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

# --- Google Quantum Engine API, run on the Quantum Virtual Machine (cirq_google, local) ---------------------

def _qvm(processor_id="willow_pink"):
    cg = pytest.importorskip("cirq_google")
    engine = cg.engine.create_default_noisy_quantum_virtual_machine(processor_id=processor_id,
                                                                    simulator_class=cirq.Simulator)
    proc = engine.get_processor(processor_id)
    qubits = sorted(proc.get_device().metadata.qubit_set)
    q0 = qubits[0]
    q1 = next(q for q in qubits if q.is_adjacent(q0))
    bell = cirq.optimize_for_target_gateset(cirq.Circuit(cirq.H(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1, key="m")),
                                            gateset=cirq.CZTargetGateset())
    return proc, bell

def test_qvm_sampler_result_is_labeled_and_keeps_job_id(record):
    proc, bell = _qvm()
    ev, _ = record(lambda: proc.get_sampler().run(bell, repetitions=100), measurement_key="m")
    assert ev["backend"] == {"provider": "local_sim", "name": "willow_pink (virtual)"}  # was local_sim / Simulator
    pj = ev["execution"]["provider_job"]
    assert pj["virtual"] is True and pj["processor"] == "willow_pink"
    assert pj["job_id"].startswith("projects/") and "/processors/willow_pink/job/" in pj["job_id"]
    assert sum(ev["artifacts"]["counts"]["histogram"].values()) == 100

def test_qvm_job_returned_is_read_with_details_and_circuit(record):
    proc, bell = _qvm("weber")
    ev, _ = record(lambda: proc.run_sweep(bell, repetitions=100), measurement_key="m")
    assert sum(ev["artifacts"]["counts"]["histogram"].values()) == 100  # the finished local job is read
    pj = ev["execution"]["provider_job"]
    assert pj["status"] == "SUCCESS" and pj["processor"] == "weber" and pj["program_id"]
    assert pj["created"].endswith("Z") and pj["calibration"] == "2021-11-03T07:06:28.204000Z"  # Weber median calibration
    cm = ev["program"]["circuit_metrics"]
    assert cm["source"] == "job" and cm["two_qubit_gate_count_post"] == 1

def test_qvm_sweep_records_one_batch_per_point(record):
    sympy = pytest.importorskip("sympy")
    proc, _ = _qvm()
    qubits = sorted(proc.get_device().metadata.qubit_set)
    q0 = qubits[0]
    q1 = next(q for q in qubits if q.is_adjacent(q0))
    theta = sympy.Symbol("theta")
    circuit = cirq.optimize_for_target_gateset(
        cirq.Circuit(cirq.ry(theta).on(q0), cirq.CNOT(q0, q1), cirq.measure(q0, q1, key="m")), gateset=cirq.CZTargetGateset())
    ev, _ = record(lambda: proc.run_sweep(circuit, params=cirq.Points("theta", [0.0, 1.0]), repetitions=50),
                   measurement_key="m", await_result=True)
    assert [b["shots"] for b in ev["artifacts"]["batches"]] == [50, 50]

"""Backend/provider labels for real Qiskit execution paths (skipped when Qiskit is not installed)."""

from __future__ import annotations

import httpx
import pytest

qiskit = pytest.importorskip("qiskit")
from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister, transpile  # noqa: E402

@pytest.fixture
def record(collector, monkeypatch):
    """Run a decorated function against a real collector and return the stored event."""
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        wrapped = observe_run(project="labels", tags={"sdk": "qiskit"},
                              endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)
        wrapped()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def bell() -> QuantumCircuit:
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return qc

def _assert_bell_counts(event, shots=1024):
    hist = event["artifacts"]["counts"]["histogram"]
    assert set(hist) <= {"00", "11"} and sum(hist.values()) == shots
    assert event["execution"]["shots"] == shots

def test_statevector_sampler_is_not_labeled_ibm(record):
    from qiskit.primitives import StatevectorSampler

    ev = record(lambda: StatevectorSampler().run([bell()], shots=1024).result())
    assert ev["backend"] == {"provider": "unknown", "name": "unknown"}
    _assert_bell_counts(ev)

def test_explicit_backend_and_provider(record):
    from qiskit.primitives import StatevectorSampler

    ev = record(lambda: StatevectorSampler().run([bell()], shots=1024).result(),
                backend="statevector_sampler", provider="local_sim")
    assert ev["backend"] == {"provider": "local_sim", "name": "statevector_sampler"}

def test_aer_sampler_v2_is_local_sim(record):
    aer_primitives = pytest.importorskip("qiskit_aer.primitives")
    ev = record(lambda: aer_primitives.SamplerV2().run([bell()], shots=1024).result())
    assert ev["backend"] == {"provider": "local_sim", "name": "aer_simulator"}
    _assert_bell_counts(ev)

def test_legacy_aer_result_uses_backend_name(record):
    qiskit_aer = pytest.importorskip("qiskit_aer")
    sim = qiskit_aer.AerSimulator()
    ev = record(lambda: sim.run(transpile(bell(), sim), shots=1024).result())
    assert ev["backend"] == {"provider": "local_sim", "name": "aer_simulator"}
    _assert_bell_counts(ev)

def test_backend_object_passed_explicitly(record):
    qiskit_aer = pytest.importorskip("qiskit_aer")
    from qiskit.primitives import BackendSamplerV2

    sim = qiskit_aer.AerSimulator()
    ev = record(lambda: BackendSamplerV2(backend=sim).run([bell()], shots=1024).result(), backend=sim)
    assert ev["backend"] == {"provider": "local_sim", "name": "aer_simulator"}

def test_runtime_job_backend_is_read_with_await_result(record):
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2

    fake = FakeManilaV2()
    # Returning the job lets QObserva read job.backend before resolving the result.
    ev = record(lambda: runtime.SamplerV2(mode=fake).run([transpile(bell(), fake)], shots=1024),
                await_result=True)
    # Fake backends simulate IBM devices locally; they must not be reported as IBM hardware.
    assert ev["backend"] == {"provider": "local_sim", "name": "fake_manila"}
    hist = ev["artifacts"]["counts"]["histogram"]
    assert sum(hist.values()) == 1024

def test_custom_classical_register_name(record):
    from qiskit.primitives import StatevectorSampler

    qr, cr = QuantumRegister(2), ClassicalRegister(2, "cr")
    qc = QuantumCircuit(qr, cr)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure(qr, cr)
    ev = record(lambda: StatevectorSampler().run([qc], shots=1024).result())
    _assert_bell_counts(ev)

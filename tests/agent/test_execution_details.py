"""
Execution timeline, runtime options and timing recorded from real local runs.

IBM hardware-only fields (execution spans, non-zero quantum_seconds) and AWS cost cannot be produced
locally; the local runs here check that the same code paths record what local runs do report, and
that local runs claim no hardware time or cost.
"""

from __future__ import annotations

import warnings
from datetime import datetime

import httpx
import pytest

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(sdk, fn, **decorator_kwargs):
        observe_run(project="execution", tags={"sdk": sdk},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def _isa_bell(fake):
    from qiskit import QuantumCircuit, transpile
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    return transpile(qc, fake, seed_transpiler=3)

def _parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))

def test_runtime_job_timeline(record):
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    pytest.importorskip("qiskit_aer")
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    isa = _isa_bell(fake)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ev = record("qiskit", lambda: runtime.SamplerV2(mode=fake).run([isa], shots=100))

    tl = ev["execution"]["timeline"]
    assert tl["source"] == "ibm_runtime_job"
    assert tl["created"].endswith("Z") and tl["finished"].endswith("Z")
    assert _parse(tl["created"]) <= _parse(tl["running"]) <= _parse(tl["finished"])
    # The job ran during this test, so the (UTC) timestamps fall inside the run's own start/end.
    started, ended = _parse(ev["execution"]["started_at"]), _parse(ev["execution"]["ended_at"])
    assert abs((_parse(tl["created"]) - started).total_seconds()) < 60
    assert _parse(tl["finished"]) <= ended or abs((_parse(tl["finished"]) - ended).total_seconds()) < 1
    assert ev["execution"]["queue_ms"] >= 0
    # Local mode reports quantum_seconds = 0: no QPU time is claimed.
    assert "qpu_time_s" not in (ev["execution"].get("resource_usage") or {})

def test_executor_sampler_options_are_recorded(record):
    pytest.importorskip("qiskit_aer")
    executor = pytest.importorskip("qiskit_ibm_runtime.executor_sampler")
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    isa = _isa_bell(fake)
    sampler = executor.Sampler(mode=fake)
    sampler.options.twirling.enable_gates = True
    sampler.options.dynamical_decoupling.enable = True

    ev = record("qiskit", lambda: sampler.run([isa], shots=128))

    opts = ev["execution"]["options"]
    assert opts["twirling"]["enable_gates"] is True
    assert opts["dynamical_decoupling"]["enable"] is True
    assert opts["dynamical_decoupling"]["sequence_type"] == "XX"
    assert sum(ev["artifacts"]["counts"]["histogram"].values()) == ev["execution"]["shots"]

def test_aer_simulator_time_is_recorded(record):
    pytest.importorskip("qiskit_aer")
    from qiskit import QuantumCircuit
    from qiskit_aer.primitives import SamplerV2
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()

    ev = record("qiskit", lambda: SamplerV2().run([qc], shots=200).result())

    assert 0 < ev["execution"]["resource_usage"]["cpu_time_s"] < 60

def test_braket_local_timeline_and_no_cost(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator

    ev = record("braket", lambda: LocalSimulator().run(Circuit().h(0).cnot(0, 1), shots=50).result())

    tl = ev["execution"]["timeline"]
    assert tl["source"] == "braket_task"
    assert _parse(tl["created"]) <= _parse(tl["finished"])
    assert ev["cost"]["estimated_cost"] is None  # the Tracker records AWS tasks only

# job.metrics() of a real IBM Quantum Platform job (SamplerV2 on ibm_kingston, job dat9iqjojkfs738qc780,
# 2026-09-28), recorded during the live check, with the account identity ("caller") removed.
# Real jobs report timestamps as ISO strings and billed QPU time as qpu_charge_time_seconds;
# local testing mode (tested above) uses datetimes and quantum_seconds instead.
IBM_KINGSTON_JOB_METRICS = {
    "qiskit_version": "qiskit_ibm_runtime-0.50.0,qiskit-2.5.2*,qiskit_aer-0.17.2",
    "timestamps": {"created": "2026-09-28T16:44:27.019265Z", "finished": "2026-09-28T16:45:16.83494Z",
                   "running": "2026-09-28T16:45:11.089205Z"},
    "usage": {"qpu_charge_time_seconds": 2, "value": 0.0327, "unit": "resource_units", "status": "complete",
              "details": [{"value": 0.0327, "unit": "resource_units",
                           "metric": {"id": "caffe3ca-729c-5750-8777-df63bbf8bfd9", "value": 2}}]},
    "circuits_execution_time_ns": 261038848,
}

def test_real_ibm_job_metrics_are_read():
    """Regression for the 2026-09-28 live run: the timeline, queue time and QPU time were all dropped."""
    pytest.importorskip("qiskit")
    from qobserva.adapters.qiskit_adapter import _job_metrics

    # A stand-in job object: it only replays the recorded metrics() payload of the real job above, so the
    # parsing is tested against IBM's real data without IBM credentials (which CI doesn't have).
    class RecordedJob:
        def metrics(self):
            return IBM_KINGSTON_JOB_METRICS
    RecordedJob.__module__ = "qiskit_ibm_runtime.runtime_job_v2"

    resource_usage = {}
    out = _job_metrics(RecordedJob(), resource_usage)

    assert out["timeline"] == {"created": "2026-09-28T16:44:27.019265Z", "running": "2026-09-28T16:45:11.089205Z",
                               "finished": "2026-09-28T16:45:16.834940Z", "source": "ibm_runtime_job"}
    assert out["queue_ms"] == 44069  # created -> running
    assert resource_usage == {"qpu_time_s": 2.0, "circuit_execution_time_s": 0.261039}

# --- 0.1.10: Runtime executor Estimator (fixes 2-4) -------------------------------------------

def _executor_estimator_job(precision):
    pytest.importorskip("qiskit_aer")
    executor = pytest.importorskip("qiskit_ibm_runtime.executor_estimator")
    from qiskit import QuantumCircuit, transpile
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    isa = transpile(qc, fake, seed_transpiler=3)
    obs = [SparsePauliOp("ZZ").apply_layout(isa.layout), SparsePauliOp("XX").apply_layout(isa.layout)]
    return executor.Estimator(mode=fake).run([(isa, obs)], precision=precision)

def test_executor_estimator_shots_precision_and_ensemble_error(record):
    """Fixes 2 and 4: shots/target precision live in result.metadata; ensemble_standard_error per value."""
    holder = {}

    def run():
        holder["job"] = _executor_estimator_job(0.05)
        return holder["job"]

    ev = record("qiskit", run)
    result = holder["job"].result()

    assert ev["execution"]["shots"] == result.metadata["shots"] > 1
    assert ev["execution"]["target_precision"] == pytest.approx(0.05)
    exps = ev["artifacts"]["expectations"]
    data = result[0].data
    assert [e["operator"] for e in exps] == ["pub0[0]", "pub0[1]"]
    assert [e["value"] for e in exps] == pytest.approx(list(data.evs))
    assert [e["stderr"] for e in exps] == pytest.approx(list(data.stds))
    assert [e["ensemble_stderr"] for e in exps] == pytest.approx(list(data.ensemble_standard_error))

def test_executor_jobs_record_circuit_metrics_from_quantum_program(record):
    """Fix 3: job.inputs is a QuantumProgram; its first item's circuit is the one executed."""
    holder = {}

    def run():
        holder["job"] = _executor_estimator_job(0.1)
        return holder["job"]

    ev = record("qiskit", run)
    executed = holder["job"].inputs.items[0].circuit

    cm = ev["program"]["circuit_metrics"]
    assert cm["source"] == "job"
    assert cm["two_qubit_gate_count_post"] == 1
    assert cm["num_qubits"] >= 2
    assert cm["depth_post"] <= executed.depth()

def test_executor_sampler_records_circuit_metrics(record):
    pytest.importorskip("qiskit_aer")
    executor = pytest.importorskip("qiskit_ibm_runtime.executor_sampler")
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    isa = _isa_bell(fake)

    ev = record("qiskit", lambda: executor.Sampler(mode=fake).run([isa], shots=64))

    cm = ev["program"]["circuit_metrics"]
    assert cm["source"] == "job"
    assert cm["two_qubit_gate_count_post"] == 1
    assert sum(ev["artifacts"]["counts"]["histogram"].values()) == ev["execution"]["shots"] == 64

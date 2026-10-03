"""
Provider job ids, the circuit's text form (QASM/Quil) and diagram, and IBM's applied options and
chunk timing (added after the 2026-09-28 IBM live run, to match what IBM's job page shows).
"""

from __future__ import annotations

import warnings
from datetime import datetime, timezone

import httpx
import pytest

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(sdk, fn, **decorator_kwargs):
        observe_run(project="jobtext", tags={"sdk": sdk},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return run, httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def _bell():
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure_all()
    return qc

# --- Provider job ids ---------------------------------------------------------------------------

def test_runtime_job_id_is_recorded_and_listed(record):
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    pytest.importorskip("qiskit_aer")
    from qiskit import transpile
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    isa = transpile(_bell(), fake, seed_transpiler=1)
    jobs = []

    def run():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            job = runtime.SamplerV2(mode=fake).run([isa], shots=100)
        jobs.append(job)
        return job

    row, ev = record("qiskit", run)

    pj = ev["execution"]["provider_job"]
    assert pj["job_id"] == jobs[0].job_id()
    assert pj["provider"] == "ibm" and pj["program"] == "sampler" and pj["items"] == 1 and pj["mode"] == "job"
    assert row["job_id"] == jobs[0].job_id()  # in the runs list, for the Job ID column and search

def test_local_primitive_job_id_is_recorded(record):
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorSampler
    jobs = []

    def run():
        jobs.append(StatevectorSampler().run([_bell()], shots=50))
        return jobs[-1]

    row, ev = record("qiskit", run)

    assert ev["execution"]["provider_job"] == {"job_id": jobs[0].job_id()}
    assert row["job_id"] == jobs[0].job_id()

# --- Circuit text and diagram -------------------------------------------------------------------

def test_qiskit_circuit_qasm_and_diagram(record):
    pytest.importorskip("qiskit")
    from qiskit import qasm3
    from qiskit.primitives import StatevectorSampler
    qc = _bell()

    _, ev = record("qiskit", lambda: StatevectorSampler().run([qc], shots=50).result(), circuit=qc)

    c = ev["program"]["circuit"]
    assert c["format"] == "openqasm3" and c["from"] == "decorator"
    assert c["source"]["text"] == qasm3.dumps(qc)
    assert "q_0" in c["diagram"]["text"] and "q_1" in c["diagram"]["text"]

def test_capture_hash_keeps_metrics_but_not_the_circuit(record):
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorSampler
    qc = _bell()

    _, ev = record("qiskit", lambda: StatevectorSampler().run([qc], shots=50).result(), circuit=qc,
                   capture_program="hash")

    assert "circuit" not in ev["program"]
    assert ev["program"]["circuit_metrics"]["num_qubits"] == 2
    assert ev["program"]["program_hash"]

def test_dynamical_decoupling_qubits_are_not_counted_as_working():
    """A circuit built like IBM's executor template, which pads idle qubits with delays and X pairs
    (154 of 156 qubits on ibm_kingston, 2026-09-28)."""
    pytest.importorskip("qiskit")
    from qiskit import QuantumCircuit
    from qobserva.adapters.circuits import describe_circuit, describe_circuit_source
    qc = QuantumCircuit(6, 2)
    qc.h(0)
    qc.cx(0, 1)
    for q in range(2, 6):  # an XX decoupling sequence on idle qubits
        qc.delay(100, q)
        qc.x(q)
        qc.delay(200, q)
        qc.x(q)
    qc.measure([0, 1], [0, 1])

    assert describe_circuit(qc)["num_qubits"] == 2
    diagram = describe_circuit_source(qc)["diagram"]["text"]
    assert "q_0" in diagram and "q_2" not in diagram

def test_cirq_braket_pyquil_circuit_text():
    from qobserva.adapters.circuits import describe_circuit_source
    cirq = pytest.importorskip("cirq")
    q = cirq.LineQubit.range(2)
    cc = cirq.Circuit(cirq.H(q[0]), cirq.CNOT(q[0], q[1]), cirq.measure(*q, key="m"))
    c = describe_circuit_source(cc)
    assert c["format"] == "openqasm2" and "cx" in c["source"]["text"] and c["diagram"]["text"] == cc.to_text_diagram()

    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit
    b = describe_circuit_source(Circuit().h(0).cnot(0, 1))
    assert b["format"] == "openqasm3" and "cnot" in b["source"]["text"] and "H" in b["diagram"]["text"]

    pytest.importorskip("pyquil")
    from pyquil import Program
    from pyquil.gates import CNOT, H
    p = describe_circuit_source(Program(H(0), CNOT(0, 1)))
    assert p == {"format": "quil", "source": {"text": "H 0\nCNOT 0 1\n"}}

def test_pennylane_qnode_text(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.set_shots(20)
    @qml.qnode(dev)
    def bell():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        return qml.counts()

    _, ev = record("pennylane", bell)

    c = ev["program"]["circuit"]
    assert c["from"] == "qnode" and c["diagram"]["text"] == qml.draw(bell)()
    assert c["format"] == "openqasm2" and "cx" in c["source"]["text"]

# --- IBM applied options and chunk timing (values recorded from real ibm_kingston jobs) ---------------

# result.metadata of the real EstimatorV2 job dat9j8lvr3kc73el5d1g (resilience_level=1), 2026-09-28
IBM_ESTIMATOR_RESULT_METADATA = {
    "dynamical_decoupling": {"enable": False, "sequence_type": "XX", "extra_slack_distribution": "middle",
                             "scheduling_method": "alap"},
    "twirling": {"enable_gates": False, "enable_measure": True, "num_randomizations": "auto",
                 "shots_per_randomization": "auto", "interleave_randomizations": True, "strategy": "active-accum"},
    "resilience": {"measure_mitigation": True, "zne_mitigation": False, "pec_mitigation": False},
    "version": 2,
}

def test_applied_options_from_ibm_estimator_metadata():
    pytest.importorskip("qiskit")
    from qiskit.primitives import PrimitiveResult
    from qobserva.adapters.qiskit_adapter import _applied_options

    applied = _applied_options(PrimitiveResult([], metadata=IBM_ESTIMATOR_RESULT_METADATA))

    assert applied["resilience"] == {"measure_mitigation": True, "zne_mitigation": False, "pec_mitigation": False}
    assert applied["twirling"]["enable_measure"] is True
    assert "version" not in applied

def test_chunk_timing_from_ibm_executor_metadata():
    """Chunk timing of the real executor job dat9jn3ojkfs738qc8d0 (2026-09-28), in IBM's own classes."""
    pytest.importorskip("qiskit_ibm_runtime")
    samplomatic = pytest.importorskip("samplomatic.quantum_program.quantum_program_result")
    from qiskit.primitives import PrimitiveResult
    from qiskit_ibm_runtime.results.quantum_program import Metadata
    from qobserva.adapters.qiskit_adapter import _chunk_timing
    span = samplomatic.ChunkSpan(start=datetime(2026, 9, 28, 16, 46, 23, 156456, tzinfo=timezone.utc),
                                 stop=datetime(2026, 9, 28, 16, 46, 24, 409399, tzinfo=timezone.utc),
                                 parts=[samplomatic.ChunkPart(idx_item=0, size=16)])

    ct = _chunk_timing(PrimitiveResult([], metadata={"executor": Metadata(chunk_timing=[span]), "shots": 64}))

    assert ct == {"count": 1, "total_s": 1.252943, "chunks": [{
        "start": "2026-09-28T16:46:23.156456Z", "stop": "2026-09-28T16:46:24.409399Z",
        "duration_s": 1.252943, "parts": [{"item": 0, "size": 16}]}]}

def test_region_is_kept_but_not_the_account_crn():
    pytest.importorskip("qiskit")
    from qobserva.adapters.qiskit_adapter import _region_from_crn
    # CRN format of the IBM instance used on 2026-09-28, with the account/instance ids replaced
    assert _region_from_crn("crn:v1:bluemix:public:quantum-computing:us-east:a/ACCOUNT:INSTANCE::") == "us-east"
    assert _region_from_crn(None) is None

def test_decoupling_pulses_are_not_counted_as_gates():
    """Gate counts, depth and 2q count describe the computation, like the qubit count (for circuits padded like IBM's
    executor template: the real one had 462 delays and 308 X on idle qubits around 21 gates)."""
    pytest.importorskip("qiskit")
    from qiskit import QuantumCircuit
    from qobserva.adapters.circuits import describe_circuit
    qc = QuantumCircuit(6, 2)
    qc.h(0)
    qc.cx(0, 1)
    for q in range(2, 6):
        qc.delay(100, q)
        qc.x(q)
        qc.delay(200, q)
        qc.x(q)
    qc.measure([0, 1], [0, 1])

    m = describe_circuit(qc)

    assert m["gate_counts"] == {"h": 1, "cx": 1}
    assert m["two_qubit_gate_count"] == 1
    assert m["depth"] == 3  # h, cx, measure

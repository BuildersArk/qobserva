"""
Circuit metrics (qubits, depth, 2-qubit gates, gate breakdown) recorded from real SDK circuits.

Sources: observe_run(circuit=...), the circuits a Qiskit Runtime job ran (job.inputs), and PennyLane
QNodes (qml.specs at device level). Depth/2q counts are "post" (as executed) for transpiled circuits
and local simulator runs, "pre" otherwise.
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
        observe_run(project="circuits", tags={"sdk": sdk},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def _ghz3():
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(3)
    qc.h(0)
    qc.cx(0, 1)
    qc.cx(1, 2)
    qc.measure_all()
    return qc

def test_qiskit_circuit_param_on_local_simulator(record, collector):
    pytest.importorskip("qiskit_aer")
    from qiskit_aer import AerSimulator
    from qiskit_aer.primitives import SamplerV2
    qc = _ghz3()

    ev = record("qiskit", lambda: SamplerV2().run([qc], shots=500).result(), circuit=qc,
                backend=AerSimulator(), benchmark_params={"target_bitstrings": ["000", "111"]})

    cm = ev["program"]["circuit_metrics"]
    assert cm["num_qubits"] == 3
    assert cm["depth_post"] == qc.depth()
    assert cm["two_qubit_gate_count_post"] == 2
    assert cm["gate_counts"] == {"h": 1, "cx": 2}
    assert cm["source"] == "decorator"

    # The Depth vs Success chart reads both values from the run summary.
    run = httpx.get(f"{collector}/v1/runs", params={"limit": 1, "include_summary": "true"}).json()[0]
    assert run["summary"]["metrics"]["qc.circuit.depth_post"] == qc.depth()
    assert run["summary"]["metrics"]["qc.quality.success_probability"] == pytest.approx(1.0)

def test_qiskit_runtime_job_circuit_is_read_from_job_inputs(record):
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    pytest.importorskip("qiskit_aer")
    from qiskit import transpile
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    isa = transpile(_ghz3(), fake, seed_transpiler=1)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ev = record("qiskit", lambda: runtime.SamplerV2(mode=fake).run([isa], shots=200))

    cm = ev["program"]["circuit_metrics"]
    assert cm["source"] == "job"
    assert cm["depth_post"] == isa.depth()
    assert cm["two_qubit_gate_count_post"] == isa.num_nonlocal_gates()
    assert cm["num_qubits"] == 3  # active qubits, not the device's 5
    assert "rz" in cm["gate_counts"] or "sx" in cm["gate_counts"]  # device basis gates

def test_untranspiled_circuit_on_unknown_backend_is_pre(record):
    """Without a transpiled circuit or a local backend, the given circuit may not be what ran."""
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorSampler
    qc = _ghz3()

    ev = record("qiskit", lambda: StatevectorSampler().run([qc], shots=50).result(), circuit=qc)

    cm = ev["program"]["circuit_metrics"]
    assert ev["backend"]["provider"] == "unknown"
    assert cm["depth_pre"] == qc.depth() and "depth_post" not in cm

def test_pennylane_qnode_specs(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=3)

    @qml.set_shots(100)
    @qml.qnode(dev)
    def ghz():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        qml.CNOT([1, 2])
        return qml.counts()

    ev = record("pennylane", ghz)

    cm = ev["program"]["circuit_metrics"]
    assert cm == {"num_qubits": 3, "depth_post": 3, "two_qubit_gate_count_post": 2,
                  "gate_counts": {"Hadamard": 1, "CNOT": 2}, "source": "qnode"}

def test_cirq_circuit_param(record):
    cirq = pytest.importorskip("cirq")
    q = cirq.LineQubit.range(3)
    circuit = cirq.Circuit(cirq.H(q[0]), cirq.CNOT(q[0], q[1]), cirq.CNOT(q[1], q[2]), cirq.measure(*q, key="m"))

    ev = record("cirq", lambda: cirq.Simulator().run(circuit, repetitions=20), circuit=circuit)

    cm = ev["program"]["circuit_metrics"]
    assert cm["num_qubits"] == 3
    assert cm["depth_post"] == 4  # moments, including the measurement moment
    assert cm["two_qubit_gate_count_post"] == 2

def test_braket_circuit_param(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    c = Circuit().h(0).cnot(0, 1).cnot(1, 2)

    ev = record("braket", lambda: LocalSimulator().run(c, shots=20).result(), circuit=c)

    cm = ev["program"]["circuit_metrics"]
    assert cm["num_qubits"] == 3 and cm["depth_post"] == 3 and cm["two_qubit_gate_count_post"] == 2
    assert cm["gate_counts"] == {"H": 1, "CNot": 2}

def test_pyquil_program_metrics_without_a_qvm():
    """Program metrics need no QVM: they are read from the pyQuil Program itself."""
    pytest.importorskip("pyquil")
    from pyquil import Program
    from pyquil.gates import CNOT, H, MEASURE
    from qobserva.adapters.circuits import describe_circuit
    p = Program()
    ro = p.declare("ro", "BIT", 3)
    p += H(0)
    p += CNOT(0, 1)
    p += CNOT(1, 2)
    p += H(0)  # runs in parallel with CNOT(1, 2)
    p += [MEASURE(i, ro[i]) for i in range(3)]

    m = describe_circuit(p)

    assert m == {"num_qubits": 3, "depth": 3, "two_qubit_gate_count": 2, "gate_counts": {"H": 2, "CNOT": 2}}

def test_capture_program_none_records_no_circuit(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=1)

    @qml.qnode(dev)
    def f():
        qml.Hadamard(0)
        return qml.expval(qml.PauliZ(0))

    ev = record("pennylane", f, capture_program="none")

    assert not ev["program"].get("circuit_metrics")

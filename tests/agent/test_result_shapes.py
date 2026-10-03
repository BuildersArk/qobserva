"""
Every result shape an SDK commonly returns must be recorded with its values, not as an empty "success".

Each test runs the real SDK (skipped when it is not installed) through @observe_run and reads the
stored run back from a real collector. These cover the silent-loss cases found on 2026-09-24
(ITEM3_PLAN_SDK_FEATURES.md, section 1: A1-A8) and the "nothing extracted" warning.
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
        observe_run(project="shapes", tags={"sdk": sdk},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def _values(ev):
    return [e["value"] for e in ev["artifacts"]["expectations"]]

# --- Qiskit (A1) -------------------------------------------------------------------------------

def _bell_and_observables():
    from qiskit import QuantumCircuit
    from qiskit.quantum_info import SparsePauliOp
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    return qc, [SparsePauliOp("ZZ"), SparsePauliOp("XX"), SparsePauliOp("ZI")]

def test_qiskit_statevector_estimator_expectations(record):
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorEstimator
    qc, obs = _bell_and_observables()

    ev = record("qiskit", lambda: StatevectorEstimator().run([(qc, obs)]).result())

    art = ev["artifacts"]
    assert art["result_type"] == "expectations"
    assert _values(ev) == pytest.approx([1.0, 1.0, 0.0], abs=1e-9)
    assert [e["operator"] for e in art["expectations"]] == ["pub0[0]", "pub0[1]", "pub0[2]"]
    assert all(e["stderr"] == pytest.approx(0.0) for e in art["expectations"])
    assert "counts" not in art

def test_qiskit_aer_estimator_expectations_and_backend(record):
    pytest.importorskip("qiskit_aer")
    from qiskit_aer.primitives import EstimatorV2
    qc, obs = _bell_and_observables()

    ev = record("qiskit", lambda: EstimatorV2().run([(qc, obs)]).result())

    assert ev["artifacts"]["result_type"] == "expectations"
    assert _values(ev) == pytest.approx([1.0, 1.0, 0.0], abs=1e-9)
    assert ev["backend"] == {"provider": "local_sim", "name": "aer_simulator"}

def test_qiskit_estimator_job_returned_without_await(record):
    """A local primitive job returned as-is is resolved, like await_result=True."""
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorEstimator
    qc, obs = _bell_and_observables()

    ev = record("qiskit", lambda: StatevectorEstimator().run([(qc, obs)]))

    assert _values(ev) == pytest.approx([1.0, 1.0, 0.0], abs=1e-9)

def test_qiskit_runtime_local_mode_estimator(record):
    """IBM Runtime's local testing mode (a fake backend) runs locally, so its job is resolved too."""
    runtime = pytest.importorskip("qiskit_ibm_runtime")
    pytest.importorskip("qiskit_aer")
    from qiskit import transpile
    from qiskit.quantum_info import SparsePauliOp
    from qiskit_ibm_runtime.fake_provider import FakeManilaV2
    fake = FakeManilaV2()
    qc, _ = _bell_and_observables()
    isa = transpile(qc, fake, seed_transpiler=7)
    zz = SparsePauliOp("ZZ").apply_layout(isa.layout)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        ev = record("qiskit", lambda: runtime.EstimatorV2(mode=fake).run([(isa, zz)]))

    assert ev["artifacts"]["result_type"] == "expectations"
    assert 0.8 < _values(ev)[0] <= 1.0  # noisy fake device: close to, not exactly, 1
    assert ev["artifacts"]["expectations"][0]["stderr"] > 0
    assert ev["execution"]["shots"] == 4096
    assert ev["backend"] == {"provider": "local_sim", "name": "fake_manila"}

# --- Braket (A2, A3, backend labels)-----------------------------------------------------------

def test_braket_expectation_exact(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit, Observable
    from braket.devices import LocalSimulator
    c = Circuit().h(0).cnot(0, 1).expectation(Observable.Z() @ Observable.Z(), target=[0, 1])

    ev = record("braket", lambda: LocalSimulator().run(c, shots=0).result())

    art = ev["artifacts"]
    assert art["result_type"] == "expectations"
    assert art["expectations"] == [{"operator": "Z0 Z1", "value": pytest.approx(1.0), "stderr": None,
                                    "kind": "expectation"}]
    assert ev["backend"] == {"provider": "local_sim", "name": "LocalSimulator"}

def test_braket_expectation_kept_alongside_counts(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit, Observable
    from braket.devices import LocalSimulator
    c = Circuit().h(0).cnot(0, 1).expectation(Observable.Z(), target=[0])

    ev = record("braket", lambda: LocalSimulator().run(c, shots=200).result())

    art = ev["artifacts"]
    assert sum(art["counts"]["histogram"].values()) == 200
    assert art["expectations"][0]["operator"] == "Z0"
    assert -1.0 <= art["expectations"][0]["value"] <= 1.0

def test_braket_probability_and_variance(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit, Observable
    from braket.devices import LocalSimulator
    c = Circuit().h(0).cnot(0, 1).probability(target=[0, 1]).variance(Observable.X(), target=[0])

    ev = record("braket", lambda: LocalSimulator().run(c, shots=0).result())

    art = ev["artifacts"]
    assert art["probabilities"]["values"] == pytest.approx({"00": 0.5, "11": 0.5})
    assert art["expectations"] == [{"operator": "X0", "value": pytest.approx(1.0), "stderr": None,
                                    "kind": "variance"}]

def test_braket_local_task_returned_without_result(record):
    pytest.importorskip("braket.circuits")
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
    bell = Circuit().h(0).cnot(0, 1)

    ev = record("braket", lambda: LocalSimulator().run(bell, shots=100))

    hist = ev["artifacts"]["counts"]["histogram"]
    assert set(hist) <= {"00", "11"} and sum(hist.values()) == 100

def test_braket_device_id_labels():
    """Braket result metadata names the device by deviceId (an ARN for AWS devices)."""
    pytest.importorskip("braket.circuits")
    from qobserva.adapters.braket_adapter import backend_from_device_id

    assert backend_from_device_id("braket_sv") == {"provider": "local_sim", "name": "braket_sv"}
    assert backend_from_device_id("braket_dm") == {"provider": "local_sim", "name": "braket_dm"}
    assert backend_from_device_id("arn:aws:braket:::device/quantum-simulator/amazon/sv1") == \
        {"provider": "aws_braket", "name": "sv1"}
    assert backend_from_device_id("arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-3") == \
        {"provider": "rigetti", "name": "Ankaa-3"}
    assert backend_from_device_id("arn:aws:braket:eu-north-1::device/qpu/iqm/Garnet") == \
        {"provider": "iqm", "name": "Garnet"}

# --- Cirq (A4, A5) ----------------------------------------------------------------------------

def test_cirq_simulate_expectation_values(record):
    cirq = pytest.importorskip("cirq")
    q = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.H(q[0]), cirq.CNOT(q[0], q[1]))
    observables = [cirq.Z(q[0]) * cirq.Z(q[1]), cirq.X(q[0])]

    ev = record("cirq", lambda: cirq.Simulator().simulate_expectation_values(circuit, observables=observables))

    assert ev["artifacts"]["result_type"] == "expectations"
    assert _values(ev) == pytest.approx([1.0, 0.0], abs=1e-6)
    assert ev["backend"]["provider"] == "local_sim"
    assert ev["backend"]["name"] != "default.qubit"  # a PennyLane name: the wrong adapter claimed it

def test_cirq_run_sweep(record):
    cirq = pytest.importorskip("cirq")
    sympy = pytest.importorskip("sympy")
    q = cirq.LineQubit(0)
    t = sympy.Symbol("t")
    circuit = cirq.Circuit(cirq.rx(t).on(q), cirq.measure(q, key="m"))

    ev = record("cirq", lambda: cirq.Simulator().run_sweep(
        circuit, params=cirq.Linspace("t", 0, 3.141592653589793, 3), repetitions=100), measurement_key="m")

    art = ev["artifacts"]
    assert art["result_type"] == "batch"
    assert [b["params"] for b in art["batches"]] == [{"t": 0.0}, {"t": pytest.approx(1.5707963)},
                                                    {"t": pytest.approx(3.1415926)}]
    assert all(sum(b["histogram"].values()) == 100 for b in art["batches"])
    assert art["batches"][0]["histogram"] == {"0": 100}  # rx(0) never flips
    assert art["batches"][2]["histogram"] == {"1": 100}  # rx(pi) always flips
    assert ev["execution"]["shots"] == 300

def test_cirq_single_measurement_key_needs_no_measurement_key(record):
    cirq = pytest.importorskip("cirq")
    q = cirq.LineQubit.range(2)
    circuit = cirq.Circuit(cirq.X(q[0]), cirq.measure(*q, key="result"))

    ev = record("cirq", lambda: cirq.Simulator().run(circuit, repetitions=50))

    assert ev["artifacts"]["counts"]["histogram"] == {"10": 50}

# --- PennyLane (A6, A7) -----------------------------------------------------------------------

def test_pennylane_probs(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev)
    def probs():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        return qml.probs(wires=[0, 1])

    ev = record("pennylane", probs)

    art = ev["artifacts"]
    assert art["result_type"] == "probabilities"
    assert art["probabilities"]["values"] == pytest.approx({"00": 0.5, "11": 0.5})
    assert ev["backend"]["name"] != "cpu"  # numpy's array.device, not a PennyLane device

def test_pennylane_shot_vector_counts(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.set_shots([100, 200])
    @qml.qnode(dev)
    def bell():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        return qml.counts()

    ev = record("pennylane", bell)

    art = ev["artifacts"]
    assert [sum(b["histogram"].values()) for b in art["batches"]] == [100, 200]
    assert set(art["counts"]["histogram"]) <= {"00", "11"}
    assert sum(art["counts"]["histogram"].values()) == 300
    assert ev["execution"]["shots"] == 300

def test_pennylane_samples_become_counts(record):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.set_shots(64)
    @qml.qnode(dev)
    def bell():
        qml.PauliX(0)
        return qml.sample()

    ev = record("pennylane", bell)

    assert ev["artifacts"]["counts"]["histogram"] == {"10": 64}
    assert ev["execution"]["shots"] == 64

# --- D-Wave (A8) ------------------------------------------------------------------------------

def _bqm():
    dimod = pytest.importorskip("dimod")
    return dimod.BinaryQuadraticModel({"a": -1, "b": -1}, {("a", "b"): 2}, 0, "BINARY")

def test_dwave_simulated_annealing_is_local(record):
    bqm = _bqm()
    samplers = pytest.importorskip("dwave.samplers")

    ev = record("dwave", lambda: samplers.SimulatedAnnealingSampler().sample(bqm, num_reads=20))

    assert ev["backend"] == {"provider": "local_sim", "name": "SimulatedAnnealingSampler"}
    assert ev["artifacts"]["energies"]["value"] == -1.0

def test_dwave_embedding_and_chain_breaks(record):
    """EmbeddingComposite(return_embedding=True) on a Chimera-structured sampler records chain details."""
    dimod = pytest.importorskip("dimod")
    samplers = pytest.importorskip("dwave.samplers")
    system = pytest.importorskip("dwave.system")
    try:
        from dwave.graphs import chimera_graph  # Ocean 9.x+ (dwave-graphs)
    except ImportError:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            dnx = pytest.importorskip("dwave_networkx")
        chimera_graph = dnx.chimera_graph
    graph = chimera_graph(1)
    structured = dimod.StructureComposite(samplers.SimulatedAnnealingSampler(), list(graph.nodes), list(graph.edges))
    # A triangle cannot embed one-to-one in bipartite Chimera, so at least one chain has 2+ qubits.
    triangle = dimod.BinaryQuadraticModel({}, {("a", "b"): 1, ("b", "c"): 1, ("a", "c"): 1}, 0, "SPIN")

    ev = record("dwave", lambda: system.EmbeddingComposite(structured).sample(
        triangle, num_reads=50, return_embedding=True, seed=5))

    ann = ev["artifacts"]["annealing"]
    assert ann["num_logical_variables"] == 3
    assert ann["max_chain_length"] >= 2
    assert ann["num_physical_qubits"] >= 4
    assert 0.0 <= ann["chain_break_fraction"] <= ann["max_chain_break_fraction"] <= 1.0
    assert ev["backend"]["provider"] == "local_sim"
    assert ev["execution"]["resource_usage"]["cpu_time_s"] >= 0

# --- Nothing extracted------------------------------------------------------------------------

def test_unrecognized_result_warns_and_is_not_an_empty_success(record):
    pytest.importorskip("qiskit")
    from qiskit import QuantumCircuit
    qc = QuantumCircuit(1)  # returned by mistake instead of a result

    with pytest.warns(UserWarning, match="could not read any results"):
        ev = record("qiskit", lambda: qc)

    art = ev["artifacts"]
    assert art["result_type"] == "unknown"
    assert art["unrecognized"]["type"] == "qiskit.circuit.quantumcircuit.QuantumCircuit"
    assert "counts" not in art

def test_recognized_result_does_not_warn(record):
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorEstimator
    qc, obs = _bell_and_observables()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        record("qiskit", lambda: StatevectorEstimator().run([(qc, obs)]).result())
    assert not [w for w in caught if "could not read any results" in str(w.message)]

def test_local_job_is_still_returned_to_the_caller(collector, monkeypatch):
    """Resolving a local job for telemetry must not change what the decorated function returns."""
    pytest.importorskip("qiskit")
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qiskit.primitives import StatevectorEstimator
    from qobserva import observe_run
    qc, obs = _bell_and_observables()

    @observe_run(project="shapes", tags={"sdk": "qiskit"}, endpoint=f"{collector}/v1/ingest/run-event")
    def run():
        return StatevectorEstimator().run([(qc, obs)])

    job = run()
    assert type(job).__name__ == "PrimitiveJob"
    assert job.result()[0].data.evs[0] == pytest.approx(1.0)

# --- Collector metrics from these runs ---------------------------------------------------------

def _analysis(collector, ev):
    return httpx.get(f"{collector}/v1/runs/{ev['run_id']}/analysis").json()["metrics"]

def test_collector_metrics_for_expectations(record, collector):
    pytest.importorskip("qiskit")
    from qiskit.primitives import StatevectorEstimator
    qc, obs = _bell_and_observables()

    m = _analysis(collector, record("qiskit", lambda: StatevectorEstimator().run([(qc, obs)]).result()))

    assert m["qc.expectation.count"] == 3
    assert m["qc.expectation.mean"] == pytest.approx(2 / 3)
    assert "qc.expectation.value" not in m  # only for a single observable

def test_collector_entropy_from_probabilities(record, collector):
    qml = pytest.importorskip("pennylane")
    dev = qml.device("default.qubit", wires=2)

    @qml.qnode(dev)
    def probs():
        qml.Hadamard(0)
        qml.CNOT([0, 1])
        return qml.probs(wires=[0, 1])

    m = _analysis(collector, record("pennylane", probs))

    assert m["qc.quality.shannon_entropy_bits"] == pytest.approx(1.0)

def test_collector_metrics_for_sweep(record, collector):
    cirq = pytest.importorskip("cirq")
    sympy = pytest.importorskip("sympy")
    q = cirq.LineQubit(0)
    circuit = cirq.Circuit(cirq.rx(sympy.Symbol("t")).on(q), cirq.measure(q, key="m"))

    m = _analysis(collector, record("cirq", lambda: cirq.Simulator().run_sweep(
        circuit, params=cirq.Linspace("t", 0, 1, 4), repetitions=10)))

    assert m["qc.batch.count"] == 4

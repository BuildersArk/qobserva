"""
Circuit metrics (qubits, depth, multi-qubit gate count, gate breakdown) for each SDK's circuit type.

`describe_circuit` never imports an SDK: it dispatches on the object's module, so it is safe to call
with anything. Two-qubit gate counts include larger gates (e.g. Toffoli), like Qiskit's
num_nonlocal_gates(); measurements, barriers and other directives are not counted as gates.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

_DIRECTIVES = {"barrier", "measure", "reset", "delay", "snapshot", "save_statevector", "save_expval"}

def _qiskit_working_qubits(circuit: Any) -> set:
    """
    Qubits the computation uses. Dynamical decoupling fills idle qubits with delays and pairs of
    X (or Y) pulses that cancel to identity; qubits with only those are not counted.
    """
    by_qubit: Dict[Any, List[str]] = {}
    for inst in circuit.data:
        for q in inst.qubits:
            by_qubit.setdefault(q, []).append(inst.operation.name)
    working = set()
    for q, names in by_qubit.items():
        real = [n for n in names if n not in ("delay", "barrier")]
        if not real:
            continue
        if all(n in ("x", "y") for n in real) and sum(n == "x" for n in real) % 2 == 0 \
                and sum(n == "y" for n in real) % 2 == 0:
            continue  # a dynamical decoupling sequence: identity overall
        working.add(q)
    return working


def _without_idle_decoupling(circuit: Any, active: set) -> Any:
    """The circuit minus delays and instructions on idle (decoupling-only) qubits; itself if there are none."""
    touched = {q for inst in circuit.data if inst.operation.name not in ("delay", "barrier") for q in inst.qubits}
    if not active or touched <= active:
        return circuit
    slim = circuit.copy_empty_like()
    for inst in circuit.data:
        if inst.operation.name == "delay" or not any(q in active for q in inst.qubits):
            continue
        slim.append(inst)
    return slim


def _qiskit(circuit: Any) -> Dict[str, Any]:
    active = _qiskit_working_qubits(circuit)
    # Provider templates (IBM's executor) add decoupling pulses to every idle device qubit;
    # count only the computation, consistently with the qubit count and the diagram.
    work = _without_idle_decoupling(circuit, active)
    gate_counts: Dict[str, int] = {}
    for name, n in work.count_ops().items():
        if name not in _DIRECTIVES:
            gate_counts[str(name)] = int(n)
    return {
        "num_qubits": len(active) or circuit.num_qubits,
        "depth": int(work.depth()),
        "two_qubit_gate_count": int(work.num_nonlocal_gates()),
        "gate_counts": gate_counts,
        # transpile() sets a layout: the circuit is already mapped to a device (ISA circuit).
        "transpiled": getattr(circuit, "layout", None) is not None,
    }

def _cirq(circuit: Any) -> Dict[str, Any]:
    import cirq  # the object is a cirq.Circuit, so cirq is installed
    gate_counts: Dict[str, int] = {}
    two_q = 0
    for op in circuit.all_operations():
        if cirq.is_measurement(op):
            continue
        name = type(op.gate).__name__ if op.gate is not None else type(op).__name__
        gate_counts[name] = gate_counts.get(name, 0) + 1
        if len(op.qubits) >= 2:
            two_q += 1
    return {
        "num_qubits": len(circuit.all_qubits()),
        "depth": len(circuit),  # number of moments
        "two_qubit_gate_count": two_q,
        "gate_counts": gate_counts,
    }

def _braket(circuit: Any) -> Dict[str, Any]:
    gate_counts: Dict[str, int] = {}
    two_q = 0
    for inst in circuit.instructions:
        name = getattr(inst.operator, "name", type(inst.operator).__name__)
        if str(name).lower() in _DIRECTIVES:
            continue
        gate_counts[name] = gate_counts.get(name, 0) + 1
        if len(inst.target) >= 2:
            two_q += 1
    return {
        "num_qubits": int(circuit.qubit_count),
        "depth": int(circuit.depth),
        "two_qubit_gate_count": two_q,
        "gate_counts": gate_counts,
    }

def _layered_depth(gates: Iterable[Tuple[str, List[Any]]]) -> int:
    """ASAP depth: each gate starts after the latest gate on any of its qubits."""
    level: Dict[Any, int] = {}
    depth = 0
    for _, qubits in gates:
        start = max((level.get(q, 0) for q in qubits), default=0) + 1
        for q in qubits:
            level[q] = start
        depth = max(depth, start)
    return depth

def _pyquil(program: Any) -> Dict[str, Any]:
    gates: List[Tuple[str, List[Any]]] = []
    for inst in program.instructions:
        name = getattr(inst, "name", None)
        if not name or str(name).lower() in _DIRECTIVES or not hasattr(inst, "get_qubit_indices"):
            continue
        gates.append((str(name), sorted(inst.get_qubit_indices())))
    gate_counts: Dict[str, int] = {}
    for name, _ in gates:
        gate_counts[name] = gate_counts.get(name, 0) + 1
    return {
        "num_qubits": len(program.get_qubit_indices()),
        "depth": _layered_depth(gates),
        "two_qubit_gate_count": sum(1 for _, q in gates if len(q) >= 2),
        "gate_counts": gate_counts,
    }

def _pennylane_specs(specs: Any) -> Dict[str, Any]:
    res = specs.resources
    sizes = dict(res.gate_sizes or {})
    return {
        "num_qubits": int(res.num_allocs),
        "depth": int(res.depth),
        "two_qubit_gate_count": sum(int(n) for size, n in sizes.items() if int(size) >= 2),
        "gate_counts": {str(k): int(v) for k, v in (res.gate_types or {}).items()},
        "transpiled": True,  # measured at level="device": the gates the device executes
    }

def describe_circuit(obj: Any) -> Optional[Dict[str, Any]]:
    """Metrics for a Qiskit QuantumCircuit, Cirq Circuit, Braket Circuit, pyQuil Program or PennyLane specs."""
    if obj is None:
        return None
    cls = type(obj)
    module, name = cls.__module__ or "", cls.__name__
    try:
        if module.startswith("qiskit") and hasattr(obj, "count_ops") and hasattr(obj, "num_nonlocal_gates"):
            return _qiskit(obj)
        if module.startswith("cirq") and name in ("Circuit", "FrozenCircuit"):
            return _cirq(obj)
        if module.startswith("braket.circuits") and name == "Circuit":
            return _braket(obj)
        if module.startswith("pyquil") and name == "Program":
            return _pyquil(obj)
        if module.startswith("pennylane") and name == "CircuitSpecs":
            return _pennylane_specs(obj)
    except Exception:
        return None
    return None

def circuit_from_job(job: Any) -> Any:
    """
    The (first) circuit a Qiskit Runtime job ran: job.inputs["pubs"][0] is a pub or (circuit, ...);
    executor jobs (the client-side Sampler) carry a QuantumProgram whose items hold the circuits.
    """
    if (type(job).__module__ or "").startswith("cirq_google.engine"):
        # Google Quantum Engine / Quantum Virtual Machine job: the (first) circuit of its program.
        return job.program().get_circuit()
    inputs = getattr(job, "inputs", None)
    if not isinstance(inputs, dict):
        return None
    pubs = inputs.get("pubs") or []
    if pubs:
        pub = pubs[0]
        if isinstance(pub, (list, tuple)):
            return pub[0] if pub else None
        return getattr(pub, "circuit", pub)
    items = getattr(inputs.get("quantum_program"), "items", None) or []
    return getattr(items[0], "circuit", None) if items else None


def circuit_from_result(result: Any) -> Any:
    """
    The circuit a Braket task ran, rebuilt from the OpenQASM program its result carries
    (result.additional_metadata.action). Explicit measurements are left out, matching a circuit
    built with braket.circuits (which measures all qubits implicitly), so depth is comparable.
    """
    action = getattr(getattr(result, "additional_metadata", None), "action", None)
    source = getattr(action, "source", None)
    if not isinstance(source, str) or not source.startswith("OPENQASM"):
        return None
    from braket.circuits import Circuit
    ran = Circuit.from_ir(source)
    circuit = Circuit()
    for inst in ran.instructions:
        if type(inst.operator).__name__ != "Measure":
            circuit.add_instruction(inst)
    for result_type in ran.result_types:
        circuit.add_result_type(result_type)
    return circuit


# Stored circuit text is capped so a very large circuit cannot bloat a run record.
MAX_SOURCE_CHARS = 200_000
MAX_DIAGRAM_CHARS = 60_000
MAX_DIAGRAM_QUBITS = 20


def _cap(text: str, limit: int) -> Dict[str, Any]:
    if len(text) <= limit:
        return {"text": text}
    return {"text": text[:limit], "truncated": True, "full_length": len(text)}


def _qiskit_source(circuit: Any) -> Dict[str, Any]:
    from qiskit import qasm3
    out: Dict[str, Any] = {"format": "openqasm3", "source": _cap(qasm3.dumps(circuit), MAX_SOURCE_CHARS)}
    # Draw only the qubits that do work: device-mapped circuits span every qubit of the device,
    # and dynamical decoupling fills idle qubits with delays.
    active = _qiskit_working_qubits(circuit)
    if active and len(active) <= MAX_DIAGRAM_QUBITS:
        # Keep the gates on working qubits; drop delays and the decoupling pulses on idle ones.
        slim = circuit.copy_empty_like()
        for inst in _without_idle_decoupling(circuit, active).data:
            if inst.operation.name != "delay":
                slim.append(inst)
        out["diagram"] = _cap(str(slim.draw("text", idle_wires=False, fold=100)), MAX_DIAGRAM_CHARS)
    elif active:
        out["diagram_omitted"] = f"{len(active)} active qubits (diagrams are drawn up to {MAX_DIAGRAM_QUBITS})"
    return out


def _cirq_source(circuit: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    try:
        out.update({"format": "openqasm2", "source": _cap(circuit.to_qasm(), MAX_SOURCE_CHARS)})
    except Exception:
        pass  # not every Cirq gate has a QASM form; the diagram still describes the circuit
    if len(circuit.all_qubits()) <= MAX_DIAGRAM_QUBITS:
        out["diagram"] = _cap(circuit.to_text_diagram(), MAX_DIAGRAM_CHARS)
    return out


def _braket_source(circuit: Any) -> Dict[str, Any]:
    from braket.circuits.serialization import IRType
    out = {"format": "openqasm3", "source": _cap(circuit.to_ir(IRType.OPENQASM).source, MAX_SOURCE_CHARS)}
    if circuit.qubit_count <= MAX_DIAGRAM_QUBITS:
        out["diagram"] = _cap(str(circuit), MAX_DIAGRAM_CHARS)
    return out


def _pyquil_source(program: Any) -> Dict[str, Any]:
    return {"format": "quil", "source": _cap(program.out(), MAX_SOURCE_CHARS)}


def describe_circuit_source(obj: Any) -> Optional[Dict[str, Any]]:
    """The circuit's text form (OpenQASM / Quil) and a text diagram, for Qiskit, Cirq, Braket and pyQuil."""
    if obj is None:
        return None
    cls = type(obj)
    module, name = cls.__module__ or "", cls.__name__
    try:
        if module.startswith("qiskit") and hasattr(obj, "count_ops"):
            return _qiskit_source(obj)
        if module.startswith("cirq") and name in ("Circuit", "FrozenCircuit"):
            return _cirq_source(obj)
        if module.startswith("braket.circuits") and name == "Circuit":
            return _braket_source(obj)
        if module.startswith("pyquil") and name == "Program":
            return _pyquil_source(obj)
    except Exception:
        return None
    return None


def qnode_source(fn: Any, args: tuple, kwargs: dict) -> Optional[Dict[str, Any]]:
    """A QNode's text diagram (qml.draw) and OpenQASM 2 (from its tape). Rebuilds the circuit; no execution."""
    cls = type(fn)
    if cls.__name__ != "QNode" or "pennylane" not in (cls.__module__ or ""):
        return None
    import pennylane as qml
    out: Dict[str, Any] = {}
    try:
        out["diagram"] = _cap(qml.draw(fn)(*args, **kwargs), MAX_DIAGRAM_CHARS)
    except Exception:
        pass
    try:
        out.update({"format": "openqasm2", "source": _cap(qml.to_openqasm(fn)(*args, **kwargs), MAX_SOURCE_CHARS)})
    except Exception:
        pass  # not every operation has a QASM form; the diagram still describes the circuit
    return out or None

def qnode_specs(fn: Any, args: tuple, kwargs: dict) -> Any:
    """qml.specs for a QNode at device level. Rebuilds the circuit from the QNode's Python function; no execution."""
    cls = type(fn)
    if cls.__name__ != "QNode" or "pennylane" not in (cls.__module__ or ""):
        return None
    import pennylane as qml
    return qml.specs(fn, level="device")(*args, **kwargs)

def to_event_metrics(metrics: Dict[str, Any], executed_as_given: bool, source: str) -> Dict[str, Any]:
    """
    Event program.circuit_metrics. The depth/2q counts are "post" (as executed) when the circuit was
    already transpiled/device-level, or when it ran as given (local simulators); otherwise "pre".
    """
    stage = "post" if metrics.get("transpiled") or executed_as_given else "pre"
    out: Dict[str, Any] = {
        "num_qubits": metrics.get("num_qubits"),
        f"depth_{stage}": metrics.get("depth"),
        f"two_qubit_gate_count_{stage}": metrics.get("two_qubit_gate_count"),
        "gate_counts": metrics.get("gate_counts") or {},
        "source": source,
    }
    return {k: v for k, v in out.items() if v is not None}

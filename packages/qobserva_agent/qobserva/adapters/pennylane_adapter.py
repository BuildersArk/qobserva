from __future__ import annotations

import numbers
from typing import Any, Dict, List, Optional
from .base import Adapter, AdapterContext
from .common import (build_artifacts, expectation, histogram_from_bit_rows, merge_histograms,
                     probabilities_from_vector, to_float)
from .version_utils import get_sdk_version


def _qnode(context: AdapterContext) -> Any:
    """The decorated function when it is a PennyLane QNode (it knows its device and shots)."""
    fn = context.function
    cls = type(fn)
    if cls.__name__ == "QNode" and "pennylane" in (cls.__module__ or ""):
        return fn
    return None


def _shot_vector(qnode: Any) -> Optional[List[int]]:
    """[100, 200] for set_shots([100, 200]); None for a single shot count or analytic mode."""
    try:
        shots = qnode.shots
        if shots is not None and shots.has_partitioned_shots:
            return [int(s) for s in shots]
    except Exception:
        pass
    return None


def _classify_device(name: str) -> Dict[str, str]:
    lowered = name.lower()
    if "default." in lowered or "lightning" in lowered or "null.qubit" in lowered or "reference.qubit" in lowered:
        return {"provider": "local_sim", "name": name}
    if "qiskit" in lowered or "ibm" in lowered:
        return {"provider": "ibm", "name": name}
    if "braket" in lowered or "aws" in lowered:
        return {"provider": "aws_braket", "name": name}
    if "cirq" in lowered or "google" in lowered:
        return {"provider": "google", "name": name}
    if "ionq" in lowered:
        return {"provider": "ionq", "name": name}
    if "rigetti" in lowered or "forest" in lowered:
        return {"provider": "rigetti", "name": name}
    return {"provider": "local_sim", "name": name}


def _plugin_backend(device: Any) -> Optional[Dict[str, str]]:
    """
    The device a plugin ran the circuit on. Plugin devices are named after the plugin (qiskit.remote,
    braket.aws.qubit), not the hardware, but hold it: a Qiskit backend (pennylane-qiskit) or a Braket
    AwsDevice/LocalSimulator (amazon-braket-pennylane-plugin), labeled like the native adapters do.
    """
    target = getattr(device, "target_device", device)  # LegacyDeviceFacade wraps old-API plugin devices
    short = str(getattr(target, "short_name", "") or "")
    if short.startswith("qiskit."):
        from .qiskit_adapter import describe_backend
        return describe_backend(getattr(target, "backend", None))
    if short.startswith("braket."):
        from .braket_adapter import backend_from_device_id
        arn = getattr(getattr(target, "_device", None), "arn", None)
        if arn:
            return backend_from_device_id(arn)
        if short == "braket.local.qubit":
            return {"provider": "local_sim", "name": short}
    return None


def _plugin_job(device: Any) -> Optional[Dict[str, Any]]:
    """
    The provider job behind a plugin run, when the plugin keeps it: the Braket plugin's device.task is the
    last AwsQuantumTask (one per QNode call). pennylane-qiskit discards its IBM job after reading the result.
    """
    target = getattr(device, "target_device", device)
    if not str(getattr(target, "short_name", "") or "").startswith("braket."):
        return None
    task = getattr(target, "task", None)
    from .braket_adapter import _task_info
    return _task_info(getattr(task, "id", None), getattr(getattr(target, "_device", None), "arn", None))


def _backend(obj: Any, qnode: Any) -> Dict[str, str]:
    if qnode is not None:
        try:
            plugin = _plugin_backend(getattr(qnode, "device", None))
        except Exception:
            plugin = None
        if plugin:
            return plugin
        name = getattr(getattr(qnode, "device", None), "name", None)
        if name:
            return _classify_device(str(name))
    if isinstance(obj, dict):
        name = obj.get("device_name") or obj.get("device")
        if name:
            return _classify_device(str(name))
    # Only PennyLane objects describe a device; numpy arrays have an unrelated .device ("cpu").
    if "pennylane" in (type(obj).__module__ or "") and hasattr(obj, "device"):
        device = obj.device
        name = getattr(device, "name", None) or getattr(device, "short_name", None)
        if name:
            return _classify_device(str(name))
    # The result does not say which device ran it; default.qubit is PennyLane's default device.
    return {"provider": "local_sim", "name": "default.qubit"}


def _is_0d_object(obj: Any) -> bool:
    return _array_kind(obj) == "O" and getattr(obj, "shape", None) == ()


def _is_counts_dict(obj: Any) -> bool:
    return isinstance(obj, dict) and bool(obj) and all(isinstance(v, numbers.Real) for v in obj.values())


def _array_kind(obj: Any) -> Optional[str]:
    dtype = getattr(obj, "dtype", None)
    return getattr(dtype, "kind", None) if dtype is not None and hasattr(obj, "shape") else None


def _samples_histogram(obj: Any) -> Dict[str, int]:
    """qml.sample() -> (shots, wires) array of 0/1; qml.sample(wires=0) may give (shots,)."""
    rows = obj.tolist()
    if rows and not isinstance(rows[0], list):
        rows = [[r] for r in rows]
    if any(b not in (0, 1) for row in rows for b in row):
        return {}
    return histogram_from_bit_rows(rows)


class PennyLaneAdapter(Adapter):
    name = "pennylane"
    priority = 85  # Higher priority to match before generic dict handlers

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        # Check tags first - if SDK tag says pennylane, prioritize this adapter
        if context.tags and context.tags.get("sdk") == "pennylane":
            return True

        # Handle PennyLane objects
        if hasattr(obj, "__class__"):
            try:
                module = obj.__class__.__module__
                if module and "pennylane" in module:
                    return True
            except Exception:
                pass

        # Handle numeric/array results (expectations, energies)
        if isinstance(obj, (numbers.Real, list, tuple)):
            return True

        # Handle dict results (counts dict from qml.counts())
        if isinstance(obj, dict):
            # Empty dict - could be PennyLane (but also could be others, so be cautious)
            if len(obj) == 0:
                return False
            # Check if all values are numeric (counts dict)
            try:
                if all(isinstance(v, numbers.Real) for v in obj.values()):
                    return True
            except Exception:
                pass
            # Also match if dict has device info (PennyLane-specific)
            if any(key in obj for key in ["device_name", "device", "shots", "result_type"]):
                return True

        return False

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        qnode = _qnode(context)
        backend = _backend(obj, qnode)
        shot_vector = _shot_vector(qnode) if qnode is not None else None
        shots = 1
        histogram: Dict[str, int] = {}
        expectations: List[Optional[Dict[str, Any]]] = []
        probabilities = None
        batches: List[Dict[str, Any]] = []
        energy = None

        if _is_0d_object(obj):
            obj = obj.item()  # the Braket plugin returns qml.counts() as a 0-d object array holding the dict
        kind = _array_kind(obj)
        if _is_counts_dict(obj):
            # qml.counts()
            histogram = {str(k): int(v) for k, v in obj.items()}
            shots = sum(histogram.values()) or 1
        elif isinstance(obj, (list, tuple)) and obj and all(_is_counts_dict(g) for g in obj):
            # Several qml.counts() results: a shot vector (set_shots([100, 200])) or several measurements.
            groups = [{str(k): int(v) for k, v in g.items()} for g in obj]
            is_shot_vector = shot_vector is not None and len(shot_vector) == len(groups)
            label = (lambda i: f"shots={shot_vector[i]}") if is_shot_vector else (lambda i: f"measurement[{i}]")
            batches = [{"label": label(i), "shots": sum(h.values()), "histogram": h} for i, h in enumerate(groups)]
            if is_shot_vector:
                # Same circuit sampled in groups: the combined histogram is the run's histogram.
                histogram = merge_histograms(groups)
                shots = sum(histogram.values()) or 1
            else:
                shots = max(b["shots"] for b in batches) or 1
        elif isinstance(obj, (list, tuple)) or (kind == "f" and len(getattr(obj, "shape", ())) == 1
                                                 and probabilities_from_vector(obj) is None):
            # Several expectation values (a tuple), or one per shot-vector group / parameter set.
            values = list(obj)
            if shot_vector is not None and len(shot_vector) == len(values):
                expectations = [expectation(f"shots={s}", v) for s, v in zip(shot_vector, values)]
                shots = sum(shot_vector)
            else:
                expectations = [expectation(f"result[{i}]", v) for i, v in enumerate(values)]
        elif kind == "f" and len(obj.shape) == 1:
            # qml.probs(): one probability per basis state, wire 0 first
            probabilities = probabilities_from_vector(obj)
        elif kind in ("i", "u", "b") and len(obj.shape) in (1, 2):
            # qml.sample(): one row of 0/1 values per shot
            histogram = _samples_histogram(obj)
            shots = sum(histogram.values()) or 1
        else:
            energy = to_float(obj)

        if energy is not None:
            # A single expectation value (e.g. a VQE energy) is recorded as the run's energy, as before.
            artifacts: Dict[str, Any] = {"result_type": "energies", "energies": {"value": energy, "stderr": None}}
        else:
            artifacts = build_artifacts(histogram=histogram, expectations=expectations,
                                        probabilities=probabilities, batches=batches)
        exact = False
        if shots == 1 and qnode is not None:
            try:
                total = qnode.shots.total_shots
                if total:
                    shots = int(total)
                elif total is None and not histogram and not batches:
                    exact = True  # analytic mode (no shots): expectation values / probs are exact
            except Exception:
                pass

        out = {
            "sdk": {"name": "pennylane", "version": get_sdk_version("pennylane")},
            "backend": backend,
            "shots": shots,
            "artifacts": artifacts,
        }
        try:
            job = _plugin_job(getattr(qnode, "device", None)) if qnode is not None else None
            if job:
                out["execution"] = {"provider_job": job}
        except Exception:
            pass
        if context.cost_tracker is not None:  # tasks the Braket plugin created on AWS during the run
            try:
                from .braket_adapter import _tracked_cost
                cost = _tracked_cost(context.cost_tracker)
                if cost:
                    out["cost"] = cost
            except Exception:
                pass
        if exact:
            out["exact"] = True
        return out

from __future__ import annotations

from typing import Any, Dict, List, Optional
from .base import Adapter, AdapterContext
from .common import build_artifacts, expectation, probabilities_from_vector
from .version_utils import get_sdk_version

# Result types whose value is one number per observable.
_SCALAR_RESULT_TYPES = {"Expectation": "expectation", "Variance": "variance"}


def backend_from_device_id(device_id: Any) -> Optional[Dict[str, str]]:
    """
    Provider/name from a Braket result's task_metadata.deviceId.

    AWS devices are ARNs, e.g. arn:aws:braket:::device/quantum-simulator/amazon/sv1 (an AWS-managed,
    billed simulator) or arn:aws:braket:us-west-1::device/qpu/rigetti/Ankaa-3 (a QPU, labeled by its
    maker). The local simulators report plain ids such as "braket_sv" and "braket_dm".
    """
    if not isinstance(device_id, str) or not device_id:
        return None
    if not device_id.startswith("arn:"):
        return {"provider": "local_sim", "name": device_id}
    parts = device_id.split("/")
    name = parts[-1] or "unknown"
    if "/qpu/" in device_id and len(parts) >= 2 and parts[-2]:
        return {"provider": parts[-2].lower(), "name": name}
    return {"provider": "aws_braket", "name": name}


def _device_id(obj: Any) -> Optional[str]:
    metadata = getattr(obj, "task_metadata", None)
    if isinstance(metadata, dict):
        return metadata.get("deviceId") or metadata.get("deviceArn")
    return getattr(metadata, "deviceId", None)


def _observable_label(observable: Any, targets: Any) -> str:
    """['z', 'z'] on [0, 1] -> "Z0 Z1"; a Hermitian matrix is labeled "Hermitian"."""
    if isinstance(observable, str):
        observable = [observable]
    if not isinstance(observable, (list, tuple)):
        return str(observable)
    factors = [o.upper() if isinstance(o, str) else "Hermitian" for o in observable]
    targets = list(targets) if targets is not None else []
    if targets and len(targets) == len(factors):
        return " ".join(f"{f}{t}" for f, t in zip(factors, targets))
    return " ".join(factors) + (f" on {targets}" if targets else "")


def _result_type_values(obj: Any):
    """Expectation/variance values and probability vectors requested with circuit.expectation() etc."""
    expectations: List[Optional[Dict[str, Any]]] = []
    probabilities: Optional[Dict[str, float]] = None
    for item in getattr(obj, "result_types", None) or []:
        rt = getattr(item, "type", None)
        kind = type(rt).__name__
        value = getattr(item, "value", None)
        if kind in _SCALAR_RESULT_TYPES:
            label = _observable_label(getattr(rt, "observable", None), getattr(rt, "targets", None))
            expectations.append(expectation(label, value, kind=_SCALAR_RESULT_TYPES[kind]))
        elif kind == "Probability" and probabilities is None:
            probabilities = probabilities_from_vector(value)
    return expectations, probabilities


def _timeline(obj: Any) -> Optional[Dict[str, Any]]:
    """Task created/ended times from the result's task metadata (ISO 8601 strings from Braket)."""
    metadata = getattr(obj, "task_metadata", None)
    if metadata is None:
        return None
    get = metadata.get if isinstance(metadata, dict) else (lambda k: getattr(metadata, k, None))
    created, ended = get("createdAt"), get("endedAt")
    timeline = {k: v for k, v in (("created", created), ("finished", ended)) if isinstance(v, str) and v}
    if not timeline:
        return None
    timeline["source"] = "braket_task"
    return timeline


def _task_info(task_arn: Any, device_arn: Any = None, created: Any = None) -> Optional[Dict[str, Any]]:
    """
    The AWS quantum task (arn:aws:braket:<region>:<account>:quantum-task/<id>) as the provider job: its
    id, as the Braket console lists it, is the job id; the full ARN, region and device are kept with it.
    Local simulator tasks have plain ids and no AWS record, so they get none.
    """
    if not isinstance(task_arn, str) or not task_arn.startswith("arn:"):
        return None
    task_id = task_arn.rsplit("/", 1)[-1]
    info: Dict[str, Any] = {"job_id": task_id or task_arn, "provider": "aws_braket", "arn": task_arn}
    parts = task_arn.split(":")
    if len(parts) > 3 and parts[3]:
        info["region"] = parts[3]
    if isinstance(device_arn, str) and device_arn:
        info["device"] = device_arn
    if isinstance(created, str) and created:
        info["created"] = created
    return info


def provider_job_info(obj: Any) -> Optional[Dict[str, Any]]:
    """The task a finished Braket result came from (result.task_metadata.id is the task ARN)."""
    metadata = getattr(obj, "task_metadata", None)
    if metadata is None:
        return None
    get = metadata.get if isinstance(metadata, dict) else (lambda k: getattr(metadata, k, None))
    return _task_info(get("id"), get("deviceId") or get("deviceArn"), get("createdAt"))


def _is_aws_task(obj: Any) -> bool:
    return (type(obj).__module__ or "").startswith("braket.aws") and type(obj).__name__ == "AwsQuantumTask"


def _tracked_devices(tracker: Any) -> Dict[str, Any]:
    try:
        return dict(tracker.quantum_tasks_statistics() or {}) if tracker is not None else {}
    except Exception:
        return {}


# Tracker task states after which a simulator task's billed duration is known (or it is not billed).
_FINAL_TASK_STATES = {"COMPLETED", "FAILED", "CANCELLED"}


def _tracked_cost(tracker: Any) -> Optional[Dict[str, Any]]:
    """
    Estimated cost of the AWS tasks this run created, from braket.tracking.Tracker (Braket's own estimate,
    using the AWS Pricing API). Local simulator tasks are not tracked, so local runs record no cost.
    """
    if tracker is None:
        return None
    stats = tracker.quantum_tasks_statistics()
    if not stats:
        return None
    breakdown: Dict[str, Any] = {"tasks": _json_safe(stats)}
    # Simulators bill by duration, which the Tracker learns only when the task finishes; until then it
    # prices the task at $0. Record "not known yet" instead of a cost that looks real.
    unfinished = [arn for arn, s in stats.items() if "quantum-simulator" in str(arn)
                  and set((s or {}).get("tasks") or {}) - _FINAL_TASK_STATES]
    if unfinished:
        breakdown["error"] = "simulator task not finished: its billed duration and cost are known only after it completes"
        return {"currency": "USD", "estimated_cost": None, "cost_source": "braket_tracker",
                "provider_cost_breakdown": breakdown}
    try:
        qpu = float(tracker.qpu_tasks_cost())
        sim = float(tracker.simulator_tasks_cost())
    except Exception as e:  # pricing lookups need network access and pricing:GetProducts permission
        breakdown["error"] = f"{type(e).__name__}: cost estimate unavailable"
        return {"currency": "USD", "estimated_cost": None, "cost_source": "braket_tracker",
                "provider_cost_breakdown": breakdown}
    breakdown.update({"qpu_usd": qpu, "simulator_usd": sim})
    return {"currency": "USD", "estimated_cost": round(qpu + sim, 6), "cost_source": "braket_tracker",
            "provider_cost_breakdown": breakdown}


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    try:
        return float(value)  # Decimal
    except (TypeError, ValueError):
        return str(value)


class BraketAdapter(Adapter):
    name = "braket"
    priority = 80

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return (
            "braket" in obj.__class__.__module__
            or hasattr(obj, "measurement_counts")
            or (isinstance(obj, dict) and obj.get("provider") == "aws_braket")
        )

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        histogram = {}
        if hasattr(obj, "measurement_counts"):
            try:
                histogram = {str(k): int(v) for k, v in dict(obj.measurement_counts).items()}
            except Exception:
                histogram = {}
        if not histogram and isinstance(obj, dict) and "counts" in obj:
            histogram = {str(k): int(v) for k, v in obj["counts"].items()}

        expectations: List[Optional[Dict[str, Any]]] = []
        probabilities = None
        try:
            expectations, probabilities = _result_type_values(obj)
        except Exception:
            pass

        shots = sum(histogram.values()) or 1
        exact = False
        if not histogram:
            try:
                metadata = getattr(obj, "task_metadata", None)
                exact = getattr(metadata, "shots", None) == 0  # Braket's shots=0: exact results
            except Exception:
                pass

        # Backend: the result's task metadata names the device that ran the task.
        backend = None
        try:
            backend = backend_from_device_id(_device_id(obj))
        except Exception:
            pass

        pending_task = _is_aws_task(obj)
        if backend is None and pending_task:
            # A task returned before it finished: the Tracker saw which device it was created on.
            devices = list(_tracked_devices(context.cost_tracker))
            if len(devices) == 1:
                backend = backend_from_device_id(devices[0])
            else:  # e.g. a task loaded by ARN: an AWS task, but its device is not known locally
                backend = {"provider": "aws_braket", "name": "unknown"}

        if backend is None and hasattr(obj, "device"):
            try:
                device = obj.device
                name = str(getattr(device, "name", None) or getattr(device, "id", None) or device)
                lowered = name.lower()
                provider = "local_sim" if ("local" in lowered or "simulator" in lowered) else "aws_braket"
                backend = {"provider": provider, "name": name}
            except Exception:
                pass

        if backend is None:
            # No device information: results from the LocalSimulator (the common case) carry none.
            backend = {"provider": "local_sim", "name": "LocalSimulator"}
        elif backend == {"provider": "local_sim", "name": "braket_sv"}:
            # Keep the label users already see for the default LocalSimulator; other local
            # simulators (braket_dm, braket_ahs) keep their own ids.
            backend = {"provider": "local_sim", "name": "LocalSimulator"}

        out: Dict[str, Any] = {
            "sdk": {"name": "braket", "version": get_sdk_version("braket")},
            "backend": backend,
            "shots": shots,
            "artifacts": build_artifacts(histogram=histogram, expectations=expectations,
                                         probabilities=probabilities),
        }
        execution: Dict[str, Any] = {}
        try:
            timeline = _timeline(obj)
            if timeline:
                execution["timeline"] = timeline
        except Exception:
            pass
        try:
            if pending_task:
                devices = list(_tracked_devices(context.cost_tracker))
                job = _task_info(obj.id, devices[0] if len(devices) == 1 else None)
            else:
                job = provider_job_info(obj)
            if job:
                execution["provider_job"] = job
        except Exception:
            pass
        if execution:
            out["execution"] = execution
        if exact:
            out["exact"] = True
        try:
            cost = _tracked_cost(context.cost_tracker)
            if cost:
                out["cost"] = cost
        except Exception:
            pass
        return out

from __future__ import annotations

import numbers
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from .base import Adapter, AdapterContext
from .common import build_artifacts, expectation, to_float
from .version_utils import get_sdk_version


def _cirq_timing_to_resource_usage(obj: Any) -> Optional[Dict[str, Any]]:
    """
    Extract execution timing from Cirq result when available.
    - RuntimeInfo.timings_s: dict of subroutine durations (seconds) -> cpu_time_s + stages
    - ExecutionStatus.Timing: started_time, completed_time -> qpu_time_s (execution duration)
    """
    out = {}
    stages = {}

    # RuntimeInfo.timings_s (e.g. from workflow ExecutableResult)
    timings_s = getattr(obj, "timings_s", None)
    if isinstance(timings_s, dict) and timings_s:
        stages["timings_s"] = {k: float(v) for k, v in timings_s.items() if isinstance(v, numbers.Real)}
        try:
            total = sum(float(v) for v in timings_s.values() if isinstance(v, numbers.Real))
            if total > 0:
                out["cpu_time_s"] = round(total, 3)
        except (TypeError, ValueError):
            pass

    # ExecutionStatus.Timing: started_time, completed_time (Google Quantum Engine)
    for attr in ("execution_status", "_execution_status"):
        est = getattr(obj, attr, None)
        if est is None:
            continue
        timing = getattr(est, "timing", None)
        if timing is None:
            continue
        started = getattr(timing, "started_time", None)
        completed = getattr(timing, "completed_time", None)
        if started is not None and completed is not None:
            try:
                # Protobuf Timestamp often has ToDatetime() or seconds/nanos
                if hasattr(started, "ToDatetime"):
                    start_dt = started.ToDatetime()
                elif hasattr(started, "seconds"):
                    from datetime import datetime, timezone
                    start_dt = datetime.fromtimestamp(float(started.seconds) + float(getattr(started, "nanos", 0)) / 1e9, tz=timezone.utc)
                else:
                    start_dt = started
                if hasattr(completed, "ToDatetime"):
                    end_dt = completed.ToDatetime()
                elif hasattr(completed, "seconds"):
                    from datetime import datetime, timezone
                    end_dt = datetime.fromtimestamp(float(completed.seconds) + float(getattr(completed, "nanos", 0)) / 1e9, tz=timezone.utc)
                else:
                    end_dt = completed
                delta = (end_dt - start_dt).total_seconds()
                if delta >= 0:
                    out["qpu_time_s"] = round(delta, 3)
                    stages["execution_status_timing"] = {"started": str(start_dt), "completed": str(end_dt)}
            except Exception:
                pass
            break

    if not out:
        return None
    if stages:
        out["stages"] = stages
    return out


def _is_result(obj: Any) -> bool:
    return hasattr(obj, "histogram") and callable(getattr(obj, "histogram")) and hasattr(obj, "measurements")


def _result_histogram(result: Any, key: Optional[str]) -> Dict[str, int]:
    """
    Counts from a cirq.Result. Uses measurement_key when given; with no key and a single
    measurement in the circuit, that measurement is used (so measurement_key= is optional).
    """
    measurements = getattr(result, "measurements", None)
    if not isinstance(measurements, dict) or not measurements:
        return {}
    if key is None or key not in measurements:
        if key is not None or len(measurements) != 1:
            return {}
        key = next(iter(measurements))
    histogram: Dict[str, int] = {}
    # Pad to the number of measured qubits so e.g. |00> is "00", not "0".
    shape = getattr(measurements[key], "shape", None)
    width = int(shape[1]) if shape and len(shape) == 2 else 1
    for intval, cnt in dict(result.histogram(key=key)).items():
        histogram[format(int(intval), f"0{width}b")] = int(cnt)
    return histogram


def _params(result: Any) -> Dict[str, Any]:
    """Sweep parameter values of one sweep point, e.g. {"t": 0.5}."""
    resolver = getattr(result, "params", None)
    param_dict = getattr(resolver, "param_dict", None) or {}
    out: Dict[str, Any] = {}
    for name, value in param_dict.items():
        v = to_float(value)
        out[str(name)] = v if v is not None else str(value)
    return out


def _flatten_results(obj: Any) -> List[Any]:
    """run_sweep returns [Result, ...]; run_batch returns [[Result, ...], ...]."""
    flat: List[Any] = []
    for item in obj:
        if isinstance(item, (list, tuple)):
            flat.extend(_flatten_results(item))
        elif _is_result(item):
            flat.append(item)
        else:
            return []
    return flat


def _expectation_values(obj: Any) -> List[Optional[Dict[str, Any]]]:
    """
    simulate_expectation_values returns one (complex) value per observable; the sweep variant
    returns one such list per sweep point.
    """
    if obj and all(isinstance(v, (list, tuple)) for v in obj):
        return [expectation(f"point{p}[{i}]", v) for p, row in enumerate(obj) for i, v in enumerate(row)]
    return [expectation(f"obs[{i}]", v) for i, v in enumerate(obj)]


# Job ids made by cirq_google's local processors (the Quantum Virtual Machine): projects/<p>/processors/<id>/job/<n>
_LOCAL_ENGINE_JOB_ID = re.compile(r"^projects/[^/]+/processors/([^/]+)/job/[^/]+$")


def _iso(value: Any, naive_is_local: bool) -> Optional[str]:
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        # Local (virtual) jobs stamp datetime.now(), i.e. local time; otherwise assume UTC.
        value = value.astimezone() if naive_is_local else value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _processor_id(hint: Any) -> Optional[str]:
    """backend= given as a cirq_google processor or ProcessorSampler."""
    processor = getattr(hint, "processor", hint)  # ProcessorSampler.processor is a property
    pid = getattr(processor, "processor_id", None)
    return pid if isinstance(pid, str) and pid else None


def engine_job_info(job: Any, result: Any, backend_hint: Any = None) -> Optional[Dict[str, Any]]:
    """
    Google Quantum Engine job details (cirq_google). A real EngineJob and a Quantum Virtual Machine
    SimulatedLocalJob share the AbstractJob API (id, processor_ids, create/update time, status, program,
    calibration); for processor.get_sampler().run(...) only the EngineResult's job_id is available.
    "virtual" marks local simulation of the processor with its published noise model.
    """
    info: Dict[str, Any] = {"provider": "google"}
    if job is not None and (type(job).__module__ or "").startswith("cirq_google.engine"):
        from cirq_google.engine.abstract_local_job import AbstractLocalJob
        virtual = isinstance(job, AbstractLocalJob)
        info["job_id"] = str(job.id())
        info["virtual"] = virtual
        for key, get in (
            ("processor", lambda: (list(job.processor_ids()) or [None])[0]),
            ("program_id", lambda: job.program().id()),
            ("status", lambda: getattr(job.execution_status(), "name", None)),
            ("created", lambda: _iso(job.create_time(), virtual)),
            ("updated", lambda: _iso(job.update_time(), virtual)),
            # Calibration.timestamp is in ms; for the virtual machine it is the calibration its noise model uses
            ("calibration", lambda: _iso(datetime.fromtimestamp(job.get_calibration().timestamp / 1000, tz=timezone.utc), False)),
        ):
            try:
                value = get()
                if value not in (None, ""):
                    info[key] = str(value)
            except Exception:
                pass
    else:
        job_id = getattr(result, "job_id", None) if type(result).__name__ == "EngineResult" else None
        if not isinstance(job_id, str) or not job_id:
            return None
        info["job_id"] = job_id
        match = _LOCAL_ENGINE_JOB_ID.match(job_id)
        info["virtual"] = bool(match)
        if match:
            info["processor"] = match.group(1)
    if "processor" not in info:
        pid = _processor_id(backend_hint)
        if pid:
            info["processor"] = pid
    return info


def engine_backend(info: Dict[str, Any]) -> Dict[str, str]:
    processor = info.get("processor") or "unknown"
    if info.get("virtual"):
        return {"provider": "local_sim", "name": f"{processor} (virtual)"}
    return {"provider": "google", "name": processor}


class CirqAdapter(Adapter):
    name = "cirq"
    priority = 70

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        if obj.__class__.__module__.startswith("cirq") or hasattr(obj, "histogram"):
            return True
        # Lists from run_sweep/run_batch/simulate_expectation_values are plain Python lists.
        return isinstance(obj, (list, tuple)) and (context.tags or {}).get("sdk", "").lower() == "cirq"

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        histogram: Dict[str, int] = {}
        expectations: List[Optional[Dict[str, Any]]] = []
        batches: List[Dict[str, Any]] = []
        key = context.measurement_key
        shots = 1
        if isinstance(obj, (list, tuple)) and len(obj) == 1 and _is_result(obj[0]):
            obj = obj[0]  # an Engine job's results() for a single circuit / sweep point
        first = obj

        if _is_result(obj):
            try:
                histogram = _result_histogram(obj, key)
            except Exception:
                pass
        elif isinstance(obj, (list, tuple)) and obj:
            results = _flatten_results(obj)
            if results:
                first = results[0]
                for r in results:
                    try:
                        h = _result_histogram(r, key)
                    except Exception:
                        h = {}
                    batches.append({"params": _params(r), "shots": sum(h.values()), "histogram": h})
                shots = sum(b["shots"] for b in batches) or 1
            else:
                expectations = _expectation_values(obj)  # simulate_expectation_values: exact
        if not histogram and isinstance(obj, dict) and "counts" in obj:
            histogram = {str(k): int(v) for k, v in obj["counts"].items()}

        if histogram:
            shots = sum(histogram.values()) or 1
        obj = first  # backend details below come from the (first) result object

        # Extract backend info from result object
        backend_name = None
        provider = "local_sim"  # Default to local simulation
        
        # Method 1: Check if result has device information (for real devices)
        if hasattr(obj, "device"):
            try:
                device = obj.device
                if hasattr(device, "name"):
                    backend_name = str(device.name)
                elif hasattr(device, "__str__"):
                    backend_name = str(device)
                
                # Determine provider from device
                if backend_name:
                    device_str = backend_name.lower()
                    # Check for Google devices
                    if "google" in device_str or "sycamore" in device_str or "weber" in device_str:
                        provider = "google"
                    # Check for IonQ devices
                    elif "ionq" in device_str:
                        provider = "ionq"
                    # Check for other real device indicators
                    elif any(indicator in device_str for indicator in ["qpu", "processor", "device"]):
                        # If it's not clearly a simulator, might be a real device
                        # Default to google for Cirq real devices (most common)
                        if "simulator" not in device_str:
                            provider = "google"
            except Exception:
                pass
        
        # Method 2: Check if result has simulator information (for simulators)
        if not backend_name and hasattr(obj, "simulator"):
            try:
                sim = obj.simulator
                if hasattr(sim, "__class__"):
                    class_name = sim.__class__.__name__
                    # Extract meaningful name (e.g., "Simulator" -> "cirq-simulator")
                    if "simulator" in class_name.lower():
                        backend_name = class_name
                    else:
                        backend_name = f"{class_name}-simulator"
            except Exception:
                pass
        
        # Method 3: Check result class name
        if not backend_name:
            try:
                class_name = obj.__class__.__name__
                module_name = obj.__class__.__module__
                # Check if it's a specific simulator type
                if "simulator" in class_name.lower() or "simulator" in module_name.lower():
                    backend_name = class_name
                else:
                    # Default to generic cirq simulator
                    backend_name = "Simulator"
            except Exception:
                pass
        
        # Fallback only if we truly can't determine
        if not backend_name:
            backend_name = "cirq-simulator"

        # Google Quantum Engine (real processors and the Quantum Virtual Machine): label by processor.
        engine = None
        try:
            engine = engine_job_info(context.job, obj, context.backend_hint)
        except Exception:
            pass
        if engine:
            backend = engine_backend(engine)
            provider, backend_name = backend["provider"], backend["name"]

        # Execution time breakdown when available (EngineResult, ExecutableResult, etc.)
        resource_usage = _cirq_timing_to_resource_usage(obj)

        out = {
            "sdk": {"name": "cirq", "version": get_sdk_version("cirq")},
            "backend": {"provider": provider, "name": backend_name},
            "shots": shots,
            "artifacts": build_artifacts(histogram=histogram, expectations=expectations, batches=batches),
        }
        execution: Dict[str, Any] = {}
        if resource_usage:
            execution["resource_usage"] = resource_usage
        if engine:
            execution["provider_job"] = engine
        if execution:
            out["execution"] = execution
        if expectations and not histogram and not batches:
            out["exact"] = True  # simulate_expectation_values takes no samples
        return out

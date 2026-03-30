from __future__ import annotations

from typing import Any, Dict, Optional
from .base import Adapter, AdapterContext
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
        stages["timings_s"] = {k: float(v) for k, v in timings_s.items() if isinstance(v, (int, float))}
        try:
            total = sum(float(v) for v in timings_s.values() if isinstance(v, (int, float)))
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


class CirqAdapter(Adapter):
    name = "cirq"
    priority = 70

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return obj.__class__.__module__.startswith("cirq") or hasattr(obj, "histogram")

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        histogram = {}
        key = context.measurement_key
        if hasattr(obj, "histogram") and callable(getattr(obj, "histogram")) and key:
            try:
                h = obj.histogram(key=key)
                for intval, cnt in dict(h).items():
                    histogram[format(int(intval), "b")] = int(cnt)
            except Exception:
                pass
        if not histogram and isinstance(obj, dict) and "counts" in obj:
            histogram = {str(k): int(v) for k, v in obj["counts"].items()}

        shots = sum(histogram.values()) or 1

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

        # Execution time breakdown when available (EngineResult, ExecutableResult, etc.)
        resource_usage = _cirq_timing_to_resource_usage(obj)

        out = {
            "sdk": {"name": "cirq", "version": get_sdk_version("cirq")},
            "backend": {"provider": provider, "name": backend_name},
            "shots": shots,
            "artifacts": {"result_type": "counts", "counts": {"bit_order": "little", "histogram": histogram, "mapping": {}}},
        }
        if resource_usage:
            out["execution"] = {"resource_usage": resource_usage}
        return out

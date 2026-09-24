from __future__ import annotations

from typing import Any, Dict, Optional
from .base import Adapter, AdapterContext
from .version_utils import get_sdk_version


def _normalize_ibm_resource_usage(raw: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Normalize IBM job.result()['metadata']['resource_usage'] into common fields.
    Example IBM shape: {'RUNNING: OPTIMIZING_FOR_HARDWARE': {'CPU_TIME': 0.91},
                       'RUNNING: WAITING_FOR_QPU': {'CPU_TIME': 18.8},
                       'RUNNING: POST_PROCESSING': {'CPU_TIME': 10.43},
                       'RUNNING: EXECUTING_QPU': {'QPU_TIME': 159.0}}
    """
    if not raw or not isinstance(raw, dict):
        return None
    cpu_time_s = 0.0
    qpu_time_s = None
    queue_time_s = None
    post_processing_time_s = None
    for stage_name, stage_data in raw.items():
        if not isinstance(stage_data, dict):
            continue
        stage_name_upper = str(stage_name).upper()
        cpu_val = stage_data.get("CPU_TIME")
        qpu_val = stage_data.get("QPU_TIME")
        if cpu_val is not None:
            try:
                cpu_time_s += float(cpu_val)
            except (TypeError, ValueError):
                pass
        if qpu_val is not None:
            try:
                qpu_time_s = float(qpu_val)
            except (TypeError, ValueError):
                pass
        if "WAITING_FOR_QPU" in stage_name_upper or "QUEUE" in stage_name_upper:
            if cpu_val is not None:
                try:
                    queue_time_s = float(cpu_val)
                except (TypeError, ValueError):
                    pass
        if "POST_PROCESSING" in stage_name_upper:
            if cpu_val is not None:
                try:
                    post_processing_time_s = float(cpu_val)
                except (TypeError, ValueError):
                    pass
    out = {"stages": raw}
    if cpu_time_s > 0:
        out["cpu_time_s"] = round(cpu_time_s, 3)
    if qpu_time_s is not None:
        out["qpu_time_s"] = round(qpu_time_s, 3)
    if queue_time_s is not None:
        out["queue_time_s"] = round(queue_time_s, 3)
    if post_processing_time_s is not None:
        out["post_processing_time_s"] = round(post_processing_time_s, 3)
    if len(out) <= 1:
        return None
    return out


def _get_resource_usage_from_result(obj: Any) -> Optional[Dict[str, Any]]:
    """Try to get resource_usage from IBM-style result (job.result() metadata)."""
    metadata = None
    if isinstance(obj, dict):
        metadata = obj.get("metadata")
    elif hasattr(obj, "metadata"):
        metadata = getattr(obj, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    raw = metadata.get("resource_usage")
    return _normalize_ibm_resource_usage(raw) if raw else None


def _backend_name(backend: Any) -> Optional[str]:
    name = getattr(backend, "name", None)
    if callable(name):  # BackendV1 exposes name() as a method
        try:
            name = name()
        except Exception:
            name = None
    return str(name) if name else None


def describe_backend(backend: Any) -> Optional[Dict[str, str]]:
    """
    Provider/name for a Qiskit backend object, classified by the package it comes from.

    Local simulators (Aer, qiskit fake backends, qiskit-ibm-runtime fake backends that
    simulate IBM devices locally) are reported as local_sim; only real IBM backends
    are reported as ibm.
    """
    if backend is None:
        return None
    name = _backend_name(backend)
    if not name:
        return None
    module = type(backend).__module__ or ""
    if module.startswith(("qiskit_aer", "qiskit.providers.fake_provider", "qiskit_ibm_runtime.fake_provider",
                          "qiskit.providers.basic_provider")):
        provider = "local_sim"
    elif module.startswith(("qiskit_ibm_runtime", "qiskit_ibm_provider")):
        provider = "ibm"
    else:
        # Third-party provider plugins, e.g. qiskit_ionq -> "ionq", qiskit_braket_provider -> "braket"
        root = module.split(".")[0]
        provider = root.removeprefix("qiskit_").removesuffix("_provider") or "unknown"
    return {"provider": provider, "name": name}


def _job_backend(job: Any) -> Any:
    if job is None or not hasattr(job, "backend"):
        return None
    backend = getattr(job, "backend", None)
    if callable(backend) and not hasattr(backend, "name"):  # RuntimeJobV2.backend() is a method
        try:
            backend = backend()
        except Exception:
            return None
    return backend


def _backend_from_result(obj: Any) -> Optional[Dict[str, str]]:
    """Backend details that the result object itself carries (it often carries none)."""
    # Legacy qiskit.result.Result (e.g. AerSimulator.run(...).result()) records backend_name.
    backend_name = getattr(obj, "backend_name", None)
    if isinstance(backend_name, str) and backend_name:
        lowered = backend_name.lower()
        if "simulator" in lowered or lowered.startswith(("aer", "fake", "statevector", "basic")):
            provider = "local_sim"
        elif lowered.startswith("ibm_"):
            provider = "ibm"
        else:
            provider = "unknown"
        return {"provider": provider, "name": backend_name}
    # V2 PrimitiveResult from Aer's SamplerV2 includes simulator metadata on each pub result.
    if obj.__class__.__name__ == "PrimitiveResult":
        try:
            if len(obj) > 0 and isinstance(getattr(obj[0], "metadata", None), dict) \
                    and "simulator_metadata" in obj[0].metadata:
                return {"provider": "local_sim", "name": "aer_simulator"}
        except Exception:
            pass
    return None


class QiskitAdapter(Adapter):
    name = "qiskit"
    priority = 90

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        # Handle Qiskit objects (old and new formats)
        if obj.__class__.__module__.startswith("qiskit"):
            return True
        # Handle objects with get_counts() method (old format)
        if hasattr(obj, "get_counts"):
            return True
        # Handle dict with counts
        if isinstance(obj, dict) and "counts" in obj:
            return True
        return False

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        counts = None
        shots = 1
        backend_name = "unknown"
        provider = "unknown"
        
        # Handle modern Qiskit 2.x PrimitiveResult format
        if hasattr(obj, "__class__") and obj.__class__.__name__ == "PrimitiveResult":
            try:
                # PrimitiveResult is indexable, get first pub result
                if len(obj) > 0:
                    pub_result = obj[0]
                    if hasattr(pub_result, "data"):
                        data = pub_result.data
                        # Access meas (measurement) or c (classical) via getattr
                        # Prefer meas for measurement counts, fall back to c
                        meas = getattr(data, "meas", None)
                        if meas is not None and hasattr(meas, "get_counts"):
                            counts = meas.get_counts()
                        elif meas is None:
                            # Try c field if meas not available
                            c = getattr(data, "c", None)
                            if c is not None and hasattr(c, "get_counts"):
                                counts = c.get_counts()
                        if counts is None and hasattr(data, "keys"):
                            # Custom classical register names (e.g. ClassicalRegister(2, "cr"))
                            for field_name in data.keys():
                                reg = getattr(data, field_name, None)
                                if reg is not None and hasattr(reg, "get_counts"):
                                    counts = reg.get_counts()
                                    break
                        # Get shots from metadata
                        if hasattr(pub_result, "metadata") and isinstance(pub_result.metadata, dict):
                            shots = pub_result.metadata.get("shots", 1)
            except Exception:
                pass
        
        # Handle old Qiskit format with get_counts() method
        if counts is None and hasattr(obj, "get_counts"):
            try:
                counts = obj.get_counts()
                # Try to get shots from result object
                if hasattr(obj, "results") and len(obj.results) > 0:
                    first_result = obj.results[0]
                    if hasattr(first_result, "shots"):
                        shots = first_result.shots
            except Exception:
                pass
        
        # Handle dict format
        if counts is None and isinstance(obj, dict):
            counts = obj.get("counts")
            shots = obj.get("shots", 1)

        # Execution time breakdown (e.g. IBM job.result()['metadata']['resource_usage'])
        resource_usage = _get_resource_usage_from_result(obj)
        execution_extra = {"resource_usage": resource_usage} if resource_usage else {}

        # Backend: only report what the objects actually tell us. V2 PrimitiveResults carry no
        # backend information, so without a job or an explicit backend= the answer is "unknown".
        backend_info = (
            describe_backend(context.backend_hint)
            or describe_backend(_job_backend(context.job))
            or describe_backend(getattr(obj, "backend", None))
            or _backend_from_result(obj)
        )
        if backend_info is None and isinstance(obj, dict):
            if obj.get("backend") or obj.get("provider"):
                backend_info = {"provider": str(obj.get("provider") or "unknown"),
                                "name": str(obj.get("backend") or "unknown")}
        if backend_info:
            provider, backend_name = backend_info["provider"], backend_info["name"]

        # Convert counts to histogram format
        histogram = {}
        if isinstance(counts, dict):
            histogram = {str(k): int(v) for k, v in counts.items()}
            if shots == 1:
                shots = sum(histogram.values()) or 1
        elif counts is None:
            histogram = {}

        out = {
            "sdk": {"name": "qiskit", "version": get_sdk_version("qiskit")},
            "backend": {"provider": provider, "name": backend_name},
            "shots": shots,
            "artifacts": {"result_type": "counts", "counts": {"bit_order": "little", "histogram": histogram, "mapping": {}}},
        }
        if execution_extra:
            out["execution"] = execution_extra
        return out

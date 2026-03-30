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
        backend_name = "qiskit-backend"
        provider = "ibm"
        
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

        # Try to extract backend info if available
        if hasattr(obj, "backend"):
            backend_obj = obj.backend
            if hasattr(backend_obj, "name"):
                backend_name = str(backend_obj.name)
            if hasattr(backend_obj, "provider"):
                provider_obj = backend_obj.provider
                if hasattr(provider_obj, "name"):
                    provider = str(provider_obj.name).lower()
                elif "ibm" in str(provider_obj).lower():
                    provider = "ibm"
                elif "local" in str(provider_obj).lower() or "simulator" in str(backend_name).lower():
                    provider = "local_sim"
        
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

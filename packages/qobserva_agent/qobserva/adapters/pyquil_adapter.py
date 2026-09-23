from __future__ import annotations

from typing import Any, Dict, Optional
from .base import Adapter, AdapterContext
from .version_utils import get_sdk_version


def _histogram_from_rows(rows: Any) -> Dict[str, int]:
    histogram: Dict[str, int] = {}
    for s in rows:
        if hasattr(s, "tolist"):
            s = s.tolist()
        key = "".join(map(str, s)) if isinstance(s, (list, tuple)) else str(s)
        histogram[key] = histogram.get(key, 0) + 1
    return histogram


def _register_rows(result: Any, measurement_key: Optional[str]) -> Any:
    """Per-shot readout rows from a pyQuil 4 QAMExecutionResult (shots x bits)."""
    register_map = result.get_register_map()
    if not register_map:
        return []
    key = measurement_key if measurement_key in register_map else ("ro" if "ro" in register_map else next(iter(register_map)))
    rows = register_map.get(key)
    return [] if rows is None else rows


def _backend_from_result(result: Any) -> Optional[Dict[str, str]]:
    try:
        result_data = result.data.result_data
        if result_data.is_qvm():
            return {"provider": "local_sim", "name": "qvm"}
        if result_data.is_qpu():
            return {"provider": "rigetti", "name": "unknown"}
    except Exception:
        pass
    return None


def _backend_from_quantum_computer(qc: Any) -> Optional[Dict[str, str]]:
    """Classify a pyquil QuantumComputer passed as @observe_run(backend=qc)."""
    name = getattr(qc, "name", None)
    qam = getattr(qc, "qam", None)
    if not name or qam is None:
        return None
    qam_type = type(qam).__name__
    provider = "local_sim" if qam_type == "QVM" else "rigetti" if qam_type == "QPU" else "unknown"
    return {"provider": provider, "name": str(name)}


class PyQuilAdapter(Adapter):
    name = "pyquil"
    priority = 50

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return "pyquil" in obj.__class__.__module__ or isinstance(obj, (list, tuple))

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        backend: Optional[Dict[str, str]] = None
        if hasattr(obj, "get_register_map"):
            # pyQuil 4: qc.run(...) returns a QAMExecutionResult
            histogram = _histogram_from_rows(_register_rows(obj, context.measurement_key))
            backend = _backend_from_result(obj)
        elif isinstance(obj, (list, tuple)):
            # A list of per-shot bitstrings returned by the user's function
            histogram = _histogram_from_rows(obj)
        else:
            histogram = {}
        shots = sum(histogram.values()) or 1

        hinted = _backend_from_quantum_computer(context.backend_hint)
        if hinted:
            backend = hinted

        return {
            "sdk": {"name": "pyquil", "version": get_sdk_version("pyquil")},
            "backend": backend or {"provider": "unknown", "name": "unknown"},
            "shots": shots,
            "artifacts": {"result_type": "counts", "counts": {"bit_order": "little", "histogram": histogram, "mapping": {}}},
        }

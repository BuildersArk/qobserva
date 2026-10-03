"""Artifact builders shared by the SDK adapters, so every SDK records the same shapes."""

from __future__ import annotations

import numbers
from typing import Any, Dict, Iterable, List, Optional

# Upper bound on stored entries per artifact (probabilities, batches, expectations), so a
# 20-qubit statevector or a 10,000-point sweep cannot turn one run event into megabytes.
MAX_ENTRIES = 4096
# Probabilities below this are dropped: they are numerical noise from simulators.
_PROB_EPSILON = 1e-12

def to_float(value: Any) -> Optional[float]:
    """A real number from Python/numpy scalars and 0-d arrays; None for anything else."""
    if isinstance(value, bool):
        return None
    if isinstance(value, numbers.Real):
        return float(value)
    if isinstance(value, numbers.Complex):
        return float(value.real)
    if getattr(value, "shape", None) == () and hasattr(value, "item"):
        return to_float(value.item())
    return None

def expectation(operator: str, value: Any, stderr: Any = None, kind: str = "expectation") -> Optional[Dict[str, Any]]:
    v = to_float(value)
    if v is None:
        return None
    return {"operator": str(operator), "value": v, "stderr": to_float(stderr), "kind": kind}

def counts_artifact(histogram: Dict[str, int]) -> Dict[str, Any]:
    return {"bit_order": "little", "histogram": histogram, "mapping": {}}

def probabilities_artifact(values: Dict[str, float]) -> Dict[str, Any]:
    kept = {k: float(p) for k, p in values.items() if float(p) > _PROB_EPSILON}
    out: Dict[str, Any] = {}
    if len(kept) > MAX_ENTRIES:
        kept = dict(sorted(kept.items(), key=lambda kv: -kv[1])[:MAX_ENTRIES])
        out["truncated"] = True
    out["values"] = kept
    return out

def probabilities_from_vector(vector: Any) -> Optional[Dict[str, float]]:
    """Index-ordered probability vector (length 2**n) -> {bitstring: p}; None if it is not one."""
    try:
        probs = [float(p) for p in vector]
    except (TypeError, ValueError):
        return None
    n = len(probs).bit_length() - 1
    if len(probs) < 2 or len(probs) != 2 ** n:
        return None
    if any(p < -1e-9 or p > 1 + 1e-9 for p in probs) or abs(sum(probs) - 1.0) > 1e-6:
        return None
    return {format(i, f"0{n}b"): p for i, p in enumerate(probs)}

def histogram_from_bit_rows(rows: Iterable[Any]) -> Dict[str, int]:
    """Per-shot rows of 0/1 values (lists or numpy rows) -> {bitstring: count}."""
    histogram: Dict[str, int] = {}
    for row in rows:
        if hasattr(row, "tolist"):
            row = row.tolist()
        key = "".join(str(int(b)) for b in row) if isinstance(row, (list, tuple)) else str(int(row))
        histogram[key] = histogram.get(key, 0) + 1
    return histogram

def merge_histograms(histograms: Iterable[Dict[str, int]]) -> Dict[str, int]:
    merged: Dict[str, int] = {}
    for h in histograms:
        for k, v in h.items():
            merged[k] = merged.get(k, 0) + int(v)
    return merged

def cap(items: List[Any]) -> List[Any]:
    return items[:MAX_ENTRIES]

def has_result_data(artifacts: Dict[str, Any]) -> bool:
    """True when the artifacts hold at least one actual result value."""
    if not isinstance(artifacts, dict):
        return False
    counts = artifacts.get("counts")
    if isinstance(counts, dict) and counts.get("histogram"):
        return True
    if artifacts.get("expectations"):
        return True
    energies = artifacts.get("energies")
    if isinstance(energies, dict) and energies.get("value") is not None:
        return True
    probabilities = artifacts.get("probabilities")
    if isinstance(probabilities, dict) and probabilities.get("values"):
        return True
    if artifacts.get("batches"):
        return True
    samples = artifacts.get("samples")
    return bool(samples)

def build_artifacts(histogram: Optional[Dict[str, int]] = None,
                    expectations: Optional[List[Optional[Dict[str, Any]]]] = None,
                    probabilities: Optional[Dict[str, float]] = None,
                    batches: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """
    Artifacts with the primary result_type first: counts, then expectations, then probabilities.
    A batch (sweep, shot vector, program set) is "batch" unless it also has combined counts.
    """
    art: Dict[str, Any] = {}
    exps = [e for e in (expectations or []) if e is not None]
    if histogram:
        art["counts"] = counts_artifact(histogram)
    if exps:
        art["expectations"] = cap(exps)
    if probabilities:
        art["probabilities"] = probabilities_artifact(probabilities)
    if batches:
        art["batches"] = cap(batches)
    if histogram:
        result_type = "counts"
    elif exps:
        result_type = "expectations"
    elif probabilities:
        result_type = "probabilities"
    elif batches:
        result_type = "batch"
    else:
        result_type = "unknown"
    return {"result_type": result_type, **art}

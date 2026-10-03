from __future__ import annotations

from typing import Any, Dict, Optional
from .base import Adapter, AdapterContext
from .version_utils import get_sdk_version


# D-Wave cloud timing fields (microseconds) -> resource_usage fields (seconds).
# QPU: sampleset.info["timing"] (https://docs.dwavequantum.com/en/latest/quantum_research/operation_timing.html).
# Leap hybrid BQM/CQM/DQM: qpu_access_time, charge_time, run_time at the top level of sampleset.info;
# the nonlinear (Stride) solver nests them under info["timing"] (dwave-system StrideHybridSolver).
_DWAVE_TIMING_FIELDS = (
    ("qpu_access_time", "qpu_time_s"),
    ("total_post_processing_time", "post_processing_time_s"),
    ("qpu_programming_time", "qpu_programming_time_s"),
    ("qpu_sampling_time", "qpu_sampling_time_s"),
    ("charge_time", "charge_time_s"),
    ("run_time", "run_time_s"),
)


def _dwave_timing_to_resource_usage(timing: Any, info: Any = None) -> Optional[Dict[str, Any]]:
    """Map D-Wave cloud timing (microseconds) from info["timing"] or the hybrid top-level fields to seconds."""
    raw: Dict[str, Any] = {}
    if isinstance(timing, dict):
        raw.update(timing)
    if isinstance(info, dict):
        for key, _ in _DWAVE_TIMING_FIELDS:
            if key in info and key not in raw:
                raw[key] = info[key]
    out: Dict[str, Any] = {}
    for key, field in _DWAVE_TIMING_FIELDS:
        value = raw.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            out[field] = round(float(value) / 1e6, 8)  # D-Wave reports microseconds to at least 0.01 µs
    if not out:
        return None
    out["stages"] = {k: v for k, v in raw.items() if isinstance(v, (int, float, str))}
    return out


def provider_job_info(info: Any) -> Optional[Dict[str, Any]]:
    """D-Wave's problem id (and label / data id) that the cloud client adds to every result's info."""
    if not isinstance(info, dict) or not info.get("problem_id"):
        return None
    out: Dict[str, Any] = {"job_id": str(info["problem_id"]), "provider": "dwave"}
    if info.get("problem_label"):
        out["label"] = str(info["problem_label"])
    if info.get("problem_data_id"):
        out["problem_data_id"] = str(info["problem_data_id"])
    return out


def _local_timing_to_resource_usage(timing: Any) -> Optional[Dict[str, Any]]:
    """dwave-samplers (SimulatedAnnealing, SteepestDescent) report preprocessing/sampling/postprocessing in ns."""
    if not isinstance(timing, dict):
        return None
    ns = {k: v for k, v in timing.items() if str(k).endswith("_ns") and isinstance(v, (int, float))}
    if not ns:
        return None
    out: Dict[str, Any] = {"stages": ns, "cpu_time_s": round(sum(ns.values()) / 1e9, 6)}
    if "postprocessing_ns" in ns:
        out["post_processing_time_s"] = round(ns["postprocessing_ns"] / 1e9, 6)
    return out


def classify_sampleset_info(info: Any) -> Optional[Dict[str, str]]:
    """
    Where a SampleSet came from, judged by what its info holds (the SampleSet does not name its sampler).

    D-Wave's cloud (QPU and Leap hybrid solvers) returns a problem_id and QPU/charge timing; the local
    dwave-samplers report timing in *_ns fields, and simulated annealing adds its beta schedule.
    Samplers that return an empty info (ExactSolver, Tabu) cannot be told apart: None.
    """
    if not isinstance(info, dict):
        return None
    timing = info.get("timing") if isinstance(info.get("timing"), dict) else {}
    if "problem_id" in info or "qpu_access_time" in timing or "charge_time" in info or "qpu_access_time" in info:
        return {"provider": "dwave", "name": "unknown"}  # the solver is named when passed as backend=
    if "beta_range" in info and "beta_schedule_type" in info:
        return {"provider": "local_sim", "name": "SimulatedAnnealingSampler"}
    if timing and all(str(k).endswith("_ns") for k in timing):
        return {"provider": "local_sim", "name": "unknown"}
    return None


def _annealing_details(obj: Any) -> Optional[Dict[str, Any]]:
    """Embedding quality from EmbeddingComposite(..., return_embedding=True) and chain breaks per sample."""
    out: Dict[str, Any] = {}
    record = getattr(obj, "record", None)
    names = getattr(getattr(record, "dtype", None), "names", None) or ()
    if "chain_break_fraction" in names:
        cbf = record.chain_break_fraction
        occ = record.num_occurrences
        total = float(occ.sum()) if hasattr(occ, "sum") else 0.0
        if total > 0:
            out["chain_break_fraction"] = float((cbf * occ).sum() / total)  # weighted by occurrences
        out["max_chain_break_fraction"] = float(cbf.max())
    context = (getattr(obj, "info", None) or {}).get("embedding_context")
    if isinstance(context, dict):
        embedding = context.get("embedding")
        if isinstance(embedding, dict) and embedding:
            lengths = [len(chain) for chain in embedding.values()]
            out["num_logical_variables"] = len(lengths)
            out["num_physical_qubits"] = sum(lengths)
            out["max_chain_length"] = max(lengths)
            out["mean_chain_length"] = round(sum(lengths) / len(lengths), 3)
        strength = context.get("chain_strength")
        if isinstance(strength, (int, float)):
            out["chain_strength"] = float(strength)
        method = context.get("chain_break_method")
        if method is not None:
            out["chain_break_method"] = getattr(method, "__name__", str(method))
    return out or None


def describe_sampler(sampler: Any) -> Optional[Dict[str, str]]:
    """Classify a sampler passed as @observe_run(backend=sampler) by the package it comes from."""
    if sampler is None or isinstance(sampler, str):
        return None
    # Composites (EmbeddingComposite(DWaveSampler()), FixedEmbeddingComposite, ...) wrap the sampler
    # that actually runs the problem; describe that one.
    for _ in range(5):
        child = getattr(sampler, "child", None)
        if child is None:
            break
        sampler = child
    module = type(sampler).__module__ or ""
    if module.startswith("dwave.system.testing"):
        # MockDWaveSampler simulates a QPU locally (its results imitate QPU timing and a problem_id).
        return {"provider": "local_sim", "name": type(sampler).__name__}
    if module.startswith("dwave.system"):
        # DWaveSampler / LeapHybridSampler run on D-Wave's cloud; name the solver when known.
        solver = getattr(getattr(sampler, "solver", None), "name", None)
        return {"provider": "dwave", "name": str(solver or type(sampler).__name__)}
    if module.startswith(("dimod", "dwave.samplers", "neal", "tabu", "greedy")):
        return {"provider": "local_sim", "name": type(sampler).__name__}
    return None


class DWaveAdapter(Adapter):
    name = "dwave"
    priority = 40

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return hasattr(obj, "record") or "dimod" in obj.__class__.__module__

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        energies = {"value": None, "stderr": None}
        backend_name = "unknown"
        provider = "unknown"
        
        try:
            # Try multiple ways to get energy from dimod sampleset
            record = getattr(obj, "record", None)
            if record is not None:
                # Method 1: Get energy array from record
                e = getattr(record, "energy", None)
                if e is not None:
                    try:
                        # Try numpy array methods first
                        if hasattr(e, "min"):
                            min_energy = float(e.min())
                            energies["value"] = min_energy
                            
                            # Calculate stderr if multiple values
                            if hasattr(e, "__len__") and len(e) > 1:
                                try:
                                    import statistics
                                    if hasattr(e, "tolist"):
                                        e_list = e.tolist()
                                    elif hasattr(e, "__iter__"):
                                        e_list = list(e)
                                    else:
                                        e_list = []
                                    
                                    if len(e_list) > 1:
                                        stdev = statistics.stdev(e_list)
                                        energies["stderr"] = float(stdev / (len(e_list) ** 0.5))
                                except Exception:
                                    pass
                        # Fallback: try to convert to list and get min
                        elif hasattr(e, "__iter__"):
                            e_list = list(e)
                            if len(e_list) > 0:
                                energies["value"] = float(min(e_list))
                    except Exception:
                        pass
                
                # Method 2: Try accessing first record directly
                if energies["value"] is None:
                    try:
                        if hasattr(record, "__len__") and len(record) > 0:
                            first_rec = record[0]
                            if hasattr(first_rec, "energy"):
                                energies["value"] = float(first_rec.energy)
                    except Exception:
                        pass
            
            classified = classify_sampleset_info(getattr(obj, "info", None))
            if classified:
                provider, backend_name = classified["provider"], classified["name"]
        except Exception:
            pass

        # Shots: sum of num_occurrences if available
        shots = 1
        try:
            record = getattr(obj, "record", None)
            if record is not None and hasattr(record, "num_occurrences"):
                noc = record.num_occurrences
                if hasattr(noc, "sum"):
                    shots = int(noc.sum()) or 1
                elif hasattr(noc, "__len__") and len(noc) > 0:
                    shots = sum(int(x) for x in noc) or 1
        except Exception:
            pass

        # Execution time breakdown from sampleset.info["timing"] (QPU fields, or local *_ns fields)
        resource_usage = None
        annealing = None
        try:
            info = getattr(obj, "info", None)
            if isinstance(info, dict):
                timing = info.get("timing")
                resource_usage = _dwave_timing_to_resource_usage(timing, info) or _local_timing_to_resource_usage(timing)
            annealing = _annealing_details(obj)
        except Exception:
            pass
        try:
            provider_job = provider_job_info(getattr(obj, "info", None))
        except Exception:
            provider_job = None

        hinted = describe_sampler(context.backend_hint)
        if hinted:
            provider, backend_name = hinted["provider"], hinted["name"]

        out = {
            "sdk": {"name": "dwave_ocean", "version": get_sdk_version("dwave")},
            "backend": {"provider": provider, "name": backend_name},
            "shots": shots,
            "artifacts": {
                "result_type": "energies",
                "energies": energies,
            },
        }
        if annealing:
            out["artifacts"]["annealing"] = annealing
        execution: Dict[str, Any] = {}
        if resource_usage:
            execution["resource_usage"] = resource_usage
        if provider_job:
            execution["provider_job"] = provider_job
        if execution:
            out["execution"] = execution
        return out

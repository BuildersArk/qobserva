from __future__ import annotations

from typing import Any, Dict, Optional
from .base import Adapter, AdapterContext
from .version_utils import get_sdk_version


def _dwave_timing_to_resource_usage(timing: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Map D-Wave sampleset.info["timing"] (microseconds) to our resource_usage (seconds).
    See: https://docs.dwavesys.com/docs/latest/c_qpu_timing.html (SAPI Timing Fields)
    """
    if not timing or not isinstance(timing, dict):
        return None
    out = {"stages": timing}
    # qpu_access_time: total time in QPU (µs)
    qpu_us = timing.get("qpu_access_time")
    if qpu_us is not None:
        try:
            out["qpu_time_s"] = round(float(qpu_us) / 1e6, 3)
        except (TypeError, ValueError):
            pass
    # total_post_processing_time (µs)
    post_us = timing.get("total_post_processing_time")
    if post_us is not None:
        try:
            out["post_processing_time_s"] = round(float(post_us) / 1e6, 3)
        except (TypeError, ValueError):
            pass
    if len(out) <= 1:
        return None
    return out


def describe_sampler(sampler: Any) -> Optional[Dict[str, str]]:
    """Classify a sampler passed as @observe_run(backend=sampler) by the package it comes from."""
    if sampler is None or isinstance(sampler, str):
        return None
    module = type(sampler).__module__ or ""
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
            
            # Backend: a SampleSet from a local dimod/dwave-samplers sampler carries no solver
            # information (info == {}); results from D-Wave's cloud carry job details in info.
            info = getattr(obj, "info", None)
            if isinstance(info, dict) and ("timing" in info or "problem_id" in info):
                provider = "dwave"  # solver name is only known when the sampler is passed as backend=
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

        # Execution time breakdown from sampleset.info["timing"] (D-Wave QPU only)
        resource_usage = None
        try:
            info = getattr(obj, "info", None)
            if isinstance(info, dict):
                timing = info.get("timing")
                resource_usage = _dwave_timing_to_resource_usage(timing)
        except Exception:
            pass

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
        if resource_usage:
            out["execution"] = {"resource_usage": resource_usage}
        return out

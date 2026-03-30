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


class DWaveAdapter(Adapter):
    name = "dwave"
    priority = 40

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return hasattr(obj, "record") or "dimod" in obj.__class__.__module__

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        energies = {"value": None, "stderr": None}
        backend_name = "dwave-sampler"  # Default
        provider = "dwave"
        
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
            
            # Extract backend/sampler name from sampleset
            # Try to get solver/sampler information
            if hasattr(obj, "solver"):
                try:
                    solver = obj.solver
                    if hasattr(solver, "__class__"):
                        solver_name = solver.__class__.__name__
                        # Map common solver names
                        if "ExactSolver" in solver_name:
                            backend_name = "ExactSolver"
                        elif "SimulatedAnnealingSampler" in solver_name:
                            backend_name = "SimulatedAnnealingSampler"
                        elif "SteepestDescentSolver" in solver_name:
                            backend_name = "SteepestDescentSolver"
                        elif "TabuSampler" in solver_name:
                            backend_name = "TabuSampler"
                        elif "DWaveSampler" in solver_name or "DWave" in solver_name:
                            backend_name = "DWaveSampler"
                        else:
                            backend_name = solver_name
                except Exception:
                    pass
            
            # Try to get device/sampler from sampleset info
            if hasattr(obj, "info"):
                try:
                    info = obj.info
                    if isinstance(info, dict):
                        # Check for device/sampler info
                        if "sampler" in info:
                            backend_name = str(info["sampler"])
                        elif "device" in info:
                            backend_name = str(info["device"])
                        elif "solver" in info:
                            backend_name = str(info["solver"])
                except Exception:
                    pass
            
            # Check class name for hints
            if backend_name == "dwave-sampler":
                try:
                    class_name = obj.__class__.__name__
                    if "Exact" in class_name:
                        backend_name = "ExactSolver"
                    elif "SimulatedAnnealing" in class_name:
                        backend_name = "SimulatedAnnealingSampler"
                    elif "DWave" in class_name:
                        backend_name = "DWaveSampler"
                except Exception:
                    pass
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

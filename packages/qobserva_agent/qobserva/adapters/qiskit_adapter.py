from __future__ import annotations

import itertools
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from .base import Adapter, AdapterContext
from .common import build_artifacts, expectation
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


def to_datetime(value: Any) -> Optional[datetime]:
    """
    A timezone-aware datetime from Runtime job timestamps. Real IBM jobs report ISO 8601 strings
    ('2026-09-28T16:44:27.019265Z'); local testing mode reports naive datetimes in the machine's local time.
    """
    if isinstance(value, str) and value:
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        value = value.astimezone()  # interpret as local time
    return value.astimezone(timezone.utc)


def iso_utc(value: Any) -> Optional[str]:
    """datetime or ISO string -> ISO 8601 UTC ('...Z')."""
    dt = to_datetime(value)
    return dt.isoformat().replace("+00:00", "Z") if dt else None


def _job_metrics(job: Any, resource_usage: Dict[str, Any]) -> Dict[str, Any]:
    """
    Qiskit Runtime job.metrics(): created/running/finished timestamps, billed QPU seconds and the reported
    circuit execution time.
    Only called for a finished job (after .result()); for cloud jobs it is one API request.
    """
    out: Dict[str, Any] = {}
    metrics_fn = getattr(job, "metrics", None)
    if job is None or not callable(metrics_fn) or not (type(job).__module__ or "").startswith("qiskit_ibm_runtime"):
        return out
    m = metrics_fn()
    if not isinstance(m, dict):
        return out
    ts = m.get("timestamps") or {}
    timeline = {k: iso_utc(ts.get(k)) for k in ("created", "running", "finished")}
    timeline = {k: v for k, v in timeline.items() if v}
    if timeline:
        timeline["source"] = "ibm_runtime_job"
        out["timeline"] = timeline
    created, running = to_datetime(ts.get("created")), to_datetime(ts.get("running"))
    if created and running:
        queue_ms = int((running - created).total_seconds() * 1000)
        if queue_ms >= 0:
            out["queue_ms"] = queue_ms
    usage = m.get("usage") or {}
    # Real IBM Quantum Platform jobs report the billed QPU time as qpu_charge_time_seconds (whole seconds,
    # seen 2026-09-28); local testing mode reports quantum_seconds instead.
    qpu_s = usage.get("qpu_charge_time_seconds", usage.get("quantum_seconds"))
    if isinstance(qpu_s, (int, float)) and qpu_s > 0 and "qpu_time_s" not in resource_usage:
        resource_usage["qpu_time_s"] = float(qpu_s)
    exec_ns = m.get("circuits_execution_time_ns")
    if isinstance(exec_ns, (int, float)) and exec_ns > 0:
        resource_usage["circuit_execution_time_s"] = round(exec_ns / 1e9, 6)
    return out


def _execution_spans(obj: Any) -> Optional[Dict[str, Any]]:
    """IBM hardware results: metadata["execution"]["execution_spans"], one span per chunk of shots on the QPU."""
    metadata = getattr(obj, "metadata", None)
    execution = metadata.get("execution") if isinstance(metadata, dict) else None
    spans = execution.get("execution_spans") if isinstance(execution, dict) else None
    if spans is None:
        return None
    items: List[Dict[str, Any]] = []
    for span in spans:
        start, stop = iso_utc(getattr(span, "start", None)), iso_utc(getattr(span, "stop", None))
        if not start or not stop:
            continue
        items.append({"start": start, "stop": stop,
                      "duration_s": round((span.stop - span.start).total_seconds(), 6)})
    if not items:
        return None
    return {"count": len(items), "spans": items[:100],
            "total_s": round(sum(s["duration_s"] for s in items), 6),
            "start": min(s["start"] for s in items), "stop": max(s["stop"] for s in items)}


# Runtime options worth showing on a run (error suppression/mitigation and shots), from
# result.metadata["options"] (client-side executor primitives) or the job's inputs.
_OPTION_KEYS = ("default_shots", "default_precision", "resilience_level", "optimization_level",
                "twirling", "dynamical_decoupling", "resilience", "execution")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)


def _execution_options(obj: Any, job: Any) -> Optional[Dict[str, Any]]:
    candidates = []
    metadata = getattr(obj, "metadata", None)
    if isinstance(metadata, dict):
        candidates.append(metadata.get("options"))
    inputs = getattr(job, "inputs", None) if job is not None else None
    if isinstance(inputs, dict):
        candidates.append(inputs.get("options"))
        candidates.append({k: inputs[k] for k in ("resilience_level", "optimization_level") if k in inputs})
    options: Dict[str, Any] = {}
    for c in candidates:
        if isinstance(c, dict):
            for k in _OPTION_KEYS:
                if k in c and c[k] is not None and k not in options:
                    options[k] = _json_safe(c[k])
    return options or None


# Settings IBM reports in the result metadata as actually applied (e.g. the Estimator's
# resilience_level=1 turns on measurement twirling and measurement mitigation).
_APPLIED_OPTION_KEYS = ("twirling", "dynamical_decoupling", "resilience")


def _applied_options(obj: Any) -> Optional[Dict[str, Any]]:
    metadata = getattr(obj, "metadata", None)
    if not isinstance(metadata, dict):
        return None
    applied = {k: _json_safe(metadata[k]) for k in _APPLIED_OPTION_KEYS if isinstance(metadata.get(k), dict)}
    return applied or None


def _input_options(job: Any) -> Optional[Dict[str, Any]]:
    """Everything the job was submitted with except the circuits themselves (IBM's 'Input options')."""
    inputs = getattr(job, "inputs", None) if job is not None else None
    if not isinstance(inputs, dict):
        return None
    out = {k: _json_safe(v) for k, v in inputs.items() if k not in ("pubs", "quantum_program")}
    program = inputs.get("quantum_program")
    if program is not None:
        out["shots"] = getattr(program, "shots", None)
        out["items"] = len(getattr(program, "items", None) or [])
    return out or None


def _region_from_crn(crn: Any) -> Optional[str]:
    """'crn:v1:bluemix:public:quantum-computing:us-east:a/<account>:<instance>::' -> 'us-east'.
    Only the region is kept: the CRN itself contains the IBM Cloud account id."""
    if not isinstance(crn, str) or not crn.startswith("crn:"):
        return None
    parts = crn.split(":")
    return parts[5] if len(parts) > 5 and parts[5] else None


def provider_job_info(job: Any, obj: Any) -> Optional[Dict[str, Any]]:
    """
    Identifiers for correlating a run with the provider's own job page: the job id always, and for
    IBM Runtime jobs the program (sampler/estimator/executor), session, tags, items, region, creation
    time and IBM's usage estimate.
    """
    if job is None:
        return None
    job_id = None
    for attr in ("job_id", "id"):
        value = getattr(job, attr, None)
        try:
            value = value() if callable(value) else value
        except Exception:
            value = None
        if isinstance(value, str) and value:
            job_id = value
            break
    if not job_id:
        return None
    info: Dict[str, Any] = {"job_id": job_id}
    if not (type(job).__module__ or "").startswith("qiskit_ibm_runtime"):
        return info
    info["provider"] = "ibm"
    for key, attr in (("program", "primitive_id"), ("session_id", "session_id"), ("tags", "tags"), ("private", "private")):
        try:
            value = getattr(job, attr, None)
            value = value() if callable(value) else value
            if value not in (None, [], ""):
                info[key] = _json_safe(value)
        except Exception:
            pass
    if info.get("session_id") == job_id:
        info.pop("session_id")  # local testing mode reports the job id as its session id
    info["mode"] = "session/batch" if info.get("session_id") else "job"
    try:
        region = _region_from_crn(getattr(job, "instance", None))
        if region:
            info["region"] = region
    except Exception:
        pass
    try:
        created = iso_utc(getattr(job, "creation_date", None))
        if created:
            info["created"] = created
    except Exception:
        pass
    try:
        estimate = (job.usage_estimation or {}).get("quantum_seconds")
        if isinstance(estimate, (int, float)):
            info["usage_estimate_s"] = round(float(estimate), 3)
    except Exception:
        pass
    try:
        inputs = job.inputs or {}
        if inputs.get("pubs") is not None:
            info["items"] = len(inputs["pubs"])
        elif inputs.get("quantum_program") is not None:
            info["items"] = len(inputs["quantum_program"].items)
    except Exception:
        pass
    return info


def _chunk_timing(obj: Any) -> Optional[Dict[str, Any]]:
    """Executor results (client-side Sampler): metadata["executor"].chunk_timing, one span per chunk on the QPU."""
    metadata = getattr(obj, "metadata", None)
    executor = metadata.get("executor") if isinstance(metadata, dict) else None
    chunks = getattr(executor, "chunk_timing", None)
    if not chunks:
        return None
    items: List[Dict[str, Any]] = []
    for chunk in chunks:
        start, stop = to_datetime(getattr(chunk, "start", None)), to_datetime(getattr(chunk, "stop", None))
        if not start or not stop:
            continue
        parts = [{"item": getattr(p, "idx_item", None), "size": getattr(p, "size", None)}
                 for p in (getattr(chunk, "parts", None) or [])]
        items.append({"start": iso_utc(start), "stop": iso_utc(stop),
                      "duration_s": round((stop - start).total_seconds(), 6), "parts": parts})
    if not items:
        return None
    return {"count": len(items), "chunks": items[:100], "total_s": round(sum(c["duration_s"] for c in items), 6)}


def _simulator_time_s(obj: Any) -> Optional[float]:
    """Aer primitives report time_taken_execute per pub (directly or under the executor's metadata)."""
    total = 0.0
    found = False
    try:
        for pub in obj:
            md = getattr(pub, "metadata", None) or {}
            sim = md.get("simulator_metadata") or (md.get("executor") or {}).get("simulator_metadata") or {}
            t = sim.get("time_taken_execute")
            if isinstance(t, (int, float)):
                total += float(t)
                found = True
    except Exception:
        return None
    return round(total, 6) if found else None


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


def _pub_counts(data: Any) -> Optional[Dict[str, int]]:
    """Counts from a SamplerV2 pub's DataBin: the 'meas' register, then 'c', then any other register."""
    meas = getattr(data, "meas", None)
    if meas is not None and hasattr(meas, "get_counts"):
        return meas.get_counts()
    if meas is None:
        c = getattr(data, "c", None)
        if c is not None and hasattr(c, "get_counts"):
            return c.get_counts()
    if hasattr(data, "keys"):
        # Custom classical register names (e.g. ClassicalRegister(2, "cr"))
        for field_name in data.keys():
            reg = getattr(data, field_name, None)
            if reg is not None and hasattr(reg, "get_counts"):
                return reg.get_counts()
    return None


def _pub_expectations(index: int, data: Any) -> List[Optional[Dict[str, Any]]]:
    """EstimatorV2 pub: data.evs / data.stds share a shape (one entry per observable/parameter set)."""
    evs = getattr(data, "evs", None)
    if evs is None:
        return []
    stds = getattr(data, "stds", None)
    shape = tuple(getattr(evs, "shape", ()) or ())
    if not shape:
        return [expectation(f"pub{index}", evs, stds)]
    out: List[Optional[Dict[str, Any]]] = []
    for idx in itertools.product(*(range(n) for n in shape)):
        label = f"pub{index}[{','.join(map(str, idx))}]"
        std = stds[idx] if stds is not None and getattr(stds, "shape", None) == shape else None
        out.append(expectation(label, evs[idx], std))
    return out


def _primitive_result(obj: Any) -> Dict[str, Any]:
    """Counts (SamplerV2) and expectation values (EstimatorV2) from every pub of a PrimitiveResult."""
    pub_counts: List[Dict[str, int]] = []
    pub_shots: List[int] = []
    expectations: List[Optional[Dict[str, Any]]] = []
    estimator_shots = 0
    exact_pubs = 0
    for i, pub_result in enumerate(obj):
        data = getattr(pub_result, "data", None)
        metadata = getattr(pub_result, "metadata", None)
        if data is None:
            continue
        counts = _pub_counts(data)
        if isinstance(counts, dict):
            pub_counts.append({str(k): int(v) for k, v in counts.items()})
            shots = metadata.get("shots") if isinstance(metadata, dict) else None
            pub_shots.append(int(shots) if isinstance(shots, int) else sum(pub_counts[-1].values()))
        pub_exps = _pub_expectations(i, data)
        if pub_exps and isinstance(metadata, dict) and isinstance(metadata.get("shots"), int):
            estimator_shots = max(estimator_shots, metadata["shots"])  # shot-based estimators report it
        if (pub_exps and isinstance(metadata, dict) and "shots" not in metadata
                and metadata.get("target_precision") == 0):
            exact_pubs += 1  # StatevectorEstimator / Aer EstimatorV2 at precision 0: computed exactly
        expectations.extend(pub_exps)
    return {"pub_counts": pub_counts, "pub_shots": pub_shots, "expectations": expectations,
            "estimator_shots": estimator_shots,
            "exact": bool(exact_pubs) and not pub_counts and exact_pubs == len(obj)}


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
        exact = False
        backend_name = "unknown"
        provider = "unknown"
        expectations: List[Optional[Dict[str, Any]]] = []
        batches: List[Dict[str, Any]] = []

        # Qiskit 2.x PrimitiveResult (SamplerV2 counts, EstimatorV2 expectation values)
        if hasattr(obj, "__class__") and obj.__class__.__name__ == "PrimitiveResult":
            try:
                prim = _primitive_result(obj)
                if prim["pub_counts"]:
                    # The first pub's counts stay the run's histogram (as before); with several pubs,
                    # each pub is also kept as a batch entry instead of being dropped.
                    counts = prim["pub_counts"][0]
                    shots = prim["pub_shots"][0]
                    if len(prim["pub_counts"]) > 1:
                        batches = [{"label": f"pub{i}", "shots": s, "histogram": h}
                                   for i, (h, s) in enumerate(zip(prim["pub_counts"], prim["pub_shots"]))]
                expectations = prim["expectations"]
                if counts is None and prim["estimator_shots"]:
                    shots = prim["estimator_shots"]
                exact = prim["exact"]
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
        resource_usage = _get_resource_usage_from_result(obj) or {}
        execution_extra: Dict[str, Any] = {}
        # Each source is independent and best effort: a missing field never loses the counts/values.
        def options():
            # Requested options (job inputs / executor metadata), overlaid with what IBM reports as applied.
            opts = _execution_options(obj, context.job) or {}
            opts.update(_applied_options(obj) or {})
            return {"options": opts or None}

        for extra in (
            lambda: _job_metrics(context.job, resource_usage),
            lambda: {"execution_spans": _execution_spans(obj)},
            lambda: {"chunk_timing": _chunk_timing(obj)},
            options,
            lambda: {"input_options": _input_options(context.job)},
            lambda: {"provider_job": provider_job_info(context.job, obj)},
        ):
            try:
                execution_extra.update({k: v for k, v in extra().items() if v is not None})
            except Exception:
                pass
        if "cpu_time_s" not in resource_usage and obj.__class__.__name__ == "PrimitiveResult":
            sim_s = _simulator_time_s(obj)
            if sim_s is not None:
                resource_usage["cpu_time_s"] = sim_s
        if resource_usage:
            execution_extra["resource_usage"] = resource_usage

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

        out = {
            "sdk": {"name": "qiskit", "version": get_sdk_version("qiskit")},
            "backend": {"provider": provider, "name": backend_name},
            "shots": shots,
            "artifacts": build_artifacts(histogram=histogram, expectations=expectations, batches=batches),
        }
        if execution_extra:
            out["execution"] = execution_extra
        if exact:
            out["exact"] = True
        return out

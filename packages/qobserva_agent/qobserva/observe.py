from __future__ import annotations

import hashlib
import json
import platform
import time
import uuid
from functools import wraps
from typing import Any, Callable, Dict, Optional, Tuple

from .adapters.base import AdapterContext
from .adapters.circuits import (circuit_from_job, circuit_from_result, describe_circuit, describe_circuit_source,
                                qnode_source, qnode_specs, to_event_metrics)
from .adapters.common import has_result_data
from .registry import load_adapters, select_adapter
from .emitter import emit
from .report import iso_now
from .sanitize import host_identity, sanitize_error_message

def _package_version(dist_name: str) -> str | None:
    """Installed distribution version, or None if not importable as a wheel/sdist."""
    try:
        from importlib import metadata

        return metadata.version(dist_name)
    except Exception:
        return None


def _hash_program(obj: Any) -> str:
    try:
        b = json.dumps(str(obj), sort_keys=True).encode("utf-8")
    except Exception:
        b = repr(obj).encode("utf-8")
    return hashlib.sha256(b).hexdigest()

def _fallback_extracted(tags: Dict[str, str] | None) -> Dict[str, Any]:
    """
    Conservative fallback when adapter selection/extraction fails.
    This intentionally does NOT claim precise hardware details; it only provides
    safe defaults based on an explicit sdk tag when available.
    """
    sdk = (tags or {}).get("sdk")
    if not sdk:
        return {
            "backend": {"provider": "unknown", "name": "unknown"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
            "sdk": {},
        }

    sdk_l = sdk.lower()
    if sdk_l == "pennylane":
        return {
            "sdk": {"name": "pennylane", "version": None},
            "backend": {"provider": "local_sim", "name": "default.qubit"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
        }
    if sdk_l == "dwave":
        return {
            "sdk": {"name": "dwave", "version": None},
            "backend": {"provider": "dwave", "name": "unknown"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
        }
    if sdk_l == "braket":
        return {
            "sdk": {"name": "braket", "version": None},
            "backend": {"provider": "aws_braket", "name": "unknown"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
        }
    if sdk_l == "cirq":
        return {
            "sdk": {"name": "cirq", "version": None},
            "backend": {"provider": "local_sim", "name": "unknown"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
        }
    if sdk_l == "qiskit":
        return {
            "sdk": {"name": "qiskit", "version": None},
            "backend": {"provider": "unknown", "name": "unknown"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
        }
    if sdk_l == "pyquil":
        return {
            "sdk": {"name": "pyquil", "version": None},
            "backend": {"provider": "unknown", "name": "unknown"},
            "shots": 1,
            "artifacts": {"result_type": "unknown"},
        }

    return {
        "backend": {"provider": "unknown", "name": "unknown"},
        "shots": 1,
        "artifacts": {"result_type": "unknown"},
        "sdk": {"name": sdk_l, "version": None},
    }

# Jobs/tasks from local simulators finish in-process, so calling .result() on them never waits on
# a remote queue. Cloud jobs (IBM Runtime, AWS Braket, ...) are only awaited with await_result=True.
_LOCAL_JOB_MODULES = (
    "qiskit.primitives.primitive_job",   # StatevectorSampler/Estimator, BackendSamplerV2/EstimatorV2
    "qiskit_aer.",                       # AerJob, Aer primitives
    "qiskit.providers.basic_provider",   # BasicSimulator jobs
    "braket.tasks.local_quantum_task",   # LocalSimulator().run(...)
    "qiskit_ibm_runtime.fake_provider.", # Runtime local testing mode: SamplerV2(mode=FakeManilaV2())
    "cirq_google.engine.simulated_local_job",  # Quantum Virtual Machine: processor.run_sweep(...)
)
_CLOUD_JOB_MODULES = (
    "qiskit_ibm_runtime.",
    "braket.aws.",
    "cirq_google.engine.engine_job",     # Google Quantum Engine
)

def _has_result(obj: Any) -> bool:
    """A job whose results can be read: .result(), or .results() on Cirq Engine jobs."""
    if callable(getattr(obj, "result", None)):
        return True
    return (type(obj).__module__ or "").startswith("cirq_google.engine") and callable(getattr(obj, "results", None))

def _result_of(job: Any) -> Any:
    return job.result() if callable(getattr(job, "result", None)) else job.results()

def _is_local_job(obj: Any) -> bool:
    module = type(obj).__module__ or ""
    return _has_result(obj) and module.startswith(_LOCAL_JOB_MODULES)

def _is_cloud_job(obj: Any) -> bool:
    module = type(obj).__module__ or ""
    return _has_result(obj) and module.startswith(_CLOUD_JOB_MODULES)

def _job_id(job: Any) -> str | None:
    for attr in ("job_id", "id"):
        value = getattr(job, attr, None)
        if callable(value):
            try:
                value = value()
            except Exception:
                value = None
        if isinstance(value, str) and value:
            return value
    return None

def _check_extracted(extracted: Dict[str, Any], obj: Any, project: str, pending_job: Any) -> None:
    """
    A successful run whose result yielded no values is recorded as result_type "unknown" with the
    type that was returned, and the user is told once, instead of storing an empty "success".
    """
    artifacts = extracted.get("artifacts")
    if not isinstance(artifacts, dict):
        artifacts = {}
    if has_result_data(artifacts):
        return
    type_name = f"{type(obj).__module__}.{type(obj).__qualname__}"
    kept = {k: v for k, v in artifacts.items() if k not in ("counts", "expectations", "result_type")}
    kept["result_type"] = "unknown"
    if pending_job is not None:
        kept["pending_job"] = {"type": type_name, "job_id": _job_id(pending_job)}
        hint = ("a cloud job was returned before it finished. Pass await_result=True to "
                "@observe_run to wait for it and record its results")
    else:
        kept["unrecognized"] = {"type": type_name}
        hint = ("return the SDK's result object (for example job.result()) from the decorated function; "
                "see https://qobserva.com/docs.html for the supported result types")
    extracted["artifacts"] = kept
    import warnings
    warnings.warn(f"QObserva: recorded the run for project '{project}' but could not read any results "
                  f"from the returned {type_name}: {hint}.", UserWarning, stacklevel=3)

def _start_braket_tracker(tags: Dict[str, str]) -> Any:
    """
    Record AWS Braket tasks created during the run so their cost can be estimated: sdk="braket", and
    sdk="pennylane" (the Braket plugin creates Braket tasks). Without amazon-braket-sdk this is a no-op.
    """
    if str((tags or {}).get("sdk", "")).lower() not in ("braket", "pennylane"):
        return None
    try:
        from braket.tracking import Tracker
        return Tracker().start()
    except Exception:
        return None

def _circuit_metrics(circuit: Any, job: Any, result: Any, fn: Any, args: tuple, kwargs: dict,
                     backend_info: Dict[str, Any], with_source: bool) -> Tuple[Dict[str, Any] | None, Dict[str, Any] | None]:
    """
    Metrics (and, with with_source, the circuit text and diagram) for the circuit that ran:
    circuit= first, then a Runtime job's inputs, then the program a Braket result carries, then a QNode.
    """
    if isinstance(circuit, (list, tuple)):
        circuit = circuit[0] if circuit else None
    candidates = [("decorator", lambda: circuit), ("job", lambda: circuit_from_job(job)),
                  ("result", lambda: circuit_from_result(result)), ("qnode", lambda: fn)]
    for source, get in candidates:
        try:
            obj = get()
            metrics = describe_circuit(qnode_specs(fn, args, kwargs) if source == "qnode" else obj)
        except Exception:
            metrics = None
        if metrics:
            # A circuit read from the job is what the provider ran; local simulators and Braket's
            # managed simulators (provider "aws_braket"; QPUs are labeled by maker) run the circuit
            # exactly as given. Either way its metrics are the executed ones.
            executed_as_given = source == "job" or backend_info.get("provider") in ("local_sim", "aws_braket")
            text = None
            if with_source:
                try:
                    text = qnode_source(fn, args, kwargs) if source == "qnode" else describe_circuit_source(obj)
                except Exception:
                    text = None
                if text:
                    text["from"] = source
            return to_event_metrics(metrics, executed_as_given, source), text
    return None, None

def _apply_backend_override(extracted: Dict[str, Any], backend: Any, provider: str | None) -> None:
    """Explicit backend=/provider= from the decorator win over values inferred from the result."""
    if backend is None and provider is None:
        return
    info = dict(extracted.get("backend") or {"provider": "unknown", "name": "unknown"})
    if isinstance(backend, str):
        info["name"] = backend
    elif backend is not None and info.get("name") in (None, "", "unknown"):
        # Adapters that understand backend objects already used the hint; this covers the rest.
        name = getattr(backend, "name", None)
        if callable(name):
            try:
                name = name()
            except Exception:
                name = None
        if name:
            info["name"] = str(name)
    if provider:
        info["provider"] = provider
    extracted["backend"] = info

def observe_run(
    project: str,
    tags: Optional[Dict[str, str]] = None,
    capture_program: str = "full",
    await_result: bool = False,
    measurement_key: Optional[str] = None,
    benchmark_id: Optional[str] = None,
    benchmark_params: Optional[Dict[str, Any]] = None,
    endpoint: str | None = None,
    api_key: str | None = None,
    backend: Any = None,
    provider: str | None = None,
    circuit: Any = None,
):
    """
    Decorator to instrument quantum program runs with QObserva telemetry.
    
    **IMPORTANT: Always include SDK tag for reliable adapter selection!**
    
    Args:
        project: Project name (user-defined, used for grouping runs)
        tags: Dictionary of tags. **REQUIRED: Include "sdk" tag** (e.g., {"sdk": "qiskit"})
        capture_program: What to record about the circuit. "full" (default): metrics, a hash, the circuit
            as OpenQASM/Quil and a text diagram (stored by your collector; local by default).
            "hash": metrics and a hash only (the 0.1.7 behavior). "none": nothing about the circuit.
        await_result: If True, await async results (e.g., Task.result())
        measurement_key: Framework-specific measurement key (e.g., for Cirq)
        benchmark_id: Optional benchmark identifier
        benchmark_params: Optional benchmark parameters
        endpoint: Optional custom collector endpoint
        api_key: Optional API key for authentication
        backend: Optional backend the run executed on, when the SDK result does not say
            (e.g. Qiskit V2 primitive results carry no backend). Either an SDK backend
            object (AerSimulator(), service.backend("ibm_brisbane"), ...) or a name string.
        provider: Optional provider label to record (e.g. "ibm", "aws_braket", "local_sim").
        circuit: Optional circuit the run executes (Qiskit QuantumCircuit, Cirq Circuit, Braket Circuit
            or pyQuil Program), to record its qubits, depth and gate counts. Not needed for IBM Runtime
            jobs or PennyLane QNodes, whose circuits are read automatically. capture_program="none"
            turns circuit metrics off.
    
    Example:
        @observe_run(
            project="my_project",
            tags={"sdk": "qiskit", "algorithm": "vqe"}  # ← SDK tag is REQUIRED!
        )
        def my_quantum_algorithm():
            # Your code here
            return result
    
    Supported SDK values: "qiskit", "braket", "cirq", "pennylane", "pyquil", "dwave"
    """
    tags = tags or {}
    benchmark_params = benchmark_params or {}
    
    # Warn if SDK tag is missing (but don't fail - allow fallback to object inspection)
    if "sdk" not in tags:
        import warnings
        warnings.warn(
            f"⚠️  QObserva: Missing 'sdk' tag in @observe_run decorator for project '{project}'. "
            f"Adapter selection will rely on result object inspection, which may be unreliable. "
            f"Please add tags={{\"sdk\": \"qiskit\"}} (or braket/cirq/pennylane/pyquil/dwave) "
            f"for definitive adapter selection. See README.md for details.",
            UserWarning,
            stacklevel=2
        )
    
    adapters = load_adapters()

    def decorator(fn: Callable[..., Any]):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            started_iso = iso_now()
            t0 = time.time()
            exc: BaseException | None = None
            status = "success"
            obj: Any = None
            job: Any = None
            pending_job: Any = None

            returned: Any = None
            tracker = _start_braket_tracker(tags)

            try:
                obj = returned = fn(*args, **kwargs)
                if await_result and _has_result(obj):
                    job = obj
                    obj = returned = _result_of(obj)
            except BaseException as e:
                exc = e
                status = "failed"
            finally:
                if tracker is not None:
                    try:
                        tracker.stop()
                    except Exception:
                        pass

            if exc is None and not await_result and _has_result(obj):
                if _is_local_job(obj):
                    # Read the finished local job's result for telemetry; the user still gets the job back.
                    try:
                        job, obj = obj, _result_of(obj)
                    except Exception:
                        pass
                elif _is_cloud_job(obj):
                    # Never block the user's program on a remote queue unless asked to.
                    pending_job = job = obj

            ended_iso = iso_now()
            runtime_ms = int((time.time() - t0) * 1000)

            ctx = AdapterContext(
                project=project,
                tags=tags,
                capture_program=capture_program,
                measurement_key=measurement_key,
                benchmark_id=benchmark_id,
                benchmark_params=benchmark_params,
                started_at_iso=started_iso,
                ended_at_iso=ended_iso,
                runtime_ms=runtime_ms,
                exception=exc,
                job=job,
                backend_hint=backend,
                function=fn,
                cost_tracker=tracker,
            )

            # Select an adapter even if obj is None (e.g., user forgot to return a result)
            # so we can still record sane metadata when sdk tag is provided.
            adapter = select_adapter(obj, ctx, adapters)
            if adapter:
                try:
                    extracted = adapter.extract(obj, ctx)
                except Exception:
                    extracted = _fallback_extracted(tags)
            else:
                extracted = _fallback_extracted(tags)

            if exc is None:
                try:
                    _check_extracted(extracted, obj, project, pending_job)
                except Exception:
                    pass  # includes warnings turned into errors: telemetry never breaks the program

            _apply_backend_override(extracted, backend, provider)

            if capture_program != "none" and exc is None:
                cm, text = _circuit_metrics(circuit, job, obj, fn, args, kwargs, extracted.get("backend") or {},
                                            with_source=capture_program in ("full", "attachment"))
                if cm:
                    extracted["circuit_metrics"] = cm
                if text:
                    extracted["circuit"] = text

            shots = int(extracted.get("shots", 1) or 1)

            _sw: Dict[str, Any] = {
                "sdk": extracted.get("sdk", {}),
                "python_version": platform.python_version(),
            }
            _av = _package_version("qobserva-agent")
            if _av:
                _sw["agent_version"] = _av
            _qv = _package_version("qobserva")
            if _qv:
                _sw["qobserva_version"] = _qv
            _cv = _package_version("qobserva-collector")
            if _cv:
                _sw["collector_version"] = _cv

            event = {
                "schema_version": "0.1.0",
                "event_id": str(uuid.uuid4()),
                "run_id": str(uuid.uuid4()),
                "created_at": started_iso,
                "project": project,
                "tags": tags,
                "actor": host_identity(),
                "software": _sw,
                "backend": extracted.get("backend", {"provider": "unknown", "name": "unknown"}),
                "program": extracted.get("program", {
                    "kind": "circuit",
                    "benchmark_id": benchmark_id,
                    "benchmark_params": benchmark_params,
                    "program_hash": _hash_program(kwargs.get("program")) if capture_program != "none" else None,
                    "circuit_metrics": extracted.get("circuit_metrics", {}),
                    **({"circuit": extracted["circuit"]} if extracted.get("circuit") else {}),
                }),
                "execution": {
                    "shots": shots,
                    "status": status,
                    "started_at": started_iso,
                    "ended_at": ended_iso,
                    "runtime_ms": runtime_ms,
                    "error": None if exc is None else {
                        "type": type(exc).__name__,
                        "message": sanitize_error_message(str(exc)),
                    },
                    **(extracted.get("execution") or {}),
                    # Computed exactly, no sampling: shots stays 1 only because the schema requires
                    # shots >= 1 (older collectors reject 0); newer collectors count these as 0 shots.
                    **({"exact": True} if extracted.get("exact") and exc is None else {}),
                },
                "cost": extracted.get("cost", {
                    "currency": "USD",
                    "estimated_cost": None,
                    "cost_source": "unknown",
                    "provider_cost_breakdown": {},
                }),
                "artifacts": extracted.get("artifacts", {"result_type": "unknown"}),
                "provider_payload": extracted.get("provider_payload", {"included": False}),
            }

            # Best effort, non-blocking emission: telemetry must never slow down or break the user workload.
            try:
                emit(event, endpoint=endpoint, api_key=api_key)
            except Exception:
                pass

            if exc is not None:
                raise exc
            return returned

        return wrapper

    return decorator

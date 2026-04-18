from __future__ import annotations

import hashlib
import json
import platform
import socket
import time
import uuid
from functools import wraps
from typing import Any, Callable, Dict, Optional

from .adapters.base import AdapterContext
from .registry import load_adapters, select_adapter
from .report import iso_now, report_run
from .sanitize import sanitize_error_message

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

def observe_run(
    project: str,
    tags: Optional[Dict[str, str]] = None,
    capture_program: str = "hash",
    await_result: bool = False,
    measurement_key: Optional[str] = None,
    benchmark_id: Optional[str] = None,
    benchmark_params: Optional[Dict[str, Any]] = None,
    endpoint: str | None = None,
    api_key: str | None = None,
):
    """
    Decorator to instrument quantum program runs with QObserva telemetry.
    
    **IMPORTANT: Always include SDK tag for reliable adapter selection!**
    
    Args:
        project: Project name (user-defined, used for grouping runs)
        tags: Dictionary of tags. **REQUIRED: Include "sdk" tag** (e.g., {"sdk": "qiskit"})
        capture_program: How to capture program ("hash", "none", "attachment")
        await_result: If True, await async results (e.g., Task.result())
        measurement_key: Framework-specific measurement key (e.g., for Cirq)
        benchmark_id: Optional benchmark identifier
        benchmark_params: Optional benchmark parameters
        endpoint: Optional custom collector endpoint
        api_key: Optional API key for authentication
    
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

            try:
                obj = fn(*args, **kwargs)
                if await_result and hasattr(obj, "result") and callable(getattr(obj, "result")):
                    obj = obj.result()
            except BaseException as e:
                exc = e
                status = "failed"

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
                "actor": {"host": socket.gethostname()},
                "software": _sw,
                "backend": extracted.get("backend", {"provider": "unknown", "name": "unknown"}),
                "program": extracted.get("program", {
                    "kind": "circuit",
                    "benchmark_id": benchmark_id,
                    "benchmark_params": benchmark_params,
                    "program_hash": _hash_program(kwargs.get("program")) if capture_program == "hash" else None,
                    "circuit_metrics": extracted.get("circuit_metrics", {}),
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

            # Best effort emission: do not break user workload if telemetry fails.
            try:
                report_run(event, endpoint=endpoint, api_key=api_key)
            except Exception:
                pass

            if exc is not None:
                raise exc
            return obj

        return wrapper

    return decorator

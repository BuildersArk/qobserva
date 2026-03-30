from __future__ import annotations

from importlib.metadata import entry_points
from typing import Any, List

from .adapters.base import Adapter, AdapterContext

def load_adapters() -> List[Adapter]:
    adapters: List[Adapter] = []
    eps = entry_points(group="qobserva.adapters")
    for ep in eps:
        try:
            cls = ep.load()
            adapters.append(cls())
        except Exception:
            # Missing optional dependency or load error -> skip
            continue
    adapters.sort(key=lambda a: (-getattr(a, "priority", 0), getattr(a, "name", "")))
    return adapters

def select_adapter(obj: Any, ctx: AdapterContext, adapters: List[Adapter]) -> Adapter | None:
    """
    Select adapter using definitive information in priority order:
    
    1. SDK tag (explicit, user-provided) - Most reliable
    2. Result object characteristics (module names, class names, methods) - Definitive for SDK objects
    3. Priority-based matching - Only for ambiguous cases (plain dicts, generic types)
    
    Note: We do NOT use project names as they are user-defined and arbitrary.
    """
    # Step 1: SDK tag (explicit, most reliable)
    # If user explicitly specifies SDK in tags, use that definitively
    if ctx.tags and "sdk" in ctx.tags:
        sdk_tag = ctx.tags["sdk"].lower()
        for adapter in adapters:
            if adapter.name.lower() == sdk_tag:
                # Verify it can handle the object (safety check)
                try:
                    if adapter.can_handle(obj, ctx):
                        return adapter
                except Exception:
                    continue
    
    # Step 2: Result object characteristics (definitive for SDK objects)
    # Most SDKs return objects with distinctive module/class names:
    # - Qiskit: obj.__class__.__module__ starts with "qiskit"
    # - Braket: obj.__class__.__module__ contains "braket"
    # - Cirq: obj.__class__.__module__ starts with "cirq"
    # - PennyLane: obj.__class__.__module__ contains "pennylane"
    # - D-Wave: obj.__class__.__module__ contains "dimod"
    # 
    # For these, we can identify the SDK immediately from the object itself.
    # Check all adapters to find one that definitively matches the object type.
    definitive_matches = []
    for adapter in adapters:
        try:
            # Check if adapter can definitively identify this as its SDK
            # (not just "could handle", but "definitively is this SDK")
            if _is_definitive_match(adapter, obj, ctx):
                definitive_matches.append(adapter)
        except Exception:
            continue
    
    # If we have definitive matches (based on object characteristics), use the highest priority one
    if definitive_matches:
        definitive_matches.sort(key=lambda a: (-getattr(a, "priority", 0), getattr(a, "name", "")))
        return definitive_matches[0]
    
    # Step 3: Priority-based matching (for ambiguous cases)
    # This handles cases like plain dicts where multiple adapters could match
    # Examples: {"00": 512, "11": 512} could be PennyLane, Qiskit, or Braket counts
    matches = []
    for a in adapters:
        try:
            if a.can_handle(obj, ctx):
                matches.append(a)
        except Exception:
            continue
    if not matches:
        return None
    matches.sort(key=lambda a: (-getattr(a, "priority", 0), getattr(a, "name", "")))
    return matches[0]


def _is_definitive_match(adapter: Adapter, obj: Any, ctx: AdapterContext) -> bool:
    """
    Check if adapter can definitively identify this object as its SDK.
    
    This is more strict than can_handle() - we only return True if the object
    has SDK-specific characteristics (module names, class names) that definitively
    indicate it's from this SDK.
    """
    if not hasattr(obj, "__class__"):
        return False
    
    try:
        module = obj.__class__.__module__
        class_name = obj.__class__.__name__
        
        # Check module name for SDK indicators
        adapter_name = adapter.name.lower()
        
        if adapter_name == "qiskit":
            return module.startswith("qiskit")
        elif adapter_name == "braket":
            return "braket" in module
        elif adapter_name == "cirq":
            return module.startswith("cirq")
        elif adapter_name == "pennylane":
            return "pennylane" in module
        elif adapter_name == "dwave":
            return "dimod" in module or hasattr(obj, "record")
        elif adapter_name == "pyquil":
            return "pyquil" in module or "quil" in module
        
    except Exception:
        pass
    
    return False

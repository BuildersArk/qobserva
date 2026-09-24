from __future__ import annotations

from qobserva.registry import load_adapters, select_adapter
from qobserva.adapters.base import AdapterContext

def test_registry_selects_adapter_with_sdk_tag():
    """Test that SDK tag takes priority in adapter selection (recommended approach)."""
    adapters = load_adapters()
    
    # Test with SDK tag (recommended)
    ctx = AdapterContext(
        project="test",
        tags={"sdk": "pennylane"},  # SDK tag should take priority
        capture_program="hash",
        measurement_key=None,
        benchmark_id=None,
        benchmark_params={},
        started_at_iso="2026-01-06T00:00:00Z",
        ended_at_iso="2026-01-06T00:01:00Z",
        runtime_ms=1000,
        exception=None,
    )
    obj = {"00": 512, "11": 512}  # Counts dict (common PennyLane format)
    adapter = select_adapter(obj, ctx, adapters)
    assert adapter is not None
    assert adapter.name == "pennylane"  # Should select PennyLane adapter due to SDK tag

def test_registry_fallback_without_sdk_tag():
    """Test fallback adapter selection when SDK tag is missing (not recommended)."""
    adapters = load_adapters()
    
    # Test without SDK tag (fallback behavior)
    ctx = AdapterContext(
        project="test",
        tags={},  # No SDK tag - relies on object inspection
        capture_program="hash",
        measurement_key=None,
        benchmark_id=None,
        benchmark_params={},
        started_at_iso="2026-01-06T00:00:00Z",
        ended_at_iso="2026-01-06T00:01:00Z",
        runtime_ms=1000,
        exception=None,
    )
    obj = {"counts": {"00": 1}, "shots": 1}  # Generic counts dict
    adapter = select_adapter(obj, ctx, adapters)
    assert adapter is not None  # Should still find an adapter (fallback)

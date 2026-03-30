from __future__ import annotations

from typing import Any, Dict
from .base import Adapter, AdapterContext
from .version_utils import get_sdk_version

class PyQuilAdapter(Adapter):
    name = "pyquil"
    priority = 50

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        return "pyquil" in obj.__class__.__module__ or isinstance(obj, (list, tuple))

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        histogram = {}
        if isinstance(obj, (list, tuple)):
            for s in obj:
                key = "".join(map(str, s)) if isinstance(s, (list, tuple)) else str(s)
                histogram[key] = histogram.get(key, 0) + 1
        shots = sum(histogram.values()) or 1

        return {
            "sdk": {"name": "pyquil", "version": get_sdk_version("pyquil")},
            "backend": {"provider": "rigetti", "name": "pyquil-backend"},
            "shots": shots,
            "artifacts": {"result_type": "counts", "counts": {"bit_order": "little", "histogram": histogram, "mapping": {}}},
        }

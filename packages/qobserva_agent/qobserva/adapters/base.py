from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass
class AdapterContext:
    project: str
    tags: Dict[str, str]
    capture_program: str
    measurement_key: Optional[str]
    benchmark_id: Optional[str]
    benchmark_params: Dict[str, Any]
    started_at_iso: str
    ended_at_iso: str
    runtime_ms: int
    exception: BaseException | None

class Adapter:
    name: str = "base"
    priority: int = 0

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        raise NotImplementedError

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        raise NotImplementedError

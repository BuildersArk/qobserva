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
    # The job object the user returned when await_result=True (before .result() replaced it).
    # Jobs often know their backend even when the result object does not.
    job: Any = None
    # Backend explicitly passed to @observe_run(backend=...): an SDK backend object or a name.
    backend_hint: Any = None

class Adapter:
    name: str = "base"
    priority: int = 0

    def can_handle(self, obj: Any, context: AdapterContext) -> bool:
        raise NotImplementedError

    def extract(self, obj: Any, context: AdapterContext) -> Dict[str, Any]:
        raise NotImplementedError

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from .models import Run
from .storage import load_analysis_bundle, load_event_bundle

log = logging.getLogger("qobserva_collector")

# Analysis metrics the dashboard charts read for many runs at once.
SUMMARY_METRICS = (
    "qc.circuit.depth_post",
    "qc.quality.success_probability",
    "qc.cost.estimated_usd",
)
# program.benchmark_params values shown on the Algorithm Analytics page.
SUMMARY_BENCHMARK_PARAMS = ("energy", "expected_success_rate", "approximation_ratio")

def _str_or_none(value: Any) -> Optional[str]:
    return value if isinstance(value, str) and value.strip() else None

def run_algorithm(event: Dict[str, Any]) -> Optional[str]:
    tags = event.get("tags") or {}
    return _str_or_none(tags.get("algorithm")) if isinstance(tags, dict) else None

def run_summary(event: Dict[str, Any], analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    The few per-run fields the dashboard aggregates across many runs, so list views can
    get them from /v1/runs?include_summary=true instead of fetching every run's bundle.
    """
    software = event.get("software") or {}
    sdk = software.get("sdk") if isinstance(software, dict) else None
    tags = event.get("tags") or {}
    execution = event.get("execution") or {}
    program = event.get("program") or {}
    params = program.get("benchmark_params") if isinstance(program, dict) else None
    metrics = (analysis or {}).get("metrics") or {}

    return {
        "sdk": (_str_or_none(sdk.get("name")) if isinstance(sdk, dict) else None)
               or (_str_or_none(tags.get("sdk")) if isinstance(tags, dict) else None),
        "runtime_ms": execution.get("runtime_ms") if isinstance(execution, dict) else None,
        "metrics": {k: metrics[k] for k in SUMMARY_METRICS if metrics.get(k) is not None},
        "benchmark_params": {k: params[k] for k in SUMMARY_BENCHMARK_PARAMS
                             if isinstance(params, dict) and params.get(k) is not None},
    }

def dump_summary(summary: Dict[str, Any]) -> str:
    return json.dumps(summary, separators=(",", ":"))

def upgrade_schema(engine: Engine) -> None:
    """
    Add the algorithm/summary columns to databases created by collector 0.1.4 and older,
    then fill them once from the stored bundles.
    """
    columns = {c["name"] for c in inspect(engine).get_columns("runs")}
    with engine.begin() as conn:
        if "algorithm" not in columns:
            conn.execute(text("ALTER TABLE runs ADD COLUMN algorithm VARCHAR(200)"))
        if "summary" not in columns:
            conn.execute(text("ALTER TABLE runs ADD COLUMN summary TEXT"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_runs_algorithm ON runs (algorithm)"))

    with Session(bind=engine) as db:
        pending = db.query(Run).filter(Run.summary.is_(None)).all()
        if not pending:
            return
        log.info("Indexing %d stored runs for the dashboard (one time)...", len(pending))
        for r in pending:
            try:
                event = load_event_bundle(r.artifact_ref)
            except Exception:
                event = {}
            try:
                analysis = load_analysis_bundle(r.analysis_ref)
            except Exception:
                analysis = {}
            r.algorithm = run_algorithm(event)
            r.summary = dump_summary(run_summary(event, analysis))
        db.commit()

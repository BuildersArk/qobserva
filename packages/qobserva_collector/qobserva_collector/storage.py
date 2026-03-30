from __future__ import annotations

import gzip, json
from pathlib import Path
from typing import Any, Dict
from .config import load_config

def _base_dir(project: str, run_id: str) -> Path:
    cfg = load_config()
    base = Path(cfg.data_dir) / "artifacts" / project / run_id
    base.mkdir(parents=True, exist_ok=True)
    return base

def store_event_bundle(project: str, run_id: str, event: Dict[str, Any]) -> str:
    p = _base_dir(project, run_id) / "bundle.json.gz"
    with gzip.open(p, "wt", encoding="utf-8") as f:
        json.dump(event, f)
    return str(p)

def load_event_bundle(path: str) -> Dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return json.load(f)

def store_analysis_bundle(project: str, run_id: str, analysis: Dict[str, Any]) -> str:
    p = _base_dir(project, run_id) / "analysis.json"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(analysis, f, indent=2)
    return str(p)

def load_analysis_bundle(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

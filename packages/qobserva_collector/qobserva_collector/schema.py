from __future__ import annotations

import json, os
from jsonschema import Draft202012Validator
from pathlib import Path

_validator: Draft202012Validator | None = None

def _find_schema_path() -> Path:
    """
    Locate qobserva_run_event.schema.json: (1) bundled next to this module (pip),
    (2) QOBSERVA_SCHEMA_PATH, (3) monorepo repo_root/schema/.
    """
    here = Path(__file__).resolve()

    # 1. Bundled schema (used when installed via pip)
    bundled = here.parent / "schema" / "qobserva_run_event.schema.json"
    if bundled.exists():
        return bundled

    # 2. Explicit override
    env = os.getenv("QOBSERVA_SCHEMA_PATH")
    if env and Path(env).exists():
        return Path(env)

    # 3. Monorepo: packages/qobserva_collector/qobserva_collector -> repo root
    if len(here.parents) >= 4:
        repo_root = here.parents[3]
        p = repo_root / "schema" / "qobserva_run_event.schema.json"
        if p.exists():
            return p

    raise FileNotFoundError(
        "Cannot locate qobserva_run_event.schema.json. Set QOBSERVA_SCHEMA_PATH."
    )

def validate_event_dict(event: dict) -> list[dict]:
    global _validator
    if _validator is None:
        schema = json.loads(_find_schema_path().read_text(encoding="utf-8"))
        _validator = Draft202012Validator(schema)
    errors = []
    for e in sorted(_validator.iter_errors(event), key=str):
        errors.append({"path": "/".join(map(str, e.path)), "message": e.message})
    return errors

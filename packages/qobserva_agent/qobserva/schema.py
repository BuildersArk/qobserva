from __future__ import annotations

import json, os
from pathlib import Path
from jsonschema import Draft202012Validator

_validator: Draft202012Validator | None = None

def _find_schema_path() -> Path:
    """
    Locate the qobserva_run_event.schema.json file.

    Prefer (1) bundle next to this module (pip-installed wheel), then
    (2) QOBSERVA_SCHEMA_PATH, then (3) monorepo layout (walk up for schema/).
    """
    here = Path(__file__).resolve()

    # 1. Bundled schema (used when installed via pip)
    bundled = here.parent / "schema" / "qobserva_run_event.schema.json"
    if bundled.exists():
        return bundled

    # 2. Explicit override via environment variable
    env = os.getenv("QOBSERVA_SCHEMA_PATH")
    if env and Path(env).exists():
        return Path(env)

    # 3. Monorepo: walk up and look for schema/qobserva_run_event.schema.json
    for parent in list(here.parents)[:6]:
        candidate = parent / "schema" / "qobserva_run_event.schema.json"
        if candidate.exists():
            return candidate

    raise FileNotFoundError(
        "Cannot locate qobserva_run_event.schema.json. "
        "Set QOBSERVA_SCHEMA_PATH or ensure the schema is bundled or present."
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

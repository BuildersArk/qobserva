from __future__ import annotations

import gzip, hashlib, json, re
from pathlib import Path
from typing import Any, Dict
from .config import load_config

# Characters that are path separators or invalid in Windows/POSIX file names.
_UNSAFE_CHARS = re.compile(r'[\x00-\x1f<>:"/\\|?*]')
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
_MAX_COMPONENT_LEN = 100

def safe_path_component(name: str) -> str:
    """
    Turn a user-supplied project/run_id into a single, safe directory name.

    Names that are already safe are returned unchanged, so existing on-disk layouts
    stay the same. Anything that could escape the artifacts directory (separators,
    "..", drive letters, reserved device names) is replaced and suffixed with a short
    hash of the original so distinct inputs never collide.
    """
    name = str(name)
    cleaned = _UNSAFE_CHARS.sub("_", name).strip(" .")
    if cleaned.split(".")[0].upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    if not cleaned:
        cleaned = "_"
    if cleaned != name or len(cleaned) > _MAX_COMPONENT_LEN:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        cleaned = f"{cleaned[:_MAX_COMPONENT_LEN]}-{digest}"
    return cleaned

def _artifacts_root() -> Path:
    cfg = load_config()
    return (Path(cfg.data_dir) / "artifacts").resolve()

def _base_dir(project: str, run_id: str) -> Path:
    root = _artifacts_root()
    base = (root / safe_path_component(project) / safe_path_component(run_id)).resolve()
    # Defense in depth: never write outside the artifacts directory.
    if root not in base.parents:
        raise ValueError("Refusing to store artifacts outside the data directory")
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

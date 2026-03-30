from __future__ import annotations

import os
from pathlib import Path
from .config import load_config

def pid_dir() -> Path:
    cfg = load_config()
    p = Path(cfg.data_dir) / ".qobserva_local"
    p.mkdir(parents=True, exist_ok=True)
    return p

def pid_path(name: str) -> Path:
    return pid_dir() / f"{name}.pid"

def write_pid(name: str, pid: int):
    pid_path(name).write_text(str(pid), encoding="utf-8")

def read_pid(name: str) -> int | None:
    p = pid_path(name)
    if not p.exists():
        return None
    try:
        return int(p.read_text(encoding="utf-8").strip())
    except Exception:
        return None

def clear_pid(name: str):
    p = pid_path(name)
    if p.exists():
        p.unlink()

def is_running(pid: int | None) -> bool:
    if not pid or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except Exception:
        return False

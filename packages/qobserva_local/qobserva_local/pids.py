from __future__ import annotations

import json
from pathlib import Path

import psutil

from .config import load_config

def pid_dir() -> Path:
    cfg = load_config()
    p = Path(cfg.data_dir) / ".qobserva_local"
    p.mkdir(parents=True, exist_ok=True)
    return p

def pid_path(name: str) -> Path:
    return pid_dir() / f"{name}.pid"

def write_pid(name: str, pid: int):
    # The start time identifies this exact process: once it exits, the OS may give the
    # same pid to an unrelated program, and `qobserva down` must not stop that one.
    try:
        create_time = psutil.Process(pid).create_time()
    except psutil.Error:
        create_time = None
    pid_path(name).write_text(json.dumps({"pid": pid, "create_time": create_time}), encoding="utf-8")

def _read(name: str) -> dict | None:
    p = pid_path(name)
    if not p.exists():
        return None
    text = p.read_text(encoding="utf-8").strip()
    try:
        data = json.loads(text)
    except ValueError:
        return None
    if isinstance(data, int):  # pid files written by qobserva-local 0.1.3 and older
        return {"pid": data, "create_time": None}
    if isinstance(data, dict) and isinstance(data.get("pid"), int):
        return data
    return None

def read_pid(name: str) -> int | None:
    data = _read(name)
    return data["pid"] if data else None

def clear_pid(name: str):
    p = pid_path(name)
    if p.exists():
        p.unlink()

def is_running(pid: int | None) -> bool:
    return bool(pid and pid > 0 and psutil.pid_exists(pid))

def qobserva_process(name: str) -> psutil.Process | None:
    """
    The process a pid file points at, only if it is still the QObserva process that
    wrote it (same start time), not an unrelated program that reused the pid.
    """
    data = _read(name)
    if not data or data["pid"] <= 0:
        return None
    try:
        proc = psutil.Process(data["pid"])
        if data.get("create_time") is not None:
            return proc if abs(proc.create_time() - data["create_time"]) < 1.0 else None
        # Older pid file without a start time: accept only a process that looks like QObserva.
        return proc if _looks_like_qobserva(proc) else None
    except psutil.Error:
        return None

def _looks_like_qobserva(proc: psutil.Process) -> bool:
    """The collector (uvicorn qobserva_collector...), `qobserva up`, or the dashboard dev server."""
    args = [a.lower() for a in proc.cmdline()]
    if any("qobserva_collector" in a for a in args):
        return True
    names = {Path(a).name.removesuffix(".exe") for a in args}
    if names & {"qobserva", "qobserva-local"} and "up" in args:
        return True
    try:
        return Path(proc.cwd()).name == "qobserva_ui_react"
    except psutil.Error:
        return False

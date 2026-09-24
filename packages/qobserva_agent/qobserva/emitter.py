"""
Background delivery of run events so telemetry never slows down the user's program.

`@observe_run` hands each event to `emit()`, which queues it for a daemon worker thread
and returns immediately. Pending events are flushed when the interpreter exits (bounded
by QOBSERVA_FLUSH_TIMEOUT_S), so short scripts still record their runs. Set
QOBSERVA_ASYNC=0 to send synchronously instead.
"""

from __future__ import annotations

import atexit
import os
import queue
import sys
import threading
import time
from typing import Any, Dict, Optional, Tuple

from .report import report_run

_Item = Tuple[Dict[str, Any], Optional[str], Optional[str]]

_lock = threading.Lock()
_queue: "queue.Queue[_Item]" = queue.Queue()
_worker: threading.Thread | None = None
_worker_pid: int | None = None
_warned = False

def _async_enabled() -> bool:
    return os.getenv("QOBSERVA_ASYNC", "1").strip().lower() not in ("0", "false", "no", "off")

def _flush_timeout_s() -> float:
    try:
        return float(os.getenv("QOBSERVA_FLUSH_TIMEOUT_S", "5"))
    except ValueError:
        return 5.0

def _warn_once(exc: BaseException, endpoint: str | None) -> None:
    """Tell the user (once per process) that telemetry is not reaching the collector."""
    global _warned
    if _warned:
        return
    _warned = True
    target = endpoint or os.getenv("QOBSERVA_ENDPOINT") or "the local collector"
    print(
        f"QObserva: could not record run telemetry to {target} ({type(exc).__name__}: {exc}). "
        "Your program is unaffected. Is the collector running? Start it with `qobserva up`.",
        file=sys.stderr,
    )

def _send(item: _Item) -> None:
    event, endpoint, api_key = item
    try:
        report_run(event, endpoint=endpoint, api_key=api_key)
    except Exception as e:
        _warn_once(e, endpoint)

def _run_worker() -> None:
    while True:
        item = _queue.get()
        try:
            _send(item)
        finally:
            _queue.task_done()

def _ensure_worker() -> None:
    global _worker, _worker_pid
    pid = os.getpid()
    # A forked child inherits the queue but not the thread, so start a fresh worker per process.
    if _worker is not None and _worker.is_alive() and _worker_pid == pid:
        return
    with _lock:
        if _worker is None or not _worker.is_alive() or _worker_pid != pid:
            _worker = threading.Thread(target=_run_worker, name="qobserva-emitter", daemon=True)
            _worker.start()
            _worker_pid = pid

def emit(event: Dict[str, Any], *, endpoint: str | None = None, api_key: str | None = None) -> None:
    """Deliver an event without blocking the caller (unless QOBSERVA_ASYNC=0)."""
    item = (event, endpoint, api_key)
    if not _async_enabled():
        _send(item)
        return
    _ensure_worker()
    _queue.put(item)

def flush(timeout: float | None = None) -> bool:
    """
    Wait until queued events have been delivered (or failed).

    Returns True if the queue drained within `timeout` seconds (default
    QOBSERVA_FLUSH_TIMEOUT_S). Useful in notebooks or tests that read runs back
    from the collector immediately after producing them.
    """
    deadline = time.monotonic() + (_flush_timeout_s() if timeout is None else timeout)
    while _queue.unfinished_tasks:
        if _worker is None or not _worker.is_alive() or _worker_pid != os.getpid():
            return False
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.02)
    return True

atexit.register(flush)

from __future__ import annotations

import importlib
from rich.console import Console
import httpx

from .config import load_config
from .pids import read_pid, is_running

console = Console()

REQUIRED_MODULES = [
    "qobserva",              # agent (package name inside qobserva_agent)
    "qobserva_collector",    # collector
]

def run_doctor():
    cfg = load_config()
    console.print("[bold]QObserva Local Doctor[/bold]")
    console.print(f"Data dir: {cfg.data_dir}")

    for m in REQUIRED_MODULES:
        try:
            importlib.import_module(m)
            console.print(f"✅ import {m}")
        except Exception as e:
            console.print(f"❌ import {m}: {e}")

    cpid = read_pid("collector")
    upid = read_pid("ui")
    console.print(f"Collector pid: {cpid} (running={is_running(cpid)})")
    console.print(f"UI pid: {upid} (running={is_running(upid)})")

    url = f"http://{cfg.collector_host}:{cfg.collector_port}/v1/runs"
    try:
        r = httpx.get(url, timeout=2.0)
        console.print(f"Collector HTTP: {r.status_code} @ {url}")
    except Exception as e:
        console.print(f"Collector HTTP: ❌ {e} @ {url}")

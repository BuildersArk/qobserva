from __future__ import annotations

import time

import typer
from rich.console import Console

from .process import start_collector_native, start_ui_native, wait_for_collector, stop_pid
from .doctor import run_doctor
from .docker_mode import compose_up, compose_down
from .config import load_config

app = typer.Typer(help="Run QObserva local stack (collector + UI) with one command.")
console = Console()

@app.command()
def up(mode: str = "native"):
    """Start collector + React dashboard (blocks until Ctrl+C)."""
    cfg = load_config()
    console.print(f"[bold]Starting QObserva local stack[/bold] (mode={mode})")
    console.print(f"Data dir: {cfg.data_dir}")

    if mode == "docker":
        compose_up()
        console.print("[green]Docker compose up[/green]")
        return

    # native
    cpid = start_collector_native()
    ok = wait_for_collector()
    if ok:
        console.print(f"[green]Collector running[/green] (pid {cpid}) @ http://{cfg.collector_host}:{cfg.collector_port}")
    else:
        console.print("[yellow]Collector started but health-check did not pass yet.[/yellow]")

    upid = start_ui_native()
    console.print(f"[green]React Dashboard running[/green] (pid {upid}) @ http://{cfg.ui_host}:{cfg.ui_port}")
    console.print("[bold cyan]Press Ctrl+C to stop QObserva.[/bold cyan]")

    try:
        # Block so that the static server thread and collector keep running
        while True:
            time.sleep(1.0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopping QObserva local stack (Ctrl+C received).[/yellow]")
        down()

@app.command()
def down(mode: str = "native"):
    """Stop collector + UI."""
    if mode == "docker":
        compose_down()
        console.print("[green]Docker compose down[/green]")
        return

    stop_pid("ui")
    stop_pid("collector")
    console.print("[green]Stopped local processes[/green]")

@app.command()
def doctor():
    """Run environment and health checks."""
    run_doctor()

if __name__ == "__main__":
    app()

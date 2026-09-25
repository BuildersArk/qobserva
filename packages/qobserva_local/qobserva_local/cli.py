from __future__ import annotations

import time

import typer
from rich.console import Console

from .process import (
    port_in_use, qobserva_collector_running,
    start_collector_native, start_ui_native, stop_pid, wait_for_collector,
)
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

    # native: refuse to start a second stack (or on ports another program holds)
    if qobserva_collector_running(cfg.collector_host, cfg.collector_port):
        console.print(f"[yellow]QObserva is already running[/yellow]: collector @ http://{cfg.collector_host}:{cfg.collector_port}, "
                      f"dashboard @ http://{cfg.ui_host}:{cfg.ui_port}")
        console.print("Stop it with [bold]qobserva down[/bold] (or Ctrl+C in the terminal running it), then run qobserva up again.")
        raise typer.Exit(0)
    busy = [f"{name} port {port}" for name, host, port in (
        ("collector", cfg.collector_host, cfg.collector_port), ("dashboard", cfg.ui_host, cfg.ui_port))
        if port_in_use(host, port)]
    if busy:
        console.print(f"[red]Cannot start QObserva: {' and '.join(busy)} already in use by another program.[/red]")
        console.print("Free the port(s), or choose others, e.g. QOBSERVA_COLLECTOR_PORT=8081 and QOBSERVA_UI_PORT=3001 "
                      "(then point your code at the new collector with QOBSERVA_ENDPOINT=http://127.0.0.1:8081/v1/ingest/run-event).")
        raise typer.Exit(1)

    collector = start_collector_native()
    state = wait_for_collector(collector)
    if state == "exited":
        stop_pid("collector")
        console.print(f"[red]The collector exited before it was ready (exit code {collector.returncode}).[/red] "
                      f"See the messages above; if port {cfg.collector_port} is now taken by another program, free it "
                      "or choose another port with QOBSERVA_COLLECTOR_PORT.")
        raise typer.Exit(1)
    if state == "ok":
        console.print(f"[green]Collector running[/green] (pid {collector.pid}) @ http://{cfg.collector_host}:{cfg.collector_port}")
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

    # Collector first: when the dashboard is served by the `qobserva up` process itself,
    # stopping "ui" ends that process.
    stopped = [name for name in ("collector", "ui") if stop_pid(name)]
    if stopped:
        console.print("[green]Stopped local processes[/green]")
    else:
        console.print("No running QObserva processes found.")

@app.command()
def doctor():
    """Run environment and health checks."""
    run_doctor()

if __name__ == "__main__":
    app()

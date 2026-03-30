from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel

# Import local CLI to forward commands
try:
    from qobserva_local.cli import app as local_app
except ImportError:
    local_app = None

app = typer.Typer(
    name="qobserva",
    help="QObserva - Quantum program observability and benchmarking",
    add_completion=False,
)
console = Console()

@app.command()
def up(mode: str = typer.Option("native", help="Mode: native or docker")):
    """Start QObserva (collector + React dashboard) - one command to run everything."""
    console.print(Panel.fit(
        "[bold cyan]QObserva[/bold cyan] - Starting quantum observability stack",
        border_style="cyan"
    ))
    
    if local_app is None:
        console.print("[red]Error: qobserva-local not installed.[/red]")
        console.print("[yellow]Install sub-packages first:[/yellow]")
        console.print("  pip install -e packages/qobserva_agent")
        console.print("  pip install -e packages/qobserva_collector")
        console.print("  pip install -e packages/qobserva_local")
        raise typer.Exit(1)
    
    # Forward to local CLI - call the command directly
    from qobserva_local.cli import up as local_up
    local_up(mode=mode)

@app.command()
def down(mode: str = typer.Option("native", help="Mode: native or docker")):
    """Stop QObserva services."""
    if local_app is None:
        console.print("[red]Error: qobserva-local not installed. Install sub-packages first.[/red]")
        raise typer.Exit(1)
    
    # Forward to local CLI
    from qobserva_local.cli import down as local_down
    local_down(mode=mode)

@app.command()
def doctor():
    """Run health checks and diagnostics."""
    if local_app is None:
        console.print("[red]Error: qobserva-local not installed. Install sub-packages first.[/red]")
        raise typer.Exit(1)
    
    # Forward to local CLI
    from qobserva_local.cli import doctor as local_doctor
    local_doctor()

@app.command()
def version():
    """Show QObserva version."""
    from qobserva import __version__
    console.print(f"[bold]QObserva[/bold] version {__version__}")

if __name__ == "__main__":
    app()

from __future__ import annotations

import json
from pathlib import Path
import typer
from rich.console import Console
from rich.table import Table

from .config import load_config
from .report import report_run

app = typer.Typer(help="QObserva CLI (agent utilities).")
console = Console()

@app.command()
def upload(path: Path, endpoint: str | None = None, api_key: str | None = None):
    data = json.loads(path.read_text(encoding="utf-8"))
    resp = report_run(data, endpoint=endpoint, api_key=api_key)
    console.print(resp)

@app.command()
def config():
    cfg = load_config()
    table = Table(title="QObserva Agent Config")
    table.add_column("key")
    table.add_column("value")
    table.add_row("endpoint", cfg.endpoint)
    table.add_row("capture_program", cfg.capture_program)
    table.add_row("api_key_set", "yes" if cfg.api_key else "no")
    console.print(table)

if __name__ == "__main__":
    app()

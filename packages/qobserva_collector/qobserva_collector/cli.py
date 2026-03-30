from __future__ import annotations

import typer
import uvicorn
from .api import create_app

app = typer.Typer(help="QObserva local collector service.")

@app.command()
def serve(host: str = "127.0.0.1", port: int = 8080):
    uvicorn.run(create_app(), host=host, port=port)

if __name__ == "__main__":
    app()

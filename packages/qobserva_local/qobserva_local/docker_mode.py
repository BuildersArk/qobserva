from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from rich.console import Console

console = Console()

def docker_available() -> bool:
    return shutil.which("docker") is not None

def _get_project_root() -> Path:
    """Find project root (directory containing docker/ folder)."""
    current = Path(__file__).resolve()
    # Go up from qobserva_local/qobserva_local/docker_mode.py
    # to find project root (where docker/ folder is)
    while current.parent != current:
        if (current / "docker" / "docker-compose.yml").exists():
            return current
        current = current.parent
    # Fallback: assume we're in project root
    return Path.cwd()

def compose_up():
    if not docker_available():
        raise RuntimeError("Docker not found on PATH.")
    project_root = _get_project_root()
    compose_file = project_root / "docker" / "docker-compose.yml"
    if not compose_file.exists():
        raise RuntimeError(f"Docker compose file not found: {compose_file}")
    # Change to docker directory for compose
    os.chdir(project_root / "docker")
    try:
        subprocess.check_call(["docker", "compose", "up", "-d"])
        console.print("[green]✓ Docker services started[/green]")
        console.print("  Collector: http://localhost:8080")
        console.print("  UI: http://localhost:3000")
    finally:
        os.chdir(project_root)

def compose_down():
    if not docker_available():
        raise RuntimeError("Docker not found on PATH.")
    project_root = _get_project_root()
    compose_file = project_root / "docker" / "docker-compose.yml"
    if not compose_file.exists():
        raise RuntimeError(f"Docker compose file not found: {compose_file}")
    # Change to docker directory for compose
    os.chdir(project_root / "docker")
    try:
        subprocess.check_call(["docker", "compose", "down"])
        console.print("[green]✓ Docker services stopped[/green]")
    finally:
        os.chdir(project_root)

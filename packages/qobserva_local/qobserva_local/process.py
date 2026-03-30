from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import httpx
from rich.console import Console

from .config import load_config
from .pids import write_pid, read_pid, clear_pid, is_running

console = Console()

def _env_with_data_dir() -> dict:
    cfg = load_config()
    env = os.environ.copy()
    env["QOBSERVA_DATA_DIR"] = cfg.data_dir
    # Keep local-first posture
    return env

def start_collector_native() -> int:
    cfg = load_config()
    existing = read_pid("collector")
    if is_running(existing):
        console.print(f"[yellow]Collector already running (pid {existing}).[/yellow]")
        return existing  # type: ignore

    # Use the entry point directly, or call uvicorn on the app
    # Option 1: Use entry point (if installed): cmd = ["qobserva-collector", "serve", "--host", cfg.collector_host, "--port", str(cfg.collector_port)]
    # Option 2: Use uvicorn directly with the app module
    cmd = [
        sys.executable, "-m", "uvicorn",
        "qobserva_collector.api:create_app",
        "--factory",
        "--host", cfg.collector_host,
        "--port", str(cfg.collector_port)
    ]
    # Allow stdout/stderr for debugging (can redirect to log file in production)
    p = subprocess.Popen(
        cmd, 
        env=_env_with_data_dir(), 
        # stdout and stderr are left as None so they inherit from parent process
        # This allows us to see debug output
    )
    write_pid("collector", p.pid)
    return p.pid

def start_ui_native() -> int:
    cfg = load_config()
    existing = read_pid("ui")
    if is_running(existing):
        console.print(f"[yellow]UI already running (pid {existing}).[/yellow]")
        return existing  # type: ignore

    return start_react_ui(cfg)

def start_react_ui(cfg) -> int:
    """
    Start React dashboard.
    
    Detects environment:
    - Source repo: Uses npm/vite dev server (packages/qobserva_ui_react)
    - PyPI install: Serves bundled static files (qobserva_local/ui_dist)
    """
    current_file = Path(__file__)
    
    # Try source repo first (for development)
    packages_path = current_file.parent.parent.parent  # packages/
    react_ui_path = packages_path / "qobserva_ui_react"
    
    if react_ui_path.exists() and (react_ui_path / "node_modules").exists():
        # Source repo: use Vite dev server
        return _start_vite_dev_server(react_ui_path, cfg)
    
    # PyPI install: serve bundled static files
    # In both dev and installed layouts, process.py and ui_dist are siblings:
    # - Dev: packages/qobserva_local/qobserva_local/process.py + ui_dist/
    # - Wheel: site-packages/qobserva_local/process.py + ui_dist/
    ui_dist_path = current_file.parent / "ui_dist"
    if ui_dist_path.exists() and (ui_dist_path / "index.html").exists():
        return _start_static_server(ui_dist_path, cfg)
    
    # Neither found
    console.print("[red]React UI not found[/red]")
    console.print("[yellow]Options:[/yellow]")
    console.print("  1. Source repo: Ensure packages/qobserva_ui_react exists and run 'npm install'")
    console.print("  2. PyPI install: React UI should be bundled in qobserva-local package")
    raise RuntimeError("React UI not found")

def _start_vite_dev_server(react_ui_path: Path, cfg) -> int:
    """Start Vite dev server (source repo)."""
    env = _env_with_data_dir()
    if sys.platform == "win32":
        cmd = ["cmd.exe", "/c", "npm", "run", "dev", "--", "--host", cfg.ui_host, "--port", str(cfg.ui_port)]
        creation_flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    else:
        cmd = ["npm", "run", "dev", "--", "--host", cfg.ui_host, "--port", str(cfg.ui_port)]
        creation_flags = 0
    
    p = subprocess.Popen(
        cmd,
        cwd=str(react_ui_path),
        env=env,
        creationflags=creation_flags,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )
    write_pid("ui", p.pid)
    time.sleep(3)  # Vite starts faster
    return p.pid

def _start_static_server(ui_dist_path: Path, cfg) -> int:
    """Start HTTP server for static files (PyPI install)."""
    # Use Python's http.server (built-in, no extra dependencies)
    import http.server
    import socketserver
    import threading
    
    class SPAHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(ui_dist_path), **kwargs)
        
        def log_message(self, format, *args):
            # Suppress default logging
            pass
        
        def do_GET(self):
            # Proxy API requests to collector
            if self.path.startswith('/api/'):
                try:
                    collector_url = f"http://{cfg.collector_host}:{cfg.collector_port}{self.path.replace('/api', '/v1')}"
                    resp = httpx.get(collector_url, timeout=5.0)
                    self.send_response(resp.status_code)
                    for k, v in resp.headers.items():
                        if k.lower() not in ('content-encoding', 'transfer-encoding', 'content-length'):
                            self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(resp.content)
                    return
                except Exception:
                    self.send_error(502, "Collector unavailable")
                    return
            
            # Serve static files, fallback to index.html for SPA routing
            if self.path == '/' or not self.path.startswith('/api'):
                # Try to serve the requested file
                file_path = ui_dist_path / self.path.lstrip('/')
                if file_path.is_file() and file_path.exists():
                    return super().do_GET()
                # If file doesn't exist, serve index.html (SPA routing)
                self.path = '/index.html'
            return super().do_GET()
        
        def do_POST(self):
            if self.path.startswith('/api/'):
                try:
                    content_length = int(self.headers.get('Content-Length', 0))
                    body = self.rfile.read(content_length)
                    collector_url = f"http://{cfg.collector_host}:{cfg.collector_port}{self.path.replace('/api', '/v1')}"
                    resp = httpx.post(collector_url, content=body, headers=dict(self.headers), timeout=5.0)
                    self.send_response(resp.status_code)
                    for k, v in resp.headers.items():
                        if k.lower() not in ('content-encoding', 'transfer-encoding', 'content-length'):
                            self.send_header(k, v)
                    self.end_headers()
                    self.wfile.write(resp.content)
                    return
                except Exception:
                    self.send_error(502, "Collector unavailable")
                    return
            return super().do_POST()
    
    def run_server():
        try:
            with socketserver.TCPServer((cfg.ui_host, cfg.ui_port), SPAHandler) as httpd:
                console.print(f"[green]Static server started[/green] @ http://{cfg.ui_host}:{cfg.ui_port}")
                httpd.serve_forever()
        except Exception as e:
            console.print(f"[red]Static server error:[/red] {e}")
            raise
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # Store thread ID as "pid" (not perfect but works for our use case)
    fake_pid = server_thread.ident or 99999
    write_pid("ui", fake_pid)
    time.sleep(2)  # Give server more time to start and bind
    
    # Verify server is actually listening
    try:
        test_url = f"http://{cfg.ui_host}:{cfg.ui_port}"
        resp = httpx.get(test_url, timeout=2.0)
        console.print(f"[green]Static server verified[/green] - responded with status {resp.status_code}")
    except Exception as e:
        console.print(f"[yellow]Warning: Could not verify static server:[/yellow] {e}")
        console.print(f"[yellow]UI dist path:[/yellow] {ui_dist_path}")
        console.print(f"[yellow]UI dist exists:[/yellow] {ui_dist_path.exists()}")
    
    return fake_pid

def wait_for_collector(timeout_s: float = 15.0) -> bool:
    cfg = load_config()
    url = f"http://{cfg.collector_host}:{cfg.collector_port}/v1/runs"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        try:
            r = httpx.get(url, timeout=1.5)
            if r.status_code in (200, 401, 403):  # token may be enabled
                return True
        except Exception:
            pass
        time.sleep(0.25)
    return False

def stop_pid(name: str):
    pid = read_pid(name)
    if not pid:
        return
    try:
        os.kill(pid, 15)
        time.sleep(0.5)
    except Exception:
        pass
    if is_running(pid):
        try:
            os.kill(pid, 9)
        except Exception:
            pass
    clear_pid(name)

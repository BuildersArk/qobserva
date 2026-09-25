from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

import httpx
import psutil
from rich.console import Console

from .config import load_config
from .pids import write_pid, clear_pid, qobserva_process

console = Console()

def _env_with_data_dir() -> dict:
    cfg = load_config()
    env = os.environ.copy()
    env["QOBSERVA_DATA_DIR"] = cfg.data_dir
    # Keep local-first posture
    return env

def _collector_auth_headers() -> dict:
    """The dashboard proxy authenticates to the collector when QOBSERVA_LOCAL_TOKEN is set."""
    token = os.getenv("QOBSERVA_LOCAL_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}

def start_collector_native() -> subprocess.Popen:
    cfg = load_config()

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
    return p

def start_ui_native() -> int:
    cfg = load_config()
    existing = qobserva_process("ui")
    if existing is not None and existing.pid != os.getpid():
        console.print(f"[yellow]UI already running (pid {existing.pid}).[/yellow]")
        return existing.pid

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
    import threading

    class DashboardServer(http.server.ThreadingHTTPServer):
        # One thread per connection: a single idle browser connection (e.g. a preconnect
        # that never sends a request) must not block every other request.
        daemon_threads = True
        # Keep the socketserver default: on Windows, address reuse would let a second
        # server bind the same port.
        allow_reuse_address = False

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
                    resp = httpx.get(collector_url, headers=_collector_auth_headers(), timeout=5.0)
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
                    resp = httpx.post(collector_url, content=body, headers={**dict(self.headers), **_collector_auth_headers()}, timeout=5.0)
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
            with DashboardServer((cfg.ui_host, cfg.ui_port), SPAHandler) as httpd:
                console.print(f"[green]Static server started[/green] @ http://{cfg.ui_host}:{cfg.ui_port}")
                httpd.serve_forever()
        except Exception as e:
            console.print(f"[red]Static server error:[/red] {e}")
            raise
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    # The dashboard is served by a thread of this `qobserva up` process, so this process's
    # pid is what `qobserva down` (run from another terminal) must stop.
    ui_pid = os.getpid()
    write_pid("ui", ui_pid)
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
    
    return ui_pid

def port_in_use(host: str, port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def qobserva_collector_running(host: str, port: int) -> bool:
    try:
        return httpx.get(f"http://{host}:{port}/v1/health", timeout=1.5).json().get("status") == "ok"
    except Exception:
        return False

def _process_tree_pids(pid: int) -> set[int]:
    """pid plus its descendants (on Windows a venv's python.exe runs the real interpreter as a child)."""
    try:
        return {pid, *(c.pid for c in psutil.Process(pid).children(recursive=True))}
    except psutil.Error:
        return {pid}

def wait_for_collector(proc: subprocess.Popen, timeout_s: float = 30.0) -> str:
    """
    Wait until the collector *this* `qobserva up` started answers its health check.

    Returns "ok", "exited" (the process ended, e.g. another program took the port first),
    or "timeout". A different collector answering on the port does not count.
    """
    cfg = load_config()
    url = f"http://{cfg.collector_host}:{cfg.collector_port}/v1/health"
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if proc.poll() is not None:
            return "exited"
        try:
            health = httpx.get(url, timeout=1.5).json()
            if health.get("status") == "ok" and health.get("pid") in _process_tree_pids(proc.pid):
                return "ok"
        except Exception:
            pass
        time.sleep(0.25)
    return "exited" if proc.poll() is not None else "timeout"

def stop_pid(name: str) -> bool:
    """Stop the QObserva process recorded in a pid file. Returns True if one was stopped."""
    proc = qobserva_process(name)
    clear_pid(name)
    if proc is None:
        # No pid file, the process already ended, or the pid now belongs to another program.
        return False
    if proc.pid == os.getpid():
        # Ctrl+C in `qobserva up`: this process is exiting anyway.
        return False
    try:
        procs = [proc, *proc.children(recursive=True)]
    except psutil.Error:
        procs = [proc]
    for p in procs:
        try:
            p.terminate()
        except psutil.Error:
            pass
    _, alive = psutil.wait_procs(procs, timeout=3)
    for p in alive:
        try:
            p.kill()
        except psutil.Error:
            pass
    return True

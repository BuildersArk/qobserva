"""`qobserva up` / `qobserva down` only act on the QObserva processes they started."""

from __future__ import annotations

import json
import subprocess
import sys
import time
from urllib.parse import urlparse

import psutil
import pytest

from qobserva_local import pids, process

def _sleeper(seconds: int = 30) -> subprocess.Popen:
    """An unrelated program (not QObserva)."""
    return subprocess.Popen([sys.executable, "-c", f"import time; time.sleep({seconds})"])

@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("QOBSERVA_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"

def test_pid_file_records_start_time(data_dir):
    pids.write_pid("collector", psutil.Process().pid)
    data = json.loads(pids.pid_path("collector").read_text())
    assert data["pid"] == psutil.Process().pid
    assert data["create_time"] == pytest.approx(psutil.Process().create_time())
    assert pids.qobserva_process("collector").pid == psutil.Process().pid

def test_down_leaves_a_reused_pid_alone(data_dir):
    other = _sleeper()
    try:
        # The pid file says QObserva started at another time: the pid now belongs to another program.
        pids.pid_path("collector").write_text(json.dumps({"pid": other.pid, "create_time": 1_000_000.0}))
        assert pids.qobserva_process("collector") is None
        assert process.stop_pid("collector") is False
        assert other.poll() is None, "an unrelated process was stopped"
        assert not pids.pid_path("collector").exists(), "stale pid file should be removed"
    finally:
        other.kill()

def test_down_leaves_unrelated_process_from_old_style_pid_file_alone(data_dir):
    other = _sleeper()
    try:
        pids.pid_path("ui").write_text(str(other.pid))  # qobserva-local 0.1.3 format
        assert process.stop_pid("ui") is False
        assert other.poll() is None
    finally:
        other.kill()

def test_down_stops_the_recorded_process(data_dir):
    proc = _sleeper()
    pids.write_pid("collector", proc.pid)
    assert process.stop_pid("collector") is True
    proc.wait(timeout=10)
    assert not pids.pid_path("collector").exists()

def test_up_waits_for_its_own_collector_not_another_one(collector, data_dir, monkeypatch):
    """Another collector answering on the port must not count as the one `up` started."""
    port = urlparse(collector).port
    monkeypatch.setenv("QOBSERVA_COLLECTOR_PORT", str(port))

    # Our "collector" dies right away, as uvicorn does when the port is already taken.
    ours = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(1); raise SystemExit(1)"])
    t0 = time.time()
    assert process.wait_for_collector(ours, timeout_s=15) == "exited"
    assert time.time() - t0 < 10

    # Still alive but never answering: timeout, not "ok".
    alive = _sleeper()
    try:
        assert process.wait_for_collector(alive, timeout_s=2) == "timeout"
    finally:
        alive.kill()

def test_up_accepts_the_collector_it_started(data_dir, monkeypatch):
    from conftest import free_port
    port = free_port()
    monkeypatch.setenv("QOBSERVA_COLLECTOR_PORT", str(port))
    proc = process.start_collector_native()
    try:
        assert process.wait_for_collector(proc, timeout_s=60) == "ok"
        assert pids.qobserva_process("collector") is not None
    finally:
        assert process.stop_pid("collector") is True
        proc.wait(timeout=10)

def test_dashboard_server_answers_while_another_connection_is_idle(tmp_path, data_dir, monkeypatch):
    """An idle browser connection (e.g. Chrome's preconnect) must not block the dashboard."""
    import socket
    from types import SimpleNamespace

    import httpx
    from conftest import free_port

    ui = tmp_path / "ui_dist"
    ui.mkdir()
    (ui / "index.html").write_text("<html>ok</html>")
    port = free_port()
    cfg = SimpleNamespace(ui_host="127.0.0.1", ui_port=port, collector_host="127.0.0.1", collector_port=free_port())
    monkeypatch.setattr(process, "write_pid", lambda *a: None)
    process._start_static_server(ui, cfg)

    idle = socket.create_connection(("127.0.0.1", port))  # connects, never sends a request
    try:
        assert httpx.get(f"http://127.0.0.1:{port}/", timeout=5).status_code == 200
    finally:
        idle.close()

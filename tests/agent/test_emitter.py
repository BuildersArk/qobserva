from __future__ import annotations

import socket
import subprocess
import sys
import textwrap
import threading
import time

import httpx
import pytest

from conftest import free_port

@pytest.fixture
def unresponsive_endpoint():
    """A TCP server that accepts connections but never answers (a hung collector)."""
    srv = socket.socket()
    srv.bind(("127.0.0.1", 0))
    srv.listen(16)
    conns = []
    stop = threading.Event()

    def accept():
        srv.settimeout(0.1)
        while not stop.is_set():
            try:
                conns.append(srv.accept()[0])
            except OSError:
                pass

    t = threading.Thread(target=accept, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.getsockname()[1]}/v1/ingest/run-event"
    stop.set()
    t.join()
    for c in conns:
        c.close()
    srv.close()

def test_decorated_function_does_not_wait_for_a_hung_collector(unresponsive_endpoint, monkeypatch):
    from qobserva import observe_run

    monkeypatch.setenv("QOBSERVA_TIMEOUT_S", "10")

    @observe_run(project="emitter", tags={"sdk": "qiskit"}, endpoint=unresponsive_endpoint)
    def run():
        return {"counts": {"00": 3, "11": 5}}

    t0 = time.monotonic()
    assert run() == {"counts": {"00": 3, "11": 5}}
    assert time.monotonic() - t0 < 1.0

def test_runs_are_delivered_and_flush_waits_for_them(collector):
    from qobserva import flush, observe_run

    @observe_run(project="emitter", tags={"sdk": "qiskit"}, endpoint=f"{collector}/v1/ingest/run-event")
    def run():
        return {"counts": {"00": 3, "11": 5}}

    for _ in range(3):
        run()
    assert flush(timeout=10)
    runs = httpx.get(f"{collector}/v1/runs", params={"project": "emitter"}).json()
    assert len(runs) == 3 and all(r["shots"] == 8 for r in runs)

def test_short_script_still_records_its_run_on_exit(collector):
    script = textwrap.dedent(f"""
        from qobserva import observe_run
        @observe_run(project="exit_flush", tags={{"sdk": "qiskit"}}, endpoint="{collector}/v1/ingest/run-event")
        def run():
            return {{"counts": {{"0": 1}}}}
        run()
    """)
    subprocess.run([sys.executable, "-c", script], check=True, timeout=60)
    runs = httpx.get(f"{collector}/v1/runs", params={"project": "exit_flush"}).json()
    assert len(runs) == 1

def test_user_is_told_once_when_collector_is_unreachable():
    port = free_port()  # nothing listening
    script = textwrap.dedent(f"""
        from qobserva import observe_run
        @observe_run(project="p", tags={{"sdk": "qiskit"}}, endpoint="http://127.0.0.1:{port}/v1/ingest/run-event")
        def run():
            return {{"counts": {{"0": 1}}}}
        run(); run()
        print("user code finished")
    """)
    t0 = time.monotonic()
    p = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "user code finished" in p.stdout
    assert p.stderr.count("could not record run telemetry") == 1
    assert time.monotonic() - t0 < 30

def test_sync_mode_sends_before_returning(collector, monkeypatch):
    from qobserva import observe_run

    monkeypatch.setenv("QOBSERVA_ASYNC", "0")

    @observe_run(project="sync", tags={"sdk": "qiskit"}, endpoint=f"{collector}/v1/ingest/run-event")
    def run():
        return {"counts": {"1": 2}}

    run()
    assert len(httpx.get(f"{collector}/v1/runs", params={"project": "sync"}).json()) == 1

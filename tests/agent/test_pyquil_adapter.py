"""pyQuil adapter against a real Rigetti QVM (skipped when pyQuil or the QVM/quilc servers are unavailable).

Start the servers with:
  docker run -d -p 5000:5000 rigetti/qvm -S
  docker run -d -p 5555:5555 rigetti/quilc -R
"""

from __future__ import annotations

import socket

import httpx
import pytest

pytest.importorskip("pyquil")

def _listening(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0

if not (_listening(5000) and _listening(5555)):
    pytest.skip("Rigetti QVM (5000) and quilc (5555) servers are not running", allow_module_level=True)

from pyquil import Program, get_qc  # noqa: E402
from pyquil.gates import CNOT, H, MEASURE  # noqa: E402

def bell_program(shots: int = 1024) -> Program:
    p = Program()
    ro = p.declare("ro", "BIT", 2)
    p += H(0)
    p += CNOT(0, 1)
    p += MEASURE(0, ro[0])
    p += MEASURE(1, ro[1])
    p.wrap_in_numshots_loop(shots)
    return p

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        observe_run(project="pyquil", tags={"sdk": "pyquil"},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def test_qvm_execution_result_is_recorded(record):
    qc = get_qc("2q-qvm")
    ev = record(lambda: qc.run(qc.compile(bell_program())))
    hist = ev["artifacts"]["counts"]["histogram"]
    assert set(hist) <= {"00", "11"} and sum(hist.values()) == 1024
    assert ev["execution"]["shots"] == 1024
    assert ev["backend"] == {"provider": "local_sim", "name": "qvm"}

def test_quantum_computer_passed_as_backend(record):
    qc = get_qc("2q-qvm")
    ev = record(lambda: qc.run(qc.compile(bell_program())), backend=qc)
    assert ev["backend"] == {"provider": "local_sim", "name": "2q-qvm"}

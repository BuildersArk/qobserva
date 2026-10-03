"""Braket adapter against the real Braket LocalSimulator (skipped when Braket is not installed)."""

from __future__ import annotations

import httpx
import pytest

pytest.importorskip("braket.circuits")
from braket.circuits import Circuit  # noqa: E402
from braket.devices import LocalSimulator  # noqa: E402

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        observe_run(project="braket", tags={"sdk": "braket"},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

def test_local_simulator_counts_and_backend(record):
    bell = Circuit().h(0).cnot(0, 1)
    ev = record(lambda: LocalSimulator().run(bell, shots=1024).result())

    hist = ev["artifacts"]["counts"]["histogram"]
    assert set(hist) <= {"00", "11"} and sum(hist.values()) == 1024
    assert ev["execution"]["shots"] == 1024
    assert ev["execution"]["status"] == "success"
    assert ev["backend"]["provider"] == "local_sim"
    assert ev["backend"]["name"] == "LocalSimulator"

# --- Found in the 2026-10-03 SV1 live run ---------------------------------------------------------
# The ARNs below have the shape of that run's real ones, with AWS's documented example account id
# (123456789012) in place of the real account.
_SV1 = "arn:aws:braket:::device/quantum-simulator/amazon/sv1"
_TASK = "arn:aws:braket:us-east-1:123456789012:quantum-task/70c8a419-41bc-4265-a1b8-61fe2bc1e8e1"

def test_circuit_is_read_from_the_result_without_circuit_param(record):
    """Each Braket result carries the OpenQASM program the device ran; metrics come from it."""
    bell = Circuit().h(0).cnot(0, 1)
    ev = record(lambda: LocalSimulator().run(bell, shots=100).result())

    cm = ev["program"]["circuit_metrics"]
    assert cm["source"] == "result"
    # Same numbers as circuit=bell gives: the result's explicit measurements are not counted as depth.
    assert cm["num_qubits"] == 2 and cm["depth_post"] == bell.depth == 2 and cm["two_qubit_gate_count_post"] == 1
    assert cm["gate_counts"] == {"H": 1, "CNot": 1}
    assert "cnot q[0], q[1];" in ev["program"]["circuit"]["source"]["text"]
    assert "provider_job" not in ev["execution"]  # local tasks have no AWS task to look up

def test_expectation_circuit_is_read_from_the_result(record):
    from braket.circuits import Observable
    circ = Circuit().h(0).cnot(0, 1).expectation(Observable.Z() @ Observable.Z(), target=[0, 1])
    ev = record(lambda: LocalSimulator().run(circ, shots=0).result())
    cm = ev["program"]["circuit_metrics"]
    assert cm["source"] == "result" and cm["two_qubit_gate_count_post"] == 1
    assert "expectation" in ev["program"]["circuit"]["source"]["text"]

def test_aws_task_arn_is_the_provider_job():
    from braket.task_result import TaskMetadata
    from qobserva.adapters.braket_adapter import provider_job_info

    # A real result; its task metadata is set to an SV1 task's (the local simulator's has a plain id).
    result = LocalSimulator().run(Circuit().h(0).cnot(0, 1), shots=10).result()
    assert provider_job_info(result) is None
    result.task_metadata = TaskMetadata(id=_TASK, shots=100, deviceId=_SV1, createdAt="2026-10-03T19:32:41.049Z")
    assert provider_job_info(result) == {"job_id": "70c8a419-41bc-4265-a1b8-61fe2bc1e8e1", "arn": _TASK,
                                         "provider": "aws_braket", "region": "us-east-1",
                                         "device": _SV1, "created": "2026-10-03T19:32:41.049Z"}

def test_unfinished_simulator_task_has_no_cost_yet():
    """Braket's Tracker prices a simulator task at $0 until it finishes; record "not known" instead."""
    from braket.tracking import Tracker
    from braket.tracking.tracking_events import _TaskCreationEvent
    from qobserva.adapters.braket_adapter import _tracked_cost

    tracker = Tracker()
    tracker.receive_event(_TaskCreationEvent(arn=_TASK, shots=100, is_job_task=False, device=_SV1))
    cost = _tracked_cost(tracker)
    assert cost["estimated_cost"] is None
    assert "not finished" in cost["provider_cost_breakdown"]["error"]
    assert cost["provider_cost_breakdown"]["tasks"][_SV1]["tasks"] == {"CREATED": 1}

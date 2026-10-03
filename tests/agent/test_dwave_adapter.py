"""D-Wave adapter against real dimod samplers (skipped when dimod is not installed)."""

from __future__ import annotations

import httpx
import pytest

dimod = pytest.importorskip("dimod")

@pytest.fixture
def record(collector, monkeypatch):
    monkeypatch.setenv("QOBSERVA_ASYNC", "0")
    from qobserva import observe_run

    def _record(fn, **decorator_kwargs):
        observe_run(project="dwave", tags={"sdk": "dwave"},
                    endpoint=f"{collector}/v1/ingest/run-event", **decorator_kwargs)(fn)()
        run = httpx.get(f"{collector}/v1/runs", params={"limit": 1}).json()[0]
        return httpx.get(f"{collector}/v1/runs/{run['run_id']}").json()
    return _record

BQM = dimod.BinaryQuadraticModel.from_qubo({(0, 0): -1, (0, 1): 1, (1, 2): 1})

def test_local_solver_is_not_labeled_as_dwave_hardware(record):
    ev = record(lambda: dimod.ExactSolver().sample(BQM))
    assert ev["backend"] == {"provider": "unknown", "name": "unknown"}
    assert ev["artifacts"]["energies"]["value"] == -1.0

def test_sampler_passed_as_backend(record):
    solver = dimod.ExactSolver()
    ev = record(lambda: solver.sample(BQM), backend=solver)
    assert ev["backend"] == {"provider": "local_sim", "name": "ExactSolver"}

def test_backend_composite_is_described_by_the_sampler_it_wraps():
    """backend=EmbeddingComposite(child) names the child that runs the problem, not the composite."""
    dimod = pytest.importorskip("dimod")
    samplers = pytest.importorskip("dwave.samplers")
    system = pytest.importorskip("dwave.system")
    from qobserva.adapters.dwave_adapter import describe_sampler

    structured = dimod.StructureComposite(samplers.SimulatedAnnealingSampler(), [0, 1], [(0, 1)])

    assert describe_sampler(system.EmbeddingComposite(structured)) == \
        {"provider": "local_sim", "name": "SimulatedAnnealingSampler"}

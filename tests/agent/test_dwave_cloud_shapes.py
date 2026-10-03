"""
D-Wave cloud result shapes, without D-Wave hardware (a trial Leap account gets no Solver API token).

Sources, so it is clear what each test does and does not prove:
- Timing values are D-Wave's published examples: QPU timing from
  https://docs.dwavequantum.com/en/latest/quantum_research/operation_timing.html, hybrid BQM info from D-Wave's
  hybrid solver docs, and the nonlinear (Stride) run_time from
  https://docs.dwavequantum.com/en/latest/industrial_optimization/leap_hybrid.html. Units are microseconds.
- Where each field sits (info["timing"] for QPU, the top level of info for hybrid BQM, a nested "timing" for
  the nonlinear solver, problem_id added to every cloud result) follows the installed dwave-cloud-client and
  dwave-system source.
- One real saved QPU output: the OpenJij tutorial notebook's printed sampleset.info (see OPENJIJ_QPU_INFO).
- Samples and energies come from solving the problem locally (dimod.ExactSolver); only info is taken from
  the published examples. MockDWaveSampler results are simulated by Ocean itself.
These tests check QObserva's parsing of real result shapes; they are not evidence of a hardware run.
"""

from __future__ import annotations

import pytest

dimod = pytest.importorskip("dimod")

# Published by D-Wave (operation_timing page): print(sampleset.info["timing"])
PUBLISHED_QPU_TIMING = {
    "qpu_sampling_time": 80.78, "qpu_anneal_time_per_sample": 20.0, "qpu_readout_time_per_sample": 39.76,
    "qpu_access_time": 16016.18, "qpu_access_overhead_time": 10426.82, "qpu_programming_time": 15935.4,
    "qpu_delay_time_per_sample": 21.02, "total_post_processing_time": 809.0, "post_processing_overhead_time": 809.0,
}
# Published by D-Wave (LeapHybridSampler docs): sampleset.info of a hybrid BQM problem
PUBLISHED_HYBRID_BQM_INFO = {"qpu_access_time": 41990, "charge_time": 2991424, "run_time": 2991424}
# Published by D-Wave (Stride solver docs): results.result().info["timing"]["run_time"]
PUBLISHED_NL_RUN_TIME = 5024685


def _local_sampleset(info):
    bqm = dimod.BinaryQuadraticModel({"a": -1, "b": -1}, {("a", "b"): 2}, 0, "BINARY")
    ss = dimod.ExactSolver().sample(bqm)
    return dimod.SampleSet(ss.record, ss.variables, info, ss.vartype)


def _extract(sampleset, backend=None):
    from qobserva.adapters.base import AdapterContext
    from qobserva.adapters.dwave_adapter import DWaveAdapter
    ctx = AdapterContext(project="t", tags={"sdk": "dwave"}, capture_program="full", measurement_key=None,
                         benchmark_id=None, benchmark_params={}, started_at_iso="", ended_at_iso="",
                         runtime_ms=0, exception=None, backend_hint=backend)
    return DWaveAdapter().extract(sampleset, ctx)


def test_qpu_timing_and_problem_id():
    # problem_id: the published example shows none, so this is a placeholder in the documented position
    out = _extract(_local_sampleset({"timing": dict(PUBLISHED_QPU_TIMING), "problem_id": "PLACEHOLDER-ID"}))

    ru = out["execution"]["resource_usage"]
    assert ru["qpu_time_s"] == pytest.approx(0.01601618)
    assert ru["qpu_programming_time_s"] == pytest.approx(0.0159354)
    assert ru["qpu_sampling_time_s"] == pytest.approx(0.00008078)
    assert ru["post_processing_time_s"] == pytest.approx(0.000809)
    assert ru["stages"]["qpu_anneal_time_per_sample"] == 20.0
    assert out["execution"]["provider_job"] == {"job_id": "PLACEHOLDER-ID", "provider": "dwave"}
    assert out["backend"]["provider"] == "dwave"  # a cloud result: it carries a problem_id

def test_hybrid_bqm_top_level_timing():
    out = _extract(_local_sampleset({**PUBLISHED_HYBRID_BQM_INFO, "problem_id": "PLACEHOLDER-ID"}))

    ru = out["execution"]["resource_usage"]
    assert ru["qpu_time_s"] == pytest.approx(0.04199)
    assert ru["charge_time_s"] == pytest.approx(2.991424)
    assert ru["run_time_s"] == pytest.approx(2.991424)
    assert out["backend"]["provider"] == "dwave"

def test_nonlinear_solver_nested_timing():
    from qobserva.adapters.dwave_adapter import _dwave_timing_to_resource_usage
    ru = _dwave_timing_to_resource_usage({"run_time": PUBLISHED_NL_RUN_TIME}, {"problem_id": "PLACEHOLDER-ID"})
    assert ru["run_time_s"] == pytest.approx(5.024685)

def test_mock_dwave_sampler_is_local_when_passed_as_backend():
    """MockDWaveSampler imitates QPU results (problem_id, QPU timing); with backend= it is labeled local."""
    system = pytest.importorskip("dwave.system")
    from dwave.system.testing import MockDWaveSampler
    mock = MockDWaveSampler()
    ss = system.EmbeddingComposite(mock).sample(
        dimod.BinaryQuadraticModel({}, {("a", "b"): 1}, 0, "SPIN"), num_reads=10)

    out = _extract(ss, backend=system.EmbeddingComposite(mock))

    assert out["backend"] == {"provider": "local_sim", "name": "MockDWaveSampler"}
    assert out["execution"]["provider_job"]["job_id"] == ss.info["problem_id"]  # the mock's simulated id

# Real saved output of a D-Wave QPU run, published in the OpenJij tutorial notebook
# https://github.com/OpenJij/OpenJijTutorial/blob/master/source/en/004-DWaveOceanSDK.ipynb (cell 115).
# It includes legacy timing keys (total_real_time, run_time_chip, ...) next to the current ones.
OPENJIJ_QPU_INFO = {
    "timing": {"qpu_sampling_time": 314960, "qpu_anneal_time_per_sample": 20, "qpu_readout_time_per_sample": 274,
               "qpu_access_time": 324337, "qpu_access_overhead_time": 1875, "qpu_programming_time": 9377,
               "qpu_delay_time_per_sample": 21, "total_post_processing_time": 18907,
               "post_processing_overhead_time": 18907, "total_real_time": 324337, "run_time_chip": 314960,
               "anneal_time_per_run": 20, "readout_time_per_run": 274},
    "problem_id": "ac673401-ba8e-4a86-a7ef-b9037f882250",
}

def test_real_published_qpu_run_output():
    out = _extract(_local_sampleset({"timing": dict(OPENJIJ_QPU_INFO["timing"]),
                                     "problem_id": OPENJIJ_QPU_INFO["problem_id"]}))

    ru = out["execution"]["resource_usage"]
    assert ru["qpu_time_s"] == pytest.approx(0.324337)
    assert ru["qpu_programming_time_s"] == pytest.approx(0.009377)
    assert ru["stages"]["run_time_chip"] == 314960  # legacy keys are kept, not dropped
    assert out["execution"]["provider_job"] == {"job_id": "ac673401-ba8e-4a86-a7ef-b9037f882250", "provider": "dwave"}
    assert out["backend"]["provider"] == "dwave"

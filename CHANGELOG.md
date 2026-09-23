# Changelog

## 0.1.6 (qobserva 0.1.6 · qobserva-agent 0.1.2 · qobserva-collector 0.1.4 · qobserva-local 0.1.3)

### Security and privacy
- **Collector:** untrusted `project` and `run_id` values can no longer write outside the data directory. Names that were already safe keep the same folder layout.
- **Collector:** browser access is limited to local pages (`localhost` / `127.0.0.1`), and writes from any other website are refused, so web pages you visit can't write to your collector. Configure with `QOBSERVA_CORS_ORIGINS`.
- **Collector:** when `QOBSERVA_LOCAL_TOKEN` is set, read endpoints require the token too, not just ingestion. `qobserva up` passes the token through its dashboard proxy.
- **Agent:** error messages are stored with secret *values* redacted (API keys, tokens, passwords, bearer headers, URL credentials, AWS keys, IBM Quantum tokens). Before this release, secret values were stored as-is.
- **Agent:** the machine's hostname is recorded as a stable hash by default. Set `QOBSERVA_HOST_MODE=raw` for the old behavior or `none` to omit it.

### Reliability
- **Agent:** telemetry is sent in the background, so the decorated function no longer waits for the collector. Before, an unreachable collector added up to 10s per run. Pending runs are flushed at exit, and `qobserva.flush()` is available for notebooks and tests. `QOBSERVA_ASYNC=0` restores synchronous sending.
- **Agent:** if the collector can't be reached, QObserva prints one warning instead of failing silently.
- **Packaging:** `qobserva` and `qobserva-agent` no longer overwrite each other's `cli.py` or the `qobserva` command. Before, reinstalling `qobserva-agent` could remove `qobserva up`. The agent's utility CLI is now `qobserva-agent`.
- **Collector / local:** reported versions now come from the installed packages instead of stale hardcoded strings.

### Correct backend labels
- **Qiskit:** runs are no longer labeled `ibm` / `qiskit-backend` by default. Labels come from what Qiskit actually reports:
  - Aer: `local_sim` / `aer_simulator`
  - IBM Runtime fake backends: `local_sim` / e.g. `fake_manila`
  - Real IBM backends: `ibm` / device name, when the job is returned with `await_result=True`
  - Otherwise `unknown`
- **Qiskit:** counts are now read from classical registers with custom names (e.g. `ClassicalRegister(2, "cr")`).
- **pyQuil:** pyQuil 4 `QAMExecutionResult` objects are now supported. Before, real QVM/QPU runs recorded an empty histogram. The QVM is labeled `local_sim` and the QPU `rigetti`.
- **Cirq:** bitstrings keep their leading zeros. Before, `|00>` was recorded as `"0"`, which split histograms and made success-probability metrics wrong for any outcome starting with 0.
- **PennyLane:** counts and expectation values are recorded again. Current PennyLane returns NumPy numbers (e.g. `int64` counts), which the adapter rejected, so runs were stored with an empty histogram.
- **D-Wave:** local samplers (`ExactSolver`, simulated annealing, …) are no longer labeled `dwave` / `dwave-sampler`, which implied D-Wave hardware. Runs with D-Wave cloud job details are labeled `dwave`. Pass the sampler as `backend=` to record its name.
- **Braket:** AWS-managed simulators (SV1, DM1, TN1) are labeled `aws_braket` instead of `local_sim`.
- **New:** `@observe_run(backend=..., provider=...)` records the backend when the SDK result doesn't include it. `backend` accepts a backend object or a name.

### Python support (verified September 2026)
Each SDK's example was run on Windows and the recorded run checked:
- **Python 3.14:** Qiskit, Braket, Cirq, PennyLane and D-Wave all work. **Braket now supports 3.14**; the earlier Pydantic v1 limitation no longer applies to amazon-braket-sdk 1.127.1.
- **Python 3.13:** same five SDKs work.
- **pyQuil:** works on 3.12. Current pyQuil releases require Python 3.11–3.12, so the `pyquil` extra is skipped on 3.13+. Before this change, pip installed an old pyQuil there that fails on import.

### Examples and docs
- The pyQuil example no longer substitutes randomly generated results when the QVM is unavailable. It now fails, and QObserva records the run as failed.
- The API reference documents all environment variables and Qiskit labeling behavior.

### Tests and CI
- CI now runs the test suite on Python 3.10–3.14 (Linux) and 3.12 (Windows), Qiskit adapter tests against real Qiskit/Aer/IBM Runtime, pyQuil adapter tests against Rigetti's QVM, and a dashboard build.

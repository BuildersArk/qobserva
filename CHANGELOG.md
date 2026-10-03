# Changelog

## 0.1.8 (qobserva 0.1.8 · qobserva-agent 0.1.3 · qobserva-collector 0.1.6 · qobserva-local 0.1.5)

### Behavior change: the circuit is recorded by default
`@observe_run` now records the circuit that ran as OpenQASM 3/2 (Quil for pyQuil) plus a text diagram, in addition to
its metrics. The default `capture_program` changed from `"hash"` to `"full"`. Run data goes only to the collector you
configure (local by default). Use `capture_program="hash"` for the 0.1.7 behavior (metrics and a hash only), or
`"none"` to record nothing about the circuit. Circuit text is size-capped.

### Results that were silently lost are now recorded
Several common result types were stored as "success" with no values. Each case below was reproduced on the real SDK before the fix and now has a real-SDK test.
- **Qiskit Estimator** (`StatevectorEstimator`, Aer `EstimatorV2`, IBM Runtime `EstimatorV2`): expectation values and standard errors from every PUB (was an empty histogram). Multi-PUB Sampler results keep every PUB, not only the first.
- **Braket** `expectation`, `variance` and `probability` result types, including alongside counts (the expectation value was dropped when `shots > 0`).
- **Cirq** `simulate_expectation_values` (recorded under a PennyLane backend name with no values) and `run_sweep` / `run_batch` (now one entry per sweep point with its parameters). `measurement_key` is optional when the circuit has one measurement.
- **PennyLane** `qml.probs` (was `unknown`, with numpy's `"cpu"` as the backend), `qml.sample` (now counts), and shot vectors (`set_shots([100, 200])`: one entry per group plus the combined counts). A decorated QNode now records its real device.
- **Local jobs returned without `.result()`** (Qiskit primitives and Aer, IBM Runtime local mode, Braket `LocalSimulator` tasks) are read automatically; the function still returns the job. Cloud jobs are never waited on without `await_result=True`; they are recorded with their job id.
- **"Nothing extracted" warning:** if no values can be read from what the function returned, the run is recorded as `unknown` with the returned type, and a one-line warning is printed, instead of an empty success.

### Backend labels
- **Braket (important for AWS users):** the adapter looked for `deviceArn` in a dict, but Braket results carry a `task_metadata` object whose field is `deviceId`, so the device was never read and every run fell back to `local_sim / LocalSimulator`. AWS simulators are now `aws_braket / sv1` etc., and QPUs are labeled by maker (e.g. `rigetti / Ankaa-3`). Confirmed on AWS SV1 on 2026-10-03 (labels and Tracker cost); QPU labels not yet run.
- **D-Wave:** `SimulatedAnnealingSampler` (also inside `EmbeddingComposite`) was labeled `dwave / unknown`, i.e. D-Wave hardware. It is now `local_sim / SimulatedAnnealingSampler`. D-Wave cloud results are recognized by their `problem_id` / QPU timing.
  - Checked against Ocean's source and D-Wave's published outputs, including a real saved QPU output (OpenJij
    tutorial), but not on D-Wave hardware: a trial Leap account gets no Solver API token.
  - The problem id is recorded as the run's job id. QPU timing (µs → s, all fields kept) and Leap hybrid timing
    (`qpu_access_time`, `charge_time`, `run_time`, top-level or nested) are recorded.
  - `MockDWaveSampler` (Ocean's local QPU imitation) is labeled `local_sim` when passed as `backend=`. Its results
    imitate a cloud result, so without `backend=` it would be labeled `dwave`.
  - Not yet supported: the nonlinear (Stride) hybrid solver's result (a model plus info, not a SampleSet).
- With an `sdk` tag, a plain Python result (list, dict, number) is no longer claimed by another SDK's adapter.

### New data
- **Circuit metrics:** qubits, depth, two-qubit gates and gate breakdown, from `@observe_run(circuit=...)` (new optional parameter: Qiskit, Cirq, Braket, pyQuil), from the circuits an IBM Runtime job ran, or from a PennyLane QNode (`qml.specs` at device level). This fills the "Circuit Depth vs Success" chart. Depth counts as "executed" for transpiled circuits and local simulators, otherwise as "submitted".
- **IBM Quantum (verified on ibm_kingston, 2026-09-28; two live rounds, the second 34/34 checks):**
  - Job details: job id, program (sampler/estimator/executor), mode, items, region, creation time, IBM's usage estimate.
    The instance CRN is not stored (it contains the IBM Cloud account id); only its region is.
  - Timeline and queue time from `job.metrics()`. Real jobs report ISO-string timestamps; local mode reports datetimes.
  - Billed QPU seconds (`usage.qpu_charge_time_seconds`), plus IBM's reported circuit execution time (`circuits_execution_time_ns`).
  - Execution spans (Sampler), and chunk timing for executor jobs (the client-side Sampler).
  - Options: what was requested, plus what IBM reports as applied in the result metadata (e.g. `resilience_level=1` turned on
    measurement twirling and measurement mitigation). Also the full input options.
  - For executor jobs, the circuit is read from the job's QuantumProgram. Qubits holding only IBM's dynamical-decoupling
    padding (delays and X pairs) are not counted as working qubits or gates (e.g. 2 qubits and 21 gates, not 156 qubits and 329 gates).
  - Every recorded count and expectation value was compared with IBM's own job result and matched exactly.
- **Aer:** simulator execution time.
- **Braket:** task created/ended times, and the estimated cost of AWS tasks from Braket's own `Tracker` (local tasks have no cost).
- **Braket task id** (as the Braket console lists it) as the run's job id, in the Job ID column and search; the full task ARN, device, region and a retrieve snippet are in the new Run Details "Amazon Braket Task" card. A task returned before it finished is labeled with the device the Tracker saw it created on (it was `local_sim`), and its cost is recorded as not known yet instead of $0 (the Tracker prices simulator tasks only when they finish). Found in the 2026-10-03 SV1 live run.
- **Braket circuits without `circuit=`:** metrics, OpenQASM and diagram are read from the program each result carries (`additional_metadata.action`), so expectation-value runs get them too.
- **Exact runs are no longer shown as 1 shot.** Results computed without sampling (Qiskit `StatevectorEstimator`/Aer `EstimatorV2` at precision 0, PennyLane analytic QNodes, Cirq `simulate_expectation_values`, Braket `shots=0`) carry `execution.exact: true`; the collector lists them with 0 shots and the dashboard shows "Exact". The event keeps `shots: 1` because the schema requires it, so older collectors still accept these runs. Runs recorded before 0.1.8 keep 1.
- **Queue time "Not reported"** instead of "0ms" when the provider gave none (it is measured for IBM jobs; local simulators have none), and the runtime classification is not guessed from an assumed 0 ms queue.
- **Google Quantum Engine and Cirq's Quantum Virtual Machine (QVM):** runs are labeled by processor (QVM runs as `local_sim / willow_pink (virtual)`, Engine runs as `google / <processor>`) and keep the Engine job id. A returned Engine job (`processor.run_sweep(...)`) is read like other jobs (QVM jobs at once, cloud jobs with `await_result=True`) and records its processor, program, status, created/updated times, calibration time and its circuit. New Run Details card. Checked on all three QVM processors (rainbow, weber, willow_pink); real Engine hardware needs Google's approval and is not verified.
- **PennyLane plugins:** the backend is the device the plugin ran (e.g. `ibm / ibm_fez`, `aws_braket / sv1`, `local_sim / aer_simulator`) instead of the plugin name; the Braket plugin's `qml.counts()` (a 0-d object array) is no longer dropped; PennyLane runs on Braket record the task id and Tracker cost. Checked live on IBM ibm_fez and AWS SV1.
- **D-Wave:** chain break fraction, chain lengths and chain strength from `EmbeddingComposite(..., return_embedding=True)`; timing from local dwave-samplers.

### Collector
- New metrics: `qc.expectation.count/mean/value/max_stderr`, `qc.batch.count`, `qc.anneal.chain_break_fraction/max_chain_length/physical_qubits`; Shannon entropy from exact probabilities.
- New insight when more than 10% of chains break.

### Dashboard
- **Job ID column** in Recent Runs and Search Runs (searchable) and the CSV export: correlate a run with the provider's
  console. `GET /v1/runs` includes each run's `job_id` (new field only).
- **SDK column** in Recent Runs, Search Runs (also searchable) and the CSV export. `GET /v1/runs` now includes each run's `sdk` and `algorithm` (new fields only).
- **Upgrades show up in the browser:** the dashboard server sent `index.html` without `Cache-Control`, so a browser could keep showing the previous dashboard for hours after an upgrade. `index.html` is now revalidated on every load, and the content-hashed files under `/assets/` are cached long-term. A browser that cached a pre-0.1.8 page picks this up after one reload.
- Runs without measurement counts (energies, expectation values, sweeps) no longer show "Effective Support Size" and "Shot Efficiency" cards filled with zeros. On the Compare page these show "N/A".

New Run Details cards, shown only when a run has that data: Expectation Values, Measurement Probabilities, Batch Results, Embedding & Chain Breaks, Circuit (metrics, text diagram, OpenQASM/Quil), IBM Quantum Job (with a snippet to retrieve the job), Job Timeline (with execution spans / chunk timing), Execution Options, Input Options, and a notice when a run recorded no results. Runs recorded by 0.1.7 render exactly as before (checked page by page in Chrome on a 0.1.7 data folder).

## 0.1.7 (qobserva 0.1.7 · qobserva-agent 0.1.2 · qobserva-collector 0.1.5 · qobserva-local 0.1.4)

qobserva-agent is unchanged (still 0.1.2).

### Dashboard speed
- **Collector:** each run's SDK, runtime, benchmark parameters and the analysis metrics used by charts are stored in an indexed summary when the run arrives. `GET /v1/runs?include_summary=true` returns them with the run list. Without the parameter, the response is unchanged.
- **Dashboard:** Run Analytics and Algorithm Analytics read those summaries instead of fetching each run's event and analysis. With 18 runs, Run Analytics went from 110 API requests to 2, and the pages render as soon as the run list arrives. Charts look the same and show the same data.
- **Collector:** filtering runs by algorithm and `GET /v1/algorithms` use the database (indexed `algorithm` column) instead of reading every stored bundle from disk. The algorithm filter previously looked at only the latest `2 × limit` runs, so it could miss older matches.
- **Upgrade:** existing data folders are upgraded automatically the first time collector 0.1.5 starts. It adds the new columns and indexes existing runs once from their stored bundles. Nothing is deleted.
- **Dashboard server:** the built-in dashboard server (pip installs) now handles connections concurrently. Before, one idle browser connection could block every other request, so pages sometimes stayed on "Loading...".
- **Dashboard bundle:** the logo shipped at 1536×1024 (2.2 MB) and the tab icon embedded a 2.9 MB image. Both are now sized for how they're displayed (62 KB and 26 KB). JavaScript is split into cached chunks, so no chunk is over 500 kB. The `qobserva-local` wheel went from 9.4 MB to 0.9 MB.

### Fixes
- **Dashboard:** the "Circuit Depth vs Success" chart read a metric name the collector never produces (`qc.circuit.depth.post` instead of `qc.circuit.depth_post`), so it always said "No data available". The name is fixed; the chart fills in once runs record a transpiled circuit depth, which the SDK adapters don't do yet.
- **Algorithm Analytics:** with more than 100 runs for an algorithm, the SDK comparison fell back to provider names (e.g. `local_sim`) and showed no runtimes. It now uses each run's SDK and runtime at any count.
- **`qobserva up`:** `up` now waits for the collector *it* started. Before, if another program took the port between the pre-check and startup, `up` reported "Collector running" because the other program answered the health check. Now it reports that the collector exited and returns an error. `/v1/health` includes the collector's pid for this check.
- **`qobserva down`:** `down` checks that each pid file still points at the QObserva process that wrote it (pid plus process start time) before stopping it. A stale pid file whose number now belongs to another program is removed and that program is left alone. `down` also stops the process's children (e.g. the dev-mode dashboard) and says when nothing was running. `qobserva-local` now depends on `psutil` for this.
- **Examples:** removed `basic_counts_dict.py`. It recorded a hardcoded counts dict, which the PennyLane adapter labeled as a PennyLane run.
- **PennyLane example:** uses `qml.set_shots` (PennyLane 0.42+) instead of device shots, which PennyLane has deprecated.

### Testing and CI
- New tests: run summaries and algorithm counts, upgrading a 0.1.4 database, pid reuse in `qobserva down`, the `qobserva up` race, the dashboard server with an idle connection, and a Braket adapter test on the real `LocalSimulator`.
- `tests/requirements.txt` lists test dependencies, including `httpx2`, which Starlette 1.x's TestClient now expects.
- CI runs on pushes to `main`, on pull requests, and every Monday against the newest SDK releases, so an SDK update that breaks an adapter shows up early. Braket is now part of the SDK job.
- Dependabot opens weekly grouped PRs for Python dependencies, the dashboard's npm packages and GitHub Actions.
- A Security workflow (CodeQL and dependency review) runs in the public repository.

## 0.1.6 (qobserva 0.1.6 · qobserva-agent 0.1.2 · qobserva-collector 0.1.4 · qobserva-local 0.1.3)

### Security and privacy
- **Collector:** untrusted `project` and `run_id` values can no longer write outside the data directory. Names that were already safe keep the same folder layout.
- **Collector:** browser access is limited to local pages (`localhost` / `127.0.0.1`), and writes from any other website are refused, so web pages you visit can't write to your collector. Configure with `QOBSERVA_CORS_ORIGINS`.
- **Collector:** when `QOBSERVA_LOCAL_TOKEN` is set, read endpoints require the token too, not just ingestion. `qobserva up` passes the token through its dashboard proxy.
- **Agent:** error messages are stored with secret *values* redacted (API keys, tokens, passwords, bearer headers, URL credentials, AWS keys, IBM Quantum tokens). Before this release, secret values were stored as-is.
- **Agent:** the machine's hostname is recorded as a stable hash by default. Set `QOBSERVA_HOST_MODE=raw` for the old behavior or `none` to omit it.

### Reliability
- **Agent:** telemetry is sent in the background, so the decorated function no longer waits for the collector. Before, an unreachable collector added up to 10s per run. Pending runs are flushed at exit, and `qobserva.flush()` is available for notebooks and tests. `QOBSERVA_ASYNC=0` restores synchronous sending.
- **Agent:** sending a run is about 1s faster on machines where loading the TLS certificate bundle is slow; it's skipped for plain `http://` collectors, and `https://` endpoints are still fully verified. With a local collector that's down, the program exits about 1.5s later than normal (measured on Windows). Before, Windows retries of refused connections plus certificate loading added about 4.3s.
- **Agent:** if the collector can't be reached, QObserva prints one warning instead of failing silently.
- **Packaging:** `qobserva` and `qobserva-agent` no longer overwrite each other's `cli.py` or the `qobserva` command. Before, reinstalling `qobserva-agent` could remove `qobserva up`. The agent's utility CLI is now `qobserva-agent`.
- **`qobserva up` / `qobserva down`:** `up` now detects a QObserva that's already running and says where, instead of reporting a start that didn't happen. A port held by another program gives a clear error with the settings to change. `qobserva down` from another terminal now stops the dashboard too. Before, pip installs kept serving the dashboard from the `up` process.
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

### Installation
- `pip install "qobserva-agent[all-sdks]"` now works. The README documented it, but the agent package had no such extra, so it installed no SDKs.
- `qobserva-local` now depends on `qobserva-collector`, so `pip install qobserva-local` followed by `qobserva-local up` works on its own.

### Examples and docs
- Examples, Getting Started and the PyPI pages now lead with the PyPI install (`pip install qobserva "qobserva-agent[<sdk>]"`, `qobserva up`); source-checkout installs are shown second.
- The agent's PyPI page named a non-existent `QOBSERVA_COLLECTOR_URL` setting; it now documents `QOBSERVA_ENDPOINT`.
- The pyQuil example no longer substitutes randomly generated results when the QVM is unavailable. It now fails, and QObserva records the run as failed.
- The API reference documents all environment variables and Qiskit labeling behavior.

### Tests and CI
- CI now runs the test suite on Python 3.10–3.14 (Linux) and 3.12 (Windows), Qiskit adapter tests against real Qiskit/Aer/IBM Runtime, pyQuil adapter tests against Rigetti's QVM, and a dashboard build.

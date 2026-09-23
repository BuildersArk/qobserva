# API Reference

Reference for the `@observe_run` decorator and related behavior.

## `observe_run` Decorator

Instrument a function that runs a quantum program so that QObserva captures execution, metrics, and results and sends them to the collector.

### Signature

```python
def observe_run(
    project: str,
    tags: Optional[Dict[str, str]] = None,
    capture_program: str = "hash",
    await_result: bool = False,
    measurement_key: Optional[str] = None,
    benchmark_id: Optional[str] = None,
    benchmark_params: Optional[Dict[str, Any]] = None,
    endpoint: str | None = None,
    api_key: str | None = None,
    backend: Any = None,
    provider: str | None = None,
):
    ...
```

### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| **project** | `str` | — | **Yes** | Project name for grouping runs (e.g. `"qiskit_test"`, `"my_experiment"`). |
| **tags** | `Dict[str, str]` | `None` | **Yes** | Metadata tags. **Must include `"sdk"`** for reliable adapter selection. |
| **capture_program** | `str` | `"hash"` | No | How to capture the program: `"hash"`, `"none"`, or `"attachment"`. |
| **await_result** | `bool` | `False` | No | If `True` and the function returns a job/task, QObserva calls `.result()` on it. The job's backend is recorded too (e.g. IBM Runtime / Aer jobs). The decorated function then returns the result. |
| **measurement_key** | `str` | `None` | Cirq only | Measurement key that matches `cirq.measure(..., key=...)`. Required for Cirq to extract counts. |
| **benchmark_id** | `str` | `None` | No | Optional benchmark identifier for comparison. |
| **benchmark_params** | `Dict[str, Any]` | `None` | No | Optional algorithm-specific metrics (e.g. energy, success rate). |
| **endpoint** | `str` | `None` | No | Custom collector URL. If not set, uses default (e.g. `http://localhost:8080`). |
| **api_key** | `str` | `None` | No | Optional API key for collector authentication. |
| **backend** | backend object or `str` | `None` | No | The backend the run executed on, for when the SDK result doesn't say (Qiskit V2 primitive results carry no backend). Pass an SDK backend object (e.g. `AerSimulator()`, `service.backend("ibm_brisbane")`) or a name. |
| **provider** | `str` | `None` | No | Provider label to record, e.g. `"ibm"`, `"aws_braket"`, `"local_sim"`. |

### Tags

- **`sdk`** (required): One of `"qiskit"`, `"braket"`, `"cirq"`, `"pennylane"`, `"pyquil"`, `"dwave"`. Used to select the correct adapter.
- **`algorithm`** (recommended): e.g. `"bell_state"`, `"vqe"`, `"grover"`, `"qubo"`. Enables algorithm-specific dashboards.
- **`test`** (optional): e.g. `"entanglement"`, `"optimization"`. For categorizing runs.

### Example

```python
from qobserva import observe_run

@observe_run(
    project="qiskit_test",
    tags={"sdk": "qiskit", "algorithm": "bell_state", "test": "entanglement"},
    benchmark_id="bell_state_2qubit",
    benchmark_params={"expected_success_rate": 0.95},
)
def run():
    # ... quantum code ...
    return result
```

### Return Value

The decorator returns whatever the wrapped function returns. It does not change the return type.

### Adapter Selection

- QObserva uses the **`tags["sdk"]`** value to choose which adapter handles the function’s return value.
- If `sdk` is omitted, the adapter is inferred from the result object, which is less reliable and can lead to wrong provider/backend.
- **Best practice:** Always set `tags={"sdk": "..."}`.

### Project, Provider, and Backend

- **Project:** Always from `project` (user-defined).
- **Provider / Backend:** Extracted from the SDK result object by the adapter (e.g. `local_sim`, `ibm`, `aws_braket`). Explicit `backend=` / `provider=` arguments take precedence. When neither the result nor the arguments identify the backend, QObserva records `unknown` rather than guessing (the Run Quality report lists these runs).

#### Qiskit

| How the run executes | What QObserva records |
|----------------------|-----------------------|
| `StatevectorSampler().run(...).result()` | `unknown` / `unknown` (the result has no backend info). Pass `backend="statevector_sampler", provider="local_sim"`. |
| `qiskit_aer.primitives.SamplerV2` | `local_sim` / `aer_simulator` |
| `AerSimulator().run(...).result()` | `local_sim` / `aer_simulator` |
| `BackendSamplerV2(backend=b)` | pass `backend=b` to get its name and provider |
| IBM Runtime `SamplerV2(mode=backend).run(...)` returned **as a job** with `await_result=True` | `ibm` / device name (e.g. `ibm_brisbane`) |
| IBM Runtime fake backends (`FakeManilaV2`, …) | `local_sim` / `fake_manila`. These simulate IBM devices locally. |

See [README.md](../README.md#understanding-project-provider-and-backend) for the full table.

## `flush()`

Runs are sent to the collector in the background so telemetry never slows down your program. Pending runs are flushed automatically when Python exits. In a notebook or test that reads runs back right away, call:

```python
import qobserva
qobserva.flush()  # waits up to QOBSERVA_FLUSH_TIMEOUT_S seconds; returns True when everything was delivered
```

If the collector can't be reached, QObserva prints one warning to stderr and your program continues normally.

## Environment variables

### Agent (your quantum program)

| Variable | Default | Description |
|----------|---------|-------------|
| `QOBSERVA_ENDPOINT` | `http://127.0.0.1:8080/v1/ingest/run-event` | Collector ingest URL. |
| `QOBSERVA_API_KEY` | — | Sent as `Authorization: Bearer ...`; must match the collector's `QOBSERVA_LOCAL_TOKEN`. |
| `QOBSERVA_ASYNC` | `1` | Set `0` to send each run before the decorated function returns. |
| `QOBSERVA_FLUSH_TIMEOUT_S` | `5` | Longest time to wait at exit (or in `flush()`) for pending runs. |
| `QOBSERVA_TIMEOUT_S` | `10` | Request timeout for sending a run (connect phase is capped at 3s). |
| `QOBSERVA_HOST_MODE` | `hash` | Machine identity recorded on each run: `hash` (stable 12-character hash), `raw` (hostname), or `none`. |

Error messages from failed runs are stored with secret values redacted (API keys, tokens, passwords, bearer headers, URL credentials, AWS keys, IBM Quantum tokens).

### Collector

| Variable | Default | Description |
|----------|---------|-------------|
| `QOBSERVA_DATA_DIR` | platform user data dir | Where the SQLite database and run artifacts are stored. |
| `QOBSERVA_LOCAL_TOKEN` | — | When set, every API call except `/v1/health` requires `Authorization: Bearer <token>`. `qobserva up` passes the token through its dashboard proxy automatically. |
| `QOBSERVA_CORS_ORIGINS` | local pages only | Comma-separated browser origins allowed to call the collector directly. By default only `localhost` / `127.0.0.1` pages can. Websites you visit can't write to your collector. |

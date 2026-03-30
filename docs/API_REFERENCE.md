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
):
    ...
```

### Parameters

| Parameter | Type | Default | Required | Description |
|-----------|------|---------|----------|-------------|
| **project** | `str` | — | **Yes** | Project name for grouping runs (e.g. `"qiskit_test"`, `"my_experiment"`). |
| **tags** | `Dict[str, str]` | `None` | **Yes** | Metadata tags. **Must include `"sdk"`** for reliable adapter selection. |
| **capture_program** | `str` | `"hash"` | No | How to capture the program: `"hash"`, `"none"`, or `"attachment"`. |
| **await_result** | `bool` | `False` | No | If `True`, await async results (e.g. Braket `Task.result()`). |
| **measurement_key** | `str` | `None` | Cirq only | Measurement key that matches `cirq.measure(..., key=...)`. Required for Cirq to extract counts. |
| **benchmark_id** | `str` | `None` | No | Optional benchmark identifier for comparison. |
| **benchmark_params** | `Dict[str, Any]` | `None` | No | Optional algorithm-specific metrics (e.g. energy, success rate). |
| **endpoint** | `str` | `None` | No | Custom collector URL. If not set, uses default (e.g. `http://localhost:8080`). |
| **api_key** | `str` | `None` | No | Optional API key for collector authentication. |

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
- **Provider / Backend:** Extracted from the SDK result object by the adapter (e.g. `local_sim`, `ibm`, `aws_braket`). If extraction fails, sensible defaults are used based on the `sdk` tag.

See [README.md](../README.md#understanding-project-provider-and-backend) for the full table.

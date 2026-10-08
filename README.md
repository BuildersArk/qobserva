# QObserva

Quantum program observability and benchmarking. Local-first observability for quantum computing.

Think: **Datadog / Prometheus - but for quantum computing SDKs.**

## Demo

![QObserva dashboard showing a real Qiskit run on IBM ibm_kingston](docs/video/demo.gif)

*A real Qiskit run on IBM's ibm_kingston quantum computer, recorded with `@observe_run`.*



## Quick Start

### Prerequisites

- **Python 3.10+** (see [Python Version Compatibility](#python-version-compatibility) for SDK-specific requirements)
- **Node.js** only if you install from source (the PyPI packages include the built dashboard)

> **Python Version Note:** For best compatibility with all SDKs, use **Python 3.12**. See the [Python Version Compatibility](#python-version-compatibility) section for details.

### Installation

**From PyPI (recommended):**

```bash
pip install qobserva
```

For SDK adapters, install the agent with extras:

```bash
pip install qobserva-agent[qiskit]      # Qiskit
pip install qobserva-agent[all-sdks]    # All supported SDKs
```

**From source (development):**

```bash
# Clone the repository
git clone https://github.com/BuildersArk/qobserva.git
cd qobserva

# Install packages in editable mode
pip install -e packages/qobserva_agent
pip install -e packages/qobserva_collector
pip install -e packages/qobserva_local
pip install -e packages/qobserva

# Install React dashboard dependencies (one-time)
cd packages/qobserva_ui_react
npm install
cd ../..
```

### Start QObserva

```bash
# Start everything (collector + React dashboard)
qobserva up
```

Dashboard opens at http://localhost:3000

### Stop QObserva

```bash
# Stop all services
qobserva down
```

## What is QObserva?

QObserva provides standardized telemetry, metrics, and visualizations for quantum program executions across all major Python quantum SDKs.

## Use Cases

- **Cross-SDK benchmarking**: Compare algorithm behavior across Qiskit, Braket, Cirq, PennyLane, pyQuil, and D-Wave.
- **Experiment observability**: Track run status, shots, runtimes, and quality metrics over time.
- **Regression detection**: Catch performance or success-rate regressions across code changes.
- **Team reporting**: Use dashboard views and generated reports to share outcomes with researchers and engineering teams.
- **Backend evaluation**: Compare providers/devices for cost, reliability, and result quality trade-offs.

### Features

- **Decorator-first instrumentation**: `@observe_run()` decorator with simple API
- **Multi-SDK support**: Qiskit, Braket, Cirq, PennyLane, pyQuil, D-Wave (all tested)
- **Professional React dashboard**: Modern dark-themed UI with diverse visualizations
  - Home dashboard with KPIs, trends, and run tables
  - Analytics dashboard with performance metrics and comparisons
  - Algorithm analytics for cross-SDK algorithm comparison
  - Run details with comprehensive quantum metrics
  - Compare runs side-by-side
  - Search and filter capabilities
  - PDF report generation
- **Local-first**: Everything runs locally, no cloud required
- **Standardized schema**: Common event format across all SDKs
- **One-command setup**: `qobserva up` starts everything
- **Energy metrics**: D-Wave optimization metrics (energy, approximation ratio)
- **Comprehensive metrics**: Entropy, top-K dominance, shot efficiency, runtime analysis

## Usage

### Instrument Your Code

**⚠️ IMPORTANT: Always include the `sdk` tag for reliable adapter selection!**

```python
from qobserva import observe_run

@observe_run(
    project="my_project",
    tags={
        "sdk": "qiskit",  # ← SDK tag is REQUIRED!
        "algorithm": "vqe"  # ← Algorithm tag (optional but recommended)
    },
    benchmark_id="vqe_h2_ground_state",
    benchmark_params={
        "energy": -1.137,  # Algorithm-specific metrics (optional)
        "convergence_iterations": 10
    }
)
def my_quantum_algorithm():
    # Your quantum code here
    result = execute_quantum_circuit()
    return result
```

**Supported SDK values:** `"qiskit"`, `"braket"`, `"cirq"`, `"pennylane"`, `"pyquil"`, `"dwave"`

**Algorithm Tagging (Optional but Recommended):**
- Add `"algorithm"` tag to enable algorithm-specific dashboards and comparisons
- Examples: `"vqe"`, `"grover"`, `"qaoa"`, `"qft"`, `"phase_estimation"`, `"bell_state"`, etc.
- Algorithm-tagged runs appear in the **Algorithms** dashboard for cross-SDK comparison
- Include `benchmark_params` for algorithm-specific metrics (energy values, success rates, etc.)

If you omit the `sdk` tag, QObserva will attempt to detect it from the result object, but this is less reliable and may result in incorrect provider/backend detection.

### What Gets Recorded

Return the SDK's result (or a local job/task) from the decorated function. QObserva records:

| Result | Examples | Shown in Run Details as |
|---|---|---|
| Counts | Qiskit `SamplerV2`, Braket `measurement_counts`, Cirq `run`, PennyLane `qml.counts` / `qml.sample`, pyQuil, D-Wave | Measurement Results and the sampling metrics |
| Expectation values | Qiskit `EstimatorV2` (`evs`, `stds`), Braket `expectation` / `variance`, Cirq `simulate_expectation_values`, PennyLane `expval` | Expectation Values table |
| Probabilities | PennyLane `qml.probs`, Braket `probability` | Measurement Probabilities chart |
| Batches | Cirq `run_sweep` / `run_batch`, PennyLane shot vectors, multi-PUB Sampler results | Batch Results table (one row per sweep point / group / PUB) |
| Energies and embedding | D-Wave SampleSets; `EmbeddingComposite(..., return_embedding=True)` adds chain lengths and chain breaks | Optimization Results, Embedding & Chain Breaks |

Also recorded when the SDK provides them: the provider's job ID (searchable in the dashboard); circuit qubits, depth and gate counts, the circuit as OpenQASM/Quil and a text diagram; the IBM Quantum job timeline, queue time, billed QPU seconds, execution spans or chunk timing, and the requested and applied error-suppression/mitigation options; Braket task times; the estimated AWS cost of Braket tasks (from Braket's `Tracker`); and Google Quantum Engine / Quantum Virtual Machine job details (processor, program, status, calibration time). Results computed exactly, without sampling (a statevector Estimator, PennyLane analytic mode, Braket `shots=0`), show **Exact** instead of a shot count.

- **Local jobs** (Qiskit primitives and Aer, IBM Runtime local mode, Braket `LocalSimulator`, Cirq Quantum Virtual Machine jobs) are read automatically, and your function still returns the job. **Cloud jobs** are never waited on unless you pass `await_result=True`. Without it, the run is recorded with the job id and a hint.
- **Circuit:** IBM Runtime jobs and PennyLane QNodes provide it automatically. For other runs, pass the circuit: `@observe_run(..., circuit=qc)` (Qiskit `QuantumCircuit`, Cirq `Circuit`, Braket `Circuit` or pyQuil `Program`). By default (`capture_program="full"`) QObserva records the circuit's metrics, its OpenQASM/Quil text and a diagram, and stores them with your collector (local by default). `capture_program="hash"` records only metrics and a hash; `"none"` records nothing about the circuit.
- If QObserva can't read any results from what your function returned, it records the run as `unknown` and prints a one-line warning, instead of an empty success.

### View Dashboard

Open http://localhost:3000 to see:
- **Home Dashboard**: Real-time run metrics, KPIs, success rate trends, status distribution
- **Analytics Dashboard**: Comprehensive performance analysis and trends
- **Algorithms Dashboard**: Algorithm-specific metrics and cross-SDK comparison (requires algorithm tags)
- **Compare Dashboard**: Side-by-side run comparison
- **Search Runs**: Find runs by ID, project, provider, backend, or status
- Backend performance comparisons
- Cost vs quality analysis (scatter plots)
- Performance heatmaps
- And more...

## Architecture

QObserva consists of four packages:

- **qobserva-agent**: Telemetry agent with decorators and adapters for all major quantum SDKs
- **qobserva-collector**: FastAPI service for ingestion, validation, and storage
- **qobserva-local**: One-command orchestrator for the local stack (includes React dashboard)
- **qobserva**: Unified meta-package and CLI

The React dashboard (`qobserva_ui_react`) is included as part of the local stack and runs automatically when you start QObserva.

## SDK Support

All 6 SDK adapters are implemented and tested:

```bash
# All SDKs
pip install qobserva-agent[all-sdks]

# Individual SDKs
pip install qobserva-agent[qiskit]
pip install qobserva-agent[braket]
pip install qobserva-agent[cirq]
pip install qobserva-agent[pennylane]
pip install qobserva-agent[pyquil]
pip install qobserva-agent[dwave]
```

### Python Version Compatibility

Verified by running each SDK's example on Python 3.12, 3.13 and 3.14 (September 2026):

| SDK | 3.12 | 3.13 | 3.14 | Notes |
|-----|------|------|------|-------|
| **Qiskit** (2.5.2) | ✅ | ✅ | ✅ | |
| **Braket** (1.127.1) | ✅ | ✅ | ✅ | Python 3.14 now supported |
| **Cirq** (1.7.0) | ✅ | ✅ | ✅ | |
| **PennyLane** (0.45.1) | ✅ | ✅ | ✅ | |
| **pyQuil** (4.20.0) | ✅ | ❌ | ❌ | pyQuil itself requires Python 3.11–3.12 |
| **D-Wave** (dimod 0.12.22) | ✅ | ✅ | ✅ | |

**Recommendations:**
- **For all SDKs:** Use **Python 3.12**
- **Without pyQuil:** Python **3.13** or **3.14** run all the other SDKs

**Note:** These limitations are due to SDK dependencies, not QObserva itself. QObserva core works with Python 3.10+.

## Understanding Project, Provider, and Backend

When using QObserva, it's important to understand how **Project**, **Provider**, and **Backend** values are determined, as these are used for filtering and comparison in the dashboard.

### How Values Are Derived

| Field | Source | Description |
|-------|--------|-------------|
| **Project** | User-defined in decorator | From `@observe_run(project="...")` - completely user-controlled, used for grouping runs |
| **Provider** | Extracted from result object | The cloud provider or simulator type (e.g., `ibm`, `aws_braket`, `local_sim`) |
| **Backend** | Extracted from result object | The specific device or simulator name (e.g., `ibm_brisbane`, `default.qubit`) |

### SDK-Specific Behavior

| SDK | Scenario | Provider Source | Backend Source | Notes |
|-----|----------|----------------|----------------|-------|
| **Qiskit** | Aer / fake backends | `local_sim` | e.g. `aer_simulator`, `fake_manila` | From the result, the returned job, or `backend=` |
| **Qiskit** | IBM hardware | `ibm` | Device name, e.g. `ibm_brisbane` | Return the job with `await_result=True`, or pass `backend=` |
| **Qiskit** | StatevectorSampler / other V2 primitives | `unknown` | `unknown` | V2 primitive results don't name their backend; pass `backend=` / `provider=` |
| **Braket** | LocalSimulator | `local_sim` | `LocalSimulator` (or the local simulator id, e.g. `braket_dm`) | From `result.task_metadata.deviceId` |
| **Braket** | AWS simulators (SV1, DM1, TN1) | `aws_braket` | e.g. `sv1` | From the device ARN in `task_metadata.deviceId` |
| **Braket** | QPU | The QPU maker from the ARN (`/qpu/rigetti/...` → `rigetti`) | Last part of the ARN, e.g. `Ankaa-3` | From the device ARN in `task_metadata.deviceId` |
| **Cirq** | Simulator | Defaults to `local_sim` | `result.simulator.__class__.__name__` | Always `local_sim` for simulators |
| **Cirq** | Quantum Virtual Machine (`cirq_google`) | `local_sim` | Processor, e.g. `willow_pink (virtual)` | From the Engine job or the EngineResult job id; local simulation with the processor's noise model |
| **Cirq** | Google Quantum Engine | `google` | Processor id | From the Engine job (`processor.run_sweep(...)` with `await_result=True`), or pass `backend=processor` (not verified on real hardware) |
| **PennyLane** | Decorated QNode | From the QNode's device | The QNode's `device.name` | Decorate the QNode itself to record its real device |
| **PennyLane** | Simulator (plain values) | **Default: `local_sim`** | **Default: `default.qubit`** | ⚠️ Counts dicts and arrays don't include device info |
| **PennyLane** | Plugin devices (`qiskit.remote`, `qiskit.aer`, `braket.aws.qubit`, `braket.local.qubit`) | The device the plugin ran: `ibm`, `aws_braket`, a QPU maker, or `local_sim` | e.g. `ibm_fez`, `sv1`, `aer_simulator` | From the plugin's Qiskit backend or Braket device ARN; Braket plugin runs also record the task id and cost |
| **pyQuil** | QVM / QPU | `local_sim` for QVM, `rigetti` for QPU | `qvm`, or the `get_qc(...)` name when passed as `backend=` | From pyQuil 4 `QAMExecutionResult` |
| **D-Wave** | `SimulatedAnnealingSampler` (also inside `EmbeddingComposite`) | `local_sim` | `SimulatedAnnealingSampler` | Recognized from its annealing schedule in the SampleSet info |
| **D-Wave** | Other local samplers (`ExactSolver`, `TabuSampler`, …) | `unknown`, or `local_sim` with `backend=sampler` | Sampler class name when passed as `backend=` | These SampleSets don't say which sampler produced them |
| **D-Wave** | D-Wave cloud (QPU / hybrid) | `dwave` | Solver name when the sampler is passed as `backend=` | Detected from the problem id D-Wave returns; the problem id is shown as the run's job id |
| **D-Wave** | `MockDWaveSampler` (Ocean's local QPU imitation) | `local_sim` with `backend=sampler` | `MockDWaveSampler` | Its results imitate a cloud result, so pass `backend=` to label it correctly |

### Important Notes

0. **Tags are metadata (and influence adapter selection), not backend overrides**:
   - Tags (like `sdk`, `algorithm`, `dataset`, `test`) are **user-supplied** metadata.
   - QObserva uses the `sdk` tag to make adapter selection deterministic.
   - Tags do not override `backend.provider` / `backend.name`. Those fields are extracted from the SDK result object. When the result doesn't identify its backend, pass it explicitly with `@observe_run(backend=..., provider=...)` (a backend object such as `AerSimulator()` or a name). Otherwise QObserva records `unknown` for Qiskit rather than guessing.

1. **SDK Tag is Required**: Always include `tags={"sdk": "..."}` in your decorator for reliable adapter selection. Without it, QObserva may incorrectly identify the SDK, leading to wrong provider/backend values.

2. **Project is User-Defined**: The `project` parameter is completely arbitrary - use it to group related runs (e.g., `"experiment_1"`, `"production"`, `"testing"`).

3. **Provider/Backend Extraction Limitations**:
   - **PennyLane counts dicts**: When returning `qml.counts()`, the result is just a plain dict with no device info, so defaults are used
   - **Some simulators**: May not expose provider information, defaulting to `local_sim`
   - **Real devices**: Usually have complete provider/backend information

4. **Filtering in Dashboard**: 
   - Filter by **Project** to see runs from specific experiments/projects
   - Filter by **Provider** to compare `ibm` vs `aws_braket` vs `local_sim`
   - Filter by **Backend** to compare specific devices (e.g., `ibm_brisbane` vs `ibm_kyoto`)

### Example: Understanding Your Data

If you see in the dashboard:
- **Project**: `"pennylane_test"` ← You defined this
- **Provider**: `"local_sim"` ← Extracted (or defaulted) from result
- **Backend**: `"default.qubit"` ← Extracted (or defaulted) from result

To compare AWS vs IBM backends, filter by:
- **Provider** = `"aws_braket"` OR **Provider** = `"ibm"`

Note: Multiple projects can have the same provider/backend combinations. The project is just for grouping your runs, not for identifying the quantum hardware.

## Configuration

Runs are sent to the collector in the background, so QObserva never slows down your program. If the collector isn't running, you get one warning and your code keeps going. Hostnames are stored as a hash and secrets are redacted from error messages. All settings (`QOBSERVA_ENDPOINT`, `QOBSERVA_HOST_MODE`, `QOBSERVA_LOCAL_TOKEN`, …) are listed in the [API Reference](docs/API_REFERENCE.md#environment-variables).

## Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** — Minimal path: install, start, run one example, view dashboard
- **[Testing Guide](docs/TESTING_GUIDE.md)** — Full guide: setup, SDK examples, version requirements, viewing results
- **[API Reference](docs/API_REFERENCE.md)** — `@observe_run` decorator parameters and behavior
- **[SDK Compatibility](docs/SDK_COMPATIBILITY.md)** — Python and SDK version matrix, limitations
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — Common errors, FAQ, and solutions
- [Examples](examples/) — SDK-specific example scripts with proper project names and tags
- [Changelog](CHANGELOG.md)

## Links

- **Website**: [qobserva.com](https://qobserva.com)
- **Documentation**: [qobserva.com/docs.html](https://qobserva.com/docs.html)
- **GitHub**: [github.com/BuildersArk/qobserva](https://github.com/BuildersArk/qobserva)
- **Issues**: [github.com/BuildersArk/qobserva/issues](https://github.com/BuildersArk/qobserva/issues)

## Release Status

> ⚠️ **Beta:** QObserva is currently in beta. APIs may change.

## Reporting Issues / Getting Help

If you run into problems, have questions, or want to request features, please open an issue on GitHub:

- [https://github.com/BuildersArk/qobserva/issues](https://github.com/BuildersArk/qobserva/issues)

## License

QObserva is provided under the **QObserva Community License v1.0** (source-available).

You may use and modify the software internally (including for academic and startup use).
Offering QObserva as a hosted/SaaS service, distributing modified versions commercially,
or building commercial products based on QObserva requires a separate commercial license
from BuildersArk LLC. See the `LICENSE` file for full terms.

**Contributors:** By submitting a pull request or contribution, you agree to the
[Contributor License Agreement (CLA)](CLA.md).

## GitHub SEO Keywords

`quantum-computing`, `qiskit`, `cirq`, `observability`, `monitoring`, `python`, `developer-tools`

## Support QObserva

If QObserva is useful to your work, please star the repository:

- [https://github.com/BuildersArk/qobserva](https://github.com/BuildersArk/qobserva)

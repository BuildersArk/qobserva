# QObserva

Quantum program observability and benchmarking. Local-first observability for quantum computing.

Think: **Datadog / Prometheus - but for quantum computing SDKs.**

## Demo

![QObserva dashboard demo](docs/video/demo.gif)



## Quick Start

### Prerequisites

- **Python 3.10+** (see [Python Version Compatibility](#python-version-compatibility) for SDK-specific requirements)
- **Node.js** (for React dashboard)

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

| SDK | Python Version | Notes |
|-----|----------------|-------|
| **Qiskit** | 3.10+ | Works with Python 3.10-3.14 |
| **Braket** | 3.10 - 3.13 | **Python 3.14+ NOT supported** (Braket SDK uses Pydantic v1 which doesn't support Python 3.14+) |
| **Cirq** | 3.10+ | Works with Python 3.10-3.14 |
| **PennyLane** | 3.10+ | Works with Python 3.10-3.14 |
| **pyQuil** | 3.10 - 3.12 | **Python 3.13+ NOT supported** (PyQuil 4.x uses PyO3 0.20.3 which supports up to Python 3.12) |
| **D-Wave** | 3.10+ | Works with Python 3.10-3.14 |

**Recommendations:**
- **For all SDKs:** Use **Python 3.12** (supports all 6 SDKs)
- **Without pyQuil:** Can use **Python 3.13** (supports all except pyQuil)
- **Without Braket:** Can use **Python 3.14** (supports all except Braket)

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
| **Qiskit** | Simulator | `result.backend.provider.name` or inferred | `result.backend.name` | Usually `local_sim` for simulators, `ibm` for real devices |
| **Qiskit** | Real Device | `result.backend.provider.name` | `result.backend.name` | Extracted from IBM backend object |
| **Braket** | Simulator | From `result.task_metadata.deviceArn` or device name | From ARN or `result.device.name` | Usually `local_sim` for LocalSimulator |
| **Braket** | Real Device | From ARN path (`/qpu/ionq/...` → `ionq`) | Last part of ARN | Extracted from device ARN structure |
| **Cirq** | Simulator | Defaults to `local_sim` | `result.simulator.__class__.__name__` | Always `local_sim` for simulators |
| **Cirq** | Real Device | From device object (if available) | From device object | May show `google` for Google devices |
| **PennyLane** | Simulator | **Hardcoded default: `local_sim`** | **Hardcoded default: `default.qubit`** | ⚠️ Counts dicts don't include device info |
| **PennyLane** | Real Device | Inferred from device name pattern | From `device.name` | Detects provider from device name (e.g., `qiskit.*` → `ibm`) |
| **D-Wave** | Simulator/QPU | **Hardcoded: `dwave`** | From `sampleset.solver` or default | Extracts solver name when available |

### Important Notes

0. **Tags are metadata (and influence adapter selection), not backend overrides**:
   - Tags (like `sdk`, `algorithm`, `dataset`, `test`) are **user-supplied** metadata.
   - QObserva uses the `sdk` tag to make adapter selection deterministic.
   - **Today, tags do not override** `backend.provider` / `backend.name`. Those fields are **best-effort extracted** from the SDK result object, and if missing, QObserva falls back to **sensible defaults** (e.g., `local_sim`, `default.qubit`).

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

## Documentation

- **[Getting Started](docs/GETTING_STARTED.md)** — Minimal path: install, start, run one example, view dashboard
- **[Testing Guide](docs/TESTING_GUIDE.md)** — Full guide: setup, SDK examples, version requirements, viewing results
- **[API Reference](docs/API_REFERENCE.md)** — `@observe_run` decorator parameters and behavior
- **[SDK Compatibility](docs/SDK_COMPATIBILITY.md)** — Python and SDK version matrix, limitations
- **[Troubleshooting](docs/TROUBLESHOOTING.md)** — Common errors, FAQ, and solutions
- [Examples](examples/) — SDK-specific example scripts with proper project names and tags
- [Project Status](STATUS.md) — Detailed progress, work log, and roadmap
- [Adapter Selection Flow](ADAPTER_SELECTION_FLOW.md)
- [Specifications](spec/) — Architecture and design specifications

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

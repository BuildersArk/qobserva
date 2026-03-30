# QObserva

Quantum program observability and benchmarking. Local-first, security-first observability for quantum computing.

> ⚠️ **Beta:** QObserva is currently in beta. APIs may change.

## Quick Start

### Prerequisites

- **Python 3.10+** (see [Python Version Compatibility](#python-version-compatibility) for SDK-specific requirements)
- **Node.js** (for React dashboard)

**Recommendation:** For best compatibility with all SDKs, use **Python 3.12**.

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
git clone https://github.com/BuildersArk/qobserva.git
cd qobserva
pip install -e packages/qobserva_agent
pip install -e packages/qobserva_collector
pip install -e packages/qobserva_local
pip install -e packages/qobserva
# One-time: cd packages/qobserva_ui_react && npm install
```

### Start QObserva

```bash
qobserva up
```

Dashboard opens at **http://localhost:3000**

### Stop QObserva

```bash
qobserva down
```

## What is QObserva?

QObserva provides standardized telemetry, metrics, and visualizations for quantum program executions across all major Python quantum SDKs.

### Features

- **Decorator-first instrumentation**: `@observe_run()` decorator with a simple API
- **Multi-SDK support**: Qiskit, Braket, Cirq, PennyLane, pyQuil, D-Wave (all tested)
- **Professional React dashboard**: Modern dark-themed UI with diverse visualizations
  - Home dashboard with KPIs, trends, and run tables
  - Analytics dashboard with performance metrics and comparisons
  - Algorithm analytics for cross-SDK algorithm comparison
  - Run details with comprehensive quantum metrics
  - Compare runs side-by-side, search and filter, PDF report generation
- **Local-first**: Everything runs locally, no cloud required
- **Standardized schema**: Common event format across all SDKs
- **One-command setup**: `qobserva up` starts collector and dashboard
- **Energy metrics**: D-Wave optimization metrics (energy, approximation ratio)
- **Comprehensive metrics**: Entropy, top-K dominance, shot efficiency, runtime analysis

## Usage

### Instrument Your Code

**Always include the `sdk` tag for reliable adapter selection.**

```python
from qobserva import observe_run

@observe_run(
    project="my_project",
    tags={
        "sdk": "qiskit",       # Required
        "algorithm": "vqe"     # Optional but recommended
    },
    benchmark_id="vqe_h2_ground_state",
    benchmark_params={"energy": -1.137, "convergence_iterations": 10}
)
def my_quantum_algorithm():
    # Your quantum code here
    return execute_quantum_circuit()
```

**Supported SDK values:** `"qiskit"`, `"braket"`, `"cirq"`, `"pennylane"`, `"pyquil"`, `"dwave"`

Add an `"algorithm"` tag (e.g. `"vqe"`, `"grover"`, `"qaoa"`) to enable algorithm-specific dashboards and cross-SDK comparison.

### View Dashboard

Open http://localhost:3000 for:

- **Home**: Real-time run metrics, KPIs, success rate trends
- **Analytics**: Performance analysis and trends
- **Algorithms**: Algorithm-specific metrics and cross-SDK comparison (with algorithm tags)
- **Compare**: Side-by-side run comparison, search and filter

## Architecture

- **qobserva-agent**: Telemetry agent with decorators and adapters for all major quantum SDKs
- **qobserva-collector**: FastAPI service for ingestion, validation, and storage
- **qobserva-local**: One-command orchestrator for the local stack (includes React dashboard)
- **qobserva**: This meta-package and CLI (`qobserva up` / `qobserva down`)

The React dashboard is part of the local stack and runs automatically when you run `qobserva up`.

## SDK Support

```bash
pip install qobserva-agent[all-sdks]

# Or individual SDKs
pip install qobserva-agent[qiskit]
pip install qobserva-agent[braket]
pip install qobserva-agent[cirq]
pip install qobserva-agent[pennylane]
pip install qobserva-agent[pyquil]
pip install qobserva-agent[dwave]
```

### Python Version Compatibility

| SDK     | Python Version   | Notes |
|--------|------------------|--------|
| Qiskit | 3.10+            | 3.10–3.14 |
| Braket | 3.10 – 3.13      | **3.14+ not supported** (Braket uses Pydantic v1) |
| Cirq   | 3.10+            | 3.10–3.14 |
| PennyLane | 3.10+         | 3.10–3.14 |
| pyQuil | 3.10 – 3.12      | **3.13+ not supported** (PyQuil 4.x) |
| D-Wave | 3.10+            | 3.10–3.14 |

**Recommendations:** Use **Python 3.12** for all 6 SDKs; **Python 3.13** if you don’t need pyQuil.

## Project, Provider, and Backend

- **Project**: From `@observe_run(project="...")` — user-defined, for grouping runs.
- **Provider**: Extracted from the result (e.g. `ibm`, `aws_braket`, `local_sim`).
- **Backend**: Extracted from the result (e.g. `ibm_brisbane`, `default.qubit`).

Filter by these in the dashboard to compare providers and backends. Always set `tags={"sdk": "..."}` so adapter selection is correct.

## Documentation

- [Getting Started](https://github.com/BuildersArk/qobserva/blob/main/docs/GETTING_STARTED.md)
- [Testing Guide](https://github.com/BuildersArk/qobserva/blob/main/docs/TESTING_GUIDE.md)
- [API Reference](https://github.com/BuildersArk/qobserva/blob/main/docs/API_REFERENCE.md)
- [SDK Compatibility](https://github.com/BuildersArk/qobserva/blob/main/docs/SDK_COMPATIBILITY.md)
- [Troubleshooting](https://github.com/BuildersArk/qobserva/blob/main/docs/TROUBLESHOOTING.md)

## Links

- **Website**: [qobserva.com](https://qobserva.com)
- **Documentation**: [qobserva.com/docs.html](https://qobserva.com/docs.html)
- **GitHub**: [github.com/BuildersArk/qobserva](https://github.com/BuildersArk/qobserva)
- **Issues**: [github.com/BuildersArk/qobserva/issues](https://github.com/BuildersArk/qobserva/issues)

## Reporting Issues / Getting Help

If you encounter bugs, have questions, or would like to request features for the `qobserva` CLI / meta-package, please open an issue on GitHub:

- [https://github.com/BuildersArk/qobserva/issues](https://github.com/BuildersArk/qobserva/issues)

## License

The `qobserva` meta-package and CLI are provided under the
**QObserva Community License v1.0** (source-available). See the `LICENSE` file in this
package for full terms. Commercial hosting, distribution of modified versions, or
commercial products based on QObserva require a separate license from BuildersArk LLC.

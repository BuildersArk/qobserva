# QObserva Testing Guide

This guide shows you how to test QObserva with real quantum SDK examples, including setup, deployment, and viewing results.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [SDK-Specific Examples](#sdk-specific-examples)
4. [Project Names and Tags](#project-names-and-tags)
5. [Version Requirements and Limitations](#version-requirements-and-limitations)
6. [Running Tests](#running-tests)
7. [Viewing Results](#viewing-results)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Python Version

**Recommended: Python 3.12** (supports all 6 SDKs)

| SDK | Python Version | Notes |
|-----|----------------|-------|
| **Qiskit** | 3.10+ | Works with Python 3.10-3.14 |
| **Braket** | 3.10 - 3.13 | **Python 3.14+ NOT supported** (Braket SDK uses Pydantic v1) |
| **Cirq** | 3.10+ | Works with Python 3.10-3.14 |
| **PennyLane** | 3.10+ | Works with Python 3.10-3.14 |
| **pyQuil** | 3.10 - 3.12 | **Python 3.13+ NOT supported** (PyQuil 4.x uses PyO3 0.20.3) |
| **D-Wave** | 3.10+ | Works with Python 3.10-3.14 |

### Install QObserva

```bash
# From qobserva root directory
pip install -e packages/qobserva_agent
pip install -e packages/qobserva_collector
pip install -e packages/qobserva_local
pip install -e packages/qobserva

# Install React dashboard dependencies (one-time)
cd packages/qobserva_ui_react
npm install
cd ../..
```

### Install SDK Dependencies

Install only the SDKs you want to test:

```bash
# Qiskit (latest 2026 - version 1.2+)
pip install --upgrade "qiskit>=1.2.0"

# Braket (latest 2026 - version 1.80+)
# ⚠️ Requires Python 3.13 or earlier
pip install --upgrade "amazon-braket-sdk>=1.80.0"

# Cirq (latest 2026 - version 1.3+)
pip install --upgrade "cirq>=1.3.0"

# PennyLane (latest 2026 - version 0.40+)
pip install --upgrade "pennylane>=0.40.0"

# pyQuil (version 4.0+)
# ⚠️ Requires Python 3.12 or earlier AND Rust/Cargo
# See troubleshooting section below
pip install --upgrade "pyquil>=4.0.0"

# D-Wave (latest 2026 - version 0.12.21)
pip install --upgrade "dimod>=0.12.20"
```

## Quick Start

### 1. Start QObserva

```bash
# Start collector and React dashboard
qobserva up
```

This starts:
- **Collector** on http://localhost:8080
- **React Dashboard** on http://localhost:3000

### 2. Run an Example

```bash
# Run a Qiskit example
python examples/qiskit_example.py
```

### 3. View Results

Open http://localhost:3000 in your browser and filter by project (e.g., `qiskit_test`).

## SDK-Specific Examples

### Qiskit

**Project Name:** `qiskit_test`

**Example:**
```python
from qobserva import observe_run
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

@observe_run(
    project="qiskit_test",
    tags={"sdk": "qiskit", "algorithm": "bell_state", "test": "entanglement"},
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],
        "expected_success_rate": 0.95,
    }
)
def run_bell_state():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    
    sampler = StatevectorSampler()
    job = sampler.run([qc], shots=1024)
    return job.result()

if __name__ == "__main__":
    run_bell_state()
    print("Done! Check QObserva dashboard at http://localhost:3000")
```

**Version Requirements:**
- Qiskit >= 1.2.0
- Python 3.10+

**Limitations:**
- None (most compatible SDK)

### Amazon Braket

**Project Name:** `braket_test`

**Example:**
```python
from qobserva import observe_run
from braket.circuits import Circuit
from braket.devices import LocalSimulator

@observe_run(
    project="braket_test",
    tags={"sdk": "braket", "algorithm": "bell_state", "test": "entanglement"},
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],
        "expected_success_rate": 0.95,
    }
)
def run_bell_state():
    bell = Circuit().h(0).cnot(0, 1)
    device = LocalSimulator()
    task = device.run(bell, shots=1024)
    return task.result()

if __name__ == "__main__":
    run_bell_state()
    print("Done! Check QObserva dashboard at http://localhost:3000")
```

**Version Requirements:**
- amazon-braket-sdk >= 1.80.0
- **Python 3.10 - 3.13 ONLY** (Python 3.14+ NOT supported)

**Limitations:**
- ⚠️ **Python 3.14+ incompatible** - Braket SDK uses Pydantic v1 internally
- If using Python 3.14+, use a virtual environment with Python 3.13:
  ```bash
  python3.13 -m venv braket_env
  braket_env\Scripts\activate  # Windows
  # braket_env/bin/activate  # Linux/Mac
  pip install -e packages/qobserva_agent[braket]
  ```

### Cirq

**Project Name:** `cirq_test`

**Example:**
```python
from qobserva import observe_run
import cirq

@observe_run(
    project="cirq_test",
    tags={"sdk": "cirq", "algorithm": "bell_state", "test": "entanglement"},
    benchmark_id="bell_state_2qubit",
    measurement_key="result",  # Required for Cirq!
    benchmark_params={
        "target_bitstrings": ["00", "11"],
        "expected_success_rate": 0.95,
    }
)
def run_bell_state():
    q0, q1 = cirq.LineQubit(0), cirq.LineQubit(1)
    circuit = cirq.Circuit()
    circuit.append(cirq.H(q0))
    circuit.append(cirq.CNOT(q0, q1))
    circuit.append(cirq.measure(q0, q1, key='result'))
    
    simulator = cirq.Simulator()
    result = simulator.run(circuit, repetitions=1024)
    return result

if __name__ == "__main__":
    run_bell_state()
    print("Done! Check QObserva dashboard at http://localhost:3000")
```

**Version Requirements:**
- cirq >= 1.3.0
- Python 3.10+

**Limitations:**
- ⚠️ **Must specify `measurement_key`** parameter matching the measurement key in your circuit
- Example: If circuit uses `cirq.measure(q0, q1, key='result')`, set `measurement_key="result"`

### PennyLane

**Project Name:** `pennylane_test`

**Example:**
```python
from qobserva import observe_run
import pennylane as qml

@observe_run(
    project="pennylane_test",
    tags={"sdk": "pennylane", "algorithm": "bell_state", "test": "entanglement"},
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],
        "expected_success_rate": 0.95,
    }
)
def run_bell_state():
    dev = qml.device("default.qubit", wires=2, shots=1024)
    
    @qml.qnode(dev)
    def bell_circuit():
        qml.Hadamard(wires=0)
        qml.CNOT(wires=[0, 1])
        return qml.counts()
    
    counts = bell_circuit()
    return counts

if __name__ == "__main__":
    run_bell_state()
    print("Done! Check QObserva dashboard at http://localhost:3000")
```

**Version Requirements:**
- pennylane >= 0.40.0
- Python 3.10+

**Limitations:**
- None (works well with counts dicts)

### pyQuil

**Project Name:** `pyquil_test`

**Example:**
```python
from qobserva import observe_run
from pyquil import Program
from pyquil.gates import H, CNOT, MEASURE

@observe_run(
    project="pyquil_test",
    tags={"sdk": "pyquil", "algorithm": "bell_state", "test": "entanglement"},
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],
        "expected_success_rate": 0.95,
    }
)
def run_bell_state():
    program = Program()
    ro = program.declare("ro", "BIT", 2)
    program += H(0)
    program += CNOT(0, 1)
    program += MEASURE(0, ro[0])
    program += MEASURE(1, ro[1])
    
    try:
        from pyquil import get_qc
        qc = get_qc("2q-qvm")
        program.wrap_in_numshots_loop(1024)
        result = qc.run(program)
    except Exception as e:
        print(f"QVM not available ({e}), using simulated results")
        import random
        result = [[0, 0] if random.random() < 0.5 else [1, 1] for _ in range(1024)]
    
    return result

if __name__ == "__main__":
    run_bell_state()
    print("Done! Check QObserva dashboard at http://localhost:3000")
```

**Version Requirements:**
- pyquil >= 4.0.0
- **Python 3.10 - 3.12 ONLY** (Python 3.13+ NOT supported)
- **Rust/Cargo** required for building

**Limitations:**
- ⚠️ **Python 3.13+ incompatible** - PyQuil 4.x uses PyO3 0.20.3 which supports up to Python 3.12
- ⚠️ **Requires Rust/Cargo** for building from source:
  - Windows: Download from https://rustup.rs/
  - Linux/Mac: `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`
- QVM server recommended but not required (can return list of bitstrings)

### D-Wave

**Project Name:** `dwave_test`

**Example:**
```python
from qobserva import observe_run
import dimod

@observe_run(
    project="dwave_test",
    tags={"sdk": "dwave", "algorithm": "qubo", "test": "optimization"},
    benchmark_id="qubo_3var",
    benchmark_params={
        "problem_type": "qubo",
        "num_variables": 3,
    }
)
def run_qubo():
    Q = {
        (0, 0): -1,
        (0, 1): 1,
        (1, 2): 1,
    }
    
    bqm = dimod.BinaryQuadraticModel.from_qubo(Q)
    solver = dimod.ExactSolver()
    sampleset = solver.sample(bqm)
    return sampleset

if __name__ == "__main__":
    run_qubo()
    print("Done! Check QObserva dashboard at http://localhost:3000")
```

**Version Requirements:**
- dimod >= 0.12.20
- Python 3.10+

**Limitations:**
- None (works well with ExactSolver)
- Shows energy metrics instead of success rate (optimization problems)

## Project Names and Tags

### Project Names

Use descriptive project names that identify the SDK and purpose:

| SDK | Recommended Project Name | Example |
|-----|-------------------------|---------|
| Qiskit | `qiskit_test` | `project="qiskit_test"` |
| Braket | `braket_test` | `project="braket_test"` |
| Cirq | `cirq_test` | `project="cirq_test"` |
| PennyLane | `pennylane_test` | `project="pennylane_test"` |
| pyQuil | `pyquil_test` | `project="pyquil_test"` |
| D-Wave | `dwave_test` | `project="dwave_test"` |

### Tags

**Required Tags:**
- `sdk`: Always include the SDK name (`"qiskit"`, `"braket"`, `"cirq"`, `"pennylane"`, `"pyquil"`, `"dwave"`)

**Recommended Tags:**
- `algorithm`: Algorithm type (`"bell_state"`, `"grover"`, `"vqe"`, `"qubo"`, etc.)
- `test`: Test category (`"entanglement"`, `"optimization"`, `"variational"`, etc.)

**Example:**
```python
tags={
    "sdk": "qiskit",           # Required
    "algorithm": "bell_state", # Recommended
    "test": "entanglement"     # Recommended
}
```

## Version Requirements and Limitations

### Summary Table

| SDK | Minimum Version | Python Version | Special Requirements |
|-----|----------------|----------------|---------------------|
| Qiskit | 1.2.0 | 3.10+ | None |
| Braket | 1.80.0 | 3.10 - 3.13 | ⚠️ Python 3.14+ NOT supported |
| Cirq | 1.3.0 | 3.10+ | ⚠️ Must specify `measurement_key` |
| PennyLane | 0.40.0 | 3.10+ | None |
| pyQuil | 4.0.0 | 3.10 - 3.12 | ⚠️ Python 3.13+ NOT supported, Rust required |
| D-Wave | 0.12.20 | 3.10+ | None |

### Known Limitations

1. **Braket Python 3.14+ Incompatibility**
   - Braket SDK uses Pydantic v1 internally
   - Pydantic v1 doesn't support Python 3.14+
   - **Solution:** Use Python 3.13 or earlier, or use a virtual environment

2. **pyQuil Python 3.13+ Incompatibility**
   - PyQuil 4.x uses PyO3 0.20.3
   - PyO3 0.20.3 supports up to Python 3.12
   - **Solution:** Use Python 3.12 or earlier

3. **pyQuil Rust Requirement**
   - PyQuil 4.x requires Rust/Cargo to build from source
   - **Solution:** Install Rust from https://rustup.rs/ or use pre-built wheels

4. **Cirq Measurement Key Requirement**
   - Cirq adapter requires `measurement_key` parameter
   - Must match the key used in `cirq.measure()`
   - **Solution:** Always specify `measurement_key` matching your circuit

## Running Tests

### Step 1: Start QObserva

```bash
# Start collector and dashboard
qobserva up
```

Wait until you see:
- "Collector started on http://localhost:8080"
- "UI started on http://localhost:3000"

### Step 2: Run Examples

**From examples folder:**
```bash
# Run individual examples
python examples/qiskit_example.py
python examples/braket_example.py
python examples/cirq_example.py
python examples/pennylane_example.py
python examples/pyquil_example.py
python examples/dwave_example.py
```

You can also create your own local test suites following the patterns in the `examples/` directory (these are not part of the published package).

### Step 3: Verify Results

Check the console output for:
- "Done! Check QObserva dashboard at http://localhost:3000"
- Measurement results (if printed)

## Viewing Results

### 1. Open Dashboard

Navigate to http://localhost:3000 in your browser.

### 2. Filter by Project

- Click on the **Filter** icon or use the search bar
- Filter by **Project** (e.g., `qiskit_test`, `braket_test`)
- All runs for that project will appear

### 3. View Run Details

- Click on any run in the **Home** dashboard
- See detailed metrics:
  - Success rate
  - Circuit depth
  - Number of qubits
  - Execution time
  - Measurement counts
  - Provider and backend information

### 4. Compare Runs

- Use the **Compare** dashboard to compare multiple runs side-by-side
- Filter by algorithm tag to compare same algorithms across SDKs

### 5. Analytics

- View trends in the **Analytics** dashboard
- See performance comparisons
- Analyze success rates over time

## Troubleshooting

### Braket Import Error (Python 3.14+)

**Error:** `ConfigError` or `Pydantic` related errors

**Solution:**
```bash
# Use Python 3.13 virtual environment
python3.13 -m venv braket_env
braket_env\Scripts\activate  # Windows
# braket_env/bin/activate  # Linux/Mac
pip install -e packages/qobserva_agent[braket]
```

### pyQuil Rust Error

**Error:** `error: failed to run custom build command for 'quil-sys'`

**Solution:**
1. Install Rust: https://rustup.rs/
2. Restart terminal
3. Try installing again: `pip install --upgrade "pyquil>=4.0.0"`

### Cirq No Counts Found

**Error:** No measurement counts in dashboard

**Solution:**
- Ensure `measurement_key` parameter matches your circuit's measurement key
- Example: If circuit uses `cirq.measure(q0, q1, key='result')`, set `measurement_key="result"`

### QObserva Not Running

**Error:** Connection refused or dashboard not accessible

**Solution:**
```bash
# Show CLI commands
qobserva --help

# Start if not running
qobserva up

# Check ports
# Collector: http://localhost:8080
# Dashboard: http://localhost:3000
```

### No Runs Appearing

**Check:**
1. QObserva collector is running (`qobserva up`)
2. Example script completed successfully (no errors)
3. Project name matches filter (e.g., `qiskit_test`)
4. Check browser console for errors

## Next Steps

- See [examples/README.md](../examples/README.md) for more example code
- See [README.md](../README.md) for general QObserva documentation

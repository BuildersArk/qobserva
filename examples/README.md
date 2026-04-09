# QObserva Examples (BYOE)

These examples show how to integrate QObserva in your code using `@observe_run`.

**📖 For comprehensive testing instructions, see [docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)**

## ⚠️ Important: SDK Tag is Required

**Always include `tags={"sdk": "..."}` in your decorator** for reliable adapter selection. Without it, QObserva may incorrectly identify the SDK, leading to wrong provider/backend values.

## Quick Start

### 1. Install QObserva

```bash
# From qobserva root directory
pip install qobserva
```

### 2. Install SDK Dependencies

QObserva does **not** execute workloads for you (BYOE). Each provider/SDK has its own dependency set. Install only what you need:

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
pip install --upgrade "pyquil>=4.0.0"

# D-Wave (latest 2026 - version 0.12.21)
pip install --upgrade "dimod>=0.12.20"
```

### 3. Start QObserva

```bash
# Start collector and React dashboard
qobserva up
```

This starts:
- **Collector** on http://localhost:8080
- **React Dashboard** on http://localhost:3000

### 4. Run Examples

```bash
# Run individual examples
python examples/qiskit_example.py
python examples/braket_example.py
python examples/cirq_example.py
python examples/pennylane_example.py
python examples/pyquil_example.py
python examples/dwave_example.py
```

### 5. View Results

Open http://localhost:3000 in your browser and filter by project (e.g., `qiskit_test`, `braket_test`).

## Python Version Compatibility

| SDK | Python Version | Notes |
|-----|----------------|-------|
| **Qiskit** | 3.10+ | Works with Python 3.10-3.14 |
| **Braket** | 3.10 - 3.13 | **Python 3.14+ NOT supported** (Braket SDK uses Pydantic v1) |
| **Cirq** | 3.10+ | Works with Python 3.10-3.14 |
| **PennyLane** | 3.10+ | Works with Python 3.10-3.14 |
| **pyQuil** | 3.10 - 3.12 | **Python 3.13+ NOT supported** (PyQuil 4.x uses PyO3 0.20.3) |
| **D-Wave** | 3.10+ | Works with Python 3.10-3.14 |

**Recommended:** Use **Python 3.12** for best compatibility with all SDKs.

## Examples

All examples use proper project names and tags for testing:

- `qiskit_example.py` - Qiskit with StatevectorSampler (project: `qiskit_test`)
- `braket_example.py` - AWS Braket with LocalSimulator (project: `braket_test`)
- `cirq_example.py` - Cirq with measurement_key (project: `cirq_test`)
- `pennylane_example.py` - PennyLane with counts dict (project: `pennylane_test`)
- `pyquil_example.py` - pyQuil with QVM (project: `pyquil_test`)
- `dwave_example.py` - D-Wave with ExactSolver (project: `dwave_test`)
- `basic_counts_dict.py` - Minimal example with plain dict

## Project Names and Tags

### Project Names

Examples use descriptive project names:
- `qiskit_test` - For Qiskit examples
- `braket_test` - For Braket examples
- `cirq_test` - For Cirq examples
- `pennylane_test` - For PennyLane examples
- `pyquil_test` - For pyQuil examples
- `dwave_test` - For D-Wave examples

### Tags

**Required:**
- `sdk`: SDK name (`"qiskit"`, `"braket"`, `"cirq"`, `"pennylane"`, `"pyquil"`, `"dwave"`)

**Recommended:**
- `algorithm`: Algorithm type (`"bell_state"`, `"grover"`, `"vqe"`, `"qubo"`, etc.)
- `test`: Test category (`"entanglement"`, `"optimization"`, `"variational"`, etc.)

## Version Requirements and Limitations

### Summary

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
   - **Solution:** Use Python 3.13 or earlier, or use a virtual environment

2. **pyQuil Python 3.13+ Incompatibility**
   - PyQuil 4.x uses PyO3 0.20.3
   - **Solution:** Use Python 3.12 or earlier

3. **pyQuil Rust Requirement**
   - PyQuil 4.x requires Rust/Cargo to build from source
   - **Solution:** Install Rust from https://rustup.rs/

4. **Cirq Measurement Key Requirement**
   - Cirq adapter requires `measurement_key` parameter
   - Must match the key used in `cirq.measure()`
   - **Solution:** Always specify `measurement_key` matching your circuit

## More Examples

For more comprehensive guidance and patterns, see:
- **[docs/TESTING_GUIDE.md](../docs/TESTING_GUIDE.md)** - Complete testing guide with setup, deploy, and viewing instructions

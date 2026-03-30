# SDK Compatibility

Canonical reference for Python and SDK version support.

## Recommended setup

- **Python:** **3.12** (supports all 6 SDKs).
- **SDK extras:** Install only what you need, e.g. `pip install -e packages/qobserva_agent[qiskit]`.

## Python version by SDK

| SDK       | Python version | Notes |
|----------|----------------|--------|
| **Qiskit**   | 3.10+ | 3.10–3.14 supported. |
| **Braket**   | 3.10–3.13 | **Python 3.14+ not supported** (Braket uses Pydantic v1). |
| **Cirq**     | 3.10+ | 3.10–3.14 supported. |
| **PennyLane**| 3.10+ | 3.10–3.14 supported. |
| **pyQuil**   | 3.10–3.12 | **Python 3.13+ not supported** (PyQuil 4.x / PyO3 0.20.3). |
| **D-Wave**   | 3.10+ | 3.10–3.14 supported. |

## SDK version requirements

| SDK       | Minimum version | Notes |
|----------|-----------------|--------|
| **Qiskit**   | 1.2.0 | Prefer StatevectorSampler for 2.x-style usage. |
| **Braket**   | 1.80.0 | Use LocalSimulator for local runs. |
| **Cirq**     | 1.3.0 | Must pass `measurement_key` to `@observe_run` for counts. |
| **PennyLane**| 0.40.0 | Works with `qml.counts()`. |
| **pyQuil**   | 4.0.0 | Requires Rust/Cargo to build from source. |
| **D-Wave**   | dimod 0.12.20 | e.g. `dimod>=0.12.20`. |

## Limitations and workarounds

### Braket (Python 3.14+)

- **Limit:** Braket SDK uses Pydantic v1; not compatible with Python 3.14+.
- **Workaround:** Use Python 3.13 or earlier, or a venv with 3.13.

### pyQuil (Python 3.13+)

- **Limit:** PyQuil 4.x uses PyO3 0.20.3; supports up to Python 3.12.
- **Workaround:** Use Python 3.12 or earlier, or a venv with 3.12.

### pyQuil (Rust)

- **Limit:** Building pyQuil from source requires Rust/Cargo.
- **Workaround:** Install Rust from https://rustup.rs/ or use a pre-built wheel if available.

### Cirq (measurement key)

- **Limit:** Counts are read from the result using a measurement key.
- **Workaround:** Always set `measurement_key="..."` in `@observe_run` to match `cirq.measure(..., key="...")`.

## Single-environment options

- **All 6 SDKs:** Python **3.12**.
- **All except pyQuil:** Python **3.13**.
- **All except Braket:** Python **3.14** (when available).

QObserva core works on Python 3.10+; limits above come from the SDKs, not QObserva.

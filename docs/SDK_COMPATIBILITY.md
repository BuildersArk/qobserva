# SDK Compatibility

Canonical reference for Python and SDK version support.

## Recommended setup

- **Python 3.12** runs all 6 SDKs in one environment.
- **Python 3.13 or 3.14** runs every SDK except pyQuil.
- **SDK extras:** Install only what you need, e.g. `pip install qobserva-agent[qiskit]`.

## Verified Python support

Each ✅ below means the SDK's example script ran on Windows and QObserva recorded the run correctly (counts or energies, shots, backend). These runs were done in September 2026 with the SDK versions listed.

| SDK | Version tested | 3.12 | 3.13 | 3.14 | Notes |
|-----|----------------|------|------|------|-------|
| **Qiskit** | qiskit 2.5.2 (+ qiskit-aer 0.17.2, qiskit-ibm-runtime 0.49.0) | ✅ | ✅ | ✅ | |
| **Braket** | amazon-braket-sdk 1.127.1 | ✅ | ✅ | ✅ | Python 3.14 is now supported (the old Pydantic v1 limitation is gone). |
| **Cirq** | cirq 1.7.0 | ✅ | ✅ | ✅ | |
| **PennyLane** | pennylane 0.45.1 | ✅ | ✅ | ✅ | |
| **pyQuil** | pyquil 4.20.0 | ✅ | ❌ | ❌ | pyQuil itself requires Python `>=3.11,<3.13`. Tested against the Rigetti QVM. |
| **D-Wave** | dimod 0.12.22 | ✅ | ✅ | ✅ | |

Python 3.10 and 3.11: QObserva itself is tested on them in CI; the SDKs were not re-verified there. Current pyQuil releases need Python 3.11 or later.

QObserva core works on Python 3.10+; the limits above come from the SDKs, not QObserva.

## SDK version requirements

| SDK | Minimum version | Notes |
|-----|-----------------|-------|
| **Qiskit** | 1.2.0 | V2 primitive results don't name their backend. See [API Reference](API_REFERENCE.md#qiskit). |
| **Braket** | 1.80.0 | Use LocalSimulator for local runs. |
| **Cirq** | 1.3.0 | Must pass `measurement_key` to `@observe_run` for counts. |
| **PennyLane** | 0.40.0 | Works with `qml.counts()` and `qml.expval()`. |
| **pyQuil** | 4.0.0 | Requires the Rigetti QVM and quilc servers (e.g. `docker run -d -p 5000:5000 rigetti/qvm -S` and `docker run -d -p 5555:5555 rigetti/quilc -R`). |
| **D-Wave** | dimod 0.12.20 | Pass the sampler as `backend=` to record which sampler ran. |

## Limitations and workarounds

### pyQuil (Python 3.13+)

- **Limit:** Current pyQuil releases declare `requires_python >=3.11,<3.13`. On 3.13+, pip falls back to an old pyQuil (4.16.2) that fails on import. `qobserva-agent[pyquil]` therefore skips pyQuil on 3.13+.
- **Workaround:** Use a Python 3.12 virtual environment for pyQuil.

### Cirq (measurement key)

- **Limit:** Counts are read from the result using a measurement key.
- **Workaround:** Always set `measurement_key="..."` in `@observe_run` to match `cirq.measure(..., key="...")`.

### Windows long paths (D-Wave)

- **Limit:** dimod's compiled modules fail to load with `DLL load failed ... The filename or extension is too long` when the virtual environment sits in a very deep folder.
- **Workaround:** Create the venv in a short path (e.g. `C:\venvs\qobserva`) or enable Windows long path support.

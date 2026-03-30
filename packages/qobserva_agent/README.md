# qobserva-agent

**Decorator-first telemetry for quantum runs:** emit standardized run events for Qiskit, Braket, Cirq, PennyLane, pyQuil, and D-Wave (BYOE — bring your own endpoint).

> ⚠️ **Beta:** This package is in beta. APIs may change.

## Install

```bash
pip install qobserva-agent
```

Optional SDK extras (install only what you use):

```bash
pip install qobserva-agent[qiskit]      # Qiskit
pip install qobserva-agent[braket]     # Amazon Braket
pip install qobserva-agent[cirq]        # Cirq
pip install qobserva-agent[pennylane]  # PennyLane
pip install qobserva-agent[pyquil]      # pyQuil
pip install qobserva-agent[dwave]      # D-Wave
pip install qobserva-agent[all-sdks]   # All of the above
```

## Quick start

```python
from qobserva import observe_run

@observe_run(project="demo", tags={"sdk": "qiskit"})
def run():
    # your quantum run here
    return {"counts": {"00": 5, "11": 5}, "shots": 10}

run()
```

Point the agent at your local collector with `QOBSERVA_COLLECTOR_URL` (or use `qobserva up` to start the stack).

- **Full docs:** [qobserva.com](https://qobserva.com) · [Documentation](https://qobserva.com/docs.html)
- **Repo:** [GitHub — BuildersArk/qobserva](https://github.com/BuildersArk/qobserva)
- **Issues / Support:** [GitHub Issues](https://github.com/BuildersArk/qobserva/issues)

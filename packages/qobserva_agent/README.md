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

Start the local collector and dashboard with `pip install qobserva` and `qobserva up`, then open http://localhost:3000.
To send runs elsewhere, set `QOBSERVA_ENDPOINT` (default `http://127.0.0.1:8080/v1/ingest/run-event`).

Runs are sent in the background, so telemetry never slows your program. If the collector isn't running, you get one warning and your code continues. Secrets in error messages are redacted, and the hostname is stored as a hash (`QOBSERVA_HOST_MODE=raw|hash|none`).

- **Full docs:** [qobserva.com](https://qobserva.com) · [Documentation](https://qobserva.com/docs.html)
- **Repo:** [GitHub — BuildersArk/qobserva](https://github.com/BuildersArk/qobserva)
- **Issues / Support:** [GitHub Issues](https://github.com/BuildersArk/qobserva/issues)

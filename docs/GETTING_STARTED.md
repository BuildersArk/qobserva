# Getting Started with QObserva

Get from zero to your first observed run in a few minutes.

## 1. Install QObserva

```bash
pip install qobserva "qobserva-agent[qiskit]"
```

Use `qobserva-agent[braket]`, `[cirq]`, `[pennylane]`, `[pyquil]`, `[dwave]` or `[all-sdks]` for other SDKs. Python 3.12 supports all six; see [SDK Compatibility](SDK_COMPATIBILITY.md).

<details>
<summary>Installing from a source checkout instead</summary>

```bash
git clone https://github.com/BuildersArk/qobserva.git
cd qobserva
pip install -e packages/qobserva_agent -e packages/qobserva_collector -e packages/qobserva_local -e packages/qobserva
cd packages/qobserva_ui_react && npm install && cd ../..   # dashboard dev server (needs Node.js)
```
</details>

## 2. Start QObserva

```bash
qobserva up
```

This starts the collector (http://127.0.0.1:8080) and the dashboard (**http://localhost:3000**). Leave it running; stop it later with Ctrl+C or `qobserva down`.

## 3. Run an instrumented program

In another terminal, save this as `bell.py` and run `python bell.py`:

```python
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler
from qobserva import observe_run

@observe_run(
    project="qiskit_test",
    tags={"sdk": "qiskit", "algorithm": "bell_state"},
    benchmark_params={"target_bitstrings": ["00", "11"]},
    backend="statevector_sampler",  # Qiskit V2 primitive results don't name their backend
    provider="local_sim",
)
def run():
    qc = QuantumCircuit(2, 2)
    qc.h(0)
    qc.cx(0, 1)
    qc.measure([0, 1], [0, 1])
    return StatevectorSampler().run([qc], shots=1024).result()

run()
```

More examples for every SDK: [examples/](https://github.com/BuildersArk/qobserva/tree/main/examples).

## 4. View Results

1. Open http://localhost:3000
2. Filter by project: `qiskit_test`
3. Click a run to see metrics

---

**Next steps**

- **Full testing and examples:** [Testing Guide](TESTING_GUIDE.md)
- **Python/SDK versions:** [SDK Compatibility](SDK_COMPATIBILITY.md)
- **Decorator parameters and settings:** [API Reference](API_REFERENCE.md)
- **Problems?** [Troubleshooting](TROUBLESHOOTING.md)

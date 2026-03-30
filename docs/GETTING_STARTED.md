# Getting Started with QObserva

Get from zero to your first observed run in a few minutes.

## 1. Install QObserva

From the repo root (or use `pip install qobserva` when published):

```bash
pip install -e packages/qobserva_agent
pip install -e packages/qobserva_collector
pip install -e packages/qobserva_local
pip install -e packages/qobserva
```

Install at least one SDK (e.g. Qiskit):

```bash
pip install --upgrade "qiskit>=1.2.0"
```

## 2. Start QObserva

```bash
qobserva up
```

Wait until the collector and UI are up. Dashboard: **http://localhost:3000**

## 3. Run an Example

In another terminal:

```bash
python examples/qiskit_example.py
```

## 4. View Results

1. Open http://localhost:3000
2. Filter by project: `qiskit_test`
3. Click a run to see metrics

---

**Next steps**

- **Full testing and examples:** [Testing Guide](TESTING_GUIDE.md)
- **Python/SDK versions:** [SDK Compatibility](SDK_COMPATIBILITY.md)
- **Decorator parameters:** [API Reference](API_REFERENCE.md)
- **Problems?** [Troubleshooting](TROUBLESHOOTING.md)

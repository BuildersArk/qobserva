# Troubleshooting & FAQ

Common issues and solutions when using QObserva.

## Common Errors

### Braket: Python 3.14+ / Pydantic errors

**Symptoms:** `ConfigError`, `ValidationError`, or import errors when using `amazon-braket-sdk`.

**Cause:** Braket SDK uses Pydantic v1, which does not support Python 3.14+.

**Fix:**

- Use **Python 3.13 or earlier** for Braket, or
- Use a dedicated virtual environment:
  ```bash
  python3.13 -m venv braket_env
  braket_env\Scripts\activate   # Windows
  # braket_env/bin/activate     # Linux/macOS
  pip install -e packages/qobserva_agent[braket]
  ```

---

### pyQuil: Rust / Cargo build error

**Symptoms:** `error: failed to run custom build command for 'quil-sys'` when installing `pyquil`.

**Cause:** pyQuil 4.x needs Rust/Cargo to build from source.

**Fix:**

1. Install Rust: https://rustup.rs/
2. Restart the terminal
3. Run again: `pip install --upgrade "pyquil>=4.0.0"`

To avoid building, you can skip pyQuil if you don’t need it.

---

### pyQuil: Python 3.13+ not supported

**Symptoms:** Build or runtime errors with pyQuil on Python 3.13+.

**Cause:** PyQuil 4.x uses PyO3 0.20.3, which supports up to Python 3.12.

**Fix:** Use **Python 3.12 or earlier** for pyQuil (e.g. a separate venv).

---

### Cirq: No measurement counts in dashboard

**Symptoms:** Run appears in UI but counts or histogram are missing.

**Cause:** Cirq adapter needs the measurement key to read counts from the result.

**Fix:** Set `measurement_key` to the same key used in `cirq.measure()`:

```python
@observe_run(
    project="cirq_test",
    tags={"sdk": "cirq", "algorithm": "bell_state"},
    measurement_key="result",   # must match cirq.measure(..., key='result')
)
def run():
    ...
    circuit.append(cirq.measure(q0, q1, key='result'))
    ...
```

---

### QObserva not running / connection refused

**Symptoms:** Script runs but nothing appears in the UI, or “connection refused” to collector.

**Fix:**

1. Start QObserva first:
   ```bash
   qobserva up
   ```
2. Verify CLI is available:
   ```bash
   qobserva --help
   ```
3. Use:
   - Collector: http://localhost:8080  
   - Dashboard: http://localhost:3000  

---

### No runs appearing in dashboard

**Check:**

1. Collector is running (`qobserva up`).
2. Your script finished without raising an uncaught exception.
3. Filter in the UI matches your `project` (e.g. `qiskit_test`).
4. Browser console (F12) for any front-end errors.

---

## FAQ

**Do I need AWS credentials for Braket examples?**  
No. The examples use `LocalSimulator`, which runs locally. For real Braket devices you need AWS credentials.

**Can I use Python 3.14?**  
Yes for Qiskit, Cirq, PennyLane, D-Wave. No for Braket (use ≤3.13) and pyQuil (use ≤3.12). See [SDK Compatibility](SDK_COMPATIBILITY.md).

**Do I have to install all 6 SDKs?**  
No. Install only the SDKs you use (e.g. `pip install -e packages/qobserva_agent[qiskit]`).

**What if I forget the `sdk` tag?**  
QObserva will try to infer the SDK from the result object. Inference can be wrong; always set `tags={"sdk": "..."}` for reliable behavior.

**Where is data stored?**  
By default, the local collector stores data in memory and serves the UI. No cloud or external storage is used unless you configure a custom endpoint.

**Can I point to a different collector?**  
Yes. Use the `endpoint` parameter of `@observe_run` (and `api_key` if your collector requires it).

---

For more detail on setup and running tests, see the [Testing Guide](TESTING_GUIDE.md).

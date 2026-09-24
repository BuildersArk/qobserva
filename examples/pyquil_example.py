"""pyQuil example (BYOE).

Install (from PyPI):
  pip install qobserva "qobserva-agent[pyquil]"
  qobserva up        # starts the collector + dashboard at http://localhost:3000
  python pyquil_example.py

Install (from a source checkout):
  pip install -e packages/qobserva_agent[pyquil]

This example uses pyQuil (version 4.0+).
Requires the Rigetti QVM and quilc servers, e.g. with Docker:
  docker run -d -p 5000:5000 rigetti/qvm -S
  docker run -d -p 5555:5555 rigetti/quilc -R

Version Requirements:
- pyquil >= 4.0.0
- Python 3.11 - 3.12 only (current pyQuil releases do not support 3.13+)

Limitations:
- QVM and quilc servers must be running (see above); otherwise the run fails and is recorded as failed
"""

from qobserva import observe_run
import sys

# pyQuil releases currently support Python 3.11-3.12 only (pyquil 4.20.0: requires_python ">=3.11,<3.13").
if not ((3, 11) <= sys.version_info[:2] < (3, 13)):
    print("pyQuil supports Python 3.11-3.12 only. Create a Python 3.12 environment for this example:")
    print("  python3.12 -m venv pyquil_env")
    print("  pip install qobserva-agent[pyquil]")
    sys.exit(1)

from pyquil import Program
from pyquil.gates import H, CNOT, MEASURE

@observe_run(
    project="pyquil_test",
    tags={"sdk": "pyquil", "algorithm": "bell_state", "test": "entanglement"},  # SDK tag is required!
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],  # Expected outcomes
        "expected_success_rate": 0.95,  # Should be close to 1.0 (50% each)
    },
    backend="2q-qvm",  # must match get_qc(...) below
    provider="local_sim",
)
def run():
    """Create and measure a Bell state on the Rigetti QVM.

    Requires the QVM and quilc servers (see the module docstring). If they are not
    running, the run fails and QObserva records it as a failed run.
    """
    from pyquil import get_qc

    # Create Bell state program
    program = Program()
    ro = program.declare("ro", "BIT", 2)
    program += H(0)
    program += CNOT(0, 1)
    program += MEASURE(0, ro[0])
    program += MEASURE(1, ro[1])
    program.wrap_in_numshots_loop(1024)

    qc = get_qc("2q-qvm")
    return qc.run(qc.compile(program))

if __name__ == "__main__":
    print("Running Bell State test with pyQuil on the QVM...")
    print("Expected: ~50% |00> and ~50% |11>")
    result = run()

    # Print results for verification
    rows = result.get_register_map()["ro"]
    counts = {}
    for row in rows:
        key = "".join(map(str, row))
        counts[key] = counts.get(key, 0) + 1
    total = sum(counts.values())
    print("\nMeasurement results:")
    for bitstring, count in sorted(counts.items()):
        print(f"  |{bitstring}>: {count} ({count / total * 100:.1f}%)")

    print("\nDone! Check QObserva dashboard at http://localhost:3000")

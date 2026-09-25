"""PennyLane example (BYOE).

Install (from PyPI):
  pip install qobserva "qobserva-agent[pennylane]"
  qobserva up        # starts the collector + dashboard at http://localhost:3000
  python pennylane_example.py

Install (from a source checkout):
  pip install -e packages/qobserva_agent[pennylane]

This example uses PennyLane default.qubit simulator (PennyLane 0.42+ / 2026).
Returns measurement counts (most common use case).

Version Requirements:
- pennylane >= 0.42.0 (for qml.set_shots; older versions set shots on the device)
- Python 3.10+ (works with Python 3.10-3.14)

Limitations:
- None (works well with counts dicts)
"""

from qobserva import observe_run
import pennylane as qml

@observe_run(
    project="pennylane_test",
    tags={"sdk": "pennylane", "algorithm": "bell_state", "test": "entanglement"},  # SDK tag is required!
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],  # Expected outcomes
        "expected_success_rate": 0.95,  # Should be close to 1.0 (50% each)
    }
)
def run():
    """Create and measure a Bell state using PennyLane default.qubit."""
    # Create a 2-qubit device
    dev = qml.device("default.qubit", wires=2)
    
    @qml.set_shots(1024)
    @qml.qnode(dev)
    def bell_circuit():
        # Create Bell state: |00⟩ -> (|00⟩ + |11⟩)/√2
        qml.Hadamard(wires=0)      # Hadamard on qubit 0
        qml.CNOT(wires=[0, 1])      # CNOT: entangles qubits
        return qml.counts()  # Return measurement counts
    
    # Execute circuit
    counts = bell_circuit()
    
    # Return counts dict - adapter will handle it
    return counts

if __name__ == "__main__":
    print("Running Bell State test with PennyLane...")
    print("Expected: ~50% |00> and ~50% |11>")
    result = run()
    
    # Print counts for verification
    if isinstance(result, dict):
        print("\nMeasurement results:")
        total = sum(result.values())
        for bitstring, count in sorted(result.items()):
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"  |{bitstring}>: {count} ({percentage:.1f}%)")
    
    print("\nDone! Check QObserva dashboard at http://localhost:3000")

"""Cirq example (BYOE).

Install:
  pip install -e packages/qobserva_agent[cirq]
  pip install --upgrade "cirq>=1.3.0"

This example uses Cirq Simulator (Cirq 1.3+ / 2026).

Version Requirements:
- cirq >= 1.3.0
- Python 3.10+ (works with Python 3.10-3.14)

Limitations:
- ⚠️ Must specify `measurement_key` parameter matching the measurement key in your circuit
- Example: If circuit uses `cirq.measure(q0, q1, key='result')`, set `measurement_key="result"`
"""

from qobserva import observe_run
import cirq

@observe_run(
    project="cirq_test",
    tags={"sdk": "cirq", "algorithm": "bell_state", "test": "entanglement"},  # SDK tag is required!
    benchmark_id="bell_state_2qubit",
    measurement_key="result",  # Required for Cirq! Must match measurement key in circuit
    benchmark_params={
        "target_bitstrings": ["00", "11"],  # Expected outcomes
        "expected_success_rate": 0.95,  # Should be close to 1.0 (50% each)
    }
)
def run():
    """Create and measure a Bell state using Cirq Simulator."""
    # Create qubits
    q0, q1 = cirq.LineQubit(0), cirq.LineQubit(1)
    
    # Create Bell state circuit: |00⟩ -> (|00⟩ + |11⟩)/√2
    circuit = cirq.Circuit()
    circuit.append(cirq.H(q0))      # Hadamard on qubit 0
    circuit.append(cirq.CNOT(q0, q1))  # CNOT: entangles qubits
    circuit.append(cirq.measure(q0, q1, key='result'))  # Measure both qubits (key must match measurement_key!)
    
    # Use Cirq Simulator
    simulator = cirq.Simulator()
    
    # Run with 1024 shots for good statistics
    result = simulator.run(circuit, repetitions=1024)
    
    # Return result - adapter will extract histogram using measurement_key
    return result

if __name__ == "__main__":
    print("Running Bell State test with Cirq...")
    print("Expected: ~50% |00> and ~50% |11>")
    result = run()
    
    # Extract and print counts for verification
    if hasattr(result, 'histogram'):
        hist = result.histogram(key='result')
        print("\nMeasurement results:")
        total = sum(hist.values())
        for bitstring, count in sorted(hist.items()):
            bitstring_str = format(bitstring, '02b')  # Format as binary
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"  |{bitstring_str}>: {count} ({percentage:.1f}%)")
    
    print("\nDone! Check QObserva dashboard at http://localhost:3000")

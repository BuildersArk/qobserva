"""Qiskit example (BYOE).

Install:
  pip install -e packages/qobserva_agent[qiskit]
  pip install --upgrade "qiskit>=1.2.0"

This example uses Qiskit StatevectorSampler (Qiskit 1.2+ / 2026).
Compatible with both Qiskit 1.2+ and 2.x APIs.

Version Requirements:
- Qiskit >= 1.2.0
- Python 3.10+ (works with Python 3.10-3.14)

Limitations:
- None (most compatible SDK)
"""

from qobserva import observe_run
from qiskit import QuantumCircuit
from qiskit.primitives import StatevectorSampler

@observe_run(
    project="qiskit_test",
    tags={"sdk": "qiskit", "algorithm": "bell_state", "test": "entanglement"},  # SDK tag is required!
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],  # Expected outcomes
        "expected_success_rate": 0.95,  # Should be close to 1.0 (50% each)
    }
)
def run():
    """Create and measure a Bell state using Qiskit StatevectorSampler."""
    # Create a 2-qubit circuit
    qc = QuantumCircuit(2, 2)
    
    # Create Bell state: |00⟩ -> (|00⟩ + |11⟩)/√2
    qc.h(0)          # Hadamard on qubit 0: |0⟩ -> (|0⟩ + |1⟩)/√2
    qc.cx(0, 1)      # CNOT: entangles qubits
    qc.measure([0, 1], [0, 1])  # Measure both qubits
    
    # Use StatevectorSampler (Qiskit 1.2+ - pure Python, no compilation needed)
    sampler = StatevectorSampler()
    
    # Run with 1024 shots for good statistics
    job = sampler.run([qc], shots=1024)
    result = job.result()
    
    # Return PrimitiveResult - adapter will extract counts from it
    return result

if __name__ == "__main__":
    print("Running Bell State test with Qiskit...")
    print("Expected: ~50% |00> and ~50% |11>")
    result = run()
    
    # Extract and print counts for verification
    pub_result = result[0]
    data = pub_result.data
    # Check meas first (for measure_all()), then c (for measure())
    meas = getattr(data, "meas", None)
    c = getattr(data, "c", None)
    if meas and hasattr(meas, "get_counts"):
        counts = meas.get_counts()
    elif c and hasattr(c, "get_counts"):
        counts = c.get_counts()
    else:
        counts = {}
    
    print("\nMeasurement results:")
    total = sum(counts.values())
    for bitstring, count in sorted(counts.items()):
        percentage = (count / total) * 100 if total > 0 else 0
        print(f"  |{bitstring}>: {count} ({percentage:.1f}%)")
    
    print("\nDone! Check QObserva dashboard at http://localhost:3000")

"""AWS Braket example (BYOE).

Install:
  pip install -e packages/qobserva_agent[braket]
  pip install --upgrade "amazon-braket-sdk>=1.80.0"

This example uses Amazon Braket LocalSimulator (Braket SDK 1.80+ / 2026).
No AWS credentials needed for LocalSimulator.

Version Requirements:
- amazon-braket-sdk >= 1.80.0
- Python 3.10 - 3.13 ONLY (Python 3.14+ NOT supported)

Limitations:
- ⚠️ Python 3.14+ incompatible - Braket SDK uses Pydantic v1 internally
- If using Python 3.14+, use a virtual environment with Python 3.13:
  python3.13 -m venv braket_env
  braket_env\\Scripts\\activate  # Windows
  pip install -e packages/qobserva_agent[braket]
"""

from qobserva import observe_run
import sys

# Check Python version first
if sys.version_info >= (3, 14):
    print("=" * 60)
    print("⚠️  Python 3.14+ Detected - Braket SDK Incompatibility")
    print("=" * 60)
    print("Braket SDK uses Pydantic v1 internally, which doesn't support Python 3.14+.")
    print("This is a known limitation of the Braket SDK.")
    print()
    print("Solutions:")
    print("1. Use Python 3.13 or earlier for Braket tests")
    print("2. Use a virtual environment with Python 3.13:")
    print("   python3.13 -m venv braket_env")
    print("   braket_env\\Scripts\\activate  # Windows")
    print("   pip install -e packages/qobserva_agent[braket]")
    print("=" * 60)
    sys.exit(1)

# Check if Braket is installed
try:
    from braket.circuits import Circuit
    from braket.devices import LocalSimulator
except ImportError as e:
    print("ERROR: Amazon Braket SDK is not installed!")
    print("Please install it with: pip install --upgrade 'amazon-braket-sdk>=1.80.0'")
    print(f"Import error: {e}")
    raise

@observe_run(
    project="braket_test",
    tags={"sdk": "braket", "algorithm": "bell_state", "test": "entanglement"},  # SDK tag is required!
    benchmark_id="bell_state_2qubit",
    benchmark_params={
        "target_bitstrings": ["00", "11"],  # Expected outcomes
        "expected_success_rate": 0.95,  # Should be close to 1.0 (50% each)
    }
)
def run():
    """Create and measure a Bell state using Braket LocalSimulator.
    
    Follows the official Braket pattern from:
    https://github.com/amazon-braket/amazon-braket-default-simulator-python
    """
    # Create Bell state using method chaining (official pattern)
    # |00⟩ -> (|00⟩ + |11⟩)/√2
    bell = Circuit().h(0).cnot(0, 1)
    
    # Use LocalSimulator (Braket's local simulator)
    device = LocalSimulator()
    
    # Run with 1024 shots for good statistics
    # Official pattern: device.run(circuit, shots=100).result().measurement_counts
    task = device.run(bell, shots=1024)
    result = task.result()
    
    # Return result - adapter will extract measurement_counts
    return result

if __name__ == "__main__":
    print("Running Bell State test with Braket...")
    print("Expected: ~50% |00> and ~50% |11>")
    result = run()
    
    # Extract and print counts for verification
    if hasattr(result, 'measurement_counts'):
        counts = result.measurement_counts
        print("\nMeasurement results:")
        total = sum(counts.values())
        for bitstring, count in sorted(counts.items()):
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"  |{bitstring}>: {count} ({percentage:.1f}%)")
    
    print("\nDone! Check QObserva dashboard at http://localhost:3000")

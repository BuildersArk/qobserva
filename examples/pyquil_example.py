"""pyQuil example (BYOE).

Install:
  pip install -e packages/qobserva_agent[pyquil]
  pip install --upgrade "pyquil>=4.0.0"

This example uses pyQuil (version 4.0+).
QVM server recommended but not required (can return list of bitstrings).

Version Requirements:
- pyquil >= 4.0.0
- Python 3.10 - 3.12 ONLY (Python 3.13+ NOT supported)
- Rust/Cargo required for building from source

Limitations:
- ⚠️ Python 3.13+ incompatible - PyQuil 4.x uses PyO3 0.20.3 which supports up to Python 3.12
- ⚠️ Requires Rust/Cargo for building from source:
  - Windows: Download from https://rustup.rs/
  - Linux/Mac: curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
- QVM server recommended but not required (can return list of bitstrings)
"""

from qobserva import observe_run
import sys

# Check Python version first
if sys.version_info >= (3, 13):
    print("=" * 60)
    print("⚠️  Python 3.13+ Detected - pyQuil Incompatibility")
    print("=" * 60)
    print("PyQuil 4.x uses PyO3 0.20.3, which supports up to Python 3.12.")
    print("This is a known limitation of PyQuil.")
    print()
    print("Solutions:")
    print("1. Use Python 3.12 or earlier for pyQuil tests")
    print("2. Use a virtual environment with Python 3.12:")
    print("   python3.12 -m venv pyquil_env")
    print("   pyquil_env\\Scripts\\activate  # Windows")
    print("   pip install -e packages/qobserva_agent[pyquil]")
    print("=" * 60)
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
    }
)
def run():
    """Create and measure a Bell state using pyQuil.
    
    Tries to use QVM server if available, otherwise returns simulated results.
    """
    # Create Bell state program
    program = Program()
    ro = program.declare("ro", "BIT", 2)
    program += H(0)
    program += CNOT(0, 1)
    program += MEASURE(0, ro[0])
    program += MEASURE(1, ro[1])

    # Try to use QVM server if available
    try:
        from pyquil import get_qc
        qc = get_qc("2q-qvm")
        program.wrap_in_numshots_loop(1024)
        result = qc.run(program)
    except Exception as e:
        # Fallback: return list of bitstrings (simulated)
        # In production, you'd handle this error appropriately
        print(f"QVM not available ({e}), using simulated results")
        import random
        result = [[0, 0] if random.random() < 0.5 else [1, 1] for _ in range(1024)]
    
    return result  # adapter converts list of bitstrings to histogram

if __name__ == "__main__":
    print("Running Bell State test with pyQuil...")
    print("Expected: ~50% |00> and ~50% |11>")
    result = run()
    
    # Print results for verification
    if isinstance(result, list):
        print("\nMeasurement results:")
        counts = {}
        for bitstring in result:
            key = "".join(map(str, bitstring))
            counts[key] = counts.get(key, 0) + 1
        total = sum(counts.values())
        for bitstring, count in sorted(counts.items()):
            percentage = (count / total) * 100 if total > 0 else 0
            print(f"  |{bitstring}>: {count} ({percentage:.1f}%)")
    
    print("\nDone! Check QObserva dashboard at http://localhost:3000")

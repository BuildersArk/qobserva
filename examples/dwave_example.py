"""D-Wave Ocean example (BYOE).

Install:
  pip install -e packages/qobserva_agent[dwave]
  pip install --upgrade "dimod>=0.12.20"

This example uses dimod ExactSolver (dimod 0.12.21 / 2026).
No D-Wave cloud required - runs locally.

Version Requirements:
- dimod >= 0.12.20
- Python 3.10+ (works with Python 3.10-3.14)

Limitations:
- None (works well with ExactSolver)
- Shows energy metrics instead of success rate (optimization problems)
"""

from qobserva import observe_run
import dimod

@observe_run(
    project="dwave_test",
    tags={"sdk": "dwave", "algorithm": "qubo", "test": "optimization"},  # SDK tag is required!
    benchmark_id="qubo_3var",
    benchmark_params={
        "problem_type": "qubo",
        "num_variables": 3,
    }
)
def run():
    """Solve a simple QUBO problem using D-Wave ExactSolver."""
    # Define a simple QUBO: minimize x0*x1 + x1*x2 - x0
    # QUBO form: minimize sum(Q[i][j] * x[i] * x[j])
    
    Q = {
        (0, 0): -1,  # Linear term for x0
        (0, 1): 1,   # Quadratic term x0*x1
        (1, 2): 1,   # Quadratic term x1*x2
    }
    
    # Create QUBO model
    bqm = dimod.BinaryQuadraticModel.from_qubo(Q)
    
    # Use ExactSolver
    solver = dimod.ExactSolver()
    
    # Solve
    sampleset = solver.sample(bqm)
    
    # Return sampleset - adapter extracts min energy and computes approximation ratio
    return sampleset

if __name__ == "__main__":
    print("Running QUBO test with D-Wave...")
    result = run()
    
    # Print results for verification
    if hasattr(result, 'first'):
        first_sample = result.first
        print(f"\nOptimal solution: {first_sample.sample}")
        print(f"Energy: {first_sample.energy}")
    
    print("\nDone! Check QObserva dashboard at http://localhost:3000")
    print("Note: D-Wave runs show energy metrics instead of success rate")

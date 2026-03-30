"""Minimal example without any quantum SDK installed.

This exercises:
- decorator usage
- adapter selection for plain dict results
- emission to collector (when configured)

Note: For best results, always specify the SDK tag even for dict results.
"""

from qobserva import observe_run

@observe_run(
    project="examples",
    tags={"sdk": "pennylane"}  # Specify SDK even for dict results
)
def run():
    # Return a counts dict (common format from many SDKs)
    return {"00": 512, "11": 512}  # adapter will sum values for shots

if __name__ == "__main__":
    run()
    print("Done! Check QObserva dashboard at http://localhost:3000")

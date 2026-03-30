"""Utility functions for extracting SDK versions."""

from __future__ import annotations

from typing import Optional

def get_sdk_version(sdk_name: str) -> str:
    """
    Get the version of an installed SDK package.
    
    Args:
        sdk_name: Package name (e.g., "qiskit", "amazon-braket-sdk", "cirq", "pennylane")
    
    Returns:
        Version string, or "unknown" if not found
    """
    # Map SDK names to package names (some SDKs have different package names)
    package_map = {
        "qiskit": "qiskit",
        "braket": "amazon-braket-sdk",
        "cirq": "cirq",
        "pennylane": "pennylane",
        "pyquil": "pyquil",
        "dwave": "dimod",  # D-Wave uses dimod package
    }
    
    package_name = package_map.get(sdk_name.lower(), sdk_name)
    
    # Try importlib.metadata first (Python 3.8+)
    try:
        from importlib.metadata import version, PackageNotFoundError
        try:
            return version(package_name)
        except PackageNotFoundError:
            pass
    except ImportError:
        pass
    
    # Fallback to pkg_resources (older Python or if importlib.metadata not available)
    try:
        import pkg_resources
        try:
            return pkg_resources.get_distribution(package_name).version
        except pkg_resources.DistributionNotFound:
            pass
    except ImportError:
        pass
    
    # Last resort: try importing the module and checking __version__
    try:
        module_map = {
            "qiskit": "qiskit",
            "braket": "braket",
            "cirq": "cirq",
            "pennylane": "pennylane",
            "pyquil": "pyquil",
            "dwave": "dimod",
        }
        module_name = module_map.get(sdk_name.lower(), sdk_name)
        module = __import__(module_name)
        if hasattr(module, "__version__"):
            return str(module.__version__)
    except (ImportError, AttributeError):
        pass
    
    return "unknown"

"""QObserva - quantum program observability and benchmarking.

This file is shipped, byte-for-byte identical, by both the `qobserva` and
`qobserva-agent` distributions (tests/packaging enforces this), so whichever one pip
installs last leaves the same working package behind.
"""

from pkgutil import extend_path

# Merge `qobserva` from meta + agent when they live on different sys.path entries
# (e.g. `pip install -e packages/qobserva` and `pip install -e packages/qobserva_agent`).
__path__ = extend_path(__path__, __name__)

def _installed_version() -> str:
    from importlib import metadata

    for dist in ("qobserva", "qobserva-agent"):
        try:
            return metadata.version(dist)
        except metadata.PackageNotFoundError:
            continue
    return "unknown"

__version__ = _installed_version()

# Agent modules (`observe`, `client`, …) ship in the `qobserva-agent` distribution.
try:
    from .observe import observe_run
    from .client import QObservaClient
    from .report import report_run
    from .emitter import flush
except ImportError as import_error:
    _import_error = import_error

    def observe_run(*args, **kwargs):
        raise ImportError(
            "qobserva-agent functionality is not available in this installation.\n"
            "Install with: pip install qobserva qobserva-agent\n"
            f"Original error: {_import_error}"
        )

    class QObservaClient:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            observe_run()

    def report_run(*args, **kwargs):
        observe_run()

    def flush(*args, **kwargs):
        observe_run()

__all__ = ["observe_run", "QObservaClient", "report_run", "flush", "__version__"]

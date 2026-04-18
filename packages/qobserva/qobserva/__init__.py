"""QObserva - Unified quantum observability package."""

from pkgutil import extend_path

# Merge `qobserva` from meta + agent when they live on different sys.path entries
# (e.g. `pip install -e packages/qobserva` and `pip install -e packages/qobserva_agent`).
__path__ = extend_path(__path__, __name__)

__version__ = "0.1.5"

# Agent modules (`observe`, `client`, …) ship in the `qobserva-agent` distribution.
try:
    from .observe import observe_run
    from .client import QObservaClient
    from .report import report_run

    __all__ = ["observe_run", "QObservaClient", "report_run", "__version__"]
except Exception as import_error:
    _import_error = import_error

    def observe_run(*args, **kwargs):
        raise ImportError(
            "qobserva-agent functionality is not available in this installation.\n"
            "Install with: pip install qobserva qobserva-agent\n"
            f"Original error: {_import_error}"
        )

    class QObservaClient:  # type: ignore[override]
        pass

    def report_run(*args, **kwargs):
        raise ImportError(
            "qobserva-agent functionality is not available in this installation.\n"
            "Install with: pip install qobserva qobserva-agent\n"
            f"Original error: {_import_error}"
        )

    __all__ = ["observe_run", "QObservaClient", "report_run", "__version__"]

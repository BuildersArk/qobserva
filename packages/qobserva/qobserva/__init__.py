"""QObserva - Unified quantum observability package."""

__version__ = "0.1.4"

# In PyPI installs, qobserva-agent and qobserva share the same package namespace.
# Import directly from the installed namespace package modules.
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

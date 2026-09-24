from importlib import metadata as _metadata

try:
    __version__ = _metadata.version("qobserva-local")
except _metadata.PackageNotFoundError:
    __version__ = "unknown"

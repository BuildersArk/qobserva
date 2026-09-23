from importlib import metadata as _metadata

try:
    __version__ = _metadata.version("qobserva-collector")
except _metadata.PackageNotFoundError:
    __version__ = "unknown"

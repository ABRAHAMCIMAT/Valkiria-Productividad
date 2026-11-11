"""Valkiria Core: backend local del asistente Valkiria Productividad."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("valkiria-core")
except PackageNotFoundError:  # pragma: no cover - solo ocurre sin instalar el paquete
    __version__ = "0.0.0"

__all__ = ["__version__"]

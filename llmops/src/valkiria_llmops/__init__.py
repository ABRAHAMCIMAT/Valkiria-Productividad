"""LLMOps de Valkiria: trazabilidad, gate y evidencias por fase sobre MLflow 3."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("valkiria-llmops")
except PackageNotFoundError:  # pragma: no cover - solo ocurre sin instalar el paquete
    __version__ = "0.0.0"

__all__ = ["__version__"]

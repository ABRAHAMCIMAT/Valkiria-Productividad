"""Verificación de salud de Valkiria Core.

En F2 la expone el endpoint ``/health`` del sidecar; en F0 sirve para probar la cadena de CI.
"""

import platform
import sys
from dataclasses import asdict, dataclass

from valkiria_core import __version__

MIN_PYTHON = (3, 15)


@dataclass(frozen=True, slots=True)
class Health:
    """Estado de salud de Core."""

    status: str
    version: str
    python: str
    os: str

    def as_dict(self) -> dict[str, str]:
        """Devuelve el estado como diccionario serializable."""
        return asdict(self)


def os_tag(system: str | None = None, machine: str | None = None) -> str:
    """Devuelve la etiqueta de SO usada en las trazas (por ejemplo, ``macos-arm64``)."""
    system = (system or platform.system()).lower()
    machine = (machine or platform.machine()).lower()
    name = {"darwin": "macos"}.get(system, system)
    arch = {"aarch64": "arm64", "x86_64": "x64", "amd64": "x64"}.get(machine, machine)
    return f"{name}-{arch}"


def check(version_info: tuple[int, ...] | None = None) -> Health:
    """Calcula el estado de salud; ``degraded`` si el intérprete es anterior a 3.15."""
    info = tuple(version_info or sys.version_info[:3])
    status = "ok" if info[:2] >= MIN_PYTHON else "degraded"
    return Health(
        status=status,
        version=__version__,
        python=".".join(str(p) for p in info),
        os=os_tag(),
    )

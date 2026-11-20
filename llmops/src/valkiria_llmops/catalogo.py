"""Catálogo de modelos aprobados (HU-05, RN-05.1 a RN-05.3) y su descarga verificada.

``llmops/models/catalog.yaml`` lista cada modelo con su URL fijada a un commit y su SHA-256. Un
archivo se considera disponible solo si su hash coincide; si no coincide, se borra (RN-05.2).
"""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, cast

import yaml

RAIZ_REPO = Path(__file__).resolve().parents[3]
CATALOGO = RAIZ_REPO / "llmops" / "models" / "catalog.yaml"
LICENCIAS = frozenset({"apache-2.0", "mit"})
FORMATOS = frozenset({"gguf", "onnx", "safetensors"})
_BLOQUE = 1 << 20


class CatalogoError(ValueError):
    """El catálogo o uno de sus modelos no cumple las reglas de HU-05."""


@dataclass(frozen=True)
class Modelo:
    id: str
    url: str
    sha256: str
    licencia: str
    formato: str
    bytes: int

    @property
    def archivo(self) -> str:
        return self.url.rsplit("/", 1)[-1]


def _modelo(d: dict[str, object]) -> Modelo:
    try:
        m = Modelo(
            id=str(d["id"]),
            url=str(d["url"]),
            sha256=str(d["sha256"]).lower(),
            licencia=str(d["licencia"]).lower(),
            formato=str(d["formato"]).lower(),
            bytes=int(str(d["bytes"])),
        )
    except KeyError as err:
        raise CatalogoError(f"modelo sin el campo {err.args[0]}: {d.get('id', '?')}") from err
    if not m.url.startswith("https://"):
        raise CatalogoError(f"{m.id}: la URL debe ser https")
    if len(m.sha256) != 64 or any(c not in "0123456789abcdef" for c in m.sha256):
        raise CatalogoError(f"{m.id}: sha256 no válido")
    if m.licencia not in LICENCIAS:
        raise CatalogoError(f"{m.id}: licencia {m.licencia} no admitida (RN-05.1)")
    if m.formato not in FORMATOS or not m.archivo.lower().endswith("." + m.formato):
        raise CatalogoError(f"{m.id}: formato {m.formato} no admitido (RN-05.3)")
    return m


def cargar(ruta: Path | None = None) -> dict[str, Modelo]:
    """Lee el catálogo y devuelve ``id -> Modelo``; falla si una entrada rompe una regla."""
    datos = yaml.safe_load((ruta or CATALOGO).read_text(encoding="utf-8"))
    modelos: dict[str, Modelo] = {}
    for d in datos.get("modelos") or []:
        m = _modelo(d)
        if m.id in modelos:
            raise CatalogoError(f"id repetido: {m.id}")
        modelos[m.id] = m
    return modelos


def sha256(ruta: Path) -> str:
    h = hashlib.sha256()
    with ruta.open("rb") as f:
        while bloque := f.read(_BLOQUE):
            h.update(bloque)
    return h.hexdigest()


def _abrir(url: str) -> BinaryIO:
    # Solo https (lo valida el catálogo); urllib sigue la redirección de HF a su CDN, también https.
    respuesta = urllib.request.urlopen(url, timeout=60)  # noqa: S310  # nosec B310
    return cast(BinaryIO, respuesta)


def directorio_cache() -> Path:
    defecto = Path.home() / ".cache" / "valkiria" / "modelos"
    return Path(os.environ.get("VALKIRIA_MODELOS_CACHE", defecto))


def descargar(
    m: Modelo, cache: Path | None = None, abrir: Callable[[str], BinaryIO] | None = None
) -> Path:
    """Devuelve la ruta del modelo verificado, descargándolo si hace falta (RN-05.2)."""
    destino = (cache or directorio_cache()) / m.sha256 / m.archivo
    if destino.is_file():
        if sha256(destino) == m.sha256:
            return destino
        destino.unlink()
    destino.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=destino.parent, delete=False) as tmp:
        parcial = Path(tmp.name)
        with (abrir or _abrir)(m.url) as r:
            shutil.copyfileobj(r, tmp, _BLOQUE)
    obtenido = sha256(parcial)
    if obtenido != m.sha256:
        parcial.unlink()
        raise CatalogoError(
            f"{m.id}: integridad no verificada (sha256 {obtenido}), archivo eliminado"
        )
    parcial.replace(destino)
    return destino

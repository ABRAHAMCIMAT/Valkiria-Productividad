"""Manifiesto de integridad de un paquete de evidencias (``manifest.sha256``, docs/05 §5).

Uso:
  python3 tools/evidencias/manifiesto.py generar evidencias/F0
  python3 tools/evidencias/manifiesto.py verificar evidencias/F0 [evidencias/F1 ...]

``generar`` escribe una línea ``<sha256>  <ruta>`` por archivo del paquete, en orden de bytes de la
ruta, igual que ``sha256sum`` con ``LC_ALL=C sort``. Lista todo menos el propio ``manifest.sha256``
(``manifest-ci.sha256``, el manifiesto original de CI, sí queda listado).

``verificar`` falla si un hash no coincide, si una ruta aparece dos veces, si falta un archivo
listado o si hay un archivo en el paquete que el manifiesto no lista. Así un anexo posterior al
cierre no puede cambiar el paquete sin regenerar el manifiesto, ni regenerarlo mal.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

MANIFIESTO = "manifest.sha256"


def sha256(archivo: Path) -> str:
    h = hashlib.sha256()
    with archivo.open("rb") as f:
        for bloque in iter(lambda: f.read(1 << 20), b""):
            h.update(bloque)
    return h.hexdigest()


def archivos(paquete: Path) -> list[str]:
    rutas = (p.relative_to(paquete).as_posix() for p in paquete.rglob("*") if p.is_file())
    return sorted((r for r in rutas if r != MANIFIESTO), key=lambda r: r.encode())


def generar(paquete: Path) -> int:
    lineas = [f"{sha256(paquete / r)}  {r}\n" for r in archivos(paquete)]
    (paquete / MANIFIESTO).write_text("".join(lineas), encoding="utf-8", newline="\n")
    return len(lineas)


def verificar(paquete: Path) -> list[str]:
    """Problemas del manifiesto de ``paquete``; lista vacía si está íntegro."""
    manifiesto = paquete / MANIFIESTO
    if not manifiesto.is_file():
        return [f"{paquete}: no tiene {MANIFIESTO}"]
    problemas: list[str] = []
    listadas: dict[str, str] = {}
    for n, linea in enumerate(manifiesto.read_text(encoding="utf-8").splitlines(), start=1):
        hash_, sep, ruta = linea.partition("  ")
        if not sep or len(hash_) != 64:
            problemas.append(f"{manifiesto}:{n}: línea mal formada: {linea!r}")
            continue
        if ruta in listadas:
            problemas.append(f"{manifiesto}:{n}: {ruta} aparece dos veces")
            continue
        listadas[ruta] = hash_
    presentes = set(archivos(paquete))
    for ruta, esperado in listadas.items():
        if ruta not in presentes:
            problemas.append(f"{paquete}: falta {ruta}, que el manifiesto lista")
        elif sha256(paquete / ruta) != esperado:
            problemas.append(f"{paquete}: {ruta} no coincide con su hash")
    problemas += [
        f"{paquete}: {r} no está en el manifiesto" for r in sorted(presentes - listadas.keys())
    ]
    return problemas


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("accion", choices=["generar", "verificar"])
    ap.add_argument("paquetes", type=Path, nargs="+")
    a = ap.parse_args(argv)
    if a.accion == "generar":
        for p in a.paquetes:
            print(f"{p / MANIFIESTO}: {generar(p)} archivos")
        return 0
    problemas = [x for p in a.paquetes for x in verificar(p)]
    for x in problemas:
        print(f"::error title=Manifiesto de evidencias::{x}")
    if not problemas:
        print(f"Manifiestos íntegros: {', '.join(str(p) for p in a.paquetes)}")
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main())

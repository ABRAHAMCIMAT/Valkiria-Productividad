"""Matriz de trazabilidad de una fase (docs/05 §4.2 y §5): HU → RN → CA → evidencia → resultado.

Uso:
  python3 tools/evidencias/trazabilidad.py --criterios evidencias/F0/criterios.toml \\
      --junit 'reports/**/*.xml' --jobs reports/jobs.json --commit <sha> \\
      --salida evidencias/F0/trazabilidad.csv

Cada criterio de ``criterios.toml`` se respalda con al menos una de estas evidencias:
- ``pruebas``: nombres de prueba; su resultado sale de los reportes JUnit.
- ``jobs``: nombres de jobs de GitHub Actions; su conclusión sale de ``--jobs``
  (``[{"name": ..., "conclusion": ...}]``, como lo devuelve ``gh run view --json jobs``).
- ``demostraciones``: PRs o runs revisados a mano (por ejemplo, un PR que debe quedar bloqueado).

Falla si un criterio no tiene evidencia o si alguna evidencia automática no pasó.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import os
import re
import sys
import tempfile
import tomllib
import xml.etree.ElementTree as ET  # nosec B405 - reportes JUnit propios de CI
from pathlib import Path
from typing import Any

COLUMNAS = [
    "hu",
    "regla",
    "criterio",
    "test",
    "resultado",
    "mlflow_run_id",
    "commit",
    "pr",
    "fase",
    "evidencia",
]


def confinar(ruta: str | Path) -> Path:
    """Solo se leen y escriben archivos del directorio de trabajo o del temporal del sistema."""
    destino = os.path.realpath(ruta)
    permitidas = [os.path.realpath(Path.cwd()), os.path.realpath(tempfile.gettempdir())]
    if not any(os.path.commonpath([base, destino]) == base for base in permitidas):
        raise ValueError(f"ruta fuera de {permitidas}: {destino}")
    return Path(destino)


def resultados_junit(patrones: list[str]) -> dict[str, str]:
    """Nombre de prueba (sin parámetros) → ``pass`` / ``fail`` / ``skip``. Un fallo gana."""
    orden = {"skip": 0, "pass": 1, "fail": 2}
    resultados: dict[str, str] = {}
    for patron in patrones:
        for ruta in glob.glob(patron, recursive=True):
            for caso in ET.parse(confinar(ruta)).getroot().iter("testcase"):  # noqa: S314  # nosec B314
                nombre = re.sub(r"\[.*\]$", "", caso.get("name", ""))
                if caso.find("failure") is not None or caso.find("error") is not None:
                    estado = "fail"
                elif caso.find("skipped") is not None:
                    estado = "skip"
                else:
                    estado = "pass"
                if orden[estado] >= orden.get(resultados.get(nombre, "skip"), 0):
                    resultados[nombre] = estado
    return resultados


def conclusiones_jobs(ruta: Path | None) -> dict[str, str]:
    if ruta is None or not ruta.exists():
        return {}
    datos = json.loads(confinar(ruta).read_text(encoding="utf-8"))
    return {
        j["name"]: "pass" if j.get("conclusion") == "success" else str(j.get("conclusion"))
        for j in datos
    }


def construir(
    criterios: dict[str, Any], junit: dict[str, str], jobs: dict[str, str], commit: str
) -> tuple[list[dict[str, str]], list[str]]:
    fase = criterios["fase"]
    filas: list[dict[str, str]] = []
    errores: list[str] = []
    for c in criterios["criterio"]:
        base = {
            "hu": c["hu"],
            "regla": ";".join(c.get("reglas", [])),
            "criterio": c["id"],
            "fase": fase,
            "commit": commit,
            "evidencia": c.get("evidencia", ""),
            "mlflow_run_id": "",
            "pr": "",
        }
        evidencias = 0
        for prueba in c.get("pruebas", []):
            resultado = junit.get(prueba, "sin-resultado")
            filas.append(base | {"test": prueba, "resultado": resultado})
            evidencias += 1
            if resultado != "pass":
                errores.append(f"{c['id']}: la prueba {prueba} tiene resultado {resultado}")
        for job in c.get("jobs", []):
            resultado = jobs.get(job, "sin-resultado")
            filas.append(base | {"test": f"job:{job}", "resultado": resultado})
            evidencias += 1
            if resultado != "pass":
                errores.append(f"{c['id']}: el job '{job}' tiene resultado {resultado}")
        for demo in c.get("demostraciones", []):
            filas.append(
                base
                | {
                    "test": demo["descripcion"],
                    "resultado": demo["resultado"],
                    "pr": demo.get("pr", ""),
                }
            )
            evidencias += 1
        if evidencias == 0:
            errores.append(f"{c['id']}: no tiene ninguna evidencia")
    return filas, errores


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--criterios", type=Path, required=True)
    ap.add_argument("--junit", action="append", default=[], help="Patrón glob de reportes JUnit")
    ap.add_argument("--jobs", type=Path)
    ap.add_argument("--commit", default="")
    ap.add_argument("--salida", type=Path, required=True)
    a = ap.parse_args(argv)

    criterios = tomllib.loads(confinar(a.criterios).read_text(encoding="utf-8"))
    a.salida = confinar(a.salida)
    filas, errores = construir(
        criterios, resultados_junit(a.junit), conclusiones_jobs(a.jobs), a.commit
    )
    a.salida.parent.mkdir(parents=True, exist_ok=True)
    with a.salida.open("w", encoding="utf-8", newline="") as f:
        escritor = csv.DictWriter(f, fieldnames=COLUMNAS)
        escritor.writeheader()
        escritor.writerows(filas)
    total = len({f["criterio"] for f in filas})
    for e in errores:
        print(f"::error title=Trazabilidad {criterios['fase']}::{e}")
    print(f"{total} criterios, {len(filas)} evidencias, {len(errores)} problemas -> {a.salida}")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

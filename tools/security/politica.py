"""Verifica la política de licencias y excepciones de Valkiria (RN-02.1 y RN-02.4).

Uso:
  python3 tools/security/politica.py excepciones [--hoy AAAA-MM-DD]
  python3 tools/security/politica.py licencias <reporte-pip-licenses.json>
  python3 tools/security/politica.py trivyignore   # imprime los CVE con excepción vigente
  python3 tools/security/politica.py vigente --tipo cve --objetivo apps/desktop

Solo usa la biblioteca estándar para poder correr en cualquier job de CI.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import tomllib
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
CAMPOS = ("id", "tipo", "objetivo", "motivo", "responsable", "riesgo", "vence")
TIPOS = {"licencia", "cve", "sast", "secreto"}


def cargar_excepciones(ruta: Path) -> list[dict[str, object]]:
    return list(tomllib.loads(ruta.read_text(encoding="utf-8")).get("excepcion", []))


def validar_excepciones(excepciones: list[dict[str, object]], hoy: dt.date) -> list[str]:
    errores = []
    for i, ex in enumerate(excepciones, 1):
        ref = ex.get("id", f"#{i}")
        faltan = [c for c in CAMPOS if not ex.get(c)]
        if faltan:
            errores.append(f"{ref}: faltan campos {', '.join(faltan)}")
            continue
        if ex["tipo"] not in TIPOS:
            errores.append(f"{ref}: tipo '{ex['tipo']}' no válido")
        vence = ex["vence"]
        if not isinstance(vence, dt.date) or vence < hoy:
            errores.append(f"{ref}: vencida o fecha no válida ({vence})")
    return errores


def normalizar(licencia: str) -> str:
    return " ".join(licencia.lower().split())


def licencia_permitida(expresion: str, permitidas: set[str]) -> bool:
    """Evalúa una expresión de licencia sencilla.

    ``;`` (varias licencias declaradas por pip-licenses) y ``OR`` (SPDX) bastan con una permitida;
    ``AND`` exige que todas lo estén. En expresiones SPDX se ignoran los paréntesis; en un nombre
    clasificador como ``Mozilla Public License 2.0 (MPL 2.0)`` se conservan.
    """
    texto = expresion
    if " OR " in texto or " AND " in texto:
        texto = texto.replace("(", " ").replace(")", " ")
    alternativas = [a for parte in texto.split(";") for a in parte.split(" OR ")]
    return any(
        all(normalizar(t) in permitidas for t in alt.split(" AND "))
        for alt in alternativas
        if alt.strip()
    )


def validar_licencias(
    paquetes: list[dict[str, str]], permitidas: set[str], exentos: set[str]
) -> list[str]:
    errores = []
    for p in paquetes:
        nombre = p.get("Name", "?")
        if nombre.lower() in exentos:
            continue
        if not licencia_permitida(p.get("License", "UNKNOWN"), permitidas):
            errores.append(
                f"{nombre} {p.get('Version', '')}: licencia no permitida '{p.get('License')}'"
            )
    return errores


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("excepciones")
    e.add_argument("--hoy", type=dt.date.fromisoformat, default=dt.date.today())
    lic = sub.add_parser("licencias")
    lic.add_argument("reporte", type=Path)
    sub.add_parser("trivyignore")
    v = sub.add_parser("vigente", help="Éxito si hay una excepción vigente para el objetivo")
    v.add_argument("--tipo", required=True, choices=sorted(TIPOS))
    v.add_argument("--objetivo", required=True)
    v.add_argument("--hoy", type=dt.date.fromisoformat, default=dt.date.today())
    a = ap.parse_args(argv)

    excepciones = cargar_excepciones(RAIZ / "security/excepciones.toml")
    if a.cmd == "vigente":
        for x in excepciones:
            if x.get("tipo") == a.tipo and x.get("objetivo") == a.objetivo:
                if not validar_excepciones([x], a.hoy):
                    print(f"Excepción vigente {x['id']} hasta {x['vence']}: {x['motivo']}")
                    return 0
                print(f"::error title=Excepción vencida::{x['id']} venció el {x['vence']}")
                return 1
        print(f"::error title=Sin excepción::no hay excepción {a.tipo} para {a.objetivo}")
        return 1
    if a.cmd == "trivyignore":
        vigentes = [x for x in excepciones if not validar_excepciones([x], dt.date.today())]
        ids = [str(x["objetivo"]) for x in vigentes if x["tipo"] == "cve"]
        print("\n".join(i for i in ids if i.startswith(("CVE-", "GHSA-"))))
        return 0
    if a.cmd == "excepciones":
        errores = validar_excepciones(excepciones, a.hoy)
        ok = f"{len(excepciones)} excepciones vigentes"
    else:
        permitidas = {
            normalizar(x)
            for x in tomllib.loads((RAIZ / "security/licencias.toml").read_text())["permitidas"]
        }
        exentos = {str(x["objetivo"]).lower() for x in excepciones if x.get("tipo") == "licencia"}
        paquetes = json.loads(a.reporte.read_text(encoding="utf-8"))
        errores = validar_licencias(paquetes, permitidas, exentos)
        ok = f"{len(paquetes)} paquetes con licencia permitida"

    for err in errores:
        print(f"::error title=Política de seguridad::{err}")
    print(ok if not errores else f"{len(errores)} incumplimientos")
    return 1 if errores else 0


if __name__ == "__main__":
    sys.exit(main())

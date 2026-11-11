"""Trazabilidad de fase (docs/05 §4.2) y alcance de Sonar (CA-29.5)."""

import csv
import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evidencias"))
import trazabilidad

RAIZ = Path(__file__).resolve().parents[2]

JUNIT = """<testsuites><testsuite>
<testcase name="test_a[x]"/><testcase name="test_a[y]"><failure/></testcase>
<testcase name="test_b"/><testcase name="test_c"><skipped/></testcase>
</testsuite></testsuites>"""

CRITERIOS = {
    "fase": "F9",
    "criterio": [
        {
            "id": "CA-90.1",
            "hu": "HU-90",
            "reglas": ["RN-90.1"],
            "pruebas": ["test_b"],
            "jobs": ["CI"],
        },
        {"id": "CA-90.2", "hu": "HU-90", "pruebas": ["test_a", "test_c", "test_falta"]},
        {
            "id": "CA-90.3",
            "hu": "HU-90",
            "demostraciones": [{"descripcion": "PR bloqueado", "resultado": "pass", "pr": "#9"}],
        },
        {"id": "CA-90.4", "hu": "HU-90"},
    ],
}


def test_junit_un_fallo_gana(tmp_path: Path) -> None:
    (tmp_path / "r.xml").write_text(JUNIT)
    assert trazabilidad.resultados_junit([str(tmp_path / "*.xml")]) == {
        "test_a": "fail",
        "test_b": "pass",
        "test_c": "skip",
    }


def test_construir_detecta_cada_problema() -> None:
    junit = {"test_a": "fail", "test_b": "pass", "test_c": "skip"}
    filas, errores = trazabilidad.construir(CRITERIOS, junit, {"CI": "pass"}, "abc")
    assert {f["criterio"] for f in filas} == {"CA-90.1", "CA-90.2", "CA-90.3"}
    assert next(f for f in filas if f["criterio"] == "CA-90.3")["pr"] == "#9"
    assert errores == [
        "CA-90.2: la prueba test_a tiene resultado fail",
        "CA-90.2: la prueba test_c tiene resultado skip",
        "CA-90.2: la prueba test_falta tiene resultado sin-resultado",
        "CA-90.4: no tiene ninguna evidencia",
    ]
    _, errores_job = trazabilidad.construir(CRITERIOS, junit, {}, "abc")
    assert "CA-90.1: el job 'CI' tiene resultado sin-resultado" in errores_job


def test_main_escribe_csv(tmp_path: Path) -> None:
    (tmp_path / "r.xml").write_text('<testsuite><testcase name="test_b"/></testsuite>')
    (tmp_path / "jobs.json").write_text(json.dumps([{"name": "CI", "conclusion": "success"}]))
    toml = '[[criterio]]\nid = "CA-90.1"\nhu = "HU-90"\npruebas = ["test_b"]\njobs = ["CI"]\n'
    (tmp_path / "c.toml").write_text('fase = "F9"\n' + toml)
    salida = tmp_path / "out" / "trazabilidad.csv"
    args = [
        *("--criterios", str(tmp_path / "c.toml"), "--junit", str(tmp_path / "*.xml")),
        *("--jobs", str(tmp_path / "jobs.json"), "--commit", "abc", "--salida", str(salida)),
    ]
    assert trazabilidad.main(args) == 0
    filas = list(csv.DictReader(salida.open(encoding="utf-8")))
    assert [f["resultado"] for f in filas] == ["pass", "pass"]
    assert list(filas[0]) == trazabilidad.COLUMNAS
    assert trazabilidad.conclusiones_jobs(None) == {}


def test_criterios_de_f0_cubren_todas_las_hu() -> None:
    import tomllib

    datos = tomllib.loads((RAIZ / "evidencias/F0/criterios.toml").read_text(encoding="utf-8"))
    ids = {c["id"] for c in datos["criterio"]}
    esperados = {f"CA-01.{i}" for i in (1, 2, 3)} | {f"CA-02.{i}" for i in (1, 2, 3)}
    esperados |= {f"CA-03.{i}" for i in (1, 2, 3)} | {f"CA-29.{i}" for i in range(1, 6)}
    assert ids == esperados


@pytest.mark.skipif(sys.platform == "win32", reason="sources.sh necesita bash de Unix")
def test_sonar_excluye_el_fork_de_jan() -> None:
    """CA-29.5 / RN-29.1: Sonar solo analiza código propio, nunca el fork de Jan."""
    salida = subprocess.run(  # noqa: S603
        ["bash", str(RAIZ / "tools/sonar/sources.sh")],  # noqa: S607
        capture_output=True, text=True, check=True,
    ).stdout  # fmt: skip
    valores = dict(linea.split("=", 1) for linea in salida.splitlines())
    rutas = valores["sources"].split(",") + [t for t in valores["tests"].split(",") if t]
    assert all(
        not r.startswith("apps/desktop")
        or r.startswith("apps/desktop/extensions/valkiria-extension")
        for r in rutas
    )
    assert "core/src" in rutas

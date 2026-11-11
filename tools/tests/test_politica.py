"""Pruebas de la política de licencias y excepciones (RN-02.1, RN-02.4)."""

import datetime as dt
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "security"))
import politica

HOY = dt.date(2026, 11, 10)
PERMITIDAS = {
    politica.normalizar(x)
    for x in ["MIT", "Apache-2.0", "BSD-2-Clause", "Mozilla Public License 2.0 (MPL 2.0)"]
}


def excepcion(**cambios: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "EX-001",
        "tipo": "cve",
        "objetivo": "CVE-2026-0001",
        "motivo": "Sin parche publicado",
        "responsable": "Oficial de seguridad",
        "riesgo": "R-01",
        "vence": dt.date(2027, 1, 31),
    }
    return base | cambios


@pytest.mark.parametrize(
    ("expresion", "esperado"),
    [
        ("MIT", True),
        ("Apache-2.0 OR BSD-2-Clause", True),
        ("(MIT AND Apache-2.0)", True),
        ("MIT AND GPL-3.0-only", False),
        ("GPL-3.0-only", False),
        ("GPL-3.0-only; MIT", True),
        ("Mozilla Public License 2.0 (MPL 2.0)", True),
        ("UNKNOWN", False),
    ],
)
def test_ca_02_licencia_permitida(expresion: str, esperado: bool) -> None:
    assert politica.licencia_permitida(expresion, PERMITIDAS) is esperado


def test_ca_02_licencia_no_permitida_bloquea_salvo_excepcion() -> None:
    paquetes = [
        {"Name": "libre", "Version": "1", "License": "MIT"},
        {"Name": "gpl", "Version": "2", "License": "GPL-3.0"},
    ]
    assert politica.validar_licencias(paquetes, PERMITIDAS, set()) == [
        "gpl 2: licencia no permitida 'GPL-3.0'"
    ]
    assert politica.validar_licencias(paquetes, PERMITIDAS, {"gpl"}) == []


def test_ca_02_excepcion_vigente_es_valida() -> None:
    assert politica.validar_excepciones([excepcion()], HOY) == []


def test_ca_02_excepcion_vencida_o_incompleta_falla() -> None:
    errores = politica.validar_excepciones(
        [
            excepcion(vence=dt.date(2026, 1, 1)),
            {"id": "EX-002", "tipo": "cve"},
            excepcion(id="EX-003", tipo="otro"),
        ],
        HOY,
    )
    assert len(errores) == 3
    assert "vencida" in errores[0]
    assert "faltan campos" in errores[1]
    assert "no válido" in errores[2]


def test_ca_02_cli_licencias(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    reporte = tmp_path / "lic.json"
    reporte.write_text(json.dumps([{"Name": "x", "Version": "1", "License": "Proprietary"}]))
    assert politica.main(["licencias", str(reporte)]) == 1
    assert "::error" in capsys.readouterr().out


def test_ca_02_cli_excepciones_y_trivyignore_del_repo() -> None:
    assert politica.main(["excepciones", "--hoy", "2026-11-10"]) == 0
    assert politica.main(["trivyignore"]) == 0


def test_ca_02_excepcion_por_objetivo(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        politica.main(
            ["vigente", "--tipo", "cve", "--objetivo", "apps/desktop", "--hoy", "2026-11-10"]
        )
        == 0
    )
    assert (
        politica.main(
            ["vigente", "--tipo", "cve", "--objetivo", "apps/desktop", "--hoy", "2027-01-01"]
        )
        == 1
    )
    assert "vencida" in capsys.readouterr().out.lower()
    assert politica.main(["vigente", "--tipo", "cve", "--objetivo", "otro"]) == 1

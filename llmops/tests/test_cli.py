"""CLI llmops, incluida la restricción de loopback (RN-03.3)."""

from pathlib import Path
from typing import Any

import pytest

from valkiria_llmops import cli


def test_rn_03_3_servidor_solo_en_loopback(tmp_path: Path) -> None:
    cmd = cli.comando_servidor("127.0.0.1", 5000, tmp_path)
    assert cmd[cmd.index("--host") + 1] == "127.0.0.1"
    assert cli.comando_servidor("::1", 5000, tmp_path)
    for host in ("0.0.0.0", "192.168.1.10", "localhost.evil", ""):  # noqa: S104
        with pytest.raises(ValueError, match="loopback"):
            cli.comando_servidor(host, 5000, tmp_path)
    for puerto in (80, 70000):
        with pytest.raises(ValueError, match="rango"):
            cli.comando_servidor("127.0.0.1", puerto, tmp_path)


def test_serve_dry_run(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("VALKIRIA_MLFLOW_HOME", str(tmp_path))
    assert cli.main(["serve", "--dry-run"]) == 0
    assert "--host 127.0.0.1" in capsys.readouterr().out


def test_serve_rechaza_host_externo(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["serve", "--host", "0.0.0.0", "--dry-run"]) == 2  # noqa: S104
    assert "RN-03.3" in capsys.readouterr().err


def test_directorio_por_defecto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("VALKIRIA_MLFLOW_HOME", raising=False)
    assert cli.directorio_datos() == Path.home() / ".valkiria" / "mlflow"


def test_flujo_completo_por_cli(
    mlflow_local: tuple[Any, Any, str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, _, uri = mlflow_local
    monkeypatch.setenv("GITHUB_SHA", "0123456789abcdef0123456789abcdef01234567")
    base = ["--tracking-uri", uri]
    assert cli.main([*base, "gate", "--phase", "F0"]) == 1  # sin runs todavía
    assert cli.main([*base, "bootstrap"]) == 0
    assert cli.main([*base, "demo-eval", "--phase", "F0", "--hu", "HU-03"]) == 0
    assert cli.main([*base, "gate", "--phase", "F0"]) == 0
    destino = tmp_path / "out"
    assert cli.main([*base, "export", "--phase", "F0", "--out", str(destino)]) == 0
    assert len(list((destino / "mlflow").glob("*.json"))) == 1
    assert "1 runs exportados" in capsys.readouterr().out


def test_cli_gate_con_hallazgos(
    mlflow_local: tuple[Any, Any, str], capsys: pytest.CaptureFixture[str]
) -> None:
    mlflow, _, uri = mlflow_local
    mlflow.set_experiment("formato-eval")
    with mlflow.start_run(tags={"phase": "F0"}):
        pass
    assert cli.main(["--tracking-uri", uri, "gate", "--phase", "F0"]) == 1
    assert "falta el tag git.sha" in capsys.readouterr().out

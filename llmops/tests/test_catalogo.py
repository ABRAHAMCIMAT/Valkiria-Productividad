"""Catálogo de modelos y descarga verificada (HU-05: RN-05.1 a RN-05.3)."""

from __future__ import annotations

import hashlib
import io
from pathlib import Path
from typing import Any

import pytest

from valkiria_llmops import catalogo, cli

CONTENIDO = b"GGUF modelo de prueba"
SHA = hashlib.sha256(CONTENIDO).hexdigest()


def _entrada(**cambios: Any) -> dict[str, Any]:
    d: dict[str, Any] = {
        "id": "m",
        "url": "https://ejemplo.test/r/abc/m.gguf",
        "sha256": SHA,
        "licencia": "apache-2.0",
        "formato": "gguf",
        "bytes": len(CONTENIDO),
    }
    d.update(cambios)
    return d


def _catalogo(tmp_path: Path, *entradas: dict[str, Any]) -> Path:
    import yaml

    ruta = tmp_path / "catalog.yaml"
    ruta.write_text(yaml.safe_dump({"version": 1, "modelos": list(entradas)}), encoding="utf-8")
    return ruta


def _abrir(contenido: bytes = CONTENIDO) -> Any:
    return lambda _url: io.BytesIO(contenido)


def test_catalogo_del_repo_es_valido() -> None:
    modelos = catalogo.cargar()
    humo = modelos["qwen3-0.6b-q8_0"]
    assert humo.licencia in catalogo.LICENCIAS
    assert "/resolve/" in humo.url
    assert "/main/" not in humo.url, "URL fijada a un commit, no a una rama"


@pytest.mark.parametrize(
    ("cambio", "motivo"),
    [
        ({"licencia": "llama3"}, "RN-05.1"),
        ({"formato": "pt", "url": "https://ejemplo.test/m.pt"}, "RN-05.3"),
        ({"formato": "gguf", "url": "https://ejemplo.test/m.bin"}, "RN-05.3"),
        ({"url": "http://ejemplo.test/m.gguf"}, "https"),
        ({"sha256": "abc"}, "sha256"),
    ],
)
def test_rn_05_1_y_05_3_reglas_del_catalogo(
    tmp_path: Path, cambio: dict[str, Any], motivo: str
) -> None:
    with pytest.raises(catalogo.CatalogoError, match=motivo):
        catalogo.cargar(_catalogo(tmp_path, _entrada(**cambio)))


def test_catalogo_sin_campo_o_repetido(tmp_path: Path) -> None:
    sin_url = _entrada()
    del sin_url["url"]
    with pytest.raises(catalogo.CatalogoError, match="url"):
        catalogo.cargar(_catalogo(tmp_path, sin_url))
    with pytest.raises(catalogo.CatalogoError, match="repetido"):
        catalogo.cargar(_catalogo(tmp_path, _entrada(), _entrada()))
    assert catalogo.cargar(_catalogo(tmp_path)) == {}


def test_descarga_verificada_y_reutiliza_la_cache(tmp_path: Path) -> None:
    m = catalogo.cargar(_catalogo(tmp_path, _entrada()))["m"]
    ruta = catalogo.descargar(m, tmp_path / "cache", _abrir())
    assert ruta.read_bytes() == CONTENIDO
    assert catalogo.descargar(m, tmp_path / "cache", _abrir(b"no se descarga")) == ruta


def test_rn_05_2_hash_distinto_se_elimina(tmp_path: Path) -> None:
    m = catalogo.cargar(_catalogo(tmp_path, _entrada()))["m"]
    cache = tmp_path / "cache"
    with pytest.raises(catalogo.CatalogoError, match="integridad no verificada"):
        catalogo.descargar(m, cache, _abrir(b"alterado"))
    assert not any(p.is_file() for p in cache.rglob("*")), "el archivo alterado no queda"
    # Uno ya descargado que se alteró después también se descarta y se baja de nuevo.
    ruta = catalogo.descargar(m, cache, _abrir())
    ruta.write_bytes(b"alterado")
    assert catalogo.descargar(m, cache, _abrir()).read_bytes() == CONTENIDO


def test_cli_modelo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(catalogo, "CATALOGO", _catalogo(tmp_path, _entrada()))
    monkeypatch.setattr(catalogo, "_abrir", _abrir())
    assert cli.main(["modelo", "m", "--cache", str(tmp_path / "c")]) == 0
    assert capsys.readouterr().out.strip().endswith("m.gguf")
    assert cli.main(["modelo", "otro"]) == 2
    assert "modelo no aprobado" in capsys.readouterr().err
    monkeypatch.setattr(catalogo, "_abrir", _abrir(b"x"))
    assert cli.main(["modelo", "m", "--cache", str(tmp_path / "d")]) == 1
    assert "integridad" in capsys.readouterr().err


def test_cache_por_defecto(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("VALKIRIA_MODELOS_CACHE", str(tmp_path))
    assert catalogo.directorio_cache() == tmp_path
    monkeypatch.delenv("VALKIRIA_MODELOS_CACHE")
    assert catalogo.directorio_cache().parts[-2:] == ("valkiria", "modelos")

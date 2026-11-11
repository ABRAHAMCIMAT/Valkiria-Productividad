"""RN-03.1 y RN-03.2: tags obligatorios."""

import pytest

from valkiria_llmops import tags as tg

SHA256 = "a" * 64


def completos(**cambios: str) -> dict[str, str]:
    base = tg.construir(
        phase="F0",
        hu="HU-03",
        model_sha256=SHA256,
        prompts={"formato": 1},
        profile="ci",
        valkiria_version="0.0.1",
        sha="0123abc",
    )
    return base | cambios


def test_ca_03_1_tags_completos_cuentan_como_evidencia() -> None:
    t = completos()
    assert tg.faltantes(t) == []
    assert t["prompt.formato.version"] == "1"
    assert t["hu"] == "HU-03"


@pytest.mark.parametrize("tag", tg.OBLIGATORIOS)
def test_ca_03_3_cada_tag_obligatorio_es_requerido(tag: str) -> None:
    t = completos()
    del t[tag]
    assert f"falta el tag {tag}" in tg.faltantes(t)


def test_ca_03_3_valor_vacio_no_cuenta() -> None:
    assert "falta el tag git.sha" in tg.faltantes(completos(**{"git.sha": "  "}))


def test_ca_03_3_sin_version_de_prompt() -> None:
    t = {k: v for k, v in completos().items() if not k.startswith("prompt.")}
    assert "falta al menos un tag prompt.<nombre>.version" in tg.faltantes(t)


@pytest.mark.parametrize(
    ("clave", "valor"),
    [
        ("phase", "F99"),
        ("hu", "HU-3"),
        ("git.sha", "no-es-sha"),
        ("model.sha256", "corto"),
        ("os", "solaris-sparc"),
        ("profile", "turbo"),
        ("prompt.formato.version", "uno"),
    ],
)
def test_ca_03_3_formatos_invalidos(clave: str, valor: str) -> None:
    assert any(clave in p for p in tg.faltantes(completos(**{clave: valor})))


def test_construir_sin_hu_y_con_extra() -> None:
    t = tg.construir(
        phase="F1",
        model_sha256=SHA256,
        prompts={},
        profile="estandar",
        valkiria_version="0.1.0",
        sha="abcdef1",
        extra={"model.name": "qwen3"},
    )
    assert "hu" not in t
    assert t["model.name"] == "qwen3"


@pytest.mark.parametrize(
    ("system", "machine", "esperado"),
    [
        ("Darwin", "arm64", "macos-arm64"),
        ("Windows", "AMD64", "windows-x64"),
        ("Linux", "x86_64", "linux-x64"),
    ],
)
def test_os_tag(system: str, machine: str, esperado: str) -> None:
    assert tg.os_tag(system, machine) == esperado


def test_git_sha_desde_ci(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_SHA", "f" * 40)
    assert tg.git_sha() == "f" * 40


def test_git_sha_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    sha = tg.git_sha()
    assert sha == "" or len(sha) == 40


def test_git_sha_sin_git(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_SHA", raising=False)
    monkeypatch.setenv("PATH", "")
    assert tg.git_sha() == ""

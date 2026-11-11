import pytest

from valkiria_core import __version__, health


def test_check_ok_con_python_315() -> None:
    result = health.check((3, 15, 0))
    assert result.status == "ok"
    assert result.python == "3.15.0"
    assert result.version == __version__


def test_check_degradado_con_python_anterior() -> None:
    assert health.check((3, 14, 8)).status == "degraded"


def test_check_usa_el_interprete_actual() -> None:
    result = health.check()
    assert result.status == "ok"
    assert set(result.as_dict()) == {"status", "version", "python", "os"}


@pytest.mark.parametrize(
    ("system", "machine", "expected"),
    [
        ("Darwin", "arm64", "macos-arm64"),
        ("Darwin", "x86_64", "macos-x64"),
        ("Windows", "AMD64", "windows-x64"),
        ("Linux", "aarch64", "linux-arm64"),
    ],
)
def test_os_tag(system: str, machine: str, expected: str) -> None:
    assert health.os_tag(system, machine) == expected


def test_os_tag_por_defecto_no_vacio() -> None:
    assert "-" in health.os_tag()

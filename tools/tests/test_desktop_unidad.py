"""Pruebas independientes del SO para rebrand.py y smoke.py (HU-01)."""

import json
import plistlib
import sys
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "desktop"))
import rebrand
import smoke


# ---------------------------------------------------------------- rebrand sobre un árbol falso
def _arbol_jan(raiz: Path) -> Path:
    """Árbol mínimo con los fragmentos originales de Jan que el script parchea."""
    archivos: dict[str, str] = {}
    for p in rebrand.PARCHES:
        archivos[p.ruta] = archivos.get(p.ruta, "// inicio\n") + p.original + "\n"
    for rel, texto in archivos.items():
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(texto, encoding="utf-8")
    tauri = {
        "productName": "Jan",
        "version": "0.8.5",
        "identifier": "jan.ai.app",
        "app": {"security": {"csp": {"script-src": "'self' https://posthog.com"}}},
        "plugins": {"updater": {"pubkey": "x", "endpoints": ["https://apps.jan.ai"]}},
        "bundle": {"publisher": "Menlo Research Pte. Ltd."},
    }
    ventana = {"app": {"windows": [{"title": "Jan"}]}}
    for rel, datos in [
        ("src-tauri/tauri.conf.json", tauri),
        ("src-tauri/tauri.macos.conf.json", ventana),
        ("src-tauri/tauri.windows.conf.json", ventana),
        ("src-tauri/tauri.linux.conf.json", ventana),
        ("web-app/package.json", {"version": "0.7.6"}),
        ("web-app/src/locales/es/settings.json", {"titulo": "Ajustes de Jan"}),
        ("web-app/src/locales/fr/common.json", {"x": "Jan"}),
    ]:
        (raiz / rel).parent.mkdir(parents=True, exist_ok=True)
        (raiz / rel).write_text(json.dumps(datos), encoding="utf-8")
    (raiz / "web-app/src/constants").mkdir(parents=True, exist_ok=True)
    (raiz / "web-app/src/constants/providers.ts").write_text(
        "export const predefinedProviders = [{ active: true, }]\n", encoding="utf-8"
    )
    (raiz / "src-tauri/Cargo.toml").write_text(
        '[package]\ndescription = "Use offline LLMs"\nauthors = ["Jan <service@jan.ai>"]\n',
        encoding="utf-8",
    )
    for destino in [
        "web-app/public/images/jan-logo.png",
        "src-tauri/icons/icon.png",
        "src-tauri/app-icon.png",
    ]:
        (raiz / destino).parent.mkdir(parents=True, exist_ok=True)
        (raiz / destino).write_bytes(b"logo de Jan")
    return raiz


def test_ca_01_rebrand_completo_sobre_jan(tmp_path: Path) -> None:
    app = _arbol_jan(tmp_path)
    cambios = rebrand.aplicar(app=app)
    assert "src-tauri/tauri.conf.json" in cambios
    assert rebrand.aplicar(app=app, solo_verificar=True) == []  # idempotente

    conf = json.loads((app / "src-tauri/tauri.conf.json").read_text(encoding="utf-8"))
    assert (conf["productName"], conf["identifier"]) == (rebrand.NOMBRE, rebrand.IDENTIFICADOR)
    assert conf["plugins"]["updater"]["endpoints"] == []
    assert "posthog" not in conf["app"]["security"]["csp"]["script-src"]
    ventana = json.loads((app / "src-tauri/tauri.macos.conf.json").read_text(encoding="utf-8"))
    assert ventana["app"]["windows"][0]["title"] == rebrand.NOMBRE
    es = json.loads((app / "web-app/src/locales/es/settings.json").read_text(encoding="utf-8"))
    assert es["titulo"] == "Ajustes de Valkiria"
    assert "active: false" in (app / "web-app/src/constants/providers.ts").read_text()
    assert 'authors = ["VALTRE"]' in (app / "src-tauri/Cargo.toml").read_text()
    assert (app / "src-tauri/icons/icon.png").read_bytes() == (
        rebrand.MARCA / "icono-1024.png"
    ).read_bytes()


def test_rebrand_check_detecta_pendientes(tmp_path: Path) -> None:
    app = _arbol_jan(tmp_path)
    pendientes = rebrand.aplicar(app=app, solo_verificar=True)
    assert "web-app/index.html" in pendientes
    assert (app / "web-app/index.html").read_text().count("<title>Jan</title>") == 1  # no escribe


def test_rebrand_tauri_con_estructura_inesperada() -> None:
    with pytest.raises(rebrand.ParcheError, match="objeto"):
        rebrand._tauri({"bundle": [], "plugins": {}, "app": {}})


def test_rebrand_main(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(rebrand, "aplicar", lambda solo_verificar=False: [])
    assert rebrand.main(["--check"]) == 0
    monkeypatch.setattr(rebrand, "aplicar", lambda solo_verificar=False: ["a.json"])
    assert rebrand.main(["--check"]) == 1
    assert rebrand.main([]) == 0

    def falla(solo_verificar: bool = False) -> list[str]:
        raise rebrand.ParcheError("x.ts: cambió upstream")

    monkeypatch.setattr(rebrand, "aplicar", falla)
    assert rebrand.main([]) == 2
    assert "cambió upstream" in capsys.readouterr().out


# ---------------------------------------------------------------- smoke con SO simulado
class ProcesoFalso:
    def __init__(self, vive_ciclos: int = 10_000) -> None:
        self.pid, self.returncode, self._ciclos = 4242, None, vive_ciclos
        self.terminado = False

    def poll(self) -> int | None:
        self._ciclos -= 1
        if self._ciclos < 0:
            self.returncode = 1
        return self.returncode

    def terminate(self) -> None:
        self.terminado = True

    def wait(self, timeout: float) -> int:
        return 0


@pytest.fixture
def macos_simulado(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Any]:
    app = tmp_path / "Valkiria Productividad.app"
    (app / "Contents").mkdir(parents=True)
    (app / "Contents" / "Info.plist").write_bytes(
        plistlib.dumps(
            {
                "CFBundleName": "Valkiria Productividad",
                "CFBundleIdentifier": "com.valtre.valkiria",
                "CFBundleShortVersionString": "0.0.1",
                "CFBundleExecutable": "Valkiria-Productividad",
                "NSHumanReadableCopyright": "© VALTRE. Basado en Jan (Apache 2.0).",
            }
        )
    )
    (app / "Contents" / "MacOS").mkdir()
    (app / "Contents" / "MacOS" / "Valkiria-Productividad").write_bytes(b"")
    estado: dict[str, Any] = {
        "app": app,
        "conexiones": ["127.0.0.1:1337"],
        "proceso": ProcesoFalso(),
    }
    monkeypatch.setattr(smoke.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(smoke.subprocess, "Popen", lambda *a, **k: estado["proceso"])
    monkeypatch.setattr(smoke.time, "sleep", lambda s: None)
    reloj = iter(range(0, 10_000, 3))
    monkeypatch.setattr(smoke.time, "monotonic", lambda: float(next(reloj)))

    def ejecutar_falso(cmd: list[str]) -> str:
        if cmd[0] == "pgrep":
            return "4243\n" if cmd[-1] == "4242" else ""
        if cmd[0] == "lsof":
            filas = [
                f"app 4242 u 10u IPv4 TCP 10.0.0.2:5000->{c} (ESTABLISHED)"
                for c in estado["conexiones"]
            ]
            return "COMMAND PID USER FD TYPE NODE NAME\n" + "\n".join(filas)
        if cmd[0] == "screencapture":
            Path(cmd[-1]).write_bytes(b"png")
        return ""

    monkeypatch.setattr(smoke, "_ejecutar", ejecutar_falso)
    return estado


def test_ca_01_3_macos_sin_conexiones_externas(
    macos_simulado: dict[str, Any], tmp_path: Path
) -> None:
    r = smoke.ejecutar(macos_simulado["app"], 30, tmp_path / "out")
    assert r.ok, r
    assert r.conexiones_loopback > 0
    assert macos_simulado["proceso"].terminado
    assert (tmp_path / "out" / f"ventana-{r.so}.png").exists()
    assert json.loads((tmp_path / "out" / f"smoke-{r.so}.json").read_text())["ok"] is True


def test_ca_01_3_macos_conexion_externa_falla(
    macos_simulado: dict[str, Any], tmp_path: Path
) -> None:
    macos_simulado["conexiones"] = ["140.82.112.3:443"]
    r = smoke.ejecutar(macos_simulado["app"], 10, tmp_path)
    assert not r.ok
    assert r.conexiones_externas == ["140.82.112.3:443"]


def test_ca_01_1_app_que_se_cierra_falla(macos_simulado: dict[str, Any], tmp_path: Path) -> None:
    macos_simulado["proceso"] = ProcesoFalso(vive_ciclos=1)
    r = smoke.ejecutar(macos_simulado["app"], 30, tmp_path)
    assert not r.ok
    assert any("terminó" in e for e in r.errores)


def test_smoke_main(macos_simulado: dict[str, Any], tmp_path: Path) -> None:
    args = ["--app", str(macos_simulado["app"]), "--segundos", "6", "--salida", str(tmp_path)]
    assert smoke.main(args) == 0


def test_funciones_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    procesos = [
        {"ProcessId": 10, "ParentProcessId": 1},
        {"ProcessId": 11, "ParentProcessId": 10},
        {"ProcessId": 12, "ParentProcessId": 11},
        {"ProcessId": 99, "ParentProcessId": 2},
    ]
    respuestas = {
        "VersionInfo": json.dumps(
            {
                "ProductName": "Valkiria Productividad",
                "CompanyName": "VALTRE",
                "ProductVersion": "0.0.1",
            }
        ),
        "Win32_Process": json.dumps(procesos),
        "Get-NetTCPConnection": "127.0.0.1:1337\n\n20.1.1.1:443\n",
    }

    recibidas: list[dict[str, str]] = []

    def ps(script: str, **variables: str) -> str:
        recibidas.append(variables)
        assert "'" not in script.split("VK_")[0][-3:]  # las rutas no se interpolan
        return next((v for k, v in respuestas.items() if k in script), "")

    monkeypatch.setattr(smoke, "_ps", ps)
    ident = smoke.identidad_windows(tmp_path / "x.exe")
    assert smoke.validar_identidad(ident, "windows") == []
    assert sorted(smoke.descendientes_windows(10)) == [10, 11, 12]
    assert smoke.conexiones_windows([10, 11]) == ["127.0.0.1:1337", "20.1.1.1:443"]
    smoke.captura_windows(tmp_path / "v.png")
    assert recibidas[0] == {"ruta": str(tmp_path / "x.exe")}
    assert recibidas[-1] == {"destino": str(tmp_path / "v.png")}


def test_ejecutar_y_ps_reales() -> None:
    assert "hola" in smoke._ejecutar([sys.executable, "-c", "print('hola')"])


def test_ejecutable_de_valida_la_ruta(tmp_path: Path) -> None:
    app = tmp_path / "V.app"
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "MacOS" / "bin").write_bytes(b"")
    assert smoke.ejecutable_de(app, "macos", "bin").name == "bin"
    for nombre in ("", "../../otro", "sub/bin"):
        with pytest.raises((ValueError, FileNotFoundError)):
            smoke.ejecutable_de(app, "macos", nombre)
    carpeta = tmp_path / "NoEsApp"
    carpeta.mkdir()
    with pytest.raises(ValueError, match="bundle"):
        smoke.ejecutable_de(carpeta, "macos", "bin")
    exe = tmp_path / "Valkiria.exe"
    exe.write_bytes(b"")
    assert smoke.ejecutable_de(exe, "windows") == exe.resolve()
    with pytest.raises(ValueError, match="exe"):
        smoke.ejecutable_de(carpeta, "windows")
    with pytest.raises(FileNotFoundError):
        smoke.ejecutable_de(tmp_path / "falta.exe", "windows")


def test_ejecutar_con_entorno() -> None:
    codigo = "import os; print(os.environ['VK_X'])"
    assert smoke._ejecutar([sys.executable, "-c", codigo], {"VK_X": "valor"}).strip() == "valor"

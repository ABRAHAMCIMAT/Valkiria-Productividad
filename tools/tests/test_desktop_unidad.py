"""Pruebas independientes del SO para rebrand.py y smoke.py (HU-01)."""

import contextlib
import json
import plistlib
import sys
import types
from collections.abc import Iterator
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
                "LSMinimumSystemVersion": "27.2",
            }
        )
    )
    (app / "Contents" / "MacOS").mkdir()
    (app / "Contents" / "MacOS" / "Valkiria-Productividad").write_bytes(b"")
    control = {"pid": 7000}
    estado: dict[str, Any] = {
        "app": app,
        "conexiones": ["127.0.0.1:1337"],
        "proceso": ProcesoFalso(),
        "ventana": 77,
        # Registro de Network.framework: la conexión de control a loopback y las de la app.
        "registro": [
            {
                "processID": 7000,
                "processImagePath": "/usr/bin/nscurl",
                "eventMessage": "[C1 IPv4#ec5f:5000 in_progress (interface: lo0)]",
            },
            {
                "processID": 900,
                "processImagePath": "/x/com.apple.WebKit.Networking",
                "eventMessage": "[C4 IPv4#ab12:1337 quic, pid: 4242] (interface: lo0)",
            },
        ],
    }

    @contextlib.contextmanager
    def registro_falso(ejecutable: str, carpeta: Path) -> Iterator[Path]:
        assert ejecutable == "Valkiria-Productividad"
        archivo = carpeta / "registro-red.ndjson"
        yield archivo
        archivo.write_text(
            "Filtering the log data\n" + "".join(json.dumps(e) + "\n" for e in estado["registro"])
        )

    monkeypatch.setattr(smoke, "registro_red_macos", registro_falso)
    monkeypatch.setattr(smoke, "conexion_de_control", lambda: control["pid"])
    monkeypatch.setattr(smoke, "ventana_macos", lambda pids: estado["ventana"])
    monkeypatch.setattr(smoke.platform, "system", lambda: "Darwin")

    def popen(*a: Any, **k: Any) -> ProcesoFalso:
        estado["entorno"] = k.get("env")
        return estado["proceso"]

    monkeypatch.setattr(smoke.subprocess, "Popen", popen)
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
    assert r.captura == "ventana 77 de la app"
    # Perfil limpio: la app no abre los datos reales de quien corre la prueba.
    home = macos_simulado["entorno"]["HOME"]
    assert home != smoke.os.environ.get("HOME")
    assert "valkiria-perfil-" in home
    assert not Path(home).exists()  # se borra al terminar
    assert "HOME temporal" in r.perfil
    assert r.registro_red["control_loopback_visto"] is True
    (c,) = r.registro_red["conexiones_de_la_app"]  # type: ignore[misc]
    assert c["interfaces"] == ["lo0"]
    assert c["externa"] is False
    assert not (tmp_path / "out" / "registro-red.ndjson").exists()  # el crudo no se guarda
    assert json.loads((tmp_path / "out" / f"smoke-{r.so}.json").read_text())["ok"] is True


def test_ca_01_3_macos_webview_externo_por_registro_falla(
    macos_simulado: dict[str, Any], tmp_path: Path
) -> None:
    """Una conexión del WebView no aparece en lsof, pero sí en el registro de red."""
    macos_simulado["registro"].append(
        {
            "processID": 900,
            "processImagePath": "/x/com.apple.WebKit.Networking",
            "eventMessage": "[C5 Hostname#fe2e:443 quic, pid: 4243] (interface: en0)",
        }
    )
    r = smoke.ejecutar(macos_simulado["app"], 10, tmp_path)
    assert not r.ok
    assert r.conexiones_externas == ["com.apple.WebKit.Networking C5 vía en0"]


def test_ca_01_3_macos_sin_control_no_es_verificable(
    macos_simulado: dict[str, Any], tmp_path: Path
) -> None:
    macos_simulado["registro"] = []
    r = smoke.ejecutar(macos_simulado["app"], 10, tmp_path)
    assert not r.ok
    assert any("no es verificable" in e for e in r.errores)


def test_captura_macos_sin_ventana_o_sin_permiso(
    macos_simulado: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    macos_simulado["ventana"] = None
    assert "no tiene una ventana" in smoke.captura_macos(tmp_path / "a.png", {1})
    macos_simulado["ventana"] = 5
    monkeypatch.setattr(smoke, "_ejecutar", lambda cmd: "")  # sin permiso: no escribe nada
    assert "Grabación de pantalla" in smoke.captura_macos(tmp_path / "b.png", {1})


def test_ca_01_3_macos_conexion_externa_falla(
    macos_simulado: dict[str, Any], tmp_path: Path
) -> None:
    macos_simulado["conexiones"] = ["140.82.112.3:443"]
    r = smoke.ejecutar(macos_simulado["app"], 10, tmp_path)
    assert not r.ok
    assert r.conexiones_externas == ["140.82.112.3:443 (app)"]


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
        "Get-NetTCPConnection": (
            "127.0.0.1|1337|valkiria\n\n::1|80|msedgewebview2\n20.1.1.1|443|bun\nmal\n"
        ),
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
    assert smoke.conexiones_windows([10, 11]) == [
        ("127.0.0.1:1337", "valkiria"),
        ("[::1]:80", "msedgewebview2"),
        ("20.1.1.1:443", "bun"),
    ]
    assert smoke.captura_windows(tmp_path / "v.png", {10}) == "sin captura"
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


def test_escrituras_confinadas(tmp_path: Path) -> None:
    assert (
        rebrand.dentro_de(tmp_path, tmp_path / "a" / "b.json")
        == (tmp_path / "a" / "b.json").resolve()
    )
    with pytest.raises(rebrand.ParcheError, match="fuera"):
        rebrand.dentro_de(tmp_path / "app", tmp_path / "app" / ".." / "otro.json")
    assert smoke.carpeta_de_salida(tmp_path / "rep").is_dir()
    with pytest.raises(ValueError, match="salida"):
        smoke.carpeta_de_salida(Path("/") / "valkiria-no-permitido")


def test_contiene_con_unidades_distintas(monkeypatch: pytest.MonkeyPatch) -> None:
    def distinta_unidad(_: list[str]) -> str:
        raise ValueError("Paths don't have the same drive")

    monkeypatch.setattr(smoke.os.path, "commonpath", distinta_unidad)
    assert smoke.contiene("C:\\a", "D:\\b") is False
    assert rebrand.contiene("C:\\a", "D:\\b") is False


def test_sin_posthog_quita_solo_posthog() -> None:
    fuentes = (
        "'self' https://us.i.posthog.com https://posthog.com/x https://notposthog.com 'unsafe-eval'"
    )
    assert rebrand.sin_posthog(fuentes) == "'self' https://notposthog.com 'unsafe-eval'"
    assert rebrand.sin_posthog("'self'") == "'self'"


# ------------------------------------------- registro de red y captura (dobles portables)
def test_conexion_de_control_sirve_por_loopback(monkeypatch: pytest.MonkeyPatch) -> None:
    """El servidor de control es real; nscurl se reemplaza por una petición HTTP equivalente."""
    import urllib.request

    pedidas: list[str] = []

    class NscurlFalso:
        pid = 31337

        def __init__(self, cmd: list[str], **_: object) -> None:
            assert cmd[:3] == ["/usr/bin/nscurl", "-o", smoke.os.devnull]
            assert cmd[3].startswith("http://127.0.0.1:")
            with urllib.request.urlopen(cmd[3], timeout=10) as r:  # noqa: S310  # nosec B310
                pedidas.append(r.read().decode())

        def wait(self, timeout: float) -> int:
            return 0

    monkeypatch.setattr(smoke.subprocess, "Popen", NscurlFalso)
    assert smoke.conexion_de_control() == 31337
    assert pedidas == ["valkiria\n"]


def test_registro_red_macos_lanza_y_detiene_log_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    lanzados: list[list[str]] = []

    class StreamFalso:
        def __init__(self, cmd: list[str], stdout: Any, **_: object) -> None:
            lanzados.append(cmd)
            stdout.write('{"processID": 1, "eventMessage": "[C1 a:1 (interface: lo0)]"}\n')
            self.terminado = False

        def terminate(self) -> None:
            self.terminado = True

        def wait(self, timeout: float) -> int:
            return 0

    monkeypatch.setattr(smoke.subprocess, "Popen", StreamFalso)
    monkeypatch.setattr(smoke.time, "sleep", lambda s: None)
    with smoke.registro_red_macos("Valkiria-Productividad", tmp_path) as archivo:
        pass
    (cmd,) = lanzados
    assert cmd[:6] == ["/usr/bin/log", "stream", "--style", "ndjson", "--level", "info"]
    assert cmd[-1] == smoke.predicado_red("Valkiria-Productividad")
    (evento,) = smoke.leer_eventos(archivo.read_text().splitlines())
    assert evento["processID"] == 1


def _coregraphics_falso(ventanas: list[dict[str, int]]) -> dict[str, Any]:
    """Dobles de CoreGraphics y CoreFoundation con la forma de las llamadas que usa smoke."""
    liberados: list[object] = []

    def funcion(f: Any) -> Any:
        return f  # las funciones aceptan restype/argtypes como atributos

    cg = types.SimpleNamespace(
        CGWindowListCopyWindowInfo=funcion(lambda opciones, relativa: "lista" if ventanas else None)
    )
    cf = types.SimpleNamespace(
        CFArrayGetCount=funcion(lambda lista: len(ventanas)),
        CFArrayGetValueAtIndex=funcion(lambda lista, i: i),
        CFStringCreateWithCString=funcion(lambda a, texto, cod: texto.decode()),
        CFDictionaryGetValue=funcion(lambda i, clave: (i, clave) if clave in ventanas[i] else 0),
        CFNumberGetValue=funcion(
            lambda valor, tipo, ref: (
                setattr(ref._obj, "value", ventanas[valor[0]][valor[1]]) or True
            )
        ),
        CFRelease=funcion(lambda objeto: liberados.append(objeto)),
    )
    return {"cg": cg, "cf": cf, "liberados": liberados}


def test_ventana_macos_elige_la_ventana_normal_de_la_app(monkeypatch: pytest.MonkeyPatch) -> None:
    falso = _coregraphics_falso(
        [
            {"kCGWindowOwnerPID": 1, "kCGWindowLayer": 0, "kCGWindowNumber": 10},  # otra app
            {"kCGWindowOwnerPID": 42, "kCGWindowLayer": 25, "kCGWindowNumber": 11},  # menú
            {"kCGWindowOwnerPID": 42, "kCGWindowLayer": 0, "kCGWindowNumber": 12},
        ]
    )
    monkeypatch.setattr(
        smoke.ctypes, "CDLL", lambda ruta: falso["cg"] if "CoreGraphics" in ruta else falso["cf"]
    )
    assert smoke.ventana_macos({42, 43}) == 12
    assert "lista" in falso["liberados"]  # se libera lo que se copió
    assert smoke.ventana_macos({99}) is None


def test_ventana_macos_sin_lista(monkeypatch: pytest.MonkeyPatch) -> None:
    falso = _coregraphics_falso([])
    monkeypatch.setattr(
        smoke.ctypes, "CDLL", lambda ruta: falso["cg"] if "CoreGraphics" in ruta else falso["cf"]
    )
    assert smoke.ventana_macos({42}) is None


@pytest.mark.skipif(sys.platform != "darwin", reason="registro unificado solo en macOS")
def test_registro_red_real_ve_la_conexion_de_control(tmp_path: Path) -> None:
    """Con el SO real: log stream debe ver la conexión de control de nscurl por lo0."""
    with smoke.registro_red_macos("Valkiria-Productividad", tmp_path) as archivo:
        pid = smoke.conexion_de_control()
    eventos = list(smoke.leer_eventos(archivo.read_text(encoding="utf-8").splitlines()))
    assert any("lo0" in c.interfaces for c in smoke.conexiones_registradas(eventos, {pid}))


# ---------------------------------------------------- CA-01.3: proxy de registro (portable)
def test_proxy_de_registro_anota_y_rechaza_sin_salir_a_internet() -> None:
    import http.client

    with smoke.proxy_de_registro() as (entorno, intentos):
        puerto = int(entorno["HTTPS_PROXY"].rsplit(":", 1)[1])
        assert entorno["https_proxy"] == entorno["HTTPS_PROXY"]
        assert "127.0.0.1" in entorno["NO_PROXY"]
        # Lo que hace un cliente HTTPS con proxy: CONNECT al host remoto.
        c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=10)
        c.request("CONNECT", "huggingface.co:443")
        assert c.getresponse().status == 403
        c.close()
        for _ in range(50):  # el hilo del proxy anota en paralelo
            if intentos:
                break
            smoke.time.sleep(0.05)
    assert intentos == ["CONNECT huggingface.co:443 HTTP/1.1"]


def test_ca_01_3_intento_por_proxy_hace_fallar(
    macos_simulado: dict[str, Any], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    @contextlib.contextmanager
    def proxy_falso() -> Iterator[tuple[dict[str, str], list[str]]]:
        yield {"HTTPS_PROXY": "http://127.0.0.1:9"}, ["CONNECT apps.jan.ai:443 HTTP/1.1"]

    monkeypatch.setattr(smoke, "proxy_de_registro", proxy_falso)
    r = smoke.ejecutar(macos_simulado["app"], 10, tmp_path)
    assert not r.ok
    assert "proxy: CONNECT apps.jan.ai:443 HTTP/1.1" in r.conexiones_externas
    assert r.intentos_por_proxy == ["CONNECT apps.jan.ai:443 HTTP/1.1"]
    # La app recibe el proxy junto con el perfil limpio.
    assert macos_simulado["entorno"]["HTTPS_PROXY"] == "http://127.0.0.1:9"
    assert "HOME" in macos_simulado["entorno"]

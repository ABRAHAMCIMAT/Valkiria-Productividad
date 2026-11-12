"""Prueba de humo de la app de escritorio (HU-01: CA-01.1 y CA-01.3).

Uso:
  python3 tools/desktop/smoke.py --app "<ruta a .app o .exe>" --segundos 300 --salida reports/smoke

1. Verifica la identidad del binario: nombre, fabricante e identificador
   (CA-01.1, RN-01.1, RN-01.4).
2. Abre la app como en una instalación limpia y comprueba que sigue viva.
3. Toma una captura de pantalla como evidencia de la ventana con la marca. En macOS captura solo
   la ventana de la app, para no guardar el resto del escritorio de un equipo del equipo.
4. Durante ``--segundos`` registra cada conexión de red que abren la app y sus procesos hijos;
   cualquier destino que no sea loopback hace fallar la prueba (CA-01.3).

Solo usa la biblioteca estándar y herramientas del SO (lsof/pgrep/log/screencapture en macOS y
PowerShell en Windows). El muestreo de sockets es cada 2 s, así que una conexión más corta podría no
verse. En macOS lo complementa el registro unificado de Network.framework (``log stream``), que
anota cada conexión al iniciarse, con la interfaz por la que sale, incluidas las del WebView: WebKit
las abre desde ``com.apple.WebKit.Networking``, que no es hijo de la app y no aparece en ``lsof``,
pero anota el pid del cliente. Antes de abrir la app se hace una conexión de control a loopback con
``nscurl``; si el registro no la ve, la prueba falla porque CA-01.3 no sería verificable.
"""

from __future__ import annotations

import argparse
import contextlib
import ctypes
import http.server
import ipaddress
import json
import os
import platform
import plistlib
import re

# Solo herramientas del SO con argumentos controlados.
import subprocess  # nosec B404
import sys
import tempfile
import threading
import time
from collections.abc import Callable, Iterable, Iterator
from dataclasses import asdict, dataclass, field
from pathlib import Path

NOMBRE = "Valkiria Productividad"
FABRICANTE = "VALTRE"
IDENTIFICADOR = "com.valtre.valkiria"
MACOS_MINIMO = "27.2"  # igual que tools/desktop/rebrand.py (R-12)


@dataclass
class Resultado:
    so: str
    app: str
    identidad: dict[str, str] = field(default_factory=dict)
    errores: list[str] = field(default_factory=list)
    conexiones_externas: list[str] = field(default_factory=list)
    conexiones_loopback: int = 0
    viva_al_final: bool = False
    segundos: int = 0
    captura: str = ""
    registro_red: dict[str, object] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errores and not self.conexiones_externas and self.viva_al_final


def es_externa(direccion: str) -> bool:
    """``True`` si la dirección remota no es loopback ni comodín (``*``, ``0.0.0.0``, ``::``)."""
    host = direccion.strip()
    if host.startswith("["):
        host = host[1 : host.index("]")]
    elif host.count(":") == 1:
        host = host.rsplit(":", 1)[0]
    if host in {"", "*", "localhost"}:
        return False
    # IPv6 sin corchetes con puerto al final (así lo imprime PowerShell): "::1:80".
    # Las fuentes siempre incluyen el puerto, así que primero se prueba sin él.
    candidatos = [host.rsplit(":", 1)[0], host] if ":" in host else [host]
    for candidato in candidatos:
        try:
            ip = ipaddress.ip_address(candidato.split("%")[0])
        except ValueError:
            continue
        return not (ip.is_loopback or ip.is_unspecified)
    return True  # nombre de host resuelto: lo tratamos como externo


def _ejecutar(cmd: list[str], env: dict[str, str] | None = None) -> str:
    entorno = {**os.environ, **env} if env else None
    salida = subprocess.run(  # noqa: S603  # nosec B603
        cmd, capture_output=True, text=True, check=False, timeout=60, env=entorno
    )
    return salida.stdout


# ---------------- macOS ----------------
def identidad_macos(app: Path) -> dict[str, str]:
    info = plistlib.loads((app / "Contents" / "Info.plist").read_bytes())
    return {
        "nombre": str(info.get("CFBundleName", "")),
        "nombre_visible": str(info.get("CFBundleDisplayName", info.get("CFBundleName", ""))),
        "identificador": str(info.get("CFBundleIdentifier", "")),
        "version": str(info.get("CFBundleShortVersionString", "")),
        "copyright": str(info.get("NSHumanReadableCopyright", "")),
        "ejecutable": str(info.get("CFBundleExecutable", "")),
        "macos_minimo": str(info.get("LSMinimumSystemVersion", "")),
    }


def descendientes_macos(pid: int) -> list[int]:
    pids, pendientes = [pid], [pid]
    while pendientes:
        hijos = _ejecutar(["pgrep", "-P", str(pendientes.pop())]).split()
        nuevos = [int(h) for h in hijos if int(h) not in pids]
        pids += nuevos
        pendientes += nuevos
    return pids


def conexiones_macos(pids: list[int]) -> list[tuple[str, str]]:
    """Pares ``(dirección remota, proceso)`` de las conexiones de ``pids``."""
    salida = _ejecutar(["lsof", "-nP", "-a", "-p", ",".join(map(str, pids)), "-iTCP", "-iUDP"])
    remotas = []
    for linea in salida.splitlines()[1:]:
        campos = linea.split()
        nombre = campos[-1] if "(" not in campos[-1] else campos[-2]
        if "->" in nombre:
            remotas.append((nombre.split("->", 1)[1], campos[0]))
    return remotas


# Conexiones de Network.framework en el registro unificado de macOS (ver el docstring).
WEBKIT_RED = "com.apple.WebKit.Networking"
CONTROL = "nscurl"
INTERFACES_LOOPBACK = frozenset({"lo0"})
_CONEXION = re.compile(r"\[(C\d+)(?:\.\d+)*[ \]]")
_PID_CLIENTE = re.compile(r"\bpid: (\d+)\b")
_INTERFAZ = re.compile(r"\binterface: ([A-Za-z]+\d*)")


def predicado_red(ejecutable: str) -> str:
    """Predicado de ``log stream``: la app, el proceso de red de WebKit y la conexión de control."""
    if not re.fullmatch(r"[\w.-]+", ejecutable):
        raise ValueError(f"nombre de ejecutable inválido para el predicado: {ejecutable!r}")
    procesos = " OR ".join(f'process == "{p}"' for p in (ejecutable, WEBKIT_RED, CONTROL))
    # Sin filtro de subsystem: en modo stream descarta los mensajes de conexión de WebKit.
    return procesos


@dataclass(frozen=True)
class ConexionRegistrada:
    proceso: str
    pid: int
    conexion: str
    interfaces: list[str]

    @property
    def externa(self) -> bool:
        return bool(set(self.interfaces) - INTERFACES_LOOPBACK)


def conexiones_registradas(
    eventos: Iterable[dict[str, object]], pids: set[int]
) -> list[ConexionRegistrada]:
    """Conexiones del registro atribuidas a ``pids``, con las interfaces por las que salieron.

    Una conexión se identifica por el proceso que la abre y su id raíz (``C3`` para ``C3.1.2``).
    Se atribuye si la abre uno de ``pids`` o si algún mensaje suyo nombra a uno como cliente
    (``pid: N``), que es como WebKit anota las del WebView.
    """
    atribuidas: set[tuple[int, str]] = set()
    interfaces: dict[tuple[int, str], set[str]] = {}
    procesos: dict[tuple[int, str], str] = {}
    for e in eventos:
        mensaje = str(e.get("eventMessage", ""))
        pid = e.get("processID")
        conexion = _CONEXION.search(mensaje)
        if not conexion or not isinstance(pid, int):
            continue
        clave = (pid, conexion.group(1))
        procesos[clave] = Path(str(e.get("processImagePath", ""))).name
        cliente = _PID_CLIENTE.search(mensaje)
        if pid in pids or (cliente and int(cliente.group(1)) in pids):
            atribuidas.add(clave)
        interfaces.setdefault(clave, set()).update(_INTERFAZ.findall(mensaje))
    return [
        ConexionRegistrada(procesos[k], k[0], k[1], sorted(interfaces.get(k, set())))
        for k in sorted(atribuidas)
    ]


def leer_eventos(lineas: Iterable[str]) -> Iterator[dict[str, object]]:
    """Eventos de ``log stream --style ndjson``; ignora la cabecera y las líneas que no son JSON."""
    for linea in lineas:
        with contextlib.suppress(ValueError):
            evento = json.loads(linea)
            if isinstance(evento, dict):
                yield evento


class _Silencioso(http.server.SimpleHTTPRequestHandler):
    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        return


def conexion_de_control() -> int:
    """Hace una petición con ``nscurl`` (Network.framework) a un servidor en 127.0.0.1.

    Devuelve el pid de ``nscurl``, para buscar su conexión en el registro.
    """
    with (
        tempfile.TemporaryDirectory() as carpeta,
        http.server.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            lambda *a, **k: _Silencioso(*a, directory=carpeta, **k),
        ) as servidor,
    ):
        (Path(carpeta) / "control.txt").write_bytes(b"valkiria\n")  # igual en todo SO
        hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
        hilo.start()
        url = f"http://127.0.0.1:{servidor.server_address[1]}/control.txt"
        # Herramienta del SO con argumentos controlados (URL de loopback construida aquí).
        control = subprocess.Popen(  # noqa: S603  # nosec B603
            ["/usr/bin/nscurl", "-o", os.devnull, url],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        control.wait(timeout=30)
        servidor.shutdown()
    return control.pid


@contextlib.contextmanager
def registro_red_macos(ejecutable: str, carpeta: Path) -> Iterator[Path]:
    """Escucha el registro de red mientras dura el bloque y lo guarda en ``carpeta``."""
    archivo = carpeta / "registro-red.ndjson"
    with archivo.open("w", encoding="utf-8") as salida:
        # /usr/bin/log con un predicado construido y validado por predicado_red().
        stream = subprocess.Popen(  # noqa: S603  # nosec B603
            [
                "/usr/bin/log",
                "stream",
                "--style",
                "ndjson",
                "--level",
                "info",
                "--predicate",
                predicado_red(ejecutable),
            ],
            stdout=salida,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)  # log stream tarda en engancharse
        try:
            yield archivo
        finally:
            time.sleep(2)  # deja llegar los últimos eventos
            stream.terminate()
            stream.wait(timeout=15)


def ventana_macos(pids: set[int]) -> int | None:
    """Id de la primera ventana normal en pantalla de alguno de ``pids`` (CoreGraphics)."""
    cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
    cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")
    vp = ctypes.c_void_p
    cg.CGWindowListCopyWindowInfo.restype = vp
    cg.CGWindowListCopyWindowInfo.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
    cf.CFArrayGetCount.restype = ctypes.c_long
    cf.CFArrayGetCount.argtypes = [vp]
    cf.CFArrayGetValueAtIndex.restype = vp
    cf.CFArrayGetValueAtIndex.argtypes = [vp, ctypes.c_long]
    cf.CFDictionaryGetValue.restype = vp
    cf.CFDictionaryGetValue.argtypes = [vp, vp]
    cf.CFStringCreateWithCString.restype = vp
    cf.CFStringCreateWithCString.argtypes = [vp, ctypes.c_char_p, ctypes.c_uint32]
    cf.CFNumberGetValue.restype = ctypes.c_bool
    cf.CFNumberGetValue.argtypes = [vp, ctypes.c_int, vp]
    cf.CFRelease.argtypes = [vp]
    utf8, sint64 = 0x08000100, 4
    solo_en_pantalla, sin_escritorio = 1, 16
    claves = {
        n: cf.CFStringCreateWithCString(None, n.encode(), utf8)
        for n in ("kCGWindowOwnerPID", "kCGWindowLayer", "kCGWindowNumber")
    }

    def numero(d: int, clave: str) -> int | None:
        valor = cf.CFDictionaryGetValue(d, claves[clave])
        if not valor:
            return None
        n = ctypes.c_int64()
        return n.value if cf.CFNumberGetValue(valor, sint64, ctypes.byref(n)) else None

    lista = cg.CGWindowListCopyWindowInfo(solo_en_pantalla | sin_escritorio, 0)
    try:
        for i in range(cf.CFArrayGetCount(lista) if lista else 0):
            d = cf.CFArrayGetValueAtIndex(lista, i)
            if numero(d, "kCGWindowOwnerPID") in pids and numero(d, "kCGWindowLayer") == 0:
                return numero(d, "kCGWindowNumber")
        return None
    finally:
        if lista:
            cf.CFRelease(lista)
        for c in claves.values():
            cf.CFRelease(c)


def captura_macos(destino: Path, pids: set[int]) -> str:
    """Captura solo la ventana de la app; devuelve qué se hizo, para dejarlo en la evidencia."""
    ventana = ventana_macos(pids)
    if ventana is None:
        return "sin captura: la app no tiene una ventana en pantalla"
    _ejecutar(["screencapture", "-x", "-o", "-l", str(ventana), str(destino)])
    if not destino.is_file() or destino.stat().st_size == 0:
        return (
            "sin captura: screencapture no generó la imagen "
            "(¿falta el permiso de Grabación de pantalla para la terminal?)"
        )
    return f"ventana {ventana} de la app"


# ---------------- Windows ----------------
def _ps(script: str, **variables: str) -> str:
    """Ejecuta PowerShell. Las rutas viajan como variables de entorno ``$env:VK_*``, nunca
    interpoladas en el script, para que no puedan inyectar comandos."""
    env = {f"VK_{k.upper()}": v for k, v in variables.items()}
    return _ejecutar(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], env)


def identidad_windows(exe: Path) -> dict[str, str]:
    datos = json.loads(
        _ps(
            "(Get-Item -LiteralPath $env:VK_RUTA).VersionInfo | "
            "Select-Object ProductName,CompanyName,FileDescription,ProductVersion,LegalCopyright "
            "| ConvertTo-Json",
            ruta=str(exe),
        )
        or "{}"
    )
    return {
        "nombre": str(datos.get("ProductName") or ""),
        "nombre_visible": str(datos.get("FileDescription") or ""),
        "fabricante": str(datos.get("CompanyName") or ""),
        "version": str(datos.get("ProductVersion") or ""),
        "copyright": str(datos.get("LegalCopyright") or ""),
    }


def descendientes_windows(pid: int) -> list[int]:
    salida = _ps(
        "Get-CimInstance Win32_Process | Select-Object ProcessId,ParentProcessId | ConvertTo-Json"
    )
    tabla = json.loads(salida or "[]")
    hijos: dict[int, list[int]] = {}
    for p in tabla if isinstance(tabla, list) else [tabla]:
        hijos.setdefault(int(p["ParentProcessId"]), []).append(int(p["ProcessId"]))
    pids, pendientes = [pid], [pid]
    while pendientes:
        nuevos = [h for h in hijos.get(pendientes.pop(), []) if h not in pids]
        pids += nuevos
        pendientes += nuevos
    return pids


def conexiones_windows(pids: list[int]) -> list[tuple[str, str]]:
    """Pares ``(dirección remota, proceso)`` de las conexiones TCP de ``pids``."""
    lista = ",".join(map(str, pids))
    filtro = f"@({lista}) -contains $_.OwningProcess -and $_.State -ne 'Listen'"
    formato = (
        '"$($_.RemoteAddress)|$($_.RemotePort)|'
        '$((Get-Process -Id $_.OwningProcess -ErrorAction SilentlyContinue).ProcessName)"'
    )
    salida = _ps(
        "Get-NetTCPConnection -ErrorAction SilentlyContinue | "
        f"Where-Object {{ {filtro} }} | ForEach-Object {{ {formato} }}"
    )
    pares = []
    for linea in salida.splitlines():
        partes = linea.strip().split("|")
        if len(partes) == 3:
            direccion, puerto, proceso = partes
            remota = f"[{direccion}]:{puerto}" if ":" in direccion else f"{direccion}:{puerto}"
            pares.append((remota, proceso or "?"))
    return pares


def captura_windows(destino: Path, pids: set[int]) -> str:
    """Pantalla completa: en Windows la prueba corre en un runner de CI sin otras ventanas."""
    _ps(
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
        "$i=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
        "$g=[System.Drawing.Graphics]::FromImage($i);$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
        "$i.Save($env:VK_DESTINO)",
        destino=str(destino),
    )
    return "pantalla completa del runner" if destino.is_file() else "sin captura"


# ---------------- Prueba ----------------
def validar_identidad(ident: dict[str, str], so: str) -> list[str]:
    errores = []
    if ident.get("nombre") != NOMBRE:
        errores.append(f"nombre del producto: {ident.get('nombre')!r} (se espera {NOMBRE!r})")
    if so == "macos" and ident.get("identificador") != IDENTIFICADOR:
        errores.append(
            f"identificador: {ident.get('identificador')!r} (se espera {IDENTIFICADOR!r})"
        )
    if so == "macos" and ident.get("macos_minimo") != MACOS_MINIMO:
        errores.append(
            f"LSMinimumSystemVersion: {ident.get('macos_minimo')!r} (se espera {MACOS_MINIMO!r})"
        )
    if so == "windows" and FABRICANTE not in ident.get("fabricante", "") + ident.get(
        "copyright", ""
    ):
        errores.append(f"fabricante: {ident.get('fabricante')!r} (se espera {FABRICANTE!r})")
    if "jan" in " ".join(ident.values()).lower().replace("basado en jan", ""):
        errores.append(f"la identidad del binario todavía menciona Jan: {ident}")
    return errores


def ejecutable_de(app: Path, so: str, nombre_binario: str = "") -> Path:
    """Valida la ruta recibida y devuelve el binario a lanzar.

    Solo se aceptan un bundle ``.app`` (con un nombre de binario simple tomado de su Info.plist)
    o un ``.exe`` existente; cualquier otra cosa se rechaza antes de ejecutar nada.
    """
    app = app.resolve(strict=True)
    if so == "macos":
        if (
            app.suffix != ".app"
            or not nombre_binario
            or Path(nombre_binario).name != nombre_binario
        ):
            raise ValueError(f"no es un bundle .app válido: {app}")
        binario = (app / "Contents" / "MacOS" / nombre_binario).resolve(strict=True)
        if app not in binario.parents:
            raise ValueError(f"el binario sale del bundle: {binario}")
        return binario
    if app.suffix.lower() != ".exe" or not app.is_file():
        raise ValueError(f"no es un .exe válido: {app}")
    return app


def contiene(base: str, destino: str) -> bool:
    """``True`` si ``destino`` está dentro de ``base``. Unidades distintas en Windows: no."""
    try:
        return os.path.commonpath([base, destino]) == base
    except ValueError:
        return False


def carpeta_de_salida(salida: Path) -> Path:
    """Solo se escriben reportes dentro del directorio de trabajo o del temporal del sistema."""
    destino = os.path.realpath(salida)
    permitidas = [os.path.realpath(Path.cwd()), os.path.realpath(tempfile.gettempdir())]
    if not any(contiene(base, destino) for base in permitidas):
        raise ValueError(f"la carpeta de salida debe estar en {permitidas}: {destino}")
    Path(destino).mkdir(parents=True, exist_ok=True)
    return Path(destino)


def ejecutar(app: Path, segundos: int, salida: Path) -> Resultado:
    so = "macos" if platform.system() == "Darwin" else "windows"
    r = Resultado(so=f"{so}-{platform.machine().lower()}", app=str(app), segundos=segundos)
    salida = carpeta_de_salida(salida)

    if so == "macos":
        r.identidad = identidad_macos(app)
        ejecutable = ejecutable_de(app, so, r.identidad["ejecutable"])
        descendientes, conexiones, captura = descendientes_macos, conexiones_macos, captura_macos
    else:
        r.identidad = identidad_windows(app)
        ejecutable = ejecutable_de(app, so)
        descendientes, conexiones, captura = (
            descendientes_windows,
            conexiones_windows,
            captura_windows,
        )
    r.errores += validar_identidad(r.identidad, so)

    if so != "macos":
        _observar(r, ejecutable, segundos, salida, descendientes, conexiones, captura, set())
        return _guardar(r, salida)
    pids_vistos: set[int] = set()
    with registro_red_macos(ejecutable.name, salida) as archivo:
        control = conexion_de_control()
        _observar(r, ejecutable, segundos, salida, descendientes, conexiones, captura, pids_vistos)
    with archivo.open(encoding="utf-8") as f:
        eventos = list(leer_eventos(f))
    de_control = conexiones_registradas(eventos, {control})
    de_app = conexiones_registradas(eventos, pids_vistos)
    verificado = any("lo0" in c.interfaces for c in de_control)
    r.registro_red = {
        "metodo": "log stream (Network.framework), incluye com.apple.WebKit.Networking",
        "control_loopback_visto": verificado,
        "eventos": len(eventos),
        "conexiones_de_la_app": [asdict(c) | {"externa": c.externa} for c in de_app],
    }
    # El resumen queda en el JSON; el registro crudo puede traer datos de otras apps.
    archivo.unlink()
    if not verificado:
        r.errores.append(
            "el registro de red no capturó la conexión de control a 127.0.0.1: "
            "CA-01.3 no es verificable en este equipo"
        )
    for c in de_app:
        if c.externa:
            vista = f"{c.proceso} {c.conexion} vía {', '.join(c.interfaces)}"
            print(f"::error title=CA-01.3::conexión saliente registrada: {vista}")
            r.conexiones_externas.append(vista)
    r.conexiones_externas.sort()
    return _guardar(r, salida)


def _guardar(r: Resultado, salida: Path) -> Resultado:
    (salida / f"smoke-{r.so}.json").write_text(
        json.dumps(asdict(r) | {"ok": r.ok}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return r


def _observar(
    r: Resultado,
    ejecutable: Path,
    segundos: int,
    salida: Path,
    descendientes: Callable[[int], list[int]],
    conexiones: Callable[[list[int]], list[tuple[str, str]]],
    captura: Callable[[Path, set[int]], str],
    pids_vistos: set[int],
) -> None:
    """Abre la app, muestrea sus sockets cada 2 s y toma la captura a los 20 s."""
    # Herramienta de CI: lanza la app recién instalada, validada por ejecutable_de().
    proceso = subprocess.Popen(  # noqa: S603  # nosec B603  # NOSONAR
        [str(ejecutable)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    vistas: set[str] = set()
    inicio = time.monotonic()
    capturada = False
    try:
        while time.monotonic() - inicio < segundos:
            if proceso.poll() is not None:
                transcurrido = time.monotonic() - inicio
                r.errores.append(
                    f"la app terminó a los {transcurrido:.0f} s (código {proceso.returncode})"
                )
                break
            pids = descendientes(proceso.pid)
            pids_vistos.update(pids)
            for remota, nombre in conexiones(pids):
                if es_externa(remota):
                    vista = f"{remota} ({nombre})"
                    if vista not in vistas:
                        print(f"::error title=CA-01.3::conexión saliente a {vista}")
                    vistas.add(vista)
                else:
                    r.conexiones_loopback += 1
            if not capturada and time.monotonic() - inicio > 20:
                r.captura = captura(salida / f"ventana-{r.so}.png", set(pids_vistos))
                capturada = True
            time.sleep(2)
        r.viva_al_final = proceso.poll() is None
    finally:
        proceso.terminate()
        try:
            proceso.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proceso.kill()
    r.conexiones_externas = sorted(vistas)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--app", type=Path, required=True)
    ap.add_argument("--segundos", type=int, default=300)
    ap.add_argument("--salida", type=Path, default=Path("reports/smoke"))
    a = ap.parse_args(argv)
    r = ejecutar(a.app, a.segundos, a.salida)
    print(json.dumps(asdict(r) | {"ok": r.ok}, indent=2, ensure_ascii=False))
    for e in r.errores:
        print(f"::error title=Prueba de humo::{e}")
    return 0 if r.ok else 1


if __name__ == "__main__":
    sys.exit(main())

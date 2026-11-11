"""Prueba de humo de la app de escritorio (HU-01: CA-01.1 y CA-01.3).

Uso:
  python3 tools/desktop/smoke.py --app "<ruta a .app o .exe>" --segundos 300 --salida reports/smoke

1. Verifica la identidad del binario: nombre, fabricante e identificador
   (CA-01.1, RN-01.1, RN-01.4).
2. Abre la app como en una instalación limpia y comprueba que sigue viva.
3. Toma una captura de pantalla como evidencia de la ventana con la marca.
4. Durante ``--segundos`` registra cada conexión de red que abren la app y sus procesos hijos;
   cualquier destino que no sea loopback hace fallar la prueba (CA-01.3).

Solo usa la biblioteca estándar y herramientas del SO (lsof/pgrep/screencapture en macOS y
PowerShell en Windows). Limitación: se muestrea cada 2 s, así que una conexión que dure menos
podría no verse; por eso el resultado se complementa con la revisión de código de VALKIRIA.md.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import platform
import plistlib

# Solo herramientas del SO con argumentos controlados.
import subprocess  # nosec B404
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

NOMBRE = "Valkiria Productividad"
FABRICANTE = "VALTRE"
IDENTIFICADOR = "com.valtre.valkiria"


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
    try:
        ip = ipaddress.ip_address(host.split("%")[0])
    except ValueError:
        return True  # nombre de host resuelto: lo tratamos como externo
    return not (ip.is_loopback or ip.is_unspecified)


def _ejecutar(cmd: list[str]) -> str:
    salida = subprocess.run(cmd, capture_output=True, text=True, check=False, timeout=60)  # noqa: S603  # nosec B603
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
    }


def descendientes_macos(pid: int) -> list[int]:
    pids, pendientes = [pid], [pid]
    while pendientes:
        hijos = _ejecutar(["pgrep", "-P", str(pendientes.pop())]).split()
        nuevos = [int(h) for h in hijos if int(h) not in pids]
        pids += nuevos
        pendientes += nuevos
    return pids


def conexiones_macos(pids: list[int]) -> list[str]:
    salida = _ejecutar(["lsof", "-nP", "-a", "-p", ",".join(map(str, pids)), "-iTCP", "-iUDP"])
    remotas = []
    for linea in salida.splitlines()[1:]:
        nombre = linea.split()[-1] if "(" not in linea.split()[-1] else linea.split()[-2]
        if "->" in nombre:
            remotas.append(nombre.split("->", 1)[1])
    return remotas


def captura_macos(destino: Path) -> None:
    _ejecutar(["screencapture", "-x", str(destino)])


# ---------------- Windows ----------------
def _ps(script: str) -> str:
    return _ejecutar(["powershell", "-NoProfile", "-NonInteractive", "-Command", script])


def identidad_windows(exe: Path) -> dict[str, str]:
    datos = json.loads(
        _ps(
            f"(Get-Item -LiteralPath '{exe}').VersionInfo | "
            "Select-Object ProductName,CompanyName,FileDescription,ProductVersion,LegalCopyright "
            "| ConvertTo-Json"
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


def conexiones_windows(pids: list[int]) -> list[str]:
    lista = ",".join(map(str, pids))
    filtro = f"@({lista}) -contains $_.OwningProcess -and $_.State -ne 'Listen'"
    formato = '"$($_.RemoteAddress):$($_.RemotePort)"'
    salida = _ps(
        "Get-NetTCPConnection -ErrorAction SilentlyContinue | "
        f"Where-Object {{ {filtro} }} | ForEach-Object {{ {formato} }}"
    )
    return [linea.strip() for linea in salida.splitlines() if linea.strip()]


def captura_windows(destino: Path) -> None:
    _ps(
        "Add-Type -AssemblyName System.Windows.Forms,System.Drawing;"
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;"
        "$i=New-Object System.Drawing.Bitmap $b.Width,$b.Height;"
        "$g=[System.Drawing.Graphics]::FromImage($i);$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
        f"$i.Save('{destino}')"
    )


# ---------------- Prueba ----------------
def validar_identidad(ident: dict[str, str], so: str) -> list[str]:
    errores = []
    if ident.get("nombre") != NOMBRE:
        errores.append(f"nombre del producto: {ident.get('nombre')!r} (se espera {NOMBRE!r})")
    if so == "macos" and ident.get("identificador") != IDENTIFICADOR:
        errores.append(
            f"identificador: {ident.get('identificador')!r} (se espera {IDENTIFICADOR!r})"
        )
    if so == "windows" and FABRICANTE not in ident.get("fabricante", "") + ident.get(
        "copyright", ""
    ):
        errores.append(f"fabricante: {ident.get('fabricante')!r} (se espera {FABRICANTE!r})")
    if "jan" in " ".join(ident.values()).lower().replace("basado en jan", ""):
        errores.append(f"la identidad del binario todavía menciona Jan: {ident}")
    return errores


def ejecutar(app: Path, segundos: int, salida: Path) -> Resultado:
    so = "macos" if platform.system() == "Darwin" else "windows"
    r = Resultado(so=f"{so}-{platform.machine().lower()}", app=str(app), segundos=segundos)
    salida.mkdir(parents=True, exist_ok=True)

    if so == "macos":
        r.identidad = identidad_macos(app)
        ejecutable = app / "Contents" / "MacOS" / r.identidad["ejecutable"]
        descendientes, conexiones, captura = descendientes_macos, conexiones_macos, captura_macos
    else:
        r.identidad = identidad_windows(app)
        ejecutable = app
        descendientes, conexiones, captura = (
            descendientes_windows,
            conexiones_windows,
            captura_windows,
        )
    r.errores += validar_identidad(r.identidad, so)

    proceso = subprocess.Popen(  # noqa: S603  # nosec B603
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
            for remota in conexiones(descendientes(proceso.pid)):
                if es_externa(remota):
                    if remota not in vistas:
                        print(f"::error title=CA-01.3::conexión saliente a {remota}")
                    vistas.add(remota)
                else:
                    r.conexiones_loopback += 1
            if not capturada and time.monotonic() - inicio > 20:
                captura(salida / f"ventana-{r.so}.png")
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
    (salida / f"smoke-{r.so}.json").write_text(
        json.dumps(asdict(r) | {"ok": r.ok}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return r


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

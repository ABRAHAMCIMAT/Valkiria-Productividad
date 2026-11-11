"""Aplica la marca y la configuración por defecto de Valkiria sobre el fork de Jan (HU-01).

Uso:
  python3 tools/desktop/rebrand.py            # aplica los cambios (idempotente)
  python3 tools/desktop/rebrand.py --check    # falla si falta algún cambio (para CI)

Cada parche de texto exige encontrar el fragmento original o el ya parchado. Si una sincronización
con upstream (tools/desktop/sync-jan.sh) cambia el código, el script falla y señala el parche en
lugar de dejar la marca a medias (riesgo R-03). La lista completa de desviaciones respecto a Jan
está documentada en apps/desktop/VALKIRIA.md.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
APP = RAIZ / "apps" / "desktop"
MARCA = Path(__file__).resolve().parent / "marca"

NOMBRE = "Valkiria Productividad"
NOMBRE_CORTO = "Valkiria"
FABRICANTE = "VALTRE"
IDENTIFICADOR = "com.valtre.valkiria"
BINARIO = "Valkiria-Productividad"
VERSION = "0.0.1"
ATRIBUCION_ES = (
    "Basado en Jan, de Menlo Research, bajo la licencia Apache 2.0. "
    "Valkiria Productividad no está afiliado a Menlo Research."
)
ATRIBUCION_EN = (
    "Based on Jan by Menlo Research, licensed under the Apache License 2.0. "
    "Valkiria Productividad is not affiliated with Menlo Research."
)


class ParcheError(RuntimeError):
    """Un parche no encontró ni el texto original ni el ya aplicado."""


@dataclass(frozen=True, slots=True)
class Parche:
    ruta: str
    original: str
    nuevo: str
    motivo: str

    def aplicar(self, texto: str) -> tuple[str, bool]:
        if self.nuevo in texto:
            return texto, False
        if self.original not in texto:
            raise ParcheError(f"{self.ruta}: no se encontró el fragmento ({self.motivo})")
        return texto.replace(self.original, self.nuevo, 1), True


PARCHES = [
    # --- RN-01.1 · marca visible ---
    Parche("web-app/index.html", "<title>Jan</title>", f"<title>{NOMBRE}</title>", "título"),
    Parche(
        "web-app/src/components/left-sidebar/index.tsx",
        '<span className="ml-2 font-medium font-studio">Jan</span>',
        f'<span className="ml-2 font-medium font-studio">{NOMBRE_CORTO}</span>',
        "nombre en la barra lateral",
    ),
    Parche(
        "web-app/src/hooks/useAssistant.ts", "name: 'Jan',", f"name: '{NOMBRE_CORTO}',", "asistente"
    ),
    Parche(
        "web-app/src/lib/utils.ts",
        "case 'jan':\n      return 'Jan'",
        f"case 'jan':\n      return '{NOMBRE_CORTO}'",
        "nombre del proveedor local",
    ),
    Parche(
        "web-app/src/lib/ai-model.ts",
        "'X-Title': 'Jan',",
        f"'X-Title': '{NOMBRE}',",
        "cabecera X-Title",
    ),
    Parche(
        "web-app/src/services/threads/default.ts",
        "id: 'jan', name: 'Jan' }",
        f"id: 'jan', name: '{NOMBRE_CORTO}' }}",
        "asistente por defecto de los hilos",
    ),
    Parche(
        "web-app/src/components/MermaidError.tsx",
        'alt="Jan Logo"',
        f'alt="{NOMBRE}"',
        "texto alternativo del logo",
    ),
    Parche(
        "web-app/src/containers/SetupScreen.tsx",
        'alt="Jan Logo"',
        f'alt="{NOMBRE}"',
        "texto alternativo del logo",
    ),
    Parche(
        "web-app/src/routes/settings/mcp-servers.tsx",
        'src="/images/jan-logo.png"\n                                alt="Jan"',
        f'src="/images/jan-logo.png"\n                                alt="{NOMBRE_CORTO}"',
        "texto alternativo del logo",
    ),
    # --- RN-01.2 · "Acerca de": versión, fabricante y atribución ---
    Parche(
        "web-app/src/routes/settings/general.tsx",
        """                    v{VERSION}
                  </span>
                }
              />
""",
        """                    v{VERSION}
                  </span>
                }
              />
              <CardItem
                title={t('settings:general.aboutTitle')}
                description={t('settings:general.aboutAttribution')}
              />
""",
        "tarjeta Acerca de",
    ),
    # --- RN-01.3 · sin proveedores ni conexiones remotas por defecto ---
    Parche(
        "web-app/vite.config.ts",
        """      MODEL_CATALOG_URL: JSON.stringify(
        'https://raw.githubusercontent.com/janhq/model-catalog/main/model_catalog_v2.json'
      ),
      LATEST_JAN_MODEL_URL: JSON.stringify(
        'https://raw.githubusercontent.com/janhq/model-catalog/main/latest_jan_model.json'
      ),
      AUTO_UPDATER_DISABLED: JSON.stringify(
        env.AUTO_UPDATER_DISABLED === 'true'
      ),""",
        """      // Valkiria: sin catálogo remoto de Jan; el verificado llega en F1 (HU-05).
      MODEL_CATALOG_URL: JSON.stringify(env.VALKIRIA_MODEL_CATALOG_URL ?? ''),
      LATEST_JAN_MODEL_URL: JSON.stringify(env.VALKIRIA_LATEST_MODEL_URL ?? ''),
      // Valkiria: el updater de Jan queda desactivado; el propio llega en F10 (HU-26).
      AUTO_UPDATER_DISABLED: JSON.stringify(
        env.AUTO_UPDATER_DISABLED !== 'false'
      ),""",
        "catálogo remoto y updater desactivados",
    ),
    Parche(
        "web-app/src/services/models/default.ts",
        """  async fetchModelCatalog(): Promise<ModelCatalog> {
    try {""",
        """  async fetchModelCatalog(): Promise<ModelCatalog> {
    // Valkiria: sin URL configurada no hay catálogo remoto (RN-01.3).
    if (!MODEL_CATALOG_URL) return [] as unknown as ModelCatalog
    try {""",
        "catálogo remoto opcional",
    ),
    Parche(
        "web-app/src/services/models/default.ts",
        """  async fetchLatestJanModel(): Promise<CatalogModel | null> {
    try {""",
        """  async fetchLatestJanModel(): Promise<CatalogModel | null> {
    // Valkiria: sin URL configurada no se consulta el modelo recomendado de Jan (RN-01.3).
    if (!LATEST_JAN_MODEL_URL) return null
    try {""",
        "modelo recomendado remoto opcional",
    ),
    Parche(
        "web-app/src/hooks/useReleaseNotes.ts",
        """  fetchLatestRelease: async (includeBeta: boolean) => {
    set({ loading: true, error: null })""",
        """  fetchLatestRelease: async (includeBeta: boolean) => {
    // Valkiria: sin updater de Jan no se consultan sus releases en GitHub al arrancar (RN-01.3).
    if (AUTO_UPDATER_DISABLED) return
    set({ loading: true, error: null })""",
        "notas de versión de Jan solo con updater activo",
    ),
    Parche(
        "src-tauri/Info.plist",
        "<key>CFBundleIdentifier</key>\n  <string>jan.ai.app</string>",
        f"<key>CFBundleIdentifier</key>\n  <string>{IDENTIFICADOR}</string>",
        "identificador del bundle de macOS (Info.plist propio de Jan)",
    ),
    Parche(
        "src-tauri/Info.plist",
        "<key>CFBundleURLName</key>\n      <string>jan.ai.app</string>",
        f"<key>CFBundleURLName</key>\n      <string>{IDENTIFICADOR}</string>",
        "nombre del esquema de URL de macOS",
    ),
    Parche(
        "extensions/llamacpp-extension/src/index.ts",
        """  private async bootstrapDefaultEmbedder(): Promise<void> {
    try {
      if (await getBackendSetting(EMBEDDER_BOOTSTRAP_KEY)) return""",
        """  private async bootstrapDefaultEmbedder(): Promise<void> {
    try {
      // Valkiria: Jan descargaba el embedder de Hugging Face (vía apps.jan.ai) en el primer
      // arranque sin consentimiento, aunque su comentario dice lo contrario (RN-01.3).
      if (!(await this.hasSetupConsent())) return
      if (await getBackendSetting(EMBEDDER_BOOTSTRAP_KEY)) return""",
        "descarga del embedder solo con consentimiento",
    ),
]

_JAN = re.compile(r"\bJan\b")


def dentro_de(raiz: Path, ruta: Path) -> Path:
    """Devuelve ``ruta`` normalizada si está dentro de ``raiz``; si no, falla (path traversal)."""
    base = os.path.realpath(raiz)
    destino = os.path.realpath(ruta)
    if os.path.commonpath([base, destino]) != base:
        raise ParcheError(f"ruta fuera de {base}: {destino}")
    return Path(destino)


def _editar_json(app: Path, ruta: Path, cambio: Callable[[dict[str, object]], None]) -> bool:
    ruta = dentro_de(app, ruta)
    texto = ruta.read_text(encoding="utf-8")
    datos = json.loads(texto)
    cambio(datos)
    nuevo = json.dumps(datos, indent=2, ensure_ascii=False) + "\n"
    if nuevo == texto:
        return False
    ruta.write_text(nuevo, encoding="utf-8")
    return True


def _tauri(datos: dict[str, object]) -> None:
    datos |= {
        "productName": NOMBRE,
        "mainBinaryName": BINARIO,
        "version": VERSION,
        "identifier": IDENTIFICADOR,
    }
    bundle = datos["bundle"]
    if not isinstance(bundle, dict):
        raise ParcheError(f"tauri.conf.json: se esperaba un objeto en {bundle!r:.40}")
    bundle["publisher"] = FABRICANTE
    bundle["copyright"] = f"© {FABRICANTE}. Basado en Jan (Apache 2.0)."
    bundle["createUpdaterArtifacts"] = False
    plugins = datos["plugins"]
    if not isinstance(plugins, dict):
        raise ParcheError(f"tauri.conf.json: se esperaba un objeto en {plugins!r:.40}")
    # Sin endpoints ni clave de Jan: nunca descarga una actualización de Jan (F10 trae el propio).
    plugins["updater"] = {"pubkey": "", "endpoints": [], "windows": {"installMode": "passive"}}
    app = datos["app"]
    if not isinstance(app, dict):
        raise ParcheError(f"tauri.conf.json: se esperaba un objeto en {app!r:.40}")
    csp = app["security"]["csp"]  # type: ignore[index]
    # Sin analítica de terceros (PostHog) en la política de contenido.
    csp["script-src"] = re.sub(r"\s*https://\S*posthog\.com", "", csp["script-src"])


ARGS_WEBVIEW2 = " ".join(
    [
        "--disable-features=msWebOOUI,msPdfOOUI,msSmartScreenProtection",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-domain-reliability",
        "--disable-client-side-phishing-detection",
        "--no-pings",
    ]
)


def _titulo_ventana(datos: dict[str, object]) -> None:
    for ventana in datos.get("app", {}).get("windows", []):  # type: ignore[union-attr]
        if ventana.get("title") == "Jan":
            ventana["title"] = NOMBRE


def _ventana_windows(datos: dict[str, object]) -> None:
    """Título y WebView2 sin tráfico de fondo hacia Microsoft (RN-01.3)."""
    _titulo_ventana(datos)
    for ventana in datos.get("app", {}).get("windows", []):  # type: ignore[union-attr]
        ventana["additionalBrowserArgs"] = ARGS_WEBVIEW2


def _version_web(datos: dict[str, object]) -> None:
    datos["version"] = VERSION


def _locales(texto: str, ruta: Path) -> str:
    datos = json.loads(texto)

    def reemplazar(valor: object) -> object:
        if isinstance(valor, str):
            return _JAN.sub(NOMBRE_CORTO, valor)
        if isinstance(valor, dict):
            return {k: reemplazar(v) for k, v in valor.items()}
        if isinstance(valor, list):
            return [reemplazar(v) for v in valor]
        return valor

    datos = reemplazar(datos)
    if ruta.name == "settings.json" and ruta.parent.name in {"en", "es"}:
        general = datos.setdefault("general", {})
        es = ruta.parent.name == "es"
        general["aboutTitle"] = f"{NOMBRE} · {FABRICANTE}"
        general["aboutAttribution"] = ATRIBUCION_ES if es else ATRIBUCION_EN
    return json.dumps(datos, indent=2, ensure_ascii=False) + "\n"


def _proveedores(texto: str) -> str:
    """Todos los proveedores predefinidos de Jan son remotos: quedan inactivos (RN-01.3)."""
    inicio = texto.index("export const predefinedProviders")
    cabeza, cuerpo = texto[:inicio], texto[inicio:]
    return cabeza + cuerpo.replace("active: true,", "active: false,")


def _cargo(texto: str) -> str:
    texto = re.sub(
        r'^description = ".*"$',
        f'description = "{NOMBRE}: asistente de IA local de {FABRICANTE}."',
        texto,
        count=1,
        flags=re.M,
    )
    return re.sub(r"^authors = \[.*\]$", f'authors = ["{FABRICANTE}"]', texto, count=1, flags=re.M)


def aplicar(app: Path = APP, solo_verificar: bool = False) -> list[str]:
    """Aplica (o verifica) todos los cambios. Devuelve la lista de archivos que cambiarían."""
    cambios: list[str] = []

    def registrar(rel: str, original: str, nuevo: str) -> None:
        if nuevo != original:
            cambios.append(rel)
            if not solo_verificar:
                dentro_de(app, app / rel).write_text(nuevo, encoding="utf-8")

    for p in PARCHES:
        ruta = app / p.ruta
        texto = ruta.read_text(encoding="utf-8")
        nuevo, cambio = p.aplicar(texto)
        if cambio:
            # Si dos parches tocan el mismo archivo, el segundo parte del texto ya parchado.
            registrar(p.ruta, texto, nuevo)

    json_edits = [
        ("src-tauri/tauri.conf.json", _tauri),
        ("src-tauri/tauri.macos.conf.json", _titulo_ventana),
        ("src-tauri/tauri.windows.conf.json", _ventana_windows),
        ("src-tauri/tauri.linux.conf.json", _titulo_ventana),
        ("web-app/package.json", _version_web),
    ]
    for rel, cambio in json_edits:
        ruta = app / rel
        if solo_verificar:
            texto = ruta.read_text(encoding="utf-8")
            datos = json.loads(texto)
            cambio(datos)
            registrar(rel, texto, json.dumps(datos, indent=2, ensure_ascii=False) + "\n")
        elif _editar_json(app, ruta, cambio):
            cambios.append(rel)

    for ruta in sorted((app / "web-app/src/locales").glob("*/*.json")):
        texto = ruta.read_text(encoding="utf-8")
        registrar(ruta.relative_to(app).as_posix(), texto, _locales(texto, ruta))

    for rel, funcion in [
        ("web-app/src/constants/providers.ts", _proveedores),
        ("src-tauri/Cargo.toml", _cargo),
    ]:
        texto = (app / rel).read_text(encoding="utf-8")
        registrar(rel, texto, funcion(texto))

    activos = [
        ("logo.png", "web-app/public/images/jan-logo.png"),  # logo y favicons de la interfaz
        (
            "icono-1024.png",
            "src-tauri/icons/icon.png",
        ),  # fuente de `yarn build:icon` (íconos del SO)
        ("icono-1024.png", "src-tauri/app-icon.png"),
    ]
    for origen, destino in activos:
        a, b = MARCA / origen, app / destino
        if a.exists() and a.read_bytes() != b.read_bytes():
            cambios.append(destino)
            if not solo_verificar:
                shutil.copyfile(a, dentro_de(app, b))
    return cambios


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--check", action="store_true", help="No escribe; falla si falta algún cambio")
    a = ap.parse_args(argv)
    try:
        cambios = aplicar(solo_verificar=a.check)
    except ParcheError as err:
        print(f"::error title=Marca Valkiria::{err}")
        return 2
    if a.check and cambios:
        for c in cambios:
            print(f"::error title=Marca Valkiria::falta aplicar la marca en {c}")
        return 1
    print(f"{len(cambios)} archivos {'por cambiar' if a.check else 'actualizados'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

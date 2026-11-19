#!/usr/bin/env bash
# Motor de inferencia real de Valkiria (F1, incremento 1.1): llama.cpp compilado en el build.
#
# Uso, desde la raíz del repositorio y después de `make -C apps/desktop build-engine`:
#   tools/desktop/motor.sh verificar <variante>   # el worker empaquetado es real, arranca y lista dispositivos
#   tools/desktop/motor.sh humo <variante>        # carga un GGUF del catálogo y genera texto
#
# <variante> es la de JAN_ENGINE_VARIANT: metal en macOS, cuda13-vulkan en Windows (incluye las
# variantes de CPU, AVX2 entre ellas). Los informes quedan en reports/motor/.
#
# La prueba de humo usa el modelo `qwen3-0.6b-q8_0` de llmops/models/catalog.yaml, descargado y
# verificado por SHA-256 con `llmops modelo` (RN-05.2), y corre las pruebas del propio motor
# (tests/engine_smoke.rs del plugin): carga del modelo, chat con plantilla y tokens generados, y
# respuesta en streaming. Todo en CPU (-ngl 0), así que no necesita GPU en el runner.
set -euo pipefail

ACCION="${1:?uso: motor.sh verificar|humo <variante>}"
VARIANTE="${2:?falta la variante (metal, cuda13-vulkan, ...)}"
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
APP="$RAIZ/apps/desktop"
BIN="$APP/src-tauri/resources/bin"
PLUGIN="$APP/src-tauri/plugins/tauri-plugin-llamacpp"
SALIDA="$RAIZ/reports/motor"
MODELO="${VALKIRIA_MODELO_HUMO:-qwen3-0.6b-q8_0}"
mkdir -p "$SALIDA"

case "$(uname -s)" in
  MINGW* | MSYS* | CYGWIN*) SO=windows; EXE=".exe"; LIB="ggml*.dll" ;;
  Darwin) SO=macos; EXE=""; LIB="libggml*" ;;
  *) SO=linux; EXE=""; LIB="libggml*" ;;
esac
WORKER="$BIN/jan-llama-worker$EXE"

# Igual que ENGINE_FEATURE_* del Makefile de apps/desktop, con el respaldo de Vulkan.
features() {
  local t f=()
  for t in ${VARIANTE//-/ }; do
    case "$t" in
      cpu) f+=(engine) ;;
      metal) f+=(engine-metal) ;;
      vulkan) f+=(engine-vulkan) ;;
      cuda12 | cuda13) f+=(engine-cuda engine-vulkan) ;;
      *) echo "variante desconocida: $t" >&2; exit 2 ;;
    esac
  done
  printf '%s\n' "${f[@]}" | sort -u | paste -sd, -
}

sha() { if command -v sha256sum >/dev/null; then sha256sum "$1"; else shasum -a 256 "$1"; fi | cut -d' ' -f1; }

verificar() {
  local tam libs version dispositivos
  [[ -f "$WORKER" ]] || { echo "::error title=Motor::no existe $WORKER"; exit 1; }
  tam=$(wc -c < "$WORKER" | tr -d ' ')
  # Un stub de stub-tauri-resources.mjs es un archivo vacío; el worker real pesa decenas de MB.
  (( tam > 1000000 )) || { echo "::error title=Motor::$WORKER mide $tam bytes: es un stub, no el motor"; exit 1; }
  libs=$(find "$BIN" -maxdepth 1 -name "$LIB" -exec basename {} \; | sort | tr '\n' ' ')
  [[ -n "$libs" ]] || { echo "::error title=Motor::faltan las bibliotecas ggml junto al worker"; exit 1; }
  for l in $libs; do
    [[ -s "$BIN/$l" ]] || { echo "::error title=Motor::$l está vacía (stub)"; exit 1; }
  done
  version=$("$WORKER" --version 2>&1 | head -5)
  # stdout trae la lista en JSON; el registro de ggml (compilación de Metal, backends) va a stderr.
  dispositivos=$("$WORKER" --list-devices 2>/dev/null | tail -1 || true)
  echo "$version"
  echo "$dispositivos"
  python3 - "$SALIDA/motor-$SO.json" <<EOF
import json, sys
json.dump({
    "so": "$SO",
    "variante": "$VARIANTE",
    "features": "$(features)",
    "worker_bytes": $tam,
    "worker_sha256": "$(sha "$WORKER")",
    "bibliotecas": "$libs".split(),
    "version": """$version""".strip().splitlines(),
    "dispositivos": json.loads(r"""$dispositivos""" or "[]"),
}, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
EOF
  echo "Motor real verificado: jan-llama-worker$EXE ($tam bytes) y $(wc -w <<< "$libs" | tr -d ' ') bibliotecas ggml"
}

humo() {
  local gguf log
  gguf=$(cd "$RAIZ/llmops" && uv run --frozen --no-dev llmops modelo "$MODELO")
  echo "Modelo verificado: $gguf"
  log="$SALIDA/humo-$SO.log"
  # Mismos features que el worker: el árbol de cmake de build-engine se reutiliza.
  (cd "$PLUGIN" && JAN_TEST_GGUF="$gguf" cargo test --release --features "$(features)" \
      --test engine_smoke -- --test-threads=1 2>&1) | tee "$log"
  grep -q "test result: ok" "$log" || { echo "::error title=Humo del motor::las pruebas no pasaron"; exit 1; }
  # Sin modelo, las pruebas de engine_smoke se saltan en silencio: que ninguna haya dicho "skipping".
  if grep -q "skipping: set JAN_TEST_GGUF" "$log"; then
    echo "::error title=Humo del motor::las pruebas se saltaron: no recibieron el modelo"; exit 1
  fi
  echo "Humo del motor: $MODELO cargó y generó texto"
}

case "$ACCION" in
  verificar) verificar ;;
  humo) humo ;;
  *) echo "acción desconocida: $ACCION" >&2; exit 2 ;;
esac

#!/usr/bin/env bash
# Prueba de humo de macOS en el hardware mínimo soportado (HU-01: CA-01.1 y CA-01.3; decisión R-12).
#
# Valkiria para macOS exige Apple Silicon M4 o posterior con macOS 27.2+. Los runners de GitHub no
# cumplen ese mínimo, así que CI (desktop.yml) solo compila y verifica el .app; esta prueba corre en
# un Mac M4 del equipo, descarga el artefacto de CI y deja la evidencia en el repositorio.
#
# Uso: tools/desktop/humo-mac-local.sh [--pr <n> | --run <id> | --sha <sha>] [--segundos 300] [--fase F1]
#   Sin selector toma el último run exitoso de desktop.yml en main.
#   Con --fase, la evidencia va a evidencias/<fase>/L4-desarrollo/escritorio/humo-macos-m4/;
#   sin ella, a reports/smoke-macos-m4/<sha>/ (ignorado por git).
# Requiere: gh autenticado y python3. No usa sudo ni modifica /Applications.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

SEGUNDOS=300; FASE=""; SELECTOR=(--branch main); RUN=""
while [[ $# -gt 0 ]]; do
  case $1 in
    --pr) SELECTOR=(--commit "$(gh pr view "$2" --json headRefOid --jq .headRefOid)"); shift 2 ;;
    --sha) SELECTOR=(--commit "$2"); shift 2 ;;
    --run) RUN=$2; shift 2 ;;
    --segundos) SEGUNDOS=$2; shift 2 ;;
    --fase) FASE=$2; shift 2 ;;
    -h|--help) sed -n '2,13p' "$0"; exit 0 ;;
    *) echo "Argumento desconocido: $1" >&2; exit 2 ;;
  esac
done
[[ $SEGUNDOS =~ ^[0-9]+$ ]] || { echo "--segundos debe ser un entero" >&2; exit 2; }
[[ -z $FASE || $FASE =~ ^F[0-9]+$ ]] || { echo "--fase debe ser F0, F1, ..." >&2; exit 2; }

# ---------- 1. Hardware y sistema mínimos ----------
[[ $(uname -s) == Darwin && $(uname -m) == arm64 ]] || { echo "Se requiere un Mac con Apple Silicon" >&2; exit 1; }
CHIP=$(sysctl -n machdep.cpu.brand_string)
MODELO=$(sysctl -n hw.model)
MACOS=$(sw_vers -productVersion)
BUILD=$(sw_vers -buildVersion)
python3 -I - "$CHIP" "$MACOS" <<'PY' || exit 1
import re, sys
chip, macos = sys.argv[1:]
m = re.match(r"Apple M(\d+)", chip)
if not m or int(m.group(1)) < 4:
    sys.exit(f"Chip no soportado: {chip!r}. El mínimo es Apple M4.")
if tuple(int(x) for x in macos.split(".")[:2]) < (27, 2):
    sys.exit(f"macOS {macos} no soportado. El mínimo es macOS 27.2.")
print(f"Equipo soportado: {chip} · macOS {macos}")
PY

# ---------- 2. Artefacto de CI ----------
if [[ -z $RUN ]]; then
  RUN=$(gh run list --workflow desktop.yml "${SELECTOR[@]}" --status success --limit 1 \
    --json databaseId --jq '.[0].databaseId // empty')
  [[ -n $RUN ]] || { echo "No hay un run exitoso de desktop.yml para ${SELECTOR[*]}" >&2; exit 1; }
fi
[[ $RUN =~ ^[0-9]+$ ]] || { echo "--run debe ser un id numérico" >&2; exit 2; }
SHA=$(gh run view "$RUN" --json headSha --jq .headSha)
URL=$(gh run view "$RUN" --json url --jq .url)
echo "Run $RUN ($URL) · commit $SHA"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
gh run download "$RUN" --name valkiria-macos-arm64 --dir "$TMP/artefacto"
ZIP=$(find "$TMP/artefacto" -name 'Valkiria-Productividad-macos.zip' -print -quit)
[[ -n $ZIP ]] || { echo "El artefacto no trae Valkiria-Productividad-macos.zip" >&2; exit 1; }
ZIP_SHA=$(shasum -a 256 "$ZIP" | awk '{print $1}')
mkdir -p "$TMP/app"
ditto -x -k "$ZIP" "$TMP/app"
APP="$TMP/app/Valkiria Productividad.app"
xattr -dr com.apple.quarantine "$APP" 2>/dev/null || true
ARCHS=$(lipo -archs "$APP/Contents/MacOS/Valkiria-Productividad")

# ---------- 3. Prueba de humo y evidencia ----------
if [[ -n $FASE ]]; then
  SALIDA="evidencias/$FASE/L4-desarrollo/escritorio/humo-macos-m4"
else
  SALIDA="reports/smoke-macos-m4/${SHA:0:12}"
fi
mkdir -p "$SALIDA"
python3 -I - "$SALIDA/entorno.json" "$CHIP" "$MODELO" "$MACOS" "$BUILD" "$RUN" "$URL" "$SHA" \
  "$ZIP_SHA" "$ARCHS" "$SEGUNDOS" <<'PY'
import datetime, json, sys
out, chip, modelo, macos, build, run, url, sha, zip_sha, archs, segundos = sys.argv[1:]
doc = {
    "fecha": datetime.datetime.now(datetime.UTC).isoformat(timespec="seconds"),
    "equipo": {"chip": chip, "modelo": modelo, "macos": macos, "build": build},
    "minimo": {"chip": "Apple M4", "macos": "27.2"},
    "artefacto": {"run_id": run, "url": url, "commit": sha, "zip_sha256": zip_sha, "arquitecturas": archs},
    "segundos": int(segundos),
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
    f.write("\n")
PY
echo "Abriendo la app $SEGUNDOS s para verificar identidad, arranque y 0 conexiones salientes..."
codigo=0
python3 tools/desktop/smoke.py --app "$APP" --segundos "$SEGUNDOS" --salida "$SALIDA" || codigo=$?
echo "Evidencia en $SALIDA"
exit $codigo

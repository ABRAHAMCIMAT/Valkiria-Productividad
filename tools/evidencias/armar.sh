#!/usr/bin/env bash
# Arma el paquete de evidencias de una fase (docs/05 §5) para un commit.
# Uso: tools/evidencias/armar.sh F0 [<sha>] [<destino>]
#
# Requiere: gh autenticado (lee artefactos de Actions), uv y Python 3.15.
# 1. Descarga los artefactos de los runs exitosos de CI, Sonar y Desktop del commit.
# 2. Ejecuta las pruebas con JUnit y la evidencia de MLflow (servidor local efímero).
# 3. Genera trazabilidad.csv y manifest.sha256, y falla si falta una evidencia obligatoria.
set -euo pipefail
FASE="${1:?Indica la fase, por ejemplo F0}"
cd "$(git rev-parse --show-toplevel)"
SHA="${2:-$(git rev-parse HEAD)}"
PKG="$(python3 -c 'import os,sys; print(os.path.abspath(sys.argv[1]))' "${3:-evidencias/$FASE}")"
TMP="$(mktemp -d)"
limpiar() {
  # El servidor de MLflow lanza workers propios: se detienen todos los que escuchan en su puerto.
  pkill -f "mlflow.*--port 5077" 2>/dev/null || true
  rm -rf "$TMP"
}
trap limpiar EXIT
export VIRTUAL_ENV=""

echo "== Paquete $FASE para $SHA en $PKG"
mkdir -p "$PKG"/{L1-alcance,L4-desarrollo,L5-evaluacion,L6-seguridad,L9-mejora}

# ---------- 1. Artefactos de los workflows del commit ----------
: > "$TMP/jobs.ndjson"
for wf in ci.yml sonar.yml desktop.yml; do
  id=$(gh run list --workflow "$wf" --commit "$SHA" --status success --limit 1 --json databaseId --jq '.[0].databaseId // empty')
  if [[ -z $id ]]; then echo "::warning::Sin run exitoso de $wf para $SHA"; continue; fi
  echo "-- $wf: run $id"
  gh run view "$id" --json jobs --jq '.jobs[] | {name, conclusion} | @json' >> "$TMP/jobs.ndjson"
  gh run download "$id" -D "$TMP/$wf" || true
  echo "$wf,$id,https://github.com/$(gh repo view --json nameWithOwner --jq .nameWithOwner)/actions/runs/$id" >> "$TMP/runs.csv"
done
python3 -c 'import json,sys; print(json.dumps([json.loads(l) for l in open(sys.argv[1]) if l.strip()], indent=2))' \
  "$TMP/jobs.ndjson" > "$PKG/L4-desarrollo/jobs.json"
{ echo "workflow,run_id,url"; cat "$TMP/runs.csv" 2>/dev/null || true; } > "$PKG/L4-desarrollo/runs.csv"

copiar() { # copiar <patrón dentro de TMP> <destino>
  local n=0
  while IFS= read -r -d '' f; do cp "$f" "$2/"; n=$((n + 1)); done < <(find "$TMP" -path "$TMP/$1" -type f -print0)
  echo "   $1 -> $(basename "$2") ($n)"
}
copiar 'ci.yml/seguridad-*/*' "$PKG/L6-seguridad"
copiar 'ci.yml/seguridad-*/.trivyignore' "$PKG/L6-seguridad"
copiar 'ci.yml/pruebas-*/*/*.xml' "$PKG/L4-desarrollo"
copiar 'sonar.yml/sonar-metrics-*/sonar-metrics.json' "$PKG/L4-desarrollo"
cp "$PKG/L4-desarrollo/sonar-metrics.json" "$PKG/L6-seguridad/" 2>/dev/null || true
mkdir -p "$PKG/L4-desarrollo/escritorio"
copiar 'desktop.yml/humo-*/*' "$PKG/L4-desarrollo/escritorio"
copiar 'desktop.yml/valkiria-windows-x64/reports/smoke/*' "$PKG/L4-desarrollo/escritorio"
# macOS (R-12): la prueba de humo corre en un Mac M4 con tools/desktop/humo-mac-local.sh --fase.
M4="evidencias/$FASE/L4-desarrollo/escritorio/humo-macos-m4"
if [[ -d $M4 && ! $M4 -ef "$PKG/L4-desarrollo/escritorio/humo-macos-m4" ]]; then
  cp -R "$M4" "$PKG/L4-desarrollo/escritorio/"; echo "   $M4 -> escritorio"
fi

# ---------- 2. Pruebas (JUnit) y evidencia de MLflow ----------
mkdir -p "$TMP/junit"
# uv construye aquí solo los paquetes propios del repositorio, desde uv.lock con --frozen y hashes;
# las dependencias de terceros se instalan como wheels. Por eso se omite --no-build.
(cd core && uv sync -q --frozen --all-groups)  # NOSONAR
(cd core && uv run --no-sync pytest -q --junitxml="$TMP/junit/core.xml")  # NOSONAR
(cd core && uv run --no-sync pytest ../tools/tests -q -o addopts="" -p no:cacheprovider --junitxml="$TMP/junit/tools.xml")  # NOSONAR
(cd llmops && uv sync -q --frozen --all-groups)  # NOSONAR
(cd llmops && uv run --no-sync pytest -q --junitxml="$TMP/junit/llmops.xml")  # NOSONAR
cp "$TMP"/junit/*.xml "$PKG/L4-desarrollo/"

export VALKIRIA_MLFLOW_HOME="$TMP/mlflow" MLFLOW_TRACKING_URI="http://127.0.0.1:5077"
(cd llmops && uv run --no-sync llmops serve --port 5077 > "$TMP/mlflow.log" 2>&1) & MLFLOW_PID=$!  # NOSONAR
for _ in $(seq 1 60); do curl -fsS "$MLFLOW_TRACKING_URI/health" >/dev/null 2>&1 && break; sleep 2; done
(cd llmops && GITHUB_SHA="$SHA" uv run --no-sync llmops bootstrap >/dev/null)  # NOSONAR
(cd llmops && GITHUB_SHA="$SHA" uv run --no-sync llmops demo-eval --phase "$FASE" --hu HU-03)  # NOSONAR
(cd llmops && uv run --no-sync llmops gate --phase "$FASE" | tee "$PKG/L5-evaluacion/gate.txt")  # NOSONAR
(cd llmops && uv run --no-sync llmops export --phase "$FASE" --out "$TMP/export")  # NOSONAR
rm -rf "$PKG/L5-evaluacion/mlflow"; cp -R "$TMP/export/mlflow" "$PKG/L5-evaluacion/mlflow"

# ---------- 3. Alcance, trazabilidad y manifiesto ----------
cp docs/07-historias-usuario.md docs/06-plan-desarrollo-incremental.md "$PKG/L1-alcance/"
cp security/excepciones.toml "$PKG/L6-seguridad/"
for f in cierre.md criterios.toml; do
  [[ -f "evidencias/$FASE/$f" && ! "evidencias/$FASE/$f" -ef "$PKG/$f" ]] && cp "evidencias/$FASE/$f" "$PKG/"
done
# Corre en el entorno de Core, que trae defusedxml para leer JUnit sin riesgo de XXE.
(cd core && uv run --no-sync python ../tools/evidencias/trazabilidad.py \
  --criterios "../evidencias/$FASE/criterios.toml" --junit "$TMP/junit/*.xml" \
  --jobs "$PKG/L4-desarrollo/jobs.json" --commit "$SHA" --salida "$PKG/trazabilidad.csv") || TRAZA_FALLO=1  # NOSONAR

OBLIGATORIOS=(
  L4-desarrollo/sonar-metrics.json L4-desarrollo/jobs.json L4-desarrollo/core.xml L4-desarrollo/llmops.xml
  L5-evaluacion/gate.txt L6-seguridad/sbom.cdx.json L6-seguridad/gitleaks.json L6-seguridad/semgrep.json
  L6-seguridad/bandit.json L6-seguridad/trivy.json L6-seguridad/trivy-desktop.json trazabilidad.csv cierre.md
)
faltan=0
for f in "${OBLIGATORIOS[@]}"; do
  [[ -s "$PKG/$f" ]] || { echo "::error title=Evidencia $FASE::falta $f"; faltan=1; }
done
python3 - "$PKG/L4-desarrollo/sonar-metrics.json" <<'PY' || faltan=1
import json, sys
try:
    gate = json.load(open(sys.argv[1]))["quality_gate"]["status"]
except (OSError, KeyError, ValueError):
    sys.exit(0)  # la ausencia ya se reporta arriba
print(f"Quality Gate de Sonar: {gate}")
sys.exit(0 if gate == "OK" else 1)
PY

python3 -I tools/evidencias/manifiesto.py generar "$PKG"
[[ $faltan -eq 0 && -z ${TRAZA_FALLO:-} ]] || { echo "Paquete $FASE INCOMPLETO"; exit 1; }
echo "Paquete $FASE completo en $PKG"

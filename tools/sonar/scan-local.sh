#!/usr/bin/env bash
# Analiza el árbol de trabajo actual contra el SonarQube local (macOS / Linux).
# Requisitos: SonarQube local en marcha (docker-compose.yml) y un token de análisis en
#   SONAR_LOCAL_TOKEN, o en el llavero de macOS:
#   security add-generic-password -a "$USER" -s valkiria-sonar-local -w <token>
# Nota: la edición Community solo guarda la rama main; este análisis es una "foto" del árbol actual.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
KEY="${SONAR_LOCAL_PROJECT_KEY:-valkiria-productividad}"
SCANNER_IMAGE="sonarsource/sonar-scanner-cli:12.2"

if [[ -z "${SONAR_LOCAL_TOKEN:-}" ]] && command -v security >/dev/null; then
  SONAR_LOCAL_TOKEN="$(security find-generic-password -s valkiria-sonar-local -w 2>/dev/null || true)"
fi
: "${SONAR_LOCAL_TOKEN:?Define SONAR_LOCAL_TOKEN o guárdalo en el llavero (ver encabezado)}"

eval "$(bash "$ROOT/tools/sonar/sources.sh")"
if [[ $has_code != true ]]; then echo "Todavía no hay código propio que analizar (core/, valkiria-extension/)."; exit 0; fi

args=(-Dsonar.projectKey="$KEY" -Dsonar.host.url=http://sonarqube:9000 -Dsonar.sources="$sources")
[[ -n $tests ]] && args+=(-Dsonar.tests="$tests")

docker run --rm --network valkiria-sonar_default \
  -e SONAR_TOKEN="$SONAR_LOCAL_TOKEN" \
  -v "$ROOT:/usr/src" -w /usr/src \
  "$SCANNER_IMAGE" "${args[@]}"
echo "Resultados: http://127.0.0.1:9000/dashboard?id=$KEY"

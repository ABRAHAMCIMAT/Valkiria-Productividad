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

# Mismos reportes que genera CI (sonar.yml): sin ellos la cobertura de código nuevo sale en 0 %.
# Las pruebas fallidas no detienen el análisis: el Quality Gate es quien decide.
export VIRTUAL_ENV=""
for mod in core llmops; do
  [[ -f "$ROOT/$mod/pyproject.toml" ]] || continue
  (
    cd "$ROOT/$mod" && mkdir -p reports && uv sync -q --frozen --all-groups  # NOSONAR
    uv run --no-sync pytest -q --cov=src --cov-report=xml:reports/coverage.xml --junitxml=reports/junit.xml || true  # NOSONAR
    if [[ $mod == core ]]; then
      uv run --no-sync pytest ../tools/tests -q -o addopts="" -p no:cacheprovider --cov=../tools --cov-branch \
        --cov-report=xml:reports/coverage-tools.xml || true  # NOSONAR
      uv run --no-sync bandit -q -r src ../tools -x ../tools/tests -f json -o reports/bandit.json || true  # NOSONAR
    else
      uv run --no-sync bandit -q -r src -f json -o reports/bandit.json || true  # NOSONAR
    fi
    uv run --no-sync ruff check --output-format=json --output-file=reports/ruff.json . || true  # NOSONAR
    uv run --no-sync mypy src > reports/mypy.txt || true  # NOSONAR
  )
done
# coverage.py escribe rutas absolutas del equipo; el escáner corre en un contenedor con el repo en /usr/src.
for f in "$ROOT"/core/reports/coverage*.xml "$ROOT"/llmops/reports/coverage.xml; do
  [[ -f $f ]] && sed -i.bak "s#$ROOT#/usr/src#g" "$f" && rm -f "$f.bak"
done

args=(-Dsonar.projectKey="$KEY" -Dsonar.host.url=http://sonarqube:9000 -Dsonar.sources="$sources")
[[ -n $tests ]] && args+=(-Dsonar.tests="$tests")

docker run --rm --network valkiria-sonar_default \
  -e SONAR_TOKEN="$SONAR_LOCAL_TOKEN" \
  -v "$ROOT:/usr/src" -w /usr/src \
  "$SCANNER_IMAGE" "${args[@]}"
echo "Resultados: http://127.0.0.1:9000/dashboard?id=$KEY"

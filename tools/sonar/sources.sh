#!/usr/bin/env bash
# Calcula sonar.sources y sonar.tests a partir de los módulos de Valkiria que existan.
# Salida (formato GITHUB_OUTPUT):  sources=a,b  tests=c,d  has_code=true|false
set -euo pipefail
cd "$(dirname "$0")/../.."

SOURCE_CANDIDATES=(
  core/src
  llmops/src
  apps/desktop/extensions/valkiria-extension/src
  llmops/evals
  llmops/redteam
  tools
)
TEST_CANDIDATES=(
  core/tests
  llmops/tests
  tools/tests
  apps/desktop/extensions/valkiria-extension/tests
)

join() { local IFS=,; echo "$*"; }
has_code_files() { find "$1" -type f \( -name '*.py' -o -name '*.ts' -o -name '*.tsx' -o -name '*.js' -o -name '*.sh' \) -print -quit | grep -q .; }

sources=(); tests=()
for d in "${SOURCE_CANDIDATES[@]}"; do [[ -d $d ]] && has_code_files "$d" && sources+=("$d"); done
for d in "${TEST_CANDIDATES[@]}";   do [[ -d $d ]] && has_code_files "$d" && tests+=("$d");   done

# 'tools' contiene solo scripts de soporte; si es lo único que hay, el proyecto aún no tiene código propio.
real=0; for s in "${sources[@]:-}"; do [[ -n $s && $s != tools ]] && real=1; done

echo "sources=$(join "${sources[@]:-}")"
echo "tests=$(join "${tests[@]:-}")"
echo "has_code=$([[ $real == 1 ]] && echo true || echo false)"

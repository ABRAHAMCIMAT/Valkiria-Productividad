#!/usr/bin/env bash
# Configura una sola vez el SonarQube local: crea el proyecto y el Quality Gate "Valkiria".
# Uso: SONAR_ADMIN_TOKEN=... tools/sonar/bootstrap-local.sh
set -euo pipefail
HOST="${SONAR_LOCAL_URL:-http://127.0.0.1:9000}"
KEY="${SONAR_LOCAL_PROJECT_KEY:-valkiria-productividad}"
GATE="Valkiria"
: "${SONAR_ADMIN_TOKEN:?Genera un token de administrador en $HOST (Mi cuenta > Seguridad)}"
post() { curl -fsS -X POST -H "Authorization: Bearer $SONAR_ADMIN_TOKEN" "$HOST/api/$1" "${@:2}" >/dev/null; }

post projects/create --data-urlencode "project=$KEY" --data-urlencode "name=Valkiria Productividad" --data-urlencode "mainBranch=main" 2>/dev/null || echo "El proyecto ya existe"
post qualitygates/create --data-urlencode "name=$GATE" 2>/dev/null || echo "El gate ya existe"

# Condiciones sobre CÓDIGO NUEVO (ver docs/08-calidad-sonar.md §2). Ratings: 1=A.
# Las versiones recientes crean el gate con condiciones por defecto: si la condición existe se actualiza.
existing=$(curl -fsS -H "Authorization: Bearer $SONAR_ADMIN_TOKEN" "$HOST/api/qualitygates/show?name=$GATE")
cond() {
  local id
  id=$(printf '%s' "$existing" | python3 -I -c 'import sys,json; m=sys.argv[1]; print(next((c["id"] for c in json.load(sys.stdin)["conditions"] if c["metric"]==m), ""))' "$1")
  if [[ -n $id ]]; then
    post qualitygates/update_condition --data-urlencode "id=$id" --data-urlencode "metric=$1" --data-urlencode "op=$2" --data-urlencode "error=$3"
  else
    post qualitygates/create_condition --data-urlencode "gateName=$GATE" --data-urlencode "metric=$1" --data-urlencode "op=$2" --data-urlencode "error=$3"
  fi
}
cond new_violations GT 0
cond new_coverage LT 85
cond new_duplicated_lines_density GT 3
cond new_reliability_rating GT 1
cond new_security_rating GT 1
cond new_maintainability_rating GT 1
cond new_security_hotspots_reviewed LT 100

post qualitygates/select --data-urlencode "gateName=$GATE" --data-urlencode "projectKey=$KEY"
post settings/set --data-urlencode "key=sonar.leak.period.type" --data-urlencode "value=previous_version" --data-urlencode "component=$KEY" || true
echo "Listo: proyecto '$KEY' con Quality Gate '$GATE' en $HOST"

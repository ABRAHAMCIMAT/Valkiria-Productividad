#!/usr/bin/env bash
# Exporta las métricas y el estado del Quality Gate a JSON como evidencia (EV-F<n>-L4 / L6).
# Uso: SONAR_TOKEN=... export-metrics.sh <host_url> <project_key> <salida.json> [branch|pr:<n>]
# Variables opcionales: GIT_SHA, PHASE (por ejemplo, F3).
set -euo pipefail
host="${1:?host_url}"; key="${2:?project_key}"; out="${3:?salida.json}"; ref="${4:-main}"
: "${SONAR_TOKEN:?Define SONAR_TOKEN}"

if [[ $ref == pr:* ]]; then scope="pullRequest=${ref#pr:}"; else scope="branch=$ref"; fi
metrics="ncloc,bugs,vulnerabilities,code_smells,security_hotspots,security_hotspots_reviewed,coverage,duplicated_lines_density,complexity,cognitive_complexity,sqale_index,reliability_rating,security_rating,sqale_rating,security_review_rating,new_coverage,new_violations,new_duplicated_lines_density,tests,test_failures,test_errors"

tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
api() { curl -fsS -H "Authorization: Bearer $SONAR_TOKEN" "$host/api/$1" -o "$2"; }
api "measures/component?component=$key&metricKeys=$metrics&$scope" "$tmp/measures.json"
api "qualitygates/project_status?projectKey=$key&$scope" "$tmp/gate.json"

python3 -I - "$tmp/measures.json" "$tmp/gate.json" "$out" "$key" "$ref" \
  "${GIT_SHA:-$(git rev-parse HEAD 2>/dev/null || echo unknown)}" "${PHASE:-}" <<'PY'
import json, sys, datetime
measures_f, gate_f, out, key, ref, sha, phase = sys.argv[1:8]
m = json.load(open(measures_f))["component"].get("measures", [])
g = json.load(open(gate_f))["projectStatus"]
doc = {
    "project": key, "ref": ref, "git_sha": sha, "phase": phase or None,
    "exported_at": datetime.datetime.now(datetime.UTC).isoformat(),
    "quality_gate": {"status": g["status"], "conditions": g.get("conditions", [])},
    "metrics": {x["metric"]: x.get("value", x.get("period", {}).get("value")) for x in m},
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(doc, f, indent=2, ensure_ascii=False)
print(f"Quality Gate: {g['status']} -> {out}")
PY

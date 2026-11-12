#!/usr/bin/env bash
# Verifica que cada paquete se instala en la versión de Python dada usando wheels para todas sus
# dependencias (ADR-0002, riesgos R-01 y R-11). Imprime una fila CSV por paquete:
#   paquete,plataforma,python,resultado,version,detalle
#
# Uso: tools/deps/solo-wheels.sh <python> <plataforma> <paquete>...
#
# A diferencia de `--only-binary :all:`, primero resuelve el árbol completo y luego exige wheel a cada
# dependencia, salvo a las de SDIST_PERMITIDOS: paquetes sin wheel para la versión nueva cuyo código
# fuente se instala sin compilador porque tienen un respaldo en Python puro. Así una dependencia
# como pyyaml no marca en falso a langgraph o mlflow-skinny, y un paquete nativo que solo trae
# código fuente (pyclipper, tree-sitter) sí hace fallar al que lo usa.
set -uo pipefail
[[ $# -ge 3 ]] || { sed -n '2,13p' "$0"; exit 2; }
PY=$1; PLATAFORMA=$2; shift 2
SDIST_PERMITIDOS=" pyyaml "   # respaldo puro verificado: ver ADR-0002 (revisión 2026-11-12)

python_de() { [[ -x "$1/bin/python" ]] && echo "$1/bin/python" || echo "$1/Scripts/python.exe"; }
fila() { echo "$1,$PLATAFORMA,$PY,$2,$3,$(printf '%s' "${4:-}" | tr ',\n' '; ' | cut -c1-200)"; }
causa() { grep -m1 'hint:' <<<"$1" || grep -m1 -E 'no usable wheels|Wheels are required' <<<"$1" || tail -1 <<<"$1"; }

for paquete in "$@"; do
  venv=$(mktemp -d)/v
  uv venv -q --clear -p "$PY" "$venv"
  py=$(python_de "$venv")
  if ! deps=$(uv pip compile -q --python "$py" --no-header --no-annotate - <<<"$paquete" 2>&1); then
    fila "$paquete" sin-resolver "" "$(causa "$deps")"
    rm -rf "$venv"; continue
  fi
  flags=()
  for dep in $(sed -E 's/[=<>!~;[ ].*//' <<<"$deps" | tr 'A-Z_' 'a-z-'); do
    [[ $SDIST_PERMITIDOS == *" $dep "* ]] || flags+=(--only-binary "$dep")
  done
  if out=$(uv pip install -q --python "$py" ${flags[@]+"${flags[@]}"} "$paquete" 2>&1); then
    nombre=${paquete%%[*}
    version=$(uv pip show --python "$py" "$nombre" 2>/dev/null | awk '/^Version:/{print $2}')
    fila "$paquete" ok "$version"
  else
    fila "$paquete" sin-wheel "" "$(causa "$out")"
  fi
  rm -rf "$(dirname "$venv")"
done

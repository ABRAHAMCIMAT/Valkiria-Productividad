#!/usr/bin/env bash
# Runner propio de GitHub Actions en un Mac Apple Silicon (R-19).
# GitHub no garantiza capacidad en sus runners macOS arm64; este runner atiende el job
# «Core · macos-arm64» de ci.yml cuando la variable del repo MACOS_RUNNER vale "valkiria-m4".
#
# Uso:
#   tools/ci/runner-mac.sh instalar      # descarga (SHA-256 verificado), registra y deja el servicio activo
#   tools/ci/runner-mac.sh estado
#   tools/ci/runner-mac.sh desinstalar   # detiene el servicio y lo quita del repositorio
#
# Seguridad (repo público): ci.yml solo manda a este runner los pushes y los PRs de ramas del
# propio repositorio; los PRs de forks siguen en macos-15 de GitHub. Para volver todo a GitHub:
#   gh variable delete MACOS_RUNNER
set -euo pipefail

REPO="ABRAHAMCIMAT/Valkiria-Productividad"
ETIQUETA="valkiria-m4"
VERSION="2.338.2"
SHA256="25a065af409ffa317ab4d5a3b614dd15fc9c40f2172bc1b35a1b1258e919a388"
DIR="${VALKIRIA_RUNNER_DIR:-$HOME/actions-runner-valkiria}"
PAQUETE="actions-runner-osx-arm64-$VERSION.tar.gz"

[[ "$(uname -s)-$(uname -m)" == "Darwin-arm64" ]] || { echo "Solo para macOS arm64" >&2; exit 1; }

instalar() {
  mkdir -p "$DIR" && cd "$DIR"
  if [[ ! -x ./config.sh ]]; then
    curl --proto '=https' --proto-redir '=https' --tlsv1.2 -fsSLO \
      "https://github.com/actions/runner/releases/download/v$VERSION/$PAQUETE"
    echo "$SHA256  $PAQUETE" | shasum -a 256 -c -
    tar xzf "$PAQUETE" && rm "$PAQUETE"
  fi
  # uv del runner aislado del usuario: setup-uv respeta estas variables si ya existen, así CI no
  # usa ~/.cache/uv ni ~/.local/share/uv/python. La caché persiste en el Mac entre corridas.
  mkdir -p "$DIR/_cache/uv" "$DIR/_cache/uv-python"
  grep -v '^UV_CACHE_DIR=\|^UV_PYTHON_INSTALL_DIR=' .env 2>/dev/null > .env.nuevo || true
  printf 'UV_CACHE_DIR=%s\nUV_PYTHON_INSTALL_DIR=%s\n' "$DIR/_cache/uv" "$DIR/_cache/uv-python" >> .env.nuevo
  mv .env.nuevo .env
  if [[ ! -f .runner ]]; then   # registrado una sola vez; volver a instalar solo reaplica el .env
    token="$(gh api -X POST "repos/$REPO/actions/runners/registration-token" --jq .token)"
    ./config.sh --unattended --replace --url "https://github.com/$REPO" --token "$token" \
      --name "$ETIQUETA" --labels "$ETIQUETA" --work _work
  fi
  ./svc.sh install || true
  ./svc.sh stop || true   # reinicia para que lea el .env
  ./svc.sh start
  ./svc.sh status
}

desinstalar() {
  cd "$DIR"
  ./svc.sh stop || true
  ./svc.sh uninstall || true
  token="$(gh api -X POST "repos/$REPO/actions/runners/remove-token" --jq .token)"
  ./config.sh remove --token "$token"
}

case "${1:-}" in
  instalar) instalar ;;
  desinstalar) desinstalar ;;
  estado) (cd "$DIR" && ./svc.sh status); gh api "repos/$REPO/actions/runners" --jq '.runners[]|[.name,.status,.busy]|@tsv' ;;
  *) sed -n 2,13p "$0"; exit 2 ;;
esac

#!/usr/bin/env bash
# Importa o actualiza el fork de Jan en apps/desktop como git subtree (ADR-0001, riesgo R-03).
# Uso: tools/desktop/sync-jan.sh v0.8.8
#
# Se importa el tag de upstream SIN su sitio web ni recursos de marketing (docs/, GIFs y banners con
# la marca Jan): no forman parte del producto, pesan ~240 MB y ADR-0001 prohíbe usar la marca Jan.
# LICENSE se conserva intacto. El commit filtrado guarda el SHA de upstream para auditar el origen.
# Después de importar, aplica la marca con tools/desktop/rebrand.py.
set -euo pipefail
TAG="${1:?Indica el tag de Jan, por ejemplo v0.8.8}"
UPSTREAM="https://github.com/janhq/jan"
PREFIX="apps/desktop"
EXCLUIR=(docs demo.gif JanBanner.png README.ja.md README.zh.md flappy-hamster.html)

cd "$(git rev-parse --show-toplevel)"
[[ -z $(git status --porcelain) ]] || { echo "El árbol de trabajo tiene cambios; haz commit antes." >&2; exit 1; }

git fetch --depth 1 --no-tags "$UPSTREAM" "refs/tags/$TAG"
upstream_sha=$(git rev-parse FETCH_HEAD)

idx=$(mktemp); trap 'rm -f "$idx"' EXIT
GIT_INDEX_FILE=$idx git read-tree FETCH_HEAD
GIT_INDEX_FILE=$idx git rm -r -q --cached --ignore-unmatch -- "${EXCLUIR[@]}"
arbol=$(GIT_INDEX_FILE=$idx git write-tree)
filtrado=$(git commit-tree "$arbol" -m "Jan $TAG filtrado para Valkiria

Upstream: $UPSTREAM
Commit de upstream: $upstream_sha
Excluido: ${EXCLUIR[*]}")

if [[ -d $PREFIX ]]; then
  git subtree merge --prefix "$PREFIX" --squash "$filtrado" -m "chore(desktop): sincronizar Jan $TAG ($upstream_sha)"
else
  git subtree add --prefix "$PREFIX" --squash "$filtrado" -m "chore(desktop): importar Jan $TAG ($upstream_sha)"
fi
echo "Jan $TAG ($upstream_sha) en $PREFIX"

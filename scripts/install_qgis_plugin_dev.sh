#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_SRC="${REPO_ROOT}/plugins/preditor_terra"
PLUGIN_DST="${HOME}/.local/share/QGIS/QGIS3/profiles/default/python/plugins/preditor_terra"

if [[ ! -d "${PLUGIN_SRC}" ]]; then
  echo "[ERRO] Plugin fonte nao encontrado: ${PLUGIN_SRC}" >&2
  exit 1
fi

mkdir -p "$(dirname "${PLUGIN_DST}")"

if [[ -L "${PLUGIN_DST}" || -d "${PLUGIN_DST}" ]]; then
  rm -rf "${PLUGIN_DST}"
fi

ln -s "${PLUGIN_SRC}" "${PLUGIN_DST}"
echo "[OK] Plugin vinculado em: ${PLUGIN_DST}"

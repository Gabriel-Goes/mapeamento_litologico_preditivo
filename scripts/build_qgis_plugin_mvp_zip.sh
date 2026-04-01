#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PLUGIN_NAME="preditor_territorial_mvp"
PLUGIN_DIR="${REPO_ROOT}/plugins/${PLUGIN_NAME}"
DATA_GPKG="${PLUGIN_DIR}/data/gamba_mvp.gpkg"

if [[ ! -d "${PLUGIN_DIR}" ]]; then
  echo "[ERRO] Pasta do plugin nao encontrada: ${PLUGIN_DIR}" >&2
  exit 1
fi

if [[ ! -f "${DATA_GPKG}" ]]; then
  echo "[INFO] Dados internos nao encontrados. Gerando gamba_mvp.gpkg..."
  "${REPO_ROOT}/scripts/build_gamba_mvp_data.sh"
fi

VERSION="$(sed -n 's/^version=//p' "${PLUGIN_DIR}/metadata.txt" | head -n1 | tr -d '[:space:]')"
if [[ -z "${VERSION}" ]]; then
  VERSION="0.1.0"
fi

DIST_DIR="${REPO_ROOT}/dist"
mkdir -p "${DIST_DIR}"
ZIP_PATH="${DIST_DIR}/${PLUGIN_NAME}_v${VERSION}_gamba.zip"

STAGE_DIR="$(mktemp -d /tmp/pt_qgis_mvp_zip_XXXXXX)"
trap 'rm -rf "${STAGE_DIR}"' EXIT

cp -a "${PLUGIN_DIR}" "${STAGE_DIR}/${PLUGIN_NAME}"
find "${STAGE_DIR}/${PLUGIN_NAME}" -type d -name '__pycache__' -prune -exec rm -rf {} +
find "${STAGE_DIR}/${PLUGIN_NAME}" -type f -name '*.pyc' -delete

rm -f "${ZIP_PATH}"
(
  cd "${STAGE_DIR}"
  zip -qr "${ZIP_PATH}" "${PLUGIN_NAME}"
)

ls -lh "${ZIP_PATH}"
echo "[OK] ZIP do plugin MVP gerado em: ${ZIP_PATH}"

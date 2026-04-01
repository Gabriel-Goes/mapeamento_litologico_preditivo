#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

FOLHA_CODE="SB21_ZA_II"
SOURCE_GPKG="/home/database/geodatabase.gpkg"
DEST_GPKG="${REPO_ROOT}/plugins/preditor_territorial_mvp/data/gamba_mvp.gpkg"

usage() {
  cat <<EOF
Uso: $0 [--folha CODIGO] [--source GPKG] [--dest GPKG]

Exemplo:
  $0 --folha SB21_ZA_II
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --folha)
      FOLHA_CODE="$2"
      shift 2
      ;;
    --source)
      SOURCE_GPKG="$2"
      shift 2
      ;;
    --dest)
      DEST_GPKG="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[ERRO] Argumento desconhecido: $1" >&2
      usage
      exit 1
      ;;
  esac
done

if ! command -v ogr2ogr >/dev/null 2>&1; then
  echo "[ERRO] ogr2ogr nao encontrado no PATH." >&2
  exit 1
fi

if ! command -v ogrinfo >/dev/null 2>&1; then
  echo "[ERRO] ogrinfo nao encontrado no PATH." >&2
  exit 1
fi

if [[ ! -f "${SOURCE_GPKG}" ]]; then
  echo "[ERRO] GPKG fonte nao encontrado: ${SOURCE_GPKG}" >&2
  exit 1
fi

mkdir -p "$(dirname "${DEST_GPKG}")"

TMP_DIR="$(mktemp -d /tmp/pt_gamba_mvp_data_XXXXXX)"
trap 'rm -rf "${TMP_DIR}"' EXIT
FOLHA_TMP="${TMP_DIR}/folha.gpkg"

echo "[INFO] Fonte: ${SOURCE_GPKG}"
echo "[INFO] Folha: ${FOLHA_CODE}"
echo "[INFO] Destino: ${DEST_GPKG}"

echo "[STEP] Extraindo folha em mc_100k..."
ogr2ogr -f GPKG "${FOLHA_TMP}" "${SOURCE_GPKG}" mc_100k \
  -where "id_folha='${FOLHA_CODE}'" -nln mc_100k

FOLHA_COUNT="$(ogrinfo -ro -so "${FOLHA_TMP}" mc_100k | sed -n 's/^Feature Count: //p' | tr -d '[:space:]')"
if [[ -z "${FOLHA_COUNT}" || "${FOLHA_COUNT}" == "0" ]]; then
  echo "[ERRO] Folha nao encontrada em mc_100k: ${FOLHA_CODE}" >&2
  exit 1
fi

echo "[STEP] Criando GPKG final com camada de folha..."
rm -f "${DEST_GPKG}"
ogr2ogr -f GPKG "${DEST_GPKG}" "${FOLHA_TMP}" mc_100k -nln mc_100k

echo "[STEP] Clippando litologia_100k pela folha..."
ogr2ogr -f GPKG -update "${DEST_GPKG}" "${SOURCE_GPKG}" litologia_100k \
  -clipsrc "${FOLHA_TMP}" -clipsrclayer mc_100k -clipsrcwhere "id_folha='${FOLHA_CODE}'" \
  -nln litologia_100k

echo "[STEP] Clippando ocorr_min_cprm pela folha..."
ogr2ogr -f GPKG -update "${DEST_GPKG}" "${SOURCE_GPKG}" ocorr_min_cprm \
  -clipsrc "${FOLHA_TMP}" -clipsrclayer mc_100k -clipsrcwhere "id_folha='${FOLHA_CODE}'" \
  -nln ocorr_min_cprm

for LAYER in mc_100k litologia_100k ocorr_min_cprm; do
  COUNT="$(ogrinfo -ro -so "${DEST_GPKG}" "${LAYER}" | sed -n 's/^Feature Count: //p' | tr -d '[:space:]')"
  echo "[OK] ${LAYER}: ${COUNT} feicao(oes)"
done

ls -lh "${DEST_GPKG}"
echo "[OK] Dados MVP gerados em ${DEST_GPKG}"

#!/usr/bin/env bash
set -euo pipefail

# Launch QGIS with PreditorTerra environment + bootstrap code.
# Usage:
#   scripts/run_qgis_preditor.sh [--dry-run] [extra qgis args...]
# Optional env file:
#   scripts/preditor_qgis.env

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PREDITOR_CODE="${REPO_ROOT}/codes/PreditoTerra_QGIS.py"
ENV_FILE="${SCRIPT_DIR}/preditor_qgis.env"

if [[ ! -f "${PREDITOR_CODE}" ]]; then
  echo "[ERRO] Arquivo nao encontrado: ${PREDITOR_CODE}" >&2
  exit 1
fi

if [[ -f "${ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  source "${ENV_FILE}"
fi

DRY_RUN=0
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

QGIS_BIN="${QGIS_BIN:-qgis}"
if ! command -v "${QGIS_BIN}" >/dev/null 2>&1; then
  echo "[ERRO] Executavel do QGIS nao encontrado: ${QGIS_BIN}" >&2
  exit 1
fi

# Backend padrao: PostgreSQL/PostGIS.
export PREDITOR_DATA_BACKEND="${PREDITOR_DATA_BACKEND:-postgres}"
export PREDITOR_PG_HOST="${PREDITOR_PG_HOST:-127.0.0.1}"
export PREDITOR_PG_PORT="${PREDITOR_PG_PORT:-5432}"
export PREDITOR_PG_DB="${PREDITOR_PG_DB:-geologia}"
export PREDITOR_PG_USER="${PREDITOR_PG_USER:-postgres}"
export PREDITOR_PG_PASS="${PREDITOR_PG_PASS:-}"
export PREDITOR_PG_GAMA_SOURCE="${PREDITOR_PG_GAMA_SOURCE:-geof.v_gamma_1082_corr}"
export PREDITOR_PG_MAG_SOURCE="${PREDITOR_PG_MAG_SOURCE:-}"
export PREDITOR_PG_CONNECT_TIMEOUT="${PREDITOR_PG_CONNECT_TIMEOUT:-8}"
export PREDITOR_TERRA_CODE_FILE="${PREDITOR_TERRA_CODE_FILE:-${PREDITOR_CODE}}"

# PROJ explicitamente definido para evitar erro de CRS.
if [[ -f "/usr/share/proj/proj.db" ]]; then
  export PROJ_DATA="${PROJ_DATA:-/usr/share/proj}"
  export PROJ_LIB="${PROJ_LIB:-${PROJ_DATA}}"
fi

qgis_py_full="$(qgis_process --version 2>/dev/null | awk '/Python version/{print $3; exit}' || true)"
qgis_py_mm="$(awk -F. '{print $1"."$2}' <<<"${qgis_py_full:-}")"

declare -a py_parts
py_parts+=("${REPO_ROOT}")
py_parts+=("${REPO_ROOT}/codes")

# Extra path manual (separado por ':')
if [[ -n "${PREDITOR_EXTRA_PYTHONPATH:-}" ]]; then
  IFS=':' read -r -a extra_paths <<<"${PREDITOR_EXTRA_PYTHONPATH}"
  for p in "${extra_paths[@]}"; do
    [[ -n "${p}" ]] && py_parts+=("${p}")
  done
fi

# Opcional: anexar site-packages de um pyenv SOMENTE se major.minor bater com QGIS.
# Exemplo: export PREDITOR_PYENV_ENV=geo-qgis314
if [[ -n "${PREDITOR_PYENV_ENV:-}" ]]; then
  pyenv_root="${PYENV_ROOT:-$HOME/.pyenv}"
  env_root="${pyenv_root}/versions/${PREDITOR_PYENV_ENV}"
  env_python="${env_root}/bin/python"
  if [[ -x "${env_python}" ]]; then
    env_py_mm="$("${env_python}" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
    if [[ -n "${qgis_py_mm}" && "${env_py_mm}" == "${qgis_py_mm}" ]]; then
      site_pkg="$("${env_python}" -c 'import site; print(site.getsitepackages()[0])')"
      if [[ -d "${site_pkg}" ]]; then
        py_parts+=("${site_pkg}")
      fi
    else
      echo "[WARN] Ignorando pyenv '${PREDITOR_PYENV_ENV}': Python ${env_py_mm} != QGIS ${qgis_py_mm}." >&2
    fi
  else
    echo "[WARN] pyenv env nao encontrado: ${env_root}" >&2
  fi
fi

new_pythonpath="$(IFS=:; echo "${py_parts[*]}")"
if [[ -n "${PYTHONPATH:-}" ]]; then
  export PYTHONPATH="${new_pythonpath}:${PYTHONPATH}"
else
  export PYTHONPATH="${new_pythonpath}"
fi

# Expor diretório de plugin local do repositório para o QGIS.
plugin_path="${REPO_ROOT}/plugins"
if [[ -d "${plugin_path}" ]]; then
  if [[ -n "${QGIS_PLUGINPATH:-}" ]]; then
    export QGIS_PLUGINPATH="${plugin_path}:${QGIS_PLUGINPATH}"
  else
    export QGIS_PLUGINPATH="${plugin_path}"
  fi
fi

echo "[INFO] QGIS: ${QGIS_BIN}"
echo "[INFO] QGIS Python: ${qgis_py_full:-desconhecido}"
echo "[INFO] Backend: ${PREDITOR_DATA_BACKEND} | DB=${PREDITOR_PG_DB}@${PREDITOR_PG_HOST}:${PREDITOR_PG_PORT}"
echo "[INFO] Gama source: ${PREDITOR_PG_GAMA_SOURCE}"
echo "[INFO] PYTHONPATH (prefix): ${new_pythonpath}"
echo "[INFO] QGIS_PLUGINPATH: ${QGIS_PLUGINPATH:-}"
echo "[INFO] Code: ${PREDITOR_CODE}"

if [[ "${PREDITOR_REMOTE_DIAG:-0}" == "1" || "${PREDITOR_CHECK_PY_DEPS:-0}" == "1" ]]; then
  echo "[INFO] Verificando dependencias Python para STAC/rasters..."
  python - <<'PY'
import importlib.util
import os
import sys

# Mantem compatibilidade com bootstrap do PreditorTerra:
# paths extras ficam como fallback e nao sobrescrevem libs do QGIS.
extra = os.environ.get("PREDITOR_EXTRA_PYTHONPATH", "")
if extra:
    for p in [os.path.abspath(os.path.expanduser(x)) for x in extra.split(":") if x]:
        while p in sys.path:
            sys.path.remove(p)
        sys.path.append(p)

mods = [
    "pystac_client",
    "planetary_computer",
    "rasterio",
    "rioxarray",
    "xarray",
]
print(f"[INFO] Python exec: {sys.executable}")
print(f"[INFO] Python version: {sys.version.split()[0]}")
for m in mods:
    spec = importlib.util.find_spec(m)
    if spec is None:
        print(f"[WARN] modulo ausente: {m}")
    else:
        print(f"[OK] modulo encontrado: {m} ({spec.origin})")

try:
    import pyproj  # type: ignore
    from pyproj import CRS, datadir  # type: ignore
    print(f"[INFO] pyproj: {getattr(pyproj, '__file__', '<desconhecido>')}")
    print(f"[INFO] pyproj data dir: {datadir.get_data_dir()}")
    CRS("EPSG:4326")
    print("[OK] pyproj CRS smoke test (EPSG:4326)")
except Exception as e:
    print(f"[WARN] pyproj indisponivel/instavel: {e}")
PY
fi

if [[ "${DRY_RUN}" -eq 1 ]]; then
  echo "[INFO] Dry-run encerrado."
  exit 0
fi

exec "${QGIS_BIN}" --nologo --code "${PREDITOR_CODE}" "$@"

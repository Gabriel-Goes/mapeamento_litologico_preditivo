#!/usr/bin/env bash
set -euo pipefail

# Launcher de demo estável:
# - força backend gráfico X11/xcb para sessões remotas;
# - ativa diagnóstico remoto;
# - usa profile limpo do QGIS por padrão;
# - grava stdout/stderr em log de sessão com tee.
#
# Uso:
#   ./scripts/run_qgis_preditor_demo.sh [args extras do qgis]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

profile_name="${PREDITOR_PROFILE_NAME:-PreditorTerraClean}"
profiles_path="${PREDITOR_PROFILES_PATH:-${REPO_ROOT}/.qgis_profiles}"
session_log_dir="${PREDITOR_SESSION_LOG_DIR:-${REPO_ROOT}/logs/sessions}"
timestamp="$(date +%Y%m%d_%H%M%S)"
session_log="${session_log_dir}/qgis_run_${timestamp}.log"

mkdir -p "${profiles_path}" "${session_log_dir}" "${REPO_ROOT}/logs"

# Defaults seguros para operação remota.
export PREDITOR_REMOTE_DIAG="${PREDITOR_REMOTE_DIAG:-1}"
export PREDITOR_TERRA_LOG_LEVEL="${PREDITOR_TERRA_LOG_LEVEL:-DEBUG}"
export PREDITOR_TERRA_LOG_DIR="${PREDITOR_TERRA_LOG_DIR:-${REPO_ROOT}/logs}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export XDG_SESSION_TYPE="${XDG_SESSION_TYPE:-x11}"
export GDK_BACKEND="${GDK_BACKEND:-x11}"
unset WAYLAND_DISPLAY || true

# Evita duplicar --profile/--profiles-path caso o usuário já tenha passado.
has_profile=0
has_profiles_path=0
has_dry_run=0
forward_args=()
for arg in "$@"; do
  case "${arg}" in
    --profile|--profile=*)
      has_profile=1
      ;;
    --profiles-path|--profiles-path=*)
      has_profiles_path=1
      ;;
    --dry-run)
      has_dry_run=1
      continue
      ;;
  esac
  forward_args+=( "${arg}" )
done

cmd=( "${SCRIPT_DIR}/run_qgis_preditor_remote.sh" )
if [[ "${has_dry_run}" -eq 1 ]]; then
  cmd+=( --dry-run )
fi
if [[ "${has_profiles_path}" -eq 0 ]]; then
  cmd+=( --profiles-path "${profiles_path}" )
fi
if [[ "${has_profile}" -eq 0 ]]; then
  cmd+=( --profile "${profile_name}" )
fi
cmd+=( "${forward_args[@]}" )

echo "[INFO] Demo launcher iniciado."
echo "[INFO] Profile: ${profile_name}"
echo "[INFO] Profiles path: ${profiles_path}"
echo "[INFO] Log do PreditorTerra: ${PREDITOR_TERRA_LOG_DIR}/preditor_terra.log"
echo "[INFO] Log de sessão: ${session_log}"

set +e
"${cmd[@]}" 2>&1 | tee "${session_log}"
status="${PIPESTATUS[0]}"
set -e

echo "[INFO] QGIS finalizado com status=${status}"
echo "[INFO] Log de sessão salvo em: ${session_log}"
exit "${status}"

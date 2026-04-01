#!/usr/bin/env bash
set -euo pipefail

# Wrapper para uso remoto (Windows -> GeoServer), com X11 forwarding.
# Uso no servidor:
#   ./scripts/run_qgis_preditor_remote.sh [args do qgis]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REMOTE_ENV_FILE="${SCRIPT_DIR}/preditor_qgis.remote.env"

if [[ -f "${REMOTE_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${REMOTE_ENV_FILE}"
  set +a
fi

if [[ -z "${DISPLAY:-}" ]]; then
  echo "[ERRO] DISPLAY vazio. Use ssh -Y ou uma sessao remota grafica (RDP/VNC)." >&2
  exit 2
fi

# Ajustes comuns para reduzir problemas de rendering remoto.
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
export QT_X11_NO_MITSHM="${QT_X11_NO_MITSHM:-1}"
export LIBGL_ALWAYS_SOFTWARE="${LIBGL_ALWAYS_SOFTWARE:-1}"
export MESA_GL_VERSION_OVERRIDE="${MESA_GL_VERSION_OVERRIDE:-3.3}"

if [[ "${PREDITOR_REMOTE_DIAG:-0}" == "1" ]]; then
  "${SCRIPT_DIR}/check_qgis_remote_env.sh"
fi

exec "${SCRIPT_DIR}/run_qgis_preditor.sh" "$@"

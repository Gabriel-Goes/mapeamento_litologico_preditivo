#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
REMOTE_ENV_FILE="${SCRIPT_DIR}/preditor_qgis.remote.env"

if [[ -f "${REMOTE_ENV_FILE}" ]]; then
  # shellcheck disable=SC1090
  set -a
  source "${REMOTE_ENV_FILE}"
  set +a
fi

if command -v hostname >/dev/null 2>&1; then
  HOST_NAME="$(hostname -f 2>/dev/null || hostname 2>/dev/null || echo unknown-host)"
else
  HOST_NAME="$(uname -n 2>/dev/null || echo unknown-host)"
fi
printf '[INFO] Host: %s\n' "${HOST_NAME}"
printf '[INFO] User: %s\n' "$(whoami)"
printf '[INFO] Date: %s\n' "$(date -Iseconds)"
printf '[INFO] DISPLAY: %s\n' "${DISPLAY:-<vazio>}"
printf '[INFO] XAUTHORITY: %s\n' "${XAUTHORITY:-<vazio>}"

if [[ -z "${DISPLAY:-}" ]]; then
  echo "[ERRO] DISPLAY vazio. Conecte com X11 forwarding (ssh -Y) ou sessão remota gráfica." >&2
  exit 2
fi

for c in qgis qgis_process xauth; do
  if command -v "$c" >/dev/null 2>&1; then
    echo "[OK] comando encontrado: $c"
  else
    echo "[WARN] comando nao encontrado: $c"
  fi
done

echo "[INFO] Testando launcher em dry-run..."
PREDITOR_CHECK_PY_DEPS=1 "${REPO_ROOT}/scripts/run_qgis_preditor.sh" --dry-run

echo "[OK] Ambiente remoto parece pronto para abrir QGIS com PreditorTerra."

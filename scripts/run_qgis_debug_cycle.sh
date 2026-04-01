#!/usr/bin/env bash
set -euo pipefail

# Ciclo operacional de debug:
# 1) precheck remoto
# 2) execução QGIS (opcional)
# 3) consolidação de evidências
# 4) triagem estruturada dos logs
# 5) gate estrito opcional
#
# Uso:
#   ./scripts/run_qgis_debug_cycle.sh [--profile PreditorTerraClean] [--collect-only] [--strict-gate]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

profile_name="PreditorTerraClean"
collect_only=0
strict_gate=0
profiles_path="${PREDITOR_PROFILES_PATH:-${REPO_ROOT}/.qgis_profiles}"
session_log_dir="${PREDITOR_SESSION_LOG_DIR:-${REPO_ROOT}/logs/sessions}"
tag=""
forward_args=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      profile_name="${2:?valor ausente para --profile}"
      shift 2
      ;;
    --profiles-path)
      profiles_path="${2:?valor ausente para --profiles-path}"
      shift 2
      ;;
    --collect-only)
      collect_only=1
      shift
      ;;
    --strict-gate)
      strict_gate=1
      shift
      ;;
    --tag)
      tag="${2:?valor ausente para --tag}"
      shift 2
      ;;
    *)
      forward_args+=( "$1" )
      shift
      ;;
  esac
done

mkdir -p "${session_log_dir}" "${profiles_path}"

echo "[INFO] Iniciando ciclo de debug PreditorTerra."
echo "[INFO] profile=${profile_name} collect_only=${collect_only} strict_gate=${strict_gate}"
echo "[INFO] profiles_path=${profiles_path}"
echo "[INFO] session_log_dir=${session_log_dir}"

echo "[STEP 1/5] Precheck remoto..."
"${SCRIPT_DIR}/check_qgis_remote_env.sh"

if [[ "${collect_only}" -eq 0 ]]; then
  echo "[STEP 2/5] Execução QGIS para ciclo de teste..."
  "${SCRIPT_DIR}/run_qgis_preditor_demo.sh" \
    --profiles-path "${profiles_path}" \
    --profile "${profile_name}" \
    "${forward_args[@]}"
else
  echo "[STEP 2/5] Execução QGIS pulada (--collect-only)."
fi

echo "[STEP 3/5] Consolidando evidências..."
"${SCRIPT_DIR}/collect_demo_evidence.sh"

echo "[STEP 4/5] Rodando triagem de logs..."
triage_args=(
  --out-dir "${session_log_dir}"
)
if [[ -n "${tag}" ]]; then
  triage_args+=( --tag "${tag}" )
fi
"${SCRIPT_DIR}/triage_preditor_logs.py" "${triage_args[@]}"

latest_triage="$(ls -1t "${session_log_dir}"/debug_triage*.json 2>/dev/null | head -n 1 || true)"
if [[ -z "${latest_triage}" ]]; then
  echo "[ERRO] Triagem não gerou JSON em ${session_log_dir}." >&2
  exit 2
fi

echo "[INFO] Última triagem: ${latest_triage}"

echo "[STEP 5/5] Avaliando gate final..."
python3 - "${latest_triage}" "${strict_gate}" <<'PY'
import json
import sys

triage_json = sys.argv[1]
strict = int(sys.argv[2])

with open(triage_json, "r", encoding="utf-8") as f:
    data = json.load(f)

counts = data.get("counts", {}) or {}
gates = data.get("gates", {}) or {}
blocking = int(counts.get("blocking", 0) or 0)
som_ok = bool(gates.get("som_success"))
terr_ok = bool(gates.get("territorial_success"))

print(
    f"[INFO] Gate summary: blocking={blocking} "
    f"som_success={som_ok} territorial_success={terr_ok}"
)

if strict:
    if blocking > 0 or not som_ok or not terr_ok:
        print("[ERRO] Gate estrito falhou.")
        raise SystemExit(3)

print("[OK] Gate avaliado.")
PY

echo "[OK] Ciclo de debug concluído."


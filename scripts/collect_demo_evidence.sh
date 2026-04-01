#!/usr/bin/env bash
set -euo pipefail

# Consolida evidências da última execução para apresentação:
# - último log de sessão (tee);
# - log principal do PreditorTerra;
# - último relatório territorial JSON.
#
# Uso:
#   ./scripts/collect_demo_evidence.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

session_log_dir="${PREDITOR_SESSION_LOG_DIR:-${REPO_ROOT}/logs/sessions}"
preditor_log_dir="${PREDITOR_TERRA_LOG_DIR:-${REPO_ROOT}/logs}"
preditor_log="${preditor_log_dir}/preditor_terra.log"
reports_dir="${PREDITOR_TERRITORIAL_DIR:-/tmp/preditor_terra_territorial}"

timestamp="$(date +%Y%m%d_%H%M%S)"
out_md="${session_log_dir}/demo_evidence_${timestamp}.md"

mkdir -p "${session_log_dir}"

if command -v hostname >/dev/null 2>&1; then
  host_name="$(hostname -f 2>/dev/null || hostname 2>/dev/null || uname -n 2>/dev/null || echo unknown-host)"
else
  host_name="$(uname -n 2>/dev/null || echo unknown-host)"
fi

latest_session_log=""
if ls -1t "${session_log_dir}"/qgis_run_*.log >/dev/null 2>&1; then
  latest_session_log="$(ls -1t "${session_log_dir}"/qgis_run_*.log | head -n 1)"
fi

latest_report=""
if ls -1t "${reports_dir}"/territorial_*.json >/dev/null 2>&1; then
  latest_report="$(ls -1t "${reports_dir}"/territorial_*.json | head -n 1)"
fi

latest_triage_json=""
if ls -1t "${session_log_dir}"/debug_triage*.json >/dev/null 2>&1; then
  latest_triage_json="$(ls -1t "${session_log_dir}"/debug_triage*.json | head -n 1)"
fi

latest_triage_md=""
if ls -1t "${session_log_dir}"/debug_triage*.md >/dev/null 2>&1; then
  latest_triage_md="$(ls -1t "${session_log_dir}"/debug_triage*.md | head -n 1)"
fi

{
  echo "# Evidências da Demo PreditorTerra"
  echo
  echo "- Data/Hora: $(date -Iseconds)"
  echo "- Host: ${host_name}"
  echo "- Repo: ${REPO_ROOT}"
  echo
  echo "## Arquivos"
  echo "- Log de sessão: ${latest_session_log:-<nao encontrado>}"
  echo "- Log do PreditorTerra: ${preditor_log}"
  echo "- Relatório territorial: ${latest_report:-<nao encontrado>}"
  echo "- Triagem JSON: ${latest_triage_json:-<nao encontrado>}"
  echo "- Triagem MD: ${latest_triage_md:-<nao encontrado>}"
  echo
  echo "## Resumo dos Logs"

  if [[ -f "${preditor_log}" ]]; then
    flow_line="$(grep -E 'Fluxo concluído \|' "${preditor_log}" | tail -n 1 || true)"
    terr_line="$(grep -E 'Prioridade territorial concluída \|' "${preditor_log}" | tail -n 1 || true)"
    report_line="$(grep -E 'Relatório salvo em:' "${preditor_log}" | tail -n 1 || true)"
    mlrun_warn="$(grep -E 'ml\.run' "${preditor_log}" | tail -n 2 || true)"
    stac_warn="$(grep -E 'import_error|pystac_client|Erro busca STAC' "${preditor_log}" | tail -n 3 || true)"

    echo "- Último fluxo SOM:"
    echo "  - ${flow_line:-<não encontrado>}"
    echo "- Último fluxo territorial:"
    echo "  - ${terr_line:-<não encontrado>}"
    echo "- Último relatório salvo:"
    echo "  - ${report_line:-<não encontrado>}"
    echo "- Avisos ml.run (últimos):"
    if [[ -n "${mlrun_warn}" ]]; then
      while IFS= read -r line; do
        echo "  - ${line}"
      done <<< "${mlrun_warn}"
    else
      echo "  - <nenhum aviso encontrado>"
    fi
    echo "- Avisos STAC/dependências (últimos):"
    if [[ -n "${stac_warn}" ]]; then
      while IFS= read -r line; do
        echo "  - ${line}"
      done <<< "${stac_warn}"
    else
      echo "  - <nenhum aviso encontrado>"
    fi
  else
    echo "- Log principal não encontrado em ${preditor_log}."
  fi

  echo
  echo "## Métricas do último relatório territorial"
  if [[ -n "${latest_report}" && -f "${latest_report}" ]]; then
    python3 - "${latest_report}" <<'PY'
import json
import sys

p = sys.argv[1]
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

fids = data.get("fids", [])
m = data.get("metrics_agg", {}) or {}
orb = data.get("orbital_summary", {}) or {}

print(f"- FIDs: {', '.join(fids) if fids else '<vazio>'}")
print(f"- pct_alta_media: {m.get('pct_alta_media')}")
print(f"- pct_media_media: {m.get('pct_media_media')}")
print(f"- pct_baixa_media: {m.get('pct_baixa_media')}")
print(f"- pct_restrita_media: {m.get('pct_restrita_media')}")

if orb:
    print("- orbital_summary:")
    for fid, meta in orb.items():
        status = (meta or {}).get("status")
        err = (meta or {}).get("error")
        line = f"  - {fid}: status={status}"
        if err:
            line += f" | error={err}"
        print(line)
else:
    print("- orbital_summary: <não executado>")
PY
  else
    echo "- Relatório territorial não encontrado."
  fi

  echo
  echo "## Triagem de Severidade (última)"
  if [[ -n "${latest_triage_json}" && -f "${latest_triage_json}" ]]; then
    python3 - "${latest_triage_json}" <<'PY'
import json
import sys

p = sys.argv[1]
with open(p, "r", encoding="utf-8") as f:
    data = json.load(f)

counts = data.get("counts", {}) or {}
gates = data.get("gates", {}) or {}
recs = data.get("recommendations", []) or []

print(f"- blocking: {counts.get('blocking', 0)}")
print(f"- major: {counts.get('major', 0)}")
print(f"- minor: {counts.get('minor', 0)}")
print(f"- gate som_success: {gates.get('som_success')}")
print(f"- gate territorial_success: {gates.get('territorial_success')}")
if recs:
    print("- recomendações:")
    for r in recs:
        print(f"  - {r}")
PY
  else
    echo "- Triagem não encontrada."
  fi
} > "${out_md}"

echo "[OK] Evidências consolidadas em: ${out_md}"

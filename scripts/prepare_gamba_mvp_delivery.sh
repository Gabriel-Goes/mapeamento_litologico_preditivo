#!/usr/bin/env bash
set -euo pipefail

# Prepara pacote de entrega MVP para o Gamba:
# - seleciona uma sessão de QGIS com SOM+Territorial concluídos (ou fallback para a última);
# - gera triagem dedicada para essa sessão;
# - consolida dossiê técnico de entrega em docs/gamba;
# - gera mensagem pronta para envio.
#
# Uso:
#   ./scripts/prepare_gamba_mvp_delivery.sh
#   ./scripts/prepare_gamba_mvp_delivery.sh --session-log logs/sessions/qgis_run_YYYYmmdd_HHMMSS.log

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
SESS_DIR="${REPO_ROOT}/logs/sessions"
PREDITOR_LOG="${REPO_ROOT}/logs/preditor_terra.log"
GAMBA_DIR="${REPO_ROOT}/docs/gamba"

session_log=""
tag="gamba_mvp_delivery"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --session-log)
      session_log="${2:?valor ausente para --session-log}"
      shift 2
      ;;
    --tag)
      tag="${2:?valor ausente para --tag}"
      shift 2
      ;;
    *)
      echo "[ERRO] argumento desconhecido: $1" >&2
      exit 2
      ;;
  esac
done

mkdir -p "${SESS_DIR}" "${GAMBA_DIR}"

pick_best_session() {
  local chosen=""
  local f=""

  # Preferência: sessão com SOM+Territorial concluídos.
  while IFS= read -r f; do
    [[ -z "${f}" ]] && continue
    if rg -q "Fluxo concluído \\|" "${f}" && rg -q "Prioridade territorial concluída \\|" "${f}"; then
      chosen="${f}"
      break
    fi
  done < <(ls -1t "${SESS_DIR}"/qgis_run_*.log 2>/dev/null || true)

  # Fallback: última sessão disponível.
  if [[ -z "${chosen}" ]]; then
    chosen="$(ls -1t "${SESS_DIR}"/qgis_run_*.log 2>/dev/null | head -n1 || true)"
  fi

  printf '%s' "${chosen}"
}

if [[ -z "${session_log}" ]]; then
  session_log="$(pick_best_session)"
else
  # resolve relativo -> absoluto
  if [[ "${session_log}" != /* ]]; then
    session_log="${REPO_ROOT}/${session_log}"
  fi
fi

if [[ -z "${session_log}" || ! -f "${session_log}" ]]; then
  echo "[ERRO] Nenhum log de sessão encontrado/selecionado." >&2
  exit 3
fi

today="$(date +%F)"
ts_utc="$(date -u +%Y%m%dT%H%M%SZ)"

triage_out="$("${SCRIPT_DIR}/triage_preditor_logs.py" \
  --session-log "${session_log}" \
  --preditor-log "${PREDITOR_LOG}" \
  --out-dir "${SESS_DIR}" \
  --tag "${tag}" 2>&1)"
printf '%s\n' "${triage_out}"

triage_json="$(printf '%s\n' "${triage_out}" | sed -n 's/^\[OK\] Triagem JSON: //p' | tail -n1)"
triage_md="$(printf '%s\n' "${triage_out}" | sed -n 's/^\[OK\] Triagem MD: //p' | tail -n1)"

if [[ -z "${triage_json}" || ! -f "${triage_json}" ]]; then
  echo "[ERRO] Falha ao identificar JSON da triagem." >&2
  exit 4
fi

flow_line="$(rg "Fluxo concluído \\|" "${session_log}" | tail -n1 || true)"
terr_line="$(rg "Prioridade territorial concluída \\|" "${session_log}" | tail -n1 || true)"
run_line="$(rg "Run territorial iniciado em ml.run" "${session_log}" | head -n1 || true)"
report_line="$(rg "Relatório salvo em:" "${session_log}" | tail -n1 || true)"

stac_present_line="$(rg "modulo encontrado: pystac_client" "${session_log}" | head -n1 || true)"
stac_missing_line="$(rg "modulo ausente: pystac_client" "${session_log}" | head -n1 || true)"

report_path="$(printf '%s\n' "${report_line}" | sed -E 's/^.*Relatório salvo em: //')"
if [[ -z "${report_path}" || ! -f "${report_path}" ]]; then
  report_path="$(ls -1t /tmp/preditor_terra_territorial/territorial_*.json 2>/dev/null | head -n1 || true)"
fi

stress_upload="$(rg "Upload_geof .*concluído" "${PREDITOR_LOG}" | tail -n1 || true)"
stress_interp="$(rg "Interpolate ids=.*concluído" "${PREDITOR_LOG}" | tail -n1 || true)"

delivery_md="${GAMBA_DIR}/entrega_mvp_${today}.md"
message_md="${GAMBA_DIR}/mensagem_gamba_${today}.md"

python3 - "${triage_json}" "${report_path}" <<'PY' > /tmp/.gamba_metrics_tmp.txt
import json
import os
import sys

triage_json = sys.argv[1]
report_path = sys.argv[2] if len(sys.argv) > 2 else ""

with open(triage_json, "r", encoding="utf-8") as f:
    tri = json.load(f)

counts = tri.get("counts", {}) or {}
gates = tri.get("gates", {}) or {}
print(f"blocking={counts.get('blocking', 0)}")
print(f"major={counts.get('major', 0)}")
print(f"minor={counts.get('minor', 0)}")
print(f"som_success={gates.get('som_success')}")
print(f"territorial_success={gates.get('territorial_success')}")

if report_path and os.path.exists(report_path):
    with open(report_path, "r", encoding="utf-8") as f:
        rep = json.load(f)
    m = rep.get("metrics_agg", {}) or {}
    fids = rep.get("fids", []) or []
    print(f"report_fids={','.join(fids)}")
    print(f"pct_alta_media={m.get('pct_alta_media')}")
    print(f"pct_media_media={m.get('pct_media_media')}")
    print(f"pct_baixa_media={m.get('pct_baixa_media')}")
    print(f"pct_restrita_media={m.get('pct_restrita_media')}")
else:
    print("report_fids=")
    print("pct_alta_media=")
    print("pct_media_media=")
    print("pct_baixa_media=")
    print("pct_restrita_media=")
PY

# shellcheck disable=SC1091
source /tmp/.gamba_metrics_tmp.txt
rm -f /tmp/.gamba_metrics_tmp.txt

cat > "${delivery_md}" <<EOF
# Entrega MVP PreditorTerra para Gamba (${today})

## 1) Escopo entregue

- Demo + dossiê técnico (MVP operacional).
- Caso principal de referência para validação: sessão \`${session_log}\`.
- STAC tratado como não bloqueante para o MVP.

## 2) Evidências de execução

- Fluxo SOM:
  - ${flow_line:-<não encontrado>}
- Fluxo Territorial:
  - ${terr_line:-<não encontrado>}
- Persistência de run:
  - ${run_line:-<não encontrado>}
- Relatório territorial:
  - ${report_line:-<não encontrado>}

## 3) Gates e severidade

- blocking=${blocking}
- major=${major}
- minor=${minor}
- som_success=${som_success}
- territorial_success=${territorial_success}

Triagem dedicada desta entrega:
- JSON: ${triage_json}
- MD: ${triage_md}

## 4) Métricas do relatório territorial

- fids=${report_fids:-<vazio>}
- pct_alta_media=${pct_alta_media:-<vazio>}
- pct_media_media=${pct_media_media:-<vazio>}
- pct_baixa_media=${pct_baixa_media:-<vazio>}
- pct_restrita_media=${pct_restrita_media:-<vazio>}

Arquivo de relatório:
- ${report_path:-<não encontrado>}

## 5) Diagnóstico STAC da sessão

- Dependência encontrada:
  - ${stac_present_line:-<não>}
- Dependência ausente:
  - ${stac_missing_line:-<não>}

## 6) Evidência de estresse (folha grande)

- Último upload_geof concluído:
  - ${stress_upload:-<não encontrado>}
- Última interpolação concluída:
  - ${stress_interp:-<não encontrado>}

## 7) Limitações conhecidas (não bloqueantes para o MVP)

- Aviso recorrente de collation do PostgreSQL.
- Tempo alto de interpolação em cenário 100k com muitas features.
- Fechamento metodológico ASTER/S2 cloud-free + cobertura total permanece como próximo ciclo.

## 8) Próximos passos imediatos

1. Rodar demo curta com folha leve (caso principal) para apresentação.
2. Usar folha 100k apenas como evidência de estresse/performance.
3. Receber do Gamba os relatórios multicritério e pesos para replicação comparativa.
EOF

cat > "${message_md}" <<EOF
# Mensagem para Gamba (${today})

Fala, Gamba, tudo bem?

Fechamos um MVP funcional no PreditorTerra para planejamento territorial no QGIS e consolidamos as evidências técnicas.

## O que já está entregue

- Fluxo ponta a ponta por folha: banco -> interpolação -> SOM -> mapa preditivo.
- Fluxo territorial acoplado ao SOM com score multicritério transparente.
- Camadas finais no QGIS: \`PT_POTENCIAL\`, \`PT_RESTRICOES\`, \`PT_PRIORIDADE\`.
- Persistência de execução em \`ml.run\` e relatório técnico JSON por folha.

## Status técnico desta entrega

- Triagem dedicada: blocking=${blocking}, major=${major}, minor=${minor}
- Gates: som_success=${som_success}, territorial_success=${territorial_success}
- Dossiê técnico: \`docs/gamba/entrega_mvp_${today}.md\`

## O que precisamos de vocês para a próxima rodada

1. 1-2 relatórios multicritério anteriores (PDF).
2. Tabela de critérios e pesos usados hoje.
3. Camadas GIS de restrições/condicionantes do planejamento territorial.
4. Um caso piloto prioritário (folha/área + data de referência).
5. Se possível, um relatório em andamento para comparação lado a lado.

Com isso, fazemos a réplica metodológica e validamos o protótipo contra o fluxo atual de vocês.
EOF

echo "[OK] Dossiê MVP: ${delivery_md}"
echo "[OK] Mensagem MVP: ${message_md}"
echo "[OK] Pacote gerado em: ${ts_utc}"

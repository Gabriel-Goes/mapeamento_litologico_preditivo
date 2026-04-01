#!/usr/bin/env python3
"""Triagem estruturada dos logs do PreditorTerra/QGIS.

Gera:
  - JSON com assinaturas, severidades e gates de sucesso.
  - Markdown resumido para anexar em documentação/evidências.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence


@dataclass(frozen=True)
class Signature:
    name: str
    severity: str
    pattern: re.Pattern[str]
    recommendation: str


SIGNATURES: Sequence[Signature] = (
    Signature(
        name="quick_flow_error",
        severity="blocking",
        pattern=re.compile(r"\[ERRO fluxo rápido\]|Fluxo rápido completo falhou", re.IGNORECASE),
        recommendation="Investigar stacktrace do fluxo rápido e corrigir antes de novo reteste.",
    ),
    Signature(
        name="interp_error",
        severity="blocking",
        pattern=re.compile(r"\[ERRO _on_interp\]|Interpolate .* falhou", re.IGNORECASE),
        recommendation="Corrigir interpolação/grade antes de treinar/aplicar SOM.",
    ),
    Signature(
        name="stac_visual_missing",
        severity="major",
        pattern=re.compile(r"Item não oferece 'tci'/'visual'|Item sem 'tci'/'visual'", re.IGNORECASE),
        recommendation="Ajustar seleção de bandas/asset STAC (preset RGB por coleção).",
    ),
    Signature(
        name="ml_run_missing",
        severity="major",
        pattern=re.compile(r"ml\.run.*não existe|Persistência ml\.run indisponível", re.IGNORECASE),
        recommendation=(
            "Aplicar schema adaptativo: "
            "`python -m adaptive.cli init-db --sql-file sql/adaptive_schema.sql`."
        ),
    ),
    Signature(
        name="collation_mismatch",
        severity="minor",
        pattern=re.compile(r"não correspondência de versão de ordenação|REFRESH COLLATION VERSION", re.IGNORECASE),
        recommendation="Planejar manutenção de collation do banco; não bloqueia demo imediata.",
    ),
    Signature(
        name="gdal_algorithm_registered",
        severity="minor",
        pattern=re.compile(r"GDAL algorithm '.*' already registered", re.IGNORECASE),
        recommendation="Ruído de plugin/provedor GDAL duplicado; monitorar, sem bloqueio funcional.",
    ),
)


def _latest_matching(base_dir: Path, pattern: str) -> Path | None:
    matches = sorted(base_dir.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return matches[0] if matches else None


def _read_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def _find_examples(lines: Sequence[str], pattern: re.Pattern[str], limit: int = 3) -> list[str]:
    out: list[str] = []
    for line in lines:
        if pattern.search(line):
            out.append(line.strip())
            if len(out) >= limit:
                break
    return out


def _count_matches(lines: Iterable[str], pattern: re.Pattern[str]) -> int:
    return sum(1 for line in lines if pattern.search(line))


def _severity_counts(findings: Sequence[dict]) -> dict[str, int]:
    counts = {"blocking": 0, "major": 0, "minor": 0}
    for finding in findings:
        sev = str(finding["severity"])
        counts[sev] = counts.get(sev, 0) + int(finding["count"])
    return counts


def _build_markdown(report: dict) -> str:
    counts = report["counts"]
    gates = report["gates"]
    findings = report["findings"]
    recommendations = report["recommendations"]

    lines = [
        "# Debug Triage PreditorTerra",
        "",
        f"- Generated at: {report['generated_at_utc']}",
        f"- Session log: {report.get('session_log') or '<none>'}",
        f"- Preditor log: {report.get('preditor_log') or '<none>'}",
        "",
        "## Severity Counts",
        f"- blocking: {counts.get('blocking', 0)}",
        f"- major: {counts.get('major', 0)}",
        f"- minor: {counts.get('minor', 0)}",
        "",
        "## Gates",
        f"- som_success: {gates.get('som_success')}",
        f"- territorial_success: {gates.get('territorial_success')}",
        "",
        "## Findings",
    ]
    if findings:
        for f in findings:
            lines.append(
                f"- [{f['severity']}] {f['name']} | count={f['count']} | recommendation={f['recommendation']}"
            )
            for ex in f.get("examples", []):
                lines.append(f"  - {ex}")
    else:
        lines.append("- none")

    lines.extend(["", "## Recommended Actions"])
    if recommendations:
        for rec in recommendations:
            lines.append(f"- {rec}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Triagem de logs do PreditorTerra.")
    parser.add_argument(
        "--session-log",
        help="Caminho do log de sessão qgis_run_*.log. Se omitido, usa o mais recente em logs/sessions.",
    )
    parser.add_argument(
        "--preditor-log",
        default="logs/preditor_terra.log",
        help="Caminho do log principal do PreditorTerra.",
    )
    parser.add_argument(
        "--out-dir",
        default="logs/sessions",
        help="Diretório de saída para JSON/MD.",
    )
    parser.add_argument(
        "--tag",
        default="",
        help="Tag opcional para nomear os arquivos de saída.",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.session_log:
        session_log = Path(args.session_log).resolve()
    else:
        session_log = _latest_matching(out_dir, "qgis_run_*.log")

    preditor_log = Path(args.preditor_log).resolve()
    session_lines = _read_lines(session_log) if session_log else []
    preditor_lines = _read_lines(preditor_log)

    scan_lines = list(session_lines) if session_lines else list(preditor_lines)

    findings: list[dict] = []
    for sig in SIGNATURES:
        count = _count_matches(scan_lines, sig.pattern)
        if count <= 0:
            continue
        findings.append(
            {
                "name": sig.name,
                "severity": sig.severity,
                "count": count,
                "recommendation": sig.recommendation,
                "examples": _find_examples(scan_lines, sig.pattern),
            }
        )

    counts = _severity_counts(findings)
    gates = {
        "som_success": any("Fluxo concluído |" in line for line in scan_lines),
        "territorial_success": any("Prioridade territorial concluída |" in line for line in scan_lines),
    }

    recommendations = []
    if counts.get("blocking", 0) > 0:
        recommendations.append(
            "Existem erros blocking; não avançar sem corrigir e retestar o ciclo."
        )
    if counts.get("major", 0) > 0:
        recommendations.append(
            "Existem erros major; priorizar reescrita focada antes de nova demo."
        )
    if not gates["som_success"]:
        recommendations.append("Gate SOM não atendido; executar fluxo rápido até obter 'Fluxo concluído'.")
    if not gates["territorial_success"]:
        recommendations.append(
            "Gate Territorial não atendido; executar prioridade territorial até obter relatório salvo."
        )
    if not recommendations:
        recommendations.append("Sem bloqueios críticos detectados neste ciclo.")

    generated_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    tag = f"_{args.tag}" if args.tag else ""
    json_path = out_dir / f"debug_triage{tag}_{generated_at}.json"
    md_path = out_dir / f"debug_triage{tag}_{generated_at}.md"

    report = {
        "generated_at_utc": generated_at,
        "session_log": str(session_log) if session_log else None,
        "preditor_log": str(preditor_log),
        "counts": counts,
        "gates": gates,
        "findings": findings,
        "recommendations": recommendations,
    }

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_build_markdown(report), encoding="utf-8")

    print(f"[OK] Triagem JSON: {json_path}")
    print(f"[OK] Triagem MD: {md_path}")
    print(
        "[OK] Resumo:"
        f" blocking={counts.get('blocking', 0)}"
        f" major={counts.get('major', 0)}"
        f" minor={counts.get('minor', 0)}"
        f" som_success={gates['som_success']}"
        f" territorial_success={gates['territorial_success']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from search_pair import get_aster_cloudmask_href, search_aster_cloudfree_for_folha
from stac_utils import item_has_assets


PREFERRED_ASSETS = ["VNIR", "SWIR"]


def filter_rankable_candidates(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep rows that expose ASTER VNIR/SWIR assets and explicit cloud mask."""

    valid_rows: List[Dict[str, Any]] = []
    for row in rows:
        item = row.get("item")
        if item is None:
            continue
        if not item_has_assets(item, PREFERRED_ASSETS):
            continue
        if get_aster_cloudmask_href(item) is None:
            continue
        valid_rows.append(row)
    return valid_rows


def sort_candidates(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Order by coverage (desc), local cloud (asc) and temporal proximity (asc)."""

    return sorted(
        rows,
        key=lambda r: (
            -(r.get("coverage_fraction", 0.0) or 0.0),
            r.get("local_cloud_frac", 1.0) if r.get("local_cloud_frac") is not None else 1.0,
            r.get("delta_days", 1_000_000),
        ),
    )


def serialize_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": row.get("id"),
        "datetime": row.get("datetime"),
        "delta_days": row.get("delta_days"),
        "coverage_fraction": row.get("coverage_fraction"),
        "local_cloud_frac": row.get("local_cloud_frac"),
        "cloud_cover": row.get("cloud_cover"),
        "catalog_name": row.get("catalog_name"),
        "catalog_url": row.get("catalog_url"),
    }


def write_csv(path: Path, rows: List[Dict[str, Any]]) -> None:
    import csv

    fieldnames = [
        "id",
        "datetime",
        "delta_days",
        "coverage_fraction",
        "local_cloud_frac",
        "cloud_cover",
        "catalog_name",
        "catalog_url",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def build_output(
    folha_id: str,
    data_aerogama: str,
    sorted_rows: List[Dict[str, Any]],
) -> Dict[str, Any]:
    best_row = sorted_rows[0] if sorted_rows else None
    serialized = [serialize_row(r) for r in sorted_rows]

    return {
        "folha_id": folha_id,
        "data_aerogama": data_aerogama,
        "best": serialize_row(best_row) if best_row else None,
        "candidates": serialized,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Busca e ranqueia cenas ASTER para uma folha cartográfica.",
    )
    parser.add_argument("folha_id", help="Código da folha (ex: SB21_ZA_II2_NE)")
    parser.add_argument("data_aerogama", help="Data alvo (YYYY-MM-DD)")
    parser.add_argument(
        "--search-window",
        default="1999-01-01/2025-12-31",
        help="Janela temporal STAC (padrão: 1999-01-01/2025-12-31)",
    )
    parser.add_argument(
        "--max-cloud",
        type=float,
        default=90.0,
        help="Limite de nuvem global (metadado) para pré-filtro.",
    )
    parser.add_argument(
        "--max-local-cloud",
        type=float,
        default=0.02,
        help="Fração máxima de nuvem na área da folha.",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=0.95,
        help="Cobertura mínima da cena sobre a folha (fração).",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=None,
        help="Caminho opcional para salvar o resultado em JSON.",
    )
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=None,
        help="Caminho opcional para salvar o ranking em CSV.",
    )

    args = parser.parse_args()

    best, candidates_sorted, metrics_rows = search_aster_cloudfree_for_folha(
        codigo_folha=args.folha_id,
        aster_target_date_str=args.data_aerogama,
        search_datetime=args.search_window,
        min_coverage=args.min_coverage,
        max_cloud=args.max_cloud,
        max_local_cloud_frac=args.max_local_cloud,
    )

    if not candidates_sorted and metrics_rows:
        candidates_sorted = metrics_rows

    validated_rows = filter_rankable_candidates(candidates_sorted)
    ranked_rows = sort_candidates(validated_rows)

    if not ranked_rows:
        print(
            "Nenhum item ASTER com VNIR/SWIR e máscara de nuvem foi encontrado dentro dos critérios."
        )
    else:
        print("Candidatos ASTER ranqueados (melhor primeiro):")
        for row in ranked_rows:
            coverage = row.get("coverage_fraction") or 0.0
            print(
                f"  id={row.get('id')} | data={row.get('datetime')} | "
                f"cov={coverage*100:.2f}% | "
                f"nuvem_local={row.get('local_cloud_frac', 0):.4f} | "
                f"Δt={row.get('delta_days')} dias"
            )

    output = build_output(args.folha_id, args.data_aerogama, ranked_rows)

    if args.output_json:
        args.output_json.parent.mkdir(parents=True, exist_ok=True)
        args.output_json.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"JSON salvo em {args.output_json}")
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))

    if args.output_csv:
        write_csv(args.output_csv, [serialize_row(r) for r in ranked_rows])
        print(f"CSV salvo em {args.output_csv}")


if __name__ == "__main__":
    main()

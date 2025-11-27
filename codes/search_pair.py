from __future__ import annotations

import argparse
import csv
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
import xarray as xr
from shapely.geometry import shape
from shapely.ops import transform as shp_transform
from pyproj import Transformer

from db_conn import get_folha_geom_geojson
from stac_utils import get_pc_client, item_datetime, get_cloud_cover
from raster_utils import (
    clip_raster_to_folha,
    compute_nodata_fraction,
    compute_scl_cloud_fraction,
)


def parse_target_date(date_str: str) -> datetime:
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.replace(tzinfo=timezone.utc)


def build_local_equal_area_transformer(geom_geojson: Dict[str, Any]) -> Transformer:
    geom = shape(geom_geojson)
    lon0, lat0 = geom.centroid.x, geom.centroid.y
    laea_proj = (
        f"+proj=laea +lat_0={lat0} +lon_0={lon0} "
        "+datum=WGS84 +units=m +no_defs"
    )
    return Transformer.from_crs("EPSG:4326", laea_proj, always_xy=True)


def coverage_fraction(
    folha_geom_geojson: Dict[str, Any],
    item_geom_geojson: Dict[str, Any],
    transformer: Transformer,
) -> float:
    folha_geom = shape(folha_geom_geojson)
    item_geom = shape(item_geom_geojson)

    project = transformer.transform
    folha_proj = shp_transform(project, folha_geom)
    item_proj = shp_transform(project, item_geom)

    inter = folha_proj.intersection(item_proj)
    if folha_proj.is_empty or inter.is_empty:
        return 0.0
    return float(inter.area / folha_proj.area)


ASTER_CLOUD_ASSET_CANDIDATES = (
    "CLOUDMASK",
    "QA",
    "CLOUD",
)


def get_aster_cloudmask_href(item: Any) -> Optional[str]:
    for key, asset in item.assets.items():
        if key.upper() in ASTER_CLOUD_ASSET_CANDIDATES:
            return asset.href

    for asset in item.assets.values():
        title = (getattr(asset, "title", "") or "").lower()
        roles = getattr(asset, "roles", []) or []
        if "cloud" in title or "qa" in title or any(r.lower() == "cloud" for r in roles):
            return asset.href
    return None


def estimate_aster_cloud_fraction(
    aster_item: Any,
    folha_geom_geojson: Dict[str, Any],
    return_masks: bool = False,
) -> Tuple[float, float, int, int, int] | Tuple[float, float, np.ndarray, np.ndarray, int, int, int]:
    """Conta pixels de nuvem/nodata usando a máscara explícita do item ASTER."""

    print(
        "[ASTER] params: "
        f"item_id={getattr(aster_item, 'id', '?')}, "
        f"return_masks={return_masks}"
    )

    cloud_href = get_aster_cloudmask_href(aster_item)
    if cloud_href is None:
        raise RuntimeError(f"Item {getattr(aster_item, 'id', '?')} sem asset de nuvem/QA.")

    da_clip = clip_raster_to_folha(cloud_href, folha_geom_geojson)
    nodata_frac, nodata_mask = compute_nodata_fraction(da_clip, return_mask=True)

    data = da_clip.values
    if data.ndim == 3:
        data = data[0]

    total_pixels = data.size
    if total_pixels == 0:
        raise RuntimeError("Recorte da máscara de nuvem retornou zero pixels.")

    cloud_mask = (~np.isnan(data)) & (data > 0)
    cloud_pixels = int(cloud_mask.sum())
    nodata_pixels = int(nodata_mask.sum())
    cloud_frac = float(cloud_pixels / total_pixels)

    if return_masks:
        return (
            cloud_frac,
            nodata_frac,
            cloud_mask,
            nodata_mask,
            cloud_pixels,
            nodata_pixels,
            total_pixels,
        )
    return cloud_frac, nodata_frac, cloud_pixels, nodata_pixels, total_pixels


def rank_scenes(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    has_cloud_free = any(r.get("cloudy_pixels_aoi", 1) == 0 for r in rows)

    if has_cloud_free:
        return sorted(
            rows,
            key=lambda d: (
                d.get("cloudy_pixels_aoi", 1) != 0,
                d["delta_days"],
                d.get("cloudy_pixels_aoi", 0),
                d["cloud_cover"],
                -d["coverage_fraction"],
            ),
        )

    return sorted(
        rows,
        key=lambda d: (
            d.get("cloudy_pixels_aoi", 0),
            d["delta_days"],
            d["cloud_cover"],
            -d["coverage_fraction"],
        ),
    )


def write_metrics_csv(path: str, rows: List[Dict[str, Any]]) -> None:
    metrics_path = Path(path)
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "id",
        "datetime",
        "delta_days",
        "cloud_meta",
        "local_cloud_frac",
        "nodata_frac",
        "cloudy_pixels_aoi",
        "nodata_pixels_aoi",
        "total_pixels_aoi",
        "coverage_fraction",
    ]
    with metrics_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"[ASTER] Métricas salvas em: {metrics_path}")


def search_aster_cloudfree_for_folha(
    codigo_folha: str,
    aster_target_date_str: str,
    collection_id: str = "aster-l1t",
    search_datetime: str = "2000-01-01/2025-12-31",
    min_coverage: float = 0.99,
    max_cloud: float = 90.0,
    max_local_cloud_frac: float = 0.02,
    max_items: int = 2000,
    metrics_csv_path: Optional[str] = None,
    debug: bool = False,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    print(
        "[ASTER] params: "
        f"folha={codigo_folha}, "
        f"target_date={aster_target_date_str}, "
        f"collection={collection_id}, "
        f"datetime_window={search_datetime}, "
        f"min_coverage={min_coverage}, "
        f"max_cloud_meta={max_cloud}, "
        f"max_local_cloud_frac={max_local_cloud_frac}, "
        f"max_items={max_items}, "
        f"metrics_csv_path={metrics_csv_path}, "
        f"debug={debug}"
    )
    folha_geom = get_folha_geom_geojson(codigo_folha)
    folha_shape = shape(folha_geom)
    print(
        f"[ASTER] Folha '{codigo_folha}' carregada. "
        f"Área WGS84 (aprox): {folha_shape.area:.6f} (graus²)"
    )

    transformer = build_local_equal_area_transformer(folha_geom)
    client = get_pc_client()

    print(f"[ASTER] Buscando itens em '{collection_id}'...")
    search = client.search(
        collections=[collection_id],
        intersects=folha_geom,
        datetime=search_datetime,
        max_items=max_items,
    )
    items = list(search.items())
    print(f"[ASTER] Total de itens retornados: {len(items)}")

    if not items:
        return None, [], []

    target_date = parse_target_date(aster_target_date_str).date()
    candidates: List[Dict[str, Any]] = []
    rankable_rows: List[Dict[str, Any]] = []
    metrics_rows: List[Dict[str, Any]] = []

    for item in items:
        dt = item_datetime(item)
        delta_days = abs((dt.date() - target_date).days)

        cloud = get_cloud_cover(item)
        if cloud is None or cloud > max_cloud:
            print(f' Cloud: {cloud} - {item.id} skipped due to cloud cover.')
            continue

        frac = coverage_fraction(
            folha_geom_geojson=folha_geom,
            item_geom_geojson=item.geometry,
            transformer=transformer,
        )
        if frac < min_coverage:
            continue

        try:
            (
                local_cloud_frac,
                nodata_frac,
                cloud_pixels,
                nodata_pixels,
                total_pixels,
            ) = estimate_aster_cloud_fraction(
                aster_item=item,
                folha_geom_geojson=folha_geom,
            )
        except Exception as e:
            print(f"[ASTER] Erro ao estimar nuvem local para {item.id}: {e}")
            continue

        rankable_row = {
            "id": item.id,
            "datetime": dt.isoformat(),
            "delta_days": delta_days,
            "coverage_fraction": frac,
            "coverage_percent": frac * 100.0,
            "cloud_cover": cloud,
            "local_cloud_frac": local_cloud_frac,
            "nodata_frac": nodata_frac,
            "cloudy_pixels_aoi": cloud_pixels,
            "nodata_pixels_aoi": nodata_pixels,
            "total_pixels_aoi": total_pixels,
            "item": item,
        }
        rankable_rows.append(rankable_row)
        metrics_rows.append(
            {
                "id": item.id,
                "datetime": dt.isoformat(),
                "delta_days": delta_days,
                "cloud_meta": cloud,
                "local_cloud_frac": local_cloud_frac,
                "nodata_frac": nodata_frac,
                "cloudy_pixels_aoi": cloud_pixels,
                "nodata_pixels_aoi": nodata_pixels,
                "total_pixels_aoi": total_pixels,
                "coverage_fraction": frac,
            }
        )

        if local_cloud_frac > max_local_cloud_frac:
            print(
                f"[ASTER] {item.id} rejeitado: nuvem local={local_cloud_frac:.4f} "
                f"(limite={max_local_cloud_frac:.4f})."
            )
            continue

        candidates.append(rankable_row)

    if not candidates and rankable_rows:
        print(
            "[ASTER] Nenhum item após filtro de nuvem local; aplicando fallback "
            "apenas com ordenação (rank_scenes)."
        )
        candidates_sorted = rank_scenes(rankable_rows)
    else:
        candidates_sorted = rank_scenes(candidates)

    if metrics_csv_path and metrics_rows:
        write_metrics_csv(metrics_csv_path, metrics_rows)

    if candidates_sorted:
        print("\n[ASTER] Itens candidatos (ordenados):")
        for c in candidates_sorted:
            print(
                f"  id={c['id']}, datetime={c['datetime']}, "
                f"Δt={c['delta_days']} dias, "
                f"cov={c['coverage_percent']:.2f}%, "
                f"cloud={c['cloud_cover']:.2f}%, "
                f"local_cloud_frac={c['local_cloud_frac']:.4f}, "
                f"nodata_frac={c['nodata_frac']:.4f}, "
                f"cloud_px={c['cloudy_pixels_aoi']}, "
                f"nodata_px={c['nodata_pixels_aoi']}, "
                f"total_px={c['total_pixels_aoi']}"
            )
    else:
        print("[ASTER] Nenhum item atendeu cobertura/nuvem.")
        return None, [], metrics_rows

    best = candidates_sorted[0]
    print(
        "\n[ASTER] Melhor item:\n"
        f"  id={best['id']}\n"
        f"  datetime={best['datetime']}\n"
        f"  Δt={best['delta_days']} dias\n"
        f"  cov={best['coverage_percent']:.2f}%\n"
        f"  cloud={best['cloud_cover']:.2f}%\n"
        f"  local_cloud_frac={best['local_cloud_frac']:.4f}\n"
        f"  nodata_frac={best['nodata_frac']:.4f}"
    )
    return best, candidates_sorted, metrics_rows


def search_s2_cloudfree_for_folha_given_aster(
    codigo_folha: str,
    aster_datetime: datetime,
    search_datetime: str = "2015-01-01/2020-01-01",
    meta_max_cloud: float = 80.0,
    scl_cloud_max: float = 0.0,
    max_items: int = 500,
) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    print(
        "[S2] params: "
        f"folha={codigo_folha}, "
        f"aster_datetime={aster_datetime.isoformat()}, "
        f"datetime_window={search_datetime}, "
        f"meta_max_cloud={meta_max_cloud}, "
        f"scl_cloud_max={scl_cloud_max}, "
        f"max_items={max_items}"
    )
    folha_geom = get_folha_geom_geojson(codigo_folha)
    folha_shape = shape(folha_geom)
    print(
        f"[S2] Folha '{codigo_folha}' carregada. "
        f"Área WGS84 (aprox): {folha_shape.area:.6f} (graus²)"
    )

    client = get_pc_client()
    print("[S2] Buscando itens em 'sentinel-2-l2a'...")
    search = client.search(
        collections=["sentinel-2-l2a"],
        intersects=folha_geom,
        datetime=search_datetime,
        max_items=max_items,
    )
    items = list(search.items())
    print(f"[S2] Total de itens retornados: {len(items)}")

    if not items:
        return None, []

    meta_list: List[Dict[str, Any]] = []
    for item in items:
        meta_cloud = get_cloud_cover(item)
        if meta_cloud is None or meta_cloud > meta_max_cloud:
            continue

        dt = item_datetime(item)
        delta_days = abs((dt.date() - aster_datetime.date()).days)
        meta_list.append(
            {
                "id": item.id,
                "datetime": dt,
                "delta_days": delta_days,
                "meta_cloud": meta_cloud,
                "item": item,
            }
        )

    if not meta_list:
        print("[S2] Nenhuma cena passou pelo filtro rápido.")
        return None, []

    meta_sorted = sorted(
        meta_list,
        key=lambda d: (d["delta_days"], d["meta_cloud"]),
    )

    candidates_with_metrics: List[Dict[str, Any]] = []
    best_cloudfree: Optional[Dict[str, Any]] = None
    best_by_scl: Optional[Dict[str, Any]] = None

    for m in meta_sorted:
        item = m["item"]
        if "SCL" not in item.assets:
            continue

        scl_href = item.assets["SCL"].href
        try:
            da_scl_clip = clip_raster_to_folha(scl_href, folha_geom)
            scl_nodata_frac, scl_cloud_frac, scl_arr, cloud_mask = compute_scl_cloud_fraction(da_scl_clip)
        except Exception as e:
            print(f"[S2] Erro ao processar SCL {item.id}: {e}")
            continue

        row = {
            "id": item.id,
            "datetime": m["datetime"].isoformat(),
            "delta_days": m["delta_days"],
            "meta_cloud": m["meta_cloud"],
            "scl_nodata_frac": scl_nodata_frac,
            "scl_cloud_frac": scl_cloud_frac,
            "item": item,
        }
        candidates_with_metrics.append(row)

        print(
            f"[S2] {item.id} | date={m['datetime'].date()} | "
            f"meta_cloud={m['meta_cloud']:.2f}% | "
            f"scl_cloud_frac={scl_cloud_frac:.4f} | "
            f"scl_nodata_frac={scl_nodata_frac:.4f} | "
            f"Δt(ASTER)={m['delta_days']} dias"
        )

        if best_by_scl is None:
            best_by_scl = row
        else:
            if (scl_cloud_frac < best_by_scl["scl_cloud_frac"]) or (
                scl_cloud_frac == best_by_scl["scl_cloud_frac"]
                and m["delta_days"] < best_by_scl["delta_days"]
            ):
                best_by_scl = row

        if scl_cloud_frac <= scl_cloud_max:
            best_cloudfree = row
            break

    if best_cloudfree is not None:
        best = best_cloudfree
        print("\n[S2] Melhor cena (primeira sem nuvem segundo SCL):")
    else:
        if best_by_scl is None:
            print("[S2] Nenhuma cena com SCL válida.")
            return None, candidates_with_metrics
        best = best_by_scl
        print("\n[S2] Nenhuma cena com SCL<=limiar; usando menor scl_cloud_frac:")

    print(
        f"  id={best['id']}\n"
        f"  datetime={best['datetime']}\n"
        f"  Δt(ASTER)={best['delta_days']} dias\n"
        f"  meta_cloud={best['meta_cloud']:.2f}%\n"
        f"  scl_cloud_frac={best['scl_cloud_frac']:.4f}\n"
        f"  scl_nodata_frac={best['scl_nodata_frac']:.4f}"
    )
    return best, candidates_with_metrics


def inspect_aster_clip(aster_item: Any, folha_geom_geojson: Dict[str, Any]) -> None:
    print("\n[INSPECT ASTER]")
    print(f"  ASTER id: {aster_item.id}")
    print(f"  cloud_cover: {aster_item.properties.get('eo:cloud_cover')} %")
    print("  Assets:", list(aster_item.assets.keys()))

    if "VNIR" in aster_item.assets:
        asset_key = "VNIR"
    else:
        asset_key = list(aster_item.assets.keys())[0]
        print(f"  Asset 'VNIR' não encontrado, usando '{asset_key}'.")

    href = aster_item.assets[asset_key].href
    da_clip = clip_raster_to_folha(href, folha_geom_geojson)
    frac_nodata, nodata_mask = compute_nodata_fraction(da_clip, return_mask=True)
    print(f"  Fração nodata: {frac_nodata:.4f}")

    if "band" in da_clip.dims:
        da_plot = da_clip.isel(band=0)
    else:
        da_plot = da_clip

    data = da_plot.values
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    im1 = ax1.imshow(data, origin="upper")
    ax1.set_title("ASTER VNIR recortado (banda 1)")
    fig.colorbar(im1, ax=ax1, shrink=0.7)

    im2 = ax2.imshow(nodata_mask, origin="upper")
    ax2.set_title("Máscara nodata")
    fig.colorbar(im2, ax=ax2, shrink=0.7)
    plt.tight_layout()
    plt.show()


def inspect_s2_clip(s2_item: Any, folha_geom_geojson: Dict[str, Any]) -> None:
    print("\n[INSPECT S2]")
    print(f"  S2 id: {s2_item.id}")
    print(f"  cloud_cover: {s2_item.properties.get('eo:cloud_cover')} %")
    print("  Assets:", list(s2_item.assets.keys()))

    if "visual" in s2_item.assets:
        visual_key = "visual"
    else:
        visual_key = list(s2_item.assets.keys())[0]
        print(f"  Asset 'visual' não encontrado, usando '{visual_key}'.")

    href_vis = s2_item.assets[visual_key].href
    da_vis_clip = clip_raster_to_folha(href_vis, folha_geom_geojson)
    frac_nodata_vis, nodata_mask_vis = compute_nodata_fraction(da_vis_clip, return_mask=True)
    print(f"  Fração nodata visual: {frac_nodata_vis:.4f}")

    arr = da_vis_clip.values
    if arr.ndim == 3 and da_vis_clip.sizes.get("band", 1) >= 3:
        arr = arr.astype("float32")
        valid = arr[~np.isnan(arr)]
        if valid.size > 0:
            vmin = np.nanpercentile(valid, 2)
            vmax = np.nanpercentile(valid, 98)
            scale = vmax - vmin if vmax > vmin else 1.0
            arr_scaled = np.clip((arr - vmin) / scale, 0, 1)
        else:
            arr_scaled = np.zeros_like(arr)

        rgb = np.transpose(arr_scaled[:3, :, :], (1, 2, 0))
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        ax1.imshow(rgb)
        ax1.set_title("S2 visual recortado (RGB)")
        ax2.imshow(nodata_mask_vis, origin="upper")
        ax2.set_title("Máscara nodata visual")
        plt.tight_layout()
        plt.show()
    else:
        data = da_vis_clip.values
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        im1 = ax1.imshow(data, origin="upper")
        ax1.set_title("S2 recortado")
        fig.colorbar(im1, ax=ax1, shrink=0.7)
        im2 = ax2.imshow(nodata_mask_vis, origin="upper")
        ax2.set_title("Máscara nodata")
        fig.colorbar(im2, ax=ax2, shrink=0.7)
        plt.tight_layout()
        plt.show()

    if "SCL" not in s2_item.assets:
        print("[INSPECT S2] Asset SCL ausente.")
        return

    href_scl = s2_item.assets["SCL"].href
    da_scl_clip = clip_raster_to_folha(href_scl, folha_geom_geojson)
    scl_nodata_frac, scl_cloud_frac, scl_arr, cloud_mask = compute_scl_cloud_fraction(da_scl_clip)
    print(f"  scl_nodata_frac={scl_nodata_frac:.4f}")
    print(f"  scl_cloud_frac={scl_cloud_frac:.4f}")

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    im1 = ax1.imshow(scl_arr, origin="upper")
    ax1.set_title("SCL códigos")
    fig.colorbar(im1, ax=ax1, shrink=0.7)
    im2 = ax2.imshow(cloud_mask, origin="upper")
    ax2.set_title("Máscara nuvem/sombra/neve")
    fig.colorbar(im2, ax=ax2, shrink=0.7)
    plt.tight_layout()
    plt.show()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folha", required=True, help="Código da folha (ex: SB21_ZA_II2_NE)")
    parser.add_argument("--aster-date", required=True, help="Data alvo ASTER (YYYY-MM-DD)")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Habilita plots de depuração para avaliação de nuvem ASTER",
    )
    parser.add_argument(
        "--max-local-cloud-aster",
        type=float,
        default=0.02,
        help="Limite de fração de nuvem local para ASTER",
    )
    parser.add_argument(
        "--max-global-cloud-aster",
        type=float,
        default=90.0,
        help="Limite de nuvem global (metadado) para ASTER",
    )
    parser.add_argument(
        "--aster-metrics-csv",
        default=None,
        help="Caminho para salvar métricas de avaliação das cenas ASTER",
    )
    args = parser.parse_args()

    folha = args.folha
    aster_target = args.aster_date
    debug_mode = args.debug
    metrics_csv = args.aster_metrics_csv or f"aster_metrics_{folha}.csv"

    print(
        "[PIPELINE SEARCH] params: "
        f"folha={folha}, "
        f"aster_date={aster_target}, "
        f"max_local_cloud_aster={args.max_local_cloud_aster}, "
        f"max_global_cloud_aster={args.max_global_cloud_aster}, "
        f"metrics_csv={metrics_csv}, "
        f"debug={debug_mode}"
    )
    print("=" * 80)
    print(f"[PIPELINE SEARCH] Folha: {folha}")
    print("=" * 80)

    aster_best, _, _ = search_aster_cloudfree_for_folha(
        codigo_folha=folha,
        aster_target_date_str=aster_target,
        max_cloud=args.max_global_cloud_aster,
        max_local_cloud_frac=args.max_local_cloud_aster,
        metrics_csv_path=metrics_csv,
        debug=debug_mode,
    )
    if aster_best is None:
        print("[PIPELINE SEARCH] Nenhuma ASTER adequada.")
        return

    aster_item = aster_best["item"]
    aster_dt = item_datetime(aster_item)
    print(f"[PIPELINE SEARCH] ASTER selecionada: {aster_best['id']}")

    s2_best, _ = search_s2_cloudfree_for_folha_given_aster(
        codigo_folha=folha,
        aster_datetime=aster_dt,
    )
    if s2_best is None:
        print("[PIPELINE SEARCH] Nenhuma S2 adequada.")
        return

    s2_item = s2_best["item"]
    print(f"[PIPELINE SEARCH] S2 selecionada: {s2_best['id']}")

    print("\n[PAR SELECIONADO]")
    print(
        f"  ASTER: {aster_best['id']} ({aster_best['datetime']}), "
        f"cov={aster_best['coverage_fraction']*100.0:.2f}%, "
        f"cloud={aster_best['cloud_cover']:.2f}%"
    )
    print(
        f"  S2   : {s2_best['id']} ({s2_best['datetime']}), "
        f"meta_cloud={s2_best['meta_cloud']:.2f}%, "
        f"scl_cloud_frac={s2_best['scl_cloud_frac']:.4f}"
    )

    folha_geom = get_folha_geom_geojson(folha)
    inspect_aster_clip(aster_item, folha_geom)
    inspect_s2_clip(s2_item, folha_geom)


if __name__ == "__main__":
    main()

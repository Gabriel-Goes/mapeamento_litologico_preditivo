from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import matplotlib.pyplot as plt
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


@dataclass
class SceneQuality:
    id: str
    collection: str
    datetime: Optional[datetime]
    delta_days: Optional[int]
    cloud_cover: Optional[float] = None
    meta_cloud: Optional[float] = None
    coverage_fraction: Optional[float] = None
    local_cloud_frac: Optional[float] = None
    nodata_frac: Optional[float] = None
    scl_cloud_frac: Optional[float] = None
    scl_nodata_frac: Optional[float] = None
    item: Any = None

    @property
    def coverage_percent(self) -> Optional[float]:
        if self.coverage_fraction is None:
            return None
        return self.coverage_fraction * 100.0


@dataclass
class PairSelectionResult:
    selected_aster: Optional[SceneQuality]
    selected_s2: Optional[SceneQuality]
    aster_candidates: List[SceneQuality]
    s2_candidates: List[SceneQuality]


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


def estimate_aster_cloud_fraction(
    aster_item: Any,
    folha_geom_geojson: Dict[str, Any],
    brightness_percentile: float = 98.0,
    debug: bool = False,
) -> Tuple[float, float]:
    """Heurística simples para estimar nuvem em ASTER sobre a folha.

    Como o produto ``aster-l1t`` não fornece uma máscara explícita de nuvem,
    usamos o brilho da banda 1 do VNIR como proxy: a fração de pixels acima
    de um percentil alto é tomada como nuvem potencial. Também retornamos a
    fração de ``nodata`` para referência.
    """

    if "VNIR" in aster_item.assets:
        asset_key = "VNIR"
    else:
        asset_key = next(iter(aster_item.assets.keys()))

    href = aster_item.assets[asset_key].href
    da_clip = clip_raster_to_folha(href, folha_geom_geojson)
    nodata_frac, _ = compute_nodata_fraction(da_clip, return_mask=True)

    data = da_clip.values
    if data.ndim == 3:
        data = data[0]

    valid = data[~np.isnan(data)]
    if valid.size == 0:
        return 1.0, nodata_frac

    threshold = float(np.nanpercentile(valid, brightness_percentile))
    cloud_mask = (~np.isnan(data)) & (data >= threshold)
    cloud_frac = float(cloud_mask.sum() / cloud_mask.size)

    if debug:
        vmin = np.nanpercentile(valid, 2) if valid.size > 0 else 0.0
        vmax = np.nanpercentile(valid, 98) if valid.size > 0 else 1.0
        scale = vmax - vmin if vmax > vmin else 1.0
        data_norm = np.clip((data - vmin) / scale, 0, 1)
        data_norm = np.nan_to_num(data_norm, nan=0.0)

        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        im1 = ax1.imshow(data_norm, origin="upper", cmap="gray", vmin=0, vmax=1)
        ax1.set_title("ASTER VNIR recortado (normalizado)")
        fig.colorbar(im1, ax=ax1, shrink=0.7)

        im2 = ax2.imshow(cloud_mask, origin="upper", cmap="gray")
        ax2.set_title(f"Máscara nuvem ≥ p{brightness_percentile}")
        fig.colorbar(im2, ax=ax2, shrink=0.7)

        plt.tight_layout()
        plt.show()

    return cloud_frac, nodata_frac


def rank_scenes(
    candidates: List[SceneQuality], max_local_cloud: Optional[float] = None
) -> List[SceneQuality]:
    filtered: List[SceneQuality] = []
    for cand in candidates:
        if (
            max_local_cloud is not None
            and cand.local_cloud_frac is not None
            and cand.local_cloud_frac > max_local_cloud
        ):
            continue
        filtered.append(cand)

    def _sort_key(cand: SceneQuality) -> Tuple[float, float, int, float]:
        primary = (
            cand.local_cloud_frac
            if cand.local_cloud_frac is not None
            else (
                cand.scl_cloud_frac
                if cand.scl_cloud_frac is not None
                else (
                    cand.meta_cloud
                    if cand.meta_cloud is not None
                    else cand.cloud_cover if cand.cloud_cover is not None else float("inf")
                )
            )
        )
        secondary = (
            cand.meta_cloud
            if cand.meta_cloud is not None
            else cand.cloud_cover if cand.cloud_cover is not None else float("inf")
        )
        delta = cand.delta_days if cand.delta_days is not None else 0
        coverage = -(cand.coverage_fraction or 0.0)
        return (float(primary), float(secondary), int(delta), float(coverage))

    return sorted(filtered, key=_sort_key)


def evaluate_aster_candidates(
    codigo_folha: str,
    aster_target_date_str: str,
    collection_id: str = "aster-l1t",
    search_datetime: str = "2000-01-01/2025-12-31",
    min_coverage: float = 0.99,
    max_cloud: float = 90.0,
    max_items: int = 2000,
    debug: bool = False,
) -> List[SceneQuality]:
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
        return []

    target_date = parse_target_date(aster_target_date_str).date()
    candidates: List[SceneQuality] = []

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
            local_cloud_frac, nodata_frac = estimate_aster_cloud_fraction(
                aster_item=item,
                folha_geom_geojson=folha_geom,
                debug=debug,
            )
        except Exception as e:
            print(f"[ASTER] Erro ao estimar nuvem local para {item.id}: {e}")
            continue

        candidates.append(
            SceneQuality(
                id=item.id,
                collection=collection_id,
                datetime=dt,
                delta_days=delta_days,
                coverage_fraction=frac,
                cloud_cover=cloud,
                local_cloud_frac=local_cloud_frac,
                nodata_frac=nodata_frac,
                item=item,
            )
        )

    return candidates


def search_aster_cloudfree_for_folha(
    codigo_folha: str,
    aster_target_date_str: str,
    collection_id: str = "aster-l1t",
    search_datetime: str = "2000-01-01/2025-12-31",
    min_coverage: float = 0.99,
    max_cloud: float = 90.0,
    max_local_cloud_frac: float = 0.02,
    max_items: int = 2000,
    debug: bool = False,
) -> Tuple[Optional[SceneQuality], List[SceneQuality]]:
    candidates = evaluate_aster_candidates(
        codigo_folha=codigo_folha,
        aster_target_date_str=aster_target_date_str,
        collection_id=collection_id,
        search_datetime=search_datetime,
        min_coverage=min_coverage,
        max_cloud=max_cloud,
        max_items=max_items,
        debug=debug,
    )

    if not candidates:
        print("[ASTER] Nenhum item atendeu cobertura/nuvem.")
        return None, []

    candidates_sorted = rank_scenes(candidates, max_local_cloud=max_local_cloud_frac)

    print("\n[ASTER] Itens candidatos (ordenados):")
    for c in candidates_sorted:
        cov_percent = c.coverage_percent if c.coverage_percent is not None else 0.0
        print(
            f"  id={c.id}, datetime={c.datetime.isoformat()}, "
            f"Δt={c.delta_days} dias, "
            f"cov={cov_percent:.2f}%, "
            f"cloud={c.cloud_cover:.2f}%, "
            f"local_cloud_frac={c.local_cloud_frac:.4f}, "
            f"nodata_frac={(c.nodata_frac or 0.0):.4f}"
        )

    best = candidates_sorted[0]
    print(
        "\n[ASTER] Melhor item:\n"
        f"  id={best.id}\n"
        f"  datetime={best.datetime}\n"
        f"  Δt={best.delta_days} dias\n"
        f"  cov={(best.coverage_percent or 0.0):.2f}%\n"
        f"  cloud={(best.cloud_cover or 0.0):.2f}%\n"
        f"  local_cloud_frac={(best.local_cloud_frac or 0.0):.4f}\n"
        f"  nodata_frac={(best.nodata_frac or 0.0):.4f}"
    )
    return best, candidates_sorted


def evaluate_s2_candidates(
    codigo_folha: str,
    aster_datetime: datetime,
    search_datetime: str = "2015-01-01/2020-01-01",
    meta_max_cloud: float = 80.0,
    max_items: int = 500,
    debug_plots: bool = False,
) -> List[SceneQuality]:
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
        return []

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
        return []

    meta_sorted = sorted(
        meta_list,
        key=lambda d: (d["delta_days"], d["meta_cloud"]),
    )

    candidates_with_metrics: List[SceneQuality] = []

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

        if debug_plots:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            im1 = ax1.imshow(scl_arr, origin="upper")
            ax1.set_title(f"SCL {item.id}")
            fig.colorbar(im1, ax=ax1, shrink=0.7)
            im2 = ax2.imshow(cloud_mask, origin="upper")
            ax2.set_title("Máscara nuvem/sombra/neve")
            fig.colorbar(im2, ax=ax2, shrink=0.7)
            plt.tight_layout()
            plt.show()

        candidates_with_metrics.append(
            SceneQuality(
                id=item.id,
                collection="sentinel-2-l2a",
                datetime=m["datetime"],
                delta_days=m["delta_days"],
                meta_cloud=m["meta_cloud"],
                scl_nodata_frac=scl_nodata_frac,
                scl_cloud_frac=scl_cloud_frac,
                local_cloud_frac=scl_cloud_frac,
                item=item,
            )
        )

        print(
            f"[S2] {item.id} | date={m['datetime'].date()} | "
            f"meta_cloud={m['meta_cloud']:.2f}% | "
            f"scl_cloud_frac={scl_cloud_frac:.4f} | "
            f"scl_nodata_frac={scl_nodata_frac:.4f} | "
            f"Δt(ASTER)={m['delta_days']} dias"
        )

    return candidates_with_metrics


def search_s2_cloudfree_for_folha_given_aster(
    codigo_folha: str,
    aster_datetime: datetime,
    search_datetime: str = "2015-01-01/2020-01-01",
    meta_max_cloud: float = 80.0,
    scl_cloud_max: float = 0.0,
    max_items: int = 500,
    debug_plots: bool = False,
) -> Tuple[Optional[SceneQuality], List[SceneQuality]]:
    candidates_with_metrics = evaluate_s2_candidates(
        codigo_folha=codigo_folha,
        aster_datetime=aster_datetime,
        search_datetime=search_datetime,
        meta_max_cloud=meta_max_cloud,
        max_items=max_items,
        debug_plots=debug_plots,
    )

    if not candidates_with_metrics:
        return None, []

    ranked = rank_scenes(candidates_with_metrics, max_local_cloud=scl_cloud_max)
    if not ranked:
        print("[S2] Nenhuma cena com SCL válida dentro do limite de nuvem.")
        return None, candidates_with_metrics

    best = ranked[0]
    print("\n[S2] Melhor cena (após ranking por SCL/local_cloud):")
    print(
        f"  id={best.id}\n"
        f"  datetime={best.datetime}\n"
        f"  Δt(ASTER)={best.delta_days} dias\n"
        f"  meta_cloud={(best.meta_cloud or 0.0):.2f}%\n"
        f"  scl_cloud_frac={(best.scl_cloud_frac or 0.0):.4f}\n"
        f"  scl_nodata_frac={(best.scl_nodata_frac or 0.0):.4f}"
    )
    return best, ranked


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
    args = parser.parse_args()

    folha = args.folha
    aster_target = args.aster_date
    debug_mode = args.debug

    print("=" * 80)
    print(f"[PIPELINE SEARCH] Folha: {folha}")
    print("=" * 80)

    aster_best, _ = search_aster_cloudfree_for_folha(
        codigo_folha=folha,
        aster_target_date_str=aster_target,
        debug=debug_mode,
    )
    if aster_best is None:
        print("[PIPELINE SEARCH] Nenhuma ASTER adequada.")
        return

    aster_item = aster_best.item
    aster_dt = aster_best.datetime
    print(f"[PIPELINE SEARCH] ASTER selecionada: {aster_best.id}")

    s2_best, _ = search_s2_cloudfree_for_folha_given_aster(
        codigo_folha=folha,
        aster_datetime=aster_dt,
    )
    if s2_best is None:
        print("[PIPELINE SEARCH] Nenhuma S2 adequada.")
        return

    s2_item = s2_best.item
    print(f"[PIPELINE SEARCH] S2 selecionada: {s2_best.id}")

    print("\n[PAR SELECIONADO]")
    print(
        f"  ASTER: {aster_best.id} ({aster_best.datetime}), "
        f"cov={(aster_best.coverage_percent or 0.0):.2f}%, "
        f"cloud={(aster_best.cloud_cover or 0.0):.2f}%"
    )
    print(
        f"  S2   : {s2_best.id} ({s2_best.datetime}), "
        f"meta_cloud={(s2_best.meta_cloud or 0.0):.2f}%, "
        f"scl_cloud_frac={(s2_best.scl_cloud_frac or 0.0):.4f}"
    )

    folha_geom = get_folha_geom_geojson(folha)
    inspect_aster_clip(aster_item, folha_geom)
    inspect_s2_clip(s2_item, folha_geom)


if __name__ == "__main__":
    main()

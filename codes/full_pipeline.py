# full_pipeline.py
from __future__ import annotations

import argparse
import os
from typing import Any, Optional

import csv
import json
import numpy as np
import xarray as xr

from config import ORBITAL_DIR
from stac_utils import item_datetime
from search_pair import (
    search_aster_cloudfree_for_folha,
    search_s2_cloudfree_for_folha_given_aster,
    estimate_aster_cloud_fraction,
)
from gs_fusion import run_gs_pair_pipeline
from supercube import build_supercube, load_supercube
from labeling_lito import build_label_raster_for_folha
from dataset_pixels import extract_pixel_dataset
from dataset_patches import generate_patches
from log_utils import log_stdout
from scene_preview import (
    build_rgb_quicklook,
    overlay_cloud_on_rgb,
    save_mask_preview,
    save_rgb_preview,
)
from db_conn import get_folha_geom_geojson
from raster_utils import (
    clip_raster_to_folha,
    compute_nodata_fraction,
    compute_scl_cloud_fraction,
)


DEFAULT_ASTER_TARGET_DATE = "2008-07-01"


def resolve_pair(
    folha: str,
    aster_id: Optional[str],
    s2_id: Optional[str],
    aster_date: Optional[str],
    max_local_cloud_aster: float = 0.02,
    max_global_cloud_aster: float = 90.0,
    aster_metrics_csv: Optional[str] = None,
    return_best: bool = False,
    return_candidates: bool = False,
) -> tuple[
    str, str
] | tuple[
    str,
    str,
    Optional[dict],
    Optional[dict],
] | tuple[
    str,
    str,
    Optional[dict],
    Optional[dict],
    list[dict],
    list[dict],
]:
    if aster_id and s2_id:
        print("[PAIR] Usando IDs fornecidos pelo usuário.")
        if return_best or return_candidates:
            base = (aster_id, s2_id, None, None)
            if return_candidates:
                return (*base, [], [])
            return base
        return aster_id, s2_id

    if not aster_date:
        raise SystemExit(
            "Se --aster-id/--s2-id não forem fornecidos, é obrigatório informar --aster-date (YYYY-MM-DD)."
        )

    best_aster, aster_candidates, _ = search_aster_cloudfree_for_folha(
        codigo_folha=folha,
        aster_target_date_str=aster_date,
        max_cloud=max_global_cloud_aster,
        max_local_cloud_frac=max_local_cloud_aster,
        metrics_csv_path=aster_metrics_csv,
    )
    if best_aster is None:
        raise SystemExit("Nenhum ASTER adequado encontrado para essa folha/data.")

    aster_item = best_aster["item"]
    aster_id_sel = aster_item.id
    aster_dt = item_datetime(aster_item)
    print(f"[PAIR] ASTER selecionado: {aster_id_sel} (Δt alvo={best_aster['delta_days']} dias)")

    best_s2, s2_candidates = search_s2_cloudfree_for_folha_given_aster(
        codigo_folha=folha,
        aster_datetime=aster_dt,
    )
    if best_s2 is None:
        raise SystemExit("Nenhum Sentinel-2 adequado encontrado para esse ASTER.")

    s2_id_sel = best_s2["id"]
    print(f"[PAIR] S2 selecionado: {s2_id_sel} (Δt ASTER={best_s2['delta_days']} dias)")

    if return_best or return_candidates:
        base = (aster_id_sel, s2_id_sel, best_aster, best_s2)
        if return_candidates:
            return (*base, aster_candidates, s2_candidates)
        return base
    return aster_id_sel, s2_id_sel


def summarize_imagery_quality(
    folha: str,
    best_aster: Optional[dict],
    best_s2: Optional[dict],
) -> None:
    """Reporta frações de nodata/nuvem para aster e S2 recortados na folha.

    A geometria da folha é obtida diretamente do banco (via ``get_folha_geom_geojson``),
    e cada asset relevante é recortado com ``clip_raster_to_folha`` antes de medir
    ``nodata`` ou nuvens.
    """

    folha_geom = get_folha_geom_geojson(folha)
    print("\n[QUALITY] Avaliando qualidade das cenas selecionadas...")

    if best_aster is None:
        print("[QUALITY][ASTER] Nenhum item ASTER disponível para avaliação.")
    else:
        aster_item = best_aster["item"]
        if "VNIR" in aster_item.assets:
            asset_key = "VNIR"
        else:
            asset_key = next(iter(aster_item.assets.keys()))
            print(f"[QUALITY][ASTER] Asset 'VNIR' ausente; usando '{asset_key}'.")

        href = aster_item.assets[asset_key].href
        da_clip = clip_raster_to_folha(href, folha_geom)
        aster_nodata_frac, _ = compute_nodata_fraction(da_clip, return_mask=True)
        print(
            f"[QUALITY][ASTER] id={aster_item.id} | nodata_frac={aster_nodata_frac:.4f} | "
            f"cloud_cover_meta={aster_item.properties.get('eo:cloud_cover')}%"
        )

    if best_s2 is None:
        print("[QUALITY][S2] Nenhum item Sentinel-2 disponível para avaliação.")
    else:
        s2_item = best_s2["item"]
        if "SCL" not in s2_item.assets:
            print(f"[QUALITY][S2] Asset SCL ausente em {s2_item.id}; impossível medir nuvem.")
        else:
            scl_href = s2_item.assets["SCL"].href
            da_scl_clip = clip_raster_to_folha(scl_href, folha_geom)
            scl_nodata_frac, scl_cloud_frac, *_ = compute_scl_cloud_fraction(da_scl_clip)
            print(
                f"[QUALITY][S2] id={s2_item.id} | scl_cloud_frac={scl_cloud_frac:.4f} | "
                f"scl_nodata_frac={scl_nodata_frac:.4f} | meta_cloud={best_s2['meta_cloud']:.2f}%"
            )


def _write_preview_summary(
    folha: str,
    preview_dir: str,
    rows: list[dict],
) -> dict:
    if not rows:
        return {}

    fieldnames = sorted({key for row in rows for key in row.keys()})

    csv_path = os.path.join(preview_dir, f"{folha}_search_previews.csv")
    json_path = os.path.join(preview_dir, f"{folha}_search_previews.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)

    print(f"[PREVIEW] Sumários salvos em: {csv_path} e {json_path}")
    return {"csv_path": csv_path, "json_path": json_path}


def _load_s2_rgb_da(item: Any, folha_geom: dict) -> xr.DataArray:
    assets = item.assets
    if "visual" in assets:
        href = assets["visual"].href
        return clip_raster_to_folha(href, folha_geom)

    rgb_band_ids = ["B04", "B03", "B02"]
    if all(b in assets for b in rgb_band_ids):
        ref_da = clip_raster_to_folha(assets[rgb_band_ids[0]].href, folha_geom)
        band_list = [ref_da]
        for b in rgb_band_ids[1:]:
            da_b = clip_raster_to_folha(assets[b].href, folha_geom)
            da_b = da_b.rio.reproject_match(ref_da)
            band_list.append(da_b)
        return xr.concat(band_list, dim="band")

    first_asset = next(iter(assets.values()))
    return clip_raster_to_folha(first_asset.href, folha_geom)


def generate_search_previews(
    folha: str,
    preview_dir: str,
    preview_top_k: int,
    aster_candidates: Optional[list[dict]],
    s2_candidates: Optional[list[dict]],
    debug_cloud_masks: bool = False,
) -> dict:
    if preview_top_k <= 0:
        return {}

    os.makedirs(preview_dir, exist_ok=True)
    folha_geom = get_folha_geom_geojson(folha)

    rows: list[dict] = []

    if aster_candidates:
        for cand in aster_candidates[:preview_top_k]:
            item = cand["item"]
            asset_key = "VNIR" if "VNIR" in item.assets else next(iter(item.assets.keys()))
            href = item.assets[asset_key].href
            da_clip = clip_raster_to_folha(href, folha_geom)
            rgb = build_rgb_quicklook(da_clip, bands_idx=(0, 1, 2))

            rgb_path = os.path.join(preview_dir, f"{folha}_ASTER_{cand['id']}_rgb.png")
            save_rgb_preview(rgb, rgb_path)

            cloud_frac, nodata_frac, cloud_mask, nodata_mask = estimate_aster_cloud_fraction(
                aster_item=item,
                folha_geom_geojson=folha_geom,
                return_masks=True,
                da_clip=da_clip,
            )
            mask = cloud_mask | nodata_mask
            mask_path = os.path.join(preview_dir, f"{folha}_ASTER_{cand['id']}_mask.png")
            save_mask_preview(mask, mask_path)

            overlay_path = None
            if debug_cloud_masks:
                overlay = overlay_cloud_on_rgb(rgb, mask)
                overlay_path = os.path.join(preview_dir, f"{folha}_ASTER_{cand['id']}_overlay.png")
                save_rgb_preview(overlay, overlay_path)

            rows.append(
                {
                    "sensor": "ASTER",
                    "id": cand.get("id"),
                    "datetime": cand.get("datetime"),
                    "delta_days": cand.get("delta_days"),
                    "coverage_fraction": cand.get("coverage_fraction"),
                    "cloud_cover_meta": cand.get("cloud_cover"),
                    "local_cloud_frac": cand.get("local_cloud_frac"),
                    "nodata_frac": nodata_frac,
                    "rgb_preview": rgb_path,
                    "mask_preview": mask_path,
                    "overlay_preview": overlay_path,
                }
            )

    if s2_candidates:
        for cand in s2_candidates[:preview_top_k]:
            item = cand["item"]
            scl_href = item.assets["SCL"].href if "SCL" in item.assets else None
            mask_path = None
            overlay_path = None
            scl_cloud_frac = cand.get("scl_cloud_frac")
            scl_nodata_frac = cand.get("scl_nodata_frac")

            if scl_href:
                da_scl_clip = clip_raster_to_folha(scl_href, folha_geom)
                scl_nodata_frac, scl_cloud_frac, scl_arr, cloud_mask = compute_scl_cloud_fraction(da_scl_clip)
                mask = cloud_mask | (scl_arr == 0)
                mask_path = os.path.join(preview_dir, f"{folha}_S2_{cand['id']}_mask.png")
                save_mask_preview(mask, mask_path)
            else:
                mask = None

            try:
                rgb_da = _load_s2_rgb_da(item, folha_geom)
                rgb = build_rgb_quicklook(rgb_da, bands_idx=(0, 1, 2))
                rgb_path = os.path.join(preview_dir, f"{folha}_S2_{cand['id']}_rgb.png")
                save_rgb_preview(rgb, rgb_path)
                if debug_cloud_masks and mask is not None:
                    overlay = overlay_cloud_on_rgb(rgb, mask)
                    overlay_path = os.path.join(preview_dir, f"{folha}_S2_{cand['id']}_overlay.png")
                    save_rgb_preview(overlay, overlay_path)
            except Exception as e:
                print(f"[PREVIEW][S2] Falha ao gerar RGB para {cand.get('id')}: {e}")
                rgb_path = None

            rows.append(
                {
                    "sensor": "S2",
                    "id": cand.get("id"),
                    "datetime": cand.get("datetime"),
                    "delta_days": cand.get("delta_days"),
                    "meta_cloud": cand.get("meta_cloud"),
                    "scl_cloud_frac": scl_cloud_frac,
                    "scl_nodata_frac": scl_nodata_frac,
                    "rgb_preview": rgb_path,
                    "mask_preview": mask_path,
                    "overlay_preview": overlay_path,
                }
            )

    return _write_preview_summary(folha=folha, preview_dir=preview_dir, rows=rows)


def run_gs_and_supercube(
    folha: str,
    aster_id: str,
    s2_id: str,
    orbital_dir: str,
) -> tuple[xr.DataArray, str, str, str]:
    print("=" * 80)
    print("[STEP] Fusão GS ASTER+S2")
    print("=" * 80)

    s2_band_ids = [
        "B02", "B03", "B04",
        "B05", "B06", "B07", "B08", "B8A",
        "B11", "B12",
    ]

    aster_ms, aster_gs, s2_stack = run_gs_pair_pipeline(
        folha_codigo=folha,
        aster_collection="aster-l1t",
        aster_id=aster_id,
        s2_collection="sentinel-2-l2a",
        s2_id=s2_id,
        s2_band_ids=s2_band_ids,
        out_dir=orbital_dir,
    )

    s2_stack_path = os.path.join(
        orbital_dir,
        f"{folha}_S2_{s2_id}_stack.tif",
    )
    aster_gs_path = os.path.join(
        orbital_dir,
        f"{folha}_ASTER_{aster_id}_VNIR_SWIR_GS_10m.tif",
    )
    supercube_out_path = os.path.join(
        orbital_dir,
        f"{folha}_S2_ASTER_GS_supercube_10m.tif",
    )

    print("=" * 80)
    print("[STEP] Construindo super-cubo S2+ASTER_GS")
    print("=" * 80)

    super_cube = build_supercube(
        folha_codigo=folha,
        s2_stack_path=s2_stack_path,
        aster_gs_path=aster_gs_path,
        out_path=supercube_out_path,
    )
    return super_cube, aster_gs_path, s2_stack_path, supercube_out_path


def build_datasets(
    folha: str,
    supercube_dir: str,
    max_samples_per_class: Optional[int],
    patch_size: int,
    stride: int,
    max_patches_per_class: Optional[int],
    out_pixels: Optional[str],
    out_patches: Optional[str],
    ) -> dict:
    print("=" * 80)
    print("[STEP] Carregando super-cubo e raster de rótulos")
    print("=" * 80)

    super_cube = load_supercube(folha, supercube_dir=supercube_dir)
    print(f"[INFO] Super-cubo shape = {super_cube.values.shape}")
    print(f"[INFO] Bandas = {list(super_cube.band.values)}")

    label_raster, gdf_lito = build_label_raster_for_folha(
        folha_codigo=folha,
        reference_da=super_cube,
        background_label=0,
    )
    print(f"[INFO] Unidades litológicas = {len(gdf_lito)}")
    print(f"[INFO] Raster labels shape = {label_raster.shape}")

    print("=" * 80)
    print("[STEP] Dataset de pixels")
    print("=" * 80)

    X_pix, y_pix = extract_pixel_dataset(
        super_cube=super_cube,
        label_raster=label_raster,
        max_samples_per_class=max_samples_per_class,
    )
    print(f"[INFO] Pixels: X.shape={X_pix.shape}, y.shape={y_pix.shape}")
    print(f"[INFO] Pixels: n_classes={np.unique(y_pix).size}")

    pixels_path = out_pixels or f"./dataset_pixels_{folha}.npz"
    np.savez_compressed(
        pixels_path,
        X=X_pix,
        y=y_pix,
        bands=np.array(list(super_cube.band.values)),
        band_metadata=np.array([super_cube.attrs.get("band_metadata", {})], dtype=object),
    )
    print(f"[OUTPUT] Dataset de pixels salvo em: {pixels_path}")

    print("=" * 80)
    print("[STEP] Dataset de patches")
    print("=" * 80)

    X_patch, y_patch = generate_patches(
        super_cube=super_cube,
        label_raster=label_raster,
        patch_size=patch_size,
        stride=stride,
        max_patches_per_class=max_patches_per_class,
    )
    print(f"[INFO] Patches: X.shape={X_patch.shape}, y.shape={y_patch.shape}")
    print(f"[INFO] Patches: n_classes={np.unique(y_patch).size}")

    patches_path = out_patches or f"./dataset_patches_{folha}_ps{patch_size}_st{stride}.npz"
    np.savez_compressed(
        patches_path,
        X=X_patch,
        y=y_patch,
        bands=np.array(list(super_cube.band.values)),
        patch_size=np.array([patch_size]),
        stride=np.array([stride]),
        band_metadata=np.array([super_cube.attrs.get("band_metadata", {})], dtype=object),
    )
    print(f"[OUTPUT] Dataset de patches salvo em: {patches_path}")

    return {
        "pixels_path": pixels_path,
        "patches_path": patches_path,
        "pixels_shape": X_pix.shape,
        "patches_shape": X_patch.shape,
        "n_pixel_classes": np.unique(y_pix).size,
        "n_patch_classes": np.unique(y_patch).size,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folha", required=True, help="Código da folha (ex: SB21_ZA_II2_NE)")

    parser.add_argument("--aster-id", default=None)
    parser.add_argument("--s2-id", default=None)
    parser.add_argument(
        "--aster-date",
        default=DEFAULT_ASTER_TARGET_DATE,
        help=(
            "YYYY-MM-DD (usado se IDs não forem dados); o padrão aponta para o período "
            "do levantamento aerogeofísico (julho/2008)."
        ),
    )

    parser.add_argument("--orbital-dir", default=ORBITAL_DIR, help="Diretório de saída para rasters")
    parser.add_argument("--supercube-dir", default=ORBITAL_DIR, help="Diretório onde está o super-cubo")

    parser.add_argument("--max-samples-per-class", type=int, default=None)
    parser.add_argument("--patch-size", type=int, default=32)
    parser.add_argument("--stride", type=int, default=16)
    parser.add_argument("--max-patches-per-class", type=int, default=None)

    parser.add_argument("--out-pixels", default=None)
    parser.add_argument("--out-patches", default=None)

    parser.add_argument("--skip-gs", action="store_true", help="Pular GS+super-cubo e usar super-cubo já existente")
    parser.add_argument("--skip-datasets", action="store_true", help="Pular geração dos datasets")
    parser.add_argument('--debug-s2-plots', action='store_true', help='Habilita plots de SCL de cada cena S2 candidata')
    parser.add_argument("--preview-top-k", type=int, default=0, help="Quantidade de cenas ASTER/S2 a pré-visualizar na busca")
    parser.add_argument("--preview-dir", default=None, help="Diretório onde salvar RGB/máscaras das pré-visualizações")
    parser.add_argument("--debug-cloud-masks", action="store_true", help="Gera overlays RGB+mascara para depuração")
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
        help=(
            "Caminho para salvar métricas de avaliação das cenas ASTER; "
            "por padrão salva no diretório de logs da folha."
        ),
    )
    parser.add_argument(
        "--search-only",
        action="store_true",
        help=(
            "Executa apenas a busca/seleção das cenas (resolve_pair) e a análise de qualidade "
            "(summarize_imagery_quality), sem rodar GS/super-cubo nem gerar datasets."
        ),
    )


    args = parser.parse_args()

    folha = args.folha
    orbital_dir = args.orbital_dir
    os.makedirs(orbital_dir, exist_ok=True)
    preview_dir = args.preview_dir or os.path.join(orbital_dir, "previews")

    log_dir = os.path.join(orbital_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    aster_metrics_csv = args.aster_metrics_csv or os.path.join(
        log_dir, f"aster_metrics_{folha}.csv"
    )
    base_name = f"full_pipeline_{folha}"

    with log_stdout(log_dir, base_name) as log_path:
        print("=" * 80)
        print(f"[FULL PIPELINE] Folha: {folha}")
        print(f"[FULL PIPELINE] Log em: {log_path}")
        print("=" * 80)

        if args.search_only:
            return_candidates = args.preview_top_k > 0
            print(
                "[FULL PIPELINE] Chamando resolve_pair com: "
                f"folha={folha}, aster_id={args.aster_id}, s2_id={args.s2_id}, "
                f"aster_date={args.aster_date}, return_best=True, return_candidates={return_candidates}"
            )
            resolve_out = resolve_pair(
                folha=folha,
                aster_id=args.aster_id,
                s2_id=args.s2_id,
                aster_date=args.aster_date,
                max_local_cloud_aster=args.max_local_cloud_aster,
                max_global_cloud_aster=args.max_global_cloud_aster,
                aster_metrics_csv=aster_metrics_csv,
                return_best=True,
                return_candidates=return_candidates,
            )
            if return_candidates:
                (
                    aster_id,
                    s2_id,
                    best_aster,
                    best_s2,
                    aster_candidates,
                    s2_candidates,
                ) = resolve_out
            else:
                aster_id, s2_id, best_aster, best_s2 = resolve_out
            print(
                "[FULL PIPELINE] resolve_pair retornou: "
                f"ASTER={aster_id}, S2={s2_id}"
            )
            summarize_imagery_quality(
                folha=folha,
                best_aster=best_aster,
                best_s2=best_s2,
            )
            if args.preview_top_k > 0:
                print(
                    f"[FULL PIPELINE] Gerando pré-visualizações top_k={args.preview_top_k} em {preview_dir}"
                )
                generate_search_previews(
                    folha=folha,
                    preview_dir=preview_dir,
                    preview_top_k=args.preview_top_k,
                    aster_candidates=aster_candidates if return_candidates else None,
                    s2_candidates=s2_candidates if return_candidates else None,
                    debug_cloud_masks=args.debug_cloud_masks,
                )
            print("[FULL PIPELINE] --search-only acionado; parando após busca e resumo de qualidade.")
            return

        if not args.skip_gs:
            return_candidates = args.preview_top_k > 0
            print(
                "[FULL PIPELINE] Chamando resolve_pair com: "
                f"folha={folha}, aster_id={args.aster_id}, s2_id={args.s2_id}, "
                f"aster_date={args.aster_date}, return_best=True, return_candidates={return_candidates}"
            )
            resolve_out = resolve_pair(
                folha=folha,
                aster_id=args.aster_id,
                s2_id=args.s2_id,
                aster_date=args.aster_date,
                max_local_cloud_aster=args.max_local_cloud_aster,
                max_global_cloud_aster=args.max_global_cloud_aster,
                aster_metrics_csv=aster_metrics_csv,
                return_best=True,
                return_candidates=return_candidates,
            )
            if return_candidates:
                (
                    aster_id,
                    s2_id,
                    best_aster,
                    best_s2,
                    aster_candidates,
                    s2_candidates,
                ) = resolve_out
            else:
                aster_id, s2_id, best_aster, best_s2 = resolve_out
            print(
                "[FULL PIPELINE] resolve_pair retornou: "
                f"ASTER={aster_id}, S2={s2_id}"
            )
            summarize_imagery_quality(
                folha=folha,
                best_aster=best_aster,
                best_s2=best_s2,
            )
            if args.preview_top_k > 0:
                print(
                    f"[FULL PIPELINE] Gerando pré-visualizações top_k={args.preview_top_k} em {preview_dir}"
                )
                generate_search_previews(
                    folha=folha,
                    preview_dir=preview_dir,
                    preview_top_k=args.preview_top_k,
                    aster_candidates=aster_candidates if return_candidates else None,
                    s2_candidates=s2_candidates if return_candidates else None,
                    debug_cloud_masks=args.debug_cloud_masks,
                )
            print(
                "[FULL PIPELINE] Chamando run_gs_and_supercube com: "
                f"folha={folha}, aster_id={aster_id}, s2_id={s2_id}, "
                f"orbital_dir={orbital_dir}"
            )
            super_cube, aster_gs_path, s2_stack_path, supercube_out_path = run_gs_and_supercube(
                folha=folha,
                aster_id=aster_id,
                s2_id=s2_id,
                orbital_dir=orbital_dir,
            )
            print(
                "[FULL PIPELINE] run_gs_and_supercube outputs: "
                f"s2_stack_path={s2_stack_path}, aster_gs_path={aster_gs_path}, "
                f"supercube_path={supercube_out_path}"
            )
            print(f"[FULL PIPELINE] Super-cubo gerado: shape={super_cube.values.shape}")
        else:
            print("[FULL PIPELINE] --skip-gs acionado; não será feito GS nem super-cubo.")
            print("[FULL PIPELINE] Assumindo que o super-cubo já existe em supercube_dir.")

        if args.skip_datasets:
            print("[FULL PIPELINE] --skip-datasets acionado; não serão gerados datasets.")
            return

        print(
            "[FULL PIPELINE] Chamando build_datasets com: "
            f"supercube_dir={args.supercube_dir}, max_samples_per_class={args.max_samples_per_class}, "
            f"patch_size={args.patch_size}, stride={args.stride}, "
            f"max_patches_per_class={args.max_patches_per_class}, "
            f"out_pixels={args.out_pixels}, out_patches={args.out_patches}"
        )
        dataset_stats = build_datasets(
            folha=folha,
            supercube_dir=args.supercube_dir,
            max_samples_per_class=args.max_samples_per_class,
            patch_size=args.patch_size,
            stride=args.stride,
            max_patches_per_class=args.max_patches_per_class,
            out_pixels=args.out_pixels,
            out_patches=args.out_patches,
        )
        print(
            "[FULL PIPELINE] build_datasets outputs: "
            f"pixels_path={dataset_stats['pixels_path']} (shape={dataset_stats['pixels_shape']}), "
            f"patches_path={dataset_stats['patches_path']} (shape={dataset_stats['patches_shape']}), "
            f"n_pixel_classes={dataset_stats['n_pixel_classes']}, "
            f"n_patch_classes={dataset_stats['n_patch_classes']}"
        )

if __name__ == "__main__":
    main()


# full_pipeline.py
from __future__ import annotations

import argparse
import os
from typing import Optional

import numpy as np
import xarray as xr

from config import ORBITAL_DIR
from stac_utils import item_datetime
from search_pair import (
    PairSelectionResult,
    SceneQuality,
    rank_scenes,
    evaluate_aster_candidates,
    evaluate_s2_candidates,
)
from gs_fusion import run_gs_pair_pipeline
from supercube import build_supercube, load_supercube
from labeling_lito import build_label_raster_for_folha
from dataset_pixels import extract_pixel_dataset
from dataset_patches import generate_patches
from log_utils import log_stdout
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
) -> PairSelectionResult:
    if aster_id and s2_id:
        print("[PAIR] Usando IDs fornecidos pelo usuário.")
        return PairSelectionResult(
            selected_aster=SceneQuality(
                id=aster_id,
                collection="aster-l1t",
                datetime=None,
                delta_days=None,
            ),
            selected_s2=SceneQuality(
                id=s2_id,
                collection="sentinel-2-l2a",
                datetime=None,
                delta_days=None,
            ),
            aster_candidates=[],
            s2_candidates=[],
        )

    if not aster_date:
        raise SystemExit(
            "Se --aster-id/--s2-id não forem fornecidos, é obrigatório informar --aster-date (YYYY-MM-DD)."
        )

    aster_candidates = evaluate_aster_candidates(
        codigo_folha=folha,
        aster_target_date_str=aster_date,
    )
    ranked_aster = rank_scenes(aster_candidates, max_local_cloud=0.02)
    if not ranked_aster:
        raise SystemExit("Nenhum ASTER adequado encontrado para essa folha/data.")

    best_aster = ranked_aster[0]
    aster_item = best_aster.item
    if aster_item is None:
        raise SystemExit("Item ASTER selecionado está ausente.")
    aster_dt = item_datetime(aster_item)
    print(
        f"[PAIR] ASTER selecionado: {best_aster.id} (Δt alvo={best_aster.delta_days} dias)"
    )

    s2_candidates = evaluate_s2_candidates(
        codigo_folha=folha,
        aster_datetime=aster_dt,
    )
    ranked_s2 = rank_scenes(s2_candidates, max_local_cloud=0.0)
    if not ranked_s2:
        raise SystemExit("Nenhum Sentinel-2 adequado encontrado para esse ASTER.")

    best_s2 = ranked_s2[0]
    print(
        f"[PAIR] S2 selecionado: {best_s2.id} (Δt ASTER={best_s2.delta_days} dias)"
    )

    return PairSelectionResult(
        selected_aster=best_aster,
        selected_s2=best_s2,
        aster_candidates=ranked_aster,
        s2_candidates=ranked_s2,
    )


def summarize_imagery_quality(
    folha: str,
    selection: PairSelectionResult,
) -> None:
    """Reporta frações de nodata/nuvem para aster e S2 recortados na folha.

    A geometria da folha é obtida diretamente do banco (via ``get_folha_geom_geojson``),
    e cada asset relevante é recortado com ``clip_raster_to_folha`` antes de medir
    ``nodata`` ou nuvens.
    """

    folha_geom = get_folha_geom_geojson(folha)
    print("\n[QUALITY] Avaliando qualidade das cenas selecionadas...")

    best_aster = selection.selected_aster
    best_s2 = selection.selected_s2

    if best_aster is None:
        print("[QUALITY][ASTER] Nenhum item ASTER disponível para avaliação.")
    else:
        aster_item = best_aster.item
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
        s2_item = best_s2.item
        if "SCL" not in s2_item.assets:
            print(f"[QUALITY][S2] Asset SCL ausente em {s2_item.id}; impossível medir nuvem.")
        else:
            scl_href = s2_item.assets["SCL"].href
            da_scl_clip = clip_raster_to_folha(scl_href, folha_geom)
            scl_nodata_frac, scl_cloud_frac, *_ = compute_scl_cloud_fraction(da_scl_clip)
            print(
                f"[QUALITY][S2] id={s2_item.id} | scl_cloud_frac={scl_cloud_frac:.4f} | "
                f"scl_nodata_frac={scl_nodata_frac:.4f} | meta_cloud={(best_s2.meta_cloud or 0.0):.2f}%"
            )


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

    log_dir = os.path.join(orbital_dir, "logs")
    base_name = f"full_pipeline_{folha}"

    with log_stdout(log_dir, base_name) as log_path:
        print("=" * 80)
        print(f"[FULL PIPELINE] Folha: {folha}")
        print(f"[FULL PIPELINE] Log em: {log_path}")
        print("=" * 80)

        if args.search_only:
            print(
                "[FULL PIPELINE] Chamando resolve_pair com: "
                f"folha={folha}, aster_id={args.aster_id}, s2_id={args.s2_id}, "
                f"aster_date={args.aster_date}"
            )
            selection = resolve_pair(
                folha=folha,
                aster_id=args.aster_id,
                s2_id=args.s2_id,
                aster_date=args.aster_date,
            )
            print(
                "[FULL PIPELINE] resolve_pair retornou: "
                f"ASTER={selection.selected_aster.id if selection.selected_aster else None}, "
                f"S2={selection.selected_s2.id if selection.selected_s2 else None}"
            )
            summarize_imagery_quality(
                folha=folha,
                selection=selection,
            )
            print("[FULL PIPELINE] --search-only acionado; parando após busca e resumo de qualidade.")
            return

        if not args.skip_gs:
            print(
                "[FULL PIPELINE] Chamando resolve_pair com: "
                f"folha={folha}, aster_id={args.aster_id}, s2_id={args.s2_id}, "
                f"aster_date={args.aster_date}"
            )
            selection = resolve_pair(
                folha=folha,
                aster_id=args.aster_id,
                s2_id=args.s2_id,
                aster_date=args.aster_date,
            )
            aster_id = selection.selected_aster.id if selection.selected_aster else None
            s2_id = selection.selected_s2.id if selection.selected_s2 else None
            print(
                "[FULL PIPELINE] resolve_pair retornou: "
                f"ASTER={aster_id}, S2={s2_id}"
            )
            summarize_imagery_quality(
                folha=folha,
                selection=selection,
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


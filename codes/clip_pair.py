from __future__ import annotations

import argparse
import os
from typing import Any, Dict, Tuple

import numpy as np
import matplotlib.pyplot as plt

from db_conn import get_folha_geom_geojson
from stac_utils import get_signed_item
from raster_utils import clip_raster_to_folha, compute_nodata_fraction
from config import ORBITAL_DIR


def process_aster_for_folha(
    folha_geom: Dict[str, Any],
    item: Any,
    out_dir: str,
    folha_codigo: str,
) -> Tuple[str, float]:
    print("\n[ASTER]")
    print(f"  id          : {item.id}")
    print(f"  cloud_cover : {item.properties.get('eo:cloud_cover')} %")
    print(f"  assets      : {list(item.assets.keys())}")

    if "VNIR" in item.assets:
        asset_key = "VNIR"
    else:
        asset_key = list(item.assets.keys())[0]
        print(f"  Asset 'VNIR' não encontrado, usando '{asset_key}'.")

    href = item.assets[asset_key].href
    da_clip = clip_raster_to_folha(href, folha_geom)
    frac_nodata, nodata_mask = compute_nodata_fraction(da_clip, return_mask=True)
    print(f"  Fração nodata ASTER: {frac_nodata:.4f}")

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

    out_path = os.path.join(
        out_dir,
        f"{folha_codigo}_ASTER_{item.id}_{asset_key}_clip.tif",
    )
    da_clip.rio.to_raster(out_path)
    print(f"  Recorte ASTER salvo em: {out_path}")
    return out_path, frac_nodata


def process_s2_for_folha(
    folha_geom: Dict[str, Any],
    item: Any,
    out_dir: str,
    folha_codigo: str,
) -> Tuple[str, float]:
    print("\n[SENTINEL-2]")
    print(f"  id          : {item.id}")
    print(f"  cloud_cover : {item.properties.get('eo:cloud_cover')} %")
    print(f"  assets      : {list(item.assets.keys())}")

    if "visual" in item.assets:
        visual_key = "visual"
    else:
        visual_key = list(item.assets.keys())[0]
        print(f"  Asset 'visual' não encontrado, usando '{visual_key}'.")

    href = item.assets[visual_key].href
    da_vis_clip = clip_raster_to_folha(href, folha_geom)
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

        import matplotlib.pyplot as plt

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

    out_path = os.path.join(
        out_dir,
        f"{folha_codigo}_S2_{item.id}_{visual_key}_clip.tif",
    )
    da_vis_clip.rio.to_raster(out_path)
    print(f"  Recorte S2 salvo em: {out_path}")
    return out_path, frac_nodata_vis


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--folha", required=True)
    parser.add_argument("--aster-collection", default="aster-l1t")
    parser.add_argument("--aster-id", required=True)
    parser.add_argument("--s2-collection", default="sentinel-2-l2a")
    parser.add_argument("--s2-id", required=True)
    parser.add_argument("--out-dir", default=ORBITAL_DIR)
    args = parser.parse_args()

    out_dir = args.out_dir
    os.makedirs(out_dir, exist_ok=True)

    folha_geom = get_folha_geom_geojson(args.folha)
    print(f"[CLIP PAIR] Geometria da folha '{args.folha}' carregada.")

    aster_item = get_signed_item(args.aster_collection, args.aster_id)
    s2_item = get_signed_item(args.s2_collection, args.s2_id)

    ast_path, ast_frac = process_aster_for_folha(
        folha_geom=folha_geom,
        item=aster_item,
        out_dir=out_dir,
        folha_codigo=args.folha,
    )
    s2_path, s2_frac = process_s2_for_folha(
        folha_geom=folha_geom,
        item=s2_item,
        out_dir=out_dir,
        folha_codigo=args.folha,
    )

    print("\n[CLIP PAIR] Concluído.")
    print(f"  ASTER: {ast_path} (nodata={ast_frac:.4f})")
    print(f"  S2   : {s2_path} (nodata={s2_frac:.4f})")


if __name__ == "__main__":
    from stac_utils import get_signed_item  # evitar import circular no topo
    main()

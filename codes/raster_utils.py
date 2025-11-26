from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import xarray as xr
import rioxarray
import requests

from config import PC_CACHE_DIR
from stac_utils import get_cloud_cover  # se quiser reutilizar aqui (opcional)


def download_pc_asset_to_local(
    href: str,
    cache_dir: Optional[str] = None,
) -> str:
    cache = cache_dir or PC_CACHE_DIR
    os.makedirs(cache, exist_ok=True)

    filename = href.split("/")[-1].split("?")[0]
    local_path = os.path.join(cache, filename)

    if os.path.exists(local_path):
        print(f"[PC] Usando cache local: {local_path}")
        return local_path

    print(f"[PC] Baixando asset: {local_path}")
    with requests.get(href, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(local_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=16 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
    return local_path


def _clip_raster_to_folha_direct(
    href: str,
    folha_geom_geojson: Dict[str, Any],
) -> xr.DataArray:
    da = rioxarray.open_rasterio(href, masked=True)
    da = da.where(da != 0)
    da_clip = da.rio.clip([folha_geom_geojson], crs="EPSG:4326", drop=True)
    return da_clip.astype("float32")


def clip_raster_to_folha(
    href: str,
    folha_geom_geojson: Dict[str, Any],
    cache_dir: Optional[str] = None,
) -> xr.DataArray:
    try:
        return _clip_raster_to_folha_direct(href, folha_geom_geojson)
    except Exception as e:
        print("[WARN] Falha ao ler raster remoto, fazendo download completo.")
        print(f"       href: {href}")
        print(f"       erro: {e}")
        local_path = download_pc_asset_to_local(href, cache_dir=cache_dir)
        return _clip_raster_to_folha_direct(local_path, folha_geom_geojson)


def compute_nodata_fraction(
    da: xr.DataArray,
    return_mask: bool = False,
) -> float | Tuple[float, np.ndarray]:
    arr = da.values
    if arr.ndim == 3:
        nodata_mask = np.all(np.isnan(arr), axis=0)
    elif arr.ndim == 2:
        nodata_mask = np.isnan(arr)
    else:
        raise ValueError("Dimensão inesperada em compute_nodata_fraction.")

    frac = float(nodata_mask.sum() / nodata_mask.size)
    if return_mask:
        return frac, nodata_mask
    return frac


def compute_scl_cloud_fraction(
    da_scl_clip: xr.DataArray,
) -> Tuple[float, float, np.ndarray, np.ndarray]:
    scl = da_scl_clip.values
    if scl.ndim == 3:
        scl = scl[0, :, :]

    scl = np.where(np.isnan(scl), 0, scl).astype("int16")
    total = scl.size

    nodata_frac = float(np.sum(scl == 0) / total)
    cloud_mask = np.isin(scl, [3, 8, 9, 10, 11])
    cloud_frac = float(np.sum(cloud_mask) / total)

    return nodata_frac, cloud_frac, scl, cloud_mask


def sanitize_long_name(da: xr.DataArray) -> xr.DataArray:
    long_name = da.attrs.get("long_name", None)
    n_bands = da.sizes.get("band", 1)

    if isinstance(long_name, (list, tuple)) and len(long_name) != n_bands:
        da = da.copy()
        da.attrs.pop("long_name", None)
    return da


def load_s2_bands_for_folha(
    item: Any,
    folha_geom: Dict[str, Any],
    band_ids: List[str],
    cache_dir: Optional[str] = None,
) -> Tuple[xr.DataArray, Dict[str, xr.DataArray]]:
    assets = item.assets
    if "B02" not in assets:
        raise RuntimeError("Asset B02 não encontrado no item Sentinel-2.")

    ref_href = assets["B02"].href
    ref_da = clip_raster_to_folha(ref_href, folha_geom, cache_dir=cache_dir)

    s2_bands: Dict[str, xr.DataArray] = {}
    for bname in band_ids:
        asset = assets.get(bname)
        if asset is None:
            print(f"[S2] Banda {bname} ausente no item.")
            continue
        da_b = clip_raster_to_folha(asset.href, folha_geom, cache_dir=cache_dir)
        da_b = da_b.rio.reproject_match(ref_da)
        s2_bands[bname] = da_b

    return ref_da, s2_bands


def load_aster_vnir_swir_for_folha(
    item: Any,
    folha_geom: Dict[str, Any],
    s2_ref_da: xr.DataArray,
    cache_dir: Optional[str] = None,
) -> xr.DataArray:
    assets = item.assets
    if "VNIR" not in assets:
        raise RuntimeError("Asset 'VNIR' não encontrado no item ASTER.")
    if "SWIR" not in assets:
        raise RuntimeError("Asset 'SWIR' não encontrado no item ASTER.")

    da_vnir = clip_raster_to_folha(assets["VNIR"].href, folha_geom, cache_dir=cache_dir)
    da_swir = clip_raster_to_folha(assets["SWIR"].href, folha_geom, cache_dir=cache_dir)

    da_vnir_match = da_vnir.rio.reproject_match(s2_ref_da)
    da_swir_match = da_swir.rio.reproject_match(s2_ref_da)

    aster_all = xr.concat([da_vnir_match, da_swir_match], dim="band")

    nb_vnir = da_vnir_match.sizes["band"]
    nb_swir = da_swir_match.sizes["band"]
    band_names = (
        [f"VNIR_{i+1}" for i in range(nb_vnir)] +
        [f"SWIR_{i+4}" for i in range(nb_swir)]
    )
    aster_all = aster_all.assign_coords(band=("band", band_names))
    aster_all = sanitize_long_name(aster_all)
    return aster_all


def quicklook_three_bands(
    da: xr.DataArray,
    bands_idx: Tuple[int, int, int] = (0, 1, 2),
    title: str = "",
) -> None:
    import matplotlib.pyplot as plt

    nb = da.sizes["band"]
    if max(bands_idx) >= nb:
        print("[Quicklook] Índices de bandas fora do intervalo, pulando.")
        return

    arr = da.isel(band=list(bands_idx)).values.astype("float32")
    valid = arr[np.isfinite(arr)]
    if valid.size == 0:
        print("[Quicklook] Nenhum pixel válido.")
        return

    vmin = np.nanpercentile(valid, 2)
    vmax = np.nanpercentile(valid, 98)
    scale = vmax - vmin if vmax > vmin else 1.0
    arr_norm = np.clip((arr - vmin) / scale, 0, 1)

    rgb = np.transpose(arr_norm, (1, 2, 0))

    plt.figure(figsize=(8, 8))
    plt.imshow(rgb)
    plt.title(title)
    plt.axis("off")
    plt.tight_layout()
    plt.show()

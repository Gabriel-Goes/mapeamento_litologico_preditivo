from __future__ import annotations

from typing import List, Tuple, Dict, Any

import numpy as np
import xarray as xr

from db_conn import get_folha_geom_geojson
from stac_utils import get_signed_item
from raster_utils import (
    sanitize_long_name,
    load_s2_bands_for_folha,
    load_aster_vnir_swir_for_folha,
    compute_nodata_fraction,
)
from config import ORBITAL_DIR


def ols_synthetic_pan(
    aster_ms: xr.DataArray,
    pan_da: xr.DataArray,
) -> Tuple[np.ndarray, np.ndarray]:
    ms = aster_ms.values
    pan = pan_da.values

    nb, ny, nx = ms.shape
    ms_flat = ms.reshape(nb, ny * nx).T
    pan_flat = pan.reshape(-1)

    mask = np.isfinite(pan_flat)
    for b in range(nb):
        mask &= np.isfinite(ms_flat[:, b])

    if mask.sum() < nb + 1:
        raise RuntimeError("Poucos píxeis válidos para OLS (ASTER vs PAN).")

    X = ms_flat[mask, :]
    y = pan_flat[mask]

    w, *_ = np.linalg.lstsq(X, y, rcond=None)
    pan_synth_flat = ms_flat @ w
    pan_synth = pan_synth_flat.reshape(ny, nx).astype("float32")

    return pan_synth, w.astype("float32")


def gs_forward(
    bands: List[np.ndarray],
) -> Tuple[List[np.ndarray], List[float], List[List[float]]]:
    n = len(bands)
    gs_list: List[np.ndarray] = []
    mu_list: List[float] = []
    phi: List[List[float]] = [[0.0] * n for _ in range(n)]

    for T in range(n):
        BT = bands[T].astype("float64")
        mu_T = float(np.nanmean(BT))
        BTc = BT - mu_T

        GST = BTc.copy()
        for l in range(T):
            GSl = gs_list[l]
            cov = np.nanmean((BT - mu_T) * GSl)
            var = np.nanmean(GSl * GSl)
            coeff = cov / var if (var not in (0, np.nan) and var != 0) else 0.0
            GST = GST - coeff * GSl
            phi[T][l] = float(coeff)

        gs_list.append(GST.astype("float32"))
        mu_list.append(mu_T)

    return gs_list, mu_list, phi


def gs_inverse(
    gs_list: List[np.ndarray],
    mu_list: List[float],
    phi: List[List[float]],
) -> List[np.ndarray]:
    n = len(gs_list)
    bands_rec: List[np.ndarray] = []

    for T in range(n):
        GST = gs_list[T].astype("float64")
        BT_rec = GST + mu_list[T]
        for l in range(T):
            BT_rec += phi[T][l] * gs_list[l]
        bands_rec.append(BT_rec.astype("float32"))

    return bands_rec


def gs_fusion_aster_with_pan(
    aster_ms: xr.DataArray,
    pan_da: xr.DataArray,
) -> xr.DataArray:
    pan_synth, _ = ols_synthetic_pan(aster_ms, pan_da)

    ms = aster_ms.values
    nb, ny, nx = ms.shape

    band_list: List[np.ndarray] = [pan_synth]
    for b in range(nb):
        band_list.append(ms[b, :, :])

    gs_list, mu_list, phi = gs_forward(band_list)

    pan_real = pan_da.values.astype("float32")
    gs0 = gs_list[0]

    pan_mean = float(np.nanmean(pan_real))
    gs0_mean = float(np.nanmean(gs0))
    pan_std = float(np.nanstd(pan_real))
    gs0_std = float(np.nanstd(gs0))

    if pan_std == 0 or np.isnan(pan_std):
        pan_adj = pan_real - pan_mean
    else:
        scale = gs0_std / pan_std if (gs0_std not in (0, np.nan) and gs0_std != 0) else 1.0
        pan_adj = (pan_real - pan_mean) * scale

    gs_list[0] = pan_adj.astype("float32")

    bands_rec = gs_inverse(gs_list, mu_list, phi)
    rec_aster = bands_rec[1:]
    arr_fused = np.stack(rec_aster, axis=0)

    aster_fused = xr.DataArray(
        data=arr_fused,
        dims=("band", "y", "x"),
        coords={
            "band": aster_ms.band,
            "y": aster_ms.y,
            "x": aster_ms.x,
        },
        attrs={**aster_ms.attrs},
    )
    aster_fused.rio.write_crs(aster_ms.rio.crs, inplace=True)
    aster_fused.rio.write_transform(aster_ms.rio.transform(), inplace=True)
    band_metadata = {**aster_ms.attrs.get("band_metadata", {})}
    for band_name in aster_fused.band.values:
        key = str(band_name)
        meta = band_metadata.get(key, {}).copy()
        meta.update(
            {
                "process": "Gram-Schmidt fusion (ASTER VNIR/SWIR upscaled using Sentinel-2 B08 as PAN)",
                "reference_band": str(pan_da.band.values[0] if "band" in pan_da.coords else "B08"),
            }
        )
        band_metadata[key] = meta
    aster_fused.attrs["band_metadata"] = band_metadata
    aster_fused.attrs.setdefault("long_name", list(aster_fused.band.values))
    aster_fused = sanitize_long_name(aster_fused)
    return aster_fused


def run_gs_pair_pipeline(
    folha_codigo: str,
    aster_collection: str,
    aster_id: str,
    s2_collection: str,
    s2_id: str,
    s2_band_ids: List[str],
    out_dir: str | None = None,
) -> Tuple[xr.DataArray, xr.DataArray, xr.DataArray]:
    import os

    out = out_dir or ORBITAL_DIR
    os.makedirs(out, exist_ok=True)

    folha_geom = get_folha_geom_geojson(folha_codigo)
    print(f"[GS PIPELINE] Folha {folha_codigo} carregada.")

    s2_item = get_signed_item(s2_collection, s2_id)
    print(f"[GS PIPELINE] S2 item: {s2_item.id}")

    s2_ref_da, s2_bands, _s2_meta = load_s2_bands_for_folha(
        item=s2_item,
        folha_geom=folha_geom,
        band_ids=s2_band_ids,
    )
    print(f"[GS PIPELINE] Bandas S2 carregadas: {list(s2_bands.keys())}")

    s2_stack_list = []
    s2_labels: List[str] = []
    s2_band_metadata: Dict[str, Any] = {}
    for bname in s2_band_ids:
        da_b = s2_bands.get(bname)
        if da_b is None:
            continue
        if "band" in da_b.dims and da_b.sizes.get("band", 1) == 1:
            arr = da_b.isel(band=0).values
        else:
            arr = da_b.values[0, :, :]
        s2_stack_list.append(arr)

        band_label = str(da_b.band.values[0]) if "band" in da_b.coords else bname
        s2_labels.append(band_label)
        s2_band_metadata[band_label] = da_b.attrs.get("band_metadata", {}).get(band_label, {})

    s2_stack = xr.DataArray(
        data=np.stack(s2_stack_list, axis=0),
        dims=("band", "y", "x"),
        coords={
            "band": s2_labels,
            "y": s2_ref_da.y,
            "x": s2_ref_da.x,
        },
        attrs={
            "description": "Sentinel-2 bands recortadas",
            "band_metadata": s2_band_metadata,
            "source_item": s2_item.id,
        },
    )
    s2_stack.rio.write_crs(s2_ref_da.rio.crs, inplace=True)
    s2_stack.rio.write_transform(s2_ref_da.rio.transform(), inplace=True)

    frac_nodata_s2 = compute_nodata_fraction(s2_stack)
    print(f"[GS PIPELINE] Fração média nodata S2: {frac_nodata_s2:.4f}")

    aster_item = get_signed_item(aster_collection, aster_id)
    print(f"[GS PIPELINE] ASTER item: {aster_item.id}")

    aster_ms = load_aster_vnir_swir_for_folha(
        item=aster_item,
        folha_geom=folha_geom,
        s2_ref_da=s2_ref_da,
    )
    frac_nodata_aster = compute_nodata_fraction(aster_ms)
    print(f"[GS PIPELINE] Fração média nodata ASTER: {frac_nodata_aster:.4f}")

    if "B08" not in s2_bands:
        raise RuntimeError("B08 não carregada; necessária como PAN.")

    da_B08 = s2_bands["B08"]
    if "band" in da_B08.dims and da_B08.sizes.get("band", 1) == 1:
        pan_da = da_B08.isel(band=0)
    else:
        pan_da = da_B08

    print("[GS PIPELINE] Iniciando fusão GS ASTER + S2 B08.")
    aster_fused = gs_fusion_aster_with_pan(aster_ms=aster_ms, pan_da=pan_da)
    print("[GS PIPELINE] Fusão concluída.")

    s2_out = os.path.join(out, f"{folha_codigo}_S2_{s2_id}_stack.tif")
    aster_ms_out = os.path.join(out, f"{folha_codigo}_ASTER_{aster_id}_VNIR_SWIR_10m.tif")
    aster_fused_out = os.path.join(out, f"{folha_codigo}_ASTER_{aster_id}_VNIR_SWIR_GS_10m.tif")

    s2_stack_sanit = sanitize_long_name(s2_stack)
    aster_ms_sanit = sanitize_long_name(aster_ms)
    aster_fused_sanit = sanitize_long_name(aster_fused)

    s2_stack_sanit.rio.to_raster(s2_out)
    aster_ms_sanit.rio.to_raster(aster_ms_out)
    aster_fused_sanit.rio.to_raster(aster_fused_out)

    print(f"[GS PIPELINE] S2 stack salvo em: {s2_out}")
    print(f"[GS PIPELINE] ASTER 10m salvo em: {aster_ms_out}")
    print(f"[GS PIPELINE] ASTER GS salvo em: {aster_fused_out}")

    return aster_ms_sanit, aster_fused_sanit, s2_stack_sanit

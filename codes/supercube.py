from __future__ import annotations

import json
import os
from typing import Optional

import numpy as np
import xarray as xr
import rioxarray

from raster_utils import sanitize_long_name
from config import ORBITAL_DIR


def build_supercube(
    folha_codigo: str,
    s2_stack_path: str,
    aster_gs_path: str,
    out_path: Optional[str] = None,
) -> xr.DataArray:
    s2_stack = rioxarray.open_rasterio(s2_stack_path, masked=True).astype("float32")
    aster_gs = rioxarray.open_rasterio(aster_gs_path, masked=True).astype("float32")
    aster_gs = aster_gs.rio.reproject_match(s2_stack)

    s2_names = [str(b) for b in s2_stack.band.values]
    aster_names = [str(b) for b in aster_gs.band.values]
    super_names = s2_names + aster_names

    super_cube = xr.concat([s2_stack, aster_gs], dim="band")
    super_cube = super_cube.assign_coords(band=("band", super_names))
    super_meta = {
        **s2_stack.attrs.get("band_metadata", {}),
        **aster_gs.attrs.get("band_metadata", {}),
    }
    super_cube.attrs["band_metadata"] = super_meta
    super_cube.attrs.setdefault("long_name", super_names)
    super_cube.rio.write_crs(s2_stack.rio.crs, inplace=True)
    super_cube.rio.write_transform(s2_stack.rio.transform(), inplace=True)

    arr = super_cube.values
    valid = np.isfinite(arr).all(axis=0)
    super_cube = super_cube.where(valid)

    super_cube = sanitize_long_name(super_cube)

    out = out_path or os.path.join(
        ORBITAL_DIR,
        f"{folha_codigo}_S2_ASTER_GS_supercube_10m.tif",
    )
    os.makedirs(os.path.dirname(out), exist_ok=True)
    super_cube.rio.to_raster(out)
    meta_path = f"{out}.meta.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(
            {
                "band_names": super_names,
                "band_metadata": super_meta,
                "sources": {
                    "s2_stack_path": s2_stack_path,
                    "aster_gs_path": aster_gs_path,
                },
            },
            f,
            indent=2,
            ensure_ascii=False,
        )
    print(f"[SUPERCUBE] Super-cubo salvo em: {out}")
    return super_cube


def load_supercube(
    folha_codigo: str,
    supercube_dir: Optional[str] = None,
) -> xr.DataArray:
    base = supercube_dir or ORBITAL_DIR
    path = os.path.join(
        base,
        f"{folha_codigo}_S2_ASTER_GS_supercube_10m.tif",
    )
    da = rioxarray.open_rasterio(path, masked=True).astype("float32")

    meta_path = f"{path}.meta.json"
    if os.path.exists(meta_path):
        with open(meta_path, "r", encoding="utf-8") as f:
            meta = json.load(f)
        band_names = meta.get("band_names")
        if band_names and len(band_names) == da.sizes.get("band", len(band_names)):
            da = da.assign_coords(band=("band", band_names))
        if "band_metadata" in meta:
            da.attrs["band_metadata"] = meta["band_metadata"]
    da = sanitize_long_name(da)
    return da

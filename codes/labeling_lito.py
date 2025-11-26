from __future__ import annotations

from typing import Tuple

import numpy as np
import xarray as xr
import geopandas as gpd
from rasterio.features import rasterize

from db_conn import get_litologia_100k_for_folha


def rasterize_litologia(
    gdf_lito: gpd.GeoDataFrame,
    reference_da: xr.DataArray,
    background_label: int = 0,
) -> np.ndarray:
    height = reference_da.sizes["y"]
    width = reference_da.sizes["x"]
    transform = reference_da.rio.transform()

    shapes = [
        (geom, int(label))
        for geom, label in zip(gdf_lito.geometry, gdf_lito["label"])
        if geom is not None
    ]

    label_raster = rasterize(
        shapes=shapes,
        out_shape=(height, width),
        transform=transform,
        fill=background_label,
        dtype="int32",
        all_touched=False,
    )
    return label_raster


def build_label_raster_for_folha(
    folha_codigo: str,
    reference_da: xr.DataArray,
    background_label: int = 0,
) -> Tuple[np.ndarray, gpd.GeoDataFrame]:
    gdf_lito = get_litologia_100k_for_folha(
        folha_codigo=folha_codigo,
        raster_crs=reference_da.rio.crs,
    )
    label_raster = rasterize_litologia(
        gdf_lito=gdf_lito,
        reference_da=reference_da,
        background_label=background_label,
    )
    return label_raster, gdf_lito

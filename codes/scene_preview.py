from __future__ import annotations

import os
from typing import Iterable, Tuple

import numpy as np
import rasterio
import rioxarray  # type: ignore
import xarray as xr


def _ensure_parent_dir(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def build_rgb_quicklook(
    da: xr.DataArray,
    bands_idx: Tuple[int, int, int] = (0, 1, 2),
    stretch_percentiles: Tuple[float, float] = (2.0, 98.0),
) -> np.ndarray:
    """Constrói um array RGB uint8 (H, W, 3) a partir de um DataArray.

    As bandas são selecionadas por índice e normalizadas pelo intervalo de
    percentis informado, com valores fora do range [vmin, vmax] truncados para
    destacar contraste rapidamente.
    """

    if da.ndim == 2:
        arr = da.expand_dims({"band": [0]}).values.astype("float32")
    else:
        arr = da.values.astype("float32")

    if arr.shape[0] < 3:
        raise ValueError("DataArray não possui bandas suficientes para RGB")

    selected = arr[list(bands_idx), :, :]
    valid = selected[np.isfinite(selected)]
    if valid.size == 0:
        return np.zeros((selected.shape[1], selected.shape[2], 3), dtype=np.uint8)

    vmin, vmax = np.nanpercentile(valid, stretch_percentiles)
    scale = vmax - vmin if vmax > vmin else 1.0
    selected_norm = np.clip((selected - vmin) / scale, 0, 1)

    rgb = np.transpose(selected_norm, (1, 2, 0))
    rgb_uint8 = (rgb * 255).round().astype("uint8")
    return rgb_uint8


def overlay_cloud_on_rgb(
    rgb: np.ndarray,
    mask: np.ndarray,
    color: Iterable[int] = (255, 0, 0),
    alpha: float = 0.4,
) -> np.ndarray:
    """Sobrepõe uma máscara booleana em um RGB uint8, colorindo pixels verdadeiros."""

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("RGB deve ter shape (H, W, 3)")

    overlay = rgb.astype("float32").copy()
    mask_bool = mask.astype(bool)
    color_arr = np.array(list(color), dtype="float32").reshape(1, 1, 3)
    overlay[mask_bool] = (
        (1 - alpha) * overlay[mask_bool] + alpha * color_arr
    )
    return overlay.clip(0, 255).astype("uint8")


def save_rgb_preview(rgb: np.ndarray, out_path: str) -> str:
    """Salva um array RGB uint8 em PNG usando rasterio."""

    if rgb.ndim != 3 or rgb.shape[2] != 3:
        raise ValueError("RGB deve ter shape (H, W, 3)")

    _ensure_parent_dir(out_path)
    height, width, _ = rgb.shape
    profile = {
        "driver": "PNG",
        "height": height,
        "width": width,
        "count": 3,
        "dtype": rasterio.uint8,
    }

    with rasterio.open(out_path, "w", **profile) as dst:
        for i in range(3):
            dst.write(rgb[:, :, i], i + 1)
    return out_path


def save_mask_preview(mask: np.ndarray, out_path: str) -> str:
    """Salva uma máscara booleana/0-1 em PNG (uint8) para depuração rápida."""

    if mask.ndim != 2:
        raise ValueError("Máscara deve ter duas dimensões (H, W)")

    _ensure_parent_dir(out_path)
    mask_uint8 = np.where(mask, 255, 0).astype("uint8")
    height, width = mask_uint8.shape
    profile = {
        "driver": "PNG",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": rasterio.uint8,
    }
    with rasterio.open(out_path, "w", **profile) as dst:
        dst.write(mask_uint8, 1)
    return out_path


__all__ = [
    "build_rgb_quicklook",
    "overlay_cloud_on_rgb",
    "save_rgb_preview",
    "save_mask_preview",
]

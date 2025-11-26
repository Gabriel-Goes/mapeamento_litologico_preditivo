from __future__ import annotations

from typing import Tuple

import numpy as np
import xarray as xr


def extract_pixel_dataset(
    super_cube: xr.DataArray,
    label_raster: np.ndarray,
    max_samples_per_class: int | None = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract per-pixel spectral vectors (X) and lithology labels (y) from a
    super-cube (bands, y, x) and a label raster (y, x).

    Pixels with label 0 or any non-finite values are discarded. When
    ``max_samples_per_class`` is provided, a balanced sampling per class is
    performed.
    """
    data = super_cube.values  # shape: (C, H, W)
    C, H, W = data.shape

    if label_raster.shape != (H, W):
        raise ValueError("label_raster e super_cube têm shapes incompatíveis.")

    labels_flat = label_raster.reshape(-1)  # (H*W,)
    data_flat = data.reshape(C, -1).T  # (H*W, C)

    mask = labels_flat != 0
    mask &= np.isfinite(data_flat).all(axis=1)

    X_all = data_flat[mask]
    y_all = labels_flat[mask]

    if max_samples_per_class is None:
        return X_all.astype("float32"), y_all.astype("int64")

    X_list = []
    y_list = []
    classes = np.unique(y_all)
    for cls in classes:
        idx_cls = np.where(y_all == cls)[0]
        if idx_cls.size == 0:
            continue
        if idx_cls.size > max_samples_per_class:
            idx_sel = np.random.choice(idx_cls, size=max_samples_per_class, replace=False)
        else:
            idx_sel = idx_cls
        X_list.append(X_all[idx_sel])
        y_list.append(y_all[idx_sel])

    X = np.vstack(X_list).astype("float32")
    y = np.concatenate(y_list).astype("int64")

    return X, y

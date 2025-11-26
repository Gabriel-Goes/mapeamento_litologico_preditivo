from __future__ import annotations

import numpy as np
import xarray as xr


def generate_patches(
    super_cube: xr.DataArray,
    label_raster: np.ndarray,
    patch_size: int = 32,
    stride: int = 16,
    max_patches_per_class: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Generate (N, C, patch_size, patch_size) patches and labels using the label of
    the central pixel. Patches containing NaNs or labels equal to 0 are skipped.
    When ``max_patches_per_class`` is set, balanced sampling per class is
    applied.
    """
    data = super_cube.values  # (C, H, W)
    C, H, W = data.shape

    if label_raster.shape != (H, W):
        raise ValueError("label_raster e super_cube têm shapes incompatíveis.")

    half = patch_size // 2
    patches: list[np.ndarray] = []
    labels: list[int] = []

    for cy in range(half, H - half, stride):
        for cx in range(half, W - half, stride):
            center_label = int(label_raster[cy, cx])
            if center_label == 0:
                continue

            patch = data[:, cy - half : cy + half, cx - half : cx + half]
            if not np.isfinite(patch).all():
                continue

            patches.append(patch)
            labels.append(center_label)

    if not patches:
        raise ValueError("Nenhum patch válido encontrado para os parâmetros fornecidos.")

    patches_arr = np.stack(patches, axis=0)  # (N, C, ps, ps)
    labels_arr = np.array(labels, dtype="int32")

    if max_patches_per_class is None:
        return patches_arr, labels_arr

    X_list = []
    y_list = []
    classes = np.unique(labels_arr)
    for cls in classes:
        idx_cls = np.where(labels_arr == cls)[0]
        if idx_cls.size == 0:
            continue
        if idx_cls.size > max_patches_per_class:
            idx_sel = np.random.choice(idx_cls, size=max_patches_per_class, replace=False)
        else:
            idx_sel = idx_cls
        X_list.append(patches_arr[idx_sel])
        y_list.append(labels_arr[idx_sel])

    X = np.concatenate(X_list, axis=0)
    y = np.concatenate(y_list, axis=0)

    return X, y

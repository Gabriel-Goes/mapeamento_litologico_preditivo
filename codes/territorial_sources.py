from __future__ import annotations

import json
from typing import Dict, Iterable, Mapping, Tuple

import numpy as np
import pandas as pd


def _ordered_grid_df(df: pd.DataFrame) -> pd.DataFrame:
    if {"E_utm", "N_utm"}.issubset(df.columns):
        out = df.copy()
    elif {"X", "Y"}.issubset(df.columns):
        out = df.rename(columns={"X": "E_utm", "Y": "N_utm"}).copy()
    else:
        raise ValueError("DataFrame sem colunas de coordenadas (E_utm/N_utm ou X/Y).")
    return out.sort_values(["N_utm", "E_utm"], ascending=[False, True], kind="mergesort", ignore_index=True)


def _reshape_col(df_ord: pd.DataFrame, col: str, ny: int, nx: int, default: float = 0.0) -> np.ndarray:
    if col not in df_ord.columns:
        return np.full((ny, nx), float(default), dtype="float64")
    vals = pd.to_numeric(df_ord[col], errors="coerce").to_numpy(dtype="float64")
    need = ny * nx
    if vals.size < need:
        pad = np.full((need - vals.size,), np.nan, dtype="float64")
        vals = np.concatenate([vals, pad], axis=0)
    vals = vals[:need]
    return vals.reshape(ny, nx)


def parse_restriction_specs(specs_text: str | None) -> Dict[str, object]:
    if not specs_text:
        return {}
    txt = str(specs_text).strip()
    if not txt:
        return {}
    try:
        obj = json.loads(txt)
    except Exception:
        return {}
    if not isinstance(obj, dict):
        return {}
    return obj


def build_slope_penalty_mask(
    df_ord: pd.DataFrame,
    ny: int,
    nx: int,
    slope_threshold_deg: float,
    slope_col: str = "slope",
    mdt_col: str = "MDT",
) -> np.ndarray:
    """Gera mascara de penalidade por declividade.

    Prioridade:
    1) Usa coluna explicita de slope (graus), se existir.
    2) Deriva slope de MDT por gradiente simples.
    """

    if slope_col in df_ord.columns:
        slope = _reshape_col(df_ord, slope_col, ny, nx, default=np.nan)
        return np.nan_to_num(slope, nan=0.0) >= float(slope_threshold_deg)

    if mdt_col not in df_ord.columns:
        return np.zeros((ny, nx), dtype=bool)

    z = _reshape_col(df_ord, mdt_col, ny, nx, default=np.nan)
    if not np.isfinite(z).any():
        return np.zeros((ny, nx), dtype=bool)

    # Preenche NaN com mediana para estabilizar gradiente.
    med = float(np.nanmedian(z)) if np.isfinite(np.nanmedian(z)) else 0.0
    zf = np.nan_to_num(z, nan=med)

    xs = np.sort(df_ord["E_utm"].dropna().unique())
    ys = np.sort(df_ord["N_utm"].dropna().unique())
    dx = float(np.median(np.diff(xs))) if xs.size > 1 else 1.0
    dy = float(np.median(np.diff(ys))) if ys.size > 1 else 1.0
    dx = 1.0 if not np.isfinite(dx) or abs(dx) < 1e-9 else abs(dx)
    dy = 1.0 if not np.isfinite(dy) or abs(dy) < 1e-9 else abs(dy)

    gy, gx = np.gradient(zf, dy, dx)
    slope_rad = np.arctan(np.sqrt(gx * gx + gy * gy))
    slope_deg = np.degrees(slope_rad)
    return slope_deg >= float(slope_threshold_deg)


def build_restriction_mask(
    df_ord: pd.DataFrame,
    ny: int,
    nx: int,
    restriction_cols: Iterable[str],
) -> np.ndarray:
    cols = [c for c in restriction_cols if c in df_ord.columns]
    if not cols:
        return np.zeros((ny, nx), dtype=bool)

    acc = np.zeros((ny, nx), dtype=bool)
    for c in cols:
        arr = _reshape_col(df_ord, c, ny, nx, default=0.0)
        acc |= np.nan_to_num(arr, nan=0.0) > 0
    return acc


def collect_masks_for_fids(
    quad: Mapping[str, Mapping[str, object]],
    layer: str,
    fids: Iterable[str],
    metas: Mapping[str, Mapping[str, object]],
    slope_threshold_deg: float = 25.0,
    restriction_cols: Iterable[str] | None = None,
    specs: Mapping[str, object] | None = None,
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, dict]]:
    """Coleta mascaras (restricao + penalidade) por folha, sem depender de QGIS."""

    specs = dict(specs or {})
    restriction_cols = list(restriction_cols or ["restricao", "restrito", "area_restrita", "uc_restricao"])
    if isinstance(specs.get("restriction_cols"), list):
        restriction_cols = [str(x) for x in specs.get("restriction_cols") if str(x).strip()]

    slope_col = str(specs.get("slope_col", "slope"))
    mdt_col = str(specs.get("mdt_col", "MDT"))

    restriction_masks: Dict[str, np.ndarray] = {}
    penalty_masks: Dict[str, np.ndarray] = {}
    diag: Dict[str, dict] = {}

    for fid in fids:
        meta = metas.get(fid, {})
        ny = int(meta.get("ny", 0) or 0)
        nx = int(meta.get("nx", 0) or 0)
        if ny <= 0 or nx <= 0:
            restriction_masks[fid] = np.zeros((1, 1), dtype=bool)
            penalty_masks[fid] = np.zeros((1, 1), dtype=bool)
            diag[fid] = {"warning": "shape_invalido"}
            continue

        blob = quad.get(fid, {})
        df = blob.get(layer)
        if not isinstance(df, pd.DataFrame) or df.empty:
            restriction_masks[fid] = np.zeros((ny, nx), dtype=bool)
            penalty_masks[fid] = np.zeros((ny, nx), dtype=bool)
            diag[fid] = {"warning": "sem_dataframe"}
            continue

        df_ord = _ordered_grid_df(df)

        rmask = build_restriction_mask(df_ord, ny, nx, restriction_cols)
        pmask = build_slope_penalty_mask(
            df_ord,
            ny,
            nx,
            slope_threshold_deg=float(slope_threshold_deg),
            slope_col=slope_col,
            mdt_col=mdt_col,
        )

        restriction_masks[fid] = rmask
        penalty_masks[fid] = pmask

        total = float(ny * nx) if ny * nx > 0 else 1.0
        diag[fid] = {
            "restriction_cols_used": [c for c in restriction_cols if c in df_ord.columns],
            "pct_restricao": float(rmask.sum() / total),
            "pct_penalidade_declividade": float(pmask.sum() / total),
            "slope_threshold_deg": float(slope_threshold_deg),
            "slope_col": slope_col if slope_col in df_ord.columns else None,
            "mdt_col": mdt_col if mdt_col in df_ord.columns else None,
        }

    return restriction_masks, penalty_masks, diag

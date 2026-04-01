from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Tuple

import numpy as np
import pandas as pd


# Pesos transparentes e auditaveis para o MVP de prioridade territorial.
DEFAULT_FEATURE_WEIGHTS: Dict[str, float] = {
    "KPERC": 0.30,
    "eTh": 0.25,
    "eU": 0.25,
    "CTCOR": 0.20,
}


@dataclass(frozen=True)
class PriorityThresholds:
    low: float = 0.40
    high: float = 0.70


def _minmax_norm(values: pd.Series) -> pd.Series:
    vmin = float(values.min())
    vmax = float(values.max())
    if not np.isfinite(vmin) or not np.isfinite(vmax) or vmax <= vmin:
        return pd.Series(np.full(values.shape[0], 0.5, dtype="float64"), index=values.index)
    return (values - vmin) / (vmax - vmin)


def compute_cluster_scores(
    df_long: pd.DataFrame,
    class_col: str = "classe",
    feature_weights: Mapping[str, float] | None = None,
) -> Tuple[Dict[int, float], pd.DataFrame]:
    """Calcula score [0,1] por cluster SOM usando medianas normalizadas e pesos."""

    if df_long is None or df_long.empty:
        raise ValueError("df_long vazio para calculo de score por cluster.")
    if class_col not in df_long.columns:
        raise ValueError(f"Coluna de classe ausente: {class_col}")

    feature_weights = dict(feature_weights or DEFAULT_FEATURE_WEIGHTS)
    feats = [f for f in feature_weights.keys() if f in df_long.columns]
    if not feats:
        raise ValueError(
            "Nenhuma feature ponderada disponivel no dataframe. "
            f"Esperadas: {list(feature_weights.keys())}"
        )

    grouped = df_long.groupby(class_col, dropna=True)
    med = grouped[feats].median(numeric_only=True)

    # Renormaliza pesos para as features realmente disponiveis.
    weight_sum = float(sum(feature_weights[f] for f in feats))
    norm_w = {f: float(feature_weights[f]) / weight_sum for f in feats}

    score_df = pd.DataFrame(index=med.index)
    score_df["class_id"] = score_df.index.astype(int)

    partial_cols = []
    for feat in feats:
        ncol = f"{feat}_norm"
        pcol = f"{feat}_weighted"
        score_df[ncol] = _minmax_norm(med[feat])
        score_df[pcol] = score_df[ncol] * float(norm_w[feat])
        partial_cols.append(pcol)

    score_df["score_potencial"] = score_df[partial_cols].sum(axis=1)
    score_df["score_potencial"] = score_df["score_potencial"].clip(lower=0.0, upper=1.0)

    out = {
        int(cls): float(score_df.loc[cls, "score_potencial"])
        for cls in score_df.index
    }
    return out, score_df.reset_index(drop=True)


def build_priority_maps(
    classes_by_fid: Mapping[str, np.ndarray],
    cluster_scores: Mapping[int, float],
    restriction_masks: Mapping[str, np.ndarray] | None = None,
    penalty_masks: Mapping[str, np.ndarray] | None = None,
    penalty_value: float = 0.25,
    thresholds: PriorityThresholds | None = None,
) -> Tuple[Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, np.ndarray], Dict[str, Dict[str, float]]]:
    """Gera mapas potencial/final/classes e metricas agregadas por folha.

    Classes de saida (uint8):
      1 = Restrita
      2 = Baixa
      3 = Media
      4 = Alta
    """

    thresholds = thresholds or PriorityThresholds()
    restriction_masks = restriction_masks or {}
    penalty_masks = penalty_masks or {}

    potential_maps: Dict[str, np.ndarray] = {}
    final_maps: Dict[str, np.ndarray] = {}
    class_maps: Dict[str, np.ndarray] = {}
    metrics: Dict[str, Dict[str, float]] = {}

    for fid, classes in classes_by_fid.items():
        arr = np.asarray(classes)
        if arr.ndim != 2:
            raise ValueError(f"Mapa de classes invalido para {fid}: shape={arr.shape}")

        # Lookup vetorizado de score por cluster.
        score = np.vectorize(lambda c: cluster_scores.get(int(c), 0.0), otypes=["float64"])(arr)
        score = np.nan_to_num(score, nan=0.0, posinf=1.0, neginf=0.0)
        score = np.clip(score, 0.0, 1.0)

        rmask = np.asarray(restriction_masks.get(fid, np.zeros_like(arr, dtype=bool)), dtype=bool)
        pmask = np.asarray(penalty_masks.get(fid, np.zeros_like(arr, dtype=bool)), dtype=bool)
        if rmask.shape != arr.shape:
            rmask = np.zeros_like(arr, dtype=bool)
        if pmask.shape != arr.shape:
            pmask = np.zeros_like(arr, dtype=bool)

        final = np.clip(score - (float(penalty_value) * pmask.astype("float64")), 0.0, 1.0)

        cls = np.where(final >= float(thresholds.high), 4, np.where(final >= float(thresholds.low), 3, 2)).astype("uint8")
        cls[rmask] = 1

        potential_maps[fid] = score.astype("float32")
        final_maps[fid] = final.astype("float32")
        class_maps[fid] = cls

        total = float(arr.size) if arr.size else 1.0
        metrics[fid] = {
            "pixels_total": float(arr.size),
            "pct_restrita": float((cls == 1).sum() / total),
            "pct_baixa": float((cls == 2).sum() / total),
            "pct_media": float((cls == 3).sum() / total),
            "pct_alta": float((cls == 4).sum() / total),
            "score_medio_potencial": float(np.nanmean(score)),
            "score_medio_final": float(np.nanmean(final)),
        }

    return potential_maps, final_maps, class_maps, metrics


def summarize_feature_weights(feature_weights: Mapping[str, float], available_features: Iterable[str]) -> Dict[str, float]:
    """Retorna pesos normalizados para as features disponiveis."""

    avail = [f for f in feature_weights.keys() if f in set(available_features)]
    if not avail:
        return {}
    s = float(sum(float(feature_weights[f]) for f in avail))
    if s <= 0:
        w = 1.0 / float(len(avail))
        return {f: w for f in avail}
    return {f: float(feature_weights[f]) / s for f in avail}

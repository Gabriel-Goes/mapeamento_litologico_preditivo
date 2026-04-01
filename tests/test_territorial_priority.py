from __future__ import annotations

import pathlib
import sys

import numpy as np
import pandas as pd

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
CODES_DIR = REPO_ROOT / "codes"
if str(CODES_DIR) not in sys.path:
    sys.path.insert(0, str(CODES_DIR))

from territorial_priority import PriorityThresholds, build_priority_maps, compute_cluster_scores
from territorial_sources import build_slope_penalty_mask


def test_compute_cluster_scores_outputs_unit_interval() -> None:
    df = pd.DataFrame(
        {
            "classe": [0, 0, 1, 1, 2, 2],
            "KPERC": [1.0, 1.2, 5.0, 4.8, 2.0, 2.1],
            "eTh": [1.5, 1.6, 2.8, 2.7, 2.0, 2.1],
            "eU": [0.8, 0.9, 3.1, 3.0, 1.8, 1.7],
            "CTCOR": [10.0, 10.2, 30.0, 29.0, 15.0, 14.0],
        }
    )
    scores, table = compute_cluster_scores(df)

    assert set(scores.keys()) == {0, 1, 2}
    assert len(table) == 3
    for val in scores.values():
        assert 0.0 <= float(val) <= 1.0


def test_build_priority_maps_applies_restriction_and_thresholds() -> None:
    classes_by_fid = {
        "F1": np.array(
            [
                [0, 1],
                [2, 0],
            ],
            dtype=np.int32,
        )
    }
    cluster_scores = {0: 0.80, 1: 0.50, 2: 0.20}
    restriction_masks = {"F1": np.array([[False, True], [False, False]], dtype=bool)}
    penalty_masks = {"F1": np.array([[False, False], [True, False]], dtype=bool)}

    pot, final, cls, metrics = build_priority_maps(
        classes_by_fid=classes_by_fid,
        cluster_scores=cluster_scores,
        restriction_masks=restriction_masks,
        penalty_masks=penalty_masks,
        penalty_value=0.25,
        thresholds=PriorityThresholds(low=0.40, high=0.70),
    )

    assert pot["F1"].shape == (2, 2)
    assert final["F1"].shape == (2, 2)
    assert cls["F1"].shape == (2, 2)

    # Restrita sobrescreve classe final.
    assert cls["F1"][0, 1] == 1
    # Classe 0 com score 0.8 deve ser alta (4).
    assert cls["F1"][0, 0] == 4
    # Classe 2 com score 0.2 e penalidade deve cair para baixa (2).
    assert cls["F1"][1, 0] == 2

    assert 0.0 <= metrics["F1"]["pct_alta"] <= 1.0
    assert 0.0 <= metrics["F1"]["pct_restrita"] <= 1.0


def test_build_slope_penalty_mask_from_mdt() -> None:
    # Grade 2x2 com forte gradiente no eixo x.
    df = pd.DataFrame(
        {
            "E_utm": [0.0, 1.0, 0.0, 1.0],
            "N_utm": [1.0, 1.0, 0.0, 0.0],
            "MDT": [0.0, 10.0, 0.0, 10.0],
        }
    ).sort_values(["N_utm", "E_utm"], ascending=[False, True], kind="mergesort", ignore_index=True)

    mask = build_slope_penalty_mask(df_ord=df, ny=2, nx=2, slope_threshold_deg=60.0)
    assert mask.shape == (2, 2)
    assert bool(mask.any())

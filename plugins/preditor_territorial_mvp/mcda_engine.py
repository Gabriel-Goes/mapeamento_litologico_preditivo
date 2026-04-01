from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable
import unicodedata

import numpy as np

try:
    import geopandas as gpd
except Exception as exc:  # pragma: no cover
    gpd = None
    _GPD_IMPORT_ERROR = exc
else:
    _GPD_IMPORT_ERROR = None


ProgressCb = Callable[[float, str], None] | None

GRAPHITE_PATTERNS = ("grafit", "graphite")

LITHO_GRAPHITE_PATTERNS = (
    "grafit",
    "graphite",
    "carbon",
)

LITHO_FAVORABLE_PATTERNS = (
    "granulit",
    "metassed",
    "metapelit",
    "gneiss",
    "xisto",
    "schist",
    "quartz",
    "paragnaiss",
)

LITHO_TEXT_FIELDS = (
    "LITOTIPOS",
    "NOME",
    "SIGLA",
    "LEGENDA",
    "DESCRICAO",
)

OCCURRENCE_TEXT_FIELDS = (
    "SUBSTANCIA",
    "DESCRICAO",
    "ROCHAS",
    "ROCHAS_HOS",
    "ROCHAS_ENC",
    "TIPOS_ALTE",
    "CLASSES_UT",
    "TOPONIMIA",
)


@dataclass(frozen=True)
class McdaResult:
    folha_codigo: str
    epsg: int
    pixel_size_m: int
    geotransform: tuple[float, float, float, float, float, float]
    potential: np.ndarray
    restriction: np.ndarray
    priority: np.ndarray
    metadata: dict


def _require_geopandas() -> None:
    if gpd is None:
        raise RuntimeError(
            "geopandas nao esta disponivel no ambiente Python atual. "
            f"Erro original: {_GPD_IMPORT_ERROR}"
        )


def _emit(progress_cb: ProgressCb, value: float, message: str) -> None:
    if callable(progress_cb):
        progress_cb(float(value), str(message))


def _normalize_text(value: str) -> str:
    txt = unicodedata.normalize("NFKD", str(value or ""))
    txt = txt.encode("ascii", "ignore").decode("ascii")
    return txt.lower().strip()


def score_lithology_text(text: str) -> float:
    txt = _normalize_text(text)
    if not txt:
        return np.nan
    if any(p in txt for p in LITHO_GRAPHITE_PATTERNS):
        return 1.0
    if any(p in txt for p in LITHO_FAVORABLE_PATTERNS):
        return 0.7
    return 0.2


def gaussian_distance_score(dist_m: np.ndarray, sigma_m: float = 2000.0) -> np.ndarray:
    sigma = max(float(sigma_m), 1.0)
    d = np.asarray(dist_m, dtype="float64")
    score = np.exp(-0.5 * (d / sigma) ** 2)
    return np.clip(score, 0.0, 1.0)


def classify_priority(
    potential: np.ndarray,
    restricted_mask: np.ndarray,
    low: float = 0.40,
    high: float = 0.70,
) -> np.ndarray:
    arr = np.asarray(potential, dtype="float64")
    restricted = np.asarray(restricted_mask, dtype=bool)

    cls = np.where(arr >= float(high), 4, np.where(arr >= float(low), 3, 2)).astype("uint8")
    cls[restricted] = 1
    return cls


def _is_graphite_occurrence(row: dict) -> bool:
    pieces: list[str] = []
    for field in OCCURRENCE_TEXT_FIELDS:
        if field in row:
            pieces.append(str(row.get(field, "")))
    txt = _normalize_text(" ".join(pieces))
    if not txt:
        return False
    return any(p in txt for p in GRAPHITE_PATTERNS)


def _safe_epsg(value: object, fallback: int = 4326) -> int:
    try:
        epsg = int(str(value).strip())
        if epsg > 0:
            return epsg
    except Exception:
        pass
    return int(fallback)


def list_available_folhas(gpkg_path: str | Path, layer: str = "mc_100k") -> list[str]:
    _require_geopandas()
    gpkg = Path(gpkg_path)
    if not gpkg.is_file():
        raise FileNotFoundError(f"GPKG nao encontrado: {gpkg}")

    mc = gpd.read_file(gpkg, layer=layer)
    if "id_folha" not in mc.columns:
        return []
    ids = mc["id_folha"].astype(str).str.strip().tolist()
    return sorted({i for i in ids if i})


def _build_grid_points(minx: float, miny: float, maxx: float, maxy: float, pixel: float):
    half = 0.5 * pixel
    if (maxx - minx) <= pixel:
        xs = np.array([(minx + maxx) * 0.5], dtype="float64")
    else:
        xs = np.arange(minx + half, maxx, pixel, dtype="float64")

    if (maxy - miny) <= pixel:
        ys = np.array([(miny + maxy) * 0.5], dtype="float64")
    else:
        ys = np.arange(maxy - half, miny, -pixel, dtype="float64")

    xx, yy = np.meshgrid(xs, ys)
    rows = np.repeat(np.arange(yy.shape[0], dtype="int32"), yy.shape[1])
    cols = np.tile(np.arange(xx.shape[1], dtype="int32"), yy.shape[0])
    return xx, yy, rows, cols


def _join_lithology_scores(points_valid, litologia_utm) -> np.ndarray:
    if litologia_utm.empty:
        return np.full(len(points_valid), np.nan, dtype="float32")

    text_cols = [c for c in LITHO_TEXT_FIELDS if c in litologia_utm.columns]
    if not text_cols:
        return np.full(len(points_valid), np.nan, dtype="float32")

    layer = litologia_utm[text_cols + ["geometry"]].copy()
    joined = gpd.sjoin(points_valid, layer, how="left", predicate="within")
    if joined.empty:
        return np.full(len(points_valid), np.nan, dtype="float32")

    def _score_row(row) -> float:
        vals: list[str] = []
        for col in text_cols:
            val = row.get(col, "")
            if val is None:
                continue
            # gpd.sjoin retorna NaN em linhas sem interseccao; isso deve virar area restrita.
            if isinstance(val, float) and np.isnan(val):
                continue
            vals.append(str(val))
        return score_lithology_text(" ".join(vals))

    joined["_lito_score"] = joined.apply(_score_row, axis=1)

    grouped = joined.groupby(joined.index)["_lito_score"].max()
    scores = np.full(len(points_valid), np.nan, dtype="float32")

    idx_lookup = {idx: i for i, idx in enumerate(points_valid.index.tolist())}
    for idx, score in grouped.items():
        pos = idx_lookup.get(idx)
        if pos is not None:
            scores[pos] = np.float32(score)
    return scores


def _occurrence_scores(points_valid, ocorr_utm, sigma_m: float) -> np.ndarray:
    if ocorr_utm.empty:
        return np.zeros(len(points_valid), dtype="float32")

    geom_series = ocorr_utm.geometry
    union_geom = geom_series.union_all() if hasattr(geom_series, "union_all") else geom_series.unary_union
    distances = points_valid.geometry.distance(union_geom).to_numpy(dtype="float64")
    scores = gaussian_distance_score(distances, sigma_m=sigma_m)
    return scores.astype("float32")


def run_mcda_from_gpkg(
    gpkg_path: str | Path,
    folha_codigo: str,
    pixel_size_m: int = 200,
    low_threshold: float = 0.40,
    high_threshold: float = 0.70,
    sigma_distance_m: float = 2000.0,
    lithology_weight: float = 0.60,
    occurrence_weight: float = 0.40,
    progress_cb: ProgressCb = None,
) -> McdaResult:
    _require_geopandas()

    gpkg = Path(gpkg_path)
    if not gpkg.is_file():
        raise FileNotFoundError(f"GPKG nao encontrado: {gpkg}")

    pixel_size_m = int(pixel_size_m)
    if pixel_size_m <= 0:
        raise ValueError("pixel_size_m deve ser positivo")

    _emit(progress_cb, 5, "Lendo camada de folhas")
    mc = gpd.read_file(gpkg, layer="mc_100k")
    if "id_folha" not in mc.columns:
        raise RuntimeError("Camada mc_100k sem coluna id_folha")

    folha_sel = mc.loc[mc["id_folha"].astype(str).str.strip() == str(folha_codigo).strip()].copy()
    if folha_sel.empty:
        raise RuntimeError(f"Folha nao encontrada no GPKG: {folha_codigo}")

    folha_sel = folha_sel.head(1)
    epsg = _safe_epsg(folha_sel.iloc[0].get("EPSG"), fallback=4326)

    folha_wgs = folha_sel.to_crs(epsg=4326)
    folha_utm = folha_sel.to_crs(epsg=epsg)
    folha_poly_utm = folha_utm.geometry.iloc[0]

    minx, miny, maxx, maxy = folha_poly_utm.bounds

    _emit(progress_cb, 15, "Montando grade de pontos")
    xx, yy, rows, cols = _build_grid_points(minx, miny, maxx, maxy, float(pixel_size_m))

    points = gpd.GeoDataFrame(
        {
            "row": rows,
            "col": cols,
        },
        geometry=gpd.points_from_xy(xx.ravel(), yy.ravel()),
        crs=f"EPSG:{epsg}",
    )

    inside_mask = points.geometry.apply(folha_poly_utm.covers).to_numpy(dtype=bool)
    points_valid = points.loc[inside_mask].copy()

    _emit(progress_cb, 30, "Lendo e filtrando litologia")
    litologia = gpd.read_file(gpkg, layer="litologia_100k")
    if litologia.crs is None:
        litologia = litologia.set_crs(epsg=4326)
    litologia = litologia.loc[litologia.geometry.notnull()].copy()
    litologia = gpd.clip(litologia.to_crs(epsg=4326), folha_wgs)
    litologia_utm = litologia.to_crs(epsg=epsg) if not litologia.empty else litologia

    lito_scores = _join_lithology_scores(points_valid, litologia_utm)

    _emit(progress_cb, 50, "Lendo e filtrando ocorrencias")
    ocorr = gpd.read_file(gpkg, layer="ocorr_min_cprm")
    if ocorr.crs is None:
        ocorr = ocorr.set_crs(epsg=4326)
    ocorr = ocorr.loc[ocorr.geometry.notnull()].copy()
    ocorr = gpd.clip(ocorr.to_crs(epsg=4326), folha_wgs) if not ocorr.empty else ocorr
    occ_total_in_folha = int(len(ocorr))
    occ_mode = "graphite_only"

    if not ocorr.empty:
        occ_mask = ocorr.apply(lambda row: _is_graphite_occurrence(row.to_dict()), axis=1)
        ocorr_graphite = ocorr.loc[occ_mask].copy()
        if ocorr_graphite.empty:
            # Fallback para manter o MVP funcional mesmo quando o atributo mineral nao esta padronizado.
            occ_mode = "all_minerals_fallback"
            ocorr = ocorr.copy()
        else:
            ocorr = ocorr_graphite

    ocorr_utm = ocorr.to_crs(epsg=epsg) if not ocorr.empty else ocorr

    _emit(progress_cb, 65, "Calculando score de ocorrencia por distancia")
    occ_scores = _occurrence_scores(points_valid, ocorr_utm, sigma_m=sigma_distance_m)

    _emit(progress_cb, 80, "Combinando criterios MCDA")
    weight_sum = max(float(lithology_weight) + float(occurrence_weight), 1e-9)
    w_l = float(lithology_weight) / weight_sum
    w_o = float(occurrence_weight) / weight_sum

    restricted_valid = np.isnan(lito_scores)
    potential_valid = np.full(len(points_valid), np.nan, dtype="float32")
    val_mask = ~restricted_valid
    if val_mask.any():
        potential_valid[val_mask] = (
            w_l * lito_scores[val_mask].astype("float32")
            + w_o * occ_scores[val_mask].astype("float32")
        )

    ny, nx = yy.shape
    potential = np.full((ny, nx), np.nan, dtype="float32")
    restriction = np.zeros((ny, nx), dtype="uint8")
    priority = np.zeros((ny, nx), dtype="uint8")

    inside_positions = np.flatnonzero(inside_mask)
    flat_rows = rows[inside_positions]
    flat_cols = cols[inside_positions]

    potential[flat_rows, flat_cols] = potential_valid
    restriction[flat_rows, flat_cols] = restricted_valid.astype("uint8")

    priority_valid = classify_priority(
        np.nan_to_num(potential_valid, nan=0.0),
        restricted_valid,
        low=low_threshold,
        high=high_threshold,
    )
    priority[flat_rows, flat_cols] = priority_valid.astype("uint8")

    geotransform = (
        float(xx.min() - 0.5 * pixel_size_m),
        float(pixel_size_m),
        0.0,
        float(yy.max() + 0.5 * pixel_size_m),
        0.0,
        -float(pixel_size_m),
    )

    metadata = {
        "folha_codigo": str(folha_codigo),
        "epsg": int(epsg),
        "pixel_size_m": int(pixel_size_m),
        "threshold_low": float(low_threshold),
        "threshold_high": float(high_threshold),
        "sigma_distance_m": float(sigma_distance_m),
        "weights": {
            "lithology": float(w_l),
            "occurrence": float(w_o),
        },
        "grid": {
            "nx": int(nx),
            "ny": int(ny),
            "inside_cells": int(inside_mask.sum()),
            "restricted_cells": int(restriction.sum()),
        },
        "inputs": {
            "gpkg": str(gpkg),
            "litologia_features": int(len(litologia_utm)),
            "ocorrencias_total_in_folha": int(occ_total_in_folha),
            "ocorrencias_features": int(len(ocorr_utm)),
            "occurrence_mode": occ_mode,
        },
    }

    _emit(progress_cb, 100, "MCDA finalizado")
    return McdaResult(
        folha_codigo=str(folha_codigo),
        epsg=int(epsg),
        pixel_size_m=int(pixel_size_m),
        geotransform=geotransform,
        potential=potential,
        restriction=restriction,
        priority=priority,
        metadata=metadata,
    )

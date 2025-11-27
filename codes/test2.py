#!/usr/bin/env python
from typing import Optional

import ee
from shapely import wkt
import os


# Coleções no Earth Engine
ASTER_COL = "ASTER/AST_L1T_003"
# Banda QA do ASTER L1T (bits de qualidade, incluindo flag de nuvem/sombra)
ASTER_CLOUD_MASK_BAND = "QA"

EE_PROJECT = os.environ.get("EE_PROJECT", None)


def init_ee():
    if EE_PROJECT:
        ee.Initialize(project=EE_PROJECT)
    else:
        ee.Initialize()


def wkt_to_ee_geometry(wkt_geom: str) -> ee.Geometry:
    geom = wkt.loads(wkt_geom)
    return ee.Geometry(geom.__geo_interface__)


def add_metrics(
    img: ee.Image,
    aoi: ee.Geometry,
    min_coverage: float,
    target_date: Optional[ee.Date],
):
    aoi_area = aoi.area()

    geom = img.geometry()
    inter = geom.intersection(aoi, ee.ErrorMargin(1))
    inter_area = inter.area()
    coverage = inter_area.divide(aoi_area)

    img = img.set("coverage_aoi", coverage)

    qa = img.select(ASTER_CLOUD_MASK_BAND)
    cloud_mask = qa.gt(0).rename("cloud_mask").unmask(0)

    native_scale = qa.projection().nominalScale()
    cloud_stats = cloud_mask.reduceRegion(
        reducer=ee.Reducer.sum().combine(ee.Reducer.count(), "", True),
        geometry=aoi,
        scale=native_scale,
        maxPixels=1e9,
        tileScale=4,
    )

    cloud_count = ee.Number(cloud_stats.get("cloud_mask_sum"))
    pixel_count = ee.Number(cloud_stats.get("cloud_mask_count"))
    cloud_fraction = ee.Algorithms.If(
        pixel_count.gt(0),
        cloud_count.divide(pixel_count),
        None,
    )

    img = img.set(
        {
            "cloud_count_aoi": cloud_count,
            "pixel_count_aoi": pixel_count,
            "cloud_fraction_aoi": cloud_fraction,
        }
    )

    if target_date:
        delta_days = img.date().difference(target_date, "day").abs()
        img = img.set("delta_days_target", delta_days)

    # aplica filtro de cobertura mínima
    img = ee.Image(
        ee.Algorithms.If(
            coverage.gte(min_coverage),
            img,
            None,
        )
    )
    return img


def find_aster_with_local_cloud(
    wkt_geom: str,
    start_date: str = "2000-01-01",
    end_date: str = "2025-12-31",
    min_coverage: float = 0.95,
    max_results: int = 50,
    target_date: Optional[str] = None,
):
    init_ee()

    aoi = wkt_to_ee_geometry(wkt_geom)

    aster_ic = (
        ee.ImageCollection(ASTER_COL)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )

    target_date_ee = ee.Date(target_date) if target_date else None

    def _map_fn(img):
        return add_metrics(img, aoi, min_coverage, target_date_ee)

    aster_with_metrics = aster_ic.map(_map_fn).filter(
        ee.Filter.notNull(["cloud_fraction_aoi", "cloud_count_aoi", "pixel_count_aoi"])
    )

    # Ordena por nuvem na folha (↑), prioridade a zero nuvem, e proximidade temporal (↑)
    if target_date_ee:
        aster_sorted = (
            aster_with_metrics.sort("cloud_count_aoi")
            .sort("delta_days_target")
            .sort("coverage_aoi", False)
        )
    else:
        aster_sorted = aster_with_metrics.sort("cloud_count_aoi").sort(
            "coverage_aoi", False
        )

    lst = aster_sorted.toList(max_results)
    size = lst.size().getInfo()

    results = []
    for i in range(size):
        img = ee.Image(lst.get(i))
        props = img.toDictionary(
            [
                "system:index",
                "system:time_start",
                "cloud_fraction_aoi",
                "cloud_count_aoi",
                "pixel_count_aoi",
                "delta_days_target",
                "coverage_aoi",
            ]
        ).getInfo()

        delta_days = props.get("delta_days_target")
        cloud_count = float(props["cloud_count_aoi"])
        pixel_count = float(props["pixel_count_aoi"])
        cloud_fraction = float(props["cloud_fraction_aoi"])

        results.append(
            {
                "id": props["system:index"],
                "datetime": ee.Date(props["system:time_start"])
                .format("YYYY-MM-dd HH:mm:ss")
                .getInfo(),
                "cloud_fraction_aoi": cloud_fraction,
                "cloud_count_aoi": cloud_count,
                "pixel_count_aoi": pixel_count,
                "delta_days": float(delta_days) if delta_days is not None else None,
                "coverage_aoi": float(props["coverage_aoi"]),
            }
        )

    def _sort_key(row):
        delta = row.get("delta_days")
        delta_val = delta if delta is not None else float("inf")
        return (
            row["cloud_count_aoi"],
            delta_val,
            -row["coverage_aoi"],
        )

    results_sorted = sorted(results, key=_sort_key)
    return results_sorted


if __name__ == "__main__":
    # Folha exemplo SB21_ZA_II2_NE
    wkt_geom = (
        "Polygon ((-56.125 -6, -56 -6, -56 -6.125, "
        "-56.125 -6.125, -56.125 -6))"
    )

    start_date = "2000-01-01"
    end_date = "2015-12-31"

    resultados = find_aster_with_local_cloud(
        wkt_geom=wkt_geom,
        start_date=start_date,
        end_date=end_date,
        min_coverage=0.95,
        max_results=20,
    )

    if not resultados:
        print("Nenhuma cena ASTER com cobertura mínima da folha.")
    else:
        print(
            "Cenas ASTER/AST_L1T_003 sobre a folha, "
            "ordenadas por fração de nuvem dentro da folha:"
        )
        for i, r in enumerate(resultados, start=1):
            print(
                f"[{i:02d}] id={r['id']}, "
                f"datetime={r['datetime']}, "
                f"cloud_fraction_aoi={r['cloud_fraction_aoi']:.3f}, "
                f"cloud_count_aoi={int(r['cloud_count_aoi'])}, "
                f"pixel_count_aoi={int(r['pixel_count_aoi'])}, "
                f"coverage_aoi={r['coverage_aoi']*100:.2f}%"
            )

#!/usr/bin/env python
import ee
from shapely import wkt
import os
import ee


# Coleções no Earth Engine
ASTER_COL = "ASTER/AST_L1T_003"
MODIS_COL = "MODIS/061/MOD09GA"

EE_PROJECT = os.environ.get("EE_PROJECT", None)


def init_ee():
    if EE_PROJECT:
        ee.Initialize(project=EE_PROJECT)
    else:
        ee.Initialize()


def wkt_to_ee_geometry(wkt_geom: str) -> ee.Geometry:
    geom = wkt.loads(wkt_geom)
    return ee.Geometry(geom.__geo_interface__)


def add_metrics(img: ee.Image, aoi: ee.Geometry, min_coverage: float):
    aoi_area = aoi.area()

    geom = img.geometry()
    inter = geom.intersection(aoi, ee.ErrorMargin(1))
    inter_area = inter.area()
    coverage = inter_area.divide(aoi_area)

    img = img.set("coverage_aoi", coverage)

    # MODIS do mesmo dia
    date = ee.Date(img.get("system:time_start"))
    date_next = date.advance(1, "day")

    modis_ic = (
        ee.ImageCollection(MODIS_COL)
        .filterDate(date, date_next)
        .filterBounds(aoi)
    )

    modis = modis_ic.first()

    def compute_cloud_fraction(mimg):
        state = mimg.select("state_1km")
        cloud_state = state.bitwiseAnd(3)  # bits 0-1
        cloudy = cloud_state.eq(1).Or(cloud_state.eq(2))  # cloudy ou mixed
        cloudy = cloudy.rename("cloudy")

        stats = cloudy.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=aoi,
            scale=1000,
            maxPixels=1e9,
        )
        return ee.Number(stats.get("cloudy"))

    cloud_fraction = ee.Number(
        ee.Algorithms.If(
            modis,
            compute_cloud_fraction(modis),
            1.0,  # se não houver MODIS, assume 100% nuvem
        )
    )

    img = img.set("cloud_fraction_aoi", cloud_fraction)

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
):
    init_ee()

    aoi = wkt_to_ee_geometry(wkt_geom)

    aster_ic = (
        ee.ImageCollection(ASTER_COL)
        .filterBounds(aoi)
        .filterDate(start_date, end_date)
    )

    def _map_fn(img):
        return add_metrics(img, aoi, min_coverage)

    aster_with_metrics = aster_ic.map(_map_fn).filter(
        ee.Filter.notNull(["cloud_fraction_aoi"])
    )

    # ordena por nuvem na folha (↑) e cobertura (↓)
    aster_sorted = aster_with_metrics.sort("cloud_fraction_aoi").sort(
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
                "coverage_aoi",
            ]
        ).getInfo()

        results.append(
            {
                "id": props["system:index"],
                "datetime": ee.Date(props["system:time_start"])
                .format("YYYY-MM-dd HH:mm:ss")
                .getInfo(),
                "cloud_fraction_aoi": float(props["cloud_fraction_aoi"]),
                "coverage_aoi": float(props["coverage_aoi"]),
            }
        )

    return results


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
                f"coverage_aoi={r['coverage_aoi']*100:.2f}%"
            )

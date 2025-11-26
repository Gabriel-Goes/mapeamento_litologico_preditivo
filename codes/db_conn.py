from __future__ import annotations

import json
from typing import Any, Dict

import geopandas as gpd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from config import PG_CONN_STR


def get_engine(conn_str: str | None = None) -> Engine:
    conn = conn_str or PG_CONN_STR
    return create_engine(conn)


def get_folha_geom_geojson(
    codigo_folha: str,
    schema: str = "carto",
    table: str = "folhas_cartograficas",
    conn_str: str | None = None,
) -> Dict[str, Any]:
    engine = get_engine(conn_str)
    sql = text(
        f"""
        SELECT ST_AsGeoJSON(ST_Transform(geom, 4326)) AS geom_json
        FROM {schema}.{table}
        WHERE codigo = :codigo
        LIMIT 1;
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql, {"codigo": codigo_folha}).fetchone()

    if row is None or row.geom_json is None:
        raise RuntimeError(f"Não foi encontrada geometria para a folha '{codigo_folha}'")

    return json.loads(row.geom_json)


def get_litologia_100k_for_folha(
    folha_codigo: str,
    raster_crs: Any,
    conn_str: str | None = None,
) -> gpd.GeoDataFrame:
    engine = get_engine(conn_str)
    sql = """
    SELECT
        id_unidade::integer AS label,
        geom
    FROM litologia.litologia_100k
    WHERE ST_Intersects(
        geom,
        (SELECT geom
         FROM carto.folhas_cartograficas
         WHERE codigo = %(codigo)s
         LIMIT 1)
    );
    """
    gdf = gpd.read_postgis(
        sql,
        con=engine,
        geom_col="geom",
        params={"codigo": folha_codigo},
    )
    if gdf.empty:
        raise RuntimeError(f"Nenhuma unidade litológica encontrada para a folha {folha_codigo}.")

    gdf = gdf.to_crs(raster_crs)
    return gdf

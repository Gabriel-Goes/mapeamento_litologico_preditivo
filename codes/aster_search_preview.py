from __future__ import annotations

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

import earthaccess as ea
from shapely.geometry import shape

from db_conn import get_folha_geom_geojson


def _get_folha_bbox(folha_id: str) -> Tuple[float, float, float, float]:
    geom_geojson = get_folha_geom_geojson(folha_id)
    geom = shape(geom_geojson)
    minx, miny, maxx, maxy = geom.bounds
    return float(minx), float(miny), float(maxx), float(maxy)


def _parse_datetime_from_umm(granule: Any) -> Optional[datetime]:
    umm = granule.get("umm", {})
    meta = granule.get("meta", {})

    t0_str: Optional[str] = None

    te = umm.get("TemporalExtent") or {}
    if isinstance(te, dict):
        rd = te.get("RangeDateTimes") or te.get("RangeDateTime")
        if isinstance(rd, dict):
            t0_str = rd.get("BeginningDateTime")
        elif isinstance(rd, list) and rd:
            first = rd[0]
            if isinstance(first, dict):
                t0_str = first.get("BeginningDateTime")
        if not t0_str:
            sd = te.get("SingleDateTime")
            if isinstance(sd, str):
                t0_str = sd

    if not t0_str:
        t0_str = (
            meta.get("time_start")
            or meta.get("start_time")
            or meta.get("start-time")
        )

    if not t0_str:
        return None

    s = t0_str.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(s)
    except Exception:
        try:
            return datetime.strptime(t0_str[:10], "%Y-%m-%d")
        except Exception:
            return None


def _parse_cloud_from_umm(umm: Dict[str, Any]) -> Optional[float]:
    vals: List[float] = []

    add_attrs = umm.get("AdditionalAttributes", [])
    for attr in add_attrs:
        name = str(attr.get("Name", "")).upper()
        if "CLOUD" in name and "COVER" in name:
            v_list = attr.get("Values") or []
            if not v_list:
                continue
            try:
                vals.append(float(v_list[0]))
            except Exception:
                continue

    if vals:
        return min(vals)

    for key in ("CloudCover", "cloud_cover", "CLOUDCOVER"):
        if key in umm:
            try:
                return float(umm[key])
            except Exception:
                continue

    return None


def search_aster_granules(
    folha_id: str,
    product: str = "AST_L1T",
    version: str = "004",
    target_date: str = "2008-06-15",  # mantido apenas por compatibilidade; não é usado
    start_date: str = "2000-01-01",
    end_date: str = "2025-12-31",
    cloud_max: float = 100.0,
    max_items: int = 50,
) -> List[Dict[str, Any]]:
    print("[ASTER] Iniciando search_aster_granules")
    print("[ASTER] Autenticando no Earthdata (earthaccess.login)...")
    auth = ea.login()
    if not auth.authenticated:
        raise RuntimeError("Falha na autenticação Earthdata (earthaccess.login).")

    bbox = _get_folha_bbox(folha_id)
    print(f"[ASTER] folha_id       = {folha_id}")
    print(f"[ASTER] product        = {product}.{version}")
    print(f"[ASTER] bbox (W,S,E,N) = {bbox}")
    print(f"[ASTER] intervalo      = ({start_date}, {end_date})")
    print(f"[ASTER] max_items      = {max_items}")
    print(f"[ASTER] cloud_max      = {cloud_max}")

    kwargs = dict(
        short_name=product,
        version=version,
        bounding_box=bbox,
        temporal=(start_date, end_date),
        count=max_items,
        cloud_hosted=True,
    )
    print("[ASTER] Chamando earthaccess.search_data com cloud_hosted=True")
    print(f"[ASTER] kwargs = {kwargs}")

    results = ea.search_data(**kwargs)
    print(f"[ASTER] Granules retornados (cloud_hosted=True): {len(results)}")

    candidatos: List[Dict[str, Any]] = []

    for g in results:
        umm = g.get("umm", {})
        t0 = _parse_datetime_from_umm(g)

        cloud = _parse_cloud_from_umm(umm)
        if cloud is not None and cloud > cloud_max:
            continue

        preview_url: Optional[str] = None
        try:
            viz_links = g.dataviz_links()
            if viz_links:
                preview_url = viz_links[0]
        except Exception:
            preview_url = None

        granule_ur = umm.get("GranuleUR", g.get("meta", {}).get("native-id", ""))

        candidatos.append(
            {
                "granule": g,
                "granule_ur": granule_ur,
                "datetime": t0,        # pode ser None
                "cloud": cloud,        # pode ser None
                "preview_url": preview_url,
            }
        )

    print(
        f"[ASTER] Após leitura de metadata: {len(candidatos)} granules "
        f"(sem filtro por data/target_date)."
    )

    if not candidatos:
        print("[ASTER] Nenhum granule com metadata utilizável.")
        return []

    def _score(c: Dict[str, Any]) -> float:
        ccloud = c["cloud"]
        if ccloud is None:
            ccloud = 9999.0
        return float(ccloud)

    candidatos.sort(key=_score)

    print("\nCenas encontradas (ordenadas por nebulosidade crescente):")
    for i, c in enumerate(candidatos):
        dt = c["datetime"]
        dt_str = dt.isoformat() if isinstance(dt, datetime) else "None"
        cloud_str = "None" if c["cloud"] is None else f"{c['cloud']:.1f}"
        print(
            f"  [{i}] id={c['granule_ur']}, "
            f"datetime={dt_str}, cloud={cloud_str}, "
            f"preview={'OK' if c['preview_url'] else 'None'}"
        )

    return candidatos

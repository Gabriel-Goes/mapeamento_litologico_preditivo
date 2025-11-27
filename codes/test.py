#!/usr/bin/env python
from shapely import wkt
from shapely.geometry import shape
from pystac_client import Client
import planetary_computer as pc

STAC_ROOT = "https://planetarycomputer.microsoft.com/api/stac/v1"
ASTER_COLLECTION = "aster-l1t"


def find_best_aster_l1t_for_region(wkt_geom: str):
    geom_folha = wkt.loads(wkt_geom)
    area_folha = geom_folha.area

    client = Client.open(STAC_ROOT)

    # IMPORTANTE: usar APENAS intersects (sem bbox) para evitar o erro de API
    search = client.search(
        collections=[ASTER_COLLECTION],
        intersects=geom_folha.__geo_interface__,
        max_items=1000,
    )

    items = list(search.items())
    if not items:
        return None

    best_item = None
    best_cloud = None
    best_coverage = None

    for item in items:
        item_geom = shape(item.geometry)
        inter = item_geom.intersection(geom_folha)
        if inter.is_empty:
            continue

        coverage = inter.area / area_folha
        if coverage < 0.90:
            continue

        cloud = item.properties.get("eo:cloud_cover")
        print(f'Item {item.id} cobertura: {coverage*100:.2f}%, nuvens: {cloud}')
        if cloud is None:
            print(f'Aviso: item {item.id} sem propriedade eo:cloud_cover, atribuindo 1000.0')
            cloud = 1000.0

        if (
            best_item is None
            or cloud < best_cloud
            or (cloud == best_cloud and coverage > best_coverage)
        ):
            best_item = item
            best_cloud = cloud
            best_coverage = coverage

    if best_item is None:
        return None

    return {
        "item_id": best_item.id,
        "datetime": best_item.datetime.isoformat() if best_item.datetime else None,
        "cloud_cover": best_cloud,
        "coverage_folha": best_coverage,
        "hrefs": {k: pc.sign(a).href for k, a in best_item.assets.items()},
    }


if __name__ == "__main__":
    # wkt_geom	fid	id_folha	EPSG
    # Polygon ((-56.375 -6, -56.25 -6, -56.25 -6.125, -56.375 -6.125, -56.375 -6))	4198	SB21_ZA_II1_NE	32721
    wkt_geom = "Polygon ((-56.125 -6, -56 -6, -56 -6.125, -56.125 -6.125, -56.125 -6))"
    # wkt_geom =  "Polygon ((-56.375 -6, -56.25 -6, -56.25 -6.125, -56.375 -6.125, -56.375 -6))"
    fid = 4198
    id_folha = "SB21_ZA_II1_NE"
    epsg_local = 32721

    result = find_best_aster_l1t_for_region(wkt_geom)

    if result is None:
        print(f"Nenhuma cena ASTER L1T cobre totalmente a folha {id_folha}.")
    else:
        print(f"Folha: {id_folha} (fid={fid}, EPSG_local={epsg_local})")
        print("Melhor cena ASTER L1T encontrada:")
        print(f"  item_id:      {result['item_id']}")
        print(f"  datetime:     {result['datetime']}")
        print(f"  cloud_cover:  {result['cloud_cover']}")
        print(f"  coverage:     {result['coverage_folha'] * 100:.2f}%")
        print("  assets (hrefs assinados):")
        for name, href in result["hrefs"].items():
            print(f"    {name}: {href}")

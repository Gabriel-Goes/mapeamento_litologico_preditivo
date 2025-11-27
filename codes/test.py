#!/usr/bin/env python
from shapely import wkt
from shapely.geometry import shape
from pystac_client import Client
import planetary_computer as pc

STAC_ROOT = "https://planetarycomputer.microsoft.com/api/stac/v1"
ASTER_COLLECTION = "aster-l1t"


def find_aster_l1t_candidates_for_region(
    wkt_geom: str,
    min_coverage: float = 0.95,
    max_items: int = 1000,
):
    geom_folha = wkt.loads(wkt_geom)
    area_folha = geom_folha.area

    client = Client.open(STAC_ROOT)
    search = client.search(
        collections=[ASTER_COLLECTION],
        intersects=geom_folha.__geo_interface__,
        max_items=max_items,
    )

    items = list(search.items())
    if not items:
        return []

    candidates = []

    for item in items:
        item_geom = shape(item.geometry)
        inter = item_geom.intersection(geom_folha)
        if inter.is_empty:
            continue

        coverage = inter.area / area_folha
        if coverage < min_coverage:
            continue

        cloud = item.properties.get("eo:cloud_cover")
        if cloud is None:
            cloud = 1000.0

        candidates.append(
            {
                "item": item,
                "item_id": item.id,
                "datetime": item.datetime.isoformat() if item.datetime else None,
                "cloud_cover": float(cloud),
                "coverage_folha": float(coverage),
            }
        )

    # ordena: menos nuvem primeiro, depois maior cobertura
    candidates.sort(key=lambda d: (d["cloud_cover"], -d["coverage_folha"]))
    return candidates


if __name__ == "__main__":
    # wkt_geom	fid	id_folha	EPSG
    # Polygon ((-56.375 -6, -56.25 -6, -56.25 -6.125, -56.375 -6.125, -56.375 -6))	4198	SB21_ZA_II1_NE	32721
    wkt_geom = "Polygon ((-56.125 -6, -56 -6, -56 -6.125, -56.125 -6.125, -56.125 -6))"
    fid = 4198
    id_folha = "SB21_ZA_II1_NE"
    epsg_local = 32721

    candidates = find_aster_l1t_candidates_for_region(wkt_geom, min_coverage=0.95)

    if not candidates:
        print(f"Nenhuma cena ASTER L1T cobre a folha {id_folha} com cobertura >= 95%.")
    else:
        print(f"Folha: {id_folha} (fid={fid}, EPSG_local={epsg_local})")
        print("Cenas candidatas (ordenadas por nuvem ↑, cobertura ↓):\n")

        for i, c in enumerate(candidates, start=1):
            print(
                f"[{i:02d}] id={c['item_id']}, "
                f"datetime={c['datetime']}, "
                f"cloud={c['cloud_cover']:.1f}%, "
                f"coverage={c['coverage_folha']*100:.2f}%"
            )

        best = candidates[0]
        best_item = best["item"]
        hrefs_best = {k: pc.sign(a).href for k, a in best_item.assets.items()}

        print("\nMelhor cena (primeira da lista acima):")
        print(f"  item_id:      {best['item_id']}")
        print(f"  datetime:     {best['datetime']}")
        print(f"  cloud_cover:  {best['cloud_cover']}")
        print(f"  coverage:     {best['coverage_folha'] * 100:.2f}%")
        print("  assets (hrefs assinados):")
        for name, href in hrefs_best.items():
            print(f"    {name}: {href}")


        best = candidates[1]
        best_item = best["item"]
        hrefs_best = {k: pc.sign(a).href for k, a in best_item.assets.items()}

        print("\nMelhor cena (primeira da lista acima):")
        print(f"  item_id:      {best['item_id']}")
        print(f"  datetime:     {best['datetime']}")
        print(f"  cloud_cover:  {best['cloud_cover']}")
        print(f"  coverage:     {best['coverage_folha'] * 100:.2f}%")
        print("  assets (hrefs assinados):")
        for name, href in hrefs_best.items():
            print(f"    {name}: {href}")

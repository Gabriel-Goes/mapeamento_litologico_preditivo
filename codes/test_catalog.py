import logging
from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import rasterio
import requests
from PIL import Image
from pystac_client import Client
from rasterio.warp import transform_bounds
from shapely.geometry import shape, box

logging.basicConfig()
logger = logging.getLogger("pystac_client")
logger.setLevel(logging.INFO)

# endpoint, id da coleção ASTER L1T em cada provedor
ast_l1t_endpoints = {
    "planetary_computer": (
        "https://planetarycomputer.microsoft.com/api/stac/v1",
        "aster-l1t",
    ),
    "nasa_lpdaac_lpcloud": (
        "https://cmr.earthdata.nasa.gov/stac/LPCLOUD",
        "AST_L1T_004",
    ),
}


def search_ast_l1t(bbox=None, datetime=None, max_items=20):
    resultados = {}

    for name, (url, coll_id) in ast_l1t_endpoints.items():
        print("\n==============================")
        print(f"Endpoint: {name}")
        print(f"URL: {url}")
        print(f"Coleção: {coll_id}")
        print("------------------------------")

        try:
            cat = Client.open(url)
        except Exception as e:
            print("Falha ao abrir catálogo:", e)
            continue

        try:
            search = cat.search(
                collections=[coll_id],
                bbox=bbox,
                datetime=datetime,
                max_items=max_items,
            )
            items = list(search.items())
        except Exception as e:
            print("Erro na busca:", e)
            continue

        resultados[name] = items
        print(f"Total de itens retornados: {len(items)}")
        for it in items[:10]:
            dt = it.properties.get("datetime")
            print(f"- {it.id} | datetime={dt}")

    return resultados


def get_cloud_cover(item):
    props = item.properties or {}
    for key in ("eo:cloud_cover", "cloud_cover", "CLOUD_COVER", "clouds", "CLOUDS"):
        if key in props:
            return props[key]
    return None


def _coverage_fraction(item, folha_geom):
    if folha_geom is None or item.geometry is None:
        return None
    geom_item = shape(item.geometry)
    inter = geom_item.intersection(folha_geom)
    if inter.is_empty or folha_geom.area == 0:
        return 0.0
    return inter.area / folha_geom.area


def search_ast_l1t_cloudfiltered(
    bbox=None,
    datetime=None,
    max_items=50,
    cloud_max=10.0,
    min_coverage=0.0,
):
    resultados = {}

    # usamos o bbox da folha como geometria de referência para a cobertura
    folha_geom = box(*bbox) if bbox is not None else None

    for name, (url, coll_id) in ast_l1t_endpoints.items():
        print("\n==============================")
        print(f"Endpoint: {name}")
        print(f"URL: {url}")
        print(f"Coleção: {coll_id}")
        print(f"Filtro de nuvem: <= {cloud_max}")
        if folha_geom is not None and min_coverage > 0:
            print(f"Filtro de cobertura: >= {min_coverage * 100:.1f}% da área do bbox")
        print("------------------------------")

        try:
            cat = Client.open(url)
        except Exception as e:
            print("Falha ao abrir catálogo:", e)
            continue

        try:
            search = cat.search(
                collections=[coll_id],
                bbox=bbox,
                datetime=datetime,
                max_items=max_items,
            )
            items = list(search.items())
        except Exception as e:
            print("Erro na busca:", e)
            continue

        selecionados = []
        for it in items:
            # filtro de nuvem
            cc = get_cloud_cover(it)
            if cc is None:
                continue
            try:
                cc_val = float(cc)
            except Exception:
                continue
            if cc_val > cloud_max:
                continue

            # filtro de cobertura da folha
            cov = None
            if folha_geom is not None and min_coverage > 0:
                cov = _coverage_fraction(it, folha_geom)
                if cov is None or cov < min_coverage:
                    continue

            selecionados.append((it, cc_val, cov))

        resultados[name] = [it for it, _, _ in selecionados]

        print(f"Total de itens retornados (antes dos filtros): {len(items)}")
        print(
            f"Itens com nuvem <= {cloud_max} "
            f"e cobertura >= {min_coverage*100:.1f}%: {len(selecionados)}"
        )
        for it, cc_val, cov in selecionados[:10]:
            dt = it.datetime
            cov_txt = f"{cov*100:.1f}%" if cov is not None else "N/A"
            print(f"- {it.id} | datetime={dt} | cloud={cc_val} | coverage={cov_txt}")

    return resultados


def pick_visual_asset(item):
    assets = item.assets or {}
    for key, asset in assets.items():
        roles = (asset.roles or [])
        roles_lower = [r.lower() for r in roles]
        if any(r in ("thumbnail", "overview", "visual", "browse") for r in roles_lower):
            return key, asset
    for key in ("vnir-browse", "browse", "thumbnail", "BROWSE"):
        if key in assets:
            return key, assets[key]
    if assets:
        key = list(assets.keys())[0]
        return key, assets[key]
    return None, None


def show_item_quicklook(item, session=None):
    if session is None:
        session = requests.Session()
    key, asset = pick_visual_asset(item)
    if asset is None:
        print("Nenhum asset visual encontrado para", item.id)
        return
    url = asset.href
    print(f"  asset_visual={key} -> {url}")
    try:
        r = session.get(url, stream=True)
        r.raise_for_status()
    except Exception as e:
        print("  erro ao baixar imagem:", e)
        return
    img = Image.open(BytesIO(r.content))
    plt.figure(figsize=(8, 8))
    plt.imshow(img)
    plt.axis("off")
    plt.title(item.id)
    plt.show()


def browse_ast_l1t_images(resultados, provider="nasa_lpdaac_lpcloud"):
    items = resultados.get(provider, [])
    if not items:
        print("Nenhum item encontrado para provider:", provider)
        return
    session = requests.Session()
    n = len(items)
    for idx, it in enumerate(items, start=1):
        cc = get_cloud_cover(it)
        print(f"\n[{idx}/{n}] {it.id} | datetime={it.datetime} | cloud={cc}")
        show_item_quicklook(it, session=session)
        cmd = input("Enter = próxima, 'q' = sair: ").strip().lower()
        if cmd == "q":
            break


def pick_fullres_asset(item, prefer_keys=None):
    assets = item.assets or {}
    prefer_keys = prefer_keys or []

    def is_fullres(a):
        mt = (a.media_type or "").lower()
        return ("tiff" in mt) or ("geotiff" in mt) or ("hdf" in mt)

    for key in prefer_keys:
        if key in assets and is_fullres(assets[key]):
            return key, assets[key]

    for key, a in assets.items():
        roles = [r.lower() for r in (a.roles or [])]
        if is_fullres(a) and not any(
            r in ("thumbnail", "overview", "browse", "visual") for r in roles
        ):
            return key, a

    for key, a in assets.items():
        if is_fullres(a):
            return key, a

    return pick_visual_asset(item)


def show_item_fullres_with_bbox(item, bbox_wgs84, band_key=None):
    assets = item.assets or {}
    if band_key is None:
        band_key, asset = pick_fullres_asset(item)
    else:
        asset = assets[band_key]

    href = asset.href
    mt = (asset.media_type or "").lower()
    roles = [r.lower() for r in (asset.roles or [])]
    print(f"  asset_fullres={band_key} -> {href}")

    geom = item.geometry
    geom_extent = None
    if geom is not None:
        minx, miny, maxx, maxy = shape(geom).bounds
        geom_extent = (minx, maxx, miny, maxy)

    # caso típico LPCLOUD: browse JPEG sem CRS
    if ("jpeg" in mt or "jpg" in mt) and "browse" in roles:
        r = requests.get(href, stream=True)
        r.raise_for_status()
        img = Image.open(BytesIO(r.content))
        data = np.array(img)
        if geom_extent is not None:
            extent = geom_extent
            x_min, y_min, x_max, y_max = bbox_wgs84
        else:
            h, w = data.shape[0], data.shape[1]
            extent = (0, w, 0, h)
            x_min, y_min, x_max, y_max = 0, 0, w, h
    else:
        with rasterio.open(href) as src:
            data = src.read(1)
            if src.crs is None:
                if geom_extent is not None:
                    extent = geom_extent
                else:
                    extent = (
                        src.bounds.left,
                        src.bounds.right,
                        src.bounds.bottom,
                        src.bounds.top,
                    )
                x_min, y_min, x_max, y_max = bbox_wgs84
            else:
                extent = (
                    src.bounds.left,
                    src.bounds.right,
                    src.bounds.bottom,
                    src.bounds.top,
                )
                x_min, y_min, x_max, y_max = transform_bounds(
                    "EPSG:4326", src.crs, *bbox_wgs84, densify_pts=21
                )

    xs = [x_min, x_max, x_max, x_min, x_min]
    ys = [y_min, y_min, y_max, y_max, y_min]

    plt.figure(figsize=(9, 9))
    plt.imshow(data, extent=extent, origin="upper")
    plt.plot(xs, ys, linewidth=2)
    plt.title(item.id)
    plt.axis("equal")
    plt.show()


def browse_ast_l1t_fullres_with_bbox(
    resultados,
    bbox_wgs84,
    provider="nasa_lpdaac_lpcloud",
    band_key=None,
):
    items = resultados.get(provider, [])
    if not items:
        print("Nenhum item encontrado para provider:", provider)
        return

    n = len(items)
    for idx, it in enumerate(items, start=1):
        cc = get_cloud_cover(it)
        print(f"\n[{idx}/{n}] {it.id} | datetime={it.datetime} | cloud={cc}")
        show_item_fullres_with_bbox(it, bbox_wgs84, band_key=band_key)
        cmd = input("Enter = próxima, 'q' = sair: ").strip().lower()
        if cmd == "q":
            break


def select_best_ast_l1t_scenes(
    resultados,
    bbox_wgs84,
    provider="nasa_lpdaac_lpcloud",
    band_key=None,
):
    items = resultados.get(provider, [])
    if not items:
        print("Nenhum item encontrado para provider:", provider)
        return []

    selecionadas = []
    n = len(items)

    for idx, it in enumerate(items, start=1):
        cc = get_cloud_cover(it)
        print(f"\n[{idx}/{n}] {it.id} | datetime={it.datetime} | cloud={cc}")
        show_item_fullres_with_bbox(it, bbox_wgs84, band_key=band_key)

        cmd = input("Selecionar esta cena? [y = sim / n = não / q = sair]: ").strip().lower()
        if cmd == "q":
            break
        if cmd == "y":
            selecionadas.append(it)
            print(f"  -> Cena adicionada à lista: {it.id}")

    if not selecionadas:
        print("\nNenhuma cena foi selecionada.")
    else:
        print("\nCenas selecionadas (em ordem de escolha):")
        for i, it in enumerate(selecionadas, start=1):
            print(f"  {i:02d} - {it.id}")

    return selecionadas

if __name__ == "__main__":
    _ = search_ast_l1t(
        bbox=None,
        datetime="2000-01-01/2015-12-31",
        max_items=10,
    )

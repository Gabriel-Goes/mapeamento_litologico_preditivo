import logging
import os
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone

import matplotlib.pyplot as plt
from PIL import Image
import requests
from pystac_client import Client
from shapely.geometry import shape, box
from rasterio.warp import transform_bounds
import rasterio
from rasterio.enums import Resampling
from rasterio.errors import RasterioIOError, WindowError
from rasterio.windows import from_bounds
import planetary_computer

logging.basicConfig()
logger = logging.getLogger("pystac_client")
logger.setLevel(logging.INFO)

# -------------------------------------------------
# Endpoints
# -------------------------------------------------

# AST_07 L2 Surface Reflectance VNIR+SWIR V004 em LPCLOUD
ast07_endpoints = {
    "nasa_lpdaac_lpcloud": (
        "https://cmr.earthdata.nasa.gov/stac/LPCLOUD",
        "AST_07_004",
    )
}

s2_endpoints = {
    "planetary_computer": (
        "https://planetary_computer.microsoft.com/api/stac/v1".replace(
            "planetary_computer", "planetarycomputer"
        ),
        "sentinel-2-l2a",
    ),
    "earth_search_aws": (
        "https://earth-search.aws.element84.com/v1",
        "sentinel-s2-l2a-cogs",
    ),
}

# -------------------------------------------------
# Helpers gerais
# -------------------------------------------------

def _get_item_datetime(item):
    dt = getattr(item, "datetime", None)
    if dt is not None:
        return dt
    props = getattr(item, "properties", {}) or {}
    dt_str = props.get("datetime") or props.get("start_datetime") or props.get("end_datetime")
    if dt_str is None:
        return None
    try:
        if "T" not in dt_str:
            return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
        dt_str = dt_str.replace("Z", "+00:00")
        return datetime.fromisoformat(dt_str)
    except Exception:
        return None


def _ensure_http_href(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return href


def _geom_from_item(item):
    if getattr(item, "geometry", None):
        return shape(item.geometry)
    return None


def _bbox_polygon(bbox):
    xmin, ymin, xmax, ymax = bbox
    return box(xmin, ymin, xmax, ymax)


def _compute_coverage(item, bbox):
    g_item = _geom_from_item(item)
    if g_item is None or g_item.is_empty:
        return None
    g_bbox = _bbox_polygon(bbox)
    inter = g_item.intersection(g_bbox)
    if inter.is_empty:
        return 0.0
    return inter.area / g_bbox.area


def get_cloud_cover(item):
    props = item.properties or {}
    for key in ("eo:cloud_cover", "cloud_cover", "CLOUD_COVER", "clouds", "CLOUDS"):
        if key in props:
            return props[key]
    return None


def pick_visual_asset(item):
    assets = item.assets or {}
    for key in ("thumbnail", "preview", "overview", "visual", "browse"):
        if key in assets:
            return key, assets[key]
    for key, asset in assets.items():
        roles = (asset.roles or [])
        roles_lower = [r.lower() for r in roles]
        if any(r in ("thumbnail", "overview", "visual", "browse") for r in roles_lower):
            return key, asset
    if assets:
        key = list(assets.keys())[0]
        return key, assets[key]
    return None, None


def pick_fullres_asset(item, prefer_keys=None):
    assets = item.assets or {}
    prefer_keys = prefer_keys or []

    def is_data_asset(key, a):
        name = key.lower()
        mt = (a.media_type or "").lower()
        roles = [r.lower() for r in (a.roles or [])]
        href = (a.href or "").lower()
        href_noq = href.split("?")[0]
        ext = href_noq.split(".")[-1] if "." in href_noq else ""

        # ignorar thumbnails / browse / preview
        if any(r in ("thumbnail", "browse", "preview", "overview", "visual") for r in roles):
            return False
        if any(w in name for w in ("browse", "thumb", "preview", "overview")):
            return False

        # tipos de dado (GeoTIFF, HDF, NetCDF)
        if any(t in mt for t in (
            "geotiff",
            "image/tiff",
            "image/geotiff",
            "application/x-hdf",
            "application/x-hdf4",
            "application/x-hdf5",
            "application/netcdf",
        )):
            return True

        # fallback pela extensão
        if ext in ("tif", "tiff", "hdf", "hdf4", "hdf5", "nc"):
            return True

        return False

    for key in prefer_keys:
        if key in assets and is_data_asset(key, assets[key]):
            return key, assets[key]

    for key, a in assets.items():
        if is_data_asset(key, a):
            return key, a

    return pick_visual_asset(item)


def show_item_quicklook(item, session=None):
    if session is None:
        session = requests.Session()
    key, asset = pick_visual_asset(item)
    if asset is None:
        print("Nenhum asset visual encontrado para", item.id)
        return
    url = _ensure_http_href(asset.href)
    print(f"  asset_visual={key} -> {url}")
    try:
        r = session.get(url, stream=True)
        r.raise_for_status()
    except Exception as e:
        print("  erro ao baixar imagem:", e)
        return
    img = Image.open(BytesIO(r.content))
    plt.figure(figsize=(6, 6))
    plt.imshow(img)
    plt.axis("off")
    plt.title(item.id)
    plt.show()


def print_item_assets(item):
    print(f"Assets de {item.id}:")
    for k, a in (item.assets or {}).items():
        print(f"  - {k}: media_type={a.media_type}, roles={a.roles}")


def download_asset(item, asset_key, out_dir, overwrite=False):
    asset = item.assets[asset_key]
    url = _ensure_http_href(asset.href)

    os.makedirs(out_dir, exist_ok=True)

    name_from_url = url.split("/")[-1].split("?")[0]
    if "." in name_from_url:
        suffix = "." + name_from_url.split(".")[-1]
    else:
        suffix = ""

    out_path = Path(out_dir) / f"{item.id}_{asset_key}{suffix}"

    if out_path.exists() and not overwrite:
        print(f"{out_path} já existe, pulando download.")
        return out_path

    print(f"Baixando {item.id} asset '{asset_key}' -> {out_path}")
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(out_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    print("Concluído:", out_path)
    return out_path

# -------------------------------------------------
# AST_07 (L2 reflectância)
# -------------------------------------------------

def search_ast07_cloudfiltered(
    bbox=None,
    datetime=None,
    max_items=100,
    cloud_max=10.0,
    min_coverage=0.0,
):
    resultados = {}

    for name, (url, coll_id) in ast07_endpoints.items():
        print("\n==============================")
        print(f"Endpoint: {name}")
        print(f"URL: {url}")
        print(f"Coleção: {coll_id}")
        print(f"Filtro de nuvem: <= {cloud_max}")
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
            items_raw = list(search.items())
        except Exception as e:
            print("Erro na busca:", e)
            continue

        items = list(items_raw)

        selecionados = []
        for it in items:
            cc = get_cloud_cover(it)
            if cc is None:
                continue
            try:
                cc_val = float(cc)
            except Exception:
                continue

            cov = None
            if bbox is not None:
                cov = _compute_coverage(it, bbox)

            if cov is None:
                cov_ok = True if min_coverage == 0.0 else False
            else:
                cov_ok = cov >= min_coverage

            if cc_val <= cloud_max and cov_ok:
                selecionados.append((it, cc_val, cov))

        resultados[name] = [it for it, _, _ in selecionados]

        print(f"Total de itens retornados (antes dos filtros): {len(items)}")
        print(
            f"Itens com nuvem <= {cloud_max} e cobertura >= {min_coverage * 100:.1f}%: "
            f"{len(selecionados)}"
        )
        for it, cc_val, cov in selecionados[:5]:
            dt = _get_item_datetime(it)
            cov_pct = cov * 100 if cov is not None else None
            print(
                f"- {it.id} | datetime={dt} | cloud={cc_val} | coverage={cov_pct:.1f}%"
            )

    return resultados


def show_ast07_clipped_to_bbox(
    item,
    bbox_wgs84,
    band_key=None,
    prefer_keys=None,
    max_size=800,
):
    prefer_keys = prefer_keys or []
    if band_key is None:
        band_key, asset = pick_fullres_asset(item, prefer_keys=prefer_keys)
    else:
        asset = item.assets[band_key]

    if asset is None:
        print("Nenhum asset fullres encontrado para", item.id)
        show_item_quicklook(item)
        return

    href = _ensure_http_href(asset.href)
    print(f"  asset_fullres={band_key} -> {href}")

    try:
        with rasterio.open(href) as src:
            if src.crs is None or src.transform is None:
                print("  asset AST_07 não georreferenciado (sem CRS/transform); usando quicklook.")
                show_item_quicklook(item)
                return

            try:
                bbox_proj = transform_bounds("EPSG:4326", src.crs, *bbox_wgs84, densify_pts=21)
            except Exception as e:
                print("  erro ao reprojetar bbox:", e)
                bbox_proj = bbox_wgs84

            try:
                window = from_bounds(*bbox_proj, transform=src.transform)
                window = window.round_offsets().round_lengths()
            except WindowError as e:
                print("  erro ao criar window a partir do bbox:", e)
                print("  usando cena inteira sem recorte.")
                window = None

            if window is not None:
                w = int(window.width)
                h = int(window.height)
                if w <= 0 or h <= 0:
                    print("  window vazia; usando cena inteira.")
                    window = None

            if window is None:
                w = src.width
                h = src.height
                scale = min(max_size / w, max_size / h, 1.0)
                out_w = max(1, int(w * scale))
                out_h = max(1, int(h * scale))

                if src.count >= 3:
                    data = src.read(
                        [1, 2, 3],
                        out_shape=(3, out_h, out_w),
                        resampling=Resampling.bilinear,
                    )
                    img = data.transpose(1, 2, 0)
                else:
                    data = src.read(
                        1,
                        out_shape=(out_h, out_w),
                        resampling=Resampling.bilinear,
                    )
                    img = data

                extent = (
                    src.bounds.left,
                    src.bounds.right,
                    src.bounds.bottom,
                    src.bounds.top,
                )
            else:
                w = int(window.width)
                h = int(window.height)
                scale = min(max_size / w, max_size / h, 1.0)
                out_w = max(1, int(w * scale))
                out_h = max(1, int(h * scale))

                if src.count >= 3:
                    data = src.read(
                        [1, 2, 3],
                        window=window,
                        out_shape=(3, out_h, out_w),
                        resampling=Resampling.bilinear,
                    )
                    img = data.transpose(1, 2, 0)
                else:
                    data = src.read(
                        1,
                        window=window,
                        out_shape=(out_h, out_w),
                        resampling=Resampling.bilinear,
                    )
                    img = data

                left, bottom, right, top = rasterio.windows.bounds(window, src.transform)
                extent = (left, right, bottom, top)

    except RasterioIOError as e:
        print("  erro ao abrir asset com rasterio:", e)
        print("  fallback para quicklook simples.")
        show_item_quicklook(item)
        return

    plt.figure(figsize=(6, 6))
    plt.imshow(img, extent=extent, origin="upper")
    plt.title(item.id + " (recorte folha)")
    plt.axis("equal")
    plt.show()


def select_best_ast07_scenes(
    resultados,
    bbox_wgs84,
    provider="nasa_lpdaac_lpcloud",
    band_key=None,
    target_date=None,
):
    items = resultados.get(provider, [])
    if not items:
        print("Nenhum item encontrado para provider:", provider)
        return []

    target_dt = None
    if target_date is not None:
        if isinstance(target_date, str):
            target_dt = datetime.fromisoformat(target_date).replace(tzinfo=timezone.utc)
        else:
            target_dt = target_date

    if target_dt is not None:
        def _time_distance(it):
            dt = _get_item_datetime(it)
            if dt is None:
                return float("inf")
            return abs((dt - target_dt).total_seconds())
        items = sorted(items, key=_time_distance)

    selected = []
    n = len(items)
    for idx, it in enumerate(items, start=1):
        cc = get_cloud_cover(it)
        dt = _get_item_datetime(it)
        if target_dt is not None and dt is not None:
            delta_days = (dt - target_dt).days
            print(f"\n[{idx}/{n}] {it.id} | datetime={dt} | cloud={cc} | delta_days={delta_days}")
        else:
            print(f"\n[{idx}/{n}] {it.id} | datetime={dt} | cloud={cc}")

        show_ast07_clipped_to_bbox(
            it,
            bbox_wgs84=bbox_wgs84,
            band_key=band_key,
            prefer_keys=None,
            max_size=800,
        )

        cmd = input("Selecionar esta cena? [y = sim / n = não / q = sair]: ").strip().lower()
        if cmd == "q":
            break
        if cmd == "y":
            selected.append(it)
            print(f"  -> Cena adicionada à lista: {it.id}")

    if not selected:
        print("\nNenhuma cena AST_07 selecionada.")
    else:
        print("\nCenas AST_07 selecionadas (em ordem de escolha):")
        for i, it in enumerate(selected, start=1):
            print(f"  {i:02d} - {it.id}")

    return selected

# -------------------------------------------------
# Sentinel-2
# -------------------------------------------------

def pick_s2_preview_asset(item):
    assets = item.assets or {}
    for key in ("thumbnail", "preview", "overview"):
        if key in assets:
            return key, assets[key]
    return pick_visual_asset(item)


def pick_s2_cloudmask_asset(item):
    assets = item.assets or {}
    priority_keys = ["SCL", "scl", "SCL_20m", "SCL_60m"]
    for key in priority_keys:
        if key in assets:
            return key, assets[key]
    for key, asset in assets.items():
        name = key.lower()
        title = (asset.title or "").lower()
        if "scl" in name or "scene class" in title:
            return key, asset
    return None, None


def show_s2_preview_and_cloudmask_with_bbox(
    item,
    bbox_wgs84,
    max_size_preview=800,
    max_size_scl=800,
):
    prev_key, prev_asset = pick_s2_preview_asset(item)
    if prev_asset is None:
        print("Nenhum asset de preview encontrado para", item.id)
        show_item_quicklook(item)
        return

    href_prev = _ensure_http_href(prev_asset.href)
    print(f"  asset_preview={prev_key} -> {href_prev}")

    try:
        with rasterio.open(href_prev) as src_prev:
            scale = min(
                max_size_preview / src_prev.width,
                max_size_preview / src_prev.height,
                1.0,
            )
            out_width = max(1, int(src_prev.width * scale))
            out_height = max(1, int(src_prev.height * scale))

            if src_prev.count >= 3:
                data_prev = src_prev.read(
                    [1, 2, 3],
                    out_shape=(3, out_height, out_width),
                    resampling=Resampling.bilinear,
                )
                img_prev = data_prev.transpose(1, 2, 0)
            else:
                data_prev = src_prev.read(
                    1,
                    out_shape=(out_height, out_width),
                    resampling=Resampling.bilinear,
                )
                img_prev = data_prev

            extent_prev = (
                src_prev.bounds.left,
                src_prev.bounds.right,
                src_prev.bounds.bottom,
                src_prev.bounds.top,
            )
            bbox_prev = transform_bounds(
                "EPSG:4326", src_prev.crs, *bbox_wgs84, densify_pts=21
            )
    except RasterioIOError as e:
        print("  erro ao abrir preview com rasterio:", e)
        show_item_quicklook(item)
        return

    scl_key, scl_asset = pick_s2_cloudmask_asset(item)
    scl_img = None
    if scl_asset is not None:
        href_scl = _ensure_http_href(scl_asset.href)
        print(f"  asset_scl={scl_key} -> {href_scl}")
        try:
            with rasterio.open(href_scl) as src_scl:
                scale_scl = min(
                    max_size_scl / src_scl.width,
                    max_size_scl / src_scl.height,
                    1.0,
                )
                out_width_scl = max(1, int(src_scl.width * scale_scl))
                out_height_scl = max(1, int(src_scl.height * scale_scl))

                data_scl = src_scl.read(
                    1,
                    out_shape=(out_height_scl, out_width_scl),
                    resampling=Resampling.nearest,
                )
                scl_img = data_scl
                extent_scl = (
                    src_scl.bounds.left,
                    src_scl.bounds.right,
                    src_scl.bounds.bottom,
                    src_scl.bounds.top,
                )
                bbox_scl = transform_bounds(
                    "EPSG:4326", src_scl.crs, *bbox_wgs84, densify_pts=21
                )
        except RasterioIOError as e:
            print("  erro ao abrir SCL com rasterio:", e)
            scl_img = None

    if scl_img is not None:
        fig, axes = plt.subplots(1, 2, figsize=(12, 6))
        ax_prev, ax_scl = axes
    else:
        fig, ax_prev = plt.subplots(1, 1, figsize=(6, 6))
        ax_scl = None

    ax_prev.imshow(img_prev, extent=extent_prev, origin="upper")
    x_min, y_min, x_max, y_max = bbox_prev
    xs = [x_min, x_max, x_max, x_min, x_min]
    ys = [y_min, y_min, y_max, y_max, y_min]
    ax_prev.plot(xs, ys, linewidth=2)
    ax_prev.set_title(f"{item.id} - preview")
    ax_prev.axis("equal")

    if ax_scl is not None:
        im = ax_scl.imshow(scl_img, extent=extent_scl, origin="upper")
        x_min_s, y_min_s, x_max_s, y_max_s = bbox_scl
        xs_s = [x_min_s, x_max_s, x_max_s, x_min_s, x_min_s]
        ys_s = [y_min_s, y_min_s, y_max_s, y_max_s, y_min_s]
        ax_scl.plot(xs_s, ys_s, linewidth=2)
        ax_scl.set_title(f"{item.id} - SCL")
        ax_scl.axis("equal")
        fig.colorbar(im, ax=ax_scl, shrink=0.7)

    plt.tight_layout()
    plt.show()


def search_s2_cloudfiltered(
    bbox=None,
    datetime=None,
    max_items=100,
    cloud_max=5.0,
    min_coverage=0.0,
):
    resultados = {}

    for name, (url, coll_id) in s2_endpoints.items():
        print("\n==============================")
        print(f"Endpoint: {name}")
        print(f"URL: {url}")
        print(f"Coleção: {coll_id}")
        print(f"Filtro de nuvem: <= {cloud_max}")
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
            items_raw = list(search.items())
        except Exception as e:
            print("Erro na busca:", e)
            continue

        items = []
        for it in items_raw:
            if name == "planetary_computer":
                try:
                    it = planetary_computer.sign(it)
                except Exception as e:
                    print("  falha ao assinar item S2:", it.id, e)
            items.append(it)

        selecionados = []
        for it in items:
            cc = get_cloud_cover(it)
            if cc is None:
                continue
            try:
                cc_val = float(cc)
            except Exception:
                continue

            cov = None
            if bbox is not None:
                cov = _compute_coverage(it, bbox)

            if cov is None:
                cov_ok = True if min_coverage == 0.0 else False
            else:
                cov_ok = cov >= min_coverage

            if cc_val <= cloud_max and cov_ok:
                selecionados.append((it, cc_val, cov))

        resultados[name] = [it for it, _, _ in selecionados]

        print(f"Total de itens retornados (antes dos filtros): {len(items)}")
        print(
            f"Itens com nuvem <= {cloud_max} e cobertura >= {min_coverage * 100:.1f}%: "
            f"{len(selecionados)}"
        )
        for it, cc_val, cov in selecionados[:5]:
            dt = _get_item_datetime(it)
            cov_pct = cov * 100 if cov is not None else None
            print(
                f"- {it.id} | datetime={dt} | cloud={cc_val} | coverage={cov_pct:.1f}%"
            )

    return resultados


def select_best_s2_scenes(
    resultados,
    bbox_wgs84,
    provider="planetary_computer",
    band_key=None,
    target_date=None,
):
    items = resultados.get(provider, [])
    if not items:
        print("Nenhum item encontrado para provider:", provider)
        return []

    target_dt = None
    if target_date is not None:
        if isinstance(target_date, str):
            target_dt = datetime.fromisoformat(target_date).replace(tzinfo=timezone.utc)
        else:
            target_dt = target_date

    if target_dt is not None:
        def _time_distance(it):
            dt = _get_item_datetime(it)
            if dt is None:
                return float("inf")
            return abs((dt - target_dt).total_seconds())
        items = sorted(items, key=_time_distance)

    selected = []
    n = len(items)
    for idx, it in enumerate(items, start=1):
        cc = get_cloud_cover(it)
        dt = _get_item_datetime(it)
        if target_dt is not None and dt is not None:
            delta_days = (dt - target_dt).days
            print(f"\n[{idx}/{n}] {it.id} | datetime={dt} | cloud={cc} | delta_days={delta_days}")
        else:
            print(f"\n[{idx}/{n}] {it.id} | datetime={dt} | cloud={cc}")
        show_s2_preview_and_cloudmask_with_bbox(it, bbox_wgs84)
        cmd = input(
            "Selecionar esta cena? [y = sim / n = não / q = sair]: "
        ).strip().lower()
        if cmd == "q":
            break
        if cmd == "y":
            selected.append(it)
            print(f"  -> Cena adicionada à lista: {it.id}")

    if not selected:
        print("\nNenhuma cena Sentinel-2 selecionada.")
    else:
        print("\nCenas Sentinel-2 selecionadas (em ordem de escolha):")
        for i, it in enumerate(selected, start=1):
            print(f"  {i:02d} - {it.id}")

    return selected

# -------------------------------------------------
# Exemplo de uso completo (AST_07 + S2)
# -------------------------------------------------

def example_downloads(selected_ast07, selected_s2):
    if selected_ast07:
        it_ast = selected_ast07[0]
        print("\n--- AST_07: assets disponíveis na primeira cena selecionada ---")
        print_item_assets(it_ast)

        ast_key, _ = pick_fullres_asset(it_ast)
        if ast_key is not None:
            ast_path = download_asset(it_ast, ast_key, "./AST07_raw")
            print("AST_07 bruto baixado em:", ast_path)
        else:
            print("Não foi possível inferir um asset de dado AST_07.")

    if selected_s2:
        it_s2 = selected_s2[0]
        print("\n--- Sentinel-2: assets disponíveis na primeira cena selecionada ---")
        print_item_assets(it_s2)

        out_dir_s2 = "./S2_raw"
        bands_rgbn = ["B02", "B03", "B04", "B08"]
        for bk in bands_rgbn:
            if bk in it_s2.assets:
                path = download_asset(it_s2, bk, out_dir_s2)
                print(f"Banda S2 {bk} baixada em: {path}")
            else:
                print(f"Banda {bk} não encontrada em {it_s2.id}")


def main():
    # bbox da folha em WGS84 (ajuste para sua folha)
    bbox_wgs84 = (-56.25, -6.125, -56.125, -6.0)
    target_date_str = "2008-06-15"
    target_dt = datetime.fromisoformat(target_date_str).replace(tzinfo=timezone.utc)

    print("====================================================")
    print("PIPELINE DE SELEÇÃO DE CENAS: AST_07 (L2) + Sentinel-2")
    print(f"Folha (bbox WGS84): {bbox_wgs84}")
    print(f"Data alvo (aerogeofísica): {target_date_str}")
    print("====================================================")

    print("\n=== ASTER AST_07 (L2 Surface Reflectance V004) ===")
    resultados_ast07 = search_ast07_cloudfiltered(
        bbox=bbox_wgs84,
        datetime=None,
        max_items=200,
        cloud_max=5.0,
        min_coverage=0.90,
    )
    selected_ast07 = select_best_ast07_scenes(
        resultados_ast07,
        bbox_wgs84=bbox_wgs84,
        provider="nasa_lpdaac_lpcloud",
        band_key=None,
        target_date=target_dt,
    )

    print("\n=== Sentinel-2 L2A ===")
    resultados_s2 = search_s2_cloudfiltered(
        bbox=bbox_wgs84,
        datetime=None,
        max_items=300,
        cloud_max=5.0,
        min_coverage=0.95,
    )
    selected_s2 = select_best_s2_scenes(
        resultados_s2,
        bbox_wgs84=bbox_wgs84,
        provider="planetary_computer",
        band_key=None,
        target_date=target_dt,
    )

    print("\n====================================================")
    print("RESUMO DAS CENAS SELECIONADAS")
    print("====================================================\n")

    print("AST_07 (ordem de escolha):")
    for i, it in enumerate(selected_ast07, start=1):
        dt = _get_item_datetime(it)
        print(f"  {i:02d} - {it.id} | datetime={dt}")

    print("\nSentinel-2 (ordem de escolha):")
    for i, it in enumerate(selected_s2, start=1):
        dt = _get_item_datetime(it)
        print(f"  {i:02d} - {it.id} | datetime={dt}")

    print("\n====================================================")
    print("DOWNLOAD DE EXEMPLO DOS DADOS BRUTOS")
    print("====================================================")
    example_downloads(selected_ast07, selected_s2)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
QGIS Console / Plugin helper — STAC → QGIS
Autor: você :)
Funcionalidades:
 - Listar coleções STAC
 - Buscar itens por bbox/WKT/seleção atual/ids de folhas
 - Adicionar assets COG (GeoTIFF) como camadas
 - Criar VRT RGB quando bands 'red','green','blue' existirem
"""

# ========= deps básicos =========
import json, os, tempfile, datetime
from typing import Iterable, Optional, Dict, Any, List

# tenta ter 'requests' no QGIS Python
try:
    import requests
except Exception:
    import sys, subprocess
    py = sys.executable
    subprocess.check_call([py, "-m", "pip", "install", "--user", "requests"])
    import requests

from qgis.core import (
    QgsProject, QgsRasterLayer, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsGeometry, QgsWkbTypes, QgsCoordinateTransformContext, QgsVectorLayer
)
from qgis.PyQt.QtCore import QVariant

# ========= configuração =========
STAC_ENDPOINT = os.environ.get("BDC_STAC_ENDPOINT", "https://data.inpe.br/bdc/stac/v1")
STAC_SEARCH   = STAC_ENDPOINT.rstrip("/") + "/search"
_CTX = QgsProject.instance().transformContext()

# ========= util Geo =========
def geom_to_4326_bbox(geom: QgsGeometry, src_epsg: Optional[int]) -> List[float]:
    """Transforma geom para EPSG:4326 e retorna bbox [minx,miny,maxx,maxy]."""
    if geom is None or geom.isEmpty():
        raise ValueError("Geometria vazia.")
    # infere SRC do layer quando não fornecido
    if src_epsg is None or int(src_epsg) <= 0:
        src_epsg = 4326 if geom.isGeosValid() else 4326
    crs_src = QgsCoordinateReferenceSystem.fromEpsgId(int(src_epsg))
    crs_dst = QgsCoordinateReferenceSystem.fromEpsgId(4326)
    if crs_src.authid() != crs_dst.authid():
        tr = QgsCoordinateTransform(crs_src, crs_dst, _CTX)
        geom = QgsGeometry(geom)  # cópia
        geom.transform(tr)
    rect = geom.boundingBox()
    return [rect.xMinimum(), rect.yMinimum(), rect.xMaximum(), rect.yMaximum()]

def bbox_from_active_selection() -> List[float]:
    """Retorna bbox (EPSG:4326) da seleção da camada ativa do QGIS."""
    layer = iface.activeLayer()
    if not isinstance(layer, QgsVectorLayer):
        raise RuntimeError("Selecione uma camada vetorial ativa com feições.")
    feats = list(layer.getSelectedFeatures())
    if not feats:
        raise RuntimeError("Nenhuma feição selecionada na camada ativa.")
    # une geometrias
    g = None
    for f in feats:
        if f.geometry() and not f.geometry().isEmpty():
            g = f.geometry() if g is None else g.combine(f.geometry())
    if g is None:
        raise RuntimeError("Geometrias inválidas/ausentes na seleção.")
    # descobre EPSG do layer
    crs = layer.crs()
    epsg = crs.postgisSrid() if crs.isValid() else 4326
    return geom_to_4326_bbox(g, epsg)

def bbox_from_wkt(wkt: str, src_epsg: int) -> List[float]:
    """Retorna bbox (EPSG:4326) a partir de um WKT e EPSG de origem."""
    g = QgsGeometry.fromWkt(wkt)
    if g.isEmpty():
        raise ValueError("WKT inválido.")
    return geom_to_4326_bbox(g, src_epsg)

def bbox_from_malha_ids(layer_name: str, ids: Iterable[str], id_field: str = "id_folha") -> List[float]:
    """
    Faz união das geometrias cujos id_field ∈ ids em uma camada da malha (por nome),
    e retorna o bbox em EPSG:4326.
    """
    layer = None
    for lyr in QgsProject.instance().mapLayers().values():
        if isinstance(lyr, QgsVectorLayer) and lyr.name() == layer_name:
            layer = lyr; break
    if layer is None:
        raise RuntimeError(f"Camada '{layer_name}' não encontrada no projeto.")
    expr = f"\"{id_field}\" IN ({','.join([repr(i) for i in ids])})"
    req = layer.getFeatures(expr)
    g = None; count=0
    for f in req:
        if f.geometry() and not f.geometry().isEmpty():
            g = f.geometry() if g is None else g.combine(f.geometry())
            count += 1
    if count == 0:
        raise RuntimeError("Nenhuma folha encontrada com os IDs informados.")
    epsg = layer.crs().postgisSrid() if layer.crs().isValid() else 4326
    return geom_to_4326_bbox(g, epsg)

# ========= STAC HTTP helpers =========
def stac_list_collections() -> List[Dict[str, Any]]:
    url = STAC_ENDPOINT.rstrip("/") + "/collections"
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    data = r.json()
    cols = data.get("collections", [])
    # retorna id e title pra ficar leve
    return [{"id": c.get("id"), "title": c.get("title")} for c in cols]

def stac_search(
    collections: Iterable[str],
    bbox: Optional[List[float]] = None,
    intersects: Optional[Dict[str, Any]] = None,
    limit: int = 10,
    sortby_field: str = "properties.datetime",
    direction: str = "desc",
    datetime_range: Optional[str] = None,
    query: Optional[Dict[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """
    Faz POST /search no STAC. Retorna lista de Features (itens).
    - collections: ids ex.: ['CB4A-WPM-PCA-FUSED-1','LANDSAT-8-L2']
    - bbox: [minx,miny,maxx,maxy] em lon/lat
    - intersects: GeoJSON geometry (opcional)
    - datetime_range: 'YYYY-MM-DD/YYYY-MM-DD' ou '.../..', etc.
    - query: STAC 'query' extra (dicionário)
    """
    payload = {
        "collections": list(collections),
        "limit": int(limit),
        "sortby": [{"field": sortby_field, "direction": direction}],
    }
    if bbox: payload["bbox"] = bbox
    if intersects: payload["intersects"] = intersects
    if datetime_range: payload["datetime"] = datetime_range
    if query: payload["query"] = query

    r = requests.post(STAC_SEARCH, json=payload, timeout=60, headers={"Content-Type":"application/json"})
    r.raise_for_status()
    data = r.json()
    feats = data.get("features", [])
    return feats

# ========= QGIS adiciona assets =========
def _is_cog_asset(asset: Dict[str, Any]) -> bool:
    t = (asset.get("type") or "").lower()
    href = (asset.get("href") or "").lower()
    if "geotiff" in t or t.startswith("image/tiff"):
        return True
    # fallback por extensão (nem sempre tem 'type')
    return href.endswith(".tif") or href.endswith(".tiff")

def _asset_role_ok(asset: Dict[str, Any]) -> bool:
    roles = asset.get("roles") or []
    # preferir 'data'/'analytic'; evitar 'thumbnail','overview','metadata'
    bad = {"thumbnail", "overview", "metadata", "qa"}
    return not any(r in bad for r in roles)

def _vsicurl_url(href: str) -> str:
    # GDAL entende /vsicurl para COG streaming
    if href.startswith("/vsicurl/"):
        return href
    if href.startswith("http://") or href.startswith("https://"):
        return "/vsicurl/" + href
    return href

def _make_safe_name(s: str) -> str:
    return "".join(c if c.isalnum() or c in ("-","_","."," ") else "_" for c in (s or ""))[:128]

def add_stac_item_to_qgis(
    item: Dict[str, Any],
    group_name: Optional[str] = None,
    only_cog: bool = True,
    make_rgb_vrt: bool = True,
) -> List[QgsRasterLayer]:
    """
    Adiciona todos os assets relevantes de um item STAC como camadas raster.
    Cria um grupo no Layer Tree. Se bands RGB existirem, cria também um VRT RGB.
    Retorna lista de camadas adicionadas.
    """
    assets = item.get("assets", {}) or {}
    if not assets:
        return []

    # nome do grupo
    coll = (item.get("collection") or "").strip()
    dt   = (item.get("properties", {}).get("datetime") or
            item.get("properties", {}).get("start_datetime") or "")
    try:
        dt_h = datetime.datetime.fromisoformat(str(dt).replace("Z","")).strftime("%Y-%m-%d")
    except Exception:
        dt_h = str(dt)[:10] if dt else "nodatetime"
    item_id = item.get("id") or "item"
    gname = group_name or f"STAC/{coll}/{dt_h}/{item_id}"
    root = QgsProject.instance().layerTreeRoot()
    grp = root.insertGroup(0, gname)

    # coleta assets válidos
    added = []
    rgb_candidates = {"red":None, "green":None, "blue":None}

    for key, asset in assets.items():
        if not _asset_role_ok(asset):
            continue
        if only_cog and not _is_cog_asset(asset):
            continue
        href = asset.get("href")
        if not href:
            continue
        name = _make_safe_name(f"{key}")
        # tenta com URL direto; se falhar, /vsicurl/
        lyr = QgsRasterLayer(href, name, "gdal")
        if not lyr.isValid():
            lyr = QgsRasterLayer(_vsicurl_url(href), name, "gdal")
        if lyr.isValid():
            QgsProject.instance().addMapLayer(lyr, False)
            grp.addLayer(lyr)
            added.append(lyr)

            # tenta detectar common_name pra RGB
            bands_meta = asset.get("eo:bands") or asset.get("raster:bands") or []
            # algumas coleções trazem 'common_name' diretamente em eo:bands
            for b in bands_meta:
                cn = (b.get("common_name") or "").lower().strip()
                if cn in rgb_candidates and rgb_candidates[cn] is None:
                    rgb_candidates[cn] = lyr.source()

        # sem eo:bands? heurística por nome da banda
        lowk = key.lower()
        if any(v is None for v in rgb_candidates.values()):
            if "red" in lowk or lowk.endswith("b04") or lowk.endswith("b4"):
                rgb_candidates["red"] = rgb_candidates["red"] or lyr.source()
            if "green" in lowk or lowk.endswith("b03") or lowk.endswith("b3"):
                rgb_candidates["green"] = rgb_candidates["green"] or lyr.source()
            if "blue" in lowk or lowk.endswith("b02") or lowk.endswith("b2"):
                rgb_candidates["blue"] = rgb_candidates["blue"] or lyr.source()

    # cria VRT RGB se possível
    if make_rgb_vrt and all(rgb_candidates.values()):
        vrt_path = _write_rgb_vrt(rgb_candidates["red"], rgb_candidates["green"], rgb_candidates["blue"])
        if vrt_path and os.path.exists(vrt_path):
            rgb_name = _make_safe_name(f"{coll}_{dt_h}_{item_id}_RGB")
            rgb_layer = QgsRasterLayer(vrt_path, rgb_name, "gdal")
            if rgb_layer.isValid():
                QgsProject.instance().addMapLayer(rgb_layer, False)
                grp.insertLayer(0, rgb_layer)  # no topo do grupo
                added.insert(0, rgb_layer)

    return added

def _write_rgb_vrt(r_href: str, g_href: str, b_href: str) -> Optional[str]:
    """
    Escreve um VRT 3 bandas (RGB) com os 3 hrefs (aceita /vsicurl/http...).
    Não chama gdalbuildvrt; gera XML mínimo pra leitura.
    """
    def gdal_safe(h):
        # GDAL lê absoluto/HTTP; se não, prefixa /vsicurl/
        return _vsicurl_url(h) if h.startswith("http") else h

    template = f"""<VRTDataset rasterXSize="0" rasterYSize="0">
  <VRTRasterBand dataType="Float32" band="1">
    <ColorInterp>Red</ColorInterp>
    <ComplexSource>
      <SourceFilename relativeToVRT="0">{gdal_safe(r_href)}</SourceFilename>
      <SourceBand>1</SourceBand>
    </ComplexSource>
  </VRTRasterBand>
  <VRTRasterBand dataType="Float32" band="2">
    <ColorInterp>Green</ColorInterp>
    <ComplexSource>
      <SourceFilename relativeToVRT="0">{gdal_safe(g_href)}</SourceFilename>
      <SourceBand>1</SourceBand>
    </ComplexSource>
  </VRTRasterBand>
  <VRTRasterBand dataType="Float32" band="3">
    <ColorInterp>Blue</ColorInterp>
    <ComplexSource>
      <SourceFilename relativeToVRT="0">{gdal_safe(b_href)}</SourceFilename>
      <SourceBand>1</SourceBand>
    </ComplexSource>
  </VRTRasterBand>
</VRTDataset>"""
    tmp = tempfile.NamedTemporaryFile(prefix="stac_rgb_", suffix=".vrt", delete=False)
    tmp.write(template.encode("utf-8")); tmp.flush(); tmp.close()
    return tmp.name

# ========= fluxos prontos =========
def add_oldest_and_newest_from_area(
    collections: Iterable[str],
    bbox_4326: List[float],
    limit_each: int = 1,
    group_prefix: str = "STAC/AREAx",
) -> Dict[str, List[QgsRasterLayer]]:
    """
    Busca o ITEM mais antigo e o mais novo em 'collections' para o bbox e adiciona ao QGIS.
    Retorna {'oldest': [layers...], 'newest': [layers...]}.
    """
    out = {"oldest": [], "newest": []}
    # mais antigo
    old = stac_search(collections, bbox=bbox_4326, limit=limit_each,
                      sortby_field="properties.datetime", direction="asc")
    if old:
        for i, it in enumerate(old, 1):
            out["oldest"] += add_stac_item_to_qgis(it, group_name=f"{group_prefix}/oldest_{i}")
    # mais novo
    new = stac_search(collections, bbox=bbox_4326, limit=limit_each,
                      sortby_field="properties.datetime", direction="desc")
    if new:
        for i, it in enumerate(new, 1):
            out["newest"] += add_stac_item_to_qgis(it, group_name=f"{group_prefix}/newest_{i}")
    return out

# ========= exemplos rápidos (copie/cole conforme o caso) =========
if False:
    # 1) Listar coleções e filtrar por 'landsat' / 'cbers'
    cols = stac_list_collections()
    print([c for c in cols if "landsat" in (c["id"] or "").lower() or "cbers" in (c["id"] or "").lower()])

    # 2) BBOX a partir da seleção atual do QGIS
    bbox = bbox_from_active_selection()
    print("bbox 4326:", bbox)

    # 3) Itens mais antigo e mais novo da CBERS-4A FUSED 2 m na área
    layers_by_when = add_oldest_and_newest_from_area(
        collections=["CB4A-WPM-PCA-FUSED-1"],  # ajuste para a coleção desejada
        bbox_4326=bbox,
        limit_each=1,
        group_prefix="STAC/CB4A_FUSED"
    )

    # 4) Busca genérica + adicionar primeiro item completamente
    items = stac_search(["LANDSAT-8-L2","LANDSAT-9-L2"], bbox=bbox, limit=3)
    if items:
        add_stac_item_to_qgis(items[0], group_name="STAC/L8L9/exemplo")

    # 5) Usando WKT + EPSG conhecido
    wkt = "POLYGON((-46.875 -23.75,-46.75 -23.75,-46.75 -23.875,-46.875 -23.875,-46.875 -23.75))"
    bbox2 = bbox_from_wkt(wkt, src_epsg=4326)
    add_oldest_and_newest_from_area(["CB4A-WPM-PCA-FUSED-1"], bbox2, group_prefix="STAC/CB4A_WKT")

    # 6) Usando nomes de folhas da tua malha já carregada no QGIS
    bbox3 = bbox_from_malha_ids(layer_name="MalhaCartografica", ids=["SF23_YC_VI3_NE"])
    add_oldest_and_newest_from_area(["CB4A-WPM-PCA-FUSED-1"], bbox3, group_prefix="STAC/CB4A_Folha")

print("STAC helpers carregados. Use: stac_list_collections(), stac_search(), add_stac_item_to_qgis(), add_oldest_and_newest_from_area(), bbox_*")

cols = stac_list_collections()
bbox = bbox_from_active_selection()
layers_by_when = add_oldest_and_newest_from_area(
    collections=["CB4A-WPM-PCA-FUSED-1"],  # CBERS-4A Fused 2 m
    bbox_4326=bbox,
    limit_each=1,
    group_prefix="STAC/CB4A_2m"
)
print({k: [lyr.name() for lyr in v] for k, v in layers_by_when.items()})

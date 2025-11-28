# -*- coding: utf-8 -*-
# QGIS 3.44 – Visualização ASTER (Earthdata/LP DAAC via earthaccess)

from __future__ import annotations

import os
import json
import tempfile
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from urllib.parse import urlparse

import requests
import earthaccess as ea
from osgeo import gdal

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import (
    QgsProject,
    QgsRasterLayer,
    QgsJsonUtils,
    QgsCoordinateReferenceSystem,
)
from qgis.utils import iface

from db_conn import get_folha_geom_geojson


def log(msg):
    print(datetime.now().strftime("[%H:%M:%S] "), msg)


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


def _get_granule_bbox_from_umm(umm: Dict[str, Any]) -> Tuple[float, float, float, float]:
    geom_umm = (
        umm.get("SpatialExtent", {})
           .get("HorizontalSpatialDomain", {})
           .get("Geometry", {})
    )

    rects = geom_umm.get("BoundingRectangles") or geom_umm.get("BoundingRectangle")
    if isinstance(rects, list) and rects:
        r = rects[0]
        west = float(r["WestBoundingCoordinate"])
        east = float(r["EastBoundingCoordinate"])
        south = float(r["SouthBoundingCoordinate"])
        north = float(r["NorthBoundingCoordinate"])
        return west, south, east, north
    elif isinstance(rects, dict):
        west = float(rects["WestBoundingCoordinate"])
        east = float(rects["EastBoundingCoordinate"])
        south = float(rects["SouthBoundingCoordinate"])
        north = float(rects["NorthBoundingCoordinate"])
        return west, south, east, north

    gpolys = geom_umm.get("GPolygons") or geom_umm.get("GPolygon")
    if isinstance(gpolys, list):
        gpoly_list = gpolys
    elif isinstance(gpolys, dict):
        gpoly_list = [gpolys]
    else:
        raise RuntimeError("Nenhuma BoundingRectangle ou GPolygon no UMM.")

    lons, lats = [], []
    for gp in gpoly_list:
        boundary = gp.get("Boundary", {})
        points = boundary.get("Points") or boundary.get("Point") or []
        for p in points:
            lon = p.get("Longitude")
            lat = p.get("Latitude")
            if lon is not None and lat is not None:
                lons.append(float(lon))
                lats.append(float(lat))

    if not lons:
        raise RuntimeError("Não foi possível extrair coordenadas de GPolygons no UMM.")

    west = min(lons)
    east = max(lons)
    south = min(lats)
    north = max(lats)
    return west, south, east, north


def _get_folha_geom_and_bbox(folha_id: str) -> Tuple[Dict[str, Any], Tuple[float, float, float, float]]:
    geom_geojson = get_folha_geom_geojson(folha_id)
    json_str = json.dumps(geom_geojson)
    g = QgsJsonUtils.geometryFromGeoJson(json_str)
    if g is None or g.isEmpty():
        raise RuntimeError(f"Não foi possível converter a geometria da folha '{folha_id}' para QgsGeometry.")
    bb = g.boundingBox()
    bbox = (
        float(bb.xMinimum()),
        float(bb.yMinimum()),
        float(bb.xMaximum()),
        float(bb.yMaximum()),
    )
    return geom_geojson, bbox


def _write_world_file(raster_path: str, west: float, south: float, east: float, north: float,
                      width: int, height: int) -> str:
    px = (east - west) / float(width)
    py = (north - south) / float(height)

    A = px
    D = 0.0
    B = 0.0
    E = -py
    C = west + px / 2.0
    F = north - py / 2.0

    base, ext = os.path.splitext(raster_path)
    ext = ext.lower()

    if ext in (".jpg", ".jpeg"):
        wld_path = base + ".jgw"
    elif ext == ".png":
        wld_path = base + ".pgw"
    elif ext in (".tif", ".tiff"):
        wld_path = base + ".tfw"
    else:
        wld_path = base + ".wld"

    with open(wld_path, "w", encoding="ascii") as f:
        f.write(f"{A}\n{D}\n{B}\n{E}\n{C}\n{F}\n")
    return wld_path


def _clip_raster_to_folha(raster_path: str, folha_geom_geojson: Dict[str, Any]) -> str:
    base, ext = os.path.splitext(raster_path)
    out_path = base + "_clip" + ext
    tmp_geojson = base + "_aoi.geojson"

    fc = {
        "type": "FeatureCollection",
        "features": [
            {"type": "Feature", "properties": {}, "geometry": folha_geom_geojson}
        ],
    }
    with open(tmp_geojson, "w", encoding="utf-8") as f:
        json.dump(fc, f)

    gdal.UseExceptions()
    warp_opts = gdal.WarpOptions(
        cutlineDSName=tmp_geojson,
        cropToCutline=True,
    )
    gdal.Warp(destNameOrDestDS=out_path, srcDSOrSrcDSTab=raster_path, options=warp_opts)
    return out_path


def search_aster_granules_for_folha(
    folha_id: str,
    product: str,
    version: str,
    start_date: str,
    end_date: str,
    cloud_max: Optional[float],
    max_items: int = 50,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    log("[ASTER] Autenticando no Earthdata via earthaccess.login()...")
    auth = ea.login()
    if not auth.authenticated:
        raise RuntimeError("Falha na autenticação Earthdata.")

    geom_geojson, bbox = _get_folha_geom_and_bbox(folha_id)
    log(f"[ASTER] folha_id={folha_id} bbox={bbox}")
    log(f"[ASTER] product={product}.{version} intervalo=({start_date},{end_date}) max_items={max_items} cloud_max={cloud_max}")

    results = ea.search_data(
        short_name=product,
        version=version,
        bounding_box=bbox,
        temporal=(start_date, end_date),
        count=max_items,
        cloud_hosted=True,
    )
    log(f"[ASTER] Granules retornados: {len(results)}")

    candidatos: List[Dict[str, Any]] = []

    for g in results:
        umm = g.get("umm", {})
        granule_ur = umm.get("GranuleUR", g.get("meta", {}).get("native-id", ""))

        t0 = _parse_datetime_from_umm(g)
        cloud = _parse_cloud_from_umm(umm)
        if cloud_max is not None and cloud is not None and cloud > cloud_max:
            continue

        preview_url: Optional[str] = None
        try:
            viz_links = g.dataviz_links()
            if viz_links:
                preview_url = viz_links[0]
        except Exception:
            preview_url = None

        try:
            west, south, east, north = _get_granule_bbox_from_umm(umm)
        except Exception as e:
            log(f"[ASTER] Aviso: não foi possível extrair bbox de {granule_ur}: {e}")
            continue

        candidatos.append(
            {
                "granule": g,
                "granule_ur": granule_ur,
                "datetime": t0,
                "cloud": cloud,
                "preview_url": preview_url,
                "granule_bbox": (west, south, east, north),
            }
        )

    if not candidatos:
        log("[ASTER] Nenhum granule após aplicar filtro de nuvem / bbox.")
        return [], geom_geojson

    candidatos.sort(
        key=lambda c: (
            9999.0 if c["cloud"] is None else float(c["cloud"]),
            c["datetime"] or datetime.max,
        )
    )

    log("[ASTER] Cenas (ordenadas por nuvem crescente):")
    for i, c in enumerate(candidatos[:20]):
        dt = c["datetime"].isoformat() if isinstance(c["datetime"], datetime) else "None"
        cloud_str = "None" if c["cloud"] is None else f"{c['cloud']:.1f}"
        log(f"  [{i}] id={c['granule_ur']} datetime={dt} cloud={cloud_str} preview={'OK' if c['preview_url'] else 'None'}")

    return candidatos, geom_geojson


class AsterEarthdataDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ASTER – Earthdata (folha → lista → preview/recorte)")
        self.resize(900, 600)

        self._candidates: List[Dict[str, Any]] = []
        self._geom_folha_geojson: Optional[Dict[str, Any]] = None

        self.cbProduct = QtWidgets.QComboBox()
        self.cbProduct.addItem("AST_L1T v003 (L1T radiância)", ("AST_L1T", "003"))
        self.cbProduct.addItem("AST_07 v004 (reflectância VNIR/SWIR)", ("AST_07", "004"))
        self.cbProduct.addItem("Custom (short_name.version)", None)

        self.edCustomProd = QtWidgets.QLineEdit()
        self.edCustomProd.setPlaceholderText("ex.: AST_L1T.003")
        self.edCustomProd.setEnabled(False)

        self.edFolha = QtWidgets.QLineEdit()
        self.edFolha.setPlaceholderText("Código da folha, ex.: SB21_XC_V4_SW")

        today = QtCore.QDate.currentDate()
        self.edStart = QtWidgets.QDateEdit(today.addYears(-20))
        self.edStart.setDisplayFormat("yyyy-MM-dd")
        self.edStart.setCalendarPopup(True)

        self.edEnd = QtWidgets.QDateEdit(today)
        self.edEnd.setDisplayFormat("yyyy-MM-dd")
        self.edEnd.setCalendarPopup(True)

        self.spCloud = QtWidgets.QDoubleSpinBox()
        self.spCloud.setRange(0.0, 100.0)
        self.spCloud.setDecimals(1)
        self.spCloud.setValue(100.0)

        self.spLimit = QtWidgets.QSpinBox()
        self.spLimit.setRange(1, 5000)
        self.spLimit.setValue(100)

        self.btnSearch = QtWidgets.QPushButton("Listar cenas")
        self.btnPreview = QtWidgets.QPushButton("Visualizar preview selecionado")
        self.btnDownloadClip = QtWidgets.QPushButton("Baixar & recortar cena selecionada")

        self.table = QtWidgets.QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["idx", "granule_ur", "datetime", "cloud"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)

        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Coleção ASTER:"))
        top.addWidget(self.cbProduct, 1)
        top.addWidget(self.edCustomProd, 1)

        folha = QtWidgets.QHBoxLayout()
        folha.addWidget(QtWidgets.QLabel("folha_id:"))
        folha.addWidget(self.edFolha, 1)

        par = QtWidgets.QHBoxLayout()
        par.addWidget(QtWidgets.QLabel("Início:"))
        par.addWidget(self.edStart)
        par.addWidget(QtWidgets.QLabel("Fim:"))
        par.addWidget(self.edEnd)
        par.addWidget(QtWidgets.QLabel("Nuvem <= "))
        par.addWidget(self.spCloud)
        par.addWidget(QtWidgets.QLabel("Limite:"))
        par.addWidget(self.spLimit)
        par.addWidget(self.btnSearch)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self.btnPreview)
        bottom.addWidget(self.btnDownloadClip)
        bottom.addStretch(1)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(folha)
        lay.addLayout(par)
        lay.addWidget(self.table, 1)
        lay.addLayout(bottom)

        self.cbProduct.currentIndexChanged.connect(self._on_product_change)
        self.btnSearch.clicked.connect(self._on_search)
        self.btnPreview.clicked.connect(self._on_preview)
        self.btnDownloadClip.clicked.connect(self._on_download_clip)

    def _get_product_version(self) -> Tuple[str, str]:
        data = self.cbProduct.currentData()
        if data is not None:
            return data
        txt = self.edCustomProd.text().strip()
        if not txt or "." not in txt:
            raise RuntimeError("Informe short_name.version no campo customizado, ex.: AST_L1T.003")
        short_name, version = txt.split(".", 1)
        return short_name.strip(), version.strip()

    def _on_product_change(self, idx: int):
        data = self.cbProduct.itemData(idx)
        self.edCustomProd.setEnabled(data is None)

    def _selected_row_idx(self) -> Optional[int]:
        sel = self.table.selectedIndexes()
        if not sel:
            return None
        return self.table.item(sel[0].row(), 0).text()

    def _on_search(self):
        folha_id = self.edFolha.text().strip()
        if not folha_id:
            QtWidgets.QMessageBox.warning(self, "Folha", "Informe o código da folha.")
            return
        try:
            product, version = self._get_product_version()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "Coleção", str(e))
            return

        start_date = self.edStart.date().toString("yyyy-MM-dd")
        end_date = self.edEnd.date().toString("yyyy-MM-dd")
        cloud_max = float(self.spCloud.value())
        max_items = int(self.spLimit.value())

        try:
            cands, geom_folha = search_aster_granules_for_folha(
                folha_id=folha_id,
                product=product,
                version=version,
                start_date=start_date,
                end_date=end_date,
                cloud_max=cloud_max,
                max_items=max_items,
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro ASTER", str(e))
            return

        self._candidates = cands
        self._geom_folha_geojson = geom_folha

        self.table.setRowCount(0)
        for i, c in enumerate(cands):
            r = self.table.rowCount()
            self.table.insertRow(r)
            dt = c["datetime"].isoformat() if isinstance(c["datetime"], datetime) else ""
            cloud_str = "" if c["cloud"] is None else f"{c['cloud']:.1f}"
            vals = [str(i), c["granule_ur"], dt, cloud_str]
            for j, v in enumerate(vals):
                self.table.setItem(r, j, QtWidgets.QTableWidgetItem(v))

        QtWidgets.QMessageBox.information(self, "Busca ASTER", f"{len(cands)} cena(s) listada(s).")

    def _on_preview(self):
        if not self._candidates:
            QtWidgets.QMessageBox.information(self, "Preview", "Nenhuma cena listada.")
            return
        idx_str = self._selected_row_idx()
        if idx_str is None:
            QtWidgets.QMessageBox.information(self, "Preview", "Selecione uma linha na tabela.")
            return
        try:
            idx = int(idx_str)
        except ValueError:
            QtWidgets.QMessageBox.information(self, "Preview", "Índice inválido.")
            return
        if idx < 0 or idx >= len(self._candidates):
            QtWidgets.QMessageBox.information(self, "Preview", "Índice fora da faixa.")
            return

        cand = self._candidates[idx]
        if not cand.get("preview_url"):
            QtWidgets.QMessageBox.information(self, "Preview", "Cena sem preview disponível.")
            return

        url = cand["preview_url"]
        granule_ur = cand["granule_ur"]
        west, south, east, north = cand["granule_bbox"]

        try:
            outdir = tempfile.mkdtemp(prefix="aster_preview_")
            path = urlparse(url).path or url
            ext = os.path.splitext(path)[1].lower()
            if not ext:
                ext = ".png"
            local_raster = os.path.join(outdir, granule_ur + ext)

            log(f"[ASTER] Baixando preview: {url} -> {local_raster}")
            with requests.get(url, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(local_raster, "wb") as f:
                    for ch in r.iter_content(1024 * 1024):
                        if ch:
                            f.write(ch)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Preview", f"Erro ao baixar preview:\n{e}")
            return

        try:
            from PIL import Image
            img = Image.open(local_raster)
            width, height = img.size
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Preview", f"Erro ao abrir imagem local:\n{e}")
            return

        _write_world_file(local_raster, west, south, east, north, width, height)

        rl = QgsRasterLayer(local_raster, f"ASTER_preview_{granule_ur}")
        if not rl.isValid():
            QtWidgets.QMessageBox.critical(self, "Preview", "Raster layer inválido (preview).")
            return

        rl.setCrs(QgsCoordinateReferenceSystem("EPSG:4326"))
        QgsProject.instance().addMapLayer(rl)

        iface.mapCanvas().setExtent(rl.extent())
        iface.mapCanvas().refresh()

        QtWidgets.QMessageBox.information(self, "Preview", "Preview adicionada ao mapa.")

    def _on_download_clip(self):
        if not self._candidates:
            QtWidgets.QMessageBox.information(self, "Download/Recorte", "Nenhuma cena listada.")
            return
        idx_str = self._selected_row_idx()
        if idx_str is None:
            QtWidgets.QMessageBox.information(self, "Download/Recorte", "Selecione uma linha na tabela.")
            return
        try:
            idx = int(idx_str)
        except ValueError:
            QtWidgets.QMessageBox.information(self, "Download/Recorte", "Índice inválido.")
            return
        if idx < 0 or idx >= len(self._candidates):
            QtWidgets.QMessageBox.information(self, "Download/Recorte", "Índice fora da faixa.")
            return

        if not self._geom_folha_geojson:
            folha_id = self.edFolha.text().strip()
            if not folha_id:
                QtWidgets.QMessageBox.warning(self, "Folha", "Informe o código da folha.")
                return
            geom, _ = _get_folha_geom_and_bbox(folha_id)
            self._geom_folha_geojson = geom

        cand = self._candidates[idx]
        granule = cand["granule"]
        granule_ur = cand["granule_ur"]

        try:
            outdir = tempfile.mkdtemp(prefix="aster_data_")
            log(f"[ASTER] Download da cena real para {outdir}")
            files = ea.download([granule], local_path=outdir)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Download", f"Erro no download via earthaccess:\n{e}")
            return

        if not files:
            QtWidgets.QMessageBox.critical(self, "Download", "Nenhum arquivo retornado pelo earthaccess.")
            return

        paths = [str(p) for p in files]
        tif_paths = [p for p in paths if p.lower().endswith((".tif", ".tiff"))]
        raster_path = tif_paths[0] if tif_paths else paths[0]

        if not os.path.isfile(raster_path):
            QtWidgets.QMessageBox.critical(self, "Download", f"Arquivo não encontrado:\n{raster_path}")
            return

        try:
            clip_path = _clip_raster_to_folha(raster_path, self._geom_folha_geojson)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Recorte", f"Erro ao recortar com GDAL/Warp:\n{e}")
            return

        rl = QgsRasterLayer(clip_path, f"ASTER_clip_{granule_ur}")
        if not rl.isValid():
            QtWidgets.QMessageBox.critical(self, "Recorte", "Raster layer inválido (recorte).")
            return

        QgsProject.instance().addMapLayer(rl)
        iface.mapCanvas().setExtent(rl.extent())
        iface.mapCanvas().refresh()

        QtWidgets.QMessageBox.information(
            self,
            "Download/Recorte",
            f"Cena recortada adicionada ao mapa.\nArquivo: {clip_path}",
        )


def run_aster_dialog():
    dlg = AsterEarthdataDialog()
    dlg.show()
    globals()["__ASTER_EARTHDATA_DLG__"] = dlg


run_aster_dialog()

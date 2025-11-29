# -*- coding: utf-8 -*-
# QGIS 3.44 – Catálogo BDC STAC + ASTER_07XT (earthaccess)
# Requisitos extras p/ ASTER: earthaccess (EDL), osgeo.gdal, requests.

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import (
    QgsGeometry,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsGeometryUtils,
    QgsVectorLayer,
    QgsRasterLayer,
    QgsPointXY,
    QgsFeature,
)
from qgis.utils import iface

import csv
import json
import os
import re
import tempfile
from datetime import datetime

import requests
from osgeo import gdal

import earthaccess as ea  # ASTER_07XT via earthaccess

DEFAULT_STAC = "https://data.inpe.br/bdc/stac/v1/"
ASTER_STAC = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD"


# -------------------- util/log --------------------
def log(msg):
    print(datetime.now().strftime("[%H:%M:%S] "), msg)


def safe_json(obj):
    return json.dumps(obj, ensure_ascii=False)


# -------------------- quadricula.csv --------------------
def read_grid_csv(csv_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if not r.get("wkt_geom") or not r.get("EPSG"):
                continue
            rows.append(
                {
                    "id_folha": r.get("id_folha", ""),
                    "epsg": int(r["EPSG"]),
                    "wkt": r["wkt_geom"],
                }
            )
    if not rows:
        raise RuntimeError("CSV vazio ou sem colunas id_folha, EPSG, wkt_geom.")
    log(f"[CSV] OK: {len(rows)} linhas.")
    return rows


def _looks_like_lonlat(g):
    try:
        p = g.centroid().asPoint()
        return -180 <= p.x() <= 180 and -90 <= p.y() <= 90
    except Exception:
        return False


def aoi_from_grid(rows):
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    geoms = []
    for i, r in enumerate(rows, 1):
        g = QgsGeometry.fromWkt(r["wkt"])
        src = QgsCoordinateReferenceSystem(f"EPSG:{r['epsg']}")
        use = src
        if src != wgs84:
            if _looks_like_lonlat(g) and src.authid() not in ("EPSG:4326", "EPSG:4674"):
                log(f"[CSV] AVISO linha {i} ({r['id_folha']}): coords parecem graus; usando 4326.")
                use = wgs84
            tr = QgsCoordinateTransform(use, wgs84, QgsProject.instance())
            g2 = QgsGeometry(g)
            g2.transform(tr)
            g = g2
        bb = g.boundingBox()
        c = g.centroid().asPoint()
        log(
            f"[CSV] {i:02d} {r['id_folha']} "
            f"bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
            f"centroid=({c.x():.6f},{c.y():.6f})"
        )
        geoms.append(g)
    aoi = (
        QgsGeometryUtils.combineGeometry(geoms)
        if hasattr(QgsGeometryUtils, "combineGeometry")
        else QgsGeometry.unaryUnion(geoms)
    )
    bb = aoi.boundingBox()
    c = aoi.centroid().asPoint()
    log(
        f"[CSV] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
        f"centroid=({c.x():.6f},{c.y():.6f})"
    )
    return aoi


def aoi_from_active_selection():
    lyr = iface.activeLayer()
    if not isinstance(lyr, QgsVectorLayer):
        raise RuntimeError("Camada ativa não é vetorial. Selecione feições em uma camada vetorial.")
    sel = lyr.selectedFeatures()
    if not sel:
        raise RuntimeError("Nenhuma feição selecionada.")
    wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
    tr = QgsCoordinateTransform(lyr.crs() or QgsProject.instance().crs(), wgs84, QgsProject.instance())
    geoms = []
    for i, ft in enumerate(sel, 1):
        g = ft.geometry()
        g2 = QgsGeometry(g)
        g2.transform(tr)
        bb = g2.boundingBox()
        c = g2.centroid().asPoint()
        log(
            f"[SEL] {i:02d} "
            f"bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
            f"centroid=({c.x():.6f},{c.y():.6f})"
        )
        geoms.append(g2)
    aoi = (
        QgsGeometryUtils.combineGeometry(geoms)
        if hasattr(QgsGeometryUtils, "combineGeometry")
        else QgsGeometry.unaryUnion(geoms)
    )
    bb = aoi.boundingBox()
    c = aoi.centroid().asPoint()
    log(
        f"[SEL] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
        f"centroid=({c.x():.6f},{c.y():.6f})"
    )
    return aoi


def geojson_from_qgsgeom(g):
    return json.loads(g.asJson())


# -------------------- STAC GENÉRICO --------------------
def fetch_collections(stac_url):
    url = stac_url.rstrip("/") + "/collections"
    log(f"GET {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    cols = r.json().get("collections", [])
    log(f"{len(cols)} coleções carregadas.")
    out = []
    for c in cols:
        sm = c.get("summaries", {}) or {}
        out.append(
            {
                "id": c.get("id", ""),
                "title": c.get("title", "") or "",
                "description": c.get("description", "") or "",
                "summaries": sm,
                "has_cloud_cover": "eo:cloud_cover" in sm,
            }
        )
    return out


def stac_search(stac_url, collections, aoi_geojson, datetime_str, max_cloud=None, limit=100, sort="desc"):
    url = stac_url.rstrip("/") + "/search"
    body = {
        "collections": collections,
        "intersects": aoi_geojson,
        "datetime": datetime_str,
        "limit": int(limit),
        "sortby": [{"field": "properties.datetime", "direction": sort}],
    }
    if max_cloud is not None:
        body.setdefault("query", {})["eo:cloud_cover"] = {"lt": float(max_cloud)}
    log("POST " + url)
    log("Body: " + safe_json(body))
    r = requests.post(url, json=body, timeout=120, headers={"Content-Type": "application/json"})
    log(f"HTTP {r.status_code}")
    r.raise_for_status()
    return r.json()


# -------------------- abrir/baixar assets --------------------
def choose_tif_asset(assets: dict):
    for k in sorted(assets.keys()):
        href = assets[k].get("href", "")
        if href and re.search(r"\.tif(f)?$", href, re.I) and "thumb" not in k.lower() and "overview" not in k.lower():
            return k, href
    return None, None


def gdal_tune_for_http():
    gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", "tif,tiff")
    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "YES")
    gdal.SetConfigOption("GDAL_HTTP_MAX_RETRY", "3")
    gdal.SetConfigOption("GDAL_HTTP_MULTIRANGE", "YES")


def open_raster(href, name=None, outdir=None, just_download=False):
    gdal_tune_for_http()
    name = name or os.path.basename(href)
    vsicurl = "/vsicurl/" + href
    if not just_download:
        log(f"Tentando abrir via /vsicurl/: {href}")
        rl = QgsRasterLayer(vsicurl, name, "gdal")
        if rl.isValid():
            QgsProject.instance().addMapLayer(rl)
            return True
        log("Falhou /vsicurl — tentando baixar para disco…")
    try:
        outdir = outdir or tempfile.gettempdir()
        os.makedirs(outdir, exist_ok=True)
        local = os.path.join(outdir, os.path.basename(href))
        log(f"Baixando: {local}")
        with requests.get(href, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(local, "wb") as f:
                for ch in r.iter_content(1024 * 1024):
                    if ch:
                        f.write(ch)
        if just_download:
            return True
        rl2 = QgsRasterLayer(local, name, "gdal")
        if rl2.isValid():
            QgsProject.instance().addMapLayer(rl2)
            return True
        log("GDAL não validou a camada (mesmo local).")
        return False
    except Exception as e:
        log(f"Erro no download: {e}")
        return False


# -------------------- GUI --------------------
class BDCDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("BDC/ASTER – Listar/Filtrar/Selecionar dados (quadícula)")
        self.resize(1000, 680)

        # provider
        self.cbProvider = QtWidgets.QComboBox()
        self.cbProvider.addItem("BDC (INPE)", DEFAULT_STAC)
        self.cbProvider.addItem("ASTER (LP DAAC STAC)", ASTER_STAC)
        self.cbProvider.addItem("Personalizado", "")
        self.cbProvider.setToolTip(
            "Catálogo STAC: BDC ou ASTER (LP DAAC). Para outro, use Personalizado.\n"
            "Para AST_07XT, a busca pode usar earthaccess (point no centróide da folha)."
        )

        self.edStac = QtWidgets.QLineEdit(DEFAULT_STAC)
        self.edStac.setToolTip(
            "URL do catálogo STAC. Em catálogos sem eo:cloud_cover (ex.: LPCLOUD/ASTER), "
            "o filtro de nuvem STAC é ignorado, mas AST_07XT pode usar earthaccess."
        )
        self.btnCols = QtWidgets.QPushButton("Carregar coleções")
        self.edFilter = QtWidgets.QLineEdit()
        self.edFilter.setPlaceholderText("filtrar coleções… ex.: landsat, cbers, sentinel…")
        self.btnApplyFilter = QtWidgets.QPushButton("Aplicar filtro")
        self.btnSelectAll = QtWidgets.QPushButton("Selecionar todas")

        self.listCols = QtWidgets.QListWidget()
        self.listCols.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listCols.setAlternatingRowColors(True)

        # origem AOI
        self.rbSel = QtWidgets.QRadioButton("Usar seleção da camada ativa")
        self.rbCsv = QtWidgets.QRadioButton("Usar quadricula.csv")
        self.rbSel.setChecked(True)
        self.btnGrid = QtWidgets.QPushButton("Escolher CSV…")
        self.labGrid = QtWidgets.QLabel("(nenhum)")

        # folha do DB (apenas código – atualizado pela seleção)
        self.edFolha = QtWidgets.QLineEdit()
        self.edFolha.setPlaceholderText("código da folha, ex.: SB21_ZA_II2_NW")

        # parâmetros de busca
        self.edStart = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addMonths(-6))
        self.edStart.setDisplayFormat("yyyy-MM-dd")
        self.edStart.setCalendarPopup(True)
        self.edEnd = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.edEnd.setDisplayFormat("yyyy-MM-dd")
        self.edEnd.setCalendarPopup(True)
        self.spCloud = QtWidgets.QDoubleSpinBox()
        self.spCloud.setRange(0, 100)
        self.spCloud.setDecimals(1)
        self.spCloud.setValue(20.0)
        self.spCloud.setToolTip(
            "Filtro por nuvem (eo:cloud_cover). Em ASTER/earthaccess, usa CloudCover do UMM."
        )
        self.spLimit = QtWidgets.QSpinBox()
        self.spLimit.setRange(1, 10000)
        self.spLimit.setValue(200)
        self.cbAsc = QtWidgets.QCheckBox("Mais antigas primeiro (asc)")

        self.btnProbe = QtWidgets.QPushButton("Provar (1 item/coleção)")
        self.btnSearch = QtWidgets.QPushButton("Listar dados")

        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(
            ["collection", "item_id", "datetime", "cloud_cover", "bbox", "assets", "href_tif", "all_hrefs"]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.btnAdd = QtWidgets.QPushButton("Visualizar selecionados no QGIS")
        self.btnDl = QtWidgets.QPushButton("Baixar selecionados")
        self.cbAllAssets = QtWidgets.QCheckBox("Baixar todos assets dos itens")
        self.btnOutdir = QtWidgets.QPushButton("Pasta de saída…")
        self.labOutdir = QtWidgets.QLabel(os.path.expanduser("~"))

        # layouts
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Catálogo STAC (BDC/ASTER):"))
        top.addWidget(self.cbProvider)
        top.addWidget(self.edStac, 1)
        top.addWidget(self.btnCols)

        filt = QtWidgets.QHBoxLayout()
        filt.addWidget(self.edFilter, 1)
        filt.addWidget(self.btnApplyFilter)
        filt.addWidget(self.btnSelectAll)

        aoi = QtWidgets.QHBoxLayout()
        aoi.addWidget(self.rbSel)
        aoi.addWidget(self.rbCsv)
        aoi.addWidget(self.btnGrid)
        aoi.addWidget(self.labGrid, 1)

        folha_row = QtWidgets.QHBoxLayout()
        folha_row.addWidget(QtWidgets.QLabel("Folha (DB):"))
        folha_row.addWidget(self.edFolha, 1)

        par = QtWidgets.QHBoxLayout()
        par.addWidget(QtWidgets.QLabel("Início:"))
        par.addWidget(self.edStart)
        par.addWidget(QtWidgets.QLabel("Fim:"))
        par.addWidget(self.edEnd)
        par.addWidget(QtWidgets.QLabel("Nuvem <="))
        par.addWidget(self.spCloud)
        par.addWidget(QtWidgets.QLabel("Limite:"))
        par.addWidget(self.spLimit)
        par.addWidget(self.cbAsc)

        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.btnProbe)
        actions.addWidget(self.btnSearch)
        actions.addStretch(1)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self.btnAdd)
        bottom.addWidget(self.btnDl)
        bottom.addWidget(self.cbAllAssets)
        bottom.addStretch(1)
        bottom.addWidget(self.btnOutdir)
        bottom.addWidget(self.labOutdir, 1)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top)
        lay.addLayout(filt)
        lay.addWidget(self.listCols, 1)
        lay.addLayout(aoi)
        lay.addLayout(folha_row)
        lay.addLayout(par)
        lay.addLayout(actions)
        lay.addWidget(self.table, 2)
        lay.addLayout(bottom)

        # estado
        self.rows = None
        self.aoi = None
        self._all_collections = []
        self._ea_logged = False
        self._last_mode = ""  # "stac" ou "aster_ea"
        self._sel_layer = None

        # signals
        self.btnCols.clicked.connect(self.load_collections)
        self.btnApplyFilter.clicked.connect(self.apply_filter)
        self.btnSelectAll.clicked.connect(self.select_all_cols)
        self.btnGrid.clicked.connect(self.pick_grid)
        self.btnProbe.clicked.connect(self.do_probe)
        self.btnSearch.clicked.connect(self.run_search)
        self.btnAdd.clicked.connect(self.view_selected)
        self.btnDl.clicked.connect(self.download_selected)
        self.btnOutdir.clicked.connect(self.pick_outdir)
        self.cbProvider.currentIndexChanged.connect(self._on_provider_change)
        self.edStac.textChanged.connect(self._on_stac_changed)

        # acompanhar seleção da camada ativa p/ atualizar Folha(DB)
        self._connect_layer_selection_signal(iface.activeLayer())
        iface.currentLayerChanged.connect(self._on_current_layer_changed)

    # ---------- helpers de estado ----------
    def _current_stac(self):
        return self.edStac.text().strip()

    def _on_provider_change(self, idx):
        url = self.cbProvider.itemData(idx)
        if url:
            self.edStac.setText(url)

    def _on_stac_changed(self, text):
        for i in range(self.cbProvider.count() - 1):
            if text.strip() == self.cbProvider.itemData(i):
                if self.cbProvider.currentIndex() != i:
                    self.cbProvider.blockSignals(True)
                    self.cbProvider.setCurrentIndex(i)
                    self.cbProvider.blockSignals(False)
                return
        if self.cbProvider.currentIndex() != self.cbProvider.count() - 1:
            self.cbProvider.blockSignals(True)
            self.cbProvider.setCurrentIndex(self.cbProvider.count() - 1)
            self.cbProvider.blockSignals(False)

    def _connect_layer_selection_signal(self, lyr):
        if self._sel_layer is not None:
            try:
                self._sel_layer.selectionChanged.disconnect(self._on_layer_selection_changed)
            except Exception:
                pass
        self._sel_layer = None
        if isinstance(lyr, QgsVectorLayer):
            lyr.selectionChanged.connect(self._on_layer_selection_changed)
            self._sel_layer = lyr

    def _on_current_layer_changed(self, lyr):
        self._connect_layer_selection_signal(lyr)

    def _on_layer_selection_changed(self, selected, deselected, clear_and_select):
        lyr = self._sel_layer
        if not isinstance(lyr, QgsVectorLayer):
            return
        sel = lyr.selectedFeatures()
        if not sel:
            return
        ft = sel[0]
        for name in ("codigo", "id_folha", "folha", "cod_folha"):
            if name in ft.fields().names():
                val = ft[name]
                if val is not None:
                    self.edFolha.setText(str(val))
                break

    def _build_aoi(self, for_probe=False):
        if self.rbSel.isChecked():
            log("AOI ← seleção da camada ativa")
            self.aoi = aoi_from_active_selection()
        else:
            if not self.rows:
                raise RuntimeError("Carregue o CSV de quadícula.")
            log("AOI ← CSV de quadícula")
            self.aoi = aoi_from_grid(self.rows)
        gj = geojson_from_qgsgeom(self.aoi)
        log(("AOI GeoJSON (probe)" if for_probe else "AOI GeoJSON (search)") + " = " + safe_json(gj))
        return gj

    def _selected_collections(self):
        return [
            self.listCols.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.listCols.count())
            if self.listCols.item(i).checkState() == QtCore.Qt.Checked
        ]

    def _collection_meta(self, coll_id):
        for c in self._all_collections:
            if c.get("id") == coll_id:
                return c
        return None

    def _cloud_filter_allowed(self, selected_ids):
        stac = self._current_stac().rstrip("/")
        if stac == DEFAULT_STAC.rstrip("/"):
            return True
        if stac == ASTER_STAC.rstrip("/"):
            # STAC LPCLOUD não tem eo:cloud_cover, mas AST_07XT via earthaccess
            # usa CloudCover internamente; filtro STAC é ignorado.
            return False
        metas = [self._collection_meta(cid) for cid in selected_ids]
        if not metas:
            return False
        return all(m and m.get("has_cloud_cover") for m in metas)

    def _http_error_message(self, err):
        resp = getattr(err, "response", None)
        if not resp:
            return str(err)
        try:
            body = (resp.text or "").strip()
        except Exception:
            body = "<sem corpo>"
        max_len = 1000
        if len(body) > max_len:
            body = body[:max_len] + "…"
        reason = resp.reason or ""
        return f"HTTP {resp.status_code} {reason}\nURL: {resp.url}\nBody: {body or '<vazio>'}"

    # ---------- earthaccess / ASTER_07XT ----------
    def _ensure_ea_login(self):
        if self._ea_logged:
            return True
        try:
            ea.login()  # usa .netrc/credenciais já configuradas
            self._ea_logged = True
            return True
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "earthaccess", f"Falha no login earthaccess:\n{e}")
            return False

    def _umm_datetime(self, umm):
        te = umm.get("TemporalExtent") or {}
        tstr = ""
        if "SingleDateTime" in te:
            tstr = te.get("SingleDateTime") or ""
        else:
            rds = te.get("RangeDateTimes") or []
            if rds:
                tstr = rds[0].get("BeginningDateTime") or ""
        if not tstr:
            return None
        try:
            if tstr.endswith("Z"):
                tstr = tstr.replace("Z", "+00:00")
            return datetime.fromisoformat(tstr)
        except Exception:
            return None

    def _aster_footprint_coords(self, gran):
        try:
            gpolys = (
                gran["umm"]["SpatialExtent"]["HorizontalSpatialDomain"]["Geometry"]["GPolygons"]
                or []
            )
            if not gpolys:
                return []
            pts = gpolys[0]["Boundary"]["Points"]
            coords = [(float(p["Longitude"]), float(p["Latitude"])) for p in pts]
            return coords
        except Exception:
            return []

    def _aster_data_links(self, gran):
        try:
            links = gran.data_links()
        except Exception:
            try:
                links = gran.get("data_links") or []
            except Exception:
                links = []
        return list(links) if links else []

    def _aster_pick_href(self, links):
        if not links:
            return ""
        prefs = ["SRF_SWIR_B04", "SRF_VNIR_B01", "B04", "B01"]
        for key in prefs:
            for h in links:
                if key in h:
                    return h
        return links[0]

    def _update_aster_footprints_layer(self, granules):
        proj = QgsProject.instance()
        name = "ASTER_07XT_footprints"
        for lyr in list(proj.mapLayers().values()):
            if lyr.name() == name:
                proj.removeMapLayer(lyr.id())
        vl = QgsVectorLayer(
            "LineString?crs=EPSG:4326&field=granule_id:string(80)&field=cloud:double&field=datetime:string(32)",
            name,
            "memory",
        )
        pr = vl.dataProvider()
        feats = []
        for g in granules:
            umm = g["umm"]
            iid = umm.get("GranuleUR", "")
            cc = umm.get("CloudCover", None)
            dt = self._umm_datetime(umm)
            coords = self._aster_footprint_coords(g)
            if len(coords) < 2:
                continue
            pts = [QgsPointXY(float(lon), float(lat)) for lon, lat in coords]
            ft = QgsFeature()
            ft.setGeometry(QgsGeometry.fromPolylineXY(pts))
            ft.setAttributes(
                [
                    iid,
                    float(cc) if cc is not None else -1.0,
                    dt.isoformat() if dt else "",
                ]
            )
            feats.append(ft)
        if feats:
            pr.addFeatures(feats)
            vl.updateExtents()
            proj.addMapLayer(vl)
            log(f"[ASTER] Footprints layer: {len(feats)} feições.")

    def _run_search_aster_earthaccess(self):
        if not self._ensure_ea_login():
            return

        try:
            aoi_gj = self._build_aoi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "AOI", str(e))
            return

        if self.aoi is None:
            QtWidgets.QMessageBox.warning(self, "AOI", "AOI não definida.")
            return

        cpt = self.aoi.centroid().asPoint()
        pt = (cpt.x(), cpt.y())
        start = self.edStart.date().toString("yyyy-MM-dd")
        end = self.edEnd.date().toString("yyyy-MM-dd")
        temporal = (start, end)
        cloud_max = float(self.spCloud.value())
        limit = int(self.spLimit.value())

        log(
            f"[ASTER] earthaccess.search_data: point={pt}, "
            f"temporal={temporal}, cloud_max={cloud_max}, limit={limit}"
        )

        res = ea.search_data(
            short_name="AST_07XT",
            version="004",
            cloud_hosted=True,
            point=pt,
            temporal=temporal,
        )

        granules = []
        for g in res:
            umm = g["umm"]
            cc = umm.get("CloudCover", None)
            if cc is not None and float(cc) > cloud_max:
                continue
            granules.append(g)

        def key_fn(g):
            umm = g["umm"]
            cc = umm.get("CloudCover", None)
            ccv = float(cc) if cc is not None else 9999.0
            dt = self._umm_datetime(umm) or datetime.min
            return (ccv, dt)

        granules.sort(key=key_fn, reverse=False)
        if self.cbAsc.isChecked():
            pass  # já em ordem cronológica crescente
        else:
            granules.sort(key=lambda g: self._umm_datetime(g["umm"]) or datetime.min, reverse=True)
        granules = granules[:limit]

        self._last_mode = "aster_ea"
        self._populate_aster_results(granules)
        self._update_aster_footprints_layer(granules)

    def _populate_aster_results(self, granules):
        self.table.setRowCount(0)
        out = []
        for g in granules:
            umm = g["umm"]
            coll = umm.get("CollectionReference", {}).get("ShortName", "AST_07XT")
            iid = umm.get("GranuleUR", "")
            dtm = self._umm_datetime(umm)
            cc = umm.get("CloudCover", "")
            coords = self._aster_footprint_coords(g)
            if coords:
                lons = [c[0] for c in coords]
                lats = [c[1] for c in coords]
                bbox = [min(lons), min(lats), max(lons), max(lats)]
            else:
                bbox = []
            links = self._aster_data_links(g)
            href_tif = self._aster_pick_href(links)
            all_hrefs = links

            r = self.table.rowCount()
            self.table.insertRow(r)
            vals = [
                coll,
                iid,
                dtm.isoformat() if dtm else "",
                str(cc),
                json.dumps(bbox),
                "data_links",
                href_tif or "",
                json.dumps(all_hrefs),
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(v))

            out.append(
                {
                    "collection": coll,
                    "item_id": iid,
                    "datetime": dtm.isoformat() if dtm else "",
                    "cloud_cover": cc,
                    "bbox": json.dumps(bbox),
                    "assets": "data_links",
                    "href_tif": href_tif or "",
                    "all_hrefs": all_hrefs,
                }
            )

        outdir = self.labOutdir.text().strip()
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_csv = os.path.join(outdir, f"aster_07xt_earthaccess_{ts}.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(
                f, fieldnames=["collection", "item_id", "datetime", "cloud_cover", "bbox", "assets", "href_tif", "all_hrefs"]
            )
            wr.writeheader()
            wr.writerows(out)
        log(f"[ASTER] {len(out)} item(ns) encontrados. CSV: {out_csv}")

    # ---------- UI actions ----------
    def load_collections(self):
        try:
            cols = fetch_collections(self._current_stac())
        except requests.exceptions.HTTPError as e:
            QtWidgets.QMessageBox.critical(self, "Erro /collections", self._http_error_message(e))
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro /collections", str(e))
            return

        # acrescenta coleção "virtual" AST_07XT/earthaccess quando estiver no LPCLOUD
        if self._current_stac().rstrip("/") == ASTER_STAC.rstrip("/"):
            cols.append(
                {
                    "id": "AST_07XT",
                    "title": "ASTER 07XT SRF VNIR+SWIR (earthaccess)",
                    "description": "Granules AST_07XT via earthaccess.search_data (point no centróide da folha).",
                    "summaries": {},
                    "has_cloud_cover": True,
                }
            )

        self._all_collections = cols
        self._populate_cols(cols)

    def _populate_cols(self, cols):
        self.listCols.clear()
        for c in cols:
            txt = f"{c['id']} — {c['title']}"
            it = QtWidgets.QListWidgetItem(txt)
            it.setData(QtCore.Qt.UserRole, c["id"])
            desc = (c["description"] or "")[:800]
            if c.get("has_cloud_cover"):
                desc += "\n[cloud cover disponível]"
            else:
                desc += "\n[sem eo:cloud_cover STAC; earthaccess pode tratar CloudCover em ASTER_07XT]"
            it.setToolTip(desc)
            it.setCheckState(QtCore.Qt.Unchecked)
            self.listCols.addItem(it)

    def apply_filter(self):
        if not self._all_collections:
            return
        q = (self.edFilter.text() or "").strip().lower()
        if not q:
            self._populate_cols(self._all_collections)
            return
        keys = re.split(r"[,\s]+", q)

        def ok(c):
            hay = (c["id"] + " " + c["title"] + " " + c["description"]).lower()
            return all(k in hay for k in keys if k)

        self._populate_cols([c for c in self._all_collections if ok(c)])

    def select_all_cols(self):
        for i in range(self.listCols.count()):
            self.listCols.item(i).setCheckState(QtCore.Qt.Checked)

    def pick_grid(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Selecionar quadricula.csv", "", "CSV (*.csv)")
        if not p:
            return
        try:
            self.rows = read_grid_csv(p)
            self.labGrid.setText(p)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "CSV", str(e))

    def pick_outdir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Pasta de saída", self.labOutdir.text())
        if d:
            self.labOutdir.setText(d)

    def do_probe(self):
        cols = self._selected_collections()
        if not cols:
            QtWidgets.QMessageBox.warning(self, "Coleções", "Marque pelo menos uma.")
            return
        try:
            aoi_gj = self._build_aoi(for_probe=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "AOI", str(e))
            return
        dt = f"{self.edStart.date().toString('yyyy-MM-dd')}/{self.edEnd.date().toString('yyyy-MM-dd')}"
        ok, zero = [], []
        for coll in cols:
            try:
                stac_url = self._current_stac().rstrip("/")
                if stac_url == ASTER_STAC.rstrip("/") and coll == "AST_07XT":
                    # probe earthaccess
                    if not self._ensure_ea_login():
                        zero.append(coll)
                        continue
                    cpt = self.aoi.centroid().asPoint()
                    temporal = (
                        self.edStart.date().toString("yyyy-MM-dd"),
                        self.edEnd.date().toString("yyyy-MM-dd"),
                    )
                    res = ea.search_data(
                        short_name="AST_07XT",
                        version="004",
                        cloud_hosted=True,
                        point=(cpt.x(), cpt.y()),
                        temporal=temporal,
                    )
                    (ok if res else zero).append(coll)
                    continue

                allow_cloud = self._cloud_filter_allowed([coll])
                if not allow_cloud:
                    log(f"[PROBE] {coll}: filtro de nuvem STAC omitido.")
                js = stac_search(
                    self._current_stac(),
                    [coll],
                    aoi_gj,
                    dt,
                    max_cloud=float(self.spCloud.value()) if allow_cloud else None,
                    limit=1,
                    sort="asc" if self.cbAsc.isChecked() else "desc",
                )
                (ok if js.get("features") else zero).append(coll)
            except requests.exceptions.HTTPError as e:
                QtWidgets.QMessageBox.critical(self, "Erro /search", f"{coll}: {self._http_error_message(e)}")
                zero.append(coll)
            except Exception:
                zero.append(coll)
        log(f"PROBE: OK={ok} ZERO={zero}")

    def run_search(self):
        cols = self._selected_collections()
        if not cols:
            QtWidgets.QMessageBox.warning(self, "Coleções", "Marque pelo menos uma.")
            return

        stac_url = self._current_stac().rstrip("/")

        # caso especial ASTER_07XT via earthaccess
        if stac_url == ASTER_STAC.rstrip("/") and len(cols) == 1 and cols[0] == "AST_07XT":
            self._run_search_aster_earthaccess()
            return

        try:
            aoi_gj = self._build_aoi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "AOI", str(e))
            return
        dt = f"{self.edStart.date().toString('yyyy-MM-dd')}/{self.edEnd.date().toString('yyyy-MM-dd')}"

        try:
            allow_cloud = self._cloud_filter_allowed(cols)
            if not allow_cloud:
                log("[SEARCH] Filtro de nuvem STAC omitido (coleções/provedor sem eo:cloud_cover).")
            js = stac_search(
                self._current_stac(),
                cols,
                aoi_gj,
                dt,
                max_cloud=float(self.spCloud.value()) if allow_cloud else None,
                limit=int(self.spLimit.value()),
                sort="asc" if self.cbAsc.isChecked() else "desc",
            )
        except requests.exceptions.HTTPError as e:
            QtWidgets.QMessageBox.critical(self, "Erro /search", self._http_error_message(e))
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro /search", str(e))
            return

        self._last_mode = "stac"
        feats = js.get("features", [])
        self.table.setRowCount(0)
        out = []
        for ft in feats:
            props = ft.get("properties", {})
            coll = ft.get("collection", "")
            iid = ft.get("id", "")
            dtm = props.get("datetime", "")
            cc = props.get("eo:cloud_cover", props.get("cloud_cover", ""))
            bbox = ft.get("bbox", "")
            assets = ft.get("assets", {})
            best_k, best_href = choose_tif_asset(assets)
            all_hrefs = [a.get("href", "") for a in assets.values() if a.get("href")]
            r = self.table.rowCount()
            self.table.insertRow(r)
            vals = [
                coll,
                iid,
                dtm,
                str(cc),
                json.dumps(bbox),
                ",".join(assets.keys()),
                best_href or "",
                json.dumps(all_hrefs),
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            out.append(
                {
                    "collection": coll,
                    "item_id": iid,
                    "datetime": dtm,
                    "cloud_cover": cc,
                    "bbox": json.dumps(bbox),
                    "assets": ",".join(assets.keys()),
                    "href_tif": best_href or "",
                    "all_hrefs": all_hrefs,
                }
            )

        outdir = self.labOutdir.text().strip()
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_csv = os.path.join(outdir, f"stac_search_{ts}.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(
                f, fieldnames=["collection", "item_id", "datetime", "cloud_cover", "bbox", "assets", "href_tif", "all_hrefs"]
            )
            wr.writeheader()
            wr.writerows(out)
        log(f"{len(out)} item(ns) encontrados. CSV: {out_csv}")

    # ---------- ações finais ----------
    def _selected_rows(self):
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def _clip_and_add_to_qgis(self, href, name_prefix=""):
        # sempre atualiza AOI p/ permitir trocar folha entre chamadas
        try:
            self._build_aoi()
        except Exception:
            self.aoi = None

        outdir = self.labOutdir.text().strip()
        os.makedirs(outdir, exist_ok=True)
        fname = os.path.basename(href)
        local = os.path.join(outdir, fname)
        open_raster(href, name=fname, outdir=outdir, just_download=True)

        if self.aoi is None:
            # sem AOI → abre inteiro
            return open_raster(href, name=name_prefix + fname, outdir=outdir, just_download=False)

        try:
            from qgis import processing
        except Exception as e:
            log(f"processing indisponível, abrindo inteiro. Erro: {e}")
            return open_raster(href, name=name_prefix + fname, outdir=outdir, just_download=False)

        mask = QgsVectorLayer("MultiPolygon?crs=EPSG:4326", "aoi_mask", "memory")
        pr = mask.dataProvider()
        ft = QgsFeature()
        ft.setGeometry(self.aoi)
        pr.addFeatures([ft])
        mask.updateExtents()

        out_clip = os.path.join(outdir, f"ASTER_clip_{fname}")
        params = {
            "INPUT": local,
            "MASK": mask,
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "NODATA": 0,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": True,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "EXTRA": "",
            "OUTPUT": out_clip,
        }
        try:
            res = processing.run("gdal:cliprasterbymasklayer", params)
            out_path = res.get("OUTPUT", out_clip)
            rl = QgsRasterLayer(out_path, os.path.basename(out_path), "gdal")
            if rl.isValid():
                QgsProject.instance().addMapLayer(rl)
                return True
            log("GDAL não validou o raster recortado, abrindo inteiro.")
        except Exception as e:
            log(f"Erro ao recortar raster: {e}")
        return open_raster(href, name=name_prefix + fname, outdir=outdir, just_download=False)

    def view_selected(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Selecionar", "Selecione linha(s) na tabela.")
            return
        ok = 0
        for r in rows:
            href = self.table.item(r, 6).text().strip() if self.table.item(r, 6) else ""
            coll = self.table.item(r, 0).text().strip() if self.table.item(r, 0) else ""
            if not href:
                log(f"[{r+1}] sem href_tif — tente baixar todos assets.")
                continue
            if self._last_mode == "aster_ea" and coll == "AST_07XT":
                if self._clip_and_add_to_qgis(href, name_prefix=f"{coll}:"):
                    ok += 1
            else:
                if open_raster(href, name=f"{coll}:{os.path.basename(href)}", outdir=self.labOutdir.text().strip(), just_download=False):
                    ok += 1
        QtWidgets.QMessageBox.information(self, "Visualizar", f"{ok} camada(s) adicionada(s).")

    def download_selected(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Selecionar", "Selecione linha(s) na tabela.")
            return
        outdir = self.labOutdir.text().strip()
        all_assets = self.cbAllAssets.isChecked()
        ok = 0
        for r in rows:
            if all_assets:
                try:
                    all_hrefs = json.loads(self.table.item(r, 7).text() or "[]")
                except Exception:
                    all_hrefs = []
                to_get = [h for h in all_hrefs if h.lower().endswith((".tif", ".tiff"))]
                if not to_get:
                    href = self.table.item(r, 6).text().strip()
                    if href:
                        to_get = [href]
            else:
                href = self.table.item(r, 6).text().strip() if self.table.item(r, 6) else ""
                to_get = [href] if href else []
            for href in to_get:
                if open_raster(href, name=os.path.basename(href), outdir=outdir, just_download=True):
                    ok += 1
        QtWidgets.QMessageBox.information(self, "Download", f"{ok} arquivo(s) baixado(s) para:\n{outdir}")


# --------- entrypoint ----------
def run():
    dlg = BDCDialog()
    dlg.show()
    globals()["__BDC_DLG__"] = dlg


run()

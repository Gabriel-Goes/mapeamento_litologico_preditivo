# -*- coding: utf-8 -*-
# QGIS 3.44 – Catálogo BDC STAC (listar → filtrar → selecionar → visualizar/baixar)
# Requisitos: requests (vem no QGIS), osgeo.gdal. Não precisa shapely/pystac-client.

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import (
    QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsProject, QgsGeometryUtils, QgsVectorLayer, QgsRasterLayer
)
from qgis.utils import iface
import csv, json, os, re, requests, tempfile
from datetime import datetime
from osgeo import gdal

import earthaccess as ea
from shapely.geometry import shape as shp_shape
from db_conn import get_folha_geom_geojson

DEFAULT_STAC = "https://data.inpe.br/bdc/stac/v1/"
ASTER_STAC = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD"

EA_SESSION = None

# -------------------- util/log --------------------
def log(msg):
    print(datetime.now().strftime("[%H:%M:%S] "), msg)

def safe_json(obj):  # pretty curto
    return json.dumps(obj, ensure_ascii=False)

# -------------------- quadricula.csv --------------------
def read_grid_csv(csv_path):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if not r.get("wkt_geom") or not r.get("EPSG"):
                continue
            rows.append({
                "id_folha": r.get("id_folha", ""),
                "epsg": int(r["EPSG"]),
                "wkt": r["wkt_geom"]
            })
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
            g2 = QgsGeometry(g); g2.transform(tr); g = g2
        bb = g.boundingBox(); c = g.centroid().asPoint()
        log(f"[CSV] {i:02d} {r['id_folha']} bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
            f"centroid=({c.x():.6f},{c.y():.6f})")
        geoms.append(g)
    aoi = (QgsGeometryUtils.combineGeometry(geoms)
           if hasattr(QgsGeometryUtils, "combineGeometry")
           else QgsGeometry.unaryUnion(geoms))
    bb = aoi.boundingBox(); c = aoi.centroid().asPoint()
    log(f"[CSV] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
        f"centroid=({c.x():.6f},{c.y():.6f})")
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
        g = ft.geometry(); g2 = QgsGeometry(g); g2.transform(tr)
        bb = g2.boundingBox(); c = g2.centroid().asPoint()
        log(f"[SEL] {i:02d} bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
            f"centroid=({c.x():.6f},{c.y():.6f})")
        geoms.append(g2)
    aoi = (QgsGeometryUtils.combineGeometry(geoms)
           if hasattr(QgsGeometryUtils, "combineGeometry")
           else QgsGeometry.unaryUnion(geoms))
    bb = aoi.boundingBox(); c = aoi.centroid().asPoint()
    log(f"[SEL] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
        f"centroid=({c.x():.6f},{c.y():.6f})")
    return aoi

def geojson_from_qgsgeom(g):
    return json.loads(g.asJson())

# -------------------- STAC --------------------
def fetch_collections(stac_url):
    url = stac_url.rstrip("/") + "/collections"
    log(f"GET {url}")
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    cols = r.json().get("collections", [])
    log(f"{len(cols)} coleções carregadas.")
    return [{
        "id": c.get("id", ""),
        "title": c.get("title", "") or "",
        "description": c.get("description", "") or "",
        "summaries": c.get("summaries", {}) or {},
        "has_cloud_cover": "eo:cloud_cover" in (c.get("summaries", {}) or {}),
    } for c in cols]

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
    log("POST " + url); log("Body: " + safe_json(body))
    r = requests.post(url, json=body, timeout=120, headers={"Content-Type":"application/json"})
    log(f"HTTP {r.status_code}")
    r.raise_for_status()
    return r.json()

# -------------------- abrir/baixar assets --------------------
def choose_tif_asset(assets: dict):
    for k in sorted(assets.keys()):
        href = assets[k].get("href","")
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
                for ch in r.iter_content(1024*1024):
                    if ch: f.write(ch)
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

        # Linha de topo
        self.cbProvider = QtWidgets.QComboBox()
        self.cbProvider.addItem("BDC (INPE)", DEFAULT_STAC)
        self.cbProvider.addItem("ASTER (LP DAAC STAC)", ASTER_STAC)
        self.cbProvider.addItem("Personalizado", "")
        self.cbProvider.setToolTip("Escolha o catálogo STAC: BDC ou ASTER (LP DAAC). Para outro, selecione Personalizado e edite a URL. Filtro de nuvem só é enviado quando o provedor/coleção suporta a propriedade eo:cloud_cover (BDC normalmente).")

        self.edStac = QtWidgets.QLineEdit(DEFAULT_STAC)
        self.edStac.setToolTip("URL do catálogo STAC. Agora aceita BDC ou ASTER (LP DAAC), ou um endpoint personalizado. Em catálogos sem eo:cloud_cover (ex.: LPCLOUD/ASTER), o filtro de nuvem será ignorado.")
        self.btnCols = QtWidgets.QPushButton("Carregar coleções")
        self.edFilter = QtWidgets.QLineEdit()
        self.edFilter.setPlaceholderText("filtrar coleções… ex.: landsat, cbers, sentinel…")
        self.btnApplyFilter = QtWidgets.QPushButton("Aplicar filtro")
        self.btnSelectAll = QtWidgets.QPushButton("Selecionar todas")

        # Lista de coleções
        self.listCols = QtWidgets.QListWidget()
        self.listCols.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listCols.setAlternatingRowColors(True)

        # Origem da AOI
        self.rbSel = QtWidgets.QRadioButton("Usar seleção da camada ativa")
        self.rbCsv = QtWidgets.QRadioButton("Usar quadricula.csv")
        self.rbSel.setChecked(True)
        self.btnGrid = QtWidgets.QPushButton("Escolher CSV…")
        self.labGrid = QtWidgets.QLabel("(nenhum)")

        # Folha (opcional, DB)
        self.edFolha = QtWidgets.QLineEdit("SB21_ZA_II1_NE")
        self.edFolha.setPlaceholderText("folha_id (opcional, ex.: SB21_ZA_II1_NE)")

        # Parâmetros de busca
        self.edStart = QtWidgets.QDateEdit(QtCore.QDate.currentDate().addMonths(-6)); self.edStart.setDisplayFormat("yyyy-MM-dd"); self.edStart.setCalendarPopup(True)
        self.edEnd   = QtWidgets.QDateEdit(QtCore.QDate.currentDate()); self.edEnd.setDisplayFormat("yyyy-MM-dd"); self.edEnd.setCalendarPopup(True)
        self.spCloud = QtWidgets.QDoubleSpinBox(); self.spCloud.setRange(0,100); self.spCloud.setDecimals(1); self.spCloud.setValue(20.0)
        self.spCloud.setToolTip("Filtro por nuvem (eo:cloud_cover) enviado apenas para provedores/coleções que anunciam esse campo. No ASTER/LPCLOUD o filtro é omitido.")
        self.spLimit = QtWidgets.QSpinBox(); self.spLimit.setRange(1, 10000); self.spLimit.setValue(200)
        self.cbAsc   = QtWidgets.QCheckBox("Mais antigas primeiro (asc)")

        # Ações de busca
        self.btnProbe  = QtWidgets.QPushButton("Provar (1 item/coleção)")
        self.btnSearch = QtWidgets.QPushButton("Listar dados")

        # Tabela de resultados
        self.table = QtWidgets.QTableWidget(0, 8)
        self.table.setHorizontalHeaderLabels(["collection","item_id","datetime","cloud_cover","bbox","assets","href_tif","all_hrefs"])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        # Saída/ações finais
        self.btnAdd = QtWidgets.QPushButton("Visualizar selecionados no QGIS")
        self.btnDl  = QtWidgets.QPushButton("Baixar selecionados")
        self.cbAllAssets = QtWidgets.QCheckBox("Baixar todos assets dos itens")
        self.btnOutdir = QtWidgets.QPushButton("Pasta de saída…")
        self.labOutdir = QtWidgets.QLabel(os.path.expanduser("~"))

        # Layout
        top = QtWidgets.QHBoxLayout()
        top.addWidget(QtWidgets.QLabel("Catálogo STAC (BDC/ASTER):"))
        top.addWidget(self.cbProvider)
        top.addWidget(self.edStac, 1)
        top.addWidget(self.btnCols)

        filt = QtWidgets.QHBoxLayout()
        filt.addWidget(self.edFilter, 1); filt.addWidget(self.btnApplyFilter); filt.addWidget(self.btnSelectAll)

        aoi = QtWidgets.QHBoxLayout()
        aoi.addWidget(self.rbSel); aoi.addWidget(self.rbCsv); aoi.addWidget(self.btnGrid); aoi.addWidget(self.labGrid,1)

        row_folha = QtWidgets.QHBoxLayout()
        row_folha.addWidget(QtWidgets.QLabel("Folha (DB):"))
        row_folha.addWidget(self.edFolha, 1)

        par = QtWidgets.QHBoxLayout()
        par.addWidget(QtWidgets.QLabel("Início:")); par.addWidget(self.edStart)
        par.addWidget(QtWidgets.QLabel("Fim:")); par.addWidget(self.edEnd)
        par.addWidget(QtWidgets.QLabel("Nuvem <=")); par.addWidget(self.spCloud)
        par.addWidget(QtWidgets.QLabel("Limite:")); par.addWidget(self.spLimit)
        par.addWidget(self.cbAsc)

        actions = QtWidgets.QHBoxLayout()
        actions.addWidget(self.btnProbe); actions.addWidget(self.btnSearch); actions.addStretch(1)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addWidget(self.btnAdd); bottom.addWidget(self.btnDl); bottom.addWidget(self.cbAllAssets)
        bottom.addStretch(1)
        bottom.addWidget(self.btnOutdir); bottom.addWidget(self.labOutdir,1)

        lay = QtWidgets.QVBoxLayout(self)
        lay.addLayout(top); lay.addLayout(filt); lay.addWidget(self.listCols,1)
        lay.addLayout(aoi)
        lay.addLayout(row_folha)
        lay.addLayout(par); lay.addLayout(actions)
        lay.addWidget(self.table,2)
        lay.addLayout(bottom)

        # state
        self.rows = None
        self.aoi  = None
        self._all_collections = []
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

        # layer listeners
        try:
            iface.currentLayerChanged.connect(self._on_layer_changed)
            self._on_layer_changed(iface.activeLayer())
        except Exception as e:
            log(f"[DEBUG] Falha ao conectar signals de camada: {e}")

    # ---------- helpers ----------
    def _current_stac(self):
        return self.edStac.text().strip()

    def _is_aster_provider(self):
        return self._current_stac().rstrip("/") == ASTER_STAC.rstrip("/")

    def _ensure_earthaccess_login(self):
        global EA_SESSION
        if EA_SESSION is None:
            EA_SESSION = ea.login()
        return EA_SESSION

    def _aoi_from_folha(self):
        fol = (self.edFolha.text() or "").strip()
        if not fol:
            return None
        try:
            gj = get_folha_geom_geojson(fol)
            geom = shp_shape(gj)
            g_qgs = QgsGeometry.fromWkt(geom.wkt)
            log(f"[DEBUG] _aoi_from_folha folha={fol} bbox={geom.bounds}")
            return g_qgs
        except Exception as e:
            log(f"[DEBUG] Erro ao obter folha {fol}: {e}")
            return None

    def _aster_search_point(self):
        fol = (self.edFolha.text() or "").strip()
        if fol:
            gj = get_folha_geom_geojson(fol)
            g = shp_shape(gj)
            c = g.centroid
            lon, lat = c.x, c.y
            log(f"[ASTER] Centro da folha {fol}: ({lon:.6f},{lat:.6f})")
            return lon, lat
        if self.aoi is None:
            self._build_aoi()
        c = self.aoi.centroid().asPoint()
        lon, lat = c.x(), c.y()
        log(f"[ASTER] Centro da AOI: ({lon:.6f},{lat:.6f})")
        return lon, lat

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

    def _build_aoi(self, for_probe=False):
        aoi_from_folha = self._aoi_from_folha()
        if aoi_from_folha:
            self.aoi = aoi_from_folha
            log(f"[DEBUG] AOI ← folha DB ({self.edFolha.text().strip()})")
        elif self.rbSel.isChecked():
            log("AOI ← seleção da camada ativa")
            self.aoi = aoi_from_active_selection()
        else:
            if not self.rows: raise RuntimeError("Carregue o CSV de quadícula.")
            log("AOI ← CSV de quadícula")
            self.aoi = aoi_from_grid(self.rows)
        gj = geojson_from_qgsgeom(self.aoi)
        log(("AOI GeoJSON (probe)" if for_probe else "AOI GeoJSON (search)") + " = " + safe_json(gj))
        return gj

    def _selected_collections(self):
        return [self.listCols.item(i).data(QtCore.Qt.UserRole)
                for i in range(self.listCols.count())
                if self.listCols.item(i).checkState()==QtCore.Qt.Checked]

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

    def _on_layer_changed(self, layer):
        try:
            if self._sel_layer and isinstance(self._sel_layer, QgsVectorLayer):
                self._sel_layer.selectionChanged.disconnect(self._on_selection_changed)
        except Exception:
            pass
        self._sel_layer = layer if isinstance(layer, QgsVectorLayer) else None
        if self._sel_layer:
            try:
                self._sel_layer.selectionChanged.connect(self._on_selection_changed)
            except Exception as e:
                log(f"[DEBUG] Não conectou selectionChanged: {e}")
        self._update_folha_from_selection()

    def _pick_folha_attr(self, ft):
        for k, v in ft.attributes().items():
            try:
                name = ft.fields()[k].name()
            except Exception:
                name = str(k)
            if name and "folha" in name.lower():
                return v
        return None

    def _update_folha_from_selection(self):
        layer = self._sel_layer
        if not isinstance(layer, QgsVectorLayer):
            return
        sel = layer.selectedFeatures()
        if not sel:
            return
        fol_val = self._pick_folha_attr(sel[0])
        if fol_val:
            fol_str = str(fol_val)
            self.edFolha.setText(fol_str)
            aoi = self._aoi_from_folha()
            if aoi:
                self.aoi = aoi
            log(f"[DEBUG] _update_folha_from_selection layer={layer.name()} folha={fol_str} aoi_set={bool(aoi)}")

    # ---------- UI actions ----------
    def load_collections(self):
        if self._is_aster_provider():
            cols = [{
                "id": "AST_07XT",
                "title": "ASTER 07XT SRF VNIR+SWIR (earthaccess)",
                "description": "Busca simplificada via earthaccess/LP DAAC usando ponto central da folha/AOI.",
                "summaries": {},
                "has_cloud_cover": True,
            }]
            self._all_collections = cols
            self._populate_cols(cols)
            return
        try:
            cols = fetch_collections(self._current_stac())
        except requests.exceptions.HTTPError as e:
            QtWidgets.QMessageBox.critical(self, "Erro /collections", self._http_error_message(e)); return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro /collections", str(e)); return
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
                desc += "\n[sem eo:cloud_cover; filtro de nuvem será ignorado]"
            it.setToolTip(desc)
            it.setCheckState(QtCore.Qt.Unchecked)
            self.listCols.addItem(it)

    def apply_filter(self):
        if not self._all_collections:
            return
        q = (self.edFilter.text() or "").strip().lower()
        if not q:
            self._populate_cols(self._all_collections); return
        keys = re.split(r"[,\s]+", q)
        def ok(c):
            hay = (c["id"]+" "+c["title"]+" "+c["description"]).lower()
            return all(k in hay for k in keys if k)
        self._populate_cols([c for c in self._all_collections if ok(c)])

    def select_all_cols(self):
        for i in range(self.listCols.count()):
            self.listCols.item(i).setCheckState(QtCore.Qt.Checked)

    def pick_grid(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Selecionar quadricula.csv", "", "CSV (*.csv)")
        if not p: return
        try:
            self.rows = read_grid_csv(p); self.labGrid.setText(p)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "CSV", str(e))

    def pick_outdir(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Pasta de saída", self.labOutdir.text())
        if d: self.labOutdir.setText(d)

    def do_probe(self):
        if self._is_aster_provider():
            QtWidgets.QMessageBox.information(
                self,
                "Probe",
                "Prova rápida não implementada para ASTER (earthaccess). Use 'Listar dados'."
            )
            return
        cols = self._selected_collections()
        if not cols: QtWidgets.QMessageBox.warning(self, "Coleções", "Marque pelo menos uma."); return
        try:
            aoi_gj = self._build_aoi(for_probe=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "AOI", str(e)); return
        dt = f"{self.edStart.date().toString('yyyy-MM-dd')}/{self.edEnd.date().toString('yyyy-MM-dd')}"
        ok, zero = [], []
        for coll in cols:
            try:
                allow_cloud = self._cloud_filter_allowed([coll])
                if not allow_cloud:
                    log(f"[PROBE] {coll}: filtro de nuvem omitido (sem eo:cloud_cover).")
                js = stac_search(self._current_stac(), [coll], aoi_gj, dt,
                                 max_cloud=float(self.spCloud.value()) if allow_cloud else None, limit=1,
                                 sort="asc" if self.cbAsc.isChecked() else "desc")
                (ok if js.get("features") else zero).append(coll)
            except requests.exceptions.HTTPError as e:
                QtWidgets.QMessageBox.critical(self, "Erro /search", f"{coll}: {self._http_error_message(e)}")
                zero.append(coll)
            except Exception:
                zero.append(coll)
        log(f"PROBE: OK={ok} ZERO={zero}")

    def run_aster_earthaccess(self):
        try:
            self._ensure_earthaccess_login()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "earthaccess/login", str(e))
            return
        try:
            lon, lat = self._aster_search_point()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "AOI/Folha", str(e))
            return

        start = self.edStart.date().toString("yyyy-MM-dd")
        end   = self.edEnd.date().toString("yyyy-MM-dd")
        temporal = (start, end)
        cloud_max = float(self.spCloud.value())

        log(f"[ASTER] Busca AST_07XT ponto=({lon:.6f},{lat:.6f}), temporal={temporal}, nuvem<={cloud_max}")

        try:
            granules = list(
                ea.search_data(
                    short_name="AST_07XT",
                    version="004",
                    point=(lon, lat),
                    temporal=temporal,
                    cloud_hosted=True,
                )
            )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "ASTER search", str(e))
            return

        if not granules:
            QtWidgets.QMessageBox.information(
                self,
                "ASTER",
                "Nenhum granule AST_07XT encontrado para esta AOI/intervalo."
            )
            self.table.setRowCount(0)
            return

        def _key(g):
            umm = g.get("umm", {})
            cc = umm.get("CloudCover")
            if cc is None:
                cc = 9999.0
            te = umm.get("TemporalExtent", {})
            if "SingleDateTime" in te:
                dtm = te["SingleDateTime"]
            else:
                r = (te.get("RangeDateTimes") or te.get("RangeDateTime") or [{}])[0]
                dtm = r.get("BeginningDateTime", "")
            return (cc, dtm)

        granules_f = []
        for g in granules:
            umm = g.get("umm", {})
            cc = umm.get("CloudCover")
            if cc is not None and cc > cloud_max:
                continue
            granules_f.append(g)

        granules_f.sort(key=_key)

        self.table.setRowCount(0)
        out = []

        for g in granules_f:
            umm = g.get("umm", {})

            coll = umm.get("CollectionReference", {}).get("ShortName", "AST_07XT")
            iid  = umm.get("GranuleUR", "")

            cc   = umm.get("CloudCover", "")

            te = umm.get("TemporalExtent", {})
            if "SingleDateTime" in te:
                dtm = te["SingleDateTime"]
            else:
                r = (te.get("RangeDateTimes") or te.get("RangeDateTime") or [{}])[0]
                dtm = r.get("BeginningDateTime", "")

            bbox = []
            try:
                sp = umm.get("SpatialExtent", {})
                hs = sp.get("HorizontalSpatialDomain", {})
                geom = hs.get("Geometry", {})
                gpolys = geom.get("GPolygons") or []
                if gpolys:
                    pts = gpolys[0]["Boundary"]["Points"]
                    xs = [p["Longitude"] for p in pts]
                    ys = [p["Latitude"] for p in pts]
                    bbox = [min(xs), min(ys), max(xs), max(ys)]
            except Exception:
                bbox = []

            hrefs = []
            try:
                hrefs = [h for h in g.data_links() if h.lower().endswith((".tif", ".tiff"))]
            except Exception:
                pass
            best_href = hrefs[0] if hrefs else ""

            r = self.table.rowCount()
            self.table.insertRow(r)
            vals = [
                coll,
                iid,
                dtm,
                str(cc),
                json.dumps(bbox),
                "data_links",
                best_href,
                json.dumps(hrefs),
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(v))

            out.append({
                "collection": coll,
                "item_id": iid,
                "datetime": dtm,
                "cloud_cover": cc,
                "bbox": bbox,
                "assets": "data_links",
                "href_tif": best_href,
                "all_hrefs": hrefs,
            })

        outdir = self.labOutdir.text().strip()
        os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_csv = os.path.join(outdir, f"aster07xt_earthaccess_{ts}.csv")

        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(
                f,
                fieldnames=["collection","item_id","datetime","cloud_cover","bbox","assets","href_tif","all_hrefs"],
            )
            wr.writeheader()
            for r in out:
                wr.writerow({
                    "collection": r["collection"],
                    "item_id": r["item_id"],
                    "datetime": r["datetime"],
                    "cloud_cover": r["cloud_cover"],
                    "bbox": json.dumps(r["bbox"]),
                    "assets": r["assets"],
                    "href_tif": r["href_tif"],
                    "all_hrefs": json.dumps(r["all_hrefs"]),
                })

        log(f"[ASTER] {len(out)} granule(s) AST_07XT. CSV: {out_csv}")

    def _clip_and_add_raster(self, href, name):
        import processing
        from qgis.core import QgsVectorLayer, QgsFeature, QgsField
        from qgis.PyQt.QtCore import QVariant

        gdal_tune_for_http()
        outdir = self.labOutdir.text().strip() or tempfile.gettempdir()
        os.makedirs(outdir, exist_ok=True)
        local = os.path.join(outdir, os.path.basename(href))

        if not os.path.exists(local):
            try:
                log(f"[CLIP] Baixando para clip: {local}")
                with requests.get(href, stream=True, timeout=600) as r:
                    r.raise_for_status()
                    with open(local, "wb") as f:
                        for ch in r.iter_content(1024*1024):
                            if ch:
                                f.write(ch)
            except Exception as e:
                log(f"Erro no download para clip: {e}")
                return False

        if self.aoi is None:
            try:
                self._build_aoi()
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "AOI", str(e))
                return False

        aoi_layer = QgsVectorLayer("Polygon?crs=EPSG:4326", "AOI_clip", "memory")
        pr = aoi_layer.dataProvider()
        pr.addAttributes([QgsField("id", QVariant.Int)])
        aoi_layer.updateFields()
        feat = QgsFeature(aoi_layer.fields())
        feat.setGeometry(self.aoi)
        feat.setAttribute("id", 1)
        pr.addFeature(feat)
        aoi_layer.updateExtents()

        params = {
            "INPUT": local,
            "MASK": aoi_layer,
            "SOURCE_CRS": None,
            "TARGET_CRS": None,
            "NODATA": 0,
            "ALPHA_BAND": False,
            "CROP_TO_CUTLINE": True,
            "KEEP_RESOLUTION": True,
            "OPTIONS": "",
            "DATA_TYPE": 0,
            "MULTITHREADING": True,
            "EXTRA": "",
            "OUTPUT": "TEMPORARY_OUTPUT",
        }

        log(f"[DEBUG] Clip raster href={href} name={name} params={params}")
        try:
            res = processing.run("gdal:cliprasterbymasklayer", params)
        except Exception as e:
            log(f"Erro ao recortar raster: {e}")
            return False

        out_path = res.get("OUTPUT")
        if not out_path:
            log("Clip não retornou caminho de saída.")
            return False

        rl = QgsRasterLayer(out_path, name, "gdal")
        if rl.isValid():
            QgsProject.instance().addMapLayer(rl)
            return True

        log("GDAL não validou raster recortado.")
        return False

    def _on_selection_changed(self):
        self._update_folha_from_selection()
        if self.edFolha.text().strip():
            log(f"[DEBUG] _on_selection_changed rebuild aoi folha={self.edFolha.text().strip()}")
            self._build_aoi()

    def run_search(self):
        if self._is_aster_provider():
            self.run_aster_earthaccess()
            return

        cols = self._selected_collections()
        if not cols:
            QtWidgets.QMessageBox.warning(self, "Coleções", "Marque pelo menos uma.")
            return
        try:
            aoi_gj = self._build_aoi()
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "AOI", str(e)); return
        dt = f"{self.edStart.date().toString('yyyy-MM-dd')}/{self.edEnd.date().toString('yyyy-MM-dd')}"
        try:
            allow_cloud = self._cloud_filter_allowed(cols)
            if not allow_cloud:
                log("[SEARCH] Filtro de nuvem omitido (coleções/provedor sem eo:cloud_cover).")
            js = stac_search(self._current_stac(), cols, aoi_gj, dt,
                             max_cloud=float(self.spCloud.value()) if allow_cloud else None, limit=int(self.spLimit.value()),
                             sort="asc" if self.cbAsc.isChecked() else "desc")
        except requests.exceptions.HTTPError as e:
            QtWidgets.QMessageBox.critical(self, "Erro /search", self._http_error_message(e)); return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro /search", str(e)); return

        feats = js.get("features", [])
        self.table.setRowCount(0)
        out = []
        for ft in feats:
            props = ft.get("properties", {})
            coll = ft.get("collection",""); iid = ft.get("id","")
            dtm  = props.get("datetime",""); cc = props.get("eo:cloud_cover", props.get("cloud_cover",""))
            bbox = ft.get("bbox",""); assets = ft.get("assets", {})
            best_k, best_href = choose_tif_asset(assets)
            all_hrefs = [a.get("href","") for a in assets.values() if a.get("href")]
            r = self.table.rowCount(); self.table.insertRow(r)
            vals = [coll, iid, dtm, str(cc), json.dumps(bbox), ",".join(assets.keys()), best_href or "", json.dumps(all_hrefs)]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            out.append({"collection": coll, "item_id": iid, "datetime": dtm, "cloud_cover": cc,
                        "bbox": json.dumps(bbox), "assets": ",".join(assets.keys()),
                        "href_tif": best_href or "", "all_hrefs": all_hrefs})

        outdir = self.labOutdir.text().strip(); os.makedirs(outdir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_csv = os.path.join(outdir, f"stac_search_{ts}.csv")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=["collection","item_id","datetime","cloud_cover","bbox","assets","href_tif","all_hrefs"])
            wr.writeheader(); wr.writerows(out)
        log(f"{len(out)} item(ns) encontrados. CSV: {out_csv}")

    # ---------- ações finais ----------
    def _selected_rows(self):
        return sorted({i.row() for i in self.table.selectedIndexes()})

    def view_selected(self):
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Selecionar", "Selecione linha(s) na tabela.")
            return
        ok = 0
        for r in rows:
            href = self.table.item(r, 6).text().strip() if self.table.item(r,6) else ""
            coll = self.table.item(r, 0).text().strip()
            if not href:
                log(f"[{r+1}] sem href_tif — tente baixar todos assets.")
                continue
            name = f"{coll}:{os.path.basename(href)}"
            if self._is_aster_provider():
                if self._clip_and_add_raster(href, name):
                    ok += 1
            else:
                if open_raster(href, name=name, outdir=self.labOutdir.text().strip(), just_download=False):
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
                    all_hrefs = json.loads(self.table.item(r,7).text() or "[]")
                except Exception:
                    all_hrefs = []
                to_get = [h for h in all_hrefs if h.lower().endswith((".tif",".tiff"))]
                if not to_get:
                    href = self.table.item(r,6).text().strip()
                    if href: to_get = [href]
            else:
                href = self.table.item(r,6).text().strip() if self.table.item(r,6) else ""
                to_get = [href] if href else []
            for href in to_get:
                if open_raster(href, name=os.path.basename(href), outdir=outdir, just_download=True):
                    ok += 1
        QtWidgets.QMessageBox.information(self, "Download", f"{ok} arquivo(s) baixado(s) para:\n{outdir}")

# --------- entrypoint (não modal) ----------
def run():
    dlg = BDCDialog()
    dlg.show()
    globals()['__BDC_DLG__'] = dlg  # mantém vivo

# iniciar
run()

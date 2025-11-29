# -*- coding: utf-8 -*-
# QGIS 3.44 – Catálogo BDC STAC (listar → filtrar → selecionar → visualizar/baixar)
# Requisitos: requests (vem no QGIS), osgeo.gdal.

from qgis.PyQt import QtWidgets, QtCore
from qgis.core import (
    QgsGeometry, QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsProject, QgsVectorLayer, QgsRasterLayer, QgsFeature, QgsField,
    QgsTask, QgsApplication,
)
from qgis.utils import iface
import csv, json, os, re, requests, tempfile
from datetime import datetime
from osgeo import gdal

import earthaccess as ea
from shapely.geometry import shape as shp_shape, Polygon
from db_conn import get_folha_geom_geojson

import time
import hashlib

DEFAULT_STAC = "https://data.inpe.br/bdc/stac/v1/"
ASTER_STAC = "https://cmr.earthdata.nasa.gov/stac/LPCLOUD"

EA_SESSION = None

# -------------------- infra de log + emitter (thread-safe) --------------------
LOG_BUFFER = []
LOG_WIDGET = None
LOG_FILE_PATH = os.path.join(os.path.expanduser("~"), "bdc_stac_qgis.log")
LOG_EMITTER = None


class LogEmitter(QtCore.QObject):
    sig_log = QtCore.pyqtSignal(str)


def attach_log_widget(widget):
    """
    Conecta o widget de log a um emissor de sinais, para permitir chamadas de log
    a partir de tarefas (threads) sem tocar diretamente no widget.
    """
    global LOG_WIDGET, LOG_EMITTER
    LOG_WIDGET = widget

    if LOG_EMITTER is None:
        LOG_EMITTER = LogEmitter()

    def _append(text):
        try:
            widget.appendPlainText(text)
            sb = widget.verticalScrollBar()
            sb.setValue(sb.maximum())
        except Exception:
            pass

    try:
        LOG_EMITTER.sig_log.disconnect()
    except Exception:
        pass

    LOG_EMITTER.sig_log.connect(_append)

    try:
        for line in LOG_BUFFER:
            widget.appendPlainText(line)
        sb = widget.verticalScrollBar()
        sb.setValue(sb.maximum())
    except Exception:
        pass


def log(msg):
    global LOG_EMITTER
    line = datetime.now().strftime("[%H:%M:%S] ") + str(msg)

    print(line)

    LOG_BUFFER.append(line)

    if LOG_EMITTER is not None:
        try:
            LOG_EMITTER.sig_log.emit(line)
        except Exception:
            pass

    try:
        with open(LOG_FILE_PATH, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


log("[INIT] Módulo BDC STAC carregado.")


# -------------------- util/json & query-id helpers --------------------
def safe_json(obj):
    return json.dumps(obj, ensure_ascii=False)


def _safe_slug(value, fallback=""):
    val = (value or "").strip()
    if not val:
        return fallback
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", val)


def _build_query_id(prefix, params_dict):
    try:
        payload = json.dumps(params_dict, sort_keys=True, ensure_ascii=False)
    except Exception:
        payload = repr(params_dict)
    h = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{h}"


# -------------------- quadricula.csv --------------------
def read_grid_csv(csv_path):
    log(f"[CALL] read_grid_csv(csv_path={csv_path!r})")
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
    log(f"[CALL] aoi_from_grid(rows_len={len(rows)})")
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
            f"[CSV] {i:02d} {r['id_folha']} bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},"
            f"{bb.xMaximum():.6f},{bb.yMaximum():.6f}] centroid=({c.x():.6f},{c.y():.6f})"
        )
        geoms.append(g)
    aoi = QgsGeometry.unaryUnion(geoms)
    bb = aoi.boundingBox()
    c = aoi.centroid().asPoint()
    log(
        f"[CSV] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
        f"centroid=({c.x():.6f},{c.y():.6f})"
    )
    return aoi


def aoi_from_active_selection():
    log("[CALL] aoi_from_active_selection()")
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
            f"[SEL] {i:02d} bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},"
            f"{bb.xMaximum():.6f},{bb.yMaximum():.6f}] centroid=({c.x():.6f},{c.y():.6f})"
        )
        geoms.append(g2)
    aoi = QgsGeometry.unaryUnion(geoms)
    bb = aoi.boundingBox()
    c = aoi.centroid().asPoint()
    log(
        f"[SEL] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
        f"centroid=({c.x():.6f},{c.y():.6f})"
    )
    return aoi


def geojson_from_qgsgeom(g):
    log(f"[CALL] geojson_from_qgsgeom(type={type(g).__name__})")
    return json.loads(g.asJson())


# -------------------- STAC --------------------
def fetch_collections(stac_url):
    log(f"[CALL] fetch_collections(stac_url={stac_url!r})")
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
    log(
        f"[CALL] stac_search(stac_url={stac_url!r}, collections={collections}, "
        f"datetime={datetime_str!r}, max_cloud={max_cloud}, limit={limit}, sort={sort!r})"
    )
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
    log(f"[CALL] choose_tif_asset(keys={list(assets.keys())})")
    for k in sorted(assets.keys()):
        href = assets[k].get("href", "")
        if href and re.search(r"\.tif(f)?$", href, re.I) and "thumb" not in k.lower() and "overview" not in k.lower():
            return k, href
    return None, None


def gdal_tune_for_http():
    log("[CALL] gdal_tune_for_http()")
    gdal.SetConfigOption("CPL_VSIL_CURL_ALLOWED_EXTENSIONS", "tif,tiff")
    gdal.SetConfigOption("GDAL_DISABLE_READDIR_ON_OPEN", "YES")
    gdal.SetConfigOption("GDAL_HTTP_MAX_RETRY", "3")
    gdal.SetConfigOption("GDAL_HTTP_MULTIRANGE", "YES")


def open_raster(href, name=None, outdir=None, just_download=False):
    log(
        f"[CALL] open_raster(href={href!r}, name={name!r}, "
        f"outdir={outdir!r}, just_download={just_download})"
    )
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


# -------------------- TASKS: download para clip (ASTER) --------------------
def _download_for_clip(task, href, local):
    gdal_tune_for_http()
    log(f"[TASK-CLIP] Iniciando download para clip: {href} -> {local}")

    try:
        t0 = time.time()
        with requests.get(href, stream=True, timeout=600) as r:
            r.raise_for_status()

            total = int(r.headers.get("Content-Length", "0") or 0)
            if total > 0:
                log(f"[TASK-CLIP] Tamanho remoto ~ {total / (1024 * 1024):.1f} MB")
            else:
                log("[TASK-CLIP] Content-Length não informado; progresso absoluto apenas.")

            downloaded = 0
            next_report = 50 * 1024 * 1024

            os.makedirs(os.path.dirname(local), exist_ok=True)

            with open(local, "wb") as f:
                for ch in r.iter_content(1024 * 1024):
                    if task.isCanceled():
                        log("[TASK-CLIP] Download cancelado pelo usuário.")
                        return False
                    if not ch:
                        continue
                    f.write(ch)
                    downloaded += len(ch)

                    if total > 0 and downloaded >= next_report:
                        pct = downloaded / total * 100.0
                        log(
                            f"[TASK-CLIP] Download {downloaded / (1024 * 1024):.1f}/"
                            f"{total / (1024 * 1024):.1f} MB ({pct:.1f}%)"
                        )
                        next_report += 50 * 1024 * 1024

        dt = time.time() - t0
        if total > 0:
            log(
                f"[TASK-CLIP] Download concluído: {downloaded / (1024 * 1024):.1f}/"
                f"{total / (1024 * 1024):.1f} MB em {dt:.1f} s"
            )
        else:
            log(f"[TASK-CLIP] Download concluído: {downloaded / (1024 * 1024):.1f} MB em {dt:.1f} s")

        return True

    except requests.exceptions.Timeout as e:
        log(f"[TASK-CLIP] Timeout no download para clip: {e}")
        return False
    except requests.exceptions.RequestException as e:
        log(f"[TASK-CLIP] Erro HTTP no download para clip: {e}")
        return False
    except Exception as e:
        log(f"[TASK-CLIP] Erro inesperado no download para clip: {e}")
        return False


def _on_download_for_clip_finished(exception, result, href, local, name, dlg):
    if exception is not None:
        log(f"[TASK-CLIP] Exceção durante download {href}: {exception}")
        return

    if not result:
        log(f"[TASK-CLIP] Download falhou ou foi cancelado para {href}. Clip não será executado.")
        return

    size_mb = os.path.getsize(local) / (1024 * 1024) if os.path.exists(local) else 0.0
    log(f"[TASK-CLIP] Download concluído ({size_mb:.1f} MB). Iniciando clip e adição ao QGIS...")

    try:
        dlg._clip_and_add_raster_local(local, name)
    except Exception as e:
        log(f"[TASK-CLIP] Erro ao executar clip após download: {e}")


# -------------------- GUI --------------------
class BDCDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        log("[CALL] BDCDialog.__init__()")
        super().__init__(parent)
        self.setWindowTitle("BDC/ASTER – Listar/Filtrar/Selecionar dados (quadícula)")
        self.resize(1000, 680)

        self.cbProvider = QtWidgets.QComboBox()
        self.cbProvider.addItem("BDC (INPE)", DEFAULT_STAC)
        self.cbProvider.addItem("ASTER (LP DAAC STAC)", ASTER_STAC)
        self.cbProvider.addItem("Personalizado", "")
        self.cbProvider.setToolTip(
            "Escolha o catálogo STAC: BDC ou ASTER (LP DAAC). Para outro, selecione Personalizado e edite a URL. "
            "Filtro de nuvem só é enviado quando o provedor/coleção suporta a propriedade eo:cloud_cover (BDC normalmente)."
        )

        self.edStac = QtWidgets.QLineEdit(DEFAULT_STAC)
        self.edStac.setToolTip(
            "URL do catálogo STAC. Agora aceita BDC ou ASTER (LP DAAC), ou um endpoint personalizado. "
            "Em catálogos sem eo:cloud_cover (ex.: LPCLOUD/ASTER), o filtro de nuvem será ignorado."
        )
        self.btnCols = QtWidgets.QPushButton("Carregar coleções")
        self.edFilter = QtWidgets.QLineEdit()
        self.edFilter.setPlaceholderText("filtrar coleções… ex.: landsat, cbers, sentinel…")
        self.btnApplyFilter = QtWidgets.QPushButton("Aplicar filtro")
        self.btnSelectAll = QtWidgets.QPushButton("Selecionar todas")

        self.listCols = QtWidgets.QListWidget()
        self.listCols.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listCols.setAlternatingRowColors(True)

        self.rbSel = QtWidgets.QRadioButton("Usar seleção da camada ativa")
        self.rbCsv = QtWidgets.QRadioButton("Usar quadricula.csv")
        self.rbSel.setChecked(True)
        self.btnGrid = QtWidgets.QPushButton("Escolher CSV…")
        self.labGrid = QtWidgets.QLabel("(nenhum)")

        self.edFolha = QtWidgets.QLineEdit()
        self.edFolha.setPlaceholderText("Código da folha (ex.: SB21_ZA_II1_NE)")

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
            "Filtro por nuvem (eo:cloud_cover) enviado apenas para provedores/coleções que anunciam esse campo. "
            "No ASTER/LPCLOUD o filtro é omitido."
        )
        self.spLimit = QtWidgets.QSpinBox()
        self.spLimit.setRange(1, 10000)
        self.spLimit.setValue(200)
        self.cbAsc = QtWidgets.QCheckBox("Mais antigas primeiro (asc)")

        self.btnProbe = QtWidgets.QPushButton("Provar (1 item/coleção)")
        self.btnSearch = QtWidgets.QPushButton("Listar dados")

        # agora 9 colunas: adicionamos coverage_ratio
        self.table = QtWidgets.QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(
            [
                "collection", "item_id", "datetime", "cloud_cover",
                "bbox", "assets", "href_tif", "all_hrefs", "coverage_ratio"
            ]
        )
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.txtLog = QtWidgets.QPlainTextEdit()
        self.txtLog.setReadOnly(True)
        self.txtLog.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.txtLog.setPlaceholderText("Log de execução (funções, parâmetros, requisições).")

        self.btnAdd = QtWidgets.QPushButton("Visualizar selecionados no QGIS")
        self.btnDl = QtWidgets.QPushButton("Baixar selecionados")
        self.cbAllAssets = QtWidgets.QCheckBox("Baixar todos assets dos itens")
        self.btnOutdir = QtWidgets.QPushButton("Pasta de saída…")
        self.labOutdir = QtWidgets.QLabel(os.path.expanduser("~"))

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

        row_folha = QtWidgets.QHBoxLayout()
        row_folha.addWidget(QtWidgets.QLabel("Folha (DB):"))
        row_folha.addWidget(self.edFolha, 1)

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
        lay.addLayout(row_folha)
        lay.addLayout(par)
        lay.addLayout(actions)
        lay.addWidget(self.table, 2)
        lay.addWidget(self.txtLog, 1)
        lay.addLayout(bottom)

        self.rows = None
        self.aoi = None
        self._all_collections = []
        self._sel_layer_ = None

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
        self.rbSel.toggled.connect(self._on_aoi_source_toggled)

        iface.currentLayerChanged.connect(self._on_current_layer_changed)

        attach_log_widget(self.txtLog)
        log("[BDCDialog] Diálogo iniciado.")

        self._on_current_layer_changed(iface.activeLayer())

    # ---------- helpers ----------
    def _current_stac(self):
        val = self.edStac.text().strip()
        log(f"[CALL] BDCDialog._current_stac() -> {val!r}")
        return val

    def _is_aster_provider(self):
        st = self._current_stac().rstrip("/")
        res = st == ASTER_STAC.rstrip("/")
        log(f"[CALL] BDCDialog._is_aster_provider() -> {res}")
        return res

    def _ensure_earthaccess_login(self):
        log("[CALL] BDCDialog._ensure_earthaccess_login()")
        global EA_SESSION
        if EA_SESSION is None:
            EA_SESSION = ea.login()
        return EA_SESSION

    def _aster_search_bbox(self):
        log("[CALL] BDCDialog._aster_search_bbox()")
        fol = (self.edFolha.text() or "").strip()

        if fol:
            try:
                gj = get_folha_geom_geojson(fol)
                g = shp_shape(gj)
                minx, miny, maxx, maxy = g.bounds
                bbox = (minx, miny, maxx, maxy)
                log(f"[ASTER] BBOX folha {fol}: {bbox}")
                return bbox
            except Exception as e:
                log(f"[ASTER] Erro ao obter geometria da folha {fol}: {e}")

        if self.aoi is None:
            self._build_aoi()

        bb = self.aoi.boundingBox()
        bbox = (bb.xMinimum(), bb.yMinimum(), bb.xMaximum(), bb.yMaximum())
        log(f"[ASTER] BBOX AOI: {bbox}")
        return bbox

    def _aster_search_point(self):
        log("[CALL] BDCDialog._aster_search_point()")
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
        log(f"[CALL] BDCDialog._on_provider_change(idx={idx})")
        url = self.cbProvider.itemData(idx)
        if url:
            self.edStac.setText(url)

    def _on_stac_changed(self, text):
        log(f"[CALL] BDCDialog._on_stac_changed(text={text!r})")
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

    def _update_aoi_from_selection(self, layer):
        if not isinstance(layer, QgsVectorLayer):
            raise RuntimeError("Camada ativa não é vetorial. Selecione feições em uma camada vetorial.")

        sel = layer.selectedFeatures()
        if not sel:
            raise RuntimeError("Nenhuma feição selecionada.")

        wgs84 = QgsCoordinateReferenceSystem("EPSG:4326")
        src_crs = layer.crs() or QgsProject.instance().crs()
        tr = QgsCoordinateTransform(src_crs, wgs84, QgsProject.instance())

        geoms = []
        codigos = set()
        idx_codigo = layer.fields().indexFromName("codigo")

        for i, ft in enumerate(sel, 1):
            g = ft.geometry()
            g2 = QgsGeometry(g)
            g2.transform(tr)
            bb = g2.boundingBox()
            c = g2.centroid().asPoint()
            log(
                f"[SEL] {i:02d} bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},"
                f"{bb.xMaximum():.6f},{bb.yMaximum():.6f}] centroid=({c.x():.6f},{c.y():.6f})"
            )
            geoms.append(g2)
            if idx_codigo != -1:
                try:
                    codigos.add(str(ft[idx_codigo]))
                except Exception:
                    pass

        self.aoi = QgsGeometry.unaryUnion(geoms)
        bb = self.aoi.boundingBox()
        c = self.aoi.centroid().asPoint()
        log(
            f"[SEL] AOI bbox=[{bb.xMinimum():.6f},{bb.yMinimum():.6f},{bb.xMaximum():.6f},{bb.yMaximum():.6f}] "
            f"centroid=({c.x():.6f},{c.y():.6f})"
        )

        if len(codigos) == 1:
            fol = next(iter(codigos))
            log(f"[SEL] Atualizando Folha(DB) com codigo={fol}")
            self.edFolha.setText(fol)

    def _build_aoi(self, for_probe=False):
        log(f"[CALL] BDCDialog._build_aoi(for_probe={for_probe})")
        if self.rbSel.isChecked():
            log("AOI ← seleção da camada ativa")
            lyr = iface.activeLayer()
            if not isinstance(lyr, QgsVectorLayer):
                raise RuntimeError("Camada ativa não é vetorial. Selecione feições em uma camada vetorial.")
            self._update_aoi_from_selection(lyr)
        else:
            if not self.rows:
                raise RuntimeError("Carregue o CSV de quadícula.")
            log("AOI ← CSV de quadícula")
            self.aoi = aoi_from_grid(self.rows)

        gj = geojson_from_qgsgeom(self.aoi)
        log(("AOI GeoJSON (probe)" if for_probe else "AOI GeoJSON (search)") + " = " + safe_json(gj))
        return gj

    def _selected_collections(self):
        cols = [
            self.listCols.item(i).data(QtCore.Qt.UserRole)
            for i in range(self.listCols.count())
            if self.listCols.item(i).checkState() == QtCore.Qt.Checked
        ]
        log(f"[CALL] BDCDialog._selected_collections() -> {cols}")
        return cols

    def _collection_meta(self, coll_id):
        for c in self._all_collections:
            if c.get("id") == coll_id:
                return c
        return None

    def _cloud_filter_allowed(self, selected_ids):
        log(f"[CALL] BDCDialog._cloud_filter_allowed(selected_ids={selected_ids})")
        stac = self._current_stac().rstrip("/")
        if stac == DEFAULT_STAC.rstrip("/"):
            return True
        if stac == ASTER_STAC.rstrip("/"):
            return False
        metas = [self._collection_meta(cid) for cid in selected_ids]
        if not metas:
            return False
        allowed = all(m and m.get("has_cloud_cover") for m in metas)
        log(f"[CLOUD] allowed={allowed} para {selected_ids}")
        return allowed

    def _http_error_message(self, err):
        log(f"[CALL] BDCDialog._http_error_message(err={type(err).__name__})")
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

    # ---------- UI actions ----------
    def load_collections(self):
        log("[CALL] BDCDialog.load_collections()")
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
            QtWidgets.QMessageBox.critical(self, "Erro /collections", self._http_error_message(e))
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro /collections", str(e))
            return
        self._all_collections = cols
        self._populate_cols(cols)

    def _populate_cols(self, cols):
        log(f"[CALL] BDCDialog._populate_cols(n={len(cols)})")
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
        log("[CALL] BDCDialog.apply_filter()")
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
        log("[CALL] BDCDialog.select_all_cols()")
        for i in range(self.listCols.count()):
            self.listCols.item(i).setCheckState(QtCore.Qt.Checked)

    def pick_grid(self):
        log("[CALL] BDCDialog.pick_grid()")
        p, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Selecionar quadricula.csv", "", "CSV (*.csv)")
        if not p:
            return
        try:
            self.rows = read_grid_csv(p)
            self.labGrid.setText(p)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "CSV", str(e))

    def pick_outdir(self):
        log("[CALL] BDCDialog.pick_outdir()")
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Pasta de saída", self.labOutdir.text())
        if d:
            self.labOutdir.setText(d)

    def do_probe(self):
        log("[CALL] BDCDialog.do_probe()")
        if self._is_aster_provider():
            QtWidgets.QMessageBox.information(
                self,
                "Probe",
                "Prova rápida não implementada para ASTER (earthaccess). Use 'Listar dados'."
            )
            return
        cols = self._selected_collections()
        if not cols:
            QtWidgets.QMessageBox.warning(self, "Coleções", "Marque pelo menos uma.")
            return
        try:
            aoi_gj = self._build_aoi(for_probe=True)
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "AOI", str(e))
            return
        start = self.edStart.date().toString("yyyy-MM-dd")
        end = self.edEnd.date().toString("yyyy-MM-dd")
        dt = f"{start}/{end}"
        ok, zero = [], []
        for coll in cols:
            try:
                allow_cloud = self._cloud_filter_allowed([coll])
                if not allow_cloud:
                    log(f"[PROBE] {coll}: filtro de nuvem omitido (sem eo:cloud_cover).")
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
                QtWidgets.QMessageBox.critical(
                    self,
                    "Erro /search",
                    f"{coll}: {self._http_error_message(e)}"
                )
                zero.append(coll)
            except Exception:
                zero.append(coll)
        log(f"PROBE: OK={ok} ZERO={zero}")

    def run_aster_earthaccess(self):
        log("[CALL] BDCDialog.run_aster_earthaccess()")
        try:
            self._ensure_earthaccess_login()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "earthaccess/login", str(e))
            return
        try:
            bbox = self._aster_search_bbox()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "AOI/Folha", str(e))
            return

        start = self.edStart.date().toString("yyyy-MM-dd")
        end = self.edEnd.date().toString("yyyy-MM-dd")
        temporal = (start, end)
        cloud_max = float(self.spCloud.value())
        fol = (self.edFolha.text() or "").strip()

        # geometria da folha (para cálculo de cobertura)
        folha_geom = None
        if fol:
            try:
                gj_f = get_folha_geom_geojson(fol)
                folha_geom = shp_shape(gj_f)
                log(f"[ASTER] Geometria da folha {fol} carregada para teste de cobertura.")
            except Exception as e:
                log(f"[ASTER] Não foi possível carregar geom da folha {fol}: {e}")
        if folha_geom is None and self.aoi is not None:
            try:
                gj_aoi = geojson_from_qgsgeom(self.aoi)
                folha_geom = shp_shape(gj_aoi)
                log("[ASTER] Usando AOI como geometria de referência para cobertura.")
            except Exception as e:
                log(f"[ASTER] Não foi possível converter AOI para geometria shapely: {e}")
        if folha_geom is not None and folha_geom.area <= 0:
            log("[ASTER] Aviso: área da geometria de referência (folha/AOI) é zero ou inválida.")

        query_params = {
            "provider": "ASTER_07XT_earthaccess",
            "bbox": bbox,
            "start": start,
            "end": end,
            "cloud_max": cloud_max,
            "folha": fol or None,
        }
        query_id = _build_query_id("aster07xt", query_params)
        log(f"[ASTER] query_id={query_id} params={safe_json(query_params)}")

        log(f"[ASTER] Busca AST_07XT bbox={bbox}, temporal={temporal}, nuvem<={cloud_max}")

        try:
            px_, py_ = folha_geom.centroid.x, folha_geom.centroid.y
            granules = list(
                ea.search_data(
                    short_name="AST_07XT",
                    version="004",
                    # bounding_box=bbox,
                    point=(px_, py_),
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

        EPS = 1e-3  # tolerância numérica para razão ~ 1.0

        for g in granules_f:
            umm = g.get("umm", {})

            coll = umm.get("CollectionReference", {}).get("ShortName", "AST_07XT")
            iid = umm.get("GranuleUR", "")

            cc = umm.get("CloudCover", "")

            te = umm.get("TemporalExtent", {})
            if "SingleDateTime" in te:
                dtm = te["SingleDateTime"]
            else:
                r = (te.get("RangeDateTimes") or te.get("RangeDateTime") or [{}])[0]
                dtm = r.get("BeginningDateTime", "")

            bbox_g = []
            granule_geom = None
            try:
                sp = umm.get("SpatialExtent", {})
                hs = sp.get("HorizontalSpatialDomain", {})
                geom = hs.get("Geometry", {})
                gpolys = geom.get("GPolygons") or []
                if gpolys:
                    pts = gpolys[0]["Boundary"]["Points"]
                    xs = [p["Longitude"] for p in pts]
                    ys = [p["Latitude"] for p in pts]
                    bbox_g = [min(xs), min(ys), max(xs), max(ys)]
                    coords = list(zip(xs, ys))
                    if len(coords) >= 3:
                        granule_geom = Polygon(coords)
            except Exception as e:
                log(f"[ASTER] Erro ao extrair footprint do granule {iid}: {e}")
                bbox_g = []

            coverage_ratio = None
            if folha_geom is not None and granule_geom is not None and folha_geom.area > 0:
                try:
                    inter = folha_geom.intersection(granule_geom)
                    inter_area = inter.area
                    folha_area = folha_geom.area
                    coverage_ratio = inter_area / folha_area if folha_area > 0 else 0.0
                    log(
                        f"[ASTER] {iid}: inter_area={inter_area:.6f}, folha_area={folha_area:.6f}, "
                        f"coverage_ratio={coverage_ratio:.3f}"
                    )
                    if coverage_ratio < 1.0 - EPS:
                        log(f"[ASTER] {iid}: descartado por cobertura < 100%.")
                        continue
                except Exception as e:
                    log(f"[ASTER] Falha ao calcular cobertura para {iid}: {e}")

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
                json.dumps(bbox_g),
                "data_links",
                best_href,
                json.dumps(hrefs),
                "" if coverage_ratio is None else f"{coverage_ratio:.3f}",
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(v))

            out.append({
                "collection": coll,
                "item_id": iid,
                "datetime": dtm,
                "cloud_cover": cc,
                "bbox": bbox_g,
                "assets": "data_links",
                "href_tif": best_href,
                "all_hrefs": hrefs,
                "coverage_ratio": coverage_ratio,
            })

        outdir = self.labOutdir.text().strip()
        os.makedirs(outdir, exist_ok=True)
        suffix = _safe_slug(fol, "aoi")
        out_csv = os.path.join(outdir, f"{query_id}_{suffix}.csv")

        log(f"[ASTER] Gravando CSV de granules (com coverage_ratio): {out_csv}")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(
                f,
                fieldnames=[
                    "query_id", "query_provider", "query_start", "query_end",
                    "query_cloud_max", "query_folha", "query_bbox",
                    "collection", "item_id", "datetime", "cloud_cover",
                    "bbox", "assets", "href_tif", "all_hrefs", "coverage_ratio",
                ],
            )
            wr.writeheader()
            for r in out:
                wr.writerow({
                    "query_id": query_id,
                    "query_provider": "ASTER_07XT_earthaccess",
                    "query_start": start,
                    "query_end": end,
                    "query_cloud_max": cloud_max,
                    "query_folha": fol,
                    "query_bbox": json.dumps(bbox),
                    "collection": r["collection"],
                    "item_id": r["item_id"],
                    "datetime": r["datetime"],
                    "cloud_cover": r["cloud_cover"],
                    "bbox": json.dumps(r["bbox"]),
                    "assets": r["assets"],
                    "href_tif": r["href_tif"],
                    "all_hrefs": json.dumps(r["all_hrefs"]),
                    "coverage_ratio": "" if r["coverage_ratio"] is None else f"{r['coverage_ratio']:.6f}",
                })

        log(f"[ASTER] {len(out)} granule(s) AST_07XT após filtro de cobertura. CSV: {out_csv}")

    def _clip_and_add_raster_local(self, local, name):
        log(f"[CALL] BDCDialog._clip_and_add_raster_local(local={local!r}, name={name!r})")
        import processing
        from qgis.PyQt.QtCore import QVariant

        gdal_tune_for_http()

        if self.aoi is None:
            try:
                log("[CLIP] AOI ainda não construída; chamando _build_aoi()")
                t_aoi0 = time.time()
                self._build_aoi()
                log(f"[CLIP] AOI construída em {time.time() - t_aoi0:.3f} s")
            except Exception as e:
                QtWidgets.QMessageBox.warning(self, "AOI", str(e))
                log(f"[CLIP] Erro ao construir AOI: {e}")
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

        log("[CLIP] AOI_layer em memória criado com 1 feição.")

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

        log(f"[CLIP] Params gdal:cliprasterbymasklayer: {params!r}")

        try:
            log("[CLIP] Iniciando gdal:cliprasterbymasklayer...")
            t_clip0 = time.time()
            res = processing.run("gdal:cliprasterbymasklayer", params)
            t_clip = time.time() - t_clip0
            log(f"[CLIP] gdal:cliprasterbymasklayer terminou em {t_clip:.1f} s")
        except Exception as e:
            log(f"[CLIP] Erro ao recortar raster: {e}")
            return False

        out_path = res.get("OUTPUT")
        log(f"[CLIP] OUTPUT={out_path!r}")
        if not out_path:
            log("[CLIP] Clip não retornou caminho de saída.")
            return False

        log(f"[CLIP] Criando QgsRasterLayer a partir de {out_path!r}")
        rl = QgsRasterLayer(out_path, name, "gdal")

        if rl.isValid():
            log(
                f"[CLIP] Raster recortado válido: size={rl.width()}x{rl.height()}, crs={rl.crs().authid()}"
            )
            QgsProject.instance().addMapLayer(rl)
            log("[CLIP] Raster adicionado ao projeto QGIS.")
            return True

        log("[CLIP] GDAL não validou raster recortado (rl.isValid() == False).")
        return False

    def _clip_and_add_raster(self, href, name):
        log(f"[CALL] BDCDialog._clip_and_add_raster(href={href!r}, name={name!r})")

        outdir = self.labOutdir.text().strip() or tempfile.gettempdir()
        os.makedirs(outdir, exist_ok=True)
        local = os.path.join(outdir, os.path.basename(href))

        if os.path.exists(local):
            size_mb = os.path.getsize(local) / (1024 * 1024)
            log(f"[CLIP] Arquivo local já existe ({size_mb:.1f} MB): {local}")
            return self._clip_and_add_raster_local(local, name)

        desc = f"Download ASTER para clip: {os.path.basename(local)}"
        log(f"[TASK-CLIP] Criando task: {desc}")

        task = QgsTask.fromFunction(
            desc,
            _download_for_clip,
            on_finished=_on_download_for_clip_finished,
            flags=QgsTask.CanCancel,
            href=href,
            local=local,
            name=name,
            dlg=self,
        )
        QgsApplication.taskManager().addTask(task)
        log(f"[TASK-CLIP] Tarefa adicionada ao Task Manager: {task.description()}")
        return True

    def run_search(self):
        log("[CALL] BDCDialog.run_search()")
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
            QtWidgets.QMessageBox.warning(self, "AOI", str(e))
            return

        start = self.edStart.date().toString("yyyy-MM-dd")
        end = self.edEnd.date().toString("yyyy-MM-dd")
        dt = f"{start}/{end}"

        try:
            allow_cloud = self._cloud_filter_allowed(cols)
            if not allow_cloud:
                log("[SEARCH] Filtro de nuvem omitido (coleções/provedor sem eo:cloud_cover).")
            cloud_val = float(self.spCloud.value()) if allow_cloud else None

            selected_ids = sorted(set(cols))
            query_params = {
                "provider": self._current_stac().rstrip("/"),
                "collections": selected_ids,
                "start": start,
                "end": end,
                "max_cloud": cloud_val,
                "limit": int(self.spLimit.value()),
                "sort": "asc" if self.cbAsc.isChecked() else "desc",
                "aoi": aoi_gj,
            }
            query_id = _build_query_id("stac", query_params)
            log(f"[SEARCH] query_id={query_id} params={safe_json(query_params)}")

            js = stac_search(
                self._current_stac(),
                cols,
                aoi_gj,
                dt,
                max_cloud=cloud_val,
                limit=int(self.spLimit.value()),
                sort="asc" if self.cbAsc.isChecked() else "desc",
            )
        except requests.exceptions.HTTPError as e:
            QtWidgets.QMessageBox.critical(self, "Erro /search", self._http_error_message(e))
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro /search", str(e))
            return

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
                "",  # coverage_ratio não calculado para BDC genérico
            ]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(v))
            out.append({
                "collection": coll,
                "item_id": iid,
                "datetime": dtm,
                "cloud_cover": cc,
                "bbox": json.dumps(bbox),
                "assets": ",".join(assets.keys()),
                "href_tif": best_href or "",
                "all_hrefs": all_hrefs,
                "coverage_ratio": None,
            })

        outdir = self.labOutdir.text().strip()
        os.makedirs(outdir, exist_ok=True)
        folha = (self.edFolha.text() or "").strip()
        suffix = _safe_slug(folha, "aoi")
        out_csv = os.path.join(outdir, f"{query_id}_{suffix}.csv")

        log(f"[SEARCH] Gravando CSV de itens STAC: {out_csv}")
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(
                f,
                fieldnames=[
                    "query_id", "query_provider", "query_start", "query_end",
                    "query_cloud_max", "query_collections", "query_sort", "query_limit", "query_aoi",
                    "collection", "item_id", "datetime", "cloud_cover",
                    "bbox", "assets", "href_tif", "all_hrefs", "coverage_ratio",
                ],
            )
            wr.writeheader()
            for r in out:
                wr.writerow({
                    "query_id": query_id,
                    "query_provider": self._current_stac().rstrip("/"),
                    "query_start": start,
                    "query_end": end,
                    "query_cloud_max": cloud_val,
                    "query_collections": ";".join(selected_ids),
                    "query_sort": "asc" if self.cbAsc.isChecked() else "desc",
                    "query_limit": int(self.spLimit.value()),
                    "query_aoi": safe_json(aoi_gj),
                    "collection": r["collection"],
                    "item_id": r["item_id"],
                    "datetime": r["datetime"],
                    "cloud_cover": r["cloud_cover"],
                    "bbox": r["bbox"],
                    "assets": r["assets"],
                    "href_tif": r["href_tif"],
                    "all_hrefs": json.dumps(r["all_hrefs"]),
                    "coverage_ratio": "",
                })
        log(f"{len(out)} item(ns) encontrados. CSV: {out_csv}")

    # ---------- ações finais ----------
    def _selected_rows(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        log(f"[CALL] BDCDialog._selected_rows() -> {rows}")
        return rows

    def view_selected(self):
        log("[CALL] BDCDialog.view_selected()")
        rows = self._selected_rows()
        if not rows:
            QtWidgets.QMessageBox.information(self, "Selecionar", "Selecione linha(s) na tabela.")
            return
        ok = 0
        for r in rows:
            href = self.table.item(r, 6).text().strip() if self.table.item(r, 6) else ""
            coll = self.table.item(r, 0).text().strip()
            log(f"[VIEW] row={r}, coll={coll}, href={href!r}")
            if not href:
                log(f"[{r + 1}] sem href_tif — tente baixar todos assets.")
                continue
            name = f"{coll}:{os.path.basename(href)}"
            if self._is_aster_provider():
                if self._clip_and_add_raster(href, name):
                    ok += 1
            else:
                if open_raster(href, name=name, outdir=self.labOutdir.text().strip(), just_download=False):
                    ok += 1
        QtWidgets.QMessageBox.information(
            self,
            "Visualizar",
            f"{ok} requisição(ões) enviada(s). Para ASTER, acompanhe o progresso no Task Manager do QGIS."
        )

    def download_selected(self):
        log("[CALL] BDCDialog.download_selected()")
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
            log(f"[DL] row={r}, to_get={to_get}")
            for href in to_get:
                if open_raster(
                    href, name=os.path.basename(href), outdir=outdir,
                    just_download=True
                ):
                    ok += 1
        text_ = f"{ok} arquivo(s) baixado(s) para:\n{outdir}"
        QtWidgets.QMessageBox.information(self, "Download", text_)

    # ---------- slots auxiliares ----------
    def _on_aoi_source_toggled(self, checked):
        log(f"[CALL] BDCDialog._on_aoi_source_toggled(checked={checked})")

    def _on_layer_selection_changed(self, *args):
        log("[CALL] BDCDialog._on_layer_selection_changed()")
        if not self.rbSel.isChecked():
            return
        layer = self._sel_layer_ or iface.activeLayer()
        if not isinstance(layer, QgsVectorLayer):
            return
        try:
            self._update_aoi_from_selection(layer)
        except Exception as e:
            log(f"[SEL] Erro ao atualizar AOI/Folha a partir da seleção: {e}")

    def _on_current_layer_changed(self, layer):
        name = getattr(layer, "name", None)
        log(f"[CALL] BDCDialog._on_current_layer_changed(layer={name!r})")

        if isinstance(self._sel_layer_, QgsVectorLayer):
            try:
                self._sel_layer_.selectionChanged.disconnect(self._on_layer_selection_changed)
            except TypeError:
                pass

        self._sel_layer_ = layer

        if isinstance(layer, QgsVectorLayer):
            try:
                layer.selectionChanged.connect(self._on_layer_selection_changed)
            except TypeError:
                pass

            if layer.selectedFeatureCount() > 0:
                self._on_layer_selection_changed()


def run():
    log("[ENTRYPOINT] run() chamado.")
    dlg = BDCDialog()
    dlg.show()
    globals()['__BDC_DLG__'] = dlg


run()

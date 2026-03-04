#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Preditor Terra (QGIS Dock) — Aerogeofísica + SOM + Satélite (BDC/INPE/STAC)
# - Interface 100% PyQt dentro do QGIS (sem Jupyter).
# - Boxplots por FEATURE com escalas independentes (horizontais).
# - Pré-visualização, treino/aplicação SOM, STAC (listar/baixar/amostrar).
import os
# ==== Garantir PROJ_DATA/PROJ_LIB se não estiverem exportadas ====
try:
    _proj_guess = "/usr/share/proj"
    if os.path.exists(os.path.join(_proj_guess, "proj.db")):
        os.environ.setdefault("PROJ_DATA", _proj_guess)
        os.environ.setdefault("PROJ_LIB", _proj_guess)
except Exception:
    pass

# ============================ IMPORTS ============================
from qgis.PyQt import QtCore, QtGui, QtWidgets
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

import os, re, json, math, warnings, tempfile, requests, pathlib
import numpy as np
import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm

try:
    from sklearn_som.som import SOM as _SklearnSOM
except Exception:
    _SklearnSOM = None
try:
    from sklearn.preprocessing import StandardScaler as _SkStandardScaler
    from sklearn.impute import SimpleImputer as _SkSimpleImputer
except Exception:
    _SkStandardScaler = None
    _SkSimpleImputer = None

from shapely import wkt as shp_wkt
from shapely.ops import transform as shp_transform
from pyproj import Transformer, CRS
try:
    import verde as vd  # type: ignore
except Exception:
    vd = None
try:
    import rasterio  # type: ignore
except Exception:
    rasterio = None
try:
    from pystac_client import Client  # type: ignore
except Exception:
    Client = None
try:
    import psycopg2  # type: ignore
except Exception:
    psycopg2 = None

from qgis.core import (
    QgsProject, QgsVectorLayer, QgsFeature, QgsGeometry, QgsPointXY,
    QgsFields, QgsField, QgsSymbol, QgsRendererRange, QgsGraduatedSymbolRenderer,
    QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsLayerTreeGroup,
    QgsStyle, QgsGradientColorRamp, QgsRasterLayer, QgsRasterShader,
    QgsColorRampShader, QgsSingleBandPseudoColorRenderer, QgsApplication
)
from osgeo import gdal, osr

warnings.filterwarnings("ignore")

if vd is None:
    class _VerdeCompat:
        @staticmethod
        def inside(coords, region):
            x, y = coords
            w, e, s, n = region
            x = np.asarray(x, dtype="float64")
            y = np.asarray(y, dtype="float64")
            return (x >= w) & (x <= e) & (y >= s) & (y <= n)

        @staticmethod
        def grid_coordinates(region, spacing=(100.0, 100.0), pixel_register=True):
            w, e, s, n = region
            if isinstance(spacing, (tuple, list)):
                dx = float(spacing[0]); dy = float(spacing[1])
            else:
                dx = dy = float(spacing)
            if pixel_register:
                x0 = w + 0.5 * dx
                y0 = s + 0.5 * dy
                xs = np.arange(x0, e - 0.5 * dx + 1e-9, dx, dtype="float64")
                ys = np.arange(y0, n - 0.5 * dy + 1e-9, dy, dtype="float64")
            else:
                xs = np.arange(w, e + 1e-9, dx, dtype="float64")
                ys = np.arange(s, n + 1e-9, dy, dtype="float64")
            if xs.size == 0:
                xs = np.array([w], dtype="float64")
            if ys.size == 0:
                ys = np.array([s], dtype="float64")
            return np.meshgrid(xs, ys)

    vd = _VerdeCompat()

if _SkSimpleImputer is None:
    class SimpleImputer:
        def __init__(self, strategy='median'):
            self.strategy = strategy
            self.fill_ = None

        def fit(self, X):
            X = np.asarray(X, dtype="float64")
            if self.strategy != 'median':
                raise ValueError("Fallback SimpleImputer suporta apenas strategy='median'.")
            fill = np.nanmedian(X, axis=0)
            fill = np.where(np.isfinite(fill), fill, 0.0)
            self.fill_ = fill
            return self

        def transform(self, X):
            if self.fill_ is None:
                raise RuntimeError("SimpleImputer não ajustado.")
            X = np.asarray(X, dtype="float64").copy()
            mask = ~np.isfinite(X)
            if mask.any():
                X[mask] = np.take(self.fill_, np.where(mask)[1])
            return X

        def fit_transform(self, X):
            return self.fit(X).transform(X)
else:
    SimpleImputer = _SkSimpleImputer

if _SkStandardScaler is None:
    class StandardScaler:
        def __init__(self):
            self.mean_ = None
            self.scale_ = None

        def fit(self, X):
            X = np.asarray(X, dtype="float64")
            self.mean_ = np.mean(X, axis=0)
            sc = np.std(X, axis=0)
            sc = np.where(sc > 1e-12, sc, 1.0)
            self.scale_ = sc
            return self

        def transform(self, X):
            if self.mean_ is None or self.scale_ is None:
                raise RuntimeError("StandardScaler não ajustado.")
            X = np.asarray(X, dtype="float64")
            return (X - self.mean_) / self.scale_
else:
    StandardScaler = _SkStandardScaler

if _SklearnSOM is None:
    class SOM:
        """
        Fallback mínimo para SOM 1D (n=1), compatível com fit/predict/transform usados no dock.
        """
        def __init__(self, m=8, n=1, sigma=1.5, dim=4, max_iter=5000, learning_rate=0.5):
            self.m = int(m)
            self.n = int(n)
            self.k = self.m * self.n
            self.sigma = float(sigma)
            self.dim = int(dim)
            self.max_iter = int(max_iter)
            self.learning_rate = float(learning_rate)
            self.weights_ = None

        def fit(self, X):
            X = np.asarray(X, dtype="float64")
            if X.ndim != 2 or X.shape[1] != self.dim:
                raise ValueError(f"X deve ter shape [n, {self.dim}]")
            if X.shape[0] == 0:
                raise ValueError("X vazio para treino SOM.")

            rng = np.random.default_rng(42)
            idx = rng.integers(0, X.shape[0], size=self.k)
            W = X[idx].copy()
            unit_pos = np.arange(self.k, dtype="float64")

            for t in range(max(1, self.max_iter)):
                x = X[rng.integers(0, X.shape[0])]
                d = np.linalg.norm(W - x, axis=1)
                bmu = int(np.argmin(d))

                frac = 1.0 - (t / max(1, self.max_iter - 1))
                lr = max(0.01, self.learning_rate * frac)
                radius = max(1.0, self.sigma * frac)
                h = np.exp(-((unit_pos - bmu) ** 2) / (2.0 * radius * radius))
                W += (lr * h[:, None]) * (x - W)

            self.weights_ = W
            return self

        def transform(self, X):
            if self.weights_ is None:
                raise RuntimeError("SOM não treinado.")
            X = np.asarray(X, dtype="float64")
            # Distância para cada neurônio [n_samples, k]
            D = np.sqrt(((X[:, None, :] - self.weights_[None, :, :]) ** 2).sum(axis=2))
            return D

        def predict(self, X):
            D = self.transform(X)
            return np.argmin(D, axis=1)
else:
    SOM = _SklearnSOM

# ============================ HOTFIX PROJ/pyproj ============================
# Corrige "pyproj.exceptions.CRSError: ... no database context specified"
# quando o QGIS é iniciado com PYTHONPATH apontando para o pyenv.
def _ensure_proj():
    try:
        from pyproj import datadir as _pdat
    except Exception:
        return
    # Já está ok?
    cur = _pdat.get_data_dir()
    if cur and os.path.isfile(os.path.join(cur, "proj.db")):
        return
    # Candidatos comuns
    cands = []
    # Do ambiente
    for k in ("PROJ_DATA", "PROJ_LIB"):
        v = os.environ.get(k)
        if v: cands.append(v)
    # Padrões de sistema
    cands += [
        "/usr/share/proj",
        "/usr/local/share/proj",
        os.path.join(QgsApplication.prefixPath(), "share", "proj"),
        os.path.join(QgsApplication.prefixPath(), "proj"),
    ]
    # Filtra por existência do proj.db
    use = None
    for p in cands:
        if p and os.path.isfile(os.path.join(p, "proj.db")):
            use = p
            break
    if use:
        os.environ["PROJ_DATA"] = use
        os.environ["PROJ_LIB"]  = use
        try: _pdat.set_data_dir(use)
        except Exception: pass

_ensure_proj()


# ============================ LOGGING ROBUSTO ============================
import logging, sys, os, inspect, pathlib, tempfile, time, traceback, functools
from logging.handlers import TimedRotatingFileHandler
from contextlib import contextmanager
from qgis.core import QgsMessageLog, Qgis
from qgis.PyQt.QtCore import qInstallMessageHandler, QtMsgType

MAX_LOG_CHARS = 4000  # evita despejar AOIs gigantes no painel

def _preferred_logs_dir():
    env = os.environ.get("PREDITOR_TERRA_LOG_DIR")
    if env:
        p = pathlib.Path(env).expanduser(); p.mkdir(parents=True, exist_ok=True); return str(p)
    try:
        here = pathlib.Path(inspect.getsourcefile(lambda:0) or ".").resolve()
        p = (here.parent / "logs"); p.mkdir(parents=True, exist_ok=True); return str(p)
    except Exception:
        pass
    p = pathlib.Path.home() / "PreditorTerra" / "logs"
    try:
        p.mkdir(parents=True, exist_ok=True); return str(p)
    except Exception:
        pass
    p = pathlib.Path(tempfile.gettempdir()) / "PreditorTerra"
    p.mkdir(parents=True, exist_ok=True); return str(p)

class _QgsHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            lvl = Qgis.Critical if record.levelno>=logging.ERROR else (Qgis.Warning if record.levelno>=logging.WARNING else Qgis.Info)
            QgsMessageLog.logMessage(msg, 'Preditor Terra', lvl)
        except Exception:
            pass

def setup_logger(name="PreditorTerra", level=None):
    logger = logging.getLogger(name)
    if getattr(logger, "_pt_configured", False):
        return logger
    lvl_name = str(level or os.environ.get("PREDITOR_TERRA_LOG_LEVEL","INFO")).upper()
    lvl = getattr(logging, lvl_name, logging.INFO)
    logger.setLevel(lvl)

    fmt = logging.Formatter(
        '%(asctime)s.%(msecs)03dZ | %(levelname)s | %(name)s | %(threadName)s | %(funcName)s:%(lineno)d | %(message)s',
        datefmt='%Y-%m-%dT%H:%M:%S'
    )
    logs_dir = _preferred_logs_dir(); fpath = os.path.join(logs_dir, "preditor_terra.log")
    fh = TimedRotatingFileHandler(fpath, when="midnight", backupCount=14, utc=True, encoding='utf-8'); fh.setFormatter(fmt); fh.setLevel(lvl); logger.addHandler(fh)
    ch = logging.StreamHandler(stream=sys.stderr); ch.setFormatter(fmt); ch.setLevel(lvl); logger.addHandler(ch)
    qh = _QgsHandler(); qh.setFormatter(logging.Formatter('%(asctime)s | %(levelname)s | %(message)s', datefmt='%H:%M:%S')); qh.setLevel(lvl); logger.addHandler(qh)

    logging.captureWarnings(True)
    def _qt_handler(mode, context, message):
        if mode == QtMsgType.QtDebugMsg:   logger.debug("Qt: %s", message)
        elif mode == QtMsgType.QtInfoMsg:  logger.info("Qt: %s", message)
        elif mode == QtMsgType.QtWarningMsg: logger.warning("Qt: %s", message)
        elif mode == QtMsgType.QtCriticalMsg: logger.error("Qt: %s", message)
        elif mode == QtMsgType.QtFatalMsg: logger.critical("Qt: %s", message)
        else: logger.info("Qt: %s", message)
    try: qInstallMessageHandler(_qt_handler)
    except Exception: pass

    def _excepthook(etype, value, tb):
        logger.exception("Exceção não tratada: %s: %s", etype.__name__, value)
        try:
            from qgis.utils import iface
            iface.messageBar().pushCritical("Preditor Terra", f"Erro: {value}")
        except Exception:
            pass
    sys.excepthook = _excepthook

    logger._pt_configured = True
    logger.info("Logger inicializado | dir=%s | file=%s | level=%s", logs_dir, fpath, lvl_name)
    return logger

LOGGER = setup_logger()
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

def logcall(level=logging.INFO, with_args=True, with_time=True):
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            t0 = time.perf_counter() if with_time else None
            if with_args:
                try:
                    arg_s = ", ".join([*map(repr, args[1:]), *(f"{k}={v!r}" for k,v in kwargs.items())])
                except Exception:
                    arg_s = "..."
                LOGGER.log(level, "▶ %s(%s)", fn.__name__, arg_s)
            else:
                LOGGER.log(level, "▶ %s", fn.__name__)
            try:
                res = fn(*args, **kwargs)
                if with_time and t0 is not None:
                    LOGGER.log(level, "✔ %s ok (%.3fs)", fn.__name__, time.perf_counter()-t0)
                return res
            except Exception as e:
                LOGGER.exception("✖ %s falhou: %s", fn.__name__, e); raise
        return wrapper
    return deco

from contextlib import contextmanager
@contextmanager
def timed_step(msg, level=logging.INFO):
    t0 = time.perf_counter(); LOGGER.log(level, "⏱ %s…", msg)
    try:
        yield
        LOGGER.log(level, "⏱ %s concluído (%.3fs)", msg, time.perf_counter()-t0)
    except Exception as e:
        LOGGER.exception("⏱ %s falhou: %s", msg, e); raise

# ============================ CONFIG/ESTADO ============================
ESCALAS = ['25k','50k','100k','250k','1kk']
MAX_LOG_CHARS = 1400  # evita travar UI com mensagens gigantes (ex. GeoJSON longos)

quadricula = {}         # {fid: { 'folha': Series(EPSG=...), 'gama_*': df, 'mag_*': df, 'geof_*': df, ... }}
data_grid = None        # nome da camada interpolada SOM (ex.: 'geof_1105_linear')
som_store = {}          # {k: {'som','imp','sca','feats','layer'}}
som_last_pred = None
bdc_items = []          # lista de pystac.Item da busca corrente
sat_store = {}          # { item_id: {'collection','datetime','bbox','assets':{name:path}, 'hrefs':{name:href}} }

# Backend de dados para a etapa SOM (postgres|files)
DATA_BACKEND = os.getenv("PREDITOR_DATA_BACKEND", "postgres").strip().lower()

# PostgreSQL (usado quando DATA_BACKEND=postgres ou fonte iniciando com db:)
PG_HOST = os.getenv("PREDITOR_PG_HOST", "127.0.0.1")
PG_PORT = int(os.getenv("PREDITOR_PG_PORT", "5432"))
PG_DB = os.getenv("PREDITOR_PG_DB", "geologia")
PG_USER = os.getenv("PREDITOR_PG_USER", "postgres")
PG_PASS = os.getenv("PREDITOR_PG_PASS", "")
PG_CONNECT_TIMEOUT = int(os.getenv("PREDITOR_PG_CONNECT_TIMEOUT", "8"))

PG_DEFAULT_GAMA_SOURCE = os.getenv("PREDITOR_PG_GAMA_SOURCE", "geof.v_gamma_1082_corr")
PG_DEFAULT_MAG_SOURCE = os.getenv("PREDITOR_PG_MAG_SOURCE", "").strip()

# ====================== BACKEND: CAMINHOS / DADOS BASE ======================
def set_gdb(path=''):
    """Raiz dos dados locais."""
    return os.path.join('/home/database/', path)

def import_xyz(caminho):
    """Lê CSV/XYZ de dados aerogeofísicos."""
    return pd.read_csv(caminho)


def _use_postgres_backend():
    return DATA_BACKEND in {"postgres", "postgis", "db"}


def _is_db_source_name(name):
    if not name:
        return False
    txt = str(name).strip().lower()
    if txt.startswith("db:"):
        return True
    return txt.startswith("geof.") or txt.startswith("carto.") or txt.startswith("litologia.")


def _normalize_pg_relation(name, default_schema="geof"):
    if not name:
        return None
    txt = str(name).strip()
    txt_l = txt.lower()
    if txt_l in {"none", "(sem fonte no banco)", "(sem fonte)", "sem fonte", "off", "null", "-"}:
        return None
    if txt_l.startswith("db:"):
        txt = txt.split(":", 1)[1].strip()
    if "." not in txt:
        txt = f"{default_schema}.{txt}"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)?", txt):
        raise ValueError(f"Nome de relação SQL inválido: {txt!r}")
    return txt


def _pg_connect():
    if psycopg2 is None:
        raise RuntimeError("psycopg2 não disponível no ambiente Python do QGIS.")
    kwargs = {
        "host": PG_HOST,
        "port": PG_PORT,
        "dbname": PG_DB,
        "user": PG_USER,
        "connect_timeout": PG_CONNECT_TIMEOUT,
    }
    if PG_PASS:
        kwargs["password"] = PG_PASS
    return psycopg2.connect(**kwargs)


def _apply_folha_filters(df, ID=None, IDs=None):
    if IDs:
        return df[df["id_folha"].astype(str).isin([str(i) for i in IDs])].copy()
    if ID:
        if isinstance(ID, (list, tuple, set)):
            pattern = "|".join(map(re.escape, ID))
        else:
            pattern = str(ID)
        return df[df["id_folha"].astype(str).str.contains(pattern, na=False)].copy()
    return df


def _import_malha_cartog_from_postgres(escala='25k', ID=None, IDs=None):
    sql = """
        SELECT
            codigo AS id_folha,
            epsg   AS "EPSG",
            ST_AsText(ST_Transform(geom, 4326)) AS geometry_wkt
        FROM carto.folhas_cartograficas
        WHERE escala = %s
    """
    with _pg_connect() as conn:
        df = pd.read_sql_query(sql, conn, params=[escala])
    if df.empty:
        return df
    df["geometry"] = df["geometry_wkt"].map(lambda v: shp_wkt.loads(v) if v else None)
    df.drop(columns=["geometry_wkt"], inplace=True)
    df["EPSG"] = pd.to_numeric(df["EPSG"], errors="coerce").astype("Int64")
    return _apply_folha_filters(df, ID=ID, IDs=IDs)


def _import_malha_cartog_from_gpkg(escala='25k', ID=None, IDs=None):
    """
    Lê a malha do GeoPackage e filtra por id_folha (exato ou regex).

    Implementação baseada em QgsVectorLayer para evitar o uso de geopandas/pyproj
    dentro do QGIS (que é o que dispara o erro 'Invalid projection: EPSG:4326').
    Retorna um pandas.DataFrame com coluna 'geometry' (objetos shapely) e, se
    possível, uma coluna 'EPSG' numérica.
    """
    from shapely import wkt

    path_gpkg = set_gdb('geodatabase.gpkg')
    layer_name = 'mc_' + escala
    uri = f"{path_gpkg}|layername={layer_name}"

    vlayer = QgsVectorLayer(uri, layer_name, 'ogr')
    if not vlayer.isValid():
        raise RuntimeError(f"Falha ao abrir malha cartográfica: {uri}")

    fields = vlayer.fields()
    field_names = [f.name() for f in fields]

    # EPSG padrão a partir do CRS da layer
    authid = vlayer.crs().authid()  # ex.: "EPSG:4326"
    default_epsg = None
    if authid and authid.upper().startswith("EPSG:"):
        try:
            default_epsg = int(authid.split(":")[1])
        except Exception:
            default_epsg = None

    rows = []
    for feat in vlayer.getFeatures():
        attrs = feat.attributes()
        rec = {name: attrs[i] for i, name in enumerate(field_names)}

        geom = feat.geometry()
        rec["geometry"] = wkt.loads(geom.asWkt()) if (geom and not geom.isEmpty()) else None

        # Se existir coluna EPSG no atributo, normaliza; senão usa o EPSG do CRS
        if "EPSG" in rec and rec["EPSG"] is not None:
            try:
                rec["EPSG"] = int(rec["EPSG"])
            except Exception:
                pass
        elif default_epsg is not None:
            rec.setdefault("EPSG", default_epsg)

        rows.append(rec)

    mc = pd.DataFrame.from_records(rows)

    return _apply_folha_filters(mc, ID=ID, IDs=IDs)


def import_malha_cartog(escala='25k', ID=None, IDs=None):
    """
    Lê a malha cartográfica preferindo PostgreSQL (quando habilitado) com fallback para GeoPackage.
    """
    pg_exc = None
    if _use_postgres_backend():
        try:
            mc = _import_malha_cartog_from_postgres(escala=escala, ID=ID, IDs=IDs)
            LOGGER.info("Malha carregada do PostgreSQL: escala=%s linhas=%s", escala, len(mc))
            return mc
        except Exception as e:
            pg_exc = e
            LOGGER.warning("Falha lendo malha no PostgreSQL (%s). Fallback para GeoPackage.", e)

    try:
        mc = _import_malha_cartog_from_gpkg(escala=escala, ID=ID, IDs=IDs)
        LOGGER.info("Malha carregada do GeoPackage: escala=%s linhas=%s", escala, len(mc))
        return mc
    except Exception as gpkg_e:
        if pg_exc is not None:
            raise RuntimeError(f"Falha na malha via PostgreSQL ({pg_exc}) e GeoPackage ({gpkg_e}).")
        raise



def import_mc(escala=None, ID=None):
    """Compat: wrapper para import_malha_cartog com a mesma assinatura antiga."""
    return import_malha_cartog(escala=escala, ID=ID)

def Build_mc(escala='50k', ID=['SF23_YA'], verbose=None):
    """Monta dicionário-base 'quadricula' a partir da malha cartográfica."""
    mc = import_mc(escala, ID)
    mc.set_index('id_folha', inplace=True)
    q = {}
    for idx, row in mc.iterrows():
        q[idx] = {'folha': row, 'escala': escala}
        if verbose:
            print(f' - Folha "{idx}" adicionada.')
    if verbose:
        print(f'\n  {len(q)} folhas adicionadas.')
    return q


def _load_gamma_from_postgres_for_folha(folha_codigo, source_relation, extend_size=0):
    rel = _normalize_pg_relation(source_relation, default_schema="geof")
    if rel is None:
        return pd.DataFrame()
    sql = f"""
        WITH folha AS (
            SELECT geom, epsg
            FROM carto.folhas_cartograficas
            WHERE codigo = %s
            LIMIT 1
        ),
        aoi AS (
            SELECT CASE
                WHEN %s::double precision > 0
                THEN ST_Transform(ST_Buffer(ST_Transform(geom, epsg), %s::double precision), 4326)
                ELSE ST_Transform(geom, 4326)
            END AS geom4326
            FROM folha
        )
        SELECT
            g.x::double precision          AS "X",
            g.y::double precision          AS "Y",
            g.ctcor::double precision      AS "CTCOR",
            g.eth::double precision        AS "eTh",
            g.eu::double precision         AS "eU",
            g.kperc::double precision      AS "KPERC",
            g.uth_razao::double precision  AS "UTHRAZAO",
            g.uk_razao::double precision   AS "UKRAZAO",
            g.thk_razao::double precision  AS "THKRAZAO",
            g.mdt::double precision        AS "MDT",
            g.lon::double precision        AS "LONGITUDE",
            g.lat::double precision        AS "LATITUDE"
        FROM {rel} g
        JOIN aoi ON ST_Intersects(g.geom, aoi.geom4326)
    """
    with _pg_connect() as conn:
        df = pd.read_sql_query(sql, conn, params=[folha_codigo, float(extend_size), float(extend_size)])
    return df


def _upload_geof_from_postgres(
    quadricula=None,
    gama_source=None,
    mag_source=None,
    extend_size=0,
    gama_alias=None,
):
    gama_df_all = pd.DataFrame()
    mag_df_all = pd.DataFrame()

    # Sem camada magnética equivalente no banco atual; mantemos opcional.
    mag_rel = _normalize_pg_relation(mag_source, default_schema="geof") if mag_source else None
    if mag_rel:
        LOGGER.warning("Fonte magnética no banco ainda não implementada (%s). Prosseguindo sem MAG.", mag_rel)

    # Permite alias de chave (ex.: "db:geof.v_gamma_1082_corr") além do nome normalizado.
    gama_keys = [k for k in dict.fromkeys([gama_source, gama_alias]) if k]
    ids = list((quadricula or {}).keys())
    for fid in ids:
        g = _load_gamma_from_postgres_for_folha(fid, gama_source, extend_size=extend_size)
        if len(g) > 100:
            for k in gama_keys:
                quadricula[fid][k] = g
            gama_df_all = pd.concat([g, gama_df_all], ignore_index=True)
            LOGGER.info("GAMA DB atualizado em %s: +%d pontos (acumulado=%d)", fid, len(g), len(gama_df_all))
        else:
            LOGGER.info("GAMA DB insuficiente em %s: %d pontos", fid, len(g))

    return gama_df_all, mag_df_all


def Upload_geof(quadricula=None, gama_xyz=None, mag_xyz=None, extend_size=0):
    """Carrega dados brutos (gama/mag) e associa às folhas em 'quadricula'."""
    pg_err = None
    try_pg = _use_postgres_backend() or _is_db_source_name(gama_xyz) or _is_db_source_name(mag_xyz)
    if try_pg:
        gama_source = _normalize_pg_relation(gama_xyz, default_schema="geof") if gama_xyz else _normalize_pg_relation(PG_DEFAULT_GAMA_SOURCE, default_schema="geof")
        mag_source = _normalize_pg_relation(mag_xyz, default_schema="geof") if mag_xyz else _normalize_pg_relation(PG_DEFAULT_MAG_SOURCE, default_schema="geof")
        if not gama_source:
            gama_source = _normalize_pg_relation(PG_DEFAULT_GAMA_SOURCE, default_schema="geof")
        try:
            return _upload_geof_from_postgres(
                quadricula=quadricula,
                gama_source=gama_source,
                mag_source=mag_source,
                extend_size=extend_size,
                gama_alias=gama_xyz,
            )
        except Exception as e:
            pg_err = e
            LOGGER.warning("Falha ao carregar geofísica do PostgreSQL (%s). Tentando arquivos locais.", e)
            if _is_db_source_name(gama_xyz) or _is_db_source_name(mag_xyz):
                raise RuntimeError(f"Falha no carregamento geofísico via banco: {e}") from e

    import pyproj
    gama_df_all = pd.DataFrame(); mag_df_all = pd.DataFrame()

    gama_data = import_xyz(set_gdb('geof/'+gama_xyz)) if gama_xyz else None
    mag_data  = import_xyz(set_gdb('geof/'+mag_xyz))  if mag_xyz  else None

    if gama_data is not None:
        if 'LAT_WGS' in gama_data.columns:
            gama_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'}, inplace=True)
        if 'eTH' in gama_data.columns:
            gama_data.rename(columns={'eTH':'eTh'}, inplace=True)

    if mag_data is not None:
        if 'LAT_WGS' in mag_data.columns:
            mag_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'}, inplace=True)

    ids = list(quadricula.keys())
    for fid in ids:
        folha = quadricula[fid]['folha']
        utm = pyproj.CRS('EPSG:'+str(folha['EPSG']))
        wgs84 = pyproj.CRS('EPSG:4326')

        geom_wgs = folha['geometry']
        proj = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
        geom_utm = shp_transform(proj, geom_wgs)
        minx, miny, maxx, maxy = geom_utm.bounds
        region = (minx-extend_size, maxx+extend_size, miny-extend_size, maxy+extend_size)

        if gama_data is not None:
            g = gama_data[vd.inside((gama_data.X, gama_data.Y), region)]
            if len(g) > 1000:
                quadricula[fid][gama_xyz] = g
                gama_df_all = pd.concat([g, gama_df_all])
                print(f' - {gama_xyz} atualizado na folha: {fid} com {len(gama_df_all)} pontos')

        if mag_data is not None:
            m = mag_data[vd.inside((mag_data.X, mag_data.Y), region)]
            if len(m) > 1000:
                quadricula[fid][mag_xyz] = m
                mag_df_all = pd.concat([m, mag_df_all])
                print(f' - {mag_xyz} atualizado na folha: {fid} com {len(mag_df_all)} pontos')

    if pg_err is not None:
        LOGGER.info("Carga final via arquivos locais (fallback após erro PG): %s", pg_err)
    return gama_df_all, mag_df_all

def pop_nodata(q):
    """Remove folhas sem dados associados (apenas 'folha' e 'escala')."""
    for fid in list(q.keys()):
        if len(q[fid]) <= 2:
            q.pop(fid)
    return q

def transform_to_carta_utm(folha_series):
    """Converte a geometria da folha de WGS84→UTM da própria folha; retorna geom UTM."""
    wgs84 = CRS('EPSG:4326')
    utm = CRS('EPSG:'+str(folha_series['EPSG']))
    proj = Transformer.from_crs(wgs84, utm, always_xy=True).transform
    return shp_transform(proj, folha_series['geometry'])

def sintetic_grid(quad, fid, psize=100):
    """Gera grade sintética (centros) em UTM sobre a folha, espaçamento psize (m)."""
    geom_utm = transform_to_carta_utm(quad[fid]['folha'])
    minx, miny, maxx, maxy = geom_utm.bounds
    try:
        X, Y = vd.grid_coordinates(
            region=(minx, maxx, miny, maxy),
            spacing=(float(psize), float(psize)),
            pixel_register=True,
        )
        return X.ravel(order='C'), Y.ravel(order='C')
        LOGGER.debug("sintetic_grid fid=%s | psize=%s | nx=%d ny=%d",
                     fid, psize, X.shape[1], Y.shape[0])
        return X.ravel(order='C'), Y.ravel(order='C')
    except Exception:
        x0 = minx + 0.5*psize
        y0 = miny + 0.5*psize
        x = np.arange(x0, maxx - 0.5*psize + 1e-9, psize, dtype='float64')
        y = np.arange(y0, maxy - 0.5*psize + 1e-9, psize, dtype='float64')
        if x.size == 0: x = np.array([x0], dtype='float64')
        if y.size == 0: y = np.array([y0], dtype='float64')
        X, Y = np.meshgrid(x, y)
        LOGGER.debug("sintetic_grid(fid=%s) fallback | nx=%d ny=%d", fid, X.shape[1], Y.shape[0])
        return X.ravel(order='C'), Y.ravel(order='C')

# ====================== BACKEND: HELPERS GERAIS (QGIS/RASTER) ======================
def _minmax_from_tif(path):
    try:
        ds = gdal.Open(path, gdal.GA_ReadOnly)
        if ds is None:
            return None, None
        b = ds.GetRasterBand(1)
        stats = b.GetStatistics(False, True)
        if stats and len(stats) >= 2:
            vmin, vmax = float(stats[0]), float(stats[1])
            if np.isfinite(vmin) and np.isfinite(vmax) and vmin != vmax:
                return vmin, vmax
    except Exception:
        pass
    return None, None

def _temp_tif(name):
    base = re.sub(r'[^a-zA-Z0-9_]+','_', name)[:60]
    return os.path.join(tempfile.gettempdir(), f"{base}.tif")

def _normalize_xy(df):
    if not {'E_utm','N_utm'}.issubset(df.columns):
        if {'X','Y'}.issubset(df.columns):
            df = df.rename(columns={'X':'E_utm','Y':'N_utm'}).copy()
        else:
            raise ValueError("Camada sem 'X','Y' ou 'E_utm','N_utm'.")
    df = df.sort_values(['N_utm','E_utm'], ascending=[False, True], ignore_index=True, kind='mergesort')
    xs1d = np.sort(df['E_utm'].unique()); ys1d = np.sort(df['N_utm'].unique())
    nx, ny = xs1d.size, ys1d.size
    xs_mesh, ys_mesh = np.meshgrid(xs1d, ys1d)
    return df, xs_mesh, ys_mesh, nx, ny

def _mesh_from_df(df):  # alias
    return _normalize_xy(df)

def _gt_from_mesh(xs_mesh, ys_mesh):
    xs1d = xs_mesh[0, :]
    ys1d = ys_mesh[:, 0]
    dx = float(np.median(np.diff(xs1d))) if xs1d.size > 1 else 1.0
    dy = float(np.median(np.diff(ys1d))) if ys1d.size > 1 else 1.0
    x0 = float(xs1d.min() - dx/2.0)
    y0 = float(ys1d.max() + dy/2.0)  # topo
    return (x0, dx, 0.0, y0, 0.0, -dy)

def _write_tif_from_grid(arr2d, xs_mesh, ys_mesh, epsg, out_path, nodata=np.nan, gdal_type=gdal.GDT_Float32):
    ny, nx = arr2d.shape
    gt = _gt_from_mesh(xs_mesh, ys_mesh)
    drv = gdal.GetDriverByName("GTiff")
    ds = drv.Create(out_path, int(nx), int(ny), 1, gdal_type, options=["COMPRESS=LZW", "PREDICTOR=2"])
    srs = osr.SpatialReference(); srs.ImportFromEPSG(int(epsg))
    ds.SetProjection(srs.ExportToWkt()); ds.SetGeoTransform(gt)
    band = ds.GetRasterBand(1)
    if nodata is not None:
        band.SetNoDataValue(float(nodata))
    band.WriteArray(arr2d)
    band.FlushCache(); ds.FlushCache(); ds = None
    return out_path

def _ensure_group(path="Preditor Terra/Preview"):
    root = QgsProject.instance().layerTreeRoot()
    cur = root
    for part in path.split("/"):
        sub = None
        for ch in cur.children():
            if isinstance(ch, QgsLayerTreeGroup) and ch.name() == part:
                sub = ch; break
        if sub is None:
            sub = cur.addGroup(part)
        cur = sub
    return cur

def _remove_by_prefix(group, prefix):
    to_rm = []
    for ch in group.children():
        if hasattr(ch, "layer") and ch.layer() and ch.layer().name().startswith(prefix):
            to_rm.append(ch.layer().id())
    for lid in to_rm:
        lyr = QgsProject.instance().mapLayer(lid)
        if lyr:
            QgsProject.instance().removeMapLayer(lyr.id())

def _add_raster_to_group(path, name, group_path, numeric=True, classes=None, ramp_name="Spectral"):
    rl = QgsRasterLayer(path, name)
    if not rl.isValid():
        iface.messageBar().pushWarning("Preditor Terra", f"Raster inválido: {path}")
        return
    prov = rl.dataProvider()
    shader = QgsRasterShader()
    cshader = QgsColorRampShader()
    style = QgsStyle.defaultStyle()
    ramp = (style.colorRamp(ramp_name)
            or style.colorRamp("Viridis")
            or QgsGradientColorRamp(QtGui.QColor("black"), QtGui.QColor("white")))

    if numeric:
        vmin, vmax = _minmax_from_tif(path)
        if vmin is None or vmax is None or not np.isfinite(vmin) or not np.isfinite(vmax) or vmin == vmax:
            vmin, vmax = 0.0, 1.0
        items = [
            QgsColorRampShader.ColorRampItem(vmin, ramp.color(0.0), f"{vmin:.3g}"),
            QgsColorRampShader.ColorRampItem(vmax, ramp.color(1.0), f"{vmax:.3g}")
        ]
        cshader.setColorRampType(QgsColorRampShader.Interpolated)
        cshader.setColorRampItemList(items)
    else:
        k = int(classes or 1)
        items = []
        for i in range(1, k+1):
            t = (i-1)/max(1, k-1)
            items.append(QgsColorRampShader.ColorRampItem(i, ramp.color(t), f"Classe {i}"))
        cshader.setColorRampType(QgsColorRampShader.Discrete)
        cshader.setColorRampItemList(items)

    shader.setRasterShaderFunction(cshader)
    renderer = QgsSingleBandPseudoColorRenderer(prov, 1, shader)
    rl.setRenderer(renderer)

    parent = _ensure_group(group_path)
    QgsProject.instance().addMapLayer(rl, False)
    parent.addLayer(rl)

# ====================== LOG UI (com truncagem + arquivo) ======================
def _log(widget, msg, level="INFO"):
    s = str(msg)
    if len(s) > MAX_LOG_CHARS:
        s = s[:MAX_LOG_CHARS] + f" ... [truncado, {len(str(msg))} chars]"
    try:
        widget.appendPlainText(s)
    except Exception:
        pass
    lvl = getattr(logging, str(level).upper(), logging.INFO)
    LOGGER.log(lvl, str(msg))


def _info(widget, msg): _log(widget, msg, "INFO")
def _warn(widget, msg): _log(widget, msg, "WARNING")
def _err(widget, msg):  _log(widget, msg, "ERROR")

# ====================== BACKEND: LISTAGENS/INFOS ======================
def _ids_from_mc(escala, filtro_regex=None):
    mc = import_malha_cartog(escala=escala)
    ids = mc['id_folha'].astype(str).tolist()
    if filtro_regex:
        try:
            pat = re.compile(filtro_regex, re.IGNORECASE)
        except re.error:
            pat = re.compile(re.escape(filtro_regex), re.IGNORECASE)
        ids = [i for i in ids if pat.search(i)]
    return sorted(ids)

def _scan_layers_from_quadricula(q):
    layers = set()
    for _, blob in (q or {}).items():
        for k, v in blob.items():
            if isinstance(v, pd.DataFrame):
                layers.add(k)
    return tuple(sorted(layers))

def _available_columns(q, layers):
    cols = set()
    for _, blob in (q or {}).items():
        for lay in layers:
            df = blob.get(lay)
            if isinstance(df, pd.DataFrame):
                cols.update([c for c in df.columns if c not in ('X','Y','E_utm','N_utm')])
    cols = sorted(cols, key=lambda c: (c!='MDT', c))
    return tuple(cols)

_SYNONYMS = {
    'GMT': {'gmt','magigrf','magr','igrf','mag','gmtigrf'},
    'MDT': {'mdt','alte','altura'},
    'CTCOR': {'ctcor','ctc','ct'},
    'eTh': {'eth','eth_ppm','thc','th_ppm','ethppm','th'},
    'eU': {'eu','uc','u','euppm','u_ppm'},
    'KPERC': {'kperc','kc','k','kpct','k_percent'},
    'UTHRAZAO': {'uthrazao','uratio','u_th','u/th','u_th_ratio'},
    'UKRAZAO': {'ukrazao','u_k','u/k','u_k_ratio'},
    'THKRAZAO': {'thkrazao','th_k','th/k','th_k_ratio'},
}
def _norm_name(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())
def _find_source_column(df, canonical):
    want = _norm_name(canonical)
    for c in df.columns:
        if _norm_name(c) == want: return c
    for s in _SYNONYMS.get(canonical, set()):
        for c in df.columns:
            if _norm_name(c) == s: return c
    return None
def _source_order_for_feature(canonical):
    return ['mag','gama'] if canonical in ('GMT','MDT') else ['gama','mag']

def _resolve_blob_layer_df(blob, key):
    if not isinstance(blob, dict):
        return None
    df = blob.get(key)
    if isinstance(df, pd.DataFrame):
        return df
    # Compat: quando a UI usa "db:schema.tabela" e a chave interna foi normalizada.
    if _is_db_source_name(key):
        try:
            k_norm = _normalize_pg_relation(key, default_schema="geof")
            df2 = blob.get(k_norm)
            if isinstance(df2, pd.DataFrame):
                return df2
        except Exception:
            pass
    return None

def _infer_suffix_from_names(*names):
    for nm in names or []:
        m = re.search(r'(\d{4})', str(nm) if nm else '')
        if m: return m.group(1)
    return '0000'

def _grid_epsg_from_blob(blob):
    v = blob.get('folha', None)
    if v is not None:
        for key in ('EPSG','epsg'):
            if hasattr(v, key):
                try: return int(getattr(v, key))
                except Exception: pass
            if isinstance(v, dict) and key in v:
                try: return int(v[key])
                except Exception: pass
    if 'EPSG' in blob:
        try: return int(blob['EPSG'])
        except Exception: pass
    raise RuntimeError("Não foi possível inferir o EPSG da folha.")

# ====================== BACKEND: PREVIEW/INTERP ======================
def _plot_layers_for_column(q, ids, layers, column, remove_neg=False):
    parent = _ensure_group("Preditor Terra/Preview (rasters)")
    _remove_by_prefix(parent, prefix=f"PrevR_{column}_")

    total = 0
    for fid in ids:
        df = None; chosen = None
        for lay in layers:
            d = q.get(fid, {}).get(lay)
            if isinstance(d, pd.DataFrame) and column in d.columns:
                has_xy = {'E_utm','N_utm'}.issubset(d.columns) or {'X','Y'}.issubset(d.columns)
                if has_xy:
                    df = d.copy(); chosen = lay; break
        if df is None:
            continue

        if {'X','Y'}.issubset(df.columns):
            df = df.rename(columns={'X':'E_utm','Y':'N_utm'})
        if remove_neg and pd.api.types.is_numeric_dtype(df[column]):
            df.loc[df[column] < 0, column] = np.nan

        try:
            df_norm, xs_mesh, ys_mesh, nx, ny = _mesh_from_df(df[['E_utm','N_utm',column]])
        except Exception:
            continue

        vals = df_norm[column].to_numpy().astype('float32', copy=False)
        try:
            arr2d = vals.reshape(ny, nx)
        except Exception:
            arr2d = df_norm.pivot(index='N_utm', columns='E_utm', values=column).sort_index(ascending=False).to_numpy().astype('float32')

        try:
            epsg = _grid_epsg_from_blob(q.get(fid, {}))
        except Exception:
            epsg = 4326

        out_name = f"PrevR_{column}_{fid}_{chosen}"
        out_tif = _temp_tif(out_name)
        _write_tif_from_grid(arr2d, xs_mesh, ys_mesh, epsg, out_tif, nodata=np.nan, gdal_type=gdal.GDT_Float32)
        _add_raster_to_group(out_tif, out_name, "Preditor Terra/Preview (rasters)", numeric=True, ramp_name="Spectral")
        total += 1

    iface.messageBar().pushInfo("Preditor Terra", f"[Canvas] '{column}': {total} raster(s) adicionados.")

def _interpolate_current_selection(quad, ids, gama_key, mag_key, features, psize, algo, noneg=False):
    suf = _infer_suffix_from_names(gama_key, mag_key); out_name = f"geof_{suf}_{algo}"
    for fid in ids:
        blob = quad.get(fid, {})
        gdf = _resolve_blob_layer_df(blob, gama_key)
        mdf = _resolve_blob_layer_df(blob, mag_key)
        if gdf is None and mdf is None:
            LOGGER.warning("fid=%s sem dados brutos (%s/%s)", fid, gama_key, mag_key); continue
        xu, yu = sintetic_grid(quad, fid, psize=int(psize))
        sources = {}
        if isinstance(gdf, pd.DataFrame):
            gsrc = gdf.copy()
            if noneg:
                for c in gsrc.columns:
                    if c not in ('X','Y') and pd.api.types.is_numeric_dtype(gsrc[c]): gsrc.loc[gsrc[c] < 0, c] = np.nan
            sources['gama'] = (np.asarray(gsrc['X']), np.asarray(gsrc['Y']), gsrc)
        if isinstance(mdf, pd.DataFrame):
            msrc = mdf.copy()
            if noneg:
                for c in msrc.columns:
                    if c not in ('X','Y') and pd.api.types.is_numeric_dtype(msrc[c]): msrc.loc[msrc[c] < 0, c] = np.nan
            sources['mag'] = (np.asarray(msrc['X']), np.asarray(msrc['Y']), msrc)

        out = {'X': xu, 'Y': yu}
        for f in features:
            picked = None; arr = None
            for src in _source_order_for_feature(f):
                if src not in sources: continue
                x, y, df = sources[src]
                col = _find_source_column(df, f)
                if col is None: continue
                picked = (src, col); break
            if picked is None:
                LOGGER.warning("fid=%s feature=%s sem coluna correspondente → NaN", fid, f)
                arr = np.full_like(xu, np.nan, dtype='float32')
            else:
                src, col = picked
                LOGGER.info("fid=%s feature=%s ← %s.%s | algo=%s", fid, f, src, col, algo)
                arr = interp_at(x, y, df[col].to_numpy(), xu, yu, algorithm=algo, extrapolate=True)
            out[f] = arr
        quad[fid][out_name] = pd.DataFrame(out)
    return out_name

# ==== opcional: interp_at do seu 'verde_source'; fallback IDW caso não exista ====
try:
    from verde_source import interp_at as _interp_at_ext
    def interp_at(x, y, z, xi, yi, algorithm='linear', extrapolate=True):
        return _interp_at_ext(x, y, z, xi, yi, algorithm=algorithm, extrapolate=extrapolate)
except Exception:
    # Fallback IDW simples
    def interp_at(x, y, z, xi, yi, algorithm='linear', extrapolate=True):
        x = np.asarray(x, dtype='float64'); y = np.asarray(y, dtype='float64'); z = np.asarray(z, dtype='float64')
        xi = np.asarray(xi, dtype='float64'); yi = np.asarray(yi, dtype='float64')
        out = np.full_like(xi, np.nan, dtype='float64')
        k = int(min(12, len(x)))
        pts = np.c_[x, y]
        q = np.c_[xi, yi]
        for i in range(len(q)):
            d = np.sqrt(((pts - q[i]) ** 2).sum(axis=1))
            if len(d) == 0:
                continue
            idx = np.argpartition(d, kth=max(0, k - 1))[:k]
            dk = d[idx]
            wk = 1.0 / np.maximum(dk, 1e-9)
            zk = z[idx]
            out[i] = np.sum(wk * zk) / np.sum(wk)
        return out.astype('float32')

# ====================== BACKEND: SOM / TABELAS LONGAS ======================
def _build_matrix_for_fids(quad, features, layer, fids=None):
    fids_all = sorted(quad.keys()) if fids is None else list(fids)
    all_blocks, slc, metas = [], {}, {}
    k = 0
    for fid in fids_all:
        blob = quad.get(fid, {})
        if layer not in blob: continue
        df = blob[layer].copy()
        try:
            df, xs_mesh, ys_mesh, nx, ny = _normalize_xy(df)
        except Exception:
            continue
        metas[fid] = {'nx': nx, 'ny': ny, 'xs': xs_mesh, 'ys': ys_mesh}
        X = df[features].to_numpy(dtype='float32')
        if X.size == 0: continue
        all_blocks.append(X)
        slc[fid] = slice(k, k+len(X)); k += len(X)
    if not all_blocks: raise RuntimeError(f"Nenhuma folha com '{layer}' e as features escolhidas.")
    return np.vstack(all_blocks), slc, metas

def _qe(som, X_std):
    D = som.transform(X_std); return float(np.mean(np.min(D, axis=1)))

def _te_1d(som, X_std):
    D = som.transform(X_std)
    bmu = np.argmin(D, axis=1); D2 = D.copy(); D2[np.arange(D.shape[0]), bmu] = np.inf
    sbmu = np.argmin(D2, axis=1); return float(np.mean(np.abs(bmu - sbmu) > 1))

def _predict_per_folha(som, X_std, slc, metas):
    out = {}
    for fid, s in slc.items():
        y = som.predict(X_std[s]); ny, nx = metas[fid]['ny'], metas[fid]['nx']
        out[fid] = y.reshape(ny, nx)
    return out

def _plot_classes(classes_by_fid, metas, n_clusters, flip_ns=False, titulo='Mapa preditivo (SOM)'):
    parent = _ensure_group("Preditor Terra/SOM (rasters)")
    _remove_by_prefix(parent, prefix=f"SOMR_k{n_clusters}_")
    added = 0
    for fid in sorted(classes_by_fid.keys()):
        Z = classes_by_fid[fid]
        if flip_ns:
            Z = np.flipud(Z)
        meta = metas[fid]
        xs_mesh, ys_mesh = meta['xs'], meta['ys']
        try:
            epsg = _grid_epsg_from_blob(quadricula.get(fid, {}))
        except Exception:
            epsg = 4326
        arr2d = (Z.astype('int32') + 1).astype('uint16', copy=False)  # classes 1..k
        out_name = f"SOMR_k{n_clusters}_{fid}"
        out_tif  = _temp_tif(out_name)
        _write_tif_from_grid(arr2d, xs_mesh, ys_mesh, epsg, out_tif, nodata=0, gdal_type=gdal.GDT_UInt16)
        _add_raster_to_group(out_tif, out_name, "Preditor Terra/SOM (rasters)",
                             numeric=False, classes=n_clusters, ramp_name="Set3")
        added += 1
    iface.messageBar().pushSuccess("Preditor Terra", f"[Canvas] {titulo} | {added} raster(s).")

def som_build_long_table(quad, layer, classes_by_fid, metas, atributos, fids=None):
    rows = []; fids_iter = list(classes_by_fid.keys()) if fids is None else list(fids)
    for fid in fids_iter:
        if fid not in classes_by_fid: continue
        Z = classes_by_fid[fid]; blob = quad.get(fid, {})
        if layer not in blob: continue
        df = blob[layer].copy(); df, xs, ys, nx, ny = _normalize_xy(df)
        Zv = Z.ravel(order='C') if Z.shape==(ny,nx) else np.ravel(Z)[:ny*nx]
        cols_keep = [a for a in atributos if a in df.columns]
        sub = pd.DataFrame({'fid': fid, 'E_utm': df['E_utm'].to_numpy(), 'N_utm': df['N_utm'].to_numpy(), 'classe': Zv.astype(int)})
        for a in cols_keep: sub[a] = df[a].to_numpy()
        rows.append(sub)
    if not rows: raise RuntimeError("Sem dados para tabela longa.")
    return pd.concat(rows, axis=0, ignore_index=True)

# ====================== BACKEND: BOXPLOTS ======================
def _pct_clip(a, pmin=None, pmax=None):
    if pmin is None and pmax is None or len(a) == 0:
        return None
    lo = np.nanpercentile(a, pmin) if pmin is not None else None
    hi = np.nanpercentile(a, pmax) if pmax is not None else None
    return (lo, hi)

def boxplots_por_feature(
    df, features, class_col="som_class", classes=None, ncols=3,
    showfliers=False, pclip=(None, None), log=False, titulo=None,
    h_pad=0.6, w_pad=0.6, dpi=140,
):
    if classes is None:
        classes = sorted([c for c in df[class_col].dropna().unique()])
    classes = list(classes)
    feats = [f for f in features if f in df.columns]
    if not feats or not classes:
        raise ValueError("Sem features ou classes válidas para plotar.")
    n = len(feats); ncols = max(1, int(ncols)); nrows = math.ceil(n / ncols)
    fig_h = max(2.4, 0.5 * len(classes)) * nrows
    fig_w = 4.5 * ncols
    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(fig_w, fig_h),
                             squeeze=False, dpi=dpi, layout='constrained')
    for i, feat in enumerate(feats):
        r, c = divmod(i, ncols)
        ax = axes[r][c]
        data = [df.loc[df[class_col] == cl, feat].dropna().values for cl in classes]
        bp = ax.boxplot(data, vert=False, labels=classes,
                        showfliers=showfliers, patch_artist=True, whis=(5, 95))
        for patch in bp['boxes']:
            patch.set_alpha(0.8)
        ax.grid(True, axis='x', linestyle=':', alpha=0.6)
        ax.set_title(feat, fontsize=10, pad=6)
        clip = _pct_clip(np.concatenate([d for d in data if len(d)]), *pclip) if any(len(d) for d in data) else None
        if clip:
            lo, hi = clip
            if lo is not None and hi is not None and np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                ax.set_xlim(lo, hi)
        if log:
            xmin, xmax = ax.get_xlim()
            ax.set_xlim(max(xmin, 1e-12), xmax)
            ax.set_xscale('log')
        ax.tick_params(axis='y', labelsize=9); ax.tick_params(axis='x', labelsize=8)
    for j in range(n, nrows * ncols):
        r, c = divmod(j, ncols); axes[r][c].axis('off')
    if titulo: fig.suptitle(titulo, fontsize=12, y=1.02)
    fig.set_constrained_layout_pads(h_pad=h_pad, w_pad=w_pad, hspace=0.02, wspace=0.02)
    plt.show()
    return fig, axes

# ====================== BACKEND: BDC / STAC (INPE) ======================
BDC_ENDPOINT = "https://data.inpe.br/bdc/stac/v1"

def _require_stac_client():
    if Client is None:
        raise RuntimeError("pystac_client não está disponível no Python do QGIS.")

def _require_rasterio():
    if rasterio is None:
        raise RuntimeError("rasterio não está disponível no Python do QGIS.")

def _aoi_bbox_from_ids(escala, ids):
    """
    Retorna [minx, miny, maxx, maxy] em coordenadas lon/lat (WGS84)
    para o conjunto de folhas informado.

    Assume que a malha já está em graus (ex.: EPSG:4326), como no seu GPKG.
    """
    if not ids:
        return None

    mc = import_malha_cartog(escala=escala, IDs=ids)
    if mc.empty:
        return None

    xs_min, ys_min, xs_max, ys_max = [], [], [], []
    for g in mc["geometry"]:
        if g is None:
            continue
        minx, miny, maxx, maxy = g.bounds
        xs_min.append(minx)
        ys_min.append(miny)
        xs_max.append(maxx)
        ys_max.append(maxy)

    if not xs_min:
        return None

    # W, S, E, N
    return [
        float(min(xs_min)),
        float(min(ys_min)),
        float(max(xs_max)),
        float(max(ys_max)),
    ]

def _bdc_list_collections(pattern=None):
    _require_stac_client()
    cli = Client.open(BDC_ENDPOINT)
    cols = [c.id for c in cli.get_collections()]
    if pattern:
        pat = re.compile(pattern, re.IGNORECASE); cols = [c for c in cols if pat.search(c)]
    return sorted(cols)

def _bdc_search_items(collections, bbox, dt_range, cloud_min, cloud_max, limit, sort_dir):
    _require_stac_client()
    cli = Client.open(BDC_ENDPOINT)
    q = {"eo:cloud_cover": {"gte": int(cloud_min), "lte": int(cloud_max)}}
    sortby = ["properties.datetime"] if sort_dir == "asc" else ["-properties.datetime"]
    search = cli.search(collections=list(collections), bbox=bbox, datetime=dt_range, query=q, sortby=sortby, max_items=int(limit))
    return list(search.items())

def _bdc_pick_visual_asset(item):
    for key in ("tci","visual","overview","thumbnail"):
        a = item.assets.get(key)
        if a and a.href: return a.href, key
    for trip in (("B4","B3","B2"),("red","green","blue")):
        if all(k in item.assets for k in trip): return item.assets[trip[0]].href, trip[0]
    return None

def _open_remote_raster(href):
    _require_rasterio()
    try: return rasterio.open(href)
    except Exception: pass
    if not href.startswith('/vsicurl/'): return rasterio.open('/vsicurl/' + href)
    raise

def _resolve_band_assets(item, bands_text):
    wanted = [b.strip() for b in str(bands_text).split(',') if b.strip()]
    out = []
    assets_ci = {k.lower(): k for k in item.assets.keys()}

    def _pick(*keys):
        for k in keys:
            kk = assets_ci.get(k.lower())
            if kk:
                href = getattr(item.assets[kk], "href", None)
                if href:
                    return kk, href
        return None, None

    for w in wanted:
        lw = w.lower()
        if lw == 'tci':
            k, href = _pick('tci', 'visual')
            if not href:
                has_rgb = (
                    (assets_ci.get('b4') and assets_ci.get('b3') and assets_ci.get('b2')) or
                    (assets_ci.get('b04') and assets_ci.get('b03') and assets_ci.get('b02'))
                )
                if has_rgb:
                    raise RuntimeError("Item sem 'tci'/'visual'. Selecione B4,B3,B2 (ou B04,B03,B02).")
                raise RuntimeError("Item não oferece 'tci'/'visual'.")
            out.append(('tci', href, (1, 2, 3))); continue

        kk = assets_ci.get(lw)
        if kk:
            href = item.assets[kk].href
            out.append((kk, href, (1,))); continue

        if lw in ('red', 'b4', 'b04', 'band4'):
            k, href = _pick('B4', 'B04', 'red')
            if href: out.append(('red', href, (1,))); continue
        if lw in ('green', 'b3', 'b03', 'band3'):
            k, href = _pick('B3', 'B03', 'green')
            if href: out.append(('green', href, (1,))); continue
        if lw in ('blue', 'b2', 'b02', 'band2'):
            k, href = _pick('B2', 'B02', 'blue')
            if href: out.append(('blue', href, (1,))); continue

        m = re.fullmatch(r'b(?:and)?0?(\d+)', lw)
        if m:
            n = int(m.group(1))
            k, href = _pick(f'B{n}', f'B{n:02d}')
            if href: out.append((f'B{n}', href, (1,))); continue

        raise RuntimeError(f"Banda/asset '{w}' não encontrada.")

    return out

def _sample_asset_into_layer(quad, fids, layer_name, href, band_idxs=(1,), prefix='sat'):
    with _open_remote_raster(href) as ds:
        if ds.crs is None: raise RuntimeError("GeoTIFF sem CRS.")
        ok_cols = 0
        for fid in fids:
            blob = quad.get(fid, {})
            df = blob.get(layer_name)
            if not isinstance(df, pd.DataFrame) or not {'X','Y'}.issubset(df.columns): continue
            try: epsg_grid = _grid_epsg_from_blob(blob)
            except Exception as e: print(f" - {fid}: erro EPSG → {e}"); continue
            tr = Transformer.from_crs(f"EPSG:{epsg_grid}", ds.crs, always_xy=True)
            xx, yy = tr.transform(df['X'].to_numpy(), df['Y'].to_numpy())

            def _batched(xa, ya, bs=200000):
                for i in range(0, xa.size, bs): yield xa[i:i+bs], ya[i:i+bs]
            for j, b in enumerate(band_idxs, 1):
                vals = np.full(df.shape[0], np.nan, dtype='float32'); k = 0
                try:
                    for xb, yb in _batched(xx, yy):
                        pts = list(zip(xb, yb))
                        it = ds.sample(pts, indexes=b)  # nearest
                        out = np.fromiter((row[0] for row in it), dtype='float32', count=xb.size)
                        vals[k:k+xb.size] = out; k += xb.size
                except Exception as e:
                    print(f" - {fid}: erro amostrando banda {b} → {e}"); continue
                if len(band_idxs)==3:
                    suffix = ('r','g','b')[j-1] if j<=3 else f'b{j}'
                    col = f"{prefix}_{suffix}"
                elif len(band_idxs)==1:
                    col = f"{prefix}"
                else:
                    col = f"{prefix}_b{b}"
                df[col] = vals.astype('float32', copy=False); ok_cols += 1
        return ok_cols

def _download_assets_for_item(item, bands_text, outdir="satellite_bdc"):
    os.makedirs(outdir, exist_ok=True)
    bands = _resolve_band_assets(item, bands_text)
    assets_local = {}; hrefs = {}
    base_dir = os.path.join(outdir, f"{item.collection_id}_{item.id}")
    os.makedirs(base_dir, exist_ok=True)
    for name, href, _idxs in bands:
        fname = os.path.basename(href.split('?')[0])
        fpath = os.path.join(base_dir, f"{name}_{fname}")
        if not os.path.exists(fpath):
            with requests.get(href, stream=True, timeout=600) as r:
                r.raise_for_status()
                with open(fpath, "wb") as f:
                    for ch in r.iter_content(1<<20):
                        if ch: f.write(ch)
        assets_local[name] = fpath; hrefs[name] = href
    sat_store[item.id] = {
        'collection': item.collection_id,
        'datetime': getattr(item, 'datetime', None),
        'bbox': getattr(item, 'bbox', None) or getattr(item, 'properties', {}).get('bbox'),
        'assets': assets_local, 'hrefs': hrefs
    }
    return assets_local

# ====================== FUNÇÕES OPCIONAIS (EXPORT TIF) ======================
def _transform_from_mesh(xs_mesh, ys_mesh):
    xs1d = np.unique(xs_mesh); ys1d = np.unique(ys_mesh)
    nx, ny = xs1d.size, ys1d.size
    xres = float(np.median(np.diff(xs1d))); yres = float(np.median(np.diff(ys1d)))
    west = xs1d.min() - xres/2; north = ys1d.max() + yres/2
    from rasterio.transform import from_origin
    return from_origin(west, north, xres, yres), nx, ny

def save_classes_tiff(fid, classes2d, xs_mesh, ys_mesh, epsg, outdir="out_som_tiff", cmap_name="Set3"):
    outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    transform, nx, ny = _transform_from_mesh(xs_mesh, ys_mesh)
    profile = dict(driver="GTiff", width=nx, height=ny, count=1,
                   dtype="uint16", transform=transform,
                   crs=None if epsg is None else f"EPSG:{int(epsg)}",
                   compress="lzw", tiled=True, predictor=2)
    path = outdir / f"{fid}_som_classes.tif"
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(classes2d.astype("uint16"), 1)
        try:
            base = matplotlib.colormaps.get_cmap(cmap_name)
            n = int(np.nanmax(classes2d)) + 1
            pal = {i: tuple(int(255*c) for c in (*base(i/max(n-1,1))[:3], 255)) for i in range(n)}
            dst.write_colormap(1, pal)
        except Exception:
            pass
    return str(path)

def save_stack_tiff(fid, df_interp, features, xs_mesh, ys_mesh, epsg, outdir="out_stacks", dtype="float32", nodata=np.nan):
    outdir = pathlib.Path(outdir); outdir.mkdir(parents=True, exist_ok=True)
    transform, nx, ny = _transform_from_mesh(xs_mesh, ys_mesh)
    df_ord = df_interp.sort_values(["N_utm", "E_utm"], ascending=[False, True], kind="mergesort", ignore_index=True)
    stack = np.stack([df_ord[col].to_numpy().reshape(ny, nx) for col in features], axis=0)
    profile = dict(driver="GTiff", width=nx, height=ny, count=len(features),
                   dtype=dtype, transform=transform,
                   crs=None if epsg is None else f"EPSG:{int(epsg)}",
                   compress="lzw", tiled=True, predictor=2, nodata=nodata)
    path = outdir / f"{fid}_stack.tif"
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(stack.astype(dtype))
        for i, name in enumerate(features, 1):
            dst.set_band_description(i, name)
    return str(path)

# ====================== UI (QGIS Dock) ======================
class PreditorTerraDock(QtWidgets.QDockWidget):
    def __init__(self, iface):
        super().__init__("Preditor Terra — Geologia")
        self.iface = iface
        self.setObjectName("PreditorTerraDock")
        self.setAllowedAreas(QtCore.Qt.LeftDockWidgetArea | QtCore.Qt.RightDockWidgetArea)
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        root = QtWidgets.QWidget(self)
        self.setWidget(root)
        layout = QtWidgets.QVBoxLayout(root)

        tabs = QtWidgets.QTabWidget()
        layout.addWidget(tabs)

        # === TAB DADOS ===
        tab_dados = QtWidgets.QWidget(); tabs.addTab(tab_dados, "Dados")
        lay_d = QtWidgets.QVBoxLayout(tab_dados)

        # Seleção malha
        gb_sel = QtWidgets.QGroupBox("Seleção da Malha / Folhas")
        lay_sel = QtWidgets.QGridLayout(gb_sel)
        self.cbEscala = QtWidgets.QComboBox(); self.cbEscala.addItems(ESCALAS); self.cbEscala.setCurrentText('100k')
        self.leFiltro = QtWidgets.QLineEdit(); self.leFiltro.setPlaceholderText("regex ex.: SF23_YA")
        self.btnRefreshIds = QtWidgets.QPushButton("Atualizar lista")
        self.listIds = QtWidgets.QListWidget(); self.listIds.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection); self.listIds.setMinimumHeight(150)
        self.btnSelAll = QtWidgets.QPushButton("Selecionar tudo"); self.btnClear = QtWidgets.QPushButton("Limpar seleção")
        lay_sel.addWidget(QtWidgets.QLabel("Escala"), 0,0); lay_sel.addWidget(self.cbEscala,0,1)
        lay_sel.addWidget(QtWidgets.QLabel("Filtro"), 0,2); lay_sel.addWidget(self.leFiltro,0,3)
        lay_sel.addWidget(self.btnRefreshIds,0,4)
        lay_sel.addWidget(self.listIds,1,0,1,5)
        lay_sel.addWidget(self.btnSelAll,2,3); lay_sel.addWidget(self.btnClear,2,4)
        lay_d.addWidget(gb_sel)

        # Carregar brutos
        gb_raw = QtWidgets.QGroupBox("Dados brutos (aerogeofísica)")
        lay_raw = QtWidgets.QGridLayout(gb_raw)
        self.sbExtend = QtWidgets.QSpinBox(); self.sbExtend.setRange(0, 2000); self.sbExtend.setSingleStep(100); self.sbExtend.setValue(600)
        self.cbGama = QtWidgets.QComboBox()
        self.cbMag  = QtWidgets.QComboBox()
        if _use_postgres_backend():
            self.cbGama.addItems([f"db:{PG_DEFAULT_GAMA_SOURCE}"])
            self.cbMag.addItems(["(sem fonte no banco)"])
        else:
            self.cbGama.addItems(['gama_line_1075','gama_line_1105','gama_line_1089','gama_1039','gama_3022','gama_line_1082'])
            self.cbMag.addItems(['mag_line_1075','mag_line_1105','mag_line_1089','mag_1039','mag_3022','mag_line_1082'])
        self.btnLoad = QtWidgets.QPushButton("Carregar brutos"); self.btnLoad.setStyleSheet("font-weight:600;")
        lay_raw.addWidget(QtWidgets.QLabel("extend_size"),0,0); lay_raw.addWidget(self.sbExtend,0,1)
        lay_raw.addWidget(QtWidgets.QLabel("Gama"),0,2); lay_raw.addWidget(self.cbGama,0,3)
        lay_raw.addWidget(QtWidgets.QLabel("Mag"),0,4); lay_raw.addWidget(self.cbMag,0,5)
        lay_raw.addWidget(self.btnLoad,0,6)
        self.btnQuickFlow = QtWidgets.QPushButton("Fluxo Rápido (DB -> SOM -> Mapa)")
        self.btnQuickFlow.setStyleSheet("font-weight:700;")
        lay_raw.addWidget(self.btnQuickFlow,1,0,1,7)
        lay_d.addWidget(gb_raw)

        # Interpolação
        gb_interp = QtWidgets.QGroupBox("Interpolação para grade (SOM)")
        lay_i = QtWidgets.QGridLayout(gb_interp)
        self.listFeatsGrid = QtWidgets.QListWidget(); self.listFeatsGrid.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        for f in ['GMT','CTCOR','eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO','MDT']:
            self.listFeatsGrid.addItem(f)
        default_feats = {'CTCOR','eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO','MDT'}
        if not _use_postgres_backend():
            default_feats.add('GMT')
        for idx in range(self.listFeatsGrid.count()):
            if self.listFeatsGrid.item(idx).text() in default_feats:
                self.listFeatsGrid.item(idx).setSelected(True)
        self.sbPixel = QtWidgets.QSpinBox(); self.sbPixel.setRange(50, 1000); self.sbPixel.setSingleStep(50); self.sbPixel.setValue(100)
        self.cbAlgo  = QtWidgets.QComboBox(); self.cbAlgo.addItems(['linear','cubic'])
        self.ckNoNegI = QtWidgets.QCheckBox("Negativos → NaN")
        self.btnInterp = QtWidgets.QPushButton("Interpolar grade")
        lay_i.addWidget(QtWidgets.QLabel("Features (grid)"),0,0); lay_i.addWidget(self.listFeatsGrid,1,0,3,2)
        lay_i.addWidget(QtWidgets.QLabel("Pixel (m)"),1,2); lay_i.addWidget(self.sbPixel,1,3)
        lay_i.addWidget(QtWidgets.QLabel("Algoritmo"),2,2); lay_i.addWidget(self.cbAlgo,2,3)
        lay_i.addWidget(self.ckNoNegI,3,2); lay_i.addWidget(self.btnInterp,3,3)
        lay_d.addWidget(gb_interp)

        # Pré-visualização
        gb_prev = QtWidgets.QGroupBox("Pré-visualização (rasters temporários)")
        lay_p = QtWidgets.QGridLayout(gb_prev)
        self.listLayers = QtWidgets.QListWidget(); self.listLayers.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.listCols   = QtWidgets.QListWidget(); self.listCols.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.ckNoNegP   = QtWidgets.QCheckBox("Remover negativos")
        self.btnPreview = QtWidgets.QPushButton("Gerar")
        lay_p.addWidget(QtWidgets.QLabel("Camadas"),0,0); lay_p.addWidget(self.listLayers,1,0,3,1)
        lay_p.addWidget(QtWidgets.QLabel("Colunas"),0,1); lay_p.addWidget(self.listCols,1,1,3,2)
        lay_p.addWidget(self.ckNoNegP,1,3); lay_p.addWidget(self.btnPreview,3,3)
        lay_d.addWidget(gb_prev)

        # === TAB SOM ===
        tab_som = QtWidgets.QWidget(); tabs.addTab(tab_som, "SOM")
        lay_s = QtWidgets.QVBoxLayout(tab_som)

        gb_train = QtWidgets.QGroupBox("Treino")
        lay_t = QtWidgets.QGridLayout(gb_train)
        self.listFeatsSom = QtWidgets.QListWidget(); self.listFeatsSom.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.dsbSigma = QtWidgets.QDoubleSpinBox(); self.dsbSigma.setRange(0.1, 5.0); self.dsbSigma.setSingleStep(0.1); self.dsbSigma.setValue(1.5)
        self.sbIter  = QtWidgets.QSpinBox(); self.sbIter.setRange(500, 30000); self.sbIter.setSingleStep(500); self.sbIter.setValue(10000)
        self.sbSeed  = QtWidgets.QSpinBox(); self.sbSeed.setRange(0, 9999); self.sbSeed.setValue(42)
        self.listKs  = QtWidgets.QListWidget(); self.listKs.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        for k in range(3,31): self.listKs.addItem(str(k))
        for idx in range(self.listKs.count()):
            if self.listKs.item(idx).text() in ('8','12','16'): self.listKs.item(idx).setSelected(True)
        self.btnTrain = QtWidgets.QPushButton("Treinar SOM(s)"); self.labModels = QtWidgets.QLabel("<i>Modelos: —</i>")
        lay_t.addWidget(QtWidgets.QLabel("Features (SOM)"),0,0); lay_t.addWidget(self.listFeatsSom,1,0,4,2)
        lay_t.addWidget(QtWidgets.QLabel("sigma"),1,2); lay_t.addWidget(self.dsbSigma,1,3)
        lay_t.addWidget(QtWidgets.QLabel("max_iter"),2,2); lay_t.addWidget(self.sbIter,2,3)
        lay_t.addWidget(QtWidgets.QLabel("seed"),3,2); lay_t.addWidget(self.sbSeed,3,3)
        lay_t.addWidget(QtWidgets.QLabel("k (classes)"),1,4); lay_t.addWidget(self.listKs,1,5,3,1)
        lay_t.addWidget(self.btnTrain,4,3); lay_t.addWidget(self.labModels,4,4,1,2)
        lay_s.addWidget(gb_train)

        gb_test = QtWidgets.QGroupBox("Aplicação/Teste")
        lay_ap = QtWidgets.QGridLayout(gb_test)
        self.listTestIds = QtWidgets.QListWidget(); self.listTestIds.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.btnSelTest  = QtWidgets.QPushButton("Selecionar todas")
        self.cbKApply = QtWidgets.QComboBox()
        self.ckFlip = QtWidgets.QCheckBox("Flip N-S no plot")
        self.btnApply  = QtWidgets.QPushButton("Aplicar/Testar")
        self.btnEvalAll= QtWidgets.QPushButton("Comparar Ks (QE/TE)")
        self.btnClearModels = QtWidgets.QPushButton("Limpar modelos")
        self.btnBoxplots = QtWidgets.QPushButton("Boxplots por feature")
        lay_ap.addWidget(QtWidgets.QLabel("Folhas (teste)"),0,0); lay_ap.addWidget(self.listTestIds,1,0,4,2)
        lay_ap.addWidget(self.btnSelTest,5,1)
        lay_ap.addWidget(QtWidgets.QLabel("k (aplicar)"),1,2); lay_ap.addWidget(self.cbKApply,1,3)
        lay_ap.addWidget(self.ckFlip,2,2)
        lay_ap.addWidget(self.btnApply,2,3)
        lay_ap.addWidget(self.btnEvalAll,3,3)
        lay_ap.addWidget(self.btnClearModels,4,3)
        lay_ap.addWidget(self.btnBoxplots,5,3)
        lay_s.addWidget(gb_test)

        # === TAB BDC / STAC ===
        tab_bdc = QtWidgets.QWidget(); tabs.addTab(tab_bdc, "Satélite (BDC/INPE)")
        lay_b = QtWidgets.QVBoxLayout(tab_bdc)

        gb_cols = QtWidgets.QGroupBox("Coleções")
        lay_bc = QtWidgets.QGridLayout(gb_cols)
        self.leFilter = QtWidgets.QLineEdit(); self.leFilter.setPlaceholderText("regex (ex.: landsat|sentinel|cbers)")
        self.btnListCols = QtWidgets.QPushButton("Listar")
        self.listColsBDC = QtWidgets.QListWidget(); self.listColsBDC.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection); self.listColsBDC.setMinimumHeight(120)
        lay_bc.addWidget(QtWidgets.QLabel("Filtro"),0,0); lay_bc.addWidget(self.leFilter,0,1)
        lay_bc.addWidget(self.btnListCols,0,2); lay_bc.addWidget(self.listColsBDC,1,0,1,3)
        lay_b.addWidget(gb_cols)

        gb_search = QtWidgets.QGroupBox("Busca STAC")
        lay_bs = QtWidgets.QGridLayout(gb_search)
        self.leDate = QtWidgets.QLineEdit("2018-01-01/2025-12-31")
        self.sbCloudMin = QtWidgets.QSpinBox(); self.sbCloudMin.setRange(0,100); self.sbCloudMin.setValue(0)
        self.sbCloudMax = QtWidgets.QSpinBox(); self.sbCloudMax.setRange(0,100); self.sbCloudMax.setValue(100)
        self.sbLimit = QtWidgets.QSpinBox(); self.sbLimit.setRange(1, 200); self.sbLimit.setValue(20)
        self.cbSort = QtWidgets.QComboBox(); self.cbSort.addItems(['desc','asc'])
        self.btnSearch = QtWidgets.QPushButton("Buscar itens")
        self.btnThumbs = QtWidgets.QPushButton("Thumbnails (rápido)")
        self.btnSaveVisual = QtWidgets.QPushButton("Baixar VISUAL")
        lay_bs.addWidget(QtWidgets.QLabel("Data (UTC)"),0,0); lay_bs.addWidget(self.leDate,0,1)
        lay_bs.addWidget(QtWidgets.QLabel("Nuvens %"),0,2)
        lay_bs.addWidget(self.sbCloudMin,0,3); lay_bs.addWidget(self.sbCloudMax,0,4)
        lay_bs.addWidget(QtWidgets.QLabel("Limite"),0,5); lay_bs.addWidget(self.sbLimit,0,6)
        lay_bs.addWidget(QtWidgets.QLabel("Ordenar"),0,7); lay_bs.addWidget(self.cbSort,0,8)
        lay_bs.addWidget(self.btnSearch,1,1); lay_bs.addWidget(self.btnThumbs,1,2); lay_bs.addWidget(self.btnSaveVisual,1,3)
        lay_b.addWidget(gb_search)

        gb_item = QtWidgets.QGroupBox("Amostragem/Download")
        lay_bi = QtWidgets.QGridLayout(gb_item)
        self.cbItem = QtWidgets.QComboBox(); self.cbItem.setEnabled(False)
        self.leBands = QtWidgets.QLineEdit("tci")
        self.lePrefix = QtWidgets.QLineEdit("sat")
        self.btnSampleItem = QtWidgets.QPushButton("Amostrar item")
        self.btnDlAll = QtWidgets.QPushButton("Baixar itens (todos)")
        self.btnSmAll = QtWidgets.QPushButton("Amostrar itens (todos)")
        lay_bi.addWidget(QtWidgets.QLabel("Item"),0,0); lay_bi.addWidget(self.cbItem,0,1,1,4)
        lay_bi.addWidget(QtWidgets.QLabel("Bandas"),1,0); lay_bi.addWidget(self.leBands,1,1)
        lay_bi.addWidget(QtWidgets.QLabel("Prefixo"),1,2); lay_bi.addWidget(self.lePrefix,1,3)
        lay_bi.addWidget(self.btnSampleItem,1,4)
        lay_bi.addWidget(self.btnDlAll,2,3); lay_bi.addWidget(self.btnSmAll,2,4)
        lay_b.addWidget(gb_item)

        self.log = QtWidgets.QPlainTextEdit(); self.log.setReadOnly(True); self.log.setMaximumBlockCount(2000)
        lay_b.addWidget(self.log)

        # Sinais
        self.btnRefreshIds.clicked.connect(self._refresh_ids)
        self.cbEscala.currentTextChanged.connect(self._refresh_ids)
        self.leFiltro.textChanged.connect(self._refresh_ids)
        self.btnSelAll.clicked.connect(lambda: self._select_all(self.listIds, True))
        self.btnClear.clicked.connect(lambda: self._select_all(self.listIds, False))
        self.btnLoad.clicked.connect(self._on_load)
        self.btnQuickFlow.clicked.connect(self._on_quick_flow)
        self.btnInterp.clicked.connect(self._on_interp)
        self.btnPreview.clicked.connect(self._on_preview)

        self.btnTrain.clicked.connect(self._on_train)
        self.btnSelTest.clicked.connect(lambda: self._select_all(self.listTestIds, True))
        self.btnApply.clicked.connect(self._on_apply)
        self.btnEvalAll.clicked.connect(self._on_evalall)
        self.btnClearModels.clicked.connect(self._on_clear_models)
        self.btnBoxplots.clicked.connect(self._on_boxplots)

        self.btnListCols.clicked.connect(self._on_bdc_list)
        self.btnSearch.clicked.connect(self._on_bdc_search)
        self.btnThumbs.clicked.connect(self._on_bdc_thumbs)
        self.btnSaveVisual.clicked.connect(self._on_bdc_save)
        self.btnSampleItem.clicked.connect(self._on_bdc_sample)
        self.btnDlAll.clicked.connect(self._on_bdc_dl_all)
        self.btnSmAll.clicked.connect(self._on_bdc_sm_all)

        # inicial
        self._refresh_ids()
        self._rescan_from_quadricula_ui()

    # ---------- helpers UI ----------
    def _select_all(self, listw, state=True):
        for i in range(listw.count()):
            listw.item(i).setSelected(state)
    def _selected_texts(self, listw):
        return [i.text() for i in listw.selectedItems()]
    def _set_list(self, listw, items, autoselect_all=False):
        listw.clear()
        for it in items: listw.addItem(str(it))
        if autoselect_all and items: self._select_all(listw, True)

    def _rescan_from_quadricula_ui(self):
        q = globals().get('quadricula', {})
        layers = _scan_layers_from_quadricula(q)
        self._set_list(self.listLayers, layers)
        global data_grid
        if data_grid and data_grid in layers:
            for i in range(self.listLayers.count()):
                self.listLayers.item(i).setSelected(self.listLayers.item(i).text()==data_grid)
        cols = _available_columns(q, self._selected_texts(self.listLayers)) or ('MDT',)
        self._set_list(self.listCols, cols)
        # SOM features
        numeric = []
        for _, blob in q.items():
            for lay in self._selected_texts(self.listLayers):
                df = blob.get(lay)
                if isinstance(df, pd.DataFrame):
                    for c in cols:
                        if c in df.columns and pd.api.types.is_numeric_dtype(df[c]): numeric.append(c)
        opts = sorted(set(numeric), key=lambda c: (c!='MDT', c)) or ['MDT']
        self._set_list(self.listFeatsSom, opts)
        # folhas com layer de grade
        test_opts = []
        if data_grid:
            for fid, blob in q.items():
                if data_grid in blob and isinstance(blob[data_grid], pd.DataFrame):
                    test_opts.append(fid)
        self._set_list(self.listTestIds, sorted(test_opts))
        # modelos
        ks = sorted(list(som_store.keys()))
        self.cbKApply.clear()
        for k in ks: self.cbKApply.addItem(str(k))
        self.labModels.setText("<b>Modelos:</b> "+(", ".join(map(str, ks)) if ks else "<i>—</i>"))

    # ---------- ações ----------
    def _refresh_ids(self):
        try:
            ids = _ids_from_mc(self.cbEscala.currentText(), self.leFiltro.text().strip() or None)
        except Exception as e:
            _log(self.log, f"Erro ao ler malha: {e}")
            return
        self._set_list(self.listIds, ids)

    def _on_load(self):
        try:
            _info(self.log, "# Montando grade…")
            ids = self._selected_texts(self.listIds)
            if not ids: _warn(self.log, "Selecione ao menos 1 folha."); return
            with timed_step(f"Build_mc escala={self.cbEscala.currentText()} ids={len(ids)}"):
                quad = Build_mc(escala=self.cbEscala.currentText(), ID=list(ids), verbose=False)

            _info(self.log, "# Carregando dados brutos…")
            _info(self.log, f"Backend={DATA_BACKEND} | gama={self.cbGama.currentText()} | mag={self.cbMag.currentText()}")
            with timed_step(f"Upload_geof gama={self.cbGama.currentText()} mag={self.cbMag.currentText()} extend={int(self.sbExtend.value())}"):
                _g, _m = Upload_geof(quad, gama_xyz=self.cbGama.currentText(), mag_xyz=self.cbMag.currentText(), extend_size=int(self.sbExtend.value()))

            quad = pop_nodata(quad); globals()['quadricula'] = quad
            _info(self.log, f"Folhas ativas: {len(quad)} | pontos_gama={len(_g)} | pontos_mag={len(_m)}")
            globals()['data_grid'] = None; som_store.clear(); globals()['som_last_pred']=None
            self._rescan_from_quadricula_ui()
            _info(self.log, "Pronto. Agora execute a INTERPOLAÇÃO.")
        except Exception as e:
            _err(self.log, f"[ERRO _on_load] {e}")

    def _on_quick_flow(self):
        """
        Fluxo 1-clique: malha -> pontos DB por interseção -> interpolação -> treino SOM -> mapa preditivo.
        """
        try:
            ids = self._selected_texts(self.listIds)
            if not ids:
                _warn(self.log, "Selecione ao menos 1 folha.")
                return

            feats_grid = self._selected_texts(self.listFeatsGrid)
            if not feats_grid:
                _warn(self.log, "Selecione ao menos 1 feature para interpolação.")
                return

            ks_sel = [int(i.text()) for i in self.listKs.selectedItems()]
            k = sorted(set(ks_sel or [8]))[0]
            sigma = float(self.dsbSigma.value())
            n_iter = int(self.sbIter.value())
            pix = int(self.sbPixel.value())
            algo = self.cbAlgo.currentText()
            noneg = self.ckNoNegI.isChecked()

            _info(self.log, "# Fluxo rápido iniciado (DB -> SOM -> Mapa)...")
            _info(self.log, f"Folhas={len(ids)} | k={k} | pixel={pix} | algo={algo}")

            with timed_step("Fluxo rápido completo"):
                quad = Build_mc(escala=self.cbEscala.currentText(), ID=list(ids), verbose=False)
                _g, _m = Upload_geof(
                    quad,
                    gama_xyz=self.cbGama.currentText(),
                    mag_xyz=self.cbMag.currentText(),
                    extend_size=int(self.sbExtend.value()),
                )
                quad = pop_nodata(quad)
                if not quad:
                    raise RuntimeError("Nenhuma folha com pontos geofísicos válidos após interseção no banco.")

                ids_ok = [fid for fid in ids if fid in quad]
                if not ids_ok:
                    raise RuntimeError("Nenhuma das folhas selecionadas recebeu pontos do banco.")

                out_layer = _interpolate_current_selection(
                    quad, ids_ok,
                    self.cbGama.currentText(), self.cbMag.currentText(),
                    feats_grid, pix, algo, noneg
                )

                feats_som = self._selected_texts(self.listFeatsSom) or list(feats_grid)
                feats_som = [f for f in feats_som if any(
                    isinstance(quad.get(fid, {}).get(out_layer), pd.DataFrame) and f in quad[fid][out_layer].columns
                    for fid in ids_ok
                )]
                if not feats_som:
                    raise RuntimeError("Sem features SOM válidas na grade interpolada.")

                X_all, _, _ = _build_matrix_for_fids(quad, feats_som, out_layer, fids=ids_ok)
                valid_cols = np.isfinite(X_all).any(axis=0)
                if not valid_cols.any():
                    raise RuntimeError("Todas as features selecionadas ficaram sem dados válidos (NaN).")
                if not np.all(valid_cols):
                    dropped = [feats_som[i] for i, ok in enumerate(valid_cols) if not ok]
                    feats_som = [feats_som[i] for i, ok in enumerate(valid_cols) if ok]
                    X_all = X_all[:, valid_cols]
                    _warn(self.log, f"Features removidas por NaN total: {dropped}")

                imp = SimpleImputer(strategy='median')
                X_imp = imp.fit_transform(X_all)
                sca = StandardScaler().fit(X_imp)
                X_std = sca.transform(X_imp)
                np.random.seed(int(self.sbSeed.value()))
                som = SOM(m=k, n=1, sigma=sigma, dim=len(feats_som), max_iter=n_iter)
                som.fit(X_std)

                X_te, slc_te, metas_te = _build_matrix_for_fids(quad, feats_som, out_layer, fids=ids_ok)
                X_te_std = sca.transform(imp.transform(X_te))
                qe = _qe(som, X_te_std)
                te = _te_1d(som, X_te_std)
                classes = _predict_per_folha(som, X_te_std, slc_te, metas_te)
                _plot_classes(classes, metas_te, n_clusters=k, flip_ns=self.ckFlip.isChecked(),
                              titulo=f"Mapa preditivo (SOM) k={k} | {out_layer}")

                som_store.clear()
                som_store[k] = {'som': som, 'imp': imp, 'sca': sca, 'feats': feats_som, 'layer': out_layer}
                globals()['quadricula'] = quad
                globals()['data_grid'] = out_layer
                globals()['som_last_pred'] = {
                    'k': k, 'classes': classes, 'metas': metas_te,
                    'fids': tuple(ids_ok), 'feats': tuple(feats_som), 'layer': out_layer
                }

            self._rescan_from_quadricula_ui()
            _info(self.log, f"Fluxo concluído | folhas={len(ids_ok)} | pontos_gama={len(_g)} | QE={qe:.6g} | TE={te:.6g}")
            _info(self.log, "Mapa preditivo adicionado ao grupo: Preditor Terra/SOM (rasters).")
        except Exception as e:
            _err(self.log, f"[ERRO fluxo rápido] {e}")

    def _on_interp(self):
        try:
            ids = self._selected_texts(self.listIds)
            if not ids: _warn(self.log, "Selecione ao menos 1 folha."); return
            feats_grid = self._selected_texts(self.listFeatsGrid)
            if not feats_grid: _warn(self.log, "Selecione ao menos 1 feature (grid)."); return
            q = globals().get('quadricula', {})
            if not q: _warn(self.log, "Carregue dados brutos primeiro."); return

            algo = self.cbAlgo.currentText(); pix = int(self.sbPixel.value()); noneg=self.ckNoNegI.isChecked()
            _info(self.log, f"# Interpolando (algo={algo}, pixel={pix} m, noneg={noneg})…")
            with timed_step(f"Interpolate ids={len(ids)} feats={len(feats_grid)}"):
                out_layer = _interpolate_current_selection(q, ids, self.cbGama.currentText(), self.cbMag.currentText(), feats_grid, pix, algo, noneg)
            globals()['quadricula'] = q; globals()['data_grid'] = out_layer
            som_store.clear(); globals()['som_last_pred']=None
            _info(self.log, f"→ Camada criada: {out_layer}")
            self._rescan_from_quadricula_ui()
        except Exception as e:
            _err(self.log, f"[ERRO _on_interp] {e}")

    def _on_preview(self):
        ids = self._selected_texts(self.listIds)
        layers = self._selected_texts(self.listLayers)
        cols = self._selected_texts(self.listCols)
        if not ids: _log(self.log, "Selecione folhas (esquerda)."); return
        if not layers: _log(self.log, "Selecione camadas."); return
        q = globals().get('quadricula', {})
        for col in cols:
            _plot_layers_for_column(q, ids, layers, col, remove_neg=self.ckNoNegP.isChecked())

    def _on_train(self):
        feats = self._selected_texts(self.listFeatsSom)
        if not feats: _log(self.log,"Selecione ao menos 1 feature (SOM)."); return
        if not globals().get('data_grid'): _log(self.log,"Interpole a grade primeiro."); return
        layer = globals()['data_grid']; q = globals().get('quadricula', {})
        _log(self.log, f"[TREINO] Montando matriz global de '{layer}'…")
        try:
            X_all, _, _ = _build_matrix_for_fids(q, feats, layer, fids=None)
        except Exception as e:
            _log(self.log, f"Erro montando matriz: {e}"); return
        valid_cols = np.isfinite(X_all).any(axis=0)
        if not valid_cols.any():
            _log(self.log, "Sem dados válidos nas features selecionadas (todas NaN).")
            return
        if not np.all(valid_cols):
            dropped = [feats[i] for i, ok in enumerate(valid_cols) if not ok]
            feats = [feats[i] for i, ok in enumerate(valid_cols) if ok]
            X_all = X_all[:, valid_cols]
            _log(self.log, f"[TREINO] Features removidas por falta de dados: {dropped}")
        imp = SimpleImputer(strategy='median'); X_imp = imp.fit_transform(X_all)
        sca = StandardScaler().fit(X_imp); X_std = sca.transform(X_imp)
        ks = [int(i.text()) for i in self.listKs.selectedItems()]
        if not ks: _log(self.log,"Escolha ao menos um k."); return
        np.random.seed(int(self.sbSeed.value()))
        for k in sorted(set(ks)):
            _log(self.log, f" - SOM(k={k}, sigma={float(self.dsbSigma.value())}, it={int(self.sbIter.value())})")
            som = SOM(m=int(k), n=1, sigma=float(self.dsbSigma.value()), dim=len(feats), max_iter=int(self.sbIter.value())); som.fit(X_std)
            som_store[k] = {'som': som, 'imp': imp, 'sca': sca, 'feats': feats, 'layer': layer}
        self._rescan_from_quadricula_ui()
        _log(self.log, "Modelos treinados.")

    def _on_apply(self):
        if not som_store: _log(self.log,"Treine um SOM antes."); return
        ids = self._selected_texts(self.listTestIds)
        if not ids: _log(self.log,"Selecione folhas para teste."); return
        ktxt = self.cbKApply.currentText()
        if not ktxt: _log(self.log,"Escolha k para aplicar."); return
        k = int(ktxt); model = som_store.get(k)
        if model is None: _log(self.log, f"k={k} não encontrado."); return
        feats = model['feats']; layer = model['layer']; q = globals().get('quadricula', {})
        _log(self.log, f"[TESTE] {len(ids)} folhas / layer '{layer}'…")
        try:
            X_te, slc_te, metas_te = _build_matrix_for_fids(q, feats, layer, fids=ids)
        except RuntimeError as e:
            _log(self.log, str(e)); return
        X_te_std = model['sca'].transform(model['imp'].transform(X_te))
        qe = _qe(model['som'], X_te_std); te = _te_1d(model['som'], X_te_std)
        _log(self.log, f"k={k} | QE_test={qe:.6g} | TE_test={te:.6g}")
        classes = _predict_per_folha(model['som'], X_te_std, slc_te, metas_te)
        _plot_classes(classes, metas_te, n_clusters=k, flip_ns=self.ckFlip.isChecked(),
                      titulo=f"SOM (aplicar) k={k} | sigma={float(self.dsbSigma.value())} | it={int(self.sbIter.value())} | {layer}")
        globals()['som_last_pred'] = {'k':k, 'classes':classes, 'metas':metas_te, 'fids':tuple(ids), 'feats':tuple(feats), 'layer':layer}
        _log(self.log, "Predição salva: som_last_pred.")

    def _on_evalall(self):
        if not som_store or not self._selected_texts(self.listTestIds):
            _log(self.log,"Treine/aplique SOM e selecione folhas."); return
        any_k = next(iter(som_store))
        feats = som_store[any_k]['feats']; layer = som_store[any_k]['layer']
        q = globals().get('quadricula', {})
        try:
            X_te, slc_te, metas_te = _build_matrix_for_fids(q, feats, layer, fids=self._selected_texts(self.listTestIds))
        except RuntimeError as e:
            _log(self.log, str(e)); return
        rows=[]
        for k, model in sorted(som_store.items()):
            if model['feats']!=feats or model['layer']!=layer:
                rows.append({'k':k,'QE':np.nan,'TE':np.nan,'obs':'incompatível'})
                continue
            X_te_std = model['sca'].transform(model['imp'].transform(X_te))
            rows.append({'k':k,'QE':_qe(model['som'],X_te_std),'TE':_te_1d(model['som'],X_te_std)})
        dfm = pd.DataFrame(rows).sort_values('QE', ascending=True, na_position='last')
        _log(self.log, dfm.to_string(index=False))

    def _on_clear_models(self):
        som_store.clear(); globals()['som_last_pred']=None
        self._rescan_from_quadricula_ui()
        _log(self.log,"Modelos apagados.")

    def _on_boxplots(self):
        if not som_store or globals().get('som_last_pred') is None:
            _log(self.log,"Treine e aplique um SOM antes."); return
        lp = globals()['som_last_pred']
        k=lp['k']; classes=lp['classes']; metas=lp['metas']; fids=lp['fids']; feats=list(lp['feats']); layer=lp['layer']
        q = globals().get('quadricula', {})
        try:
            df_long = som_build_long_table(q, layer, classes, metas, atributos=feats, fids=fids)
        except RuntimeError as e:
            _log(self.log, str(e)); return
        dfw = df_long.rename(columns={'classe':'som_class'})
        _log(self.log, f"[Boxplots] {len(fids)} folha(s) | k={k} | layer='{layer}' | attrs={feats}")
        boxplots_por_feature(
            df=dfw, features=feats, class_col='som_class',
            classes=sorted(dfw['som_class'].unique()),
            ncols=3, showfliers=False, pclip=(5,95), log=False,
            titulo='Boxplots por feature • escalas independentes (valores no eixo X)'
        )

    # ----- BDC -----
    def _on_bdc_list(self):
        try:
            cols = _bdc_list_collections(self.leFilter.text().strip() or None)
            self._set_list(self.listColsBDC, cols)
            _log(self.log, f"{len(cols)} coleção(ões) listadas.")
        except Exception as e:
            _log(self.log, f"Erro ao listar coleções: {e}")

    def _on_bdc_search(self):
        cols = self._selected_texts(self.listColsBDC)
        if not cols: _log(self.log,"Selecione coleções."); return
        bbox = _aoi_bbox_from_ids(self.cbEscala.currentText(), self._selected_texts(self.listIds))
        if not bbox: _log(self.log,"Selecione folhas para definir a AOI."); return
        _log(self.log, f"AOI bbox (WGS84): {bbox}")
        try:
            items = _bdc_search_items(
                collections=cols, bbox=bbox, dt_range=self.leDate.text().strip(),
                cloud_min=int(self.sbCloudMin.value()), cloud_max=int(self.sbCloudMax.value()),
                limit=int(self.sbLimit.value()), sort_dir=self.cbSort.currentText()
            )
        except Exception as e:
            _log(self.log, f"Erro busca STAC: {e}"); return
        globals()['bdc_items'] = items
        labels = []
        for i,it in enumerate(items):
            coll = getattr(it,"collection_id","") or ""
            dt   = getattr(it,"datetime",None)
            dts  = (dt.date().isoformat() if hasattr(dt,"date") else str(dt)) if dt else "—"
            props = getattr(it,"properties",{}) or {}
            cc = props.get("eo:cloud_cover") or props.get("cloud_cover")
            cc_str = (f"{cc:.0f}%" if isinstance(cc,(int,float)) else "—")
            labels.append(f"{i:02d} | {coll} | {dts} | clouds {cc_str}")
        self.cbItem.clear()
        self.cbItem.addItems(labels)
        self.cbItem.setEnabled(bool(items))
        _log(self.log, f"Encontrados {len(items)} item(ns).")

    def _on_bdc_thumbs(self):
        items = globals().get('bdc_items', [])
        if not items: _log(self.log,"Faça a busca primeiro."); return
        max_show=12
        _log(self.log, "Thumbnails (nomes):")
        for i,it in enumerate(items[:max_show]):
            _log(self.log, f"  - {i:02d} {it.collection_id} {getattr(it,'datetime',None)}")

    def _on_bdc_save(self):
        items = globals().get('bdc_items', [])
        if not items: _log(self.log,"Faça a busca primeiro."); return
        saved=0
        for it in items:
            pair = _bdc_pick_visual_asset(it)
            if not pair: continue
            href, key = pair
            name = os.path.basename(href.split('?')[0])
            fpath = os.path.join("satellite_bdc", f"{it.collection_id}_{it.id}_{key}_{name}")
            try:
                os.makedirs("satellite_bdc", exist_ok=True)
                if not os.path.exists(fpath):
                    with requests.get(href, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        with open(fpath,"wb") as f:
                            for ch in r.iter_content(1<<20):
                                if ch: f.write(ch)
                saved += 1
            except Exception as e:
                _log(self.log, f"[WARN] Falha {href}: {e}")
        _log(self.log, f"Arquivos VISUAL salvos: {saved}")

    def _on_bdc_sample(self):
        items = globals().get('bdc_items', [])
        if not items: _log(self.log,"Busque itens primeiro."); return
        idx = self.cbItem.currentIndex()
        if not (0 <= idx < len(items)): _log(self.log, "Índice inválido."); return
        if not globals().get('data_grid'): _log(self.log,"Interpole a grade (crie a camada SOM)."); return
        layer = globals()['data_grid']; q = globals().get('quadricula', {})
        fids_target = [fid for fid,blob in q.items() if layer in blob]
        item = items[idx]
        try:
            bands = _resolve_band_assets(item, self.leBands.text())
        except Exception as e:
            _log(self.log, f"Bandas: {e}"); return
        _log(self.log, f"Amostrando {[b[0] for b in bands]} → '{layer}' em {len(fids_target)} folha(s)…")
        total_cols=0
        for name, href, idxs in bands:
            try:
                cols = _sample_asset_into_layer(q, fids_target, layer_name=layer, href=href, band_idxs=tuple(idxs), prefix=(self.lePrefix.text() or name))
                total_cols += cols; _log(self.log, f"  - OK {name}: {cols} coluna(s).")
            except Exception as e:
                _log(self.log, f"  - {name}: erro → {e}")
        if total_cols==0: _log(self.log,"Nenhuma coluna criada (verifique EPSG/GeoTIFF).")
        else:
            globals()['quadricula']=q; self._rescan_from_quadricula_ui(); _log(self.log,"Novas colunas disponíveis no SOM.")

    def _on_bdc_dl_all(self):
        items = globals().get('bdc_items', [])
        if not items: _log(self.log,"Busque itens primeiro."); return
        bands_text = self.leBands.text()
        _log(self.log, f"Baixando {len(items)} item(ns) ({bands_text})…")
        ok=0
        for it in items:
            try:
                local = _download_assets_for_item(it, bands_text, outdir="satellite_bdc")
                _log(self.log, f" - {it.id}: {list(local.keys())}")
                ok += 1
            except Exception as e:
                _log(self.log, f" - {it.id}: erro → {e}")
        _log(self.log, f"Concluído. {ok}/{len(items)} item(ns) no cache (sat_store).")

    def _on_bdc_sm_all(self):
        items = globals().get('bdc_items', [])
        if not items: _log(self.log,"Busque itens primeiro."); return
        if not globals().get('data_grid'): _log(self.log,"Interpole a grade (crie a camada SOM)."); return
        layer = globals()['data_grid']; q = globals().get('quadricula', {})
        fids_target = [fid for fid,blob in q.items() if layer in blob]
        bands_text = self.leBands.text()
        _log(self.log, f"Amostrar TODOS os itens ({len(items)}) bandas={bands_text} → layer '{layer}' …")
        total_cols = 0; it_done = 0
        for it in items:
            try:
                bands = _resolve_band_assets(it, bands_text)
                for name, href, idxs in bands:
                    cols = _sample_asset_into_layer(q, fids_target, layer_name=layer, href=href, band_idxs=tuple(idxs), prefix=(self.lePrefix.text() or name))
                    total_cols += cols
                it_done += 1
            except Exception as e:
                _log(self.log, f" - {it.id}: erro → {e}")
        if total_cols==0: _log(self.log,"Nenhuma coluna criada (verifique EPSG/GeoTIFF).")
        else:
            globals()['quadricula']=q; self._rescan_from_quadricula_ui()
            _log(self.log, f"OK. {it_done}/{len(items)} itens amostrados; {total_cols} coluna(s) adicionada(s).")

# ====================== BOOTSTRAP DOCK ======================
def close_preditor_terra_dock(qgis_iface=None):
    if qgis_iface is None:
        qgis_iface = iface
    if qgis_iface is None:
        return
    for d in qgis_iface.mainWindow().findChildren(QtWidgets.QDockWidget):
        if d.objectName() == "PreditorTerraDock":
            d.close()
            qgis_iface.mainWindow().removeDockWidget(d)
            d.deleteLater()


def open_preditor_terra_dock(qgis_iface=None):
    if qgis_iface is None:
        qgis_iface = iface
    if qgis_iface is None:
        raise RuntimeError("QGIS iface indisponível para abrir o dock.")
    close_preditor_terra_dock(qgis_iface)
    dock = PreditorTerraDock(qgis_iface)
    qgis_iface.addDockWidget(QtCore.Qt.RightDockWidgetArea, dock)
    dock.show()
    return dock


# Compat com versões anteriores.
def _open_preditor_terra_dock():
    return open_preditor_terra_dock(iface)


# Execução direta via QGIS --code / console.
if __name__ in {"__main__", "__console__", "builtins"}:
    open_preditor_terra_dock(iface)

# -*- coding: utf-8 -*-
"""
PreditorTerra · Interpolar + GeoTIFF (Lite, GDAL)
- Sem rasterio (usa osgeo.gdal)
- Importa 'src' mesmo se seaborn não estiver instalado (stub)
- interp_at: tenta 'verde_source'; se não houver, faz fallback IDW puro NumPy
- Exporta GeoTIFF multibanda por folha e adiciona no QGIS

Requisitos do seu projeto:
  - src.py com: Build_mc, Upload_geof, pop_nodata, sintetic_grid
  - (opcional) verde_source.py com: interp_at
"""

import os, re, json, types, importlib
import numpy as np

from qgis.core import (
    QgsProcessing, QgsProcessingAlgorithm, QgsProcessingProvider,
    QgsProcessingParameterEnum, QgsProcessingParameterString,
    QgsProcessingParameterNumber, QgsProcessingParameterBoolean,
    QgsProcessingParameterFolderDestination, QgsProcessingOutputString,
    QgsProject, QgsRasterLayer, QgsApplication
)

# GDAL (vem com QGIS)
from osgeo import gdal, osr

ESCALAS = ['25k','50k','100k','250k','1kk']

# ---------- importes robustos ----------
def _soft_import_src(feedback=None):
    """Importa 'src' e injeta um stub de seaborn se necessário."""
    try:
        return importlib.import_module('src')
    except ModuleNotFoundError as e:
        if 'seaborn' in str(e).lower():
            import sys
            sns = types.ModuleType('seaborn')
            def _noop(*a, **k): return None
            for name in ('set_theme','despine','heatmap','pairplot','jointplot',
                         'kdeplot','histplot','scatterplot','lineplot','color_palette'):
                setattr(sns, name, _noop)
            sys.modules['seaborn'] = sns
            if feedback: feedback.pushInfo("[Lite] Stub de 'seaborn' injetado para importar 'src'.")
            return importlib.import_module('src')
        raise

def _get_interp_at(feedback=None):
    """Tenta verde_source.interp_at; se falhar, usa IDW puro (sem SciPy)."""
    try:
        return importlib.import_module('verde_source').interp_at
    except Exception:
        if feedback: feedback.pushInfo("[Lite] 'verde_source.interp_at' não encontrado; usando fallback IDW.")
        def _interp_at(x, y, z, xu, yu, algorithm='linear', extrapolate=True, power=2.0, eps=1e-12, chunk=20000):
            # IDW simples, em chunks para não estourar memória
            x = np.asarray(x, float); y = np.asarray(y, float); z = np.asarray(z, float)
            xu = np.asarray(xu, float); yu = np.asarray(yu, float)
            out = np.empty_like(xu, dtype=float)
            n = xu.size
            for i0 in range(0, n, chunk):
                i1 = min(i0+chunk, n)
                dx = x[None, :] - xu[i0:i1, None]
                dy = y[None, :] - yu[i0:i1, None]
                d2 = dx*dx + dy*dy
                # evita divisão por zero
                w = 1.0 / np.power(np.maximum(d2, eps), power/2.0)
                # se houver pontos exatamente coincidentes, usa o valor do ponto
                mask0 = d2 <= eps
                if mask0.any():
                    # pega primeiro coincidente
                    rows, cols = np.where(mask0)
                    vals = np.zeros(rows.size, float)
                    # para cada target com coincidência, usa z do primeiro col
                    last_row = -1
                    for r, c in zip(rows, cols):
                        if r != last_row:
                            vals[rows==r] = z[c]
                            last_row = r
                    out[i0:i1] = np.where(mask0.any(axis=1), vals, (w @ z) / np.clip(w.sum(axis=1), eps, None))
                else:
                    out[i0:i1] = (w @ z) / np.clip(w.sum(axis=1), eps, None)
            return out
        return _interp_at

# ---------- helpers ----------
def _infer_suffix_from_names(*names):
    for nm in names or []:
        m = re.search(r'(\d{4})', str(nm or ''))
        if m: return m.group(1)
    return '0000'

def _norm(s): return re.sub(r'[^a-z0-9]+','', str(s).lower())

SYN = {
    'gmt': {'gmt','magigrf','magr','igrf','mag','gmtigrf','magig rf','magigrf'},
    'mdt': {'mdt','alte','altura'},
    'ctcor': {'ctcor','ctc','ct'},
    'eth': {'eth','eth_ppm','thc','th_ppm','ethppm','th'},
    'eu': {'eu','uc','u','euppm','u_ppm'},
    'kperc': {'kperc','kc','k','kpct','k_percent'},
    'uthrazao': {'uthrazao','uratio','u_th','u/th','u_th_ratio'},
    'ukrazao': {'ukrazao','u_k','u/k','u_k_ratio'},
    'thkrazao': {'thkrazao','th_k','th/k','th_k_ratio'},
}
def _find_col(df, target):
    want = _norm(target)
    for c in df.columns:
        if _norm(c) == want: return c
    for s in SYN.get(want, set()):
        for c in df.columns:
            if _norm(c) == s: return c
    return None

def _scan_numeric_cols(df):
    import pandas as pd
    ignore = {'E_utm','N_utm','X','Y'}
    return [c for c in df.columns if c not in ignore and pd.api.types.is_numeric_dtype(df[c])]

# ---------- export GeoTIFF (GDAL) ----------
def _export_geotiff_stack_gdal(df, out_tif, epsg=32723):
    """
    df: DataFrame com 'X'/'Y' ou 'E_utm'/'N_utm' + colunas numéricas (bandas)
    """
    import pandas as pd
    if {'E_utm','N_utm'}.issubset(df.columns):
        pass
    elif {'X','Y'}.issubset(df.columns):
        df = df.rename(columns={'X':'E_utm','Y':'N_utm'})
    else:
        raise ValueError("Camada sem colunas 'X','Y' ou 'E_utm','N_utm'.")

    # Ordena para formar grade regular (N decrescente, E crescente)
    df = df.sort_values(['N_utm','E_utm'], ascending=[False, True], ignore_index=True)
    xs = np.sort(df['E_utm'].unique())
    ys = np.sort(df['N_utm'].unique())
    nx, ny = xs.size, ys.size
    if nx <= 1 or ny <= 1:
        raise ValueError("Não foi possível inferir resolução (nx<=1 ou ny<=1).")

    px = float(np.diff(xs).min())
    py = float(np.diff(ys).min())

    # GeoTransform: origem no canto superior esquerdo
    originX = xs.min()
    originY = ys.max()
    geotransform = (originX, px, 0.0, originY, 0.0, -py)

    bands = _scan_numeric_cols(df)
    if not bands:
        raise ValueError("Nenhuma coluna numérica para exportar.")

    os.makedirs(os.path.dirname(out_tif), exist_ok=True)
    driver = gdal.GetDriverByName('GTiff')
    dst = driver.Create(out_tif, nx, ny, len(bands), gdal.GDT_Float32, options=['COMPRESS=DEFLATE', 'TILED=YES'])
    dst.SetGeoTransform(geotransform)

    # Projeção
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(int(epsg))
    dst.SetProjection(srs.ExportToWkt())

    # Escreve bandas (reshape (ny, nx))
    for i, col in enumerate(bands, start=1):
        arr = df[col].to_numpy(dtype=np.float32).reshape(ny, nx)
        band = dst.GetRasterBand(i)
        band.WriteArray(arr)
        band.SetDescription(col)
        band.FlushCache()

    dst.FlushCache()
    dst = None
    return out_tif, bands, epsg

# ---------- algoritmo Processing ----------
class PreditorTerraLiteGDAL(QgsProcessingAlgorithm):
    P_ESCALA='ESCALA'; P_FIDS='FIDS'; P_GAMA='GAMA'; P_MAG='MAG'
    P_EXT='EXTEND'; P_FEATS='FEATS'; P_PSIZE='PSIZE'; P_ALGO='ALGO'
    P_NONEG='NONEG'; P_EPSG='EPSG'; P_OUTDIR='OUTDIR'
    O_LAYER='LAYER_NAME'; O_TIFS='TIFS_JSON'

    def name(self): return 'preditor_terra_lite_gdal'
    def displayName(self): return 'Interpolar + GeoTIFF (Lite, GDAL)'
    def group(self): return 'PreditorTerra'
    def groupId(self): return 'preditor_terra'
    def shortHelpString(self):
        return ("Carrega gama/mag, interpola grade por folha e exporta GeoTIFF multibanda usando GDAL "
                "(sem rasterio). Usa fallback IDW se não houver 'verde_source.interp_at'.")

    def initAlgorithm(self, config=None):
        self.addParameter(QgsProcessingParameterEnum(
            self.P_ESCALA, 'Escala', options=ESCALAS, defaultValue=ESCALAS.index('100k')))
        self.addParameter(QgsProcessingParameterString(
            self.P_FIDS, 'Folhas (IDs separados por ;)', defaultValue='SF23_ZA_II3_SW'))
        self.addParameter(QgsProcessingParameterEnum(
            self.P_GAMA, 'Camada Gama', options=['gama_line_1105','gama_line_1089','gama_1039','gama_3022'], defaultValue=0))
        self.addParameter(QgsProcessingParameterEnum(
            self.P_MAG, 'Camada Mag', options=['mag_line_1105','mag_line_1089','mag_1039','mag_3022'], defaultValue=0))
        self.addParameter(QgsProcessingParameterNumber(
            self.P_EXT, 'extend_size (m)', type=QgsProcessingParameterNumber.Integer, defaultValue=600, minValue=0))
        self.addParameter(QgsProcessingParameterString(
            self.P_FEATS, 'Features p/ grade (CSV)', defaultValue='GMT,CTCOR,eTh,eU,KPERC,MDT'))
        self.addParameter(QgsProcessingParameterNumber(
            self.P_PSIZE, 'Pixel (m)', type=QgsProcessingParameterNumber.Integer, defaultValue=200, minValue=10))
        self.addParameter(QgsProcessingParameterEnum(
            self.P_ALGO, 'Algoritmo', options=['linear','cubic','nearest','idw'], defaultValue=0))
        self.addParameter(QgsProcessingParameterBoolean(
            self.P_NONEG, 'Negativos → NaN (grade)', defaultValue=False))
        self.addParameter(QgsProcessingParameterNumber(
            self.P_EPSG, 'Forçar EPSG (opcional)', type=QgsProcessingParameterNumber.Integer, optional=True))
        self.addParameter(QgsProcessingParameterFolderDestination(
            self.P_OUTDIR, 'Pasta de saída (GeoTIFF)'))

        self.addOutput(QgsProcessingOutputString(self.O_LAYER, 'Camada criada'))
        self.addOutput(QgsProcessingOutputString(self.O_TIFS, 'GeoTIFFs (JSON {fid:path})'))

    def processAlgorithm(self, parameters, context, feedback):
        esc_idx = self.parameterAsInt(parameters, self.P_ESCALA, context)
        escala  = ESCALAS[esc_idx]
        fids    = [s.strip().upper() for s in self.parameterAsString(parameters, self.P_FIDS, context).replace(',', ';').split(';') if s.strip()]
        gama    = ['gama_line_1105','gama_line_1089','gama_1039','gama_3022'][ self.parameterAsInt(parameters, self.P_GAMA, context) ]
        mag     = ['mag_line_1105','mag_line_1089','mag_1039','mag_3022'][ self.parameterAsInt(parameters, self.P_MAG, context) ]
        extend  = self.parameterAsInt(parameters, self.P_EXT, context)
        feats   = [s.strip() for s in self.parameterAsString(parameters, self.P_FEATS, context).split(',') if s.strip()]
        psize   = self.parameterAsInt(parameters, self.P_PSIZE, context)
        algo    = ['linear','cubic','nearest','idw'][ self.parameterAsInt(parameters, self.P_ALGO, context) ]
        noneg   = self.parameterAsBool(parameters, self.P_NONEG, context)
        outdir  = self.parameterAsFile(parameters, self.P_OUTDIR, context) or os.getcwd()
        epsg_forc = parameters.get(self.P_EPSG, None)
        epsg_forc = int(epsg_forc) if epsg_forc not in (None, '') else None

        src = _soft_import_src(feedback)
        interp_at = _get_interp_at(feedback)

        feedback.pushInfo(f"# Folhas: {', '.join(fids)} | Escala={escala}")
        quad = src.Build_mc(escala=escala, ID=fids, verbose=True)
        _g, _m = src.Upload_geof(quad, gama_xyz=gama, mag_xyz=mag, extend_size=int(extend))
        quad = src.pop_nodata(quad)

        # escolhe algoritmo: se o usuário pedir 'idw', força IDW mesmo que haja verde
        def _interp(x, y, z, xu, yu):
            if algo == 'idw':
                return _get_interp_at(feedback=feedback)(x,y,z,xu,yu,algorithm='idw')
            return interp_at(x,y,z,xu,yu,algorithm=algo, extrapolate=True)

        layer_name = f"geof_{_infer_suffix_from_names(gama,mag)}_{algo}"
        import pandas as pd
        for fid in fids:
            blob = quad.get(fid, {})
            gdf  = blob.get(gama); mdf = blob.get(mag)
            if gdf is None and mdf is None:
                feedback.reportError(f"[{fid}] sem dados brutos ({gama}/{mag}). Pulando.")
                continue

            xu, yu = src.sintetic_grid(quad, fid, psize=int(psize))

            sources = {}
            if isinstance(gdf, pd.DataFrame):
                gsrc = gdf.copy()
                if noneg:
                    for c in gsrc.columns:
                        if c not in ('X','Y') and pd.api.types.is_numeric_dtype(gsrc[c]):
                            gsrc.loc[gsrc[c] < 0, c] = np.nan
                sources['gama'] = (np.asarray(gsrc['X']), np.asarray(gsrc['Y']), gsrc)
            if isinstance(mdf, pd.DataFrame):
                msrc = mdf.copy()
                if noneg:
                    for c in msrc.columns:
                        if c not in ('X','Y') and pd.api.types.is_numeric_dtype(msrc[c]):
                            msrc.loc[msrc[c] < 0, c] = np.nan
                sources['mag'] = (np.asarray(msrc['X']), np.asarray(msrc['Y']), msrc)
            if not sources:
                feedback.reportError(f"[{fid}] fontes vazias. Pulando.")
                continue

            out = {'X': xu, 'Y': yu}
            for f in feats:
                arr = None
                order = ['mag','gama'] if _norm(f) in ('gmt','mdt') else ['gama','mag']
                for sname in order:
                    if sname not in sources: continue
                    x, y, df = sources[sname]
                    col = _find_col(df, f)
                    if col is None: continue
                    vals = df[col].to_numpy()
                    arr = _interp(x, y, vals, xu, yu)
                    break
                if arr is None:
                    arr = np.full_like(xu, np.nan, dtype='float32')
                out[f] = arr
            quad[fid][layer_name] = pd.DataFrame(out)

        feedback.pushInfo(f"→ Camada criada: {layer_name}")

        # Exporta GeoTIFF e adiciona ao QGIS
        tif_map = {}
        for fid in fids:
            if layer_name not in quad.get(fid, {}): continue
            df = quad[fid][layer_name]
            # tenta EPSG do meta; cai para o forçado, depois 32723
            meta_epsg = None
            try:
                meta_epsg = int((quad.get(fid, {}) or {}).get('meta', {}).get('epsg', None))
            except Exception:
                meta_epsg = None
            epsg_use = epsg_forc or meta_epsg or 32723

            out_tif = os.path.join(outdir, f"{fid}_{layer_name}.tif")
            tif_path, bands, epsg_used = _export_geotiff_stack_gdal(df, out_tif, epsg=epsg_use)
            tif_map[fid] = tif_path
            feedback.pushInfo(f"[GeoTIFF] {fid}: {tif_path} | EPSG {epsg_used} | Bandas: {', '.join(bands)}")

            rl = QgsRasterLayer(tif_path, f"{fid}_{layer_name}")
            if rl.isValid():
                QgsProject.instance().addMapLayer(rl)
            else:
                feedback.reportError(f"Raster inválido: {tif_path}")

        return { self.O_LAYER: layer_name, self.O_TIFS: json.dumps(tif_map, ensure_ascii=False) }

class PreditorTerraLiteProvider(QgsProcessingProvider):
    def id(self): return 'preditor_terra'
    def name(self): return 'PreditorTerra'
    def loadAlgorithms(self, *args, **kwargs):
        self.addAlgorithm(PreditorTerraLiteGDAL())

def PreditorTerraLite_register():
    prov = PreditorTerraLiteProvider()
    QgsApplication.processingRegistry().addProvider(prov)
    print("[PreditorTerra · Lite (GDAL)] Provider registrado.")

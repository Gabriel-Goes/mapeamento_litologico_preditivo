# %% [markdown]
# G-Geo | Notebook compacto: seleção → dicionário → pré-process → interpolação → predição (SOM/SVM)
# Executar em pequenos passos com run("passo"): "area", "dic", "prep", "interp", "som", "svm"

# %% Imports essenciais
import os, sys, re, json
import pandas as pd
import numpy as np
# Coloque isto acima de step_interp()
from shapely.geometry.base import BaseGeometry as _ShpBase
from shapely import wkb as _shwkb, wkt as _shwkt


# Tenta importar seus módulos no pacote `nucleo`; se não houver, cai para arquivos locais
try:
    from nucleo.utils import set_db, delimt, reverse_meta_cartas, gdb_url
    from nucleo.databaseengine import DatabaseEngine
    from nucleo.abrirfolhas import AbrirFolhas
except Exception:
    sys.path.append(os.getcwd())  # ajuste se rodar fora do projeto
    from utils import set_db, delimt, reverse_meta_cartas, gdb_url  # /home/database + meta_cartas
    from databaseengine import DatabaseEngine
    from abrirfolhas import AbrirFolhas

# Interpolação
import verde as vd

# %% Parâmetros do experimento (edite só aqui)
PARAMS = dict(
    escala="25k",                 # "25k","50k","100k","250k","500k","1kk"  (ou "1:25.000" que eu converto)
    id_area="SF23",               # prefixo/ID da área-mãe (ex.: "SF23")
    filtro_folhas=".*",           # regex para refinar (ex.: "SF23_YA.*" p/ subset)
    extend_size=0,                # “gordurinha” da bbox em metros ao selecionar pontos
    gama_xyz=None,                # ex.: "gama_SP-RJ_1039.xyz" (dentro de /home/database/geof/)
    mag_xyz=None,                 # ex.: "mag_SP-RJ_1039.xyz"
    features_gama=['CTCOR','eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO','MDT'],
    features_mag =['MAGIGRF','MDT'],
    litologia_layer=None,         # se quiser cruzar rótulos (ex.: "litologia_25k"); opcional
    som_cfg=dict(m=20, n=20, sigma=1.2, learning_rate=0.5),  # gancho p/ SOM (minisom)
    svm_cfg=dict(C=10.0, gamma="scale", kernel="rbf")        # gancho p/ SVM
)

STATE = dict(
    cartas=None,      # dict[codigo] -> {'geometry': WKB, 'epsg': '32723', 'escala': '25k', ...}
    folhas=None,      # lista de códigos selecionados
    dados_xyz=dict(), # 'gama' -> DataFrame (X,Y, features...), 'mag' -> DataFrame
    interp=dict()     # interp[folha][feature] -> xarray grid (Verde)
)


def _resolve_escala(e):
    # aceita "1:25.000" ou "25k"
    if ":" in e:
        return reverse_meta_cartas.get(e, None)
    return e

# %% 1) Escolha da área (escala + ID)
def step_area():
    print(delimt + "1) Escolha da área")
    esc = _resolve_escala(PARAMS['escala'])
    if not esc:
        raise ValueError(f"Escala inválida: {PARAMS['escala']}")
    # inicializa engine/sessão (se ainda não houver)
    DatabaseEngine(gdb_url)
    # abre folhas dessa escala do PostGIS
    af = AbrirFolhas()
    cartas = af.seleciona_escala_postgres(esc) or {}
    # filtra por ID da área e regex extra
    regex = re.compile(PARAMS['filtro_folhas'])
    cartas_sel = {k:v for k,v in cartas.items()
                  if k.startswith(PARAMS['id_area']) and regex.search(k)}
    if not cartas_sel:
        raise RuntimeError("Nenhuma folha encontrada para esses filtros.")
    STATE['cartas'] = cartas_sel
    STATE['folhas'] = sorted(cartas_sel.keys())
    print(f"→ {len(STATE['folhas'])} folhas na área {PARAMS['id_area']} @ {esc}: {STATE['folhas'][:6]}...")

# %% 2) Construção do dicionário de quadrículas
def step_dic():
    print(delimt + "2) Construção do dicionário")
    if not STATE['cartas']:
        raise RuntimeError("Execute primeiro: step_area()")
    # já está no formato desejado: {codigo: {'geometry': WKB, 'epsg': ..., 'escala': ...}}
    print(f"→ dicionário com {len(STATE['cartas'])} entradas pronto.")

# %% Utilitário: ler e unificar XYZ (X/Y + atributos)
def _read_xyz(name):
    if not name:
        return pd.DataFrame()
    path = os.path.join(set_db('geof/'), name)
    df = pd.read_csv(path)
    # unifica colunas X/Y (aceita UTME/UTMN, X/Y, LONG/LAT)
    cols = {c.upper(): c for c in df.columns}
    def pick(*opts):
        for o in opts:
            if o in cols: return cols[o]
        return None
    cx = pick('X','UTME','EASTING','LONG','LONGITUDE','LON')
    cy = pick('Y','UTMN','NORTHING','LAT','LATITUDE')
    if cx is None or cy is None:
        raise ValueError(f"Não encontrei colunas X/Y em {name}. Colunas: {list(df.columns)[:12]}")
    df = df.rename(columns={cx:'X', cy:'Y'})
    return df

# %% 3) Pré-processamento dos .xyz
def step_prep():
    print(delimt + "3) Pré-processamento dos .xyz")
    gama = _read_xyz(PARAMS['gama_xyz'])
    mag  = _read_xyz(PARAMS['mag_xyz'])
    # mantém só o que existe:
    if not gama.empty:
        keep = ['X','Y'] + [c for c in PARAMS['features_gama'] if c in gama.columns]
        gama = gama[keep].dropna()
        print(f"→ gama: {gama.shape} | feats: {keep[2:]}")
        STATE['dados_xyz']['gama'] = gama
    if not mag.empty:
        keep = ['X','Y'] + [c for c in PARAMS['features_mag'] if c in mag.columns]
        mag = mag[keep].dropna()
        print(f"→ mag : {mag.shape} | feats: {keep[2:]}")
        STATE['dados_xyz']['mag'] = mag
    if not STATE['dados_xyz']:
        print("⚠️ Nenhum dado .xyz carregado. Defina PARAMS['gama_xyz'] e/ou ['mag_xyz'].")

# %% 4) Interpolação por folha (Verde: Trend + BlockReduce + Spline)
def _interp_one(df, region, data_name):
    coords = (df.X.values.astype(float), df.Y.values.astype(float))
    chain = vd.Chain([
        ('trend',  vd.Trend(degree=1)),
        ('reduce', vd.BlockReduce(np.mean, spacing=1000)),
        ('spline', vd.Spline())  # Thin-plate spline
    ])
    chain.fit(coords, df[data_name].values)
    grid = chain.grid(spacing=200, data_names=[data_name], pixel_register=True)
    # máscara por distância até pontos
    grid_masked = vd.distance_mask(coords, maxdist=1000, grid=grid)
    return grid_masked


def _to_shapely(geom):
    """Aceita Shapely, GeoAlchemy2 WKBElement, QgsGeometry, WKT/hex ou objetos com .desc"""
    # 1) Já é shapely?
    if isinstance(geom, _ShpBase):
        return geom
    # 2) GeoAlchemy2 WKBElement
    try:
        from geoalchemy2.elements import WKBElement
        if isinstance(geom, WKBElement):
            return _shwkb.loads(bytes(geom.data))
    except Exception:
        pass
    # 3) QgsGeometry (PyQGIS)
    try:
        from qgis.core import QgsGeometry
        if isinstance(geom, QgsGeometry):
            # asWkb() retorna bytes prontos p/ shapely
            return _shwkb.loads(geom.asWkb())
    except Exception:
        pass
    # 4) Objetos com atributo .desc (GeoAlchemy2 antigo)
    if hasattr(geom, "desc"):
        return _shwkb.loads(geom.desc, hex=True)
    # 5) String WKT
    if isinstance(geom, str):
        return _shwkt.loads(geom)
    raise TypeError(f"Tipo de geometria não suportado: {type(geom)}")


def step_interp():
    print(delimt + "4) Interpolação (Verde)")
    if not STATE['cartas']:
        raise RuntimeError("Execute primeiro: step_area()")
    if not STATE['dados_xyz']:
        print("⚠️ Sem dados para interpolar. Rode step_prep()."); return
    STATE['interp'] = {}
    # monta área por folha a partir da geometria WKB + EPSG
    from shapely.wkb import loads as wkb_loads
    import pyproj
    from shapely.ops import transform as shp_transform

    for cod, meta in STATE['cartas'].items():
        wkb = meta['geometry']
        epsg = meta['epsg']
        # poly = wkb_loads(wkb.desc, hex=True) if hasattr(wkb, 'desc') else wkb  # compat
        poly = _to_shapely(meta['geometry'])
        # reprojeta WGS84->UTM da folha
        wgs84 = pyproj.CRS('epsg:4326')
        utm   = pyproj.CRS('epsg:' + str(epsg))
        proj  = pyproj.Transformer.from_crs(wgs84, utm, always_xy=True).transform
        poly_u = shp_transform(proj, poly)
        minx,miny,maxx,maxy = poly_u.bounds
        reg = (minx, maxx, miny, maxy)  # (W, E, S, N) em metros UTM
        STATE['interp'][cod] = {}

        # Gama
        if 'gama' in STATE['dados_xyz']:
            df = STATE['dados_xyz']['gama']
            # recorta pontos desta folha
            inside = vd.inside((df.X, df.Y), reg)
            if inside.any():
                feats = [c for c in PARAMS['features_gama'] if c in df.columns]
                for f in feats:
                    grid = _interp_one(df[inside], reg, f)
                    STATE['interp'][cod].setdefault('gama', {})[f] = grid

        # Mag
        if 'mag' in STATE['dados_xyz']:
            df = STATE['dados_xyz']['mag']
            inside = vd.inside((df.X, df.Y), reg)
            if inside.any():
                feats = [c for c in PARAMS['features_mag'] if c in df.columns]
                for f in feats:
                    grid = _interp_one(df[inside], reg, f)
                    STATE['interp'][cod].setdefault('mag', {})[f] = grid

    FolhasOK = [k for k,v in STATE['interp'].items() if v]
    print(f"→ folhas interpoladas: {len(FolhasOK)} / {len(STATE['cartas'])}")

# %% 5) Ganchos de predição (SOM agora; SVM depois)
def step_som():
    """
    Exemplo de encaixe: você pode empilhar grids por folha -> vetorizar -> treinar SOM.
    (Requer `minisom`: pip install minisom)
    """
    try:
        from minisom import MiniSom
    except Exception:
        print("⚠️ Instale `minisom` para usar o SOM. Pulando..."); return
    print(delimt + "5) Predição não supervisionada (SOM) — exemplo")
    # Exemplo: pega a primeira folha e empilha alguns grids disponíveis
    any_leaf = next((k for k in STATE['interp'] if STATE['interp'][k]), None)
    if not any_leaf:
        print("Sem grids interpolados. Rode step_interp()."); return
    stacks = []
    for group in ('gama','mag'):
        if group in STATE['interp'][any_leaf]:
            for f, grid in STATE['interp'][any_leaf][group].items():
                arr = np.asarray(grid[f])  # xarray -> numpy
                stacks.append(arr.reshape(-1, 1))
    if not stacks:
        print("Sem camadas para SOM nesta folha."); return
    X = np.hstack(stacks)
    # normaliza por coluna
    X = (X - X.mean(0)) / (X.std(0) + 1e-9)
    m,n = PARAMS['som_cfg']['m'], PARAMS['som_cfg']['n']
    som = MiniSom(m, n, X.shape[1],
                  sigma=PARAMS['som_cfg']['sigma'],
                  learning_rate=PARAMS['som_cfg']['learning_rate'])
    som.random_weights_init(X)
    som.train_random(X, 2000)
    print(f"→ SOM treinado ({m}x{n}) em {X.shape[0]} amostras / {X.shape[1]} variáveis.")
    STATE['som_model'] = som

def step_svm():
    """
    Exemplo de gancho para SVM SUPERVISIONADO (precisa de rótulos).
    Sugestão: gerar amostras rotuladas por join espacial (pontos vs. litologia).
    """
    try:
        from sklearn.pipeline import make_pipeline
        from sklearn.preprocessing import StandardScaler
        from sklearn.svm import SVC
    except Exception:
        print("⚠️ Instale scikit-learn para usar SVM. Pulando..."); return
    print(delimt + "5) Predição supervisionada (SVM) — esqueleto")
    print("→ Prepare X (features de grids/pixels) e y (rótulos de litologia) antes deste passo.")

# %% Orquestrador
def run(step="area"):
    step = step.lower()
    if step == "area":  step_area()
    elif step == "dic": step_dic()
    elif step == "prep": step_prep()
    elif step == "interp": step_interp()
    elif step == "som": step_som()
    elif step == "svm": step_svm()
    elif step == "all":
        step_area(); step_dic(); step_prep(); step_interp(); step_som()
    else:
        raise ValueError("passo desconhecido. Use: area | dic | prep | interp | som | svm | all")

# Exemplo mínimo de execução interativa no notebook:
# PARAMS.update(dict(escala="25k", id_area="SF23",
#                    gama_xyz="gama_SP-RJ_1039.csv", mag_xyz=None))
# run("area"); run("dic"); run("prep"); run("interp"); run("som")

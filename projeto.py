# -*- coding: utf-8 -*-
# UI integrada: Aerogeofísica + SOM + Satélite (BDC/INPE/STAC)
# - Corrigido rasterio.sample (sem 'resampling')
# - Baixar itens STAC que intersectam a quadrícula -> sat_store[item_id]
# - Amostrar TCI/bandas (item único ou todos) para a grade interpolada

# ==== imports do seu projeto ====
from src import *                               # Build_mc, Upload_geof, pop_nodata, sintetic_grid, import_malha_cartog
from verde_source import regular, interp_at     # opcional (interp_at utilizado se presente)

# ==== libs ====
import os, re, json, types, importlib, warnings, requests, math
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib import cm, colors
from matplotlib.colors import ListedColormap, BoundaryNorm
from shapely.geometry import Point, Polygon
from shapely.ops import transform as shp_transform

from tqdm import tqdm
import ipywidgets as W
from IPython.display import display, clear_output

from sklearn_som.som import SOM
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

from pystac_client import Client
import rasterio
from rasterio.enums import Resampling
from pyproj import Transformer

warnings.filterwarnings("ignore")

# ====================== ESTADO GLOBAL ======================
ESCALAS = ['25k','50k','100k','250k','1kk']

quadricula = {}         # {fid: { 'folha': Series(EPSG=...), 'gama_*': df, 'mag_*': df, 'geof_*': df, ... }}
data_grid = None        # nome da camada interpolada SOM (ex.: 'geof_1105_linear')
som_store = {}          # {k: {'som','imp','sca','feats','layer'}}
som_last_pred = None
bdc_items = []          # lista de pystac.Item da busca corrente
sat_store = {}          # { item_id: {'collection','datetime','bbox','assets':{name:path}, 'hrefs':{name:href}} }

# ====================== HELPERS GERAIS ======================
def _ids_from_mc(escala, filtro_regex=None):
    mc = import_malha_cartog(escala=escala)
    ids = mc['id_folha'].astype(str).tolist()
    if filtro_regex:
        pat = re.compile(filtro_regex, re.IGNORECASE)
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

def _global_min_max_numeric(q, ids, layers, column, remove_neg=False):
    vals = []
    for fid in ids:
        blob = q.get(fid, {})
        for lay in layers:
            df = blob.get(lay)
            if isinstance(df, pd.DataFrame) and column in df.columns:
                s = df[column]
                if pd.api.types.is_numeric_dtype(s):
                    if remove_neg: s = s[s >= 0]
                    if s.size: vals.append(s.to_numpy())
    if not vals: return None, None
    v = np.concatenate(vals)
    if v.size == 0 or np.all(np.isnan(v)): return None, None
    return float(np.nanmin(v)), float(np.nanmax(v))

def _plot_layers_for_column(q, ids, layers, column, remove_neg=False):
    plt.figure(figsize=(12,9)); ax = plt.gca()
    is_num = False
    for fid in ids:
        for lay in layers:
            df = q.get(fid, {}).get(lay)
            if isinstance(df, pd.DataFrame) and column in df.columns:
                is_num = pd.api.types.is_numeric_dtype(df[column]); break
        if is_num: break
    if is_num:
        vmin, vmax = _global_min_max_numeric(q, ids, layers, column, remove_neg)
        if vmin is not None and vmax is not None and vmin == vmax: vmin, vmax = vmin-1e-9, vmax+1e-9
        norm = colors.Normalize(vmin=vmin, vmax=vmax) if vmin is not None else None
        cmap = cm.get_cmap('terrain')
    for fid in ids:
        for lay in layers:
            df = q.get(fid, {}).get(lay)
            if not isinstance(df, pd.DataFrame) or column not in df.columns: continue
            d = df if not (is_num and remove_neg) else df[df[column] >= 0]
            if d.empty: continue
            if is_num:
                ax.scatter(d.X.values, d.Y.values, c=d[column].values, s=0.1, cmap=cmap, norm=norm, marker='H')
            else:
                codes, _ = pd.factorize(d[column], sort=True)
                ax.scatter(d.X.values, d.Y.values, c=codes, s=0.1, cmap='tab20', marker='H')
    ax.set_aspect('equal'); ax.set_title(f'Pré-visualização • {column} • {len(ids)} folha(s) • {", ".join(layers)}')
    if is_num and norm is not None:
        cbar = plt.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax)
        vmin, vmax = norm.vmin, norm.vmax; mid = (vmin+vmax)/2
        cbar.set_ticks([vmin, mid, vmax]); cbar.ax.set_yticklabels([f'{vmin:.3g}', f'{mid:.3g}', f'{vmax:.3g}'])
        cbar.set_label(f'{column} (min→máx)')
    plt.show()

def _make_discrete_cmap(n):
    base = plt.get_cmap('tab20')
    if hasattr(base, 'colors') and len(base.colors) >= n: return ListedColormap(base.colors[:n], name=f'tab20_{n}')
    return plt.get_cmap('nipy_spectral', n)

def _infer_suffix_from_names(*names):
    for nm in names or []:
        m = re.search(r'(\d{4})', str(nm) if nm else '')
        if m: return m.group(1)
    return '0000'

def _norm_name(s): return re.sub(r'[^a-z0-9]+','',str(s).lower())

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

# ============ INTERPOLAÇÃO para a grade ============
def _interpolate_current_selection(quad, ids, gama_key, mag_key, features, psize, algo, noneg=False):
    suf = _infer_suffix_from_names(gama_key, mag_key); out_name = f"geof_{suf}_{algo}"
    for fid in ids:
        blob = quad.get(fid, {})
        gdf = blob.get(gama_key); mdf = blob.get(mag_key)
        if gdf is None and mdf is None: continue
        xu, yu = sintetic_grid(quad, fid, psize=int(psize))
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
        if not sources: continue
        out = {'X': xu, 'Y': yu}
        for f in features:
            arr = None
            for src in _source_order_for_feature(f):
                if src not in sources: continue
                x, y, df = sources[src]
                col = _find_source_column(df, f)
                if col is None: continue
                arr = interp_at(x, y, df[col].to_numpy(), xu, yu, algorithm=algo, extrapolate=True)
                break
            if arr is None: arr = np.full_like(xu, np.nan, dtype='float32')
            out[f] = arr
        quad[fid][out_name] = pd.DataFrame(out)
    return out_name

# ============ helpers UI ============
def _rescan_from_quadricula():
    q = globals().get('quadricula', {})
    layers = _scan_layers_from_quadricula(q); w_layers.options = layers
    global data_grid
    pick = (data_grid,) if data_grid and data_grid in layers else (layers[:1] if layers else ())
    w_layers.value = pick if pick else ()
    cols = _available_columns(q, w_layers.value) or ('MDT',)
    w_cols.options = cols
    w_cols.value = tuple([c for c in ('MDT',) if c in cols]) or ((cols[0],) if cols else ())
    # SOM widgets dependentes
    numeric = []
    for _, blob in q.items():
        for lay in w_layers.value:
            df = blob.get(lay)
            if isinstance(df, pd.DataFrame):
                for c in cols:
                    if c in df.columns and pd.api.types.is_numeric_dtype(df[c]): numeric.append(c)
    opts = sorted(set(numeric), key=lambda c: (c!='MDT', c)) or ['MDT']
    w_feats.options = opts
    keep = [c for c in w_feats.value if c in opts] or (['MDT'] if 'MDT' in opts else opts[:min(5,len(opts))])
    w_feats.value = tuple(keep)
    test_opts = []
    if data_grid:
        for fid, blob in q.items():
            if data_grid in blob and isinstance(blob[data_grid], pd.DataFrame):
                test_opts.append(fid)
    w_test_ids.options = tuple(sorted(test_opts))
    w_test_ids.value = tuple(sorted(test_opts))[:min(4, len(test_opts))]
    ks = sorted(list(som_store.keys()))
    w_k_apply.options = ks
    if ks: w_k_apply.value = ks[0]

def _normalize_xy(df):
    if not {'E_utm','N_utm'}.issubset(df.columns):
        if {'X','Y'}.issubset(df.columns): df = df.rename(columns={'X':'E_utm','Y':'N_utm'}).copy()
        else: raise ValueError("Camada sem 'X','Y' ou 'E_utm','N_utm'.")
    df = df.sort_values(['N_utm','E_utm'], ascending=[False, True], ignore_index=True, kind='mergesort')
    xs1d = np.sort(df['E_utm'].unique()); ys1d = np.sort(df['N_utm'].unique())
    nx, ny = xs1d.size, ys1d.size
    xs_mesh, ys_mesh = np.meshgrid(xs1d, ys1d)
    return df, xs_mesh, ys_mesh, nx, ny

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
        except Exception: continue
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

def _plot_classes(classes_by_fid, metas, n_clusters, flip_ns=False, titulo='Mapa preditivo (SOM)'):
    cmap = _make_discrete_cmap(n_clusters)
    bounds = np.arange(-0.5, n_clusters + 0.5, 1); norm = BoundaryNorm(bounds, ncolors=n_clusters, clip=True)
    fig, ax = plt.subplots(figsize=(10,10), facecolor='w')
    for fid in sorted(classes_by_fid.keys()):
        Z = classes_by_fid[fid];  Z = np.flipud(Z) if flip_ns else Z
        xs = metas[fid]['xs']; ys = metas[fid]['ys']
        ax.pcolormesh(xs, ys, Z, cmap=cmap, norm=norm, shading='nearest', rasterized=True)
    ax.set_aspect('equal'); ax.set_title(titulo)
    cbar = fig.colorbar(cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, ticks=np.arange(n_clusters), pad=0.01)
    cbar.ax.set_yticklabels([f'Classe {i+1}' for i in range(n_clusters)]); cbar.set_label('Classes')
    plt.tight_layout(); plt.show()

def _predict_per_folha(som, X_std, slc, metas):
    out = {}
    for fid, s in slc.items():
        y = som.predict(X_std[s]); ny, nx = metas[fid]['ny'], metas[fid]['nx']
        out[fid] = y.reshape(ny, nx)
    return out

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

# ====== util de clip por percentil ======
def _pct_clip(a, pmin=None, pmax=None):
    """Retorna limites por percentil sem alterar os dados."""
    if pmin is None and pmax is None or len(a) == 0:
        return None
    lo = np.nanpercentile(a, pmin) if pmin is not None else None
    hi = np.nanpercentile(a, pmax) if pmax is not None else None
    return (lo, hi)

# ====== Boxplots (independentes por feature) ======
def boxplots_por_feature(
    df,
    features,
    class_col="som_class",
    classes=None,
    ncols=3,
    showfliers=False,
    pclip=(None, None),     # ex: (1, 99) para limitar visualmente
    log=False,              # log no eixo de valores (x)
    titulo=None,
    h_pad=0.6, w_pad=0.6,
    dpi=140,
):
    """
    1 subplot por feature, cada qual com ESCALA INDEPENDENTE.
    Boxplots horizontais: eixo-Y = classes; eixo-X = valores (escala do valor).
    """
    if classes is None:
        classes = sorted([c for c in df[class_col].dropna().unique()])
    classes = list(classes)
    feats = [f for f in features if f in df.columns]

    if not feats or not classes:
        raise ValueError("Sem features ou classes válidas para plotar.")

    n = len(feats)
    ncols = max(1, int(ncols))
    nrows = math.ceil(n / ncols)
    fig_h = max(2.4, 0.5 * len(classes)) * nrows
    fig_w = 4.5 * ncols

    fig, axes = plt.subplots(
        nrows=nrows, ncols=ncols, figsize=(fig_w, fig_h),
        squeeze=False, dpi=dpi, layout='constrained'
    )

    for i, feat in enumerate(feats):
        r, c = divmod(i, ncols)
        ax = axes[r][c]
        data = [df.loc[df[class_col] == cl, feat].dropna().values for cl in classes]

        bp = ax.boxplot(
            data,
            vert=False,
            labels=classes,
            showfliers=showfliers,
            patch_artist=True,
            whis=(5, 95)
        )
        for patch in bp['boxes']:
            patch.set_alpha(0.8)

        ax.grid(True, axis='x', linestyle=':', alpha=0.6)
        ax.set_title(feat, fontsize=10, pad=6)

        # escala independente por feature (no eixo X)
        clip = _pct_clip(np.concatenate([d for d in data if len(d)]), *pclip) if any(len(d) for d in data) else None
        if clip:
            lo, hi = clip
            if lo is not None and hi is not None and np.isfinite(lo) and np.isfinite(hi) and hi > lo:
                ax.set_xlim(lo, hi)

        if log:
            xmin, xmax = ax.get_xlim()
            ax.set_xlim(max(xmin, 1e-12), xmax)
            ax.set_xscale('log')

        ax.tick_params(axis='y', labelsize=9)
        ax.tick_params(axis='x', labelsize=8)

    for j in range(n, nrows * ncols):
        r, c = divmod(j, ncols)
        axes[r][c].axis('off')

    if titulo:
        fig.suptitle(titulo, fontsize=12, y=1.02)

    fig.set_constrained_layout_pads(h_pad=h_pad, w_pad=w_pad, hspace=0.02, wspace=0.02)
    return fig, axes

# ====== Widget interativo para boxplots por feature ======
def boxplot_widget(
    df,
    features,
    class_col="som_class",
    classes=None,
    titulo="Distribuição por classe (boxplots independentes por feature)"
):
    try:
        import ipywidgets as W
        from IPython.display import display, clear_output
    except Exception as e:
        raise RuntimeError("Este widget requer Jupyter + ipywidgets instalados.") from e

    feats_all = [f for f in features if f in df.columns]
    if classes is None:
        classes = sorted([c for c in df[class_col].dropna().unique()])

    sel_feats = W.SelectMultiple(
        options=feats_all, value=tuple(feats_all[:min(6, len(feats_all))]),
        description='Features', rows=min(12, len(feats_all))
    )
    sel_classes = W.SelectMultiple(
        options=classes, value=tuple(classes),
        description='Classes', rows=min(10, len(classes))
    )

    ncols = W.IntSlider(value=3, min=1, max=6, step=1, description='Colunas')
    showfliers = W.Checkbox(value=False, description='Outliers')
    logscale = W.Checkbox(value=False, description='Escala log')
    pmin = W.IntSlider(value=5, min=0, max=40, step=1, description='Clip min (%)')
    pmax = W.IntSlider(value=95, min=60, max=100, step=1, description='Clip max (%)')

    btn = W.Button(description='Plotar', button_style='primary')
    out = W.Output()

    def _on_click(_):
        with out:
            clear_output(wait=True)
            feats = list(sel_feats.value)
            cls = list(sel_classes.value)
            if not feats or not cls:
                print("Selecione ao menos 1 feature e 1 classe.")
                return
            fig, _ = boxplots_por_feature(
                df=df,
                features=feats,
                class_col=class_col,
                classes=cls,
                ncols=ncols.value,
                showfliers=showfliers.value,
                pclip=(pmin.value if pmin.value > 0 else None,
                       pmax.value if pmax.value < 100 else None),
                log=logscale.value,
                titulo=titulo
            )
            display(fig); plt.show()

    btn.on_click(_on_click)

    ui = W.VBox([
        W.HBox([sel_feats, sel_classes]),
        W.HBox([ncols, showfliers, logscale, pmin, pmax]),
        btn,
        out
    ])
    return ui

# ====== Alternativa rápida: boxplots por classe (compartilha escala do eixo Y por padrão) ======
def plot_boxplots_por_atributo(df_long, atributos, classes=None, ncols=2, showfliers=False, rotation=45, sharey=True, figsize_cell=(4.0,3.2), suptitle=None):
    if classes is None: classes = sorted(pd.Series(df_long['classe']).dropna().unique())
    n = len(classes); ncols = max(1,int(ncols)); nrows = math.ceil(n/ncols)
    fig_w = max(6.0, figsize_cell[0]*ncols); fig_h = max(3.2, figsize_cell[1]*nrows)
    fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), sharey=sharey); axes = np.atleast_1d(axes).ravel()
    y_min = y_max = None
    if sharey:
        gvals=[]
        for c in classes:
            sub = df_long[df_long['classe']==c]
            for a in atributos:
                if a in sub.columns:
                    s = pd.to_numeric(sub[a], errors='coerce').dropna().values
                    if s.size: gvals.append(s)
        if gvals:
            gcat = np.concatenate(gvals); y_min, y_max = np.nanmin(gcat), np.nanmax(gcat)
    for i,c in enumerate(classes):
        ax = axes[i]; sub = df_long[df_long['classe']==c]
        vals, labels = [], []
        for a in atributos:
            if a in sub.columns:
                s = pd.to_numeric(sub[a], errors='coerce').dropna()
                if s.size: vals.append(s.values); labels.append(a)
        lab = int(c)+1 if isinstance(c,(int,np.integer)) else c
        if not vals: ax.set_title(f"Classe {lab} (sem dados)"); ax.axis("off")
        else:
            ax.boxplot(vals, labels=labels, showfliers=showfliers); ax.set_title(f"Classe {lab}")
            ax.set_xlabel("Atributo"); ax.set_ylabel("Valor"); ax.tick_params(axis='x', labelrotation=rotation)
            if y_min is not None and y_max is not None:
                pad = 0.03*(y_max-y_min if y_max!=y_min else 1.0); ax.set_ylim(y_min-pad, y_max+pad)
    for j in range(i+1, len(axes)): axes[j].axis("off")
    if suptitle: fig.suptitle(suptitle)
    plt.tight_layout(); plt.show(); return fig

# ============================ WIDGETS BASE ============================
w_escala = W.Dropdown(options=ESCALAS, value='100k', description='Escala')
w_filtro = W.Text(placeholder='ex.: SF23_YA', description='Filtro')
w_ids    = W.SelectMultiple(options=(), rows=10, description='Folhas')
w_selall = W.ToggleButton(value=False, description='Selecionar tudo', icon='check')
w_clear  = W.Button(description='Limpar', icon='trash')

w_ext    = W.IntSlider(min=0, max=2000, step=100, value=600, description='extend_size')
w_gama   = W.Dropdown(options=['gama_line_1105','gama_line_1089','gama_1039','gama_3022'], value='gama_line_1105', description='Gama')
w_mag    = W.Dropdown(options=['mag_line_1105','mag_line_1089','mag_1039','mag_3022'], value='mag_line_1105', description='Mag')
w_load   = W.Button(description='Carregar brutos', button_style='success', icon='download')

w_feats_interp = W.SelectMultiple(
    options=['GMT','CTCOR','eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO','MDT'],
    value=('GMT','CTCOR','eTh','eU','KPERC','MDT'),
    rows=8, description='Features (grid)'
)
w_psize  = W.IntSlider(min=50, max=1000, step=50, value=100, description='Pixel (m)')
w_algo   = W.Dropdown(options=[('Linear','linear'),('Cúbico','cubic')], value='linear', description='Algoritmo')
w_nonegI = W.Checkbox(value=False, description='Negativos→NaN (grid)')
w_interpolar = W.Button(description='Interpolar grade', icon='shuffle')

w_layers = W.SelectMultiple(options=(), rows=6, description='Camadas')
w_cols   = W.SelectMultiple(options=('MDT',), value=('MDT',), rows=6, description='Colunas')
w_nonegP = W.Checkbox(value=False, description='Remover negativos (preview)')
w_refresh = W.Button(description='Atualizar', icon='refresh')
w_plot   = W.Button(description='Pré-visualizar', icon='eye')

w_feats  = W.SelectMultiple(options=('MDT',), value=('MDT',), rows=8, description='Features (SOM)')
w_sigma  = W.FloatSlider(min=0.1, max=5.0, step=0.1, value=1.5, description='sigma')
w_iter   = W.IntSlider(min=500, max=30000, step=500, value=10000, description='max_iter')
w_seed   = W.IntSlider(min=0, max=9999, step=1, value=42, description='seed')
w_flip   = W.Checkbox(value=False, description='flip N-S no plot')
w_ks_train = W.SelectMultiple(options=tuple(range(3,31)), value=(8,12,16), rows=8, description='k p/ treinar')
w_train  = W.Button(description='Treinar SOM(s)', button_style='primary', icon='play')

w_test_ids = W.SelectMultiple(options=(), rows=8, description='Folhas (teste)')
w_seltest  = W.ToggleButton(value=False, description='Selecionar todas (teste)', icon='check')
w_k_apply  = W.Dropdown(options=[], description='k (aplicar)')
w_apply    = W.Button(description='Aplicar/Testar', icon='check-circle')
w_evalall  = W.Button(description='Comparar Ks (métricas)', icon='bar-chart')
w_clear_models = W.Button(description='Limpar modelos', icon='trash')

w_boxplots = W.Button(description='Boxplots por atributo', icon='bar-chart')
w_datagrid_label = W.HTML(value="<b>Camada SOM:</b> <i>—</i>")
w_models_label   = W.HTML(value="<b>Modelos treinados:</b> <i>—</i>")
w_out    = W.Output()

# ============================ CALLBACKS BASE ============================
def refresh_ids(*_):
    ids = _ids_from_mc(w_escala.value, w_filtro.value.strip() or None)
    w_ids.options = ids; w_selall.value = False

def on_selall_change(ch):
    if ch['name']=='value': w_ids.value = tuple(w_ids.options) if ch['new'] else ()

def on_seltest_change(ch):
    if ch['name']=='value': w_test_ids.value = tuple(w_test_ids.options) if ch['new'] else ()

def on_clear_clicked(_):
    w_filtro.value = ''; w_ids.value = ()

def on_load_clicked(_):
    with w_out:
        clear_output()
        if not w_ids.value: print('Selecione ao menos 1 folha.'); return
        print('# Montando grade…')
        quad = Build_mc(escala=w_escala.value, ID=list(w_ids.value), verbose=True)
        print('# Carregando dados brutos…')
        _g, _m = Upload_geof(quad, gama_xyz=w_gama.value, mag_xyz=w_mag.value, extend_size=int(w_ext.value))
        quad = pop_nodata(quad)
        globals()['quadricula'] = quad
        print(f'Folhas ativas: {len(quad)}')
        globals()['data_grid'] = None
        w_datagrid_label.value = "<b>Camada SOM:</b> <i>— (interpole primeiro)</i>"
        som_store.clear(); globals()['som_last_pred']=None; w_models_label.value = "<b>Modelos treinados:</b> <i>—</i>"
        _rescan_from_quadricula()
        print('Pronto. Dados brutos anexados. Agora execute a INTERPOLAÇÃO.')

def on_refresh_clicked(_):
    with w_out:
        clear_output()
        if 'quadricula' not in globals(): print('Carregue dados primeiro.'); return
        _rescan_from_quadricula(); print('Atualizado.')

def on_plot_clicked(_):
    with w_out:
        clear_output()
        if not w_ids.value: print('Selecione ao menos 1 folha.'); return
        if not w_layers.value: print('Nenhuma camada selecionada.'); return
        q = globals().get('quadricula', {})
        for col in w_cols.value:
            _plot_layers_for_column(q, w_ids.value, w_layers.value, col, remove_neg=w_nonegP.value)

def on_interpolar_clicked(_):
    with w_out:
        clear_output()
        if not w_ids.value: print('Selecione ao menos 1 folha.'); return
        feats_grid = list(w_feats_interp.value)
        if not feats_grid: print('Selecione ao menos 1 feature (grid).'); return
        q = globals().get('quadricula', {})
        if not q: print('Carregue dados brutos primeiro.'); return
        print(f"# Interpolando (algo={w_algo.value}, pixel={int(w_psize.value)} m)…")
        out_layer = _interpolate_current_selection(q, w_ids.value, w_gama.value, w_mag.value, feats_grid, int(w_psize.value), w_algo.value, w_nonegI.value)
        globals()['quadricula'] = q; globals()['data_grid'] = out_layer
        w_datagrid_label.value = f"<b>Camada SOM:</b> <code>{out_layer}</code>"
        print(f"→ Camada criada: {out_layer}")
        som_store.clear(); globals()['som_last_pred']=None; w_models_label.value = "<b>Modelos treinados:</b> <i>—</i>"
        _rescan_from_quadricula()
        if out_layer in w_layers.options: w_layers.value = (out_layer,)

def on_train_clicked(_):
    with w_out:
        clear_output()
        feats = list(w_feats.value)
        if not feats: print("Selecione ao menos 1 feature (SOM)."); return
        if not globals().get('data_grid'): print("Interpole a grade primeiro."); return
        layer = globals()['data_grid']; q = globals().get('quadricula', {})
        print(f"[TREINO] Montando matriz global de '{layer}'…")
        X_all, _, _ = _build_matrix_for_fids(q, feats, layer, fids=None)
        imp = SimpleImputer(strategy='median'); X_imp = imp.fit_transform(X_all)
        sca = StandardScaler().fit(X_imp); X_std = sca.transform(X_imp)
        ks = sorted(set(int(k) for k in w_ks_train.value));
        if not ks: print("Escolha ao menos um k."); return
        np.random.seed(int(w_seed.value))
        for k in ks:
            print(f" - SOM(k={k}, sigma={float(w_sigma.value)}, it={int(w_iter.value)})")
            som = SOM(m=int(k), n=1, sigma=float(w_sigma.value), dim=len(feats), max_iter=int(w_iter.value)); som.fit(X_std)
            som_store[k] = {'som': som, 'imp': imp, 'sca': sca, 'feats': feats, 'layer': layer}
        w_models_label.value = f"<b>Modelos treinados:</b> {', '.join(map(str, sorted(som_store.keys())))}"
        w_k_apply.options = sorted(list(som_store.keys()))
        if w_k_apply.options: w_k_apply.value = w_k_apply.options[0]
        print("Modelos treinados.")

def on_apply_clicked(_):
    with w_out:
        clear_output()
        if not som_store: print("Treine um SOM antes."); return
        if not w_test_ids.value: print("Selecione folhas para teste."); return
        k = int(w_k_apply.value); model = som_store.get(k)
        if model is None: print(f"k={k} não encontrado."); return
        feats = model['feats']; layer = model['layer']; q = globals().get('quadricula', {})
        print(f"[TESTE] Subset {len(w_test_ids.value)} folhas / layer '{layer}'…")
        try:
            X_te, slc_te, metas_te = _build_matrix_for_fids(q, feats, layer, fids=w_test_ids.value)
        except RuntimeError as e: print(str(e)); return
        X_te_std = model['sca'].transform(model['imp'].transform(X_te))
        qe = _qe(model['som'], X_te_std); te = _te_1d(model['som'], X_te_std)
        print(pd.DataFrame([{'k':k,'QE_test':qe,'TE_test':te}]).to_string(index=False))
        classes = _predict_per_folha(model['som'], X_te_std, slc_te, metas_te)
        _plot_classes(classes, metas_te, n_clusters=k, flip_ns=bool(w_flip.value),
                      titulo=f"SOM (aplicar) k={k} | sigma={float(w_sigma.value)} | it={int(w_iter.value)} | {layer}")
        globals()['som_last_pred'] = {'k':k, 'classes':classes, 'metas':metas_te, 'fids':tuple(w_test_ids.value), 'feats':tuple(feats), 'layer':layer}
        print("Predição salva: som_last_pred.")

def on_evalall_clicked(_):
    with w_out:
        clear_output()
        if not som_store or not w_test_ids.value: print("Treine/aplique SOM e selecione folhas."); return
        any_k = next(iter(som_store)); feats = som_store[any_k]['feats']; layer = som_store[any_k]['layer']
        q = globals().get('quadricula', {})
        try:
            X_te, slc_te, metas_te = _build_matrix_for_fids(q, feats, layer, fids=w_test_ids.value)
        except RuntimeError as e: print(str(e)); return
        rows=[]
        for k, model in sorted(som_store.items()):
            if model['feats']!=feats or model['layer']!=layer: rows.append({'k':k,'QE_test':np.nan,'TE_test':np.nan,'obs':'incompatível'}); continue
            X_te_std = model['sca'].transform(model['imp'].transform(X_te))
            rows.append({'k':k,'QE_test':_qe(model['som'],X_te_std),'TE_test':_te_1d(model['som'],X_te_std)})
        print(pd.DataFrame(rows).sort_values('QE_test', ascending=True, na_position='last').to_string(index=False))

def on_clear_models_clicked(_):
    som_store.clear(); globals()['som_last_pred']=None
    w_models_label.value = "<b>Modelos treinados:</b> <i>—</i>"; w_k_apply.options=[]
    with w_out: clear_output(); print("Modelos apagados.")

def on_boxplots_clicked(_):
    with w_out:
        clear_output()
        if not som_store or globals().get('som_last_pred') is None:
            print("Treine e aplique um SOM antes."); return
        lp = globals()['som_last_pred']
        k=lp['k']; classes=lp['classes']; metas=lp['metas']; fids=lp['fids']; feats=list(lp['feats']); layer=lp['layer']
        q = globals().get('quadricula', {})
        try:
            df_long = som_build_long_table(q, layer, classes, metas, atributos=feats, fids=fids)
        except RuntimeError as e: print(str(e)); return
        print(f"[Boxplots] {len(fids)} folha(s) | k={k} | layer='{layer}' | atributos={feats}")

        # --- 1) Plot principal: por FEATURE (escala independente; horizontal)
        dfw = df_long.rename(columns={'classe':'som_class'})
        fig, _ = boxplots_por_feature(
            df=dfw,
            features=feats,
            class_col='som_class',
            classes=sorted(dfw['som_class'].unique()),
            ncols=3,
            showfliers=False,
            pclip=(5, 95),
            log=False,
            titulo='Boxplots por feature • escalas independentes (valores no eixo X)'
        )
        display(fig); plt.show()

        # --- 2) Widget interativo para refinar (mesma base)
        print("\nWidget interativo para ajustar features/classes/clip/log:")
        ui = boxplot_widget(
            df=dfw,
            features=feats,
            class_col='som_class',
            titulo='Boxplots por feature • escalas independentes'
        )
        display(ui)

        # --- 3) Alternativa rápida: por classe (compartilha Y por padrão)
        # plot_boxplots_por_atributo(df_long, atributos=feats, ncols=2, showfliers=False)

# liga
w_escala.observe(refresh_ids, names='value')
w_filtro.observe(refresh_ids, names='value')
w_selall.observe(on_selall_change, names='value')
w_seltest.observe(on_seltest_change, names='value')
w_clear.on_click(on_clear_clicked)
w_load.on_click(on_load_clicked)
w_refresh.on_click(on_refresh_clicked)
w_plot.on_click(on_plot_clicked)
w_interpolar.on_click(on_interpolar_clicked)
w_train.on_click(on_train_clicked)
w_apply.on_click(on_apply_clicked)
w_evalall.on_click(on_evalall_clicked)
w_clear_models.on_click(on_clear_models_clicked)
w_boxplots.on_click(on_boxplots_clicked)
refresh_ids()

# ============================ BDC / STAC (INPE) ============================
BDC_ENDPOINT = "https://data.inpe.br/bdc/stac/v1"

def _aoi_bbox_from_ids(escala, ids):
    if not ids: return None
    gdf = import_malha_cartog(escala=escala)
    gdf = gdf[gdf['id_folha'].astype(str).isin([str(i) for i in ids])].copy()
    if gdf.empty: return None
    try: gdf = gdf.to_crs(4326)
    except Exception: pass
    minx,miny,maxx,maxy = gdf.total_bounds
    return [float(minx), float(miny), float(maxx), float(maxy)]

def _bdc_list_collections(pattern=None):
    cli = Client.open(BDC_ENDPOINT)
    cols = [c.id for c in cli.get_collections()]
    if pattern:
        pat = re.compile(pattern, re.IGNORECASE); cols = [c for c in cols if pat.search(c)]
    return sorted(cols)

def _bdc_search_items(collections, bbox, dt_range, cloud_min, cloud_max, limit, sort_dir):
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

def _bdc_preview_thumbs(items, max_show=12):
    n = min(len(items), max_show)
    if n == 0: print("Nenhum item."); return
    ncols = 4; nrows = (n + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(3.4*ncols, 2.8*nrows)); axes = np.atleast_1d(axes).ravel()
    for i in range(n):
        it = items[i]; ax = axes[i]; ax.axis("off")
        pair = _bdc_pick_visual_asset(it)
        title = f"{it.collection_id}\n{getattr(it,'datetime',None).date() if getattr(it,'datetime',None) else '—'}"
        ax.set_title(title, fontsize=9)
        if pair is None: ax.text(0.5,0.5,"sem preview",ha="center",va="center"); continue
        href, _ = pair
        try:
            r = requests.get(href, timeout=15); r.raise_for_status()
            from PIL import Image; from io import BytesIO
            img = Image.open(BytesIO(r.content)); ax.imshow(img)
        except Exception as e:
            ax.text(0.5,0.5,f"erro preview\n{e}",ha="center",va="center",fontsize=8)
    for j in range(i+1, len(axes)): axes[j].axis("off")
    plt.tight_layout(); plt.show()

# -------- Amostragem de bandas na grade --------
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

def _open_remote_raster(href):
    try: return rasterio.open(href)
    except Exception: pass
    if not href.startswith('/vsicurl/'): return rasterio.open('/vsicurl/' + href)
    raise

def _resolve_band_assets(item, bands_text):
    """
    Converte a string de bandas em [(name, href, idxs)].
    Suporta:
      - 'tci'/'visual' (RGB, índices (1,2,3))
      - nomes exatos de assets do item (uma banda)
      - apelidos: red/green/blue -> B4/B3/B2 (ou B04/B03/B02)
      - padrões: B8, band8, B08 etc.
    """
    wanted = [b.strip() for b in str(bands_text).split(',') if b.strip()]
    out = []

    # mapa case-insensitive das chaves de asset
    assets_ci = {k.lower(): k for k in item.assets.keys()}

    def _pick(*keys):
        """Tenta retornar (asset_key_real, href) para a primeira key disponível."""
        for k in keys:
            kk = assets_ci.get(k.lower())
            if kk:
                href = getattr(item.assets[kk], "href", None)
                if href:
                    return kk, href
        return None, None

    for w in wanted:
        lw = w.lower()

        # 1) TCI / VISUAL (RGB)
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
            out.append(('tci', href, (1, 2, 3)))
            continue

        # 2) nome exato do asset
        kk = assets_ci.get(lw)
        if kk:
            href = item.assets[kk].href
            out.append((kk, href, (1,)))
            continue

        # 3) apelidos RGB
        if lw in ('red', 'b4', 'b04', 'band4'):
            k, href = _pick('B4', 'B04', 'red')
            if href:
                out.append(('red', href, (1,)))
                continue

        if lw in ('green', 'b3', 'b03', 'band3'):
            k, href = _pick('B3', 'B03', 'green')
            if href:
                out.append(('green', href, (1,)))
                continue

        if lw in ('blue', 'b2', 'b02', 'band2'):
            k, href = _pick('B2', 'B02', 'blue')
            if href:
                out.append(('blue', href, (1,)))
                continue

        # 4) padrão genérico: B8, B08, band8, band08, etc.
        m = re.fullmatch(r'b(?:and)?0?(\d+)', lw)
        if m:
            n = int(m.group(1))
            k, href = _pick(f'B{n}', f'B{n:02d}')
            if href:
                out.append((f'B{n}', href, (1,)))
                continue

        # 5) não achou
        raise RuntimeError(f"Banda/asset '{w}' não encontrada.")

    return out

def _sample_asset_into_layer(quad, fids, layer_name, href, band_idxs=(1,), prefix='sat'):
    """
    Amostra 1+ bandas do 'href' sobre os pontos (X,Y) do DataFrame 'layer_name'.
    Usa sample() do rasterio (nearest). Colunas criadas: <prefix>, <prefix>_r/g/b, etc.
    """
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
            # amostragem em blocos
            def _batched(xa, ya, bs=200000):
                for i in range(0, xa.size, bs): yield xa[i:i+bs], ya[i:i+bs]
            for j, b in enumerate(band_idxs, 1):
                vals = np.full(df.shape[0], np.nan, dtype='float32'); k = 0
                try:
                    for xb, yb in _batched(xx, yy):
                        pts = list(zip(xb, yb))
                        # rasterio.sample não aceita 'resampling' -> nearest
                        it = ds.sample(pts, indexes=b)  # FIX
                        out = np.fromiter((row[0] for row in it), dtype='float32', count=xb.size)
                        vals[k:k+xb.size] = out; k += xb.size
                except Exception as e:
                    print(f" - {fid}: erro amostrando banda {b} → {e}"); continue
                # nome de coluna
                if len(band_idxs)==3:
                    suffix = ('r','g','b')[j-1] if j<=3 else f'b{j}'
                    col = f"{prefix}_{suffix}"
                elif len(band_idxs)==1:
                    col = f"{prefix}"
                else:
                    col = f"{prefix}_b{b}"
                df[col] = vals.astype('float32', copy=False); ok_cols += 1
        return ok_cols

# -------- Download e cache local de assets STAC --------
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
    # guarda no sat_store
    sat_store[item.id] = {
        'collection': item.collection_id,
        'datetime': getattr(item, 'datetime', None),
        'bbox': getattr(item, 'bbox', None) or getattr(item, 'properties', {}).get('bbox'),
        'assets': assets_local,
        'hrefs': hrefs
    }
    return assets_local

# -------- UI BDC --------
w_bdc_filter = W.Text(placeholder='regex (ex.: landsat|sentinel|cbers)', description='Filtro')
w_bdc_list   = W.Button(description='Listar coleções', icon='list')
w_bdc_cols   = W.SelectMultiple(options=(), rows=8, description='Coleções')

w_bdc_date   = W.Text(value='2018-01-01/2025-12-31', description='Data (UTC)')
w_bdc_cloud  = W.IntRangeSlider(value=[0,100], min=0, max=100, step=1, description='Nuvens (%)')
w_bdc_limit  = W.IntSlider(value=20, min=1, max=200, step=1, description='Limite')
w_bdc_sort   = W.Dropdown(options=[('Mais antigo','asc'),('Mais recente','desc')], value='desc', description='Ordenar')

w_bdc_search = W.Button(description='Buscar itens', icon='search', button_style='info')
w_bdc_prev   = W.Button(description='Thumbnails', icon='image')
w_bdc_save   = W.Button(description='Baixar VISUAL', icon='download')

w_bdc_item    = W.Dropdown(options=(), description='Item', disabled=True)
w_bdc_bands   = W.Text(value='tci', description='Bandas')      # 'tci' | 'B4,B3,B2' | 'B8' | 'red,green,blue'
w_bdc_prefix  = W.Text(value='sat', description='Prefixo')
w_bdc_sample  = W.Button(description='Amostrar item', icon='plus-square', button_style='warning')

# novos botões p/ baixar / amostrar em lote
w_bdc_dl_all  = W.Button(description='Baixar itens (todos)', icon='download', button_style='success')
w_bdc_sm_all  = W.Button(description='Amostrar itens (todos)', icon='plus-square')
w_bdc_out     = W.Output()

def _format_item_label(it, i):
    coll = getattr(it, "collection_id", "") or ""
    dt   = getattr(it, "datetime", None)
    dts  = (dt.date().isoformat() if hasattr(dt, "date") else str(dt)) if dt else "—"
    props = getattr(it, "properties", {}) or {}
    cc = props.get("eo:cloud_cover") or props.get("cloud_cover")
    cc_str = (f"{cc:.0f}%" if isinstance(cc,(int,float)) else "—")
    return f"{i:02d} | {coll} | {dts} | clouds {cc_str}"

def on_bdc_list_clicked(_):
    with w_bdc_out:
        clear_output()
        try:
            cols = _bdc_list_collections(w_bdc_filter.value.strip() or None)
            if not cols: print("Nenhuma coleção encontrada.")
            else:
                w_bdc_cols.options = tuple(cols)
                print(f"{len(cols)} coleção(ões). Selecione e pesquise.")
        except Exception as e:
            print("Erro ao listar coleções:", e)

def on_bdc_search_clicked(_):
    with w_bdc_out:
        clear_output()
        if not w_bdc_cols.value: print("Selecione coleções."); return
        bbox = _aoi_bbox_from_ids(w_escala.value, list(w_ids.value))
        if not bbox: print("Selecione folhas (à esquerda) para definir a AOI)."); return
        print("AOI (bbox WGS84):", bbox)
        try:
            items = _bdc_search_items(
                collections=w_bdc_cols.value, bbox=bbox, dt_range=w_bdc_date.value.strip(),
                cloud_min=w_bdc_cloud.value[0], cloud_max=w_bdc_cloud.value[1],
                limit=int(w_bdc_limit.value), sort_dir=w_bdc_sort.value
            )
        except Exception as e:
            print("Erro na busca STAC:", e); return
        globals()['bdc_items'] = items
        print(f"Encontrados {len(items)} item(ns). Use 'Thumbnails' ou selecione um Item.")
        labels = [_format_item_label(it, i) for i,it in enumerate(items)]
        w_bdc_item.options = list(zip(labels, range(len(items))))
        w_bdc_item.disabled = (len(items)==0)
        if items: w_bdc_item.value = 0

def on_bdc_prev_clicked(_):
    with w_bdc_out: clear_output(); _bdc_preview_thumbs(globals().get('bdc_items', []), max_show=16)

def on_bdc_save_clicked(_):
    with w_bdc_out:
        clear_output()
        items = globals().get('bdc_items', [])
        if not items: print("Faça a busca primeiro."); return
        os.makedirs("satellite_bdc", exist_ok=True)
        saved=[]
        for it in items:
            pair = _bdc_pick_visual_asset(it)
            if not pair: continue
            href, key = pair
            name = os.path.basename(href.split('?')[0])
            fpath = os.path.join("satellite_bdc", f"{it.collection_id}_{it.id}_{key}_{name}")
            try:
                if not os.path.exists(fpath):
                    with requests.get(href, stream=True, timeout=60) as r:
                        r.raise_for_status()
                        with open(fpath,"wb") as f:
                            for ch in r.iter_content(1<<20):
                                if ch: f.write(ch)
                saved.append(fpath)
            except Exception as e:
                print(f"[WARN] Falha ao baixar {href}: {e}")
        if saved:
            print("Arquivos salvos:"); [print(" -",p) for p in saved]
        else:
            print("Nenhum asset visual pôde ser baixado.")

def on_bdc_sample_clicked(_):
    with w_bdc_out:
        clear_output()
        items = globals().get('bdc_items', [])
        if not items: print("Busque itens primeiro."); return
        idx = int(w_bdc_item.value)
        if not (0 <= idx < len(items)): print(f"Índice inválido 0..{len(items)-1}."); return
        if not globals().get('data_grid'): print("Interpole a grade (crie a camada SOM)."); return
        layer = globals()['data_grid']; q = globals().get('quadricula', {})
        fids_target = [fid for fid,blob in q.items() if layer in blob]
        item = items[idx]
        try:
            bands = _resolve_band_assets(item, w_bdc_bands.value)
        except Exception as e:
            print("Bandas:", str(e)); return
        print(f"Amostrando {[b[0] for b in bands]} → '{layer}' em {len(fids_target)} folha(s)…")
        total_cols=0
        for name, href, idxs in bands:
            try:
                cols = _sample_asset_into_layer(q, fids_target, layer_name=layer, href=href, band_idxs=tuple(idxs), prefix=(w_bdc_prefix.value or name))
                total_cols += cols; print(f"  - OK {name}: {cols} coluna(s).")
            except Exception as e:
                print(f"  - {name}: erro → {e}")
        if total_cols==0:
            print("Nenhuma coluna criada (verifique EPSG/GeoTIFF).")
        else:
            globals()['quadricula']=q; _rescan_from_quadricula(); print("Pronto. Novas colunas disponíveis no SOM.")

def on_bdc_dl_all_clicked(_):
    with w_bdc_out:
        clear_output()
        items = globals().get('bdc_items', [])
        if not items: print("Busque itens primeiro."); return
        bands_text = w_bdc_bands.value
        print(f"Baixando {len(items)} item(ns) ({bands_text})…")
        ok=0
        for it in items:
            try:
                local = _download_assets_for_item(it, bands_text, outdir="satellite_bdc")
                print(f" - {it.id}: {list(local.keys())}")
                ok += 1
            except Exception as e:
                print(f" - {it.id}: erro → {e}")
        print(f"Concluído. {ok}/{len(items)} item(ns) armazenados em sat_store.")

def on_bdc_sm_all_clicked(_):
    with w_bdc_out:
        clear_output()
        items = globals().get('bdc_items', [])
        if not items: print("Busque itens primeiro."); return
        if not globals().get('data_grid'): print("Interpole a grade (crie a camada SOM)."); return
        layer = globals()['data_grid']; q = globals().get('quadricula', {})
        fids_target = [fid for fid,blob in q.items() if layer in blob]
        bands_text = w_bdc_bands.value
        print(f"Amostrar TODOS os itens ({len(items)}), bandas={bands_text} → layer '{layer}' …")
        total_cols = 0; it_done = 0
        for it in items:
            try:
                bands = _resolve_band_assets(it, bands_text)
                for name, href, idxs in bands:
                    cols = _sample_asset_into_layer(q, fids_target, layer_name=layer, href=href, band_idxs=tuple(idxs), prefix=(w_bdc_prefix.value or name))
                    total_cols += cols
                it_done += 1
            except Exception as e:
                print(f" - {it.id}: erro → {e}")
        if total_cols==0:
            print("Nenhuma coluna criada (verifique EPSG/GeoTIFF).")
        else:
            globals()['quadricula']=q; _rescan_from_quadricula()
            print(f"OK. {it_done}/{len(items)} itens amostrados; {total_cols} coluna(s) adicionada(s).")

# liga BDC
w_bdc_list.on_click(on_bdc_list_clicked)
w_bdc_search.on_click(on_bdc_search_clicked)
w_bdc_prev.on_click(on_bdc_prev_clicked)
w_bdc_save.on_click(on_bdc_save_clicked)
w_bdc_sample.on_click(on_bdc_sample_clicked)
w_bdc_dl_all.on_click(on_bdc_dl_all_clicked)
w_bdc_sm_all.on_click(on_bdc_sm_all_clicked)

# painel BDC
bdc_controls = W.VBox([
    W.HBox([w_bdc_filter, w_bdc_list]),
    W.HBox([w_bdc_cols]),
    W.HBox([w_bdc_date, w_bdc_cloud, w_bdc_limit, w_bdc_sort]),
    W.HBox([w_bdc_search, w_bdc_prev, w_bdc_save]),
    W.HBox([w_bdc_item, w_bdc_bands, w_bdc_prefix, w_bdc_sample]),
    W.HBox([w_bdc_dl_all, w_bdc_sm_all]),
    w_bdc_out
])

# ============================ LAYOUT FINAL ============================
left = W.VBox([
    W.HBox([w_escala, w_filtro]),
    W.HBox([w_ids, W.VBox([w_selall, w_clear, w_ext, w_gama, w_mag, w_load, w_refresh, w_plot])]),
    W.HTML("<hr><b>Interpolação para grade</b>"),
    W.HBox([w_feats_interp, W.VBox([w_psize, w_algo, w_nonegI, w_interpolar])]),
    w_datagrid_label,
    W.HTML("<hr><b>Imagens de Satélite — BDC/INPE (STAC)</b>"),
    bdc_controls,
])

mid = W.VBox([
    W.HTML("<b>Pré-visualização</b>"),
    W.HBox([w_layers, w_cols]),
    w_nonegP,
    W.HTML("<hr><b>SOM — Treino</b>"),
    w_feats,
    W.HBox([w_sigma, w_iter, w_seed]),
    W.HBox([w_ks_train, w_train]),
    w_models_label
])

right = W.VBox([
    W.HTML("<b>SOM — Teste/Aplicação</b>"),
    W.HBox([w_test_ids, W.VBox([w_seltest, w_k_apply, w_apply, w_evalall, w_flip, w_clear_models, w_boxplots])])
])

ui = W.VBox([W.HBox([left, mid, right]), w_out])
display(ui)

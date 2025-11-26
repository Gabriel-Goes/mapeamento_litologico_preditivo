
# -*- coding: utf-8 -*-
"""
geof_interp_widget.py  —  Utilitários para seleção de folhas, carga de dados geofísicos,
interpolação em mosaico com recorte por folha (sem costura) e exportação GeoTIFF.

Uso típico no Jupyter/IPython:
------------------------------
from geof_interp_widget import (
    ESCALAS, build_selector_widget, interpolate_mosaic_and_update,
    export_geotiff_stack, save_all_stacks, run_workflow_quick
)

# 1) Constrói os widgets (opcional, se quiser interface)
widgets = build_selector_widget()

# 2) Ou roda rápido via função (sem widgets):
mc, quadricula = run_workflow_quick(
    escala="100k",
    ids=["SF23_YB_I","SF23_YB_II","SF23_YB_III","SF23_YB_IV","SF23_YB_V","SF23_YB_VI"],
    gama="gama_line_1105", mag="mag_line_1105", extend_size=600
)

# 3) Interpola no mosaico e recorta por folha (encaixe perfeito nas arestas)
value_fields = { "gama_line_1105": "TC", "mag_line_1105": "TMI" }
quadricula = interpolate_mosaic_and_update(
    quadricula, value_fields, folhas_gdf=mc, epsg=mc.crs.to_epsg() if mc.crs else None,
    spacing=100.0, reduce_spacing=500.0, buffer_m=600.0, dtype="float32", nodata=float("nan")
)

# 4) Exporta 1 GeoTIFF por folha (stack com as bandas na ordem dos canais)
save_all_stacks(quadricula, canais=["gama_line_1105","mag_line_1105"], outdir="out_tif")

Requisitos do seu ambiente/projeto:
-----------------------------------
- Funções utilitárias já existentes no seu projeto:
  import_malha_cartog(escala, IDs=None)
  Build_mc(escala, ID, verbose=False)
  Upload_geof(quadricula, gama_xyz, mag_xyz, extend_size=...)
  pop_nodata(quadricula)
- Bibliotecas: numpy, pandas, geopandas, shapely, rasterio, verde, ipywidgets (opcional p/ UI).
"""
from __future__ import annotations

# ==== Imports essenciais ====
import os
import re
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

import geopandas as gpd
import pyproj
from shapely.ops import unary_union

import rasterio
from rasterio import features, windows
from rasterio.transform import from_origin

import verde as vd

# Importa do seu projeto (precisa estar no PYTHONPATH do kernel)
# Ex.: sys.path.append("/caminho/do/seu/projeto") se necessário.
from src import *  # noqa

# ==== Constantes ====
ESCALAS = ['25k','50k','100k','250k','1kk']


# ---------------------------------------------------------------------------
# Seleção de folhas + widgets (opcional)
# ---------------------------------------------------------------------------

def _ids_from_mc(escala: str, filtro_regex: str|None = None) -> List[str]:
    mc = import_malha_cartog(escala=escala)
    col_id = None
    for cand in ("id_folha", "codigo", "ID", "id", "sheet", "folha"):
        if cand in mc.columns:
            col_id = cand
            break
    if col_id is None:
        raise KeyError(f"Não encontrei coluna de ID em {list(mc.columns)}")
    ids = mc[col_id].astype(str).tolist()
    if filtro_regex:
        pat = re.compile(filtro_regex, re.IGNORECASE)
        ids = [i for i in ids if pat.search(i)]
    return sorted(ids)


def build_selector_widget():
    """
    Constrói os widgets de seleção e ligações de callbacks.
    Retorna um dict com {'widgets': ..., 'state': ...}.
    A variável global 'quadricula' é atualizada ao clicar em 'Carregar dados'.
    """
    try:
        import ipywidgets as W
        import matplotlib.pyplot as plt
        from IPython.display import display, clear_output
    except Exception as e:
        raise RuntimeError("ipywidgets/matplotlib não disponível neste kernel.") from e

    # --- widgets ---
    w_escala = W.Dropdown(options=ESCALAS, value='100k', description='Escala')
    w_filtro = W.Text(placeholder='ex.: SF23_YB', description='Filtro')
    w_ids    = W.SelectMultiple(options=(), rows=10, description='Folhas')
    w_selall = W.ToggleButton(value=False, description='Selecionar tudo', icon='check')
    w_clear  = W.Button(description='Limpar', icon='trash')
    w_ext    = W.IntSlider(min=0, max=2000, step=100, value=600, description='extend_size')
    w_gama   = W.Dropdown(options=['gama_line_1105','gama_line_1089','gama_1039','gama_3022'], value='gama_line_1105', description='Gama')
    w_mag    = W.Dropdown(options=['mag_line_1105','mag_line_1089','mag_1039','mag_3022'], value='mag_line_1105', description='Mag')
    w_load   = W.Button(description='Carregar dados', button_style='success', icon='download')
    w_plot   = W.Button(description='Pré-visualizar', icon='eye')
    w_out    = W.Output()

    def refresh_ids(*_):
        try:
            ids = _ids_from_mc(w_escala.value, w_filtro.value.strip() or None)
        except Exception as e:
            ids = []
            with w_out:
                print("Falha ao listar IDs:", e)
        w_ids.options = ids
        w_selall.value = False

    def on_selall_change(change):
        if change['name'] == 'value':
            if change['new']:
                w_ids.value = tuple(w_ids.options)
            else:
                w_ids.value = ()

    def on_clear_clicked(_):
        w_filtro.value = ''
        w_ids.value = ()

    def plot_preview(ids):
        mc = import_malha_cartog(escala=w_escala.value, IDs=list(ids))
        import matplotlib.pyplot as plt
        plt.figure(figsize=(10,6))
        ax = mc.boundary.plot(color='k', linewidth=1)
        labels = mc.representative_point()
        id_col = 'id_folha' if 'id_folha' in mc.columns else (
            'codigo' if 'codigo' in mc.columns else mc.columns[0]
        )
        for i, row in mc.iterrows():
            xy = labels.loc[i].xy
            ax.text(xy[0][0], xy[1][0], str(row[id_col]), fontsize=7, ha='center')
        ax.set_aspect('equal')
        plt.title(f'{len(mc)} folha(s) – {w_escala.value}')
        plt.show()

    def on_plot_clicked(_):
        with w_out:
            clear_output()
            if not w_ids.value:
                print('Selecione ao menos 1 folha.')
                return
            plot_preview(w_ids.value)

    def on_load_clicked(_):
        with w_out:
            clear_output()
            if not w_ids.value:
                print('Selecione ao menos 1 folha.')
                return
            print('# Montando grade…')
            quad = Build_mc(escala=w_escala.value, ID=list(w_ids.value), verbose=True)
            print('# Carregando geofísica…')
            gdf_gama, gdf_mag = Upload_geof(
                quad, gama_xyz=w_gama.value, mag_xyz=w_mag.value, extend_size=int(w_ext.value)
            )
            quad = pop_nodata(quad)
            print(f'Folhas ativas: {len(quad)}')
            # preview opcional
            try:
                import matplotlib.pyplot as plt
                plt.figure(figsize=(12,9))
                for fid in quad:
                    if w_gama.value in quad[fid]:
                        df = quad[fid][w_gama.value]
                        if all(k in df.columns for k in ("X","Y")):
                            plt.scatter(df.X, df.Y, s=0.05, c="k", alpha=0.2)
                plt.axis('scaled'); plt.title('Preview nuvem de pontos (gama)')
                plt.show()
            except Exception as e:
                print('Preview não disponível:', e)
            # atualiza variável global e estado
            globals()['quadricula'] = quad
            state['quadricula'] = quad
            state['gama'] = w_gama.value
            state['mag']  = w_mag.value
            print('Pronto. Variável global `quadricula` atualizada.')

    # ligações
    w_escala.observe(refresh_ids, names='value')
    w_filtro.observe(refresh_ids, names='value')
    w_selall.observe(on_selall_change, names='value')
    w_clear.on_click(on_clear_clicked)
    w_plot.on_click(on_plot_clicked)
    w_load.on_click(on_load_clicked)

    # inicializa
    refresh_ids()

    ui = W.VBox([
        W.HBox([w_escala, w_filtro]),
        W.HBox([w_ids, W.VBox([w_selall, w_clear, w_ext, w_gama, w_mag, w_plot, w_load])]),
        w_out
    ])
    display(ui)

    state = {'quadricula': None, 'gama': None, 'mag': None}
    return {'widgets': dict(
                escala=w_escala, filtro=w_filtro, ids=w_ids, selall=w_selall,
                clear=w_clear, ext=w_ext, gama=w_gama, mag=w_mag,
                load=w_load, plot=w_plot, out=w_out
            ),
            'state': state
           }


# ---------------------------------------------------------------------------
# Interpolação no mosaico + recorte por folha (sem costura)
# ---------------------------------------------------------------------------

def _parse_epsg_from_obj(obj):
    """Extrai um EPSG de várias formas comuns."""
    try:
        if obj is None:
            return None
        if isinstance(obj, (int, np.integer)):
            return int(obj)
        if isinstance(obj, str):
            digs = ''.join(ch for ch in obj if ch.isdigit())
            return int(digs) if digs else None
        # CRS do rasterio/pyproj/geopandas
        if hasattr(obj, "to_epsg"):
            return obj.to_epsg()
        if hasattr(obj, "epsg"):
            return int(obj.epsg) if obj.epsg is not None else None
    except Exception:
        pass
    return None


def _detect_epsg(quadricula: Dict, folhas_gdf: gpd.GeoDataFrame|None = None, fallback=None) -> int:
    """Descobre 1 EPSG válido a partir da quadricula, do GeoDataFrame ou de um fallback."""
    # 1) tentar no GeoDataFrame da malha
    if folhas_gdf is not None:
        epsg = _parse_epsg_from_obj(getattr(folhas_gdf, "crs", None))
        if epsg:
            return epsg
        if "epsg" in folhas_gdf.columns:
            vals = set(int(v) for v in folhas_gdf["epsg"].dropna().unique())
            if len(vals) == 1:
                return vals.pop()
    # 2) tentar na estrutura da quadricula
    for rec in quadricula.values():
        if not isinstance(rec, dict):
            continue
        for key in ("epsg", "EPSG", "crs", "CRS", "srid", "meta"):
            v = rec.get(key)
            if isinstance(v, dict):
                for k2 in ("epsg", "EPSG", "srid", "crs"):
                    epsg = _parse_epsg_from_obj(v.get(k2))
                    if epsg:
                        return epsg
            else:
                epsg = _parse_epsg_from_obj(v)
                if epsg:
                    return epsg
    # 3) fallback explícito
    epsg = _parse_epsg_from_obj(fallback)
    if epsg:
        return epsg
    raise ValueError(
        "EPSG não encontrado. Passe epsg=32723 (ex.) e/ou forneça folhas_gdf=import_malha_cartog(...)."
    )


def _folhas_geoms_utm(folhas_gdf: gpd.GeoDataFrame, epsg_target: int) -> List[Tuple[str, object]]:
    """
    Retorna lista [(fid, geom_utm)] a partir do GeoDataFrame da malha.
    Supõe coluna 'id_folha' (ajusta automaticamente para 'codigo' ou outra).
    """
    if folhas_gdf is None:
        raise ValueError("folhas_gdf=None")
    gdf = folhas_gdf.copy()
    if gdf.crs is None:
        raise ValueError("folhas_gdf.crs está None; defina o CRS da malha.")
    if _parse_epsg_from_obj(gdf.crs) != epsg_target:
        gdf = gdf.to_crs(epsg=epsg_target)

    id_col = None
    for cand in ("id_folha", "codigo", "ID", "id", "sheet", "folha"):
        if cand in gdf.columns:
            id_col = cand; break
    if id_col is None:
        raise KeyError(f"Não encontrei coluna de ID em {list(gdf.columns)}")

    out = []
    for _, row in gdf.iterrows():
        fid = str(row.get(id_col))
        out.append((fid, row.geometry))
    return out


def _mosaic_region_from_geoms(geoms: List[Tuple[str, object]], buffer_m: float) -> Tuple[float,float,float,float]:
    union = unary_union([g for _, g in geoms])
    minx, miny, maxx, maxy = union.bounds
    return (minx - buffer_m, maxx + buffer_m, miny - buffer_m, maxy + buffer_m)


def _make_transform(region, spacing):
    w, e, s, n = region
    nx = int(np.floor((e - w)/spacing)) + 1
    ny = int(np.floor((n - s)/spacing)) + 1
    transform = from_origin(w, n, spacing, spacing)  # origem canto superior esquerdo
    shape = (ny, nx)
    return transform, shape


def _label_raster(geoms: List[Tuple[str, object]], transform, shape):
    """Rasteriza TODAS as folhas de uma vez, gerando um rótulo inteiro por folha."""
    idx_by_fid = {fid: i+1 for i, (fid, _) in enumerate(sorted(geoms, key=lambda x: x[0]))}
    shapes = [ (g, idx_by_fid[fid]) for fid, g in geoms ]
    labels = features.rasterize(
        shapes=shapes, out_shape=shape, transform=transform,
        fill=0, all_touched=False, dtype='uint32'
    )
    return labels, idx_by_fid


def _resolve_value_column(df: pd.DataFrame, preferred: str, canal: str) -> str:
    """
    Retorna o nome REAL da coluna de valor no df: tenta match exato, case-insensitive,
    sinônimos por canal e heurística (numérica de maior variância).
    """
    cols = list(df.columns)
    lowmap = {c.lower(): c for c in cols}

    # 1) preferido exato
    if preferred in df.columns:
        return preferred
    # 2) case-insensitive
    if preferred and preferred.lower() in lowmap:
        return lowmap[preferred.lower()]

    # 3) sinônimos por canal
    canal_l = (canal or "").lower()
    if "gama" in canal_l:
        synonyms = ["tc","total_count","totalcount","counts","count","gamma","gama","val","value","z","mdt"]
    elif "mag" in canal_l:
        synonyms = ["tmi","mag","mag_total","totalmag","intensity","bz","b","val","value","z"]
    else:
        synonyms = ["val","value","z","mdt","tmi","tc","mag"]

    for s in synonyms:
        if s in lowmap:
            return lowmap[s]

    # 4) heurística em numéricas
    num_cols = [c for c in df.select_dtypes(include=[np.number]).columns
                if c.lower() not in ("x","y","lon","lat","easting","northing")]
    if len(num_cols) == 1:
        return num_cols[0]
    if len(num_cols) > 1:
        col = max(num_cols, key=lambda c: df[c].astype("float64").std(skipna=True))
        return col

    raise KeyError(f"Não encontrei coluna de valor em {list(df.columns)} para canal='{canal}' (preferido='{preferred}').")


def _collect_xyz(quadricula: Dict, channel: str, value_col: str):
    """Concatena X,Y,Z de todas as folhas para um 'channel', resolvendo a coluna Z de forma robusta."""
    xs, ys, zs = [], [], []
    nrows = 0
    chosen_cols = set()

    for fid, rec in quadricula.items():
        if not isinstance(rec, dict):
            continue
        item = rec.get(channel)
        # ignora entradas que não são DataFrame (ex.: __mosaic__)
        if item is None or not isinstance(item, pd.DataFrame):
            continue
        df = item

        # Garantir X/Y com case-insensitive
        for c in ("X","Y"):
            if c not in df.columns:
                lower = {k.lower(): k for k in df.columns}
                if c.lower() in lower:
                    df = df.rename(columns={lower[c.lower()]: c})
                else:
                    raise KeyError(f"DataFrame da folha {fid} do canal '{channel}' não possui coluna '{c}'. Colunas: {list(df.columns)}")

        zcol = _resolve_value_column(df, value_col, channel)
        chosen_cols.add(zcol)

        xs.append(df["X"].to_numpy())
        ys.append(df["Y"].to_numpy())
        zs.append(df[zcol].to_numpy())
        nrows += len(df)

    if nrows == 0:
        raise ValueError(f"Nenhuma folha possui dados para '{channel}'.")

    # log amigável do que foi usado
    if (value_col not in chosen_cols) or (len(chosen_cols) > 1):
        print(f"  [info] Canal '{channel}': coluna preferida='{value_col}', usadas={sorted(chosen_cols)}")

    x = np.concatenate(xs).astype('float64', copy=False)
    y = np.concatenate(ys).astype('float64', copy=False)
    z = np.concatenate(zs).astype('float64', copy=False)
    return x, y, z


def interpolate_mosaic_and_update(
    quadricula: Dict,
    canais: Dict[str, str],          # {canal_nome: value_col}
    folhas_gdf: gpd.GeoDataFrame,    # malha das folhas selecionadas
    epsg=None,                       # int ou "EPSG:xxxx" (opcional)
    spacing: float = 100.0,
    reduce_spacing: float = 100.0,
    damping: float = 1e-10,
    mindist: float = 500.0,
    buffer_m: float = 600.0,
    dtype: str = 'float32',
    nodata: float = float("nan")
) -> Dict:
    """
    Interpola cada canal no mosaico (único grid) e recorta por folha via label raster.
    Salva em quadricula[fid][f"{canal}__interp"] = dict(array, transform, crs, spacing, nodata).
    Guarda metadados do mosaico em quadricula["__mosaic__"][canal].
    """
    # 0) EPSG
    epsg = _detect_epsg(quadricula, folhas_gdf=folhas_gdf, fallback=epsg)

    # 1) Geometrias e região do mosaico
    geoms = _folhas_geoms_utm(folhas_gdf, epsg_target=epsg)
    region = _mosaic_region_from_geoms(geoms, buffer_m=buffer_m)

    # 2) Grid base + labels
    transform, shape = _make_transform(region, spacing)
    w, e, s, n = region
    xs = np.linspace(w, e, shape[1], dtype='float64')
    ys = np.linspace(n, s, shape[0], dtype='float64')  # top->down
    labels, idx_by_fid = _label_raster(geoms, transform, shape)
    fid_by_idx = {idx: fid for fid, idx in idx_by_fid.items()}

    # 3) Interpola por canal no mosaico e recorta por folha
    for canal, value_col in canais.items():
        print(f"\n[interp] Canal: {canal} • valor='{value_col}'")
        X, Y, Z = _collect_xyz(quadricula, canal, value_col)

        reducer = vd.BlockReduce(reduction=np.median, spacing=reduce_spacing)
        res = reducer.filter((X, Y), Z)
        # Support Verde return signatures:
        # v1.x often returns (coords, data); older may return (x, y, data)
        if isinstance(res, tuple) and len(res) == 2:
            (coords_r, zr) = res
            xr, yr = coords_r
        else:
            xr, yr, zr = res
        print(f"  pontos: {len(Z):,} → reduzidos: {len(zr):,}")

        spline = vd.Spline(damping=damping, mindist=mindist).fit((xr, yr), zr)

        grid_x, grid_y = np.meshgrid(xs, ys)
        grid_vals = spline.predict((grid_x.ravel(), grid_y.ravel())).reshape(shape).astype(dtype, copy=False)

        # Recorte por folha via labels
        for idx in np.unique(labels):
            if idx == 0:
                continue
            fid = fid_by_idx[idx]
            mask = (labels == idx)
            if not mask.any():
                continue

            rows, cols = np.where(mask)
            r0, r1 = rows.min(), rows.max()
            c0, c1 = cols.min(), cols.max()
            win = windows.Window.from_slices((r0, r1+1), (c0, c1+1))
            subarr = grid_vals[r0:r1+1, c0:c1+1].copy()
            submask = mask[r0:r1+1, c0:c1+1]
            subarr[~submask] = nodata
            sub_transform = rasterio.windows.transform(win, transform)

            rec = quadricula.setdefault(fid, {})
            rec[f"{canal}__interp"] = {
                "array": subarr,
                "transform": sub_transform,
                "crs": f"EPSG:{epsg}",
                "spacing": float(spacing),
                "nodata": float(nodata),
            }

        # metadados do mosaico (sem reatribuir quadricula!)
        m = quadricula.setdefault("__mosaic__", {})
        m[canal] = {
            "region": region, "transform": transform, "shape": shape,
            "crs": f"EPSG:{epsg}", "spacing": float(spacing)
        }

    return quadricula


# ---------------------------------------------------------------------------
# Export GeoTIFF (stack por folha)
# ---------------------------------------------------------------------------

def report_interpolation_status(quadricula: dict, canais: list[str]) -> None:
    """
    Mostra quais folhas possuem as chaves '<canal>__interp' geradas.
    Útil para depurar antes de exportar.
    """
    canais = list(canais)
    for fid, rec in quadricula.items():
        if fid == "__mosaic__":
            continue
        missing = [c for c in canais if f"{c}__interp" not in rec]
        if missing:
            print(f"- {fid}: faltando {missing}")
        else:
            print(f"- {fid}: OK ({', '.join(canais)})")

def export_geotiff_stack(
    quadricula: Dict,
    fid: str,
    canais: List[str],
    outpath: str,
    compress: str = "DEFLATE"
) -> str:
    """
    Exporta 1 GeoTIFF com múltiplas bandas (uma por canal) para uma folha (fid).
    Espera que cada canal tenha sido salvo como f"{canal}__interp".
    """
    # coleta arrays e valida shapes/transform/crs
    first = None
    bands = []
    for canal in canais:
        key = f"{canal}__interp"
        if key not in quadricula[fid]:
            raise KeyError(f"Folha {fid} não possui '{key}'. Rode a interpolação primeiro.")
        meta = quadricula[fid][key]
        arr = meta["array"]
        tr  = meta["transform"]
        crs = meta["crs"]
        nod = meta["nodata"]
        if first is None:
            first = (arr.shape, tr, crs, nod)
        else:
            if arr.shape != first[0]:
                raise ValueError(f"Shape diferente em '{key}' (got {arr.shape}, expected {first[0]}).")
            if (tr.a != first[1].a) or (tr.e != first[1].e) or (tr.c != first[1].c) or (tr.f != first[1].f):
                # compara campos principais do Affine
                raise ValueError("Transform diferente entre canais.")
            if crs != first[2]:
                raise ValueError(f"CRS diferente entre canais: {crs} vs {first[2]}.")
        bands.append((canal, arr))

    if first is None:
        raise ValueError("Nenhum canal válido encontrado para export.")
    (height, width), transform, crs, nodata = (first[0], first[1], first[2], first[3])

    outpath = str(outpath)
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": len(bands),
        "dtype": str(bands[0][1].dtype),
        "crs": crs,
        "transform": transform,
        "tiled": True,
        "compress": compress,
        "nodata": nodata,
    }
    with rasterio.open(outpath, "w", **profile) as dst:
        for i, (name, arr) in enumerate(bands, start=1):
            dst.write(arr, i)
            dst.set_band_description(i, name)
    return outpath


def save_all_stacks(quadricula: Dict, canais: List[str], outdir: str, skip_missing: bool = True, verbose: bool = True) -> List[str]:
    """
    Salva um GeoTIFF por folha com as bandas de 'canais' na ordem fornecida.
    Ignora a chave especial '__mosaic__'.
    """
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    paths = []
    for fid in quadricula.keys():
        if fid == "__mosaic__":
            continue
        missing = [c for c in canais if f"{c}__interp" not in quadricula[fid]]
        if missing:
            if skip_missing:
                if verbose:
                    print(f"[skip] {fid}: faltando {missing}")
                continue
            else:
                raise KeyError(f"Folha {fid} sem {missing}. Rode a interpolação para todos os canais.")
        outpath = outdir / f"{fid}_stack.tif"
        p = export_geotiff_stack(quadricula, fid, canais, outpath)
        if verbose:
            print(f"[ok] {fid} → {outpath}")
        paths.append(p)
    return paths


# ---------------------------------------------------------------------------
# Execução rápida sem widgets (conveniência)
# ---------------------------------------------------------------------------

def run_workflow_quick(
    escala: str,
    ids: List[str],
    gama: str,
    mag: str,
    extend_size: int = 600,
    verbose: bool = True
):
    """
    Monta a grade (Build_mc), carrega geofísica (Upload_geof) e retorna (mc, quadricula).
    """
    if verbose:
        print("# Montando grade…")
    quad = Build_mc(escala=escala, ID=list(ids), verbose=verbose)
    if verbose:
        print("# Carregando geofísica…")
    _gdf_gama, _gdf_mag = Upload_geof(quad, gama_xyz=gama, mag_xyz=mag, extend_size=int(extend_size))
    quad = pop_nodata(quad)
    if verbose:
        print(f"Folhas ativas: {len(quad)}")
    mc = import_malha_cartog(escala=escala, IDs=list(ids))
    return mc, quad

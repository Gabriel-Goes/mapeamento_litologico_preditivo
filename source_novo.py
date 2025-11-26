import re
import geopandas as gpd
import ipywidgets as W
from IPython.display import display, clear_output
import matplotlib.pyplot as plt
from src import *

# --- util: lista de escalas disponíveis no seu geopackage ---
ESCALAS = ['25k','50k','100k','250k','1kk']

def _ids_from_mc(escala, filtro_regex=None):
    mc = import_malha_cartog(escala=escala)
    ids = mc['id_folha'].astype(str).tolist()
    if filtro_regex:
        pat = re.compile(filtro_regex, re.IGNORECASE)
        ids = [i for i in ids if pat.search(i)]
    return sorted(ids)

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
    ids = _ids_from_mc(w_escala.value, w_filtro.value.strip() or None)
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
    plt.figure(figsize=(10,6))
    ax = mc.boundary.plot(color='k', linewidth=1)
    labels = mc.representative_point()
    for i, row in mc.iterrows():
        xy = labels.loc[i].xy
        ax.text(xy[0][0], xy[1][0], row['id_folha'], fontsize=7, ha='center')
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
        quadricula = Build_mc(escala=w_escala.value, ID=list(w_ids.value), verbose=True)
        print('# Carregando geofísica…')
        gdf_gama, gdf_mag = Upload_geof(quadricula, gama_xyz=w_gama.value, mag_xyz=w_mag.value, extend_size=int(w_ext.value))
        quadricula = pop_nodata(quadricula)
        print(f'Folhas ativas: {len(quadricula)}')
        # preview rápida do MDT da gama (se houver)
        try:
            plt.figure(figsize=(12,9))
            for fid in quadricula:
                if w_gama.value in quadricula[fid]:
                    df = quadricula[fid][w_gama.value]
                    plt.scatter(df.X, df.Y, c=df.MDT, s=0.1, cmap='terrain', marker='H')
            plt.axis('scaled'); plt.title('Preview MDT (gama)')
            plt.show()
        except Exception as e:
            print('Preview não disponível:', e)
        # guarda em variável global se você quiser reaproveitar
        globals()['quadricula'] = quadricula
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

import os
import matplotlib.pyplot as plt
import pygmt
import geopandas as gpd


# funções e variáveis úteis podem ser adicionadas aqui conforme necessário
# Configura diretório da base de dados

'''
        # Atualizar labelFolhaEstudo
        self.frameSeletor.atualizarLabelFolhaEstudo(self.folhaEstudo)
'''

# Configura delimitador para prints de relatorio de execução
delimt = '------------------------------------------------------\n'


# configura PostgreSQL para conexão
gdb_url = 'postgresql+psycopg2://postgres:postgres@localhost:5432/geodatabase'


def set_db(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/database/'
        # $HOME/database/

        path : caminho até o  arquivo desejado
    '''
    _DBpath = '/home/database/' + path

    return _DBpath


# Lista os arquivos de um diretório
def list_files(path):
    '''
    Lista os arquivos de um diretório
    '''
    return os.listdir(path)


# Criar gerador de intervalos
def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step


def get_epsg(folha_id):
    if folha_id.startswith('S'):
        return '327' + folha_id[2:4]
    else:
        return '326' + folha_id[2:4]


# define geometria do Brasil
ibge = set_db('shapefiles/IBGE/')
regioes = gpd.read_file(ibge + 'ANMS2010_06_grandesregioes.shp')
brasil = regioes.unary_union


def plotar(folhas, carta):
    '''
    Plota as folhas de cartas.
    '''
    fig, ax = plt.subplots()
    for folha_id, poligono in folhas.items():
        print(f' Folha: {folha_id}')
        print(f' Poligono: {poligono}')
        x, y = poligono['geometry'].exterior.xy
        ax.plot(x, y, color='#6699cc', alpha=0.7, linewidth=0.3,
                solid_capstyle='round', zorder=2)
        centro = poligono['geometry'].centroid
        ax.annotate(folha_id, (centro.x, centro.y), color='black',
                    weight='bold', fontsize=6, ha='center', va='center')

    ax.set_title(f'Folhas da Carta {meta_cartas[carta]["escala"]}')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_xlim(-80, -40)
    ax.set_ylim(-70, 10)
    ax.axis('scaled')
    plt.show()


def plotarInicial():
    '''
    Com pygmt visualiza a carta de 1:1.000.000.
    Plota a carta de 1:1.000.000.
    '''
    print(' Iniciando plotagem da carta de 1:1.000.000.')
    print('---------------------------------------------------')
    fig = pygmt.Figure()
    fig.basemap(region=[-80, -40, -70, 10], projection='M10i', frame=True)
    fig.coast(land='black', water='skyblue')
    fig.show()

    print('---------------------------------------------------')

    return fig


meta_cartas = {
    '1kk': {'escala': '1:1.000.000',
            'incrementos': (4, 6),
            'codigos': ['A', 'B', 'C', 'D', 'E', 'F', 'G',
                        'H', 'I', 'J', 'K', 'L', 'M', 'N',
                        'O', 'P', 'Q', 'R', 'S', 'T']},
    '500k': {'escala': '1:500.000',
             'incrementos': (2, 3),
             'codigos': [['V', 'Y'], ['X', 'Z']]},
    '250k': {'escala': '1:250.000',
             'incrementos': (1, 1.5),
             'codigos': [['A', 'C'], ['B', 'D']]},
    '100k': {'escala': '1:100.000',
             'incrementos': (0.5, 0.5),
             'codigos': [['I', 'IV'], ['II', 'V'], ['III', 'VI']]},
    '50k': {'escala': '1:50.000',
            'incrementos': (0.25, 0.25),
            'codigos': [['1', '3'], ['2', '4']]},
    '25k': {'escala': '1:25.000',
            'incrementos': (0.125, 0.125),
            'codigos': [['NW', 'SW'], ['NE', 'SE']]}
}

reverse_meta_cartas = {meta_cartas[k]['escala']: k for k in meta_cartas}


'''
def carregar_mapa_folium(self):
    mapa_html = criar_mapa_folium()
    print(f' Mapa HTML: {mapa_html}')
    html_frame = HtmlFrame(self.plot_frame, horizontal_scrollbar="auto",
                            vertical_scrollbar="auto",
                            width=1200, height=800)
    with open(mapa_html, 'r') as f:
        html = f.read()
    html_frame.set_content(html)
    html_frame.place(relx=0.5, rely=0.5, anchor='center')
    print('Mapa carregado')

# [print(f" --> carta: {k}: {v}\n") for k, v in meta_cartas.items()]



# Obter a camada ativa e a geometria selecionada
layer = iface.activeLayer()
selected_features = layer.selectedFeatures()
selected_geom = selected_features[0].geometry()  # Assume que apenas uma geometria está selecionada

# Conectar ao banco de dados e realizar a consulta
from qgis.core import QgsDataSourceUri, QgsVectorLayer

uri = QgsDataSourceUri()
uri.setConnection("localhost", "5432", "geodatabase", "usuario", "senha")
uri.setDataSource("public", "folhas_cartograficas", "wkb_geometry", "escala = '25k' AND ST_Intersects(wkb_geometry, '{}')".format(selected_geom.asWkt()))

folhas_layer = QgsVectorLayer(uri.uri(), "Folhas Intersectadas", "postgres")
QgsProject.instance().addMapLayer(folhas_layer)

'''

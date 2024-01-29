import os
import matplotlib.pyplot as plt
import geopandas as gpd


# funções e variáveis úteis podem ser adicionadas aqui conforme necessário
# Configura diretório da base de dados
def set_gdb(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/database/'
        # $HOME/database/

        path : caminho até o  arquivo desejado
    '''
    gdb = '/home/ggrl/database/' + path
    return gdb


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


# define geometria do Brasil
ibge = set_gdb('shapefiles/IBGE/')
regioes = gpd.read_file(ibge + 'ANMS2010_06_grandesregioes.shp')
brasil = regioes.unary_union


def plotar(folhas, carta):
    '''
    Plota as folhas de cartas.
    '''
    fig, ax = plt.subplots()
    for folha_id, poligono in folhas.items():
        x, y = poligono['geometry'].exterior.xy
        ax.plot(x, y, color='#6699cc', alpha=0.7, linewidth=0.3,
                solid_capstyle='round', zorder=2)
        centro = poligono['geometry'].centroid
        ax.annotate(folha_id, (centro.x, centro.y), color='black',
                    weight='bold', fontsize=6, ha='center', va='center')

    for geom in brasil.geoms:
        x, y = geom.exterior.xy
        ax.plot(x, y, color='black', alpha=0.7, linewidth=0.3,
                solid_capstyle='round', zorder=2)

    ax.set_title(f'Folhas da Carta {cartas[carta]["escala"]}')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_xlim(-180, 180)
    ax.set_ylim(-80, 80)
    ax.axis('scaled')
    plt.show()


cartas = {
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

[print(f" --> carta: {k}: {v}\n") for k, v in cartas.items()]

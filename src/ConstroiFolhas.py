# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Esta classe é responsável por criar geometrias de folhas de cartas de acordo
# com a escala, salvar cada uma das cartas como uma layer em um geoPackage.
# Ela só será executada apenas uma vez para criar as folhas de cartas e o
# geopackage.

# ------------------------------ IMPORTS ------------------------------------
import math
import geopandas as gpd
from geodatasets import get_path
import matplotlib.pyplot as plt
from tqdm import tqdm
import fiona
from shapely.geometry import mapping, Polygon
from fiona.crs import CRS

from utils import set_gdb, float_range


# define geometria do Brasil
path = get_path('natural_earth.land')
world = gpd.read_file(path)

brasil = world[world['name'] == 'Brazil']


escalas = {
    '1kk': '1:1.000.000',
    '500k': '1:500.000',
    '250k': '1:250.000',
    '100k': '1:100.000',
    '50k':  '1:50.000',
    '25k':  '1:25.000',
}


# ------------------------------ CLASSES ------------------------------------
class CartografiaSistematica:
    '''
    Esta classe é responsável por criar as folhas de cartas de acordo com a
    escala.

    Exemplo:
        cs = CartografiaSistematica()
        cs.criar_folhas_de_cartas('1kk')
        carta_1kk = cs.folhas
        cs.criar_folhas_de_cartas('500k')
        carta_500k = cs.folhas
        cs.criar_folhas_de_cartas('250k')
        folhas_250k = cs.folhas
        cs.criar_folhas_de_cartas('100k')
        carta_100k = cs.folhas
        cs.criar_folhas_de_cartas('50k')
        carta_50k = cs.folhas
        cs.criar_folhas_de_cartas('25k')
        carta_25k = cs.folhas

        # lista de cartas
        lista_cartas = [carta_1kk, carta_500k, carta_250k,
                        carta_100k, carta_50k, carta_25k]

        # Salvar folhas de cartas
        [cs.salvar_folhas_de_cartas(carta) for carta in lista_cartas]

    '''

    # Construtor da classe CartografiaSistematica
    def __init__(self):
        self.folhas = {}
        self.carta = None
        print('Cartografia Sistematica')
        print('-----------------------')
        print('1kk: 1:1.000.000')
        print('500k: 1:500.000')
        print('250k: 1:250.000')
        print('100k: 1:100.000')
        print('50k: 1:50.000')
        print('25k: 1:25.000')
        print('-----------------------')

# ------------------------------ FUNÇÕES ------------------------------------
    # Método para criar as folhas de cartas
    def criar_folhas_de_cartas(self, carta):
        '''
        Cria as folhas de cartas de acordo com a escala (Carta).
        '''
        self.carta = carta
        incrementos = {
            '1kk': (4, 6),
            '500k': (2, 3),
            '250k': (1, 1.5),
            '100k': (0.5, 0.5),
            '50k': (0.25, 0.25),
            '25k': (0.125, 0.125),
        }
        lat_incremen, lon_incremen = incrementos[carta]
        (lon_min_brasil, lat_min_brasil,
         lon_max_brasil, lat_max_brasil) = brasil.bounds

        # Arredonde os limites para os múltiplos mais próximos do incremento
        lat_min = self.arredondar_para_multiplo(lat_min_brasil, lat_incremen)
        lon_min = self.arredondar_para_multiplo(lon_min_brasil, lon_incremen)
        lat_max = self.arredondar_para_multiplo(lat_max_brasil, lat_incremen,
                                                True)
        lon_max = self.arredondar_para_multiplo(lon_max_brasil, lon_incremen,
                                                True)
        lat_ranges = [(i, i + lat_incremen) for i in float_range(lat_min,
                                                                 lat_max,
                                                                 lat_incremen)]
        lon_ranges = [(i, i + lon_incremen) for i in float_range(lon_min,
                                                                 lon_max,
                                                                 lon_incremen)]
        for lat_range in tqdm(lat_ranges):
            for lon_range in lon_ranges:
                polygon = Polygon([(lon_range[0], lat_range[0]),
                                   (lon_range[1], lat_range[0]),
                                   (lon_range[1], lat_range[1]),
                                   (lon_range[0], lat_range[1]),
                                   (lon_range[0], lat_range[0])])
                # Seleciona apenas poligonos que intersectam com o Brasil
                if polygon.intersects(brasil):
                    left, bottom, right, top = polygon.bounds
                    folha_id = self.gerar_id_folha(left,
                                                   right,
                                                   top,
                                                   bottom,
                                                   5)
                    self.folhas[folha_id] = polygon

    @staticmethod
    def gerar_id_folha(left, right, top, bottom, carta=5):
        '''
        Gera o id da folha de acordo com a escala (Carta).
        '''
        # Adquire o valor de carta do método criar_folhas
        e1kk = ['A', 'B', 'C', 'D', 'E', 'F', 'G',
                'H', 'I', 'J', 'K', 'L', 'M', 'N',
                'O', 'P', 'Q', 'R', 'S', 'T']
        e500k = [['V', 'Y'], ['X', 'Z']]
        e250k = [['A', 'C'], ['B', 'D']]
        e100k = [['I', 'IV'], ['II', 'V'], ['III', 'VI']]
        e50k = [['1', '3'], ['2', '4']]
        e25k = [['NW', 'SW'], ['NE', 'SE']]
        if left > right:
            print('Oeste deve ser menor que leste')
        if top < bottom:
            print('Norte deve ser maior que Sul')
        else:
            id_folha = ''
            if top <= 0:
                id_folha += 'S'
                index = math.floor(-top / 4)
            else:
                id_folha += 'N'
                index = math.floor(bottom / 4)
            numero = math.ceil((180 + right) / 6)
            id_folha += e1kk[index] + str(numero)
            lat_gap = abs(top - bottom)
            # p500k-----------------------
            if lat_gap <= 2:
                LO = math.ceil(right / 3) % 2 == 0
                NS = math.ceil(top / 2) % 2 != 0
                id_folha += '_' + e500k[LO][NS]
            # p250k-----------------------
            if lat_gap <= 1:
                LO = math.ceil(right / 1.5) % 2 == 0
                NS = math.ceil(top) % 2 != 0
                id_folha += e250k[LO][NS]
            # p100k-----------------------
            if lat_gap <= 0.5:
                LO = (math.ceil(right / 0.5) % 3) - 1
                NS = math.ceil(top / 0.5) % 2 != 0
                id_folha += '_' + e100k[LO][NS]
            # p50k------------------------
            if lat_gap <= 0.25:
                LO = math.ceil(right / 0.25) % 2 == 0
                NS = math.ceil(top / 0.25) % 2 != 0
                id_folha += '_' + e50k[LO][NS]
            # p25k------------------------
            if lat_gap <= 0.125:
                LO = math.ceil(right / 0.125) % 2 == 0
                NS = math.ceil(top / 0.125) % 2 != 0
                id_folha += e25k[LO][NS]
            return id_folha

    def arredondar_para_multiplo(
            self, numero, multiplo, arredondar_para_cima=False):
        if arredondar_para_cima:
            return math.ceil(numero / multiplo) * multiplo
        else:
            return math.floor(numero / multiplo) * multiplo

    def plotar(self, brasil=brasil):
        '''
        Plota as folhas de cartas.
        '''
        if self.carta is None:
            print('Crie as folhas cartográficas primeiro')
            return

        fig, ax = plt.subplots()
        for folha_id, poligono in self.folhas.items():
            x, y = poligono.exterior.xy
            ax.plot(x, y, color='#6699cc', alpha=0.7, linewidth=0.3,
                    solid_capstyle='round', zorder=2)
            centro = poligono.centroid
            ax.annotate(folha_id, (centro.x, centro.y), color='black',
                        weight='bold', fontsize=6, ha='center', va='center')

        for geom in brasil.geoms:
            x, y = geom.exterior.xy
            ax.plot(x, y, color='black', alpha=0.7, linewidth=0.3,
                    solid_capstyle='round', zorder=2)

        a = escalas[self.carta]
        ax.set_title(f'Folhas da Carta {a}')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_xlim(-180, 180)
        ax.set_ylim(-80, 80)
        ax.axis('scaled')
        plt.show()

    # Método para salvar as camadas em um geopackage com fiona
    def salvar_folhas_de_cartas(self, folhas=None, file_name='fc.gpkg'):
        '''
        Salva as folhas de cartas em um geopackage.
        '''
        if self.folhas is None:
            print('Crie as folhas cartográficas primeiro')
            return
        if folhas is None:
            folhas = self.folhas
        carta = self.carta
        # Esquema para geopackage
        schema = {
            'geometry': 'Polygon',
            'properties': {'id_folha': 'str',
                           'EPSG': 'str'}
        }
        # Define o CRS como WGS84
        crs = CRS.from_epsg(4326)
        # Nome da camada baseada na carta
        layer_name = f'fc_{carta}'
        # Cria o geopackage
        with fiona.open(set_gdb(file_name), 'w', driver='GPKG',
                        crs=crs, layer=layer_name, schema=schema) as layer:

            for folha_id, poligono in folhas.items():
                epsg_code = self.get_EPSG(folha_id)
                # Adiciona o poligono e o id da folha no geopackage
                element = {
                    'geometry': mapping(poligono),
                    'properties': {'id_folha': folha_id,
                                   'EPSG': epsg_code}
                }
                layer.write(element)

    @staticmethod
    def get_EPSG(folha_id):
        if folha_id.startswith('S'):
            return '327' + folha_id[2:4]
        else:
            return '326' + folha_id[2:4]

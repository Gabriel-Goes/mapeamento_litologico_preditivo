# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------

# ------------------------------ IMPORTS ------------------------------------
import math
from shapely.geometry import Polygon, shape
from shapely.ops import unary_union
import matplotlib.pyplot as plt
from tqdm import tqdm
import fiona
from shapely.geometry import mapping
from fiona.crs import CRS


# Criar gerador de intervalos
def float_range(start, stop, step):
    while start < stop:
        yield start
        start += step


# Abre o arquivo de shapefile e define como brasil
with fiona.open('/home/ggrl/database/shapefiles/IBGE/ANMS2010_06_grandesregioes.shp', 'r', encoding='utf-8') as brasil_shapefile:
    regioes = [shape(feature['geometry']) for feature in brasil_shapefile]

brasil = unary_union(regioes)


# ------------------------------ CLASSES ------------------------------------
class ConstroiMalhaCartografica:
    def __init__(self):
        self.folhas_cartograficas = {}
        self.escala = None

# ------------------------------ FUNÇÕES ------------------------------------
    def criar_folhas(self, escala):
        self.escala = escala
        incrementos = {
            '1kk': (4, 6),
            '500k': (2, 3),
            '250k': (1, 1.5),
            '100k': (0.5, 0.5),
            '50k': (0.25, 0.25),
            '25k': (0.125, 0.125),
        }
        lat_incremento, lon_incremento = incrementos[escala]

        lon_min_brasil, lat_min_brasil, lon_max_brasil, lat_max_brasil = brasil.bounds

        # Arredonde os limites para os múltiplos mais próximos do incremento de latitude e longitude
        lat_min = self.arredondar_para_multiplo(lat_min_brasil, lat_incremento)
        lon_min = self.arredondar_para_multiplo(lon_min_brasil, lon_incremento)
        lat_max = self.arredondar_para_multiplo(lat_max_brasil, lat_incremento,
                                                True)
        lon_max = self.arredondar_para_multiplo(lon_max_brasil, lon_incremento,
                                                True)

        lat_ranges = [(i, i + lat_incremento) for i in float_range(lat_min,
                                                                   lat_max,
                                                                   lat_incremento)]
        lon_ranges = [(i, i + lon_incremento) for i in float_range(lon_min,
                                                                   lon_max,
                                                                   lon_incremento)]
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
                    self.folhas_cartograficas[folha_id] = polygon

    @staticmethod
    def gerar_id_folha(left, right, top, bottom, escala=5):
        # Adquire o valor de escala do método criar_folhas
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
                index = math.floor(-top/4)
            else:
                id_folha += 'N'
                index = math.floor(bottom/4)
            numero = math.ceil((180+right)/6)
            id_folha += e1kk[index]+str(numero)
            lat_gap = abs(top-bottom)
            # p500k-----------------------
            if lat_gap <= 2:
                LO = math.ceil(right/3) % 2 == 0
                NS = math.ceil(top/2) % 2 != 0
                id_folha += '_'+e500k[LO][NS]
            # p250k-----------------------
            if lat_gap <= 1:
                LO = math.ceil(right/1.5) % 2 == 0
                NS = math.ceil(top) % 2 != 0
                id_folha += e250k[LO][NS]
            # p100k-----------------------
            if lat_gap <= 0.5:
                LO = (math.ceil(right/0.5) % 3)-1
                NS = math.ceil(top/0.5) % 2 != 0
                id_folha += '_'+e100k[LO][NS]
            # p50k------------------------
            if lat_gap <= 0.25:
                LO = math.ceil(right/0.25) % 2 == 0
                NS = math.ceil(top/0.25) % 2 != 0
                id_folha += '_'+e50k[LO][NS]
            # p25k------------------------
            if lat_gap <= 0.125:
                LO = math.ceil(right/0.125) % 2 == 0
                NS = math.ceil(top/0.125) % 2 != 0
                id_folha += e25k[LO][NS]
            return id_folha

    def arredondar_para_multiplo(self, numero, multiplo, arredondar_para_cima=False):
        if arredondar_para_cima:
            return math.ceil(numero / multiplo) * multiplo
        else:
            return math.floor(numero / multiplo) * multiplo

    def plotar(self):
        fig, ax = plt.subplots()
        for folha_id, poligono in self.folhas_cartograficas.items():
            x, y = poligono.exterior.xy
            ax.plot(x, y, color='#6699cc', alpha=0.7, linewidth=0.3,
                    solid_capstyle='round', zorder=2)
            centro = poligono.centroid
            ax.annotate(folha_id, (centro.x, centro.y), color='black',
                        weight='bold', fontsize=6, ha='center', va='center')

        ax.set_title('Folhas Cartográficas')
        ax.set_xlabel('Longitude')
        ax.set_ylabel('Latitude')
        ax.set_xlim(-180, 180)
        ax.set_ylim(-80, 80)
        ax.axis('scaled')
        plt.show()

    # Método para salvar as camadas em um geopackage com fiona
    def salvar_folhas_cartograficas_geopackage(self, file_name):
        if self.escala is None:
            print('Crie as folhas cartográficas primeiro')
            return
        escala = self.escala
        # Esquema para geopackage
        schema = {
            'geometry': 'Polygon',
            'properties': {'id_folha': 'str',
                           'EPSG': 'str'}
        }
        # Define o CRS como WGS84
        crs = CRS.from_epsg(4326)
        # Nome da camada baseada na escala
        layer_name = f'folhas_cartograficas_{escala}'
        # Cria o geopackage
        with fiona.open(file_name, 'w', driver='GPKG', crs=crs,
                        layer=layer_name, schema=schema) as layer:
            for folha_id, poligono in self.folhas_cartograficas.items():
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


# ------------------------------ MAIN ---------------------------------------
# Uso da classe
folhas_cartograficas = ConstroiMalhaCartografica()
folhas_cartograficas.criar_folhas('1kk')
folhas_cartograficas.salvar_folhas_cartograficas_geopackage('/home/ggrl/database/folhas_cartograficas.gpkg')
folhas_cartograficas.criar_folhas('500k')
folhas_cartograficas.salvar_folhas_cartograficas_geopackage('/home/ggrl/database/folhas_cartograficas.gpkg')
folhas_cartograficas.criar_folhas('250k')
folhas_cartograficas.salvar_folhas_cartograficas_geopackage('/home/ggrl/database/folhas_cartograficas.gpkg')
folhas_cartograficas.criar_folhas('100k')
folhas_cartograficas.salvar_folhas_cartograficas_geopackage('/home/ggrl/database/folhas_cartograficas.gpkg')
folhas_cartograficas.criar_folhas('50k')
folhas_cartograficas.salvar_folhas_cartograficas_geopackage('/home/ggrl/database/folhas_cartograficas.gpkg')
folhas_cartograficas.criar_folhas('25k')
folhas_cartograficas.salvar_folhas_cartograficas_geopackage('/home/ggrl/database/folhas_cartograficas.gpkg')

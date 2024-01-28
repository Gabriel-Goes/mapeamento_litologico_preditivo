# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
# tornar um dicionário com os ids, bounding_box e litologia de cada folha.
# dicionario = {'id': {'bounding_box': (lon_min, lat_min, lon_max, lat_max),
#                      'litologia': litologia}}
#
# # ------------------------------ IMPORTS ------------------------------------
from tqdm import tqdm
from utils import set_gdb
import geopandas as gpd


# ------------------------------ CLASSES ------------------------------------
class DicionarioFolhasdeCartas:
    '''
    Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
    tornar um dicionário com os ids, bounding_box e litologia de cada folha.
    dicionario = {'id_folha': {'geometry': Polygon,
                               'EPSG': 'str',
                               'litologia': 'str'}}
    '''

    # Construtor da classe
    def __init__(self):
        self.file = set_gdb('fc.gpkg')
        # Lê o arquivo geopackage
        self.carta_1kk = gpd.read_file(self.file, layer='fc_1kk')
        self.bbox = None

    # Método para importar a malha cartográfica
    def gera_dicionario_de_folhas(self, carta='1kk', id_folha=None):
        '''
        Gera um dicionário com as folhas de cartas de acordo com a escala e o
        id_folha. Utilizamos a bounding box da folha 1kk para filtrar as folhas
        '''
        # Cria um dicionário vazio
        folhas = {}
        # Define a máscara de acordo com a carta
        # a mascara é a bounding box da folha 1kk da escala escolhida. Esta é
        # a carta formada pelas 4 primeiras letras da id_folha.
        folha_1kk_id = id_folha[:4]
        folha_1kk = self.carta_1kk[self.carta_1kk['id_folha'] == folha_1kk_id]
        minx, miny = folha_1kk.bounds.minx, folha_1kk.bounds.miny
        maxx, maxy = folha_1kk.bounds.maxx, folha_1kk.bounds.maxy
        self.bbox = (minx, miny, maxx, maxy)
        # Lê o arquivo geopackage
        gdf = gpd.read_file(self.file, layer=f'fc_{carta}', driver='GPKG',
                            bbox=self.bbox)
        # transforma a gdf em um dicionário python neste modelo:
        # {'folha_id: {'geometry': Polygon,
        #              'EPSG': 'str'}
        for index, row in tqdm(gdf.iterrows()):
            folha_id = row['id_folha']
            # Converte a geometria de GeoJSON para um objeto Shapely
            geometry = row['geometry']
            # Obtem o código EPSG
            epsg = row['EPSG']
            # Adiciona ao dicionário
            folhas[folha_id] = {'geometry': geometry,
                                'EPSG': epsg}

        # Retorna o dicionário
        return folhas

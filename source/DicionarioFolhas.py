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
import geopandas as gpd

# Minhas Classes
from geologist.utils.utils import set_gdb


# ------------------------------ CLASSES ------------------------------------
class DicionarioFolhas:
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
        self.bbox = (minx + 0.125, miny + 0.125, maxx - 0.125, maxy - 0.125)
        # Lê o arquivo geopackage
        macro_gdf = gpd.read_file(self.file, layer=f'fc_{carta}',
                                  driver='GPKG', bbox=self.bbox)
        # Filtra macro_gdf pr id_folha
        gdf = macro_gdf[macro_gdf['id_folha'].str.contains(id_folha)]

        # transforma a gdf em um dicionário python neste modelo:
        # {'folha_id: {'geometry': Polygon,
        #              'EPSG': 'str'}
        folhas = {row['id_folha']: {'geometry': row['geometry'],
                                    'EPSG': row['EPSG']}
                  for index, row in tqdm(gdf.iterrows())}

        # Retorna o dicionário
        return folhas

    # Métodos de filtragem de folhas de cartas para serem adicionados no futuro
    # Método para filtrar a malha cartográfica por ID exato
    def filtrar_mc_exato(self, df, ID):
        return df[df['id'].isin(ID)]

    '''
    # Filtrar apenas ID que terminam com o padrão especificado
    def filtrar_mc_regex(self, df, ID):
        return df[df['id'].str.contais(ID + '$')]

    # Filtragem Complexa com funções Lambda
    def filtrar_mc_lambda(self, df, ID):
        return df[df['id'].apply(lambda x: x == ID or x.startswith(ID + '_'))]

    # Filtragem baseada em partes do ID
    def filtrar_mc_partes(self, df, parte_ID):
        return df[df['id'].str.startswith(parte_ID)]
    '''


# ------------------------------ MAIN ---------------------------------------
if __name__ == "__main__":
    from geologist.utils import plotar
    dicionariofolhas = DicionarioFolhas()
    carta_25k = dicionariofolhas.gera_dicionario_de_folhas('25k', 'SF23')
    plotar(carta_25k, '25k')

    carta_50k = dicionariofolhas.gera_dicionario_de_folhas('50k', 'SF23_YA_I')
    # plotar(carta_50k, '50k')

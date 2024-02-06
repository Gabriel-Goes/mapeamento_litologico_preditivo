# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
# tornar um dicionário com os ids, bounding_box e litologia de cada folha.
# dicionario = {'id': {'bounding_box': (lon_min, lat_min, lon_max, lat_max),
#                      'litologia': litologia}}
#
# # ------------------------------ IMPORTS ------------------------------------
import geopandas as gpd
from utils import setDB


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
        self.file = setDB('fc.gpkg')
        # Lê o arquivo geopackage
        self.carta_1kk = gpd.read_file(self.file, layer='fc_1kk')
        self.bbox = None

    # Método para importar a malha cartográfica
    def gera_dicionario(self, id_folha_estudo, carta, folhas, dicionario):
        '''
        Método responsável por gerar construir um dicionário python que será
        populado com folhas de carta contidas na área de estudo na escala
        escolhida.
        '''
        # Define a máscara de acordo com a carta
        # a mascara é a bounding box da folha 1kk da escala escolhida. Esta é
        # a carta formada pelas 4 primeiras letras da id_folha.
        folha_estudo = self.carta_1kk[
            self.carta_1kk['id_folha'] == id_folha_estudo]
        minx, miny = folha_estudo.bounds.minx, folha_estudo.bounds.miny
        maxx, maxy = folha_estudo.bounds.maxx, folha_estudo.bounds.maxy
        self.bbox = (minx + 0.125, miny + 0.125, maxx - 0.125, maxy - 0.125)
        try:
            # Lê o arquivo geopackage
            macro_gdf = gpd.read_file(self.file, layer=f'fc_{carta}',
                                      driver='GPKG', bbox=self.bbox)
            # Filtra macro_gdf pr id_folha
            gdf = macro_gdf[macro_gdf['id_folha'].str.contains(folhas)]
            # transforma a gdf em um dicionário python neste modelo:
            # {'folha_id: {'geometry': Polygon,
            #              'EPSG': 'str'}
            dicionario = {row['id_folha']: {'geometry': row['geometry'],
                                            'EPSG': row['EPSG']}
                          for index, row in gdf.iterrows()}
            print(' --> Dicionário de folhas gerado com sucesso!')
            print(f' --> {len(dicionario)} folhas encontradas.')
            print(f' --> {dicionario.keys()}')
        # Retorna erro se não existir id_folha na gdf
        except KeyError:
            print("\\e2716 ---> Erro ao gerar dicionário de folhas!")

        # Retorna o dicionário
        return dicionario

    # Métodos de filtragem de ID  para serem adicionados no futuro
    # Método para filtrar a malha cartográfica por ID exato
    def filtrar_id(self, dicionariofolhas, ID):
        return dicionariofolhas[dicionariofolhas['id'].isin(ID)]

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
    # from geologist.utils.utils import plotar
    dic_f = DicionarioFolhas()
    carta_25k = dic_f.gera_dicionario('SF23',
                                      '25k',
                                      'SF23_YA_I')
    # plotar(carta_25k, '25k')

    # carta_50k = dicionariofolhas.gera_dicionario('50k',
    #                                                        'SF23_YA_I')
    # plotar(carta_50k, '50k')

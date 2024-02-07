# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# /source/core/DicionarioFolhas.py
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
# tornar um dicionário com os ids, e geometry de cada folha.
# dicionario = {'id': {'geometry': Polygon,
#                      'EPSG': 'str'}
#
# # ------------------------------ IMPORTS ------------------------------------
import geopandas as gpd
from utils import setDB


# ------------------------------ CLASSES ------------------------------------
class DicionarioFolhas:
    '''
    Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
    tornar um dicionário onde id_folha é a chave e EPSG e geometry de cada
    folha são seu valores. Este dicionário será manipulado por outras
    Classes como ManipulaFolhas.

    dicionario = {'id_folha': {'geometry': Polygon,
                               'EPSG': 'str'},}
    '''
    # Método transformar gdf em dicionário
    def gera_dicionario(folhas_selecionadas):
        '''
        Método responsável por gerar construir um dicionário python que será
        populado com folhas de carta contidas na área de estudo na escala
        escolhida.
        '''
        try:
            # transforma a gdf em um dicionário python neste modelo:
            # {'folha_id: {'geometry': Polygon,
            #              'EPSG': 'str'}
            dicionario = {row['id_folha']: {'geometry': row['geometry'],
                                            'EPSG': row['EPSG']}
                          for index, row in folhas_selecionadas.iterrows()}
            print(' --> Dicionário de folhas gerado com sucesso!')
            print(f' --> {len(dicionario)} folhas encontradas.')
            print(f' --> {dicionario.keys()}')

            return dicionario

        # Retorna erro se não existir id_folha na gdf
        except KeyError:
            print("\\e2716 ---> Erro ao gerar dicionário de folhas!")

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

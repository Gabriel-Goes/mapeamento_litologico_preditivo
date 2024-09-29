# Autor: Gabriel Góes Rocha de Lima
# Data: 20/04/2021
# /source/core/DicionarioFolhas.py
# ---------------------------------------------------------------------------
# Esta classe é responsável por abrir layer de um bancode dados, filtrar por
# ids e retornar um dicionário com os ids, e geometry de cada folha.
# ---------------------------------------------------------------------------
# dicionario = {
# 'id': {
#     'geometry': Polygon,
#     'EPSG': 'str'}
#
# # ------------------------------ IMPORTS ------------------------------------


# ------------------------------ CLASSES ------------------------------------
class DicionarioFolhas:
    '''
    Esta classe é responsável por abrir layer de um gpkg, filtrar por ids e re-
    tornar um dicionário onde folha_id é a chave e EPSG e geometry de cada
    folha são seu valores. Este dicionário será manipulado por outras
    Classes como ManipulaFolhas.

    dicionario = {'folha_id': {'geometry': Polygon,
                               'EPSG': 'str'},}
    '''

    # Construtor do DicionarioFolhas
    def __init__(self):
        pass

    # Método transformar gdf em dicionário
    def dicionario(folhas_selecionadas):
        '''
        Método responsável por gerar construir um dicionário python que será
        populado com folhas de carta contidas na área de estudo na escala
        escolhida.

        Transforma o geodataframe em um dicionário python neste modelo:

             {'folha_id: {'geometry': Polygon,
                          'EPSG': 'str'}
        '''
        try:
            dicionario = {row['folha_id']: {'geometry': row['geometry'],
                                            'EPSG': row['EPSG']}
                          for index, row in folhas_selecionadas.iterrows()}
            print(' --> Dicionário de folhas gerado com sucesso!')
            print(f' --> {len(dicionario)} folhas encontradas.')
            print(f' --> {dicionario.keys()}')

            return dicionario
        # Retorna erro se não existir folha_id na gdf
        except KeyError as e:
            print(f' --> Erro ao gerar dicionário de folhas: {e}')
            print("\\e2716 ---> Erro ao gerar dicionário de folhas!")


# ------------------------------ MAIN ---------------------------------------
if __name__ == "__main__":
    # from geologist.utils.utils import plotar
    dic_f = DicionarioFolhas()
    carta_25k = dic_f.gera_dicionario(
        'SF23',
        '25k',
        'SF23_YA_I'
    )
    # plotar(carta_25k, '25k')
    # carta_50k = dicionariofolhas.gera_dicionario('50k',
    # plotar(carta_50k, '50k')

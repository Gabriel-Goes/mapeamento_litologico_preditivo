import pandas as pd

from src.funcs1_importar import import_malha_cartog
from contribuicoes.hilogoes.nomeador_hilo import nomeador_grid


# DEFININDO NOMES DA MALHA A PARTIR DA ARTICULaÇO SISTEMÁTICA DE FOLHAS DE CARTAS. 
# CONSTURINDO UMA LISTA E DEFININDO COMO UMA SERIES (OBJETO DO PANDAS).
def nomeador_malha(gdf):
    '''
    
    '''
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_grid(row.region[0],row.region[1],
                                         row.region[3],row.region[2],escala=5))
        lista_malha.append(row.id_folha)

    gdf['id_folha'] = lista_malha
# ---------------------------------------------------------------------------------------------------------------
 
# DEFININDO LIMITES DE CADA FOLHA CARTOGRÁFICA -----------------------------------------------------------------#
def regions(malha_cartog):
    '''
    
    '''
    bounds = malha_cartog.bounds
    malha_cartog['region'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]


    malha_cartog.to_crs("EPSG:32723",inplace=True)   # APENAS AS INFORMAÇOES NA ZONA 23SUL UTM ESTARÃO CORRETAS
    print(f"{malha_cartog.crs}")

    bounds = malha_cartog.bounds
    malha_cartog['region_proj'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]
    return malha_cartog
# ----------------------------------------------------------------------------------------------------------------------

# LISTANDO REGIÕES DE CADA FOLHA DE CARTAS DA MALHA CARTOGRÁFICA \ ['REGEION'] = ['ID_FOLHA'] REDUNDANCIA
# SELECIONANDO AREA DE ESTUDO

def cartas(escala,ids):
    '''
    
    '''
    print('# --- Iniciando seleção de área de estudo')
    malha_cartog_gdf_select = import_malha_cartog(escala,ids)
    malha_cartog_gdf_select.set_index('id_folha',inplace=True)
    regions(malha_cartog_gdf_select)

    # CRIANDO UM DICIONÁRIO DE CARTAS
    print('# --- Construindo Dicionario de Cartas')
    malha_cartog_gdf_select['raw_data']= ''
    dic_cartas = malha_cartog_gdf_select.to_dict()

    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) > 1:
        print(f"{len(dic_cartas['raw_data'])} folhas cartográfica selecionadas")
        print("")

    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) == 1:
        print(f"{len(dic_cartas['raw_data'])} folha cartográfica selecionada")
        print("")
        
    return dic_cartas,malha_cartog_gdf_select 
# ----------------------------------------------------------------------------------------------------------------------

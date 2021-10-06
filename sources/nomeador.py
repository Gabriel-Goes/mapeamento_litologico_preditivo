from sources import importar
from contribuicoes.hilogoes import nomeador_hilo

import pandas as pd

# DEFININDO NOMES DA MALHA A PARTIR DA ARTICULA~AO SISTEMÁTICA DE FOLHAS DE CARTAS. 
# CONSTURINDO UMA LISTA E DEFININDO COMO UMA SERIES (OBJETO DO PANDAS).
def nomeador_malha(gdf):
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_hilo.nomeador_grid(row.region[0],row.region[1],
                                         row.region[3],row.region[2],escala=5))
        lista_malha.append(row.id_folha)

    gdf['id_folha'] = lista_malha

# ----------------------------------------------------------------------------------------------------------------------   
# DEFININDO LIMITES DE CADA FOLHA CARTOGRÁFICA -----------------------------------------------------------------#
def regions(gdf):
    # CRIANDO COLUNA REGION EM COORDENADAS GEOGRÁFICAS
    
    bounds = gdf.bounds
    gdf['region'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]

    # CRIANDOCOLUNA REGIONS EM COORDENADAS PROJETADAS
    gdf.to_crs("EPSG:32723",inplace=True)   # APENAS AS INFORMAÇOES NA ZONA 23SUL UTM ESTARAO CORRETAS
    print(f"{gdf.crs}")

    bounds = gdf.bounds
    gdf['region_proj'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]
    return gdf

# ----------------------------------------------------------------------------------------------------------------------
# SELECIONADOR DE REGIÃO  ------------------------------------------------------------------------------------------#
def select_area(escala,ids):
    malha_cartog = importar.geologico('malha_cartog_'+escala+'_wgs84')
    malha_cartog_gdf_select = malha_cartog[malha_cartog['id_folha'].str.contains(ids)]       # '.contains' não é ideal.
    malha_cartog_gdf_select = regions(malha_cartog_gdf_select) 
    
    return(malha_cartog_gdf_select)
# ----------------------------------------------------------------------------------------------------------------------
# LISTANDO REGIÕES DE CADA FOLHA DE CARTAS DA MALHA CARTOGRÁFICA \ ['REGEION'] = ['ID_FOLHA'] REDUNDANCIA
def cartas(escala,id):
    # SELECIONANDO AREA DE ESTUDO
    print('# --- Iniciando seleção de área de estudo')
    malha_cartog_gdf_select = select_area(escala,id)
    
    #print("Indexando a coluna 'id_folha'") 
        #print("Indexando a coluna 'id_folha'") 
    #print("Indexando a coluna 'id_folha'") 
        #print("Indexando a coluna 'id_folha'") 
    #print("Indexando a coluna 'id_folha'") 
        #print("Indexando a coluna 'id_folha'") 
    #print("Indexando a coluna 'id_folha'") 
    malha_cartog_gdf_select.set_index('id_folha',inplace=True)
    
    #print(list(malha_cartog_gdf_select.index))              
        #print(list(malha_cartog_gdf_select.index))              
    #print(list(malha_cartog_gdf_select.index))              
        #print(list(malha_cartog_gdf_select.index))              
    #print(list(malha_cartog_gdf_select.index))              
        #print(list(malha_cartog_gdf_select.index))              
    #print(list(malha_cartog_gdf_select.index))              
    lista_cartas = list(malha_cartog_gdf_select.index)

    # CRIANDO UM DICIONÁRIO DE CARTAS
    #print(f"Retirada da coluna 'geometry'")
    malha_cartog_df_select = malha_cartog_gdf_select.drop(columns=['geometry'])
    malha_cartog_df_select['raw_data'] =''
    malha_cartog_df_select['splines'] =''
    malha_cartog_df_select['scores'] =''
    malha_cartog_df_select['lito_splines'] =''
    malha_cartog_df_select['mean_score'] =''
    malha_cartog_df_select['litologia']=''
    malha_cartog_df_select['cubic']=''
    malha_cartog_df_select['lito_cubic'] =''

    #print("Gerando dicionário com o index")                     
    dic_cartas = malha_cartog_df_select.to_dict()
    #print(dic_cartas.keys())                                    
    #print(dic_cartas)
    
    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) > 1:
        print(f"{len(dic_cartas['raw_data'])} folhas cartográfica selecionadas")
        print("")

    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) == 1:
        print(f"{len(dic_cartas['raw_data'])} folha cartográfica selecionada")
        print("")
    return lista_cartas, dic_cartas, malha_cartog_gdf_select
# ----------------------------------------------------------------------------------------------------------------------
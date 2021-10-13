
from sources.importar import geometrias


# SELECIONADOR DE REGIÃO  ------------------------------------------------------------------------------------------#
def import_malha_cartog(escala,ids):
    malha_cartog = geometrias(camada='malha_cartog_'+escala+'_wgs84')
    malha_cartog_gdf_select = malha_cartog[malha_cartog['id_folha'] == ids]       # '.contains' não é ideal.
    malha_cartog_gdf_select = regions(malha_cartog_gdf_select) 
    
    return(malha_cartog_gdf_select)
# ----------------------------------------------------------------------------------------------------------------------

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
def cartas(escala,id):
    
    print('# --- Iniciando seleção de área de estudo')
    malha_cartog_gdf_select = import_malha_cartog(escala,id)
    malha_cartog_gdf_select.set_index('id_folha',inplace=True)

    malha_cartog_df_select = malha_cartog_gdf_select.drop(columns=['geometry'])
    malha_cartog_df_select['raw_data'] =''
    dic_cartas = malha_cartog_df_select.to_dict()
    
    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) > 1:
        print("")
        print(f"{len(dic_cartas['raw_data'])} folhas cartográfica selecionadas")

    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) == 1:
        print("")
        print(f"{len(dic_cartas['raw_data'])} folha cartográfica selecionada")
    return dic_cartas, malha_cartog_gdf_select
# ----------------------------------------------------------------------------------------------------------------------


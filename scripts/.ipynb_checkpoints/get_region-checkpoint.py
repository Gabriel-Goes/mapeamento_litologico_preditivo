from sources.importar import geometrias
from sources.dicionario_cartas import cartas
from sources.descricao import descricao

from tqdm import tqdm
import verde as vd


# CRIANDO DICIONARIO DE FOLHAS CARTOGRAFICAS PARA CARA TIPO DE DADO
def get_region(escala,id,geof,camada,mapa=None):
    
    print('importando dados geofisicos')
    geof_dataframe = geometrias(geofisico=geof)
    
    # LISTANDO REGIOES DAS FOLHAS DE CARTAS
    lista_cartas, dic_cartas,malha_cartog_gdf_select = cartas(escala,id)       # importa malha cartografica
    print(f"Lista de chaves do dicionario de cartas: {list(dic_cartas.keys())}")
    metadatadict,        \
    lista_atributo_geof, \
    lista_atributo_geog, \
    lista_atributo_proj, \
          geof_descrito  = descricao(geof_dataframe)

    dic_raw_meta={'Metadata'          :metadatadict,
                  'Lista_id'          :lista_cartas,
                  'Lista_at_geof'     :lista_atributo_geof,
                  'Lista_at_geog'     :lista_atributo_geog,
                  'Lista_at_proj'     :lista_atributo_proj,
                  'Percentiles'       :geof_descrito,
                  'Malha_cartografica':malha_cartog_gdf_select}

    print(f"Lista de chaves do dicionario de metadata bruto: {list(dic_raw_meta.keys())}")


    # ITERANDO ENTRE AS FOLHAS DE CARTAS
    print("")
    print(f"# --- Início da iteração entre as folhas cartográficas #")

    for index, row in tqdm(malha_cartog_gdf_select.iterrows()):
        # RECORTANDO DATA PARA CADA FOLHA COM ['region.proj']
        print(index, row)
        data = geof_dataframe[vd.inside((geof_dataframe.X, geof_dataframe.Y), region = row.region_proj)]

        # GERANDO TUPLA DE COORDENADAS
        if data.empty:
            None
            
        elif len(data) < 1000:
            None
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            
        else:
            print(f"# Folha de código: {index}")
            print(f" Atualizando dados brutos em dic_cartas['raw_data']")
            x = {index:data}
            dic_cartas['raw_data'].update(x) 
            print(f" com {len(data)} pontos de amostragem")

            litologia= geometrias(camada,mapa)
            region = dic_cartas['region_proj']
            litologia.to_crs(32723,inplace=True)
            print(litologia.crs)

            litologia=litologia.cx[row.region_proj[0]:row.region_proj[1],row.region_proj[2]:row.region_proj[3]]
            print(f" Atualizando dados geologicos em dic_cartas['litologia']")
            print(f" com {litologia.shape[0]} poligonos descritos por\
                         {litologia.shape[1]} atributos geologicos ")

            y = {index:litologia}
            dic_cartas['litologia'].update(y)

    return dic_cartas,dic_raw_meta


# data_list[Dicionario de Cartas['region',                 #0  DICIONARIO COM DADOS PRINCIPAIS
#                                'region_proj',
#                                'raw_data',
#                                'interpolado',
#                                'scores',
#                                'lito_geof',
#                                'mean_score'],



#           Malha Cartografica Selecionada['geometry',     #2 GEODATAFRAME DA MALHA CARTOGRAFICA
#                                          'region',
#                                          'region_proj']

#           Descricao Dados Brutos['KPERC',                #3 DATAFRAME DESCRICAO ESTATISTICA DADOS BRUTOS
#                                  'eU',
#                                  'eTH',
#                                  'UTHRAZAO',
#                                  'UKRAZAO',
#                                  'MDT',
#                                  'THKRAZAO',
#                                  'CTCOR']           
#           ]


     



from src.funcs_importar import dado_bruto
from src.funcs_cartog_automation import cartas
from src.funcs_descricao import descricao

from tqdm import tqdm
from verde import inside


# CRIANDO DICIONARIO DE FOLHAS CARTOGRAFICAS PARA CARA TIPO DE DADO
def get_region(escala,id,geof,camada,mapa=None):
    '''
    Recebe:
        escala : Escalas disponíveis para recorte: '50k', '100k', '250k', '1kk'.
            id : ID da folha cartográfica (Articulação Sistemática de Folhas Cartográficas)
          geof : Dado aerogeofísico disponível na base de dados (/home/ggrl/geodatabase/geof/)
        camada : Litologias disponíveis na base de dados (/home/ggrl/geodatabase/geodatabase.gpkg)
    '''
    print('# Importando dados')
    litologia, geof_dataframe = dado_bruto(camada,mapa,geof)

    # LISTANDO REGIOES DAS FOLHAS DE CARTAS
    print('')
    print('# -- Selecionando Folhas Cartograficas')
    
    dict_cartas,\
    malha_cartog_gdf_select = cartas(escala,id)

    metadatadict,        \
    lista_atributo_geof, \
    lista_atributo_geog, \
    lista_atributo_proj, \
          geof_descrito  = descricao(geof_dataframe)

    print('# -- Contruindo dicionario de metadados')
    dic_raw_meta={'Metadata'          :metadatadict,
                  'Lista_at_geof'     :lista_atributo_geof,
                  'Lista_at_geog'     :lista_atributo_geog,
                  'Lista_at_proj'     :lista_atributo_proj,
                  'Percentiles'       :geof_descrito,
                  'Malha_cartografica':malha_cartog_gdf_select}
    # ITERANDO ENTRE AS FOLHAS DE CARTAS
    print("")
    print(f"# --- Início da iteração entre as folhas cartográficas #")

    ## Dicionario de cartas[key: 'litologia']
    dict_cartas['litologia'] ={}
    
    for index, row in tqdm(malha_cartog_gdf_select.iterrows()):

        # RECORTANDO DATA PARA CADA FOLHA COM verde.inside() ['region.proj']
        data = geof_dataframe[inside((geof_dataframe.X, geof_dataframe.Y), region = row.region_proj)]

        # GERANDO TUPLA DE COORDENADAS          
        if len(data) < 1000:
            y = {index:litologia}
            dict_cartas['litologia'].update(y)
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            
        else:
            print(f"# Folha de código: {index}")
            print(f" Atualizando dados brutos em dic_cartas['raw_data']")
            x = {index:data}
            dict_cartas['raw_data'].update(x) 
            print(f" com {len(data)} pontos de amostragem")

            litologia.to_crs(32723,inplace=True)
            print(litologia.crs)

            litologia=litologia.cx[row.region_proj[0]:row.region_proj[1],row.region_proj[2]:row.region_proj[3]]
            print(f" Atualizando dados geologicos em dic_cartas['litologia']")
            print(f" com {litologia.shape[0]} poligonos descritos por\
                         {litologia.shape[1]} atributos geologicos ")

            y = {index:litologia}
            dict_cartas['litologia'].update(y)
        
        if data.empty:
            None
            print('Folha cartografica sem dados Aerogeofisicos')

    return dict_cartas,dic_raw_meta
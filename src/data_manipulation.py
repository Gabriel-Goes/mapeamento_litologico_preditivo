# ggrl;
# geologist_machine;
# ic_2021
\
\
\

import numpy as np
import pandas as pd
import geopandas as gpd

from shapely import geometry
from tqdm import tqdm
from verde import inside

from src.funcs_importar import dado_bruto
from src.funcs_cartog_automation import cartas
from src.funcs_descricao import descricao

from contribuicoes.victsnet_emails import source_code_verde as td


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
# --------------------------------------------------------------------------------------

# # --------------------- DEFININDO FUNÇÃO DE QUE CHAMARÁ AS FUNÇÕES ANTERIORES PROVOCANDO UM ENCADEAMENTO DE OPERAÇÕES -------------- 
def interpolar(mag=None,gama=None,
               dic_cartas=None,dic_raw_meta=None):
               
    print('# Inicio dos processos de interpolação pelo método cúbico')
    for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):
        print(index,row)
        # lista_atributo_geof = dic_raw_meta['Lista_at_geof']
        data = dic_cartas['raw_data'][index]              

        # GERANDO TUPLA DE COORDENADAS
        if len(data) == 0:
            None
            
        elif len(data) < 1000:
            None
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            
        else:
            print(f"# Folha de código: {index}")
            print(f" Retirando dados brutos em dic_cartas['raw_data']")
            print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de 500 metros")

            data['geometry'] = [geometry.Point(x, y) for x, y in zip(data['X'], data['Y'])]
            crs = "+proj=utm +zone=23 +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs"

            gdf_geof = gpd.GeoDataFrame(data, geometry='geometry', crs=crs)

            area = dic_cartas['region_proj'][index]

            # creating a grid with cells
            xu, yu = td.regular(shape = (636, 444),
                                area  = area)

            if mag:
                ALTURA = np.array(gdf_geof.ALTURA)
                MAGIGRF = np.array(gdf_geof.MAGIGRF)
                MDT = np.array(gdf_geof.MDT)

                x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)

                altura_ = td.interp_at(x2, y2, ALTURA, xu, yu, algorithm = 'cubic', extrapolate = True)
                mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm = 'cubic', extrapolate = True)
                magigrf_ = td.interp_at(x2, y2, MAGIGRF, xu, yu, algorithm = 'cubic', extrapolate = True)

                # intialise data of lists. 
                data_interpolado = {'X':xu, 'Y':yu, 'MDT': mdt_,
                        'KPERC': altura_, 'eU':magigrf_} 
                
                # Create DataFrame 
                interpolado_cubico = pd.DataFrame(data_interpolado)
                
                # Print the output. 
                y={index:interpolado_cubico}
                dic_cartas['cubic'].update(y)  

            if gama:
                CTCOR = np.array(gdf_geof.CTCOR)
                MDT = np.array(gdf_geof.MDT)
                eTH = np.array(gdf_geof.eTH)
                eU = np.array(gdf_geof.eU)
                KPERC = np.array(gdf_geof.KPERC)
                THKRAZAO = np.array(gdf_geof.THKRAZAO)
                UKRAZAO = np.array(gdf_geof.UKRAZAO)
                UTHRAZAO = np.array(gdf_geof.UTHRAZAO)

                x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)

                eTH_ = td.interp_at(x2, y2, eTH, xu, yu, algorithm = 'cubic', extrapolate = True)
                eu_ = td.interp_at(x2, y2, eU, xu, yu, algorithm = 'cubic', extrapolate = True)
                kperc_ = td.interp_at(x2, y2, KPERC, xu, yu, algorithm = 'cubic', extrapolate = True)
                ctcor_ = td.interp_at(x2, y2, CTCOR, xu, yu, algorithm = 'cubic', extrapolate = True)
                mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm = 'cubic', extrapolate = True)
                uthrazao_ = td.interp_at(x2, y2, UTHRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                ukrazao_ = td.interp_at(x2, y2, UKRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                thkrazao_ = td.interp_at(x2, y2, THKRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)

                # intialise data of lists. 
                data = {'X':xu, 'Y':yu, 'MDT': mdt_,  'CTCOR': ctcor_,
                        'KPERC': kperc_, 'eU':eu_, 'eTH': eTH_,
                        'UTHRAZAO':uthrazao_,'UKRAZAO':ukrazao_,'THKRAZAO':thkrazao_} 
                
                # Create DataFrame 
                interpolado_cubico = pd.DataFrame(data)

                dic_cartas['cubic'] = {}
                                
                y={index:interpolado_cubico}
                dic_cartas['cubic'].update(y)

            print('__________________________________________')
        print(" ")
    print("Dicionário de cartas disponível")
    return dic_cartas, dic_raw_meta
# --------------------------------------------------------------------------------------


# RETIRANDO VALORES DE LITOLOGIA DE CADA PIXEL
def describe(dic_cartas,dic_raw_data,crs__,tdm,):
    print("")
    print(f"# --- Inicio da análise geoestatística")
    lista_interpolado = list()
        
    for index in dic_cartas:
        # IMPORTANDO VETORES LITOLÓGICOS ------------
        litologia = dic_cartas['litologia'][index]
        litologia.reset_index(inplace=True)
        
        if crs__=='proj':
            litologia.to_crs(32723,inplace=True)
            print(f" lito: {litologia.crs}")
        else:
            litologia.to_crs(4326,inplace=True)
            print(f" lito: {litologia.crs}")
        # -------------------------------------------
        
        # GRID POR CUBICO
        if tdm:
            for i in tqdm(dic_raw_data['lista_atributo_geof']):
                df = dic_cartas['interpolado_cubico'][i].to_dataframe()
                lista_interpolado.append(df[i])

            geof_cubic = pd.concat(lista_interpolado,axis=1, join='inner')
            geof_cubic.reset_index(inplace=True)

            # AJUSTANDO CRS
            #print("Ajustando crs")
            if crs__=='proj':
                gdf = gpd.GeoDataFrame(geof_cubic,crs=32723)
                gdf = gdf.set_crs(32723, allow_override=True)
                gdf = gdf.to_crs("EPSG:32723")
                print(f" geof: {gdf.crs}")
            else:
                gdf = gpd.GeoDataFrame(geof_cubic,crs=32723)
                gdf = gdf.set_crs(32723, allow_override=True)
                gdf = gdf.to_crs("EPSG:4326")
                print(f" geof: {gdf.crs}")


            # CALCULO DE GEOMETRIA MAIS PROXIMA
            print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_cubic)} centróides de pixel")
            lito_cubic = dic_cartas['cubic'][index]
            lito_cubic['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])
            print(f"# Listagem de unidades geológicas presentes na folha de id {index}:    ")
            print(f"  {list(lito_cubic['closest_unid'].unique())}")

            # Adicionando lito_geof ao dicionario
            print('')
            print(f" Adicionando dataframe com valores de litologia e geofíscios ao dicionário de cartas")
            x = {index:lito_cubic}
            dic_cartas['lito_cubic'].update(x)
            print(dic_cartas['lito_cubic'][index].keys())
import math
import numpy as np

import geopandas as gpd
import pandas as pd

import pyproj
from shapely import geometry

import verde as vd
import rioxarray as rio

import matplotlib.pyplot as plt
import seaborn as sns

import Custom_Stats_fabio as csf

####################################### LEMBRAR DE PEDIR AJUDA
import tqdm 
from tqdm.notebook import trange

gdb = '/home/ggrl/geodatabase/'


#                                      DEFININDO FUNÇÕES PARA SCRIPT 
# Importador de Litologias por escala
def importar(camada, mapa=False):
    lito =  gpd.read_file(gdb+'database.gpkg',
                        driver= 'GPKG',
                        layer= camada)
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]
        return(folha)
    else:
        return(lito)

# DEFININDO LIMITES DE CADA FOLHA CARTOGRÁFICA
def regions(gdf):
    # CRIANDO COLUNA REGION EM COORDENADAS GEOGRÁFICAS
    #print(f" Definindo limites com GeoDataFrame.bounds ")
    #print(f"{gdf.crs}")
    bounds = gdf.bounds
    #print(bounds[:1])

    gdf['region'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]

    # CRIANDOCOLUNA REGIONS EM COORDENADAS PROJETADAS
    gdf = gdf.to_crs("EPSG:32723")
    #print(f"{gdf.crs}")
    
    bounds = gdf.bounds
    #print(bounds[:1])
    
    gdf['region_proj'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                          bounds['miny'],bounds['maxy'])]
    return gdf
        
# Definindo nomes da malha a partir da articulação sistematica de folhas de cartas. Construindo uma lista e definindo como uma series.
def nomeador_malha(gdf):
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_grid(row.region[0],row.region[1],
                                         row.region[3],row.region[2],escala=5))
        lista_grid.append(row.id_folha)

    gdf['id_folha'] = lista_malha

# Selecionador de Região
def select_area(escala,id):
    malha_cartog = importar('malha_cartog_'+escala+'_wgs84')
    malha_cartog_gdf_select = malha_cartog[malha_cartog['id_folha'].str.contains(id)]       # '.contains' não é ideal.
    malha_cartog_gdf_select = regions(malha_cartog_gdf_select)    
    
    return(malha_cartog_gdf_select)
    
# LEVANTAMENTO 1089 # tie + flight_lines
geof_1089 =pd.read_csv(gdb+'geof/g1089')


# DEFININDO DADOS AEROGEOFÍSICOS
geof_1089 =pd.read_csv(gdb+'geof/g1089')
    
# LISTANDO REGIÕES DE CADA FOLHA DE CARTAS DA MALHA CARTOGRÁFICA \ ['REGEION'] = ['ID_FOLHA'] REDUNDANCIA
def cartas(escala,id):
    # SELECIONANDO AREA DE ESTUDO
    if escala and id:
        print('# --- Iniciando seleção de área de estudo')
        malha_cartog_gdf_select = select_area(escala,id)
        #print("Indexando a coluna 'id_folha'")
        malha_cartog_gdf_select.set_index('id_folha',inplace=True)
        print(malha_cartog_gdf_select.index)

   
    # CRIANDO UM DICIONÁRIO DE CARTAS
    #print(f"Retirada da coluna 'geometry'")
    malha_cartog_gdf_select.drop(columns=['geometry'],inplace=True)
    malha_cartog_gdf_select['raw_data'] =''
    malha_cartog_gdf_select['interpolado'] =''
    malha_cartog_gdf_select['scores'] =''
    malha_cartog_gdf_select['lito_geof'] =''
    print("Gerando dicionário com o index")
    dic_cartas = malha_cartog_gdf_select.to_dict()
    print(dic_cartas.keys())
    #print(dic_cartas)
    
    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas) > 1:
        print(f"{len(dic_cartas['raw_data'])} folhas cartográfica selecionadas")
        print("")

    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas) == 1:
        print(f"{len(dic_cartas['raw_data'])} folha cartográfica selecionada")
        print("")
    return malha_cartog_gdf_select, dic_cartas




# DEFININDO FUNÇÃO DE QUE CHAMARÁ AS FUNÇÕES ANTERIORES PROVOCANDO UM ENCADEAMENTO DE OPERAÇÕES  
def interpolar(escala,id,geof, interpolador_verde=True,n_splits=None,camada=None,nome=None,crs__='proj'):
    # DEFININDO PADRÃO DE INTERPOLAÇÃO VERDE
    if interpolador_verde == True:
        save=False
        degree=1
        spacing=499
        psize= 100
        
    # Listando regiões das folhas cartográficas
    malha_cartog_gdf_select, dic_cartas = cartas(escala,id)
        
    # LISTANDO ATRIBUTOS GEOFÍSICOS E ATRIBUTOS GEOGRÁFICOS
    atributos_geof = list(geof.columns)
    lista_atributo_geof=[]
    lista_atributo_geog=[]
    lista_atributo_proj=[]

    for atributo in atributos_geof:
        if atributo == 'LATITUDE':
            lista_atributo_geog.append(atributo)
        elif atributo == 'LONGITUDE':
            lista_atributo_geog.append(atributo)
        elif atributo == 'LONG':
            lista_atributo_geog.append(atributo)
        elif atributo == 'LAT':
            lista_atributo_geog.append(atributo) 
        elif atributo == 'X':
            lista_atributo_proj.append(atributo)
        elif atributo == 'Y':
            lista_atributo_proj.append(atributo)
        elif atributo == 'UTME':
            lista_atributo_proj.append(atributo)
        elif atributo == 'UTMN':
            lista_atributo_proj.append(atributo)
        else:
            lista_atributo_geof.append(atributo)
    codigo=str(geof)        
    print(f"# --- # Listagem de dados do aerolevantamento de código: '{codigo}'")
    print(f"Lista de atributos geofísicos = {lista_atributo_geof}")
    print(f"lista de atributos geograficos = {lista_atributo_geog}")
    print(f"lista de atributos projetados = {lista_atributo_proj}")
    print("")
            

    # Iterando entre itens da lista de folhas cartográficas
    print(f"# --- Início da iteração entre as folhas cartográficas #")

    for index, row in malha_cartog_gdf_select.iterrows():
        # RECORTANDO DATA PARA CADA FOLHA COM 'region.proj'
        #X = lista_atributo_proj[0]
        #Y = lista_atributo_proj[1]
        
        data = geof[vd.inside((geof.X, geof.Y), region = row.region_proj)]
        
        # GERANDO TUPLA DE COORDENADAS
        if data.empty:
            None
            
        elif len(data) < 1000:
            None
            #print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            
        else:
            print(f"# Folha de código: {index}")
            print(f" Atualizando dados brutos em dic_cartas['raw_data']")
            x = {index:data}
            dic_cartas['raw_data'].update(x) 
            print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de {spacing} metros")
            
            # ADICIONANDO ATRIBUTOS GEOFÍSICOS AO DICIONÁRIO INTERPOLADO
            interpolado={}
            for atributo in lista_atributo_geof:
                x = {atributo:''}
                interpolado.update(x)
            #print(f" Construindo dic_cartas['interpolado'] vazio com os atributos geofísicos")
            #print(interpolado.keys())
                
            # ADICIONANDO ATRIBUTOS AO DICIONÁRIO SCORES
            scores={}
            for atributo in lista_atributo_geof:
                x = {atributo:''}
                scores.update(x)
            #print(f" Construindo dicionário vazio de score do cross validation")
            #print(scores.keys())

            # Iterando entre os canais de interpolação
            print("")
            print(f"# --- Inicio da interpolação com verde Splines # ")
            for i in lista_atributo_geof:
                # Definindo encadeamento de processsos para interpolação
                chain = vd.Chain([
                                ('trend', vd.Trend(degree=degree)),
                                ('reduce', vd.BlockReduce(np.median, spacing=spacing)),
                                ('spline', vd.Spline())
                            ])
                
                coordinates = (data.X.values, data.Y.values)
                
                print(f"fitting: {i}")
                chain.fit(coordinates, data[i])
                
                # Griding the predicted data.
                #print(f"gridding: {i}")
                grid = chain.grid(spacing=psize, data_names=[i],pixel_register=True)
                interpolado[i] = vd.distance_mask(coordinates, maxdist=1000, grid= grid)
                
                # ATUALIZAÇÃO DE DICIONÁRIO DE INTERPOLADOS
                #print(f" Atualizando dicionário com grids interpolados")
                x = {index:interpolado}
                dic_cartas['interpolado'].update(x)
                                    
                # Processo de validação cruzada da biblioteca verde
                if n_splits:
                    cv     = vd.BlockKFold(spacing=spacing,
                                n_splits=n_splits,
                                shuffle=True)

                    scores[i] = vd.cross_val_score(chain,
                                            coordinates,
                                            data[i],
                                            cv=cv)

                # ATUALIZAÇÃO DE DICIONÁRIO DE SCORES
                #print(f" Atualizando dicionário com scores")
                y = {index:scores}
                dic_cartas['scores'].update(y)
                
                # SALVANDO DADOS INTERPOLADOS NO FORMATO .TIF
                if save:
                    local='grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif'
                    print('salvando grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif')
                    #grids[i].to_netcdf(gdb+'/grids/geof_3022_'+str(psize)+'m_'+i+'_'+row.id_folha+'.nc')
                    tif_ = interpolado[i].rename(easting = 'x',northing='y')
                    tif_.rio.to_raster(gdb+local)
        
            # RETIRANDO VALORES DE LITOLOGIA DE CADA PIXEL
            print("")
            print(f"# --- Inicio da análise geoestatística")
            dataframe = list()
            
            for i in lista_atributo_geof:
                df = interpolado[i].to_dataframe()
                dataframe.append(df[i])

            geof_grids = pd.concat(dataframe,axis=1, join='inner')
            geof_grids.reset_index(inplace=True)
            geof_grids['geometry'] =\
                 [geometry.Point(x,y) for x, y in zip(geof_grids['easting'], geof_grids['northing'])]

            print('Ajustando crs')
            if crs__=='proj':
                gdf = gpd.GeoDataFrame(geof_grids,crs=32723)
                gdf = gdf.set_crs(32723, allow_override=True)
                gdf = gdf.to_crs("EPSG:32723")
                print(f" geof: {gdf.crs}")
            else:
                gdf = gpd.GeoDataFrame(geof_grids,crs=32723)
                gdf = gdf.set_crs(32723, allow_override=True)
                gdf = gdf.to_crs("EPSG:4326")
                print(f" geof: {gdf.crs}")

            # IMPORTANDO VETORES LITOLÓGICOS
            litologia = importar(camada,nome)
            litologia.reset_index(inplace=True)
            if crs__=='proj':
                litologia = litologia.set_crs(32723, allow_override=True)
                litologia = litologia.to_crs("EPSG:32723")
                print(f" lito: {litologia.crs}")
            else:
                litologia = litologia.set_crs(4326, allow_override=True)
                litologia = litologia.to_crs("EPSG:4326")
                litologia=litologia.cx[row.region[0]:row.region[1],row.region[2]:row.region[3]]
                litologia.reset_index(inplace=True)
                print(f" lito: {litologia.crs}")
            

            print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_grids)} centróides de pixel")
            #print(f"# Listagem de unidade geológicas do mapa litologia['MAPA'].unique():")
            #print(f" {list(litologia['litologia'].unique())}")
            lito_geof = geof_grids
            lito_geof['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])
            print(f"# Listagem de unidades geológicas presentes na folha de id {index}:    ")
            print(f"  {list(lito_geof['closest_unid'].unique())}")

            # Adicionando lito_geof ao dicionario
            print('')
            print(f" Adicionando dataframe com valores de litologia e geofíscios ao dicionário de cartas")
            x = {index:lito_geof}
            dic_cartas['lito_geof'].update(x)
            #print(dic_cartas['lito_geof'][index].keys())

            print('__________________________________________')
        print(" ")
    print("Dicionário de cartas disponível")
    return dic_cartas



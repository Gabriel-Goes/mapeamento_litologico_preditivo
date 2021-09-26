import math
import numpy as np

import geopandas as gpd
import pandas as pd

import pyproj
from shapely import geometry

import verde as vd
import rioxarray as rio

import matplotlib.pyplot as plt

import tqdm

from tqdm.notebook import trange

gdb = '/home/ggrl/geodatabase/'
# ----------------------------------- DEFININDO FUNÇÕES PARA SCRIPT 
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
    bounds = gdf.bounds
    gdf['region'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]

    # Ajustando crs
    gdf = gdf.to_crs("EPSG:32723")
    # CRIANDOCOLUNA REGIONS EM COORDENADAS PROJETADAS
    bounds = gdf.bounds
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
        print('1# --- Iniciando seleção de área de estudo')
        malha_cartog_gdf_select = select_area(escala,id)
        malha_cartog_gdf_select.set_index('id_folha',inplace=True)
        print(f"Selecionada malha cartográfica: {malha_cartog_gdf_select.index}")

   
    # CRIANDO UM DICIONÁRIO DE CARTAS
    print(f"Retirada da coluna 'geometry' e indexando 'id_folha")
    malha_cartog_gdf_select.drop(columns=['geometry'],inplace=True)
    print(f"{malha_cartog_gdf_select[]}")
    dic_cartas = malha_cartog_gdf_select.to_dict()
    print(dic_cartas.keys())
    
    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas) > 1:
        print(f"Foram selecionadas {len(dic_cartas)} folhas cartográfica em escala de {escala} selecionadas")

    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas) == 1:
        print(f"Foi selecionada {len(dic_cartas)} folha cartográfica em escala de {escala} selecionada")
    
    return malha_cartog_gdf_select ,dic_cartas




# DEFININDO FUNÇÃO DE QUE CHAMARÁ AS FUNÇÕES ANTERIORES PROVOCANDO UM ENCADEAMENTO DE OPERAÇÕES  
def interpolar(escala,id,geof, interpolador_verde=True,nome=None,describe_data=True
):
    # DEFININDO PADRÃO DE INTERPOLAÇÃO VERDE
    if interpolador_verde == True:
        n_splits=False
        save=False
        crs__='proj'
        degree=2
        spacing=499
        psize=100
        
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
        else:
            lista_atributo_geof.append(atributo)
            
    print(f"Lista de atributos geofísicos = {lista_atributo_geof}")
    print(f"lista de atributos geograficos = {lista_atributo_geog}")
    print(f"lista de atributos projetados = {lista_atributo_proj}")

    
    # Dicionário de dados interpolados
    print(f"Criando dicionário de grids partir da lista de atributos")
    for atributo in lista_atributo_geof:
        grids = {atributo:()}
    print(grids.keys())
    
    # Dicionário validação cruzada
    print(f"Criando dicionário de scores partir da lista de atributos")
    scores = {lista_atributo_geof[0]:(),lista_atributo_geof[1]:(),lista_atributo_geof[2]:(), lista_atributo_geof[3]:(), lista_atributo_geof[4]:()}
    
    # Iterando entre itens da lista de folhas cartográficas
    for index, row in malha_cartog_gdf_select.iterrows():
        print(f"# --- Início da iteração da folha: {index} #")
        data = geof[vd.inside((geof.X, geof.Y), region = row.region_proj)]
        dic_cartas['data'] = {index:data}
        
        coordinates = (data.X.values, data.Y.values)
        dic_cartas['coordinates'] = {index:coordinates}

        if data.empty or len(data) < 1000:  # if data dont have values pass to next step
            print('não há dados aerogofísicos para folha cartográfica de id: '+index)
            print(f"A folha possui:  {len(data)} pontos coletados")

        else:
            print(f"com {len(data)} pontos de contagens radiométricas coletados a distâncias médias de {spacing} metros")
            print(f"# - Inicio da interpolação - # ")

            # Iterando entre os canais de interpolação
            for i in lista_atributo_geof:
                # Definindo encadeamento de processsos para interpolação
                chain = vd.Chain([
                                ('trend', vd.Trend(degree=degree)),
                                ('reduce', vd.BlockReduce(np.median, spacing=spacing)),
                                ('spline', vd.Spline())
                            ])
                
                chain.fit(coordinates, data[i])
                print(f"fit: {i}")
                # Griding the predicted data.  
                grid = chain.grid(spacing=psize, data_names=[i],pixel_register=True)
                grids[i] = vd.distance_mask(coordinates, maxdist=spacing, grid= grid)

                # Processo de validação cruzada da biblioteca verde
                if n_splits:
                    cv     = vd.BlockKFold(spacing=spacing,
                                n_splits=n_splits,
                                shuffle=True)

                    scores[i] = vd.cross_val_score(chain,
                                            coordinates,
                                            data[i],
                                            cv=cv)

                # Salvar os dados interpolados em formato .tif
                if save:
                    print('salvando '+index+' '+i)
                    #grids[i].to_netcdf(gdb+'/grids/geof_3022_'+str(psize)+'m_'+i+'_'+row.id_folha+'.nc')
                    tif_ = grids[i].rename(easting = 'x',northing='y')
                    tif_.rio.to_raster(gdb+'grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif')
                    
        print(f"# - Fim da interpolação - #")

        # Descrição estatisica das contagens
        if describe_data:
            dataframe = list()
            for i in lista_atributo_geof:
                df = grids[i].to_dataframe()
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


            #litologia=importar(lito,"Rio de Janeiro")
            litologia = importar('l_100k',nome)
            litologia.reset_index(inplace=True)
            if crs__=='proj':
                litologia = litologia.set_crs(32723, allow_override=True)
                litologia = litologia.to_crs("EPSG:32723")
                print(f" lito: {litologia.crs}")
            else:
                litologia = litologia.set_crs(4326, allow_override=True)
                litologia = litologia.to_crs("EPSG:4326")
                print(f" lito: {litologia.crs}")

            print(f"# Lista 'SIGLA' do mapa {litologia['MAPA'].unique()}:")
            print(f" {list(litologia['SIGLA'].unique())}")

            print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_grids)} centróides de pixel")
            geof_grids['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])

            print(f"# siglas de unidades litológicas presentes na folha de id {index}:    ")
            print(f"  {list(geof_grids['closest_unid'].unique())}")
            
            # Adicionando grids ao dicionario
            print(f"# Adicionando geof com {len(geof_grids)} canais ao dicionário de cartas")
            #lista_geof.append(geof_grids)
            dic_cartas['geof']= geof_grids

            # Adicionando scores ao dicionario
            print(f"# Adicionando scores com {len(scores)} blocks ao dicionário de cartas")
            dic_cartas['scores'] = scores
            
        print(f"# --- Fim da iteração da folha: {index} #")
        print('__________________________________________')
    return malha_cartog_gdf_select, dic_cartas

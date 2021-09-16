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


# Definindo Regions (W,E,S,N)
def regions(gdf):
    # Region em coordenadas Projetadas
    bounds = gdf.bounds 
    gdf['region'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]
    
    # Region em coordenadas Projetadas    #gdf = gdf.set_crs(32723, allow_override=True)
    gdf = gdf.to_crs("EPSG:32723")
    bounds = gdf.bounds 
    gdf['region_proj'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                          bounds['miny'],bounds['maxy'])]
    
    return gdf
        

# Definindo nomes da malha a partir da articulação sistematica de folhas de cartas. Construindo uma lista e definindo como uma series.
def nomeador_malha(gdf):
    df = pd.DataFrame(gdf)
    lista_grid = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_grid(row.region[0],row.region[1],
                                         row.region[3],row.region[2],escala=5))
        lista_grid.append(row.id_folha)

    gdf['id_folha'] = lista_grid

# Selecionador de Região
def select_area(escala,id):
    malha_cartog = importar('malha_cartog_'+escala+'_wgs84')
    marlha_cartog_gdf_select = malha_cartog[malha_cartog['id_folha'].str.contains(id)]       # '.contains' não é ideal.
    marlha_cartog_gdf_select = regions(area)    
    
    return(marlha_cartog_gdf_select)

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
    
# Script para interpolação de aerolevantamentos geofísicos. ####################################################################
def interpolar(escala,id,geof,degree=2,spacing=499,psize=100,n_splits=False,save=False,lista_canal=['CTCOR','eU','eth','MDT','KPERC'],describe_data=True,nome='Rio Paraim'):
    # Definindo encadeamento de processsos para interpolação
    chain = vd.Chain([
                    ('trend', vd.Trend(degree=degree)),
                    ('reduce', vd.BlockReduce(np.median, spacing=spacing)),
                    ('spline', vd.Spline())
                ])
    
    # Listando regiões das folhas cartográficas
    marlha_cartog_gdf_select = select_area(escala,id)
    break
    
    # Apenas uma folha de carta
    if (malha_cartografica.shape[0]) > 1:
        print(f"#{len(malha_cartografica)} folhas cartográfica em escala de {escala} selecionadas: {list(malha_cartografica['id_folha'])}")
        
    # Mais de uma folha de carta
    if len(malha_cartografica) == 1:
        print(f"#{len(malha_cartografica)} folha cartográfica em escala de {escala} selecionada: {list(malha_cartografica['id_folha'])}")
        
    #cartas = malha_cartografica['id_folha'].to_dict()
                    
    # Listando colunas do dado aerogeofísico
    print(f"Lista de atributos:  {list(geof.columns)}")
    
    # Dicionário de dados interpolados
    grids = {lista_canal[0]:(),lista_canal[1]:(),lista_canal[2]:(),lista_canal[3]:(), lista_canal[4]:()}
    
    # Dicionário validação cruzada
    scores = {lista_canal[0]:(),lista_canal[1]:(),lista_canal[2]:(), lista_canal[3]:(), lista_canal[4]:()}
    
    # Iterando entre itens da lista de folhas cartográficas
    for n in trange(1):
        for index, row in malha_cartografica.iterrows():
            print(f"# -- Início da iteração da folha: {row.id_folha} #")
            print(f"# -- Recortando dados da folha: {row.id_folha} #")

            data = geof[vd.inside((geof.X, geof.Y), region = row.region_proj)]
            coordinates = (data.X.values, data.Y.values)

            #print('# Distribuição')
            #print(f"{data['CTCOR'].describe(percentiles = [0.02, 0.25, 0.50, 0.75, 0.995])}")
            #print('# Distribuição')
            #print(f"{data['eU'].describe(percentiles = [0.02, 0.25, 0.50, 0.75, 0.995])}")


            if data.empty or len(data) < 1000:  # if data dont have values pass to next step
                print('não há dados aerogofísicos para folha cartográfica de id: '+row.id_folha)
                print(f"A folha possui:  {len(data)} pontos coletados")

            else:
                print(f"# -- Inicio da interpolação -- # ")
                print(f"com {len(data)} pontos de contagens radiométricas coletados")

                # Iterando entre os canais de interpolação
                print("pipeline")
                print(f" {chain} ")
                for n in trange(1):
                    print('fit: ')
                    for i in lista_canal:
                        chain.fit(coordinates, data[i])
                        print(i)

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
                            print('salvando '+row.id_folha+' '+i)
                            #grids[i].to_netcdf(gdb+'/grids/geof_3022_'+str(psize)+'m_'+i+'_'+row.id_folha+'.nc')
                            tif_ = grids[i].rename(easting = 'x',northing='y')
                            tif_.rio.to_raster(gdb+'grids/geof_'+str(save)+'_'+str(psize)+'m_'+i+'_'+row.id_folha+'.tif')

                    print(f"# -- Fim da interpolação -- # {row.id_folha}'")

                    # Descrição estatisica das contagens
                    if describe_data:
                        dataframe = list()
                        for i in lista_canal:
                            df = grids[i].to_dataframe()
                            dataframe.append(df[i])
                        geof_grids = pd.concat(dataframe,axis=1, join='inner')
                        geof_grids.reset_index(inplace=True)

                        geof_grids['geometry'] =\
                             [geometry.Point(x,y) for x, y in zip(geof_grids['easting'], geof_grids['northing'])]

                        for n in trange(1):
                            print('Ajustando crs')
                            gdf = gpd.GeoDataFrame(geof_grids,crs=32723)
                            gdf = gdf.set_crs(32723, allow_override=True)
                            gdf = gdf.to_crs("EPSG:32723")
                            print(f" geof: {gdf.crs}")

                            #litologia=importar(lito,"Rio de Janeiro")
                            litologia = importar('l_100k',nome)
                            litologia.reset_index(inplace=True)
                            litologia = litologia.set_crs(32723, allow_override=True)
                            litologia = litologia.to_crs("EPSG:32723")
                            print(f" lito: {litologia.crs}")

                            print(f"# Listando de siglas de unidades litológicas do mapa {litologia['MAPA'].unique()}:       {list(litologia['SIGLA'].unique())} ") 

                            print(f"# Calculando geometria mais próxima para cada um dos {len(geof_grids)} pixels da folha {row.id_folha}")


                            geof_grids['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])

                            print(f"# siglas de unidades litológicas presentes na folha de id {row.id_folha}:    {list(geof_grids['closest_unid'].unique())}")
                            
                            
                            
                            
                            
                            #print('# Distribuição')
                            #print(f"{geof_grids['CTCOR'].describe(percentiles = [0.02, 0.25, 0.50, 0.75, 0.995])}")

                            #print('# Distribuição')
                            #print(f"{geof_grids['eU'].describe(percentiles = [0.02, 0.25, 0.50, 0.75, 0.995])}")
                            print(f"#{row.id_folha}'# -- Fim da iteração -- #'")
                            print('__________________________________________')


        return data, grids, geof_grids



import math
import numpy as np

import geopandas as gpd
import pandas as pd

import pyproj
from shapely import geometry

import verde as vd
import rioxarray as rio

import matplotlib.pyplot as plt

import Custom_Stats_fabio as csf

gdb = '/home/ggrl/geodatabase/'

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

'''
# Selecionador de ocorrências
def ocrr(substancia):
    ocorrencias= gpd.read_file(gdb+'database.gpkg',
                              driver= 'GPKG',
                              layer= 'ocorr_min')
    
    subs= ocorrencias
'''

# Nomeador de Grids
p1kk=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
p500k=[['V','Y'],['X','Z']]
p250k=[['A','C'],['B','D']]
p100k=[['I','IV'],['II','V'],['III','VI']]
p50k=[['1','3'],['2','4']]
p25k=[['NW','SW'],['NE','SE']]

def nomeador_grid(left,right,top,bottom,escala=5):
    if left>right:
        print('Oeste deve ser menor que leste')
    if top<bottom:
        print('Norte deve ser maior que Sul')
    
    else:
        folha=''
        if top<=0:
            folha+='S'
            north=False
            index=math.floor(-top/4)
        else:
            folha+='N'
            north=True
            index=math.floor(bottom/4)
        
        numero=math.ceil((180+right)/6)
        folha+=p1kk[index]+str(numero)

        
        lat_gap=abs(top-bottom)
        #p500k-----------------------
        if (lat_gap<=2) & (escala>=1):
            LO=math.ceil(right/3)%2==0
            NS=math.ceil(top/2)%2!=north
            folha+='_'+p500k[LO][NS]
        #p250k-----------------------
        if (lat_gap<=1) & (escala>=2):
            LO=math.ceil(right/1.5)%2==0
            NS=math.ceil(top)%2!=north
            folha+='_'+p250k[LO][NS]
        #p100k-----------------------
        if (lat_gap<=0.5) & (escala>=3):
            LO=(math.ceil(right/0.5)%3)-1
            NS=math.ceil(top/0.5)%2!=north
            folha+='_'+p100k[LO][NS]
        #p50k------------------------
        if (lat_gap<=0.25) & (escala>=4):
            LO=math.ceil(right/0.25)%2==0
            NS=math.ceil(top/0.25)%2!=north
            folha+='_'+p50k[LO][NS]
        #p25k------------------------
        if (lat_gap<=0.125) & (escala>=5):
            LO=math.ceil(right/0.125)%2==0
            NS=math.ceil(top/0.125)%2!=north
            folha+='_'+p25k[LO][NS]
        return folha

# Definindo Regions (W,E,S,N)
def regions(gdf):
    bounds = gdf.bounds 
    gdf['region'] = [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                                              bounds['miny'],bounds['maxy'])]

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
    regions(malha_cartog)
    area = malha_cartog[malha_cartog['id_folha'].str.contains(id)]       # '.contains' não é ideal.
    return(area)

# Selecionar Intersecção do aerolevantamento 1039
'''

'''
# Script para interpolação de aerolevantamentos geofísicos. ####################################################################
def interpolar(escala,id,geof,degree=False,spacing=499,psize=100,n_splits=False,save=False,lista_canal=['CTCOR','eU','eTH','MDT','KPERC'],describe_data=False,lito='l_1kk'):
    # Listando regiões das folhas cartográficas
    malha_cartografica = select_area(escala,id) 
    print(len(malha_cartografica))
    
    # Listando colunas do dado aerogeofísico
    print(geof.columns)
    grids = {lista_canal[0]:(),lista_canal[1]:(),lista_canal[2]:(),lista_canal[3]:(), lista_canal[4]:()}# Dicionário de dados interpolados
    scores = {lista_canal[0]:(),lista_canal[1]:(),lista_canal[2]:(), lista_canal[3]:(), lista_canal[4]:()}# Dicionário validação cruzada
      
    # Iterando entre itens da lista de folhas cartográficas
    for index, row in malha_cartografica.iterrows():
        print('Recortando '+row.id_folha)
        data = geof[vd.inside((geof.LONGITUDE, geof.LATITUDE), region = row.region)]
        coordinates = (data.X.values, data.Y.values)
        
        if data.empty or len(data) < 1000:  # if data dont have values pass to next step
            print('não há dados aerogofísicos para folha cartográfica de id: '+row.id_folha)
            print(f"A folha possui:  {len(data)}")
        
        else:
            print(f"A folha possui:  {len(data)}")
            # Iterando entre os canais de interpolação
            for i in lista_canal:
                print(i)
                chain = vd.Chain([
                    ('trend', vd.Trend(degree=degree)),
                    ('reduce', vd.BlockReduce(np.median, spacing=spacing)),
                    ('spline', vd.Spline())
                ])
                chain.fit(coordinates, data[i])
                                
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
                
                                           
            # Descrição estatisica das contagens
            if describe_data:
                # 
                dataframe = list()
                for i in lista_canal:
                    df = grids[i].to_dataframe()
                    dataframe.append(df[i])
                geof = pd.concat(dataframe,axis=1, join='inner')
                geof.reset_index(inplace=True)
                geof['geometry'] = [geometry.Point(x,y) for x, y in zip(geof['easting'], geof['northing'])]

                gdf = gpd.GeoDataFrame(geof,crs=32723)
                gdf = gdf.set_crs(32723, allow_override=True)

                #litologia=importar(lito,"Rio de Janeiro")
                litologia=importar('socorro_250k')
                litologia = litologia.set_crs(32723, allow_override=True)
                litologia.reset_index(inplace=True)
                
                geof['closest_unid'] = gdf['geometry'].apply(lambda x: litologia['litologia'].iloc[litologia.distance(x).idxmin()])  
                    
    return grids, data , geof
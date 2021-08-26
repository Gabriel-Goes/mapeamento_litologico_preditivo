import math
import numpy as np
import verde as vd

import geopandas as gpd
import pandas as pd


gdb = '/home/ggrl/geodatabase/'



# Importador de Litologias por escala
def importar(camada):
    lito =  gpd.read_file(gdb+'database.gpkg',
                        driver= 'GPKG',
                        layer= camada)
    return(lito)



# Selecionador de Mapas a partir do nome
def mapa(escala,nome):
    folha = escala[escala.MAPA == 'Carta geológica da folha '+nome]
    return(folha)

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




# Selecionador de Região
# Selecionar SF23 Folha Rio de Janeiro Escala 1:1.000.000
# Selecionar Intersecção do aerolevantamento 1039
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
##

def select_area(escala,id):
    malha_cartog = importar('malha_cartog_'+escala+'_wgs84')
    regions(malha_cartog)
    df=[]
    for i in id:
        print(i)
        df.append(pd.DataFrame(malha_cartog[malha_cartog['id_folha'].str.contains(i)]))
    return(df)

# Iterando entre as regions da malha cartográfica
def interpolar(escala,id,geof,degree=1,spacing=499,psize=100,n_splits=15,validate=False):
    chain_list = input('Liste canais a serem interpolados:')      # Lista de canais a serem interpolados
                                                      
    grids = {chain_list[0]:(),chain_list[1]:(),chain_list[2]:(),chain_list[3]:(), chain_list[4]:()}    # Dicionário para salvar os dados interpolados (grids)
    scores = {chain_list[0]:(),chain_list[1]:(),chain_list[2]:(), chain_list[3]:(), chain_list[4]:()}   # Dicionário para salvar os dados da validação cruzada
    
    df = select_area(escala,id)
       
    for index, row in df.iterrows():
        print(row.id_folha+' start')
        data = geof[vd.inside((geof.LONGITUDE, geof.LATITUDE), region = row.region)]
        coordinates = (data.X.values, data.Y.values)
        if data.empty == True:  # if data dont have values pass to next step
            print('none')
        if len(data) < 2000:    # if less then 2000 points pass to next step
            print('few data')
        else:
            # Iterando entre os canais de interpolação
            for i in chain_list:
                print(i)
                chain = vd.Chain([
                    ('trend', vd.Trend(degree=degree)),
                    ('reduce', vd.BlockReduce(np.median, spacing=spacing)),
                    ('spline', vd.Spline())
                ])
                
                chain.fit(coordinates, data[i])
                
                if validate == True:
                    cv     = vd.BlockKFold(spacing=spacing,
                                n_splits=n_splits,
                                shuffle=True)

                    scores[i] = vd.cross_val_score(chain,
                                            coordinates,
                                            data[i],
                                            cv=cv)
                    
                grid = chain.grid(spacing=psize, data_names=[i],pixel_register=True)
                grids[i] = vd.distance_mask(coordinates, maxdist=499, grid= grid)
                tif_ = grids[i].rename(easting = 'x',northing='y')
                tif_.rio.to_raster('/home/ggrl/Desktop/grids/3022/100m_25k/'+i+'_'+row.id_folha+'.tif')
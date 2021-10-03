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

####################################### LEMBRAR DE PEDIR AJUDA
from tqdm import tqdm
from tqdm.notebook import trange


# DEFININDO CAMINHO PARA A BASE DE DADOS
gdb = '/home/ggrl/geodatabase/'


# ---------------------------------------- DEFININDO FUNÇÕES PARA SCRIPT ---------------------------------------#

# IMPORTADOR DE DADOS AEROGEOFISICOS ---------------------------------------------------------------------------#
def importar_geof(raw_data):
    geof_dataframe = pd.read_csv(gdb+'/geof/'+str(raw_data))
    return geof_dataframe
# ----------------------------------------------------------------------------------------------------------------------

# IMPORTADOR DE LITOLOGIAS POR ESCALA --------------------------------------------------------------------------#
def importar(camada, mapa=False):
    lito =  gpd.read_file(gdb+'database.gpkg',
                        driver= 'GPKG',
                        layer= camada)
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]
        if folha.empty:
            print(f"O mapa escolhido nao est'a presente na coluna MAPA da camada veotiral.")
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")

            return(lito)

        else:    
            return(folha)
    else:
        return(lito)
# ----------------------------------------------------------------------------------------------------------------------
    
# DEFININDO LIMITES DE CADA FOLHA CARTOGRÁFICA -----------------------------------------------------------------#
def regions(gdf):
    # CRIANDO COLUNA REGION EM COORDENADAS GEOGRÁFICAS
    bounds = gdf.bounds

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
# ----------------------------------------------------------------------------------------------------------------------

# Nomeador de Grids ------------------------------------------------------------------------------------------#
def nomeador_grid(left,right,top,bottom,escala=5):
    e1kk=['A','B','C','D','E','F','G','H','I','J','K','L','M','N','O','P','Q','R','S','T','U','V','W','X','Y','Z']
    e500k=[['V','Y'],['X','Z']]
    e250k=[['A','C'],['B','D']]
    e100k=[['I','IV'],['II','V'],['III','VI']]
    e50k=[['1','3'],['2','4']]
    e25k=[['NW','SW'],['NE','SE']]

    if left>right:
        print('Oeste deve ser menor que leste')
    if top<bottom:
        print('Norte deve ser maior que Sul')
    
    else:
        id_folha=''
        if top<=0:
            id_folha+='S'
            north=False
            index=math.floor(-top/4)
        else:
            id_folha+='N'
            north=True
            index=math.floor(bottom/4)
        
        numero=math.ceil((180+right)/6)
        id_folha+=e1kk[index]+str(numero)

        lat_gap=abs(top-bottom)
        #p500k-----------------------
        if (lat_gap<=2) & (escala>=1):
            LO=math.ceil(right/3)%2==0
            NS=math.ceil(top/2)%2!=north
            id_folha+='_'+e500k[LO][NS]
        #p250k-----------------------
        if (lat_gap<=1) & (escala>=2):
            LO=math.ceil(right/1.5)%2==0
            NS=math.ceil(top)%2!=north
            id_folha+='_'+e250k[LO][NS]
        #p100k-----------------------
        if (lat_gap<=0.5) & (escala>=3):
            LO=(math.ceil(right/0.5)%3)-1
            NS=math.ceil(top/0.5)%2!=north
            id_folha+='_'+e100k[LO][NS]
        #p50k------------------------
        if (lat_gap<=0.25) & (escala>=4):
            LO=math.ceil(right/0.25)%2==0
            NS=math.ceil(top/0.25)%2!=north
            id_folha+='_'+e50k[LO][NS]
        #p25k------------------------
        if (lat_gap<=0.125) & (escala>=5):
            LO=math.ceil(right/0.125)%2==0
            NS=math.ceil(top/0.125)%2!=north
            id_folha+='_'+e25k[LO][NS]
        return id_folha
# ----------------------------------------------------------------------------------------------------------------------

# DEFININDO NOMES DA MALHA A PARTIR DA ARTICULA~AO SISTEMÁTICA DE FOLHAS DE CARTAS. 
# CONSTURINDO UMA LISTA E DEFININDO COMO UMA SERIES (OBJETO DO PANDAS).
def nomeador_malha(gdf):
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_grid(row.region[0],row.region[1],
                                         row.region[3],row.region[2],escala=5))
        lista_malha.append(row.id_folha)

    gdf['id_folha'] = lista_malha
# ----------------------------------------------------------------------------------------------------------------------

# SELECIONADOR DE REGIÃO  ------------------------------------------------------------------------------------------#
def select_area(escala,id):
    malha_cartog = importar('malha_cartog_'+escala+'_wgs84')
    malha_cartog_gdf_select = malha_cartog[malha_cartog['id_folha'].str.contains(id)]       # '.contains' não é ideal.
    malha_cartog_gdf_select = regions(malha_cartog_gdf_select)    
    
    return(malha_cartog_gdf_select)
# ----------------------------------------------------------------------------------------------------------------------

# LISTANDO REGIÕES DE CADA FOLHA DE CARTAS DA MALHA CARTOGRÁFICA \ ['REGEION'] = ['ID_FOLHA'] REDUNDANCIA
def cartas(escala,id):
    # SELECIONANDO AREA DE ESTUDO
    if escala and id:
        print('# --- Iniciando seleção de área de estudo')
        malha_cartog_gdf_select = select_area(escala,id)
        #print("Indexando a coluna 'id_folha'") 
        malha_cartog_gdf_select.set_index('id_folha',inplace=True)
        #print(list(malha_cartog_gdf_select.index))              

    lista_cartas = list(malha_cartog_gdf_select.index)
   
    # CRIANDO UM DICIONÁRIO DE CARTAS
    #print(f"Retirada da coluna 'geometry'")
    malha_cartog_df_select = malha_cartog_gdf_select.drop(columns=['geometry'])
    malha_cartog_df_select['raw_data'] =''
    malha_cartog_df_select['interpolado'] =''
    malha_cartog_df_select['scores'] =''
    malha_cartog_df_select['lito_geof'] =''
    malha_cartog_df_select['mean_score'] =''
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

# LISTANDO ATRIBUTOS GEOFÍSICOS E ATRIBUTOS GEOGRÁFICOS
def list_atributos(geof):
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
    print(f"# --- # Listagem de dados do aerolevantamento:  ")
    print(f"Lista de atributos geofísicos = {lista_atributo_geof}")
    print(f"lista de atributos geograficos = {lista_atributo_geog}")
    print(f"lista de atributos projetados = {lista_atributo_proj}")
    return lista_atributo_geof, lista_atributo_geog, lista_atributo_proj
# ----------------------------------------------------------------------------------------------------------------------

# DESCRIÇÃO DOS DADOS AEROGEOFÍSICOS
def descricao(geof):            
    lista_atributo_geof,lista_atributo_geog,lista_atributo_proj = list_atributos(geof)  # USANDO FUNCAO DEFINIDA ACIMA PARA CATEGORIZAR METADADO
    
    metadatadict = pd.DataFrame(geof.dtypes)
    metadatadict["Valores Faltantes"] = geof.isnull().sum()
    metadatadict["Valores Únicos"] = geof.nunique()
    metadatadict["Amostragem"] = geof.count()
    metadatadict = metadatadict.rename(columns = {0 : 'dType'})

    lista_negativo=[]
    for i in lista_atributo_geof:
        lista_negativo.append(geof.query(i+' < 0')[i].count())


    geof_df = geof.drop(axis=0,columns=lista_atributo_geog)
    geof_df.drop(axis=0,columns=lista_atributo_proj,inplace=True)

    #datadict['Valores Negativos'] = lista_negativo

    geof_df_describe = geof_df.describe(percentiles=[0.001,0.1,0.25,0.5,0.75,0.995])
    
    return metadatadict,lista_atributo_geof,lista_atributo_geog,lista_atributo_proj,geof_df_describe


# CRIANDO DICIONARIO DE FOLHAS CARTOGRAFICAS PARA CARA TIPO DE DADO
def get_region(escala,id,geof):
    geof_dataframe = importar_geof(geof)                          # importa dado bruto
    
    # LISTANDO REGIOES DAS FOLHAS DE CARTAS
    lista_cartas, dic_cartas,malha_cartog_gdf_select = cartas(escala,id)       # importa malha cartografica
        
    # DESCREVENDO ATRIBUTOS ESTATISTICOS DOS DADOS    
    metadatadict,        \
    lista_atributo_geof, \
    lista_atributo_geog, \
    lista_atributo_proj, \
    geof_df_describe     = descricao(geof_dataframe)              # lista atributos e descreve metadados e estatisticas do dado

    # ITERANDO ENTRE AS FOLHAS DE CARTAS
    print("")
    print(f"# --- Início da iteração entre as folhas cartográficas #")

    for index, row in malha_cartog_gdf_select.iterrows():
        # RECORTANDO DATA PARA CADA FOLHA COM ['region.proj']
        data = geof_dataframe[vd.inside((geof_dataframe.X, geof_dataframe.Y), region = row.region_proj)]
        #del geof_dataframe
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
            print(f" com {len(data)} pontos")

    dic_meta={'Lista_id':lista_cartas,
              'Lista_at_geof':lista_atributo_geof,
              'Lista_at_geog':lista_atributo_geog,
              'Lista_at_proj':lista_atributo_proj}

    return dic_cartas,dic_meta,malha_cartog_gdf_select,geof_df_describe


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
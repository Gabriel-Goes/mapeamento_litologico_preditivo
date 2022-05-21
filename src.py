# Imports
import geopandas as gpd
import pandas as pd
import fiona
#from setuptools_scm import meta
from tqdm import tqdm
import verde as vd
from shapely import geometry
import numpy as np
import matplotlib.pyplot as plt
import math
import pyproj
from shapely.ops import transform

# -----------------------------------------------------------------------------
def set_gdb(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/database/'

        path : caminho até o  arquivo desejado
    '''
    gdb = '/home/ggrl/database/' + path
    return gdb
# -----------------------------------------------------------------------------
def importar_geometrias(camada=None, mapa=None):
    '''
    Recebe:
        camada      : camada vetorial a ser lida do geopackage.
        mapa        : nome do mapa presente na camada vetorial;

    Retorna:
        Objeto GeoDataFrame.
    Se houver seleçao de mapa retornara apenas as geometrias que possuem o nome 
    escolhido na coluna ['MAPA']
    Se Retornar camada vazia recebera a lista das camadas veotoriais diposniveis
    Se mapa == False: retorna todos os objetos presente nesta camada vetorial
    '''
    lito = gpd.read_file(set_gdb('geodatabase.gpkg'),
                         driver='GPKG',
                         layer=camada)
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha ' + mapa]
        if len(folha) == 0:
            print("O mapa escolhido nao est'a presente na coluna MAPA da camada veotiral. Os mapas disponiveis serao listados a seguir.")
            print('# Selecionando apenas os caracteres apos ''folha'' (SEM ESPAÇO)')
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")
            lista_mapas = list(lito.MAPA.unique())
            return lista_mapas
        return folha
    else:
        return lito
# -----------------------------------------------------------------------------
def import_malha_cartog(escala='25k',ID=None,IDs=None):
    mc = gpd.read_file(set_gdb('geodatabase.gpkg'),
                                 driver='GPKG',
                                 layer='mc_' + escala)
                                 
    if IDs:
        mc_slct = gpd.GeoDataFrame()
        for id in tqdm(IDs):
            mc_slct = mc_slct.append(mc[mc['id_folha'] == id])

    elif ID: 
        mc_slct = mc[mc['id_folha'].str.contains(ID)]

        return mc_slct

    else:
        return mc
# -----------------------------------------------------------------------------
def import_mc(escala=None,ID=None):
    mc = gpd.read_file(set_gdb('geodatabase.gpkg'),driver='GPKG',layer='mc_'+escala)
    mc_slct = gpd.GeoDataFrame()
    if ID:
        for id in tqdm(ID):
            mc_slct = mc_slct.append(mc[mc['id_folha'].str.contains(id)])
        return mc_slct
    else:
        return mc
# -----------------------------------------------------------------------------
def import_xyz(caminho):
    '''
    '''
    dataframe = pd.read_csv(caminho)

    return dataframe
# ----------------------------------------------------------------------------------------------------------------------
def dado_bruto(camada=None, mapa=None, geof=None):

    '''
    Recebe:
        __camada : Camada vetorial presento no geopackage;
        __mapa   : Nome da folha cartografica presenta na coluna 'MAPA' da 
                   camada vetorial 
        (SE NAO INSERIR MAPA RETORNA TODOS OS VETORES DA CAMADA SELECIONADA);
        __geof   : Dados dos aerolevantamentos. gama_tie, gama_line, 
    '''
    print(f'Diretório de dados aerogeofisicos brutos: {set_gdb(geof)}')
    geof_dataframe = import_xyz(geof)
    path_lito = set_gdb('geodatabase.gpkg')
    print(f'Diretório de dados litologicos brutos: {path_lito}')
    lito = gpd.read_file(path_lito,
                         driver='GPKG',
                         layer=camada)
    print('')
    print(f"# -- Lista de camadas vetoriais disponíveis: {fiona.listlayers(path_lito)}")
    if lito.empty:
        raise "# FALHA : A camada escolhida nao está presente no geopackage."
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha ' + mapa]
        if folha.empty:
            print('')
            print("O mapa escolhido não está presente na coluna MAPA da camada veotiral.")
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")
        else:
            return folha, geof_dataframe
    else:
        return lito, geof_dataframe
# -----------------------------------------------------------------------------
def nomeador_grid(left,right,top,bottom,escala=5):
    e1kk=['A','B','C','D','E','F','G','H','I','J','K','L','M','N']
    e500k=[['V','Y'],['X','Z']]
    e250k=[['A','C'],['B','D']]
    e100k=[['I','IV'],['II','V'],['III','VI']]
    e50k=[['2','3'],['2','4']]
    e25k=[['NW','SW'],['NE','SE']]
    if left>right:
        print('Oeste deve ser menor que leste')
    if top<bottom:
        print('Norte deve ser maior que Sul')
    else:
        id_folha=''
        if top<=0:
            id_folha+='S'
            index=math.floor(-top/4)
        else:
            id_folha+='N'
            index=math.floor(bottom/4)
        numero=math.ceil((180+right)/6)
        print(numero)
        id_folha+=e1kk[index]+str(numero)
        lat_gap=abs(top-bottom)
        #p500k-----------------------
        if (lat_gap<=2) & (escala>=1):
            LO=math.ceil(right/3)%2==0
            NS=math.ceil(top/2)%2!=0
            id_folha+='_'+e500k[LO][NS]
        #p250k-----------------------
        if (lat_gap<=1) & (escala>=2):
            LO=math.ceil(right/1.5)%2==0
            NS=math.ceil(top)%2!=0
            id_folha+=e250k[LO][NS]
        #p100k-----------------------
        if (lat_gap<=0.5) & (escala>=3):
            LO=(math.ceil(right/0.5)%3)-1
            NS=math.ceil(top/0.5)%2!=0
            id_folha+='_'+e100k[LO][NS]
        #p50k------------------------
        if (lat_gap<=0.25) & (escala>=4):
            LO=math.ceil(right/0.25)%2==0
            NS=math.ceil(top/0.25)%2!=0
            id_folha+='_'+e50k[LO][NS]
        #p25k------------------------
        if (lat_gap<=0.125) & (escala>=5):
            LO=math.ceil(right/0.125)%2==0
            NS=math.ceil(top/0.125)%2!=0
            id_folha+=e25k[LO][NS]

        return id_folha
# -----------------------------------------------------------------------------
def set_EPSG(mc):
    EPSG=[]
    for i in mc['id_folha']:
        if i[:1] == 'S':
            EPSG.append('327'+str(i[2:4]))
        else:
            EPSG.append('326'+str(i[2:4]))
    mc['EPSG']=EPSG
    return mc
        
# -----------------------------------------------------------------------------
def nomeador_malha(gdf):
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (td.nomeador_grid(row.region[0], row.region[1],
                                            row.region[3], row.region[2], escala=5))
        lista_malha.append(row.id_folha)
    gdf['id_folha'] = lista_malha
# -----------------------------------------------------------------------------
def regions(mc):
    bounds = mc.bounds
    for index,row in mc.iterrows():
        mc['region'] = [(left, right, bottom, top) for
                                    left, right, bottom, top in
                                    zip(bounds['minx'],bounds['maxx'],
                                        bounds['miny'],bounds['maxy'])]
        
        crs__= row.EPSG
        mc_proj=mc.to_crs("EPSG:"+str(crs__))
        bounds_proj = mc_proj.bounds
        mc['region_proj'] = [(left, right, bottom, top) for 
                                left, right, bottom, top in 
                                    zip(bounds['minx'], bounds['maxx'],
                                        bounds['miny'], bounds['maxy'])]
    return mc
# -----------------------------------------------------------------------------
def cartas(escala=None,ids=None):
    print('# --- Iniciando seleção de área de estudo')
    mc_select = import_malha_cartog(escala,ids)
    regions(mc_select)
    mc_select.set_index('id_folha', inplace=True)
    # CRIANDO UM DICIONÁRIO DE CARTAS
    print('# --- Construindo Dicionario de Cartas')
    mc_select['raw_data'] = ''
    dic_cartas = mc_select.to_dict()
    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) > 1:
        print(f"{len(dic_cartas['raw_data'])} folhas cartográfica selecionadas")
        print("")
    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) == 1:
        print(f"{len(dic_cartas['raw_data'])} folha cartográfica selecionada")
        print("")
    
    return dic_cartas, mc_select
# -----------------------------------------------------------------------------
def lista_cols(geof):
    print('Listando atributos dos dados geofisicos')
    atributos_geof = list(geof.columns)  # DataFrame.columns
    lista_atributo_geof = []
    lista_atributo_geog = []
    lista_atributo_proj = []
    for atributo in tqdm(atributos_geof):
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
    codigo = str(geof)
    print(f"# --- # Listagem de dados do aerolevantamento:  ")
    print(f"Lista de atributos geofísicos = {lista_atributo_geof}")
    print(f"lista de atributos geograficos = {lista_atributo_geog}")
    print(f"lista de atributos projetados = {lista_atributo_proj}")

    return lista_atributo_geof, lista_atributo_geog, lista_atributo_proj
# ----------------------------------------------------------------------------------------------------------------------
def descricao(geof):
    lista_at_geof, lista_at_geog, lista_at_proj = lista_cols(geof)
    metadatadict = pd.DataFrame(geof.dtypes)
    metadatadict["Valores Faltantes"] = geof.isnull().sum()
    metadatadict["Valores Únicos"] = geof.nunique()
    metadatadict["Valores Negativos"] = sum(n < 0 for n in geof.values)
    metadatadict["Amostragem"] = geof.count()
    metadatadict = metadatadict.rename(columns={0: 'dType'})
    geof_df = geof.drop(axis=0, columns=lista_at_geog)
    geof_df.drop(axis=0, columns=lista_at_proj, inplace=True)
    geof_descrito = geof_df.describe(percentiles=[0.001, 0.1, 0.25, 0.5, 0.75, 0.995])

    return metadatadict, lista_at_geof, lista_at_geog, lista_at_proj, geof_descrito
# ----------------------------------------------------------------------------------------------------------------------
def metadataframe(GeoDataFrame):
    '''
    Recebe: GeoDataFrame (Features and Geometry)
        Retorna: An object Pandas DataFrame containing a MetaData description of the GeoPandas Object GeoDataFrame
    '''
    meta_lito = pd.DataFrame(
        GeoDataFrame.dtypes)  # Describe the dtype of each column from the DataFrame or, better saying, GeoDataFrame;
    meta_lito['Valores null'] = GeoDataFrame.isnull().sum()  # Describe the sum of each null value from our object
    meta_lito[
        'Valores unicos'] = GeoDataFrame.nunique()  # Describe the number of unique values from our object, that is a GeoDataFrame
    meta_lito = meta_lito.rename(
        columns={0: 'dType'})  # Rename the first column to 'dtype', the name of the function we used.

    return meta_lito
# ----------------------------------------------------------------------------------------------------------------------
def describe_geologico(gdf):
    lista_colunas = list(gdf.columns)
    lista_litotipos = list(gdf.LITOTIPOS.unique())
    lista_legenda = list(gdf.LEGENDA.unique())

    dic_litologico = {'lista_colunas': lista_colunas,
                      'lista_litotipos': lista_litotipos,
                      'lista_legenda': lista_legenda}
    return dic_litologico
# ----------------------------------------------------------------------------------------------
'''
def set_region(escala, id, geof, camada, mapa=None,crs__=None):
    Recebe:
        escala : Escalas disponíveis para recorte: '50k', '100k', '250k', '1kk'.
            id : ID da folha cartográfica (Articulação Sistemática de Folhas Cartográficas)
          geof : Dado aerogeofísico disponível na base de dados (/home/ggrl/database/geof/)
        camada : Litologias disponíveis na base de dados (/home/ggrl/database/geodatabase.gpkg)
        mapa   : Nome do mapa caso necessário.

    # LISTANDO REGIOES DAS FOLHAS DE CARTAS
    print('')
    print('# - Selecionando Folhas Cartograficas')
    dict_cartas, mc_select = cartas(escala, id)
    dict_cartas['litologia'] = {}
    # Importando dados litológicos e geofísicos
    print('')
    print('# Importando dados')
    geof_df = import_xyz(set_gdb(geof))
    litologia = importar_geometrias(camada, mapa)
    print('')
    print('# -- Contruindo dicionario de metadados')
    metadatadict,\
    lista_at_geof,\
    lista_at_geog,\
    lista_at_proj,\
    geof_descrito=descricao(geof_df)
    dic_raw_meta = {'Metadata': metadatadict,
                    'Lista_at_geof': lista_at_geof,
                    'Lista_at_geog': lista_at_geog,
                    'Lista_at_proj': lista_at_proj,
                    'Percentiles': geof_descrito,
                    'Malha_cartografica': mc_select}
    print('')
    print(f"# --- Início da iteração entre as folhas cartográficas #")
    for index, row in tqdm(mc_select.iterrows()):
        data = geof_df[vd.inside((geof_df.X,
                                  geof_df.Y),
                                  region=row.region_proj)]
        crs__= row.EPSG
        if len(data) < 10000 & len(data) > 0:
            y = {index:litologia}
            dict_cartas['litologia'].update(y)
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            print(f" Atualizando dados geofísicos brutos em dic_cartas['raw_data']['{index}']")
            x = {index:data}
            dict_cartas['raw_data'].update(x) 
            print(f" com {len(data)} pontos de amostragem")
        if len(data) >= 10000:
            print('')
            print(f"# Folha de código: {index}")
            print(f" - Atualizando dados geofísicos em dic_cartas['raw_data']['{index}']")
            x = {index: data}
            dict_cartas['raw_data'].update(x)
            print(f" com {len(data)} pontos de amostragem.")
            litologia.to_crs('EPSG:'+crs__, inplace=True)
            lito_cut = litologia.cx[row.region_proj[0]:row.region_proj[1],
                                     row.region_proj[2]:row.region_proj[3]]
            print(f" - Atualizando dados litológicos em dic_cartas['litologia']['{index}']")
            print(f" com {lito_cut.shape[0]} polígonos descritos por: {lito_cut.shape[1]} atributos geológicos ")
            print(lito_cut.crs)
            y={index:lito_cut}
            dict_cartas['litologia'].update(y)
        elif data.empty:
            None
            print('')
            print(f'Folha de código {index} sem dados Aerogeofisicos')

    return dict_cartas, dic_raw_meta
'''
# --------------------------------------------------------------------------------------
def batch_verde(dic_cartas=None, dic_raw_meta=None):
    lista_at_geof = dic_raw_meta['Lista_at_geof']
    dic_cartas['splines'] = {}
    for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):
        data = dic_cartas['raw_data'][index]
        y = {index:{}}
        dic_cartas['splines'].update(y)
        if len(data) == 0:
            None
            print('Folha {index} sem dados aerogeofísicos.')
        elif len(data) < 10000:
            None
            print(
                f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
        else:
            print(f"# Folha de código: {index}")
            print(f" Retirando dados brutos em dic_cartas['raw_data']['{index}']")
            print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de 500 metros")
            coordinates = (data.X.values.astype(float), data.Y.values.astype(float))
            #region = dic_cartas['region_proj'][index]
            chain = vd.Chain([('trend',  vd.Trend(degree=1)),
                              ('reduce', vd.BlockReduce(np.mean, spacing=1000)),
                              ('spline', vd.Spline())])
            for i in tqdm(lista_at_geof):
                chain.fit(coordinates,data[i])
                grid = chain.grid(spacing=200,data_names=[i],pixel_register=True)                
                y = {i:''}
                dic_cartas['splines'][index].update(y)
                dic_cartas['splines'][index][i]=vd.distance_mask(coordinates,maxdist=500,grid=grid)
                print(f" Atualizando dic_cartas['splines']['{index}']['{i}']")
                print('__________________________________________')
        print(" ")
    print("Dicionário de cartas disponível")

    return dic_cartas, dic_raw_meta
# ---------------------------------------------------------------------------- 
def interpolar(splines=None,cubico=None,mag=None, gama=None, geof=None,dic_cartas=None, dic_raw_meta=None):
    if splines:
        dic_cartas['splines'] = {}
        print('# Inicio dos processos de interpolação pelo método cúbico')
        for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):
            dic_cartas['splines']
            lista_at_geof = dic_raw_meta['Lista_at_geof']
            data = dic_cartas['raw_data'][index]
            # GERANDO TUPLA DE COORDENADAS
            if len(data) == 0:
                None
                print('Folha {index} sem dados aerogeofísicos.')
            elif len(data) < 10000:
                None
                print(
                    f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            else:
                print(f"# Folha de código: {index}")
                print(f" Retirando dados brutos em dic_cartas['raw_data']['{index}']")
                print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de 500 metros")
                coordinates = (data.X.values, data.Y.values)
                region = dic_cartas['region_proj'][index]
                chain = vd.Chain([('trend',  vd.Trend(degree=1)),
                                  ('reduce', vd.BlockReduce(np.mean, spacing=1000)),
                                  ('spline', vd.Spline())])
                print(f"# Folha de código: {index}")
                print(f" Atualizando dados brutos em dic_cartas['raw_data']")
                cv     = vd.BlockKFold(spacing=1000,
                                       n_splits=5,
                                       shuffle=True)
                for i in lista_at_geof:
                    chain.fit(coordinates,data[i])
                    grid = chain.grid(spacing=200,data_names=[i],pixel_register=True)
                    grids[i]=vd.distance_mask(coordinates,maxdist=1000,grid=grid)
                y = {index: grids}
                dic_cartas['splines'].update(y)
                print('__________________________________________')
            print(" ")
        print("Dicionário de cartas disponível")
# ----------------------------------------------------------------------------------------------    
    if cubico:
        dic_cartas['cubic'] = {'': ''}
        print('# Inicio dos processos de interpolação pelo método cúbico')
        for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):
            print(index, row)
            lista_atributo_geof = dic_raw_meta['Lista_at_geof']
            data = dic_cartas['raw_data'][index]
            if len(data) == 0:
                None
            elif len(data) < 10000:
                None
                print(
                    f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            else:
                print(f"# Folha de código: {index}")
                print(f" Retirando dados brutos em dic_cartas['raw_data']['{index}']")
                print(f" com {len(data)} pontos de contagens radiométricas coletados com linhas de voo de 500 metros")
                data['geometry'] = [geometry.Point(x, y) for x, y in zip(data['X'], data['Y'])]
                crs = "+proj=utm +zone="+crs__+" +south +ellps=WGS84 +datum=WGS84 +units=m +no_defs"
                gdf_geof = gpd.GeoDataFrame(data, geometry='geometry', crs=crs)
                area = dic_cartas['region_proj'][index]
                xu, yu = td.regular(shape=(1272, 888),
                                    area=area)
                if geof:
                    CTC = np.array(gdf_geof.CTC)
                    THC = np.array(gdf_geof.THC)
                    UC = np.array(gdf_geof.UC)
                    KC = np.array(gdf_geof.KC)
                    MAGR = np.array(gdf_geof.MAGR)
                    ALTE = np.array(gdf_geof.ALTE)
                    x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)
                    alte_ = td.interp_at(x2, y2, ALTE, xu, yu, algorithm='cubic', extrapolate=True)
                    uc_ = td.interp_at(x2, y2, UC, xu, yu, algorithm='cubic', extrapolate=True)
                    kc_ = td.interp_at(x2, y2, KC, xu, yu, algorithm='cubic', extrapolate=True)
                    ctc_ = td.interp_at(x2, y2, CTC, xu, yu, algorithm='cubic', extrapolate=True)
                    thc_ = td.interp_at(x2, y2, THC, xu, yu, algorithm='cubic', extrapolate=True)
                    magr_ = td.interp_at(x2, y2, MAGR, xu, yu, algorithm='cubic', extrapolate=True)
                    # intialise data of lists.
                    data = {'X': xu, 'Y': yu, 'MAGIGRF': magr_, 'ALTE': alte_,
                            'CTC': ctc_, 'KC': kc_, 'UC': uc_, 'THC': thc_}
                    # Create DataFrame 
                    # Atualizando chave 'cubic' com dados interpolados
                    y = {index: interpolado_cubico}
                    dic_cartas['cubic'].update(y)
                if mag:
                    ALTURA = np.array(gdf_geof.ALTURA)
                    MAGIGRF = np.array(gdf_geof.MAGIGRF)
                    MDT = np.array(gdf_geof.MDT)
                    x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)
                    altura_ = td.interp_at(x2, y2, ALTURA, xu, yu, algorithm='cubic', extrapolate=True)
                    mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm='cubic', extrapolate=True)
                    magigrf_ = td.interp_at(x2, y2, MAGIGRF, xu, yu, algorithm='cubic', extrapolate=True)
                    # intialise data of lists. 
                    data_interpolado = {'X': xu, 'Y': yu, 'MDT': mdt_,
                                        'KPERC': altura_, 'eU': magigrf_}
                    # Create DataFrame 
                    interpolado_cubico = pd.DataFrame(data_interpolado)
                    # Print the output 
                    y = {index: interpolado_cubico}
                    dic_cartas['cubic'].update(y)
                if gama:
                    CTCOR = np.array(gdf_geof.CTCOR)
                    MDT = np.array(gdf_geof.MDT)
                    eTh = np.array(gdf_geof.eTH)
                    eU = np.array(gdf_geof.eU)
                    KPERC = np.array(gdf_geof.KPERC)
                    THKRAZAO = np.array(gdf_geof.THKRAZAO)
                    UKRAZAO = np.array(gdf_geof.UKRAZAO)
                    UTHRAZAO = np.array(gdf_geof.UTHRAZAO)
                    x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)
                    eTh_ = td.interp_at(x2, y2, eTh, xu, yu, algorithm='cubic', extrapolate=True)
                    eu_ = td.interp_at(x2, y2, eU, xu, yu, algorithm='cubic', extrapolate=True)
                    kperc_ = td.interp_at(x2, y2, KPERC, xu, yu, algorithm='cubic', extrapolate=True)
                    ctcor_ = td.interp_at(x2, y2, CTCOR, xu, yu, algorithm='cubic', extrapolate=True)
                    mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm='cubic', extrapolate=True)
                    uthrazao_ = td.interp_at(x2, y2, UTHRAZAO, xu, yu, algorithm='cubic', extrapolate=True)
                    ukrazao_ = td.interp_at(x2, y2, UKRAZAO, xu, yu, algorithm='cubic', extrapolate=True)
                    thkrazao_ = td.interp_at(x2, y2, THKRAZAO, xu, yu, algorithm='cubic', extrapolate=True)
                    # intialise data of lists. 
                    data = {'X': xu, 'Y': yu, 'MDT': mdt_, 'CTCOR': ctcor_,
                            'KPERC': kperc_, 'eU': eu_, 'eTH': eTh_,
                            'UTHRAZAO': uthrazao_, 'UKRAZAO': ukrazao_, 'THKRAZAO': thkrazao_}
                    # Create DataFrame 
                    interpolado_cubico = pd.DataFrame(data)
                    y = {index: interpolado_cubico}
                    dic_cartas['cubic'].update(y)
                print('__________________________________________')
            print(" ")
        print("Dicionário de cartas disponível")

    return dic_cartas, dic_raw_meta
# --------------------------------------------------------------------------------------
# RETIRANDO VALORES DE LITOLOGIA DE CADA PIXEL
def describe(dic_cartas, dic_raw_data, crs__, tdm, ):
    print("")
    print(f"# --- Inicio da análise geoestatística")
    lista_interpolado = list()
    for index in dic_cartas:
        # IMPORTANDO VETORES LITOLÓGICOS ------------
        litologia = dic_cartas['litologia'][index]
        litologia.reset_index(inplace=True)

        if crs__ == 'proj':
            litologia.to_crs(crs__, inplace=True)
            print(f" lito: {litologia.crs}")
        else:
            litologia.to_crs(4326, inplace=True)
            print(f" lito: {litologia.crs}")
        # -------------------------------------------
        # GRID POR CUBICO
        if tdm:
            for i in tqdm(dic_raw_data['lista_atributo_geof']):
                df = dic_cartas['interpolado_cubico'][i].to_dataframe()
                lista_interpolado.append(df[i])
            geof_cubic = pd.concat(lista_interpolado, axis=1, join='inner')
            geof_cubic.reset_index(inplace=True)
            # AJUSTANDO CRS
            # print("Ajustando crs")
            if crs__ == 'proj':
                gdf = gpd.GeoDataFrame(geof_cubic, crs=crs__)
                gdf = gdf.set_crs(crs__, allow_override=True)
                gdf = gdf.to_crs("EPSG:32723")
                print('')
                print(f" geof: {gdf.crs}")
            else:
                gdf = gpd.GeoDataFrame(geof_cubic, crs=crs__)
                gdf = gdf.set_crs(crs__, allow_override=True)
                gdf = gdf.to_crs("EPSG:4326")
                print('')
                print(f" geof: {gdf.crs}")
            # CALCULO DE GEOMETRIA MAIS PROXIMA
            print(f"# -- Calculando geometria mais próxima para cada um dos {len(geof_cubic)} centróides de pixel")
            lito_cubic = dic_cartas['cubic'][index]
            lito_cubic['closest_unid'] = gdf['geometry'].apply(
                lambda x: litologia['SIGLA'].iloc[litologia.distance(x).idxmin()])
            print(f"# Listagem de unidades geológicas presentes na folha de id {index}:    ")
            print(f"  {list(lito_cubic['closest_unid'].unique())}")
            # Adicionando lito_geof ao dicionario
            print('')
            print(f" Adicionando dataframe com valores de litologia e geofíscios ao dicionário de cartas")
            x = {index: lito_cubic}
            dic_cartas['lito_cubic'].update(x)
            print(dic_cartas['lito_cubic'][index].keys())
# ----------------------------------------------------------------------------------------------------------------------
# FUNÇOES DE PLOTAGEM COM GEOPANDAS
def plot_brazil(gdf, atributo=None):
    world = dado_bruto.gpd.read_file(dado_bruto.gpd.datasets.get_path('naturalearth_lowres'))
    brazil = world[world.name == 'Brazil']
    if atributo:
        ax = brazil.boundary.plot(color='black')
        gdf.plot(atributo, ax=ax, color='black')
    else:
        ax = brazil.boundary.plot(color='black')
        gdf.plot(ax=ax, color='black')
# ----------------------------------------------------------------------------------------------------------------------
def plot_base(escala=None,ids=None,atributo=None, camada=None, mapa=None):
    litologia = importar_geometrias(camada, mapa)
    gdf = import_malha_cartog(escala,ids)
    gdf = gdf.boundary
    if atributo:
        ax = litologia.plot('SIGLA')
        gdf.plot(atributo, color='black', ax=ax)
    else:
        ax = litologia.plot('SIGLA')
        gdf.plot(ax=ax, color='black')
# ----------------------------------------------------------------------------------------------------------------------
def labels(escala=None,ids=None):
    gdf = import_malha_cartog(escala=escala,ids=ids)
    gdf['centroid'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
    gdf['centroid'] = [coords[0] for coords in gdf['centroid']]
    for index, row in gdf.iterrows():
        plt.annotate(text=row['id_folha'], xy=row['centroid'], horizontalalignment='center')
# ----------------------------------------------------------------------------------------------------------------------
def plot_boxplots(folha, atributos):
    fig, axs = plt.subplots(nrows = 2, ncols = 4)

    for ax, atributo in zip(axs.flat, atributos):
        g = ax.boxplot(folha[atributo])
        ax.set_title(atributo)

    plt.show()
# ---------------------------------------------------------------------------------------------------
def filtro(gdf, mineral):
    '''
    Recebe uma camada vetorial e uma 'str', navega pela coluna LITOTIPOS selecionando geometrias que contem a 'str'
    Caso nenhuma geometria seja selecionada, retornara a lista de valores unicos presenta na coluna LITOTIPOS da camada vetorial
    '''
    filtrado = gdf[gdf['LITOTIPOS'].str.contains(mineral)]
    if filtrado.empty:
        print(f"{list(gdf['LITOTIPOS'].unique())}")
    else:
        return filtrado
# ---------------------------------------------------------------------------------------------------
def Build_mc(escala='50k',ID=['SF23_YA'],verbose=None):
    mc = import_mc(escala,ID)
    mc.set_index('id_folha',inplace=True)
    
    quadricula = {}
    for index,row in tqdm(mc.iterrows()):
        y = {index:{'folha':row,
                    'mag' :'',
                    'gama':'',
                    'lito':''}}
        quadricula.update(y)
        if verbose:
            print(f' - Folha "{index}" adicionada.')
    if verbose:
        print('')
        print(f'  {len(quadricula.keys())} folhas adicionadas.')

        
    
    return quadricula
# ---------------------------------------------------------------------------------------------------
def Upload_mc(quadricula=None,gama_xyz=None,mag_xyz=None,camada=None):
    gama_data = import_xyz('/home/ggrl/database/geof/'+gama_xyz)
    mag_data = import_xyz('/home/ggrl/database/geof/'+mag_xyz)
    lito = importar_geometrias(camada)
    if len(gama_data) > 10:
        print(f' - Levantamento {gama_xyz} importado com sucesso')
    else:
        raise() 
    if len(mag_data)  > 10:
        print(f' - Levantamento {mag_xyz} importado com sucesso')
    else:
        raise()
    gama_coords=(gama_data.X,gama_data.Y)
    mag_coords=(mag_data.X,mag_data.Y)
    wgs84 = pyproj.CRS('EPSG:4326')
    ids = list(quadricula.keys())
    for id in ids:
        utm = pyproj.CRS('EPSG:'+quadricula[id]['folha']['EPSG'])
        carta_wgs84 = quadricula[id]['folha']['geometry']
        project = pyproj.Transformer.from_crs(wgs84,utm,always_xy=True).transform
        carta_utm = transform(project,carta_wgs84)
        # TEST PLOT ----------------------------------------------------------
        plt.figure()
        plt.plot(*carta_utm.exterior.xy)
        plt.axis('scaled')
        # --------------------------------------------------------------------
        region = carta_utm.bounds
        reg =(region[0]-1000,region[2]+1000,region[1]-1000,region[3]+1000)
        gama_df = gama_data[vd.inside(gama_coords,reg)]
        mag_df = mag_data[vd.inside(mag_coords,reg)]
        lito_id = lito.cx[region[0]:region[1],
                          region[2]:region[3]]
        y = {'gama':gama_df}
        quadricula[id].update(y)
        print(f' - {gama_xyz} atualizado na folha: {id}')
        z = {'mag':mag_df}
        quadricula[id].update(z)
        print(f' - {mag_xyz} atualizado na folha: {id}')
        w = {'lito':lito_id}
        quadricula[id].update(w)
        print(f' - {camada} atualizado na folha: {id}')

    
    return





























# Imports

import seaborn as sns
import geopandas as gpd
# import xarray as xr
import pandas as pd
import fiona
import verde as vd
import numpy as np
import matplotlib.pyplot as plt
import math
import pyproj

from verde_source import regular, interp_at
from tqdm import tqdm
from shapely import geometry
from shapely.ops import transform
from pylab import cm

# -----------------------------------------------------------------------------
# Gama Titulos
gama_FEAT = ['CTCOR', 'eTh', 'eU', 'KPERC',
             'UTHRAZAO', 'UKRAZAO', 'THKRAZAO', 'MDT']
gama_titles = ['Contagem Total', 'Th (ppm)', 'U (ppm)', 'K (%)',
               'U/Th', 'U/K', 'Th/K', 'MDT (m)']
gama_dic_titles = {}
for f, t in zip(gama_FEAT, gama_titles):
    gama_dic_titles[f] = t

# Mag Titulos
mag_FEAT = ['MAGIGRF', 'MDT']
mag_titles = ['GMT (nT)', 'MDT (m)']
mag_dic_titles = {}
for f, t in zip(mag_FEAT, mag_titles):
    mag_dic_titles[f] = t

# Percentiles
percentiles = (0.001, 0.01, 0.05, 0.25, 0.5, 0.75, 0.9995)
# ColorMap
cmap = cm.get_cmap('rainbow', 15)

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
    Retornando camada vazia recebera a lista das camadas veotoriais diposniveis
    Se mapa == False: retorna todos os objetos presente nesta camada vetorial
    '''
    lito = gpd.read_file(set_gdb('geodatabase.gpkg'),
                         driver='GPKG',
                         layer=camada)
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha ' + mapa]
        if len(folha) == 0:
            print("O mapa escolhido não existe na coluna MAPA do vetor.")
            print("Os mapas disponiveis serão listados a seguir.")
            print('')
            print('# Selecionando apenas os caracteres apos ''folha''')
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")
            lista_mapas = list(lito.MAPA.unique())
            return lista_mapas
        return folha
    else:
        return lito
# -----------------------------------------------------------------------------


def import_malha_cartog(escala='25k', ID=None, IDs=None):
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


def import_mc(escala=None, ID=None):
    mc = gpd.read_file(set_gdb('geodatabase.gpkg'),
                       driver='GPKG',
                       layer='mc_' + escala)
    mc_slct = gpd.GeoDataFrame()
    if type(ID) is list:
        for id in tqdm(ID):
            mc_slct = mc_slct._append(mc[mc['id_folha'].str.contains(id)])
        return mc_slct
    elif type(ID) is str:
        mc_slct = mc[mc['id_folha'] == ID]
        return mc_slct
    elif type(ID) is str:
        mc_slct = mc[mc['id_folha'] == ID]
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
    print(f"# -- Lista de camadas vetoriais disponíveis:\
            {fiona.listlayers(path_lito)}")
    if lito.empty:
        raise "# FALHA : A camada escolhida nao está presente no geopackage."
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha ' + mapa]
        if folha.empty:
            print('')
            print("O mapa escolhido não está presente na coluna MAPA.")
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")
        else:
            return folha, geof_dataframe
    else:
        return lito, geof_dataframe
# -----------------------------------------------------------------------------


def nomeador_grid(left, right, top, bottom, escala=5):
    e1kk = ['A', 'B', 'C', 'D', 'E', 'F', 'G',
            'H', 'I', 'J', 'K', 'L', 'M', 'N']
    e500k = [['V', 'Y'], ['X', 'Z']]
    e250k = [['A', 'C'], ['B', 'D']]
    e100k = [['I', 'IV'], ['II', 'V'], ['III', 'VI']]
    e50k = [['2', '3'], ['2', '4']]
    e25k = [['NW', 'SW'], ['NE', 'SE']]
    if left > right:
        print('Oeste deve ser menor que leste')
    if top < bottom:
        print('Norte deve ser maior que Sul')
    else:
        id_folha = ''
        if top <= 0:
            id_folha += 'S'
            index = math.floor(-top / 4)
        else:
            id_folha += 'N'
            index = math.floor(bottom / 4)
        numero = math.ceil((180+right)/6)
        print(numero)
        id_folha += e1kk[index]+str(numero)
        lat_gap = abs(top-bottom)
        # p500k-----------------------
        if (lat_gap <= 2) & (escala >= 1):
            LO = math.ceil(right/3) % 2 == 0
            NS = math.ceil(top/2) % 2 != 0
            id_folha += '_'+e500k[LO][NS]
        # p250k-----------------------
        if (lat_gap <= 1) & (escala >= 2):
            LO = math.ceil(right/1.5) % 2 == 0
            NS = math.ceil(top) % 2 != 0
            id_folha += e250k[LO][NS]
        # p100k-----------------------
        if (lat_gap <= 0.5) & (escala >= 3):
            LO = (math.ceil(right/0.5) % 3)-1
            NS = math.ceil(top/0.5) % 2 != 0
            id_folha += '_'+e100k[LO][NS]
        # p50k------------------------
        if (lat_gap <= 0.25) & (escala >= 4):
            LO = math.ceil(right/0.25) % 2 == 0
            NS = math.ceil(top/0.25) % 2 != 0
            id_folha += '_'+e50k[LO][NS]
        # p25k------------------------
        if (lat_gap <= 0.125) & (escala >= 5):
            LO = math.ceil(right/0.125) % 2 == 0
            NS = math.ceil(top/0.125) % 2 != 0
            id_folha += e25k[LO][NS]
        return id_folha

# -----------------------------------------------------------------------------


def set_EPSG(mc):
    EPSG = []
    for i in mc['id_folha']:
        if i[:1] == 'S':
            EPSG.append('327'+str(i[2:4]))
        else:
            EPSG.append('326'+str(i[2:4]))
    mc['EPSG'] = EPSG
    return mc
# -----------------------------------------------------------------------------

def nomeador_malha(gdf):
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_grid(row.region[0], row.region[1],
                                         row.region[3], row.region[2],
                                         escala=5))
        lista_malha.append(row.id_folha)
    gdf['id_folha'] = lista_malha
# -----------------------------------------------------------------------------


def regions(mc):
    bounds = mc.bounds
    for index, row in mc.iterrows():
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


def cartas(escala="", ids=""):
    print('# --- Iniciando seleção de área de estudo')
    mc_select = import_malha_cartog(escala, ids)
    regions(mc_select)
    mc_select.set_index('id_folha', inplace=True)
    # CRIANDO UM DICIONÁRIO DE CARTAS
    print('# --- Construindo Dicionario de Cartas')
    mc_select['raw_data'] = ''
    dic_cartas = mc_select.to_dict()
    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) > 1:
        print(f"{len(dic_cartas['raw_data'])} \
                folhas cartográfica selecionadas")
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
    geof_descrito = geof_df.describe(percentiles=[0.001, 0.1, 0.25, 0.5,
                                                  0.75, 0.995])
    return metadatadict, lista_at_geof, \
        lista_at_geog, lista_at_proj, geof_descrito


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


def describe_geologico(gdf, columns=['SIGLA', 'NOME',
                                     'LITOTIPOS', 'LEGENDA', 'AMBIENTE_T']):
    if columns is None:
        columns = list(gdf.columns)
    else:
        columns = columns
    dic_lito_titles = {}
    for col in columns:
        lista = list(gdf[col].unique())
        dic_lito_titles.update({col: {'lista': lista,
                                      'len': len(lista)}})
    return dic_lito_titles
# ----------------------------------------------------------------------------------------------


def set_region(escala, id, geof, camada, mapa=None, crs__=None):
    '''
    Recebe:
        escala : Escalas disponíveis para recorte: '50k', '100k', '250k', '1kk'
            id : ID da folha cartográfica (Articulação Sistemática de Folhas Cartográficas)
          geof : Dado aerogeofísico disponível na base de dados (/home/ggrl/database/geof/)
        camada : Litologias disponíveis na base de dados (/home/ggrl/database/geodatabase.gpkg)
        mapa   : Nome do mapa caso necessário.
    '''
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
    metadatadict, \
        lista_at_geof, \
        lista_at_geog, \
        lista_at_proj, \
        geof_descrito = descricao(geof_df)
    dic_raw_meta = {'Metadata': metadatadict,
                    'Lista_at_geof': lista_at_geof,
                    'Lista_at_geog': lista_at_geog,
                    'Lista_at_proj': lista_at_proj,
                    'Percentiles': geof_descrito,
                    'Malha_cartografica': mc_select}
    print('')
    print("# --- Início da iteração entre as folhas cartográficas #")
    for index, row in tqdm(mc_select.iterrows()):
        data = geof_df[vd.inside((geof_df.X,
                                  geof_df.Y), region=row.region_proj)]

        crs__ = row.EPSG
        if len(data) < 10000 & len(data) > 0:
            y = {index: litologia}
            dict_cartas['litologia'].update(y)
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            print(f" Atualizando dados geofísicos brutos em dic_cartas['raw_data']['{index}']")
            x = {index: data}
            dict_cartas['raw_data'].update(x)
            print(f" com {len(data)} pontos de amostragem")
        if len(data) >= 10000:
            print('')
            print(f"# Folha de código: {index}")
            print(f" - Atualizando dados geofísicos em dic_cartas['raw_data']['{index}']")
            x = {index: data}
            dict_cartas['raw_data'].update(x)
            print(f" com {len(data)} pontos de amostragem.")
            litologia.to_crs('EPSG:' + crs__, inplace=True)
            lito_cut = litologia.cx[row.region_proj[0]:row.region_proj[1],
                                    row.region_proj[2]:row.region_proj[3]]
            print(f" - Atualizando dados litológicos em \
                    dic_cartas['litologia']['{index}']")
            print(f" com {lito_cut.shape[0]} polígonos descritos por: {lito_cut.shape[1]} atributos geológicos ")
            print(lito_cut.crs)
            y = {index: lito_cut}
            dict_cartas['litologia'].update(y)
        elif data.empty:
            None
            print('')
            print(f'Folha de código {index} sem dados Aerogeofisicos')

    return dict_cartas, dic_raw_meta
# --------------------------------------------------------------------------------------


def batch_verde(quadricula=None):
    lista_at_geof = dic_raw_meta['Lista_at_geof']
    dic_cartas['splines'] = {}
    for index, row in tqdm(dic_raw_meta['Malha_cartografica'].iterrows()):
        data = dic_cartas['raw_data'][index]
        y = {index: {}}
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
            # region = dic_cartas['region_proj'][index]
            chain = vd.Chain([('trend', vd.Trend(degree=1)),
                              ('reduce', vd.BlockReduce(np.mean, spacing=1000)),
                              ('spline', vd.Spline())])
            for i in tqdm(lista_at_geof):
                chain.fit(coordinates, data[i])
                grid = chain.grid(spacing=200,
                                  data_names=[i],
                                  pixel_register=True)

                y = {i: ''}
                grid = chain.grid(spacing=200, data_names=[i], pixel_register=True)
                dic_cartas['splines'][index].update(y)
                dic_cartas['splines'][index][i] = \
                    vd.distance_mask(coordinates, maxdist=500, grid=grid)
                print(f" Atualizando dic_cartas['splines']['{index}']['{i}']")
                print('__________________________________________')
        print(" ")
    print("Dicionário de cartas disponível")

    return dic_cartas, dic_raw_meta
# ----------------------------------------------------------------------------


def interpolar(splines=None, cubico=None, mag=None, gama=None, geof=None, dic_cartas=None, dic_raw_meta=None):
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
                chain = vd.Chain([('trend', vd.Trend(degree=1)),
                                  ('reduce', vd.BlockReduce(np.mean, spacing=1000)),
                                  ('spline', vd.Spline())])
                print(f"# Folha de código: {index}")
                print(f" Atualizando dados brutos em dic_cartas['raw_data']")
                cv = vd.BlockKFold(spacing=1000,
                                   n_splits=5,
                                   shuffle=True)
                for i in lista_at_geof:
                    chain.fit(coordinates, data[i])
                    grid = chain.grid(spacing=200, data_names=[i],
                                      pixel_register=True)
                    grids[i] = vd.distance_mask(coordinates,
                                                maxdist=1000,
                                                grid=grid)
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
                xu, yu = vd.regular(shape=(1272, 888),
                                    area=area)
                if geof:
                    CTC = np.array(gdf_geof.CTC)
                    THC = np.array(gdf_geof.THC)
                    UC = np.array(gdf_geof.UC)
                    KC = np.array(gdf_geof.KC)
                    MAGR = np.array(gdf_geof.MAGR)
                    ALTE = np.array(gdf_geof.ALTE)
                    x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)
                    alte_ = vd.interp_at(x2, y2, ALTE, xu, yu, algorithm='cubic', extrapolate=True)
                    uc_ = vd.interp_at(x2, y2, UC, xu, yu, algorithm='cubic', extrapolate=True)
                    kc_ = vd.interp_at(x2, y2, KC, xu, yu, algorithm='cubic', extrapolate=True)
                    ctc_ = vd.interp_at(x2, y2, CTC, xu, yu, algorithm='cubic', extrapolate=True)
                    thc_ = vd.interp_at(x2, y2, THC, xu, yu, algorithm='cubic', extrapolate=True)
                    magr_ = vd.interp_at(x2, y2, MAGR, xu, yu, algorithm='cubic', extrapolate=True)
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
                    altura_ = vd.interp_at(x2, y2, ALTURA, xu, yu, algorithm='cubic', extrapolate=True)
                    mdt_ = vd.interp_at(x2, y2, MDT, xu, yu, algorithm='cubic', extrapolate=True)
                    magigrf_ = vd.interp_at(x2, y2, MAGIGRF, xu, yu, algorithm='cubic', extrapolate=True)
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
def describe(dic_cartas, dic_raw_data, crs__, vdm, ):
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
        if vdm:
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


def bounding_box(geometry):
    recorte = [geometry.bounds['minx'].min(), geometry.bounds['maxx'].max(),
               geometry.bounds['miny'].min(), geometry.bounds['maxy'].max()]

    return recorte
# ----------------------------------------------------------------------------------------------------------------------


# FUNÇOES DE PLOTAGEM COM GEOPANDA
def plot_brazil(gdf, atributo=None):
    recorte = bounding_box(gdf)
    world = gpd.read_file(gpd.datasets.get_path('naturalearth_lowres'))
    brazil = world[world.name == 'Brazil']
    recorte_brazil = brazil.clip(recorte[0], recorte[2],
                                 recorte[1], recorte[3])
    if atributo:
        ax = recorte_brazil.boundary.plot(color='black')
        gdf.plot(atributo, ax=ax, color='black')
    else:
        ax = recorte_brazil.boundary.plot(color='black')
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
    fig, axs = plt.subplots(figsize=(14,21),nrows = 2, ncols = 4)
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


def plot_mc_base(quadricula=None):
    for id in list(quadricula.keys()):
        carta=quadricula[id]
        plt.plot(*transform_to_carta_utm(carta['folha']).exterior.xy,color='black')
        for data in list(carta.keys())[2:]:
            if 'mag' in data:
                pass
            else:
                plt.scatter(carta[data].X,carta[data].Y,
                            c=carta[data].MDT,
                            cmap='terrain',
                            s=0.5,
                            marker='H')
                plt.axis('scaled')
    plt.tight_layout()

# ---------------------------------------------------------------------------------------------------


def Build_mc(escala='50k',ID=['SF23_YA'],verbose=None):
    mc = import_mc(escala,ID)
    mc.set_index('id_folha',inplace=True)
    quadricula = {}
    for index,row in tqdm(mc.iterrows()):
        y = {index:{'folha':row,
                    'escala':escala}}
        quadricula.update(y)
        if verbose:
            print(f' - Folha "{index}" adicionada.')
    if verbose:
        print('')
        print(f'  {len(quadricula.keys())} folhas adicionadas.')
    return quadricula
# ---------------------------------------------------------------------------------------------------


def Upload_geof(quadricula=None,gama_xyz=None,mag_xyz=None,extend_size=0):
    gama_data = import_xyz('/home/ggrl/database/geof/'+gama_xyz)
    mag_data = import_xyz('/home/ggrl/database/geof/'+mag_xyz)
    list_atri=gama_data.columns
    if 'LAT_WGS' in list_atri:
        gama_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'},inplace=True)
    if 'eTH' in list_atri:
        gama_data.rename(columns={'eTH':'eTh'},inplace=True)
    list_atri=mag_data.columns
    if 'LAT_WGS' in list_atri:
        mag_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'},inplace=True)


def pop_nodata(quadricula):
    for id in tqdm(list(quadricula.keys())):
        if len(quadricula[id]) <= 2:
            quadricula.pop(id)
    return quadricula
# -----------------------------------------------------------------o
def batch_grid_coordinates(quadricula,spacing=0.001, pixel_register=True):
    list_id = list(quadricula.keys())
    #print(f' Folhas disponíveis: {list_id}')
    for id in list_id:
        folha = quadricula[id]
        print(f' Folha {id}')

        df = quadricula[id]['area']
        area = (df['geometry'].bounds[0],df['geometry'].bounds[2],
                df['geometry'].bounds[1],df['geometry'].bounds[3])
        xu,yu = grid_coordinates(region=area,spacing=spacing, pixel_register=pixel_register)

        df['coords'] = xu,yu
        df['area'] = area
        x = {'area':df}
        quadricula[id].update(x)
        print('Quadricula atualizada')

# -----------------------------------------------------------------


def Upload_litologia(quadricula=None,camada=None):
    lito=geometrias(camada)
    ids = list(quadricula.keys())
    for id in tqdm(ids):
        carta=quadricula[id]['folha']['geometry']
        region = carta.bounds
        lito_id = lito.cx[region[0]:region[2],region[1]:region[3]]
        lito_id = lito_id[['LITOTIPOS','SIGLA','NOME','MAPA','geometry']]
        quadricula[id].update({camada:lito_id})
        if len(lito_id) > 0:
            print(f' - {camada} atualizado na folha: {id}')
# ---------------------------------------------------------------------------------------------------


def plot_quadricula(quadricula=None,xyz=None,canal=None):
    plt.figure(figsize=(16,8))
    for id in list(quadricula.keys()):
        Folha=quadricula[id][xyz]
        coords=[Folha.X,Folha.Y]
        plt.scatter(coords[0],coords[1],
                c=Folha[canal],s=2,cmap='hsv',
                vmin=Folha[canal].min(),
                vmax=Folha[canal].max())
        plt.axis('scaled')
# ---------------------------------------------------------------------------------------------------


def plot_folha(Folha=None,xyz=None,canal=None):
    plt.figure(figsize=(16,8))
    df = Folha[xyz]
    coords=[df.X,df.Y]
    plt.scatter(coords[0],coords[1],
                c=df[canal],s=2,cmap='bwr',
                vmin=df[canal].min(),
                vmax=df[canal].max())
    plt.axis('scaled')
    plt.colorbar()
# ---------------------------------------------------------------------------------------------------


def plot_df(df=None,canal=None,legenda=None):
    print(df.describe(percentiles=[0.01,0.25,0.5,0.75,0.995]).T)
    plt.figure(figsize=(18,12))
    coords=[df.X,df.Y]
    plt.scatter(coords[0],coords[1],c=df[canal],cmap='bwr',vmin=df[canal].min(),vmax=df[canal].max(),marker='.')
    plt.axis('scaled')
    plt.colorbar(label=legenda,orientation='horizontal')
# ---------------------------------------------------------------------------------------------------


def parser_siglas(ID='SF23',quadricula=None):
    lito = quadricula[ID]['lito']
    lista_SIGLAS = lito.SIGLA.unique()
    lista_periodos = []
    for sigla in lista_SIGLAS:
        print(sigla)
        periodo = ''
        for letra in sigla:
            if letra.isdigit()==False:
                print(f'{letra} não é digito')
                if letra != '_':
                    print(f'{letra} não é "_"')
                    periodo+=letra
                else:
                    break
            else:
                break
        print(periodo)
        lista_periodos.append(periodo)
    lista_periodos_set = list(set(lista_periodos))
    return lista_SIGLAS,lista_periodos,lista_periodos_set
# ---------------------------------------------------------------------------------------------------


def remove_negative_gama(df):
    df['K_pos'] = df['KPERC'] - df['KPERC'].min() + 0.01
    df['eU_pos'] = df['eU'] - df['eU'].min() + 0.01
    df['eTh_pos'] = df['eTh'] - df['eTh'].min() + 0.01
    # excluindo os canais originais
    df.drop(['KPERC', 'eU', 'eTh'], axis=1, inplace=True)
    #renomeando os positivos para os nomes dos originais
    df.rename(columns={'K_pos':'KPERC','eU_pos':'eU','eTh_pos':'eTh','CTCOR':'CT'}, inplace=True)
    df = df[['CT', 'eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO','MDT','X','Y','LATITUDE','LONGITUDE']]
# ---------------------------------------------------------------------------------------------------


'''
def remove_negative_values(dataframe=None,lista=['X','Y','LATITUDE','LONGITUDE','geometry']):
    atributo = list(dataframe.columns)
    for i in lista:
        if i in atributo:
            atributo.remove(i)
        else:
            None
'''


def remove_negative_values(dataframe=None,high_pass=None):
    atributo = list(dataframe.columns)[4:]
    descrito_df = dataframe[atributo].describe(percentiles=(0.01,0.25,0.5,0.75,0.9,0.999))
    for i in atributo:
        print(f'Atributo - {i}')
        dataframe[i][dataframe[i] <= 0] = 0.001
    if high_pass:
        if descrito_df[i]['99.9%'] > descrito_df[i]['mean']:
            print(descrito_df[i]['99.99%'])
            dataframe[i][dataframe[i] > descrito_df[i]['99.99%']] = descrito_df[i]['99.99%']
    print(descrito_df.T)
    return dataframe
# ---------------------------------------------------------------------------------------------------


def transform_to_carta_utm(carta):
    wgs84=pyproj.CRS('EPSG:4326')
    utm = pyproj.CRS('EPSG:'+carta['EPSG'])
    carta_wgs84 = carta['geometry']
    project=pyproj.Transformer.from_crs(wgs84,utm,always_xy=True).transform
    carta_utm=transform(project,carta_wgs84)
    return carta_utm
# -----------------------------------------------------------------------------


def sintetic_grid(quadricula,ID,spacing=0.001,projec='geog'):
    if projec=='geog':
        area=quadricula[ID]['area']['area']
    elif projec=='proj':
        area=transform_to_carta_utm(quadricula[ID]['folha']).bounds
    elif projec=='merc':
        projection=pyproj.Proj(proj='merc',lat_ts=data.latitude.mean())
    spacing=0.001
    xu, yu = regular(shape=(int((area[3]-area[2])/spacing),int((area[1]-area[0])/spacing)),area=area)
    return xu,yu
# -------------------------------------------------------------------------------------------------


def Build_mc(escala='50k',ID=['SF23_YA'],verbose=None):
    mc = import_mc(escala,ID)
    mc.set_index('id_folha',inplace=True)
    quadricula = {}
    wgs84 = pyproj.CRS('EPSG:4326')
    ids = list(quadricula.keys())
    print(f' - Folhas selecionadas:')
    for index,row in tqdm(mc.iterrows()):
        carta_wgs84 = row['geometry']
        utm = pyproj.CRS('EPSG:'+row['EPSG'])
        carta_wgs84 = row['geometry']
        project = pyproj.Transformer.from_crs(wgs84,utm,always_xy=True).transform
        carta_utm = transform(project,carta_wgs84)
        row['geometry_proj'] = carta_utm
        y = {index:{'folha':row}}
        quadricula.update(y)
        if verbose:
            print(f'"{index}"')
    if verbose:
        print('')
        print(f'  {len(quadricula.keys())} folhas adicionadas.')
    return quadricula
# ---------------------------------------------------------------------------------------------------


def Upload_geof_geografica(quadricula=None,gama_xyz=None,mag_xyz=None,extend_size=0):
    gama_data = import_xyz(set_gdb('geof/')+gama_xyz)
    mag_data = import_xyz(set_gdb('geof/')+mag_xyz)
    list_atri=list(mag_data.columns)
    if 'MAGIGRF' in list_atri:
        mag_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'},inplace=True)
        mag_data=mag_data[['X','Y','LATITUDE','LONGITUDE','MDT','MAGIGRF','ALTURA']]
    if 'MAGR' in list_atri:
        mag_data.rename(columns={'MAGR':'MAGIGRF'},inplace=True)
        mag_data=mag_data[['X','Y','LATITUDE','LONGITUDE','MAGIGRF','MDT']]
    list_atri=list(gama_data.columns)
    if 'LAT_WGS' in list_atri:
        gama_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'},inplace=True)
    if 'eTH' in list_atri:
        gama_data.rename(columns={'eTH':'eTh'},inplace=True)
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTCOR','eU','eTh','KPERC','UTHRAZAO','THKRAZAO','UKRAZAO','MDT']]
    if 'eth' in list_atri:
        gama_data.rename(columns={'eTH':'eTh'},inplace=True)
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTCOR','eU','eTh','KPERC','UTHRAZAO','THKRAZAO','UKRAZAO','MDT']]
    if 'CTCOR' in list_atri:
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTCOR','eU','eTh','KPERC','UTHRAZAO','THKRAZAO','UKRAZAO','MDT']]
    if 'CTC' in list_atri:
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTC','UC','THC','KC','MDT']]
    gama_coords=(gama_data.LONGITUDE,gama_data.LATITUDE)
    mag_coords=(mag_data.LONGITUDE,mag_data.LATITUDE)
    ids = list(quadricula.keys())
    gama_df=pd.DataFrame()
    mag_df=pd.DataFrame()
    for id in tqdm(ids):
        area = quadricula[id]['area']['area']
        region = (area[0] - extend_size,area[1]+ extend_size,
                  area[2] - extend_size, area[3] + extend_size)
        if gama_xyz:
            gama = gama_data[vd.inside(gama_coords,region)]
            if len(gama) > 10000:
                quadricula[id].update({gama_xyz:gama})
                print(f' - {gama_xyz} atualizado na folha: {id} com {len(gama)} pontos')
        if mag_xyz:
            mag = mag_data[vd.inside(mag_coords,region)]
            if len(mag) > 10000:
                quadricula[id].update({mag_xyz:mag})
                print(f' - {mag_xyz} atualizado na folha: {id} com {len(mag)} pontos')
    return
#  -----------------------------------------------------------------------------


def Upload_geof(quadricula=None,gama_xyz=None,mag_xyz=None,extend_size=0):
    gama_data = import_xyz(set_gdb('geof/')+gama_xyz)
    mag_data = import_xyz(set_gdb('geof/')+mag_xyz)
    list_atri=list(mag_data.columns)
    if 'MAGIGRF' in list_atri:
        mag_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'},inplace=True)
        mag_data=mag_data[['X','Y','LATITUDE','LONGITUDE','MDT','MAGIGRF']]
    if 'MAGR' in list_atri:
        mag_data.rename(columns={'MAGR':'MAGIGRF'},inplace=True)
        mag_data=mag_data[['X','Y','LATITUDE','LONGITUDE','MAGIGRF','MDT']]
    list_atri=list(gama_data.columns)
    if 'LAT_WGS' in list_atri:
        gama_data.rename(columns={'LAT_WGS':'LATITUDE','LONG_WGS':'LONGITUDE'},inplace=True)
    if 'eTH' in list_atri:
        gama_data.rename(columns={'eTH':'eTh'},inplace=True)
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTCOR','eU','eTh','KPERC','UTHRAZAO','THKRAZAO','UKRAZAO','MDT']]
    if 'CTCOR' in list_atri:
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTCOR','eU','eTh','KPERC','UTHRAZAO','THKRAZAO','UKRAZAO','MDT']]
    if 'CTC' in list_atri:
        gama_data=gama_data[['X','Y','LATITUDE','LONGITUDE','CTC','UC','THC','KC','MDT']]
    gama_coords=(gama_data.X,gama_data.Y)
    mag_coords=(mag_data.X,mag_data.Y)
    wgs84 = pyproj.CRS('EPSG:4326')
    ids = list(quadricula.keys())
    for id in tqdm(ids):
        utm = pyproj.CRS('EPSG:'+quadricula[id]['folha']['EPSG'])
        carta_wgs84 = quadricula[id]['folha']['geometry']
        project = pyproj.Transformer.from_crs(wgs84,utm,always_xy=True).transform
        carta_utm = transform(project,carta_wgs84)
        region_utm = carta_utm.bounds[0],carta_utm.bounds[2],carta_utm.bounds[1],carta_utm.bounds[3]
        reg =(region_utm[0]-extend_size,region_utm[2]+extend_size,region_utm[1]-extend_size,region_utm[3]+extend_size)
        quadricula[id].update({'region_utm':region_utm})
        if gama_xyz:
            gama = gama_data[vd.inside(gama_coords,reg)]
            if len(gama) > 10000:
                quadricula[id].update({gama_xyz:gama})
                print(f' - {gama_xyz} atualizado na folha: {id} com {len(gama)} pontos')
        if mag_xyz:
            mag = mag_data[vd.inside(mag_coords,reg)]
            if len(mag) > 10000:
                quadricula[id].update({mag_xyz:mag})
                print(f' - {mag_xyz} atualizado na folha: {id} com {len(mag)} pontos')
    return
#  -----------------------------------------------------------------------------


def traditional_interpolation(quadricula='',mag_xyz=None,gama_xyz=None,algorithm='cubic',geof=None,projec="geog",extrapolate=False):
    for id in tqdm(list(quadricula.keys())):
        if mag_xyz and gama_xyz in list(quadricula[id].keys()):
            #print(f' - Folha: {id}')
            gama_data=remove_negative_values(quadricula[id][gama_xyz])
            mag_data=quadricula[id][mag_xyz]
            CTCOR=np.array(gama_data.CTCOR)
            eTh=np.array(gama_data.eTh)
            eU=np.array(gama_data.eU)
            KPERC=np.array(gama_data.KPERC)
            if 'THKRAZAO' in gama_data.columns:
                THKRAZAO=np.array(gama_data.THKRAZAO)
                UKRAZAO=np.array(gama_data.UKRAZAO)
                UTHRAZAO=np.array(gama_data.UTHRAZAO)
                MAGIGRF=np.array(mag_data.MAGIGRF)
                MDT=np.array(mag_data.MDT)
                xu,yu=sintetic_grid(quadricula,id,projec)
                x1,y1=np.array(gama_data.LONGITUDE),np.array(gama_data.LATITUDE)
                x2,y2=np.array(mag_data.LONGITUDE),np.array(mag_data.LATITUDE)
                df_xu_yu = pd.DataFrame(np.array([xu,yu]))
                df_xu_yu=df_xu_yu.T
                df_xu_yu.rename(columns={0:'xu',1:'yu'},inplace=True)
                eth_=interp_at(x1,y1,eTh,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                eu_=interp_at(x1,y1,eU,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                kperc_=interp_at(x1,y1,KPERC, xu, yu, algorithm= algorithm,extrapolate=extrapolate)
                ctcor_=interp_at(x1,y1,CTCOR,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                uthrazao_=interp_at(x1,y1,UTHRAZAO,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                ukrazao_=interp_at(x1,y1,UKRAZAO,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                thkrazao_=interp_at(x1,y1,THKRAZAO,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                mdt_=interp_at(x2,y2,MDT,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                mag_=interp_at(x2,y2,MAGIGRF,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                data={'LONGITUDE':xu,'LATITUDE':yu,'MDT': mdt_,'CTCOR':ctcor_,
                      'KPERC': kperc_,'eU':eu_,'eTh':eth_,'GMT':mag_,
                      'UTHRAZAO':uthrazao_,'UKRAZAO':ukrazao_,'THKRAZAO':thkrazao_}
                df=pd.DataFrame(data)
                ds = df.set_index(['LATITUDE','LONGITUDE']).to_xarray()
                quadricula[id].update({geof+'_'+algorithm:ds})

            else:
                MAGIGRF=np.array(mag_data.MAGIGRF)
                MDT=np.array(gama_data.MDT)
                xu,yu=sintetic_grid(quadricula,id,200,projection)
                x1,y1=np.array(gama_data.LONGITUDE),np.array(gama_data.LATITUDE)
                x2,y2=np.array(mag_data.LONGITUDE),np.array(mag_data.LATITUDE)
                df_xu_yu = pd.DataFrame(np.array([xu,yu]))
                df_xu_yu=df_xu_yu.T
                df_xu_yu.rename(columns={0:'xu',1:'yu'},inplace=True)
                eth_=interp_at(x1,y1,eTh,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                eu_=interp_at(x1,y1,eU,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                kperc_=interp_at(x1,y1,KPERC, xu, yu, algorithm= algorithm,extrapolate=extrapolate)
                ctcor_=interp_at(x1,y1,CTCOR,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                mdt_=interp_at(x2,y2,MDT,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                mag_=interp_at(x2,y2,MAGIGRF,xu,yu,algorithm=algorithm,extrapolate=extrapolate)
                data={'LONGITUDE':xu,'LATITUDE':yu,'MDT': mdt_,'CTCOR':ctcor_,
                      'KPERC': kperc_,'eU':eu_,'eTh':eth_,'GMT':mag_}
                df=pd.DataFrame(data)
                ds = df.set_index(['LATITUDE','LONGITUDE']).to_xarray()
                quadricula[id].update({geof+'_'+algorithm:ds})
# -----------------------------------------------------------------------------


# Mag Titulos
mag_FEAT=['MAGIGRF','MDT']
mag_titles=['GMT (nT)', 'MDT (m)']
mag_dic_titles = {}
for f, t in zip(mag_FEAT, mag_titles):
    mag_dic_titles[f] = t
# Percentiles
percentiles=(0.001,0.01,0.05,0.25,0.5,0.75,0.9995)
# ColorMap
#cmap=cm.get_cmap('rainbow',15)
# -----------------------------------------------------------------------------


def plot_raw_mag_data(raw_data,suptitle='SET TITLE',minimo='min',maximo='99.95%'):
    fig, axs = plt.subplots(nrows = 1, ncols = 2, figsize = (19,9),sharex='all',sharey='all')
    raw_data_describe = raw_data.describe(percentiles=percentiles)
    X, Y = raw_data.X, raw_data.Y
    for ax, f in zip(axs.flat, mag_dic_titles):
        vmin = raw_data_describe[f][minimo]
        vmax = raw_data_describe[f][maximo]
        if f == 'MDT':
            g = ax.scatter(c=raw_data[f],x=X,y=Y,cmap='terrain',marker='H',s=1,vmax=vmax,vmin=vmin)
            fig.colorbar(g, ax = ax,orientation='horizontal',shrink=0.25)
            ax.set_title(str(mag_dic_titles[f]), size = 11)
            ax.axis('scaled')
        else:
            g = ax.scatter(c=raw_data[f],x=X,y=Y,cmap=cmap,marker='H',s=1,vmax=vmax,vmin=vmin)
            fig.colorbar(g, ax = ax,orientation='horizontal',shrink=0.25,spacing='proportional')
            ax.set_title(str(mag_dic_titles[f]), size = 11)
            ax.axis('scaled')
    fig.suptitle(suptitle)
    plt.tight_layout()

# ---------------------------------------------------------------------------------------------------


def plot_filtered_values(quadricula,c='MDT',cmap='terrain'):
    plt.figure(figsize=(24,16))
    for id in list(quadricula.keys()):
        carta=quadricula[id]
        plt.plot(*(carta['folha']['geometry']).exterior.xy,color='black')
        plt.axis('scaled')
        for data in list(carta.keys())[2:]:
            data=quadricula[id][data]
            print(data)
            if 'geof' in data:
                print(' - passou "geof_data"')
                pass
            if 'gama' in list(data.columns):
                plt.scatter(carta[data].LONGITUDE,carta[data].LATITUDE,c=carta[data][c],cmap=cmap,s=1,marker='H')
            else:
                pass
    plt.suptitle('Área de cobertura dos levantamentos aerogeofísicos')
    plt.tight_layout()
# -------------------------------------------------------------------------------------------------


def plot_raw_gama_data(raw_data,suptitle='SET TITLE',minimo='min',maximo='99.95%',orientation='horizontal',figsize=(26,16)):
    fig, axs = plt.subplots(nrows = 2, ncols = 4, figsize =figsize,sharex='all',sharey='all')
    raw_data_describe = raw_data.describe(percentiles=percentiles)
    X, Y = raw_data.X, raw_data.Y
    gama_dic_titles={}
    gama_FEAT=list(raw_data.columns)[4:]
    if 'CTC' in gama_FEAT:
        gama_titles=[ 'Urânio Corrigido (contagens/s)','Thório Corrigido (contagens/s)', 'Potássio Corrigido (contagens/s)', 'Contagem Total Corrigida (contagens/s)','MDT (m)']
    if 'CTCOR':
        gama_titles=['Contagem Total', 'Th (ppm)', 'U (ppm)','K (%)','U/Th', 'U/K', 'Th/K', 'MDT (m)']
    for f, t in zip(gama_FEAT,gama_titles):
        print(f'f: {f},t: {t}')
        gama_dic_titles[f]=t
    for ax, f in zip(axs.flat, gama_dic_titles):
        vmin = raw_data_describe[f][minimo]
        vmax = raw_data_describe[f][maximo]
        if f == 'MDT':
            g = ax.scatter(c=raw_data[f],x=X,y=Y,cmap='terrain',marker='H',s=1,vmax=vmax,vmin=vmin)
            fig.colorbar(g, ax = ax,orientation=orientation,shrink=0.5)
            ax.set_title(str(gama_dic_titles[f]), size = 11)
            ax.axis('scaled')
        else:
            g = ax.scatter(c=raw_data[f],x=X,y=Y,cmap=cmap,marker='H',s=1,vmax=vmax,vmin=vmin)
            fig.colorbar(g, ax = ax,orientation=orientation,shrink=0.5)
            ax.set_title(str(gama_dic_titles[f]), size = 11)
            ax.axis('scaled')
    fig.suptitle(suptitle)
    plt.tight_layout()
# -----------------------------------------------------------------------------


def plot_histograms(dataframe=None,bins=500,suptitle='Distribuição de Contagens Radiométricas'):
    fig, axs = plt.subplots(nrows = 2, ncols = 4, figsize = (26, 13))
    print(dataframe[['CTCOR','eTh','eU','KPERC','MDT','THKRAZAO','UTHRAZAO','UKRAZAO']].describe(percentiles).T)


def plot_interpolated_histograms(dataframe=None,bins=100,suptitle='Distribuição de Contagens Radiométricas',verbose=False):
    if 'CTCOR' in list(dataframe.columns):
        print('Levantamento Novo')
        dataframe=dataframe[['LONGITUDE','LATITUDE','MDT','CTCOR','eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO']]
        gama_FEAT = list(dataframe.columns)[2:]
        fig, axs = plt.subplots(nrows = int(len(gama_FEAT)/4), ncols = int(len(gama_FEAT)/2), figsize = (21, 9))
    if 'CTC' in list(dataframe.columns):
        print('Levantamento Antigo')
        gama_titles=['MDT (m)','Contagem Total Corrigida (contagens/s)','Urânio Corrigido (contagens/s)','Thório Corrigido (contagens/s)', 'Potássio Corrigido (contagens/s)']
        dataframe=dataframe[['LONGITUDE','LATITUDE','MDT','CTC','THC','UC','KC']]
        gama_FEAT = list(dataframe.columns)[2:]
        fig, axs = plt.subplots(nrows = 2, ncols = 3, figsize = (21, 9))
        fig.delaxes(axs[1][2])
    else:
        gama_titles=['MDT (m)','Contagem Total','Th (ppm)', 'U (ppm)','K (%)','U/Th', 'U/K', 'Th/K']
    gama_dic_titles={}
    for f, t in zip(gama_FEAT, gama_titles):
        gama_dic_titles[f] = t
    if verbose:
        print(f'Features: {gama_FEAT}')
        print(f'Titulos: {gama_dic_titles}')

    for ax, f in zip(axs.flat, gama_FEAT):
        if verbose:
            print(f'feature: {f}, titles: {t}')
        _,_,bars = ax.hist(dataframe[f],color='blue',bins=bins)
        for bar in bars:
            if bar.get_x() < 0:
                bar.set_facecolor("red")
                ax.axvline(x=0,linestyle='--',linewidth=0.1,color='red')
        ax.set_title(str(gama_dic_titles[f]))
    plt.suptitle(suptitle)
    plt.tight_layout()
# -----------------------------------------------------------------------------------


def plot_histograms(dataframe=None,bins=100,suptitle='Distribuição de Contagens Radiométricas',verbose=False):
    if 'CTCOR' in list(dataframe.columns):
        print('Levantamento Novo')
        dataframe=dataframe[['X','Y','LONGITUDE','LATITUDE','MDT','CTCOR','eTh','eU','KPERC','UTHRAZAO','UKRAZAO','THKRAZAO']]
        gama_FEAT = list(dataframe.columns)[4:]
        fig, axs = plt.subplots(nrows = int(len(gama_FEAT)/4), ncols = int(len(gama_FEAT)/2), figsize = (21, 9))
    if 'CTC' in list(dataframe.columns):
        print('Levantamento Antigo')
        gama_titles=['MDT (m)','Contagem Total Corrigida (contagens/s)','Urânio Corrigido (contagens/s)','Thório Corrigido (contagens/s)', 'Potássio Corrigido (contagens/s)']
        dataframe=dataframe[['X','Y','LONGITUDE','LATITUDE','MDT','CTC','THC','UC','KC']]
        gama_FEAT = list(dataframe.columns)[4:]
        fig, axs = plt.subplots(nrows = 2, ncols = 3, figsize = (21, 9))
        fig.delaxes(axs[1][2])
    else:
        gama_titles=['MDT (m)','Contagem Total','Th (ppm)', 'U (ppm)','K (%)','U/Th', 'U/K', 'Th/K']
    gama_dic_titles={}
    for f, t in zip(gama_FEAT, gama_titles):
        gama_dic_titles[f] = t
    if verbose:
        print(f'Features: {gama_FEAT}')
        print(f'Titulos: {gama_dic_titles}')
    for ax, f in zip(axs.flat, gama_FEAT):
        if verbose:
            print(f'feature: {f}, titles: {t}')
        _,_,bars = ax.hist(dataframe[f],color='blue',bins=bins)
        for bar in bars:
            if bar.get_x() < 0:
                bar.set_facecolor("red")
                ax.axvline(x=0,linestyle='--',linewidth=0.1,color='red')
        ax.set_title(str(gama_dic_titles[f]))
    plt.suptitle(suptitle)
    plt.tight_layout()
# -----------------------------------------------------------------------------------


def plotBoxplots(df, cols = None):
    """
    plotBoxplots(df :: dataframe, cols :: list)
    Plota n boxplots, sendo n o número de features presentes na lista cols.
    Parâmetros:
    - df : dataframe com os dados
    - cols : lista de features
    Retorna:
    - Um boxplot por feature presente na lista cols
    """
    n = len(cols)
    fig,axs=plt.subplots(n,1,figsize=(16,n*2.5))
    for ax, f in zip(axs, cols):
        sns.boxplot(y=f,x='closest_unid',data=df,ax=ax)
        if f!=cols[n-1]:
            ax.axes.get_xaxis().set_visible(False)
# -----------------------------------------------------------------------------


def sintetic_grid(quadricula,ID,psize=100):
    area = transform_to_carta_utm(quadricula[ID]['folha']).bounds
    area = area[0],area[2],area[1],area[3]
    xu, yu = regular(shape=(int((area[3]-area[2])/psize),int((area[1]-area[0])/psize)),area=area)
    return xu,yu
# -----------------------------------------------------------------------------


def traditional_interpolation(quadricula=None,mag_xyz=None,gama_xyz=None,algorithm='cubic',geof=None):
    for id in list(quadricula.keys()):
        if mag_xyz and gama_xyz in list(quadricula[id].keys()):
            print(f' - Folha: {id}')
            mag_data=remove_negative_values(quadricula[id][mag_xyz])
            gama_data=remove_negative_values(quadricula[id][gama_xyz])
            print(mag_data.columns)
            CTCOR=np.array(gama_data.CTCOR)
            eTh=np.array(gama_data.eTh)
            eU=np.array(gama_data.eU)
            KPERC=np.array(gama_data.KPERC)
            if 'THKRAZAO' in gama_data.columns:
                THKRAZAO=np.array(gama_data.THKRAZAO)
                UKRAZAO=np.array(gama_data.UKRAZAO)
                UTHRAZAO=np.array(gama_data.UTHRAZAO)
                MAGIGRF=np.array(mag_data.MAGIGRF)
                MDT=np.array(mag_data.MDT)
                xu,yu=sintetic_grid(quadricula,id)
                x1,y1=np.array(gama_data.X),np.array(gama_data.Y)
                x2,y2=np.array(mag_data.X),np.array(mag_data.Y)
                df_xu_yu = pd.DataFrame(np.array([xu,yu]))
                df_xu_yu=df_xu_yu.T
                df_xu_yu.rename(columns={0:'xu',1:'yu'},inplace=True)
                eth_=interp_at(x1,y1,eTh,xu,yu,algorithm=algorithm,extrapolate=True)
                eu_=interp_at(x1,y1,eU,xu,yu,algorithm=algorithm,extrapolate=True)
                kperc_=interp_at(x1,y1,KPERC, xu, yu, algorithm= algorithm,extrapolate=True)
                ctcor_=interp_at(x1,y1,CTCOR,xu,yu,algorithm=algorithm,extrapolate=True)
                uthrazao_=interp_at(x1,y1,UTHRAZAO,xu,yu,algorithm=algorithm,extrapolate=True)
                ukrazao_=interp_at(x1,y1,UKRAZAO,xu,yu,algorithm=algorithm,extrapolate=True)
                thkrazao_=interp_at(x1,y1,THKRAZAO,xu,yu,algorithm=algorithm,extrapolate=True)
                mdt_=interp_at(x2,y2,MDT,xu,yu,algorithm=algorithm,extrapolate=True)
                mag_=interp_at(x2,y2,MAGIGRF,xu,yu,algorithm=algorithm,extrapolate=True)
                data={'X':xu,'Y':yu,'MDT': mdt_,'CTCOR':ctcor_,
                      'KPERC': kperc_,'eU':eu_,'eTh':eth_,'GMT':mag_,
                      'UTHRAZAO':uthrazao_,'UKRAZAO':ukrazao_,'THKRAZAO':thkrazao_}
                df=pd.DataFrame(data)
                quadricula[id].update({geof+'_'+algorithm:df})

            else:
                MAGIGRF=np.array(mag_data.MAGIGRF)
                MDT=np.array(gama_data.MDT)
                xu,yu=sintetic_grid(quadricula,id,200)
                x1,y1=np.array(gama_data.X),np.array(gama_data.Y)
                x2,y2=np.array(mag_data.X),np.array(mag_data.Y)
                df_xu_yu = pd.DataFrame(np.array([xu,yu]))
                df_xu_yu=df_xu_yu.T
                df_xu_yu.rename(columns={0:'xu',1:'yu'},inplace=True)
                eth_=interp_at(x1,y1,eTh,xu,yu,algorithm=algorithm,extrapolate=True)
                eu_=interp_at(x1,y1,eU,xu,yu,algorithm=algorithm,extrapolate=True)
                kperc_=interp_at(x1,y1,KPERC, xu, yu, algorithm= algorithm,extrapolate=True)
                ctcor_=interp_at(x1,y1,CTCOR,xu,yu,algorithm=algorithm,extrapolate=True)
                mdt_=interp_at(x2,y2,MDT,xu,yu,algorithm=algorithm,extrapolate=True)
                mag_=interp_at(x2,y2,MAGIGRF,xu,yu,algorithm=algorithm,extrapolate=True)
                data={'X':xu,'Y':yu,'MDT': mdt_,'CTCOR':ctcor_,
                      'KPERC': kperc_,'eU':eu_,'eTh':eth_,'GMT':mag_}
                df=pd.DataFrame(data)
                quadricula[id].update({geof+'_'+algorithm:df})

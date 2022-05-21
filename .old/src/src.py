import geopandas as gpd
import pandas as pd
import numpy as np
import verde as vd
import rasterio
from tqdm import tqdm

# ~/Geodatabase/; # ---------------------------------------------------------------------------------------------------
def gdb(path=''):
    '''
    Diretório raíz dos dados : '/home/ggrl/geodatabase/'

        path : caminho até o arquivo desejado
    '''
    gdb = '/home/ggrl/geodatabase/' + path
    return gdb
# ----------------------------------------------------------------------------------------------------------------------

# IMPORTADOR DE LITOLOGIAS POR ESCALA ---------------------------------------------------------------------------------#
def importar_geometrias(camada, mapa=False):
    '''
    Recebe:
        camada      : camada vetorial a ser lida do geopackage.
        mapa        : nome do mapa presente na camada vetorial;

    Retorna:
        Objeto GeoDataFrame.
        
    Se houver seleçao de mapa retornara apenas as geometrias que possuem o nome escolhido na coluna ['MAPA']
    Se Retornar camada vazia recebera a lista das camadas veotoriais diposniveis
    Se mapa == False: retorna todos os objetos presente nesta camada vetorial
    '''
    
    lito =  gpd.read_file(gdb('geodatabase.gpkg'),
                        driver= 'GPKG',
                        layer= camada)
                        
    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]
        if folha.empty:
            print("O mapa escolhido nao est'a presente na coluna MAPA da camada veotiral. Os mapas disponiveis serao listados a seguir.")
            print('# Selecionando apenas os caracteres apos ''folha'' (SEM ESPAÇO)')
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")
            lista_mapas = list(lito.MAPA.unique())
            return lista_mapas

        else:    
            return(folha)
    else:
        return(lito)
# ----------------------------------------------------------------------------------------------------------------------

# SELECIONADOR DE REGIÃO # ---------------------------------------------------------------------------------------------
def import_malha_cartog(escala,ids):

    malha_cartog = gpd.read_file(gdb('geodatabase.gpkg'),
                                driver='GPKG',
                                layer='malha_cartog_'+escala+'_wgs84')

    malha_cartog_id_select = malha_cartog[malha_cartog['id_folha'].str.contains(ids)] # '.contains' não é ideal.
    
    return malha_cartog_id_select
# ----------------------------------------------------------------------------------------------------------------------

# IMPORTADOR DE LITOLOGIAS POR ESCALA ----------------------------------------------------------------------------------
def import_xyz(caminho):
    '''
    
    '''
    dataframe = pd.read_csv(caminho)

    return dataframe
# ----------------------------------------------------------------------------------------------------------------------

# IMPORTADOR DE LITOLOGIAS POR ESCALA ----------------------------------------------------------------------------------
def dado_bruto(camada, mapa,geof=None):
    '''
    Recebe:
        __camada : Camada vetorial presento no geopackage;
        __mapa   : Nome da folha cartografica presenta na coluna 'MAPA' da camada vetorial (SE NAO INSERIR MAPA RETORNA TODOS OS VETORES DA CAMADA SELECIONADA);
        __geof   : Dados dos aerolevantamentos. gama_tie, gama_line, 

    '''
    print(f'Diretório de dados aerogeofisicos brutos: {gdb(geof)}')
    geof_dataframe = import_xyz(geof)

    path_lito = gdb('geodatabase.gpkg')
    print(f'Diretório de dados litologicos brutos: {path_lito}')
    lito =  gpd.read_file(path_lito,
                        driver= 'GPKG',
                        layer= camada)
    print('')
    print(f"# -- Lista de camadas vetoriais disponiveis: {fiona.listlayers(path_lito)}")

    if lito.empty:
        raise "# FALHA : A camada escolhida nao está presente no geopackage."

    if mapa:
        folha = lito[lito.MAPA == 'Carta geológica da folha '+mapa]

        if folha.empty:
            print('')
            print("O mapa escolhido nao está presente na coluna MAPA da camada veotiral.")
            print(f"# -- Lista de mapas: {list(lito.MAPA.unique())}")

        else:    
            return folha, geof_dataframe
    else:
        return lito, geof_dataframe
# ----------------------------------------------------------------------------------------------------------------------



# CRIANDO DICIONARIO DE FOLHAS CARTOGRAFICAS PARA CARA TIPO DE DADO
def set_region(escala,id,geof,camada,mapa=None):
    '''
    Recebe:
        escala : Escalas disponíveis para recorte: '50k', '100k', '250k', '1kk'.
            id : ID da folha cartográfica (Articulação Sistemática de Folhas Cartográficas)
          geof : Dado aerogeofísico disponível na base de dados (/home/ggrl/geodatabase/geof/)
        camada : Litologias disponíveis na base de dados (/home/ggrl/geodatabase/geodatabase.gpkg)
    '''
    # Importando dados litológicos e geofísicos
    print('')
    print('# Importando dados')
    litologia = importar_geometrias(camada,mapa)
    geof_dataframe = import_xyz(gdb(geof))

    # LISTANDO REGIOES DAS FOLHAS DE CARTAS
    print('')
    print('# - Selecionando Folhas Cartograficas')
    dict_cartas,\
    malha_cartog_gdf_select = cartas(escala,id)

    print('')
    print('# -- Contruindo dicionario de metadados')
    metadatadict,        \
    lista_atributo_geof, \
    lista_atributo_geog, \
    lista_atributo_proj, \
          geof_descrito  = descricao(geof_dataframe)

    dic_raw_meta={'Metadata'          :metadatadict,
                  'Lista_at_geof'     :lista_atributo_geof,
                  'Lista_at_geog'     :lista_atributo_geog,
                  'Lista_at_proj'     :lista_atributo_proj,
                  'Percentiles'       :geof_descrito,
                  'Malha_cartografica':malha_cartog_gdf_select}

    # ITERANDO ENTRE AS FOLHAS DE CARTAS
    print('')
    print(f"# --- Início da iteração entre as folhas cartográficas #")

    ## dict_cartas = {'litologia':''}
    dict_cartas['litologia'] ={}
    
    for index, row in tqdm(malha_cartog_gdf_select.iterrows()):

        # RECORTANDO DATA PARA CADA FOLHA COM verde.inside() ['region.proj']
        data = geof_dataframe[vd.inside((geof_dataframe.X, geof_dataframe.Y), region = row.region_proj)]

        # GERANDO TUPLA DE COORDENADAS
        '''if len(data) < 10000 & len(data) > 0:
            print('TESTE AQUI')

            y = {index:litologia}
            dict_cartas['litologia'].update(y)
            print(f"A folha {index} possui apenas '{len(data)}' pontos coletados que devem ser adicionados a folha mais próxima")
            print(f" Atualizando dados geofísicos em dic_cartas['raw_data']")
            x = {index:data}
            dict_cartas['raw_data'].update(x) 
            print(f" com {len(data)} pontos de amostragem")'''
        if len(data) > 0:
            print(f"# Folha de código: {index}")
            print(f" Atualizando dados geofísicos em dic_cartas['raw_data']")
            x = {index:data}
            dict_cartas['raw_data'].update(x) 
            print(f" com {len(data)} pontos de amostragem")

            litologia.to_crs(32723,inplace=True)
            print(litologia.crs)

            litologia = litologia.cx[row.region_proj[0]:row.region_proj[1],row.region_proj[2]:row.region_proj[3]]
            print(f" Atualizando dados litológicos em dic_cartas['litologia']")
            print(f" com {litologia.shape[0]} poligonos descritos por\
                         {litologia.shape[1]} atributos geologicos ")
            
            # dict_cartas = {'litologia':{'id_folha':''}         # this can be done better
            #                                                     dict_cartas = {'index':'litologia','geofisico','interpolado','...'}
            #                }
            y = {index:litologia}
            dict_cartas['litologia'].update(y)
            
        
        elif data.empty:
            None
            #print('Folha cartografica sem dados Aerogeofisicos')

    return dict_cartas, dic_raw_meta
# --------------------------------------------------------------------------------------

# # --------------------- DEFININDO FUNÇÃO DE QUE CHAMARÁ AS FUNÇÕES ANTERIORES PROVOCANDO UM ENCADEAMENTO DE OPERAÇÕES -------------- 
def interpolar(mag=None,gama=None, geof=None,
               dic_cartas=None,dic_raw_meta=None):
    '''
    Recebe:
                 mag :
                gama :
          dic_cartas :
        dic_raw_meta :


    '''
    # Criando chave para dados Interpolados
    dic_cartas['cubic'] = {'':''}

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
            xu, yu = td.regular(shape = (1272, 888),
                                area  = area)

            if geof:
                CTC = np.array(gdf_geof.CTC)
                THC = np.array(gdf_geof.THC)
                UC = np.array(gdf_geof.UC)
                KC = np.array(gdf_geof.KC)
                MAGR = np.array(gdf_geof.MAGR)
                ALTE = np.array(gdf_geof.ALTE)


                x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)

                alte_ = td.interp_at(x2, y2, ALTE, xu, yu, algorithm = 'cubic', extrapolate = True)
                uc_ = td.interp_at(x2, y2, UC, xu, yu, algorithm = 'cubic', extrapolate = True)
                kc_ = td.interp_at(x2, y2, KC, xu, yu, algorithm = 'cubic', extrapolate = True)
                ctc_ = td.interp_at(x2, y2, CTC, xu, yu, algorithm = 'cubic', extrapolate = True)
                thc_ = td.interp_at(x2, y2, THC, xu, yu, algorithm = 'cubic', extrapolate = True)
                magr_ = td.interp_at(x2, y2, MAGR, xu, yu, algorithm = 'cubic', extrapolate = True)


                # intialise data of lists. 
                data = {'X':xu, 'Y':yu, 'MAGIGRF': magr_,'ALTE':alte_,
                        'CTC': ctc_, 'KC': kc_, 'UC':uc_, 'THC': thc_} 
                
                # Create DataFrame 
                interpolado_cubico = pd.DataFrame(data)
                
                # Atualizando chave 'cubic' com dados interpolados
                y={index:interpolado_cubico}
                dic_cartas['cubic'].update(y)


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
                
                # Print the output 
                y={index:interpolado_cubico}
                dic_cartas['cubic'].update(y)  

            if gama:
                CTCOR = np.array(gdf_geof.CTCOR)
                MDT = np.array(gdf_geof.MDT)
                eTh = np.array(gdf_geof.eTh)
                eU = np.array(gdf_geof.eU)
                KPERC = np.array(gdf_geof.KPERC)
                THKRAZAO = np.array(gdf_geof.THKRAZAO)
                UKRAZAO = np.array(gdf_geof.UKRAZAO)
                UTHRAZAO = np.array(gdf_geof.UTHRAZAO)

                x2, y2 = np.array(gdf_geof.X), np.array(gdf_geof.Y)

                eTh_ = td.interp_at(x2, y2, eTh, xu, yu, algorithm = 'cubic', extrapolate = True)
                eu_ = td.interp_at(x2, y2, eU, xu, yu, algorithm = 'cubic', extrapolate = True)
                kperc_ = td.interp_at(x2, y2, KPERC, xu, yu, algorithm = 'cubic', extrapolate = True)
                ctcor_ = td.interp_at(x2, y2, CTCOR, xu, yu, algorithm = 'cubic', extrapolate = True)
                mdt_ = td.interp_at(x2, y2, MDT, xu, yu, algorithm = 'cubic', extrapolate = True)
                uthrazao_ = td.interp_at(x2, y2, UTHRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                ukrazao_ = td.interp_at(x2, y2, UKRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)
                thkrazao_ = td.interp_at(x2, y2, THKRAZAO, xu, yu, algorithm = 'cubic', extrapolate = True)

                # intialise data of lists. 
                data = {'X':xu, 'Y':yu, 'MDT': mdt_,  'CTCOR': ctcor_,
                        'KPERC': kperc_, 'eU':eu_, 'eTH': eTh_,
                        'UTHRAZAO':uthrazao_,'UKRAZAO':ukrazao_,'THKRAZAO':thkrazao_} 
                
                # Create DataFrame 
                interpolado_cubico = pd.DataFrame(data)
                                
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
                print('')
                print(f" geof: {gdf.crs}")
            else:
                gdf = gpd.GeoDataFrame(geof_cubic,crs=32723)
                gdf = gdf.set_crs(32723, allow_override=True)
                gdf = gdf.to_crs("EPSG:4326")
                print('')
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

# FUNÇOES DE PLOTAGEM COM GEOPANDAS
def plot_brazil(gdf,atributo=None):
    world = dado_bruto.gpd.read_file(dado_bruto.gpd.datasets.get_path('naturalearth_lowres'))
    brazil = world[world.name == 'Brazil']
    if atributo:
        ax = brazil.boundary.plot(color='black')
        gdf.plot(atributo,ax=ax,color='black')
    else:
        ax = brazil.boundary.plot(color='black')
        gdf.plot(ax=ax,color='black')

def plot_base(gdf,atributo=None,camada=None,mapa=None):
    litologia = dado_bruto(camada,mapa)

    if atributo:
        ax = litologia.plot('SIGLA')
        gdf.plot(atributo,color='black',ax=ax)
    else:
        ax = litologia.plot('SIGLA')
        gdf.plot(ax=ax,color='black')

def labels(gdf):
    gdf['centroid'] = gdf['geometry'].apply(lambda x: x.representative_point().coords[:])
    gdf['centroid'] = [coords[0] for coords in gdf['centroid']]

    for index, row in gdf.iterrows():
        plt.annotate(text=row['id_folha'], xy=row['centroid'],horizontalalignment='center')

# ----------------------------------------------------------------------------------------------------------------------


# DEFININDO NOMES DA MALHA A PARTIR DA ARTICULaÇO SISTEMÁTICA DE FOLHAS DE CARTAS. 
# CONSTURINDO UMA LISTA E DEFININDO COMO UMA SERIES (OBJETO DO PANDAS).
def nomeador_malha(gdf):
    '''
    
    '''
    df = pd.DataFrame(gdf)
    lista_malha = []
    for index, row in df.iterrows():
        row['id_folha'] = (nomeador_grid(row.region[0],row.region[1],
                                         row.region[3],row.region[2],escala=5))
        lista_malha.append(row.id_folha)

    gdf['id_folha'] = lista_malha
# ---------------------------------------------------------------------------------------------------------------
 
# DEFININDO LIMITES DE CADA FOLHA CARTOGRÁFICA -----------------------------------------------------------------#
def regions(malha_cartog):
    '''
    
    '''
    bounds = malha_cartog.bounds
    malha_cartog['region'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]


    malha_cartog.to_crs("EPSG:32723",inplace=True)   # APENAS AS INFORMAÇOES NA ZONA 23SUL UTM ESTARÃO CORRETAS
    print(f"{malha_cartog.crs}")

    bounds = malha_cartog.bounds
    malha_cartog['region_proj'] = \
    [(left,right,bottom,top) for left,right,bottom,top in zip(bounds['minx'],bounds['maxx'],
                                                              bounds['miny'],bounds['maxy'])]
    return malha_cartog
# ----------------------------------------------------------------------------------------------------------------------

# LISTANDO REGIÕES DE CADA FOLHA DE CARTAS DA MALHA CARTOGRÁFICA \ ['REGEION'] = ['ID_FOLHA'] REDUNDANCIA
# SELECIONANDO AREA DE ESTUDO

def cartas(escala,ids):
    '''
    
    '''
    print('# --- Iniciando seleção de área de estudo')
    malha_cartog_gdf_select = import_malha_cartog(escala,ids)
    malha_cartog_gdf_select.set_index('id_folha',inplace=True)
    regions(malha_cartog_gdf_select)

    # CRIANDO UM DICIONÁRIO DE CARTAS
    print('# --- Construindo Dicionario de Cartas')
    malha_cartog_gdf_select['raw_data']= ''
    dic_cartas = malha_cartog_gdf_select.to_dict()

    # MAIS DE UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) > 1:
        print(f"{len(dic_cartas['raw_data'])} folhas cartográfica selecionadas")
        print("")

    # APENAS UMA FOLHA DE CARTA SELECIONADA
    if len(dic_cartas['raw_data']) == 1:
        print(f"{len(dic_cartas['raw_data'])} folha cartográfica selecionada")
        print("")
        
    return dic_cartas,malha_cartog_gdf_select 
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# LISTANDO ATRIBUTOS GEOFÍSICOS E ATRIBUTOS GEOGRÁFICOS
def lista_cols(geof):
    print('Listando atributos dos dados geofisicos')
    atributos_geof = list(geof.columns)             # DataFrame.columns
    lista_atributo_geof=[]
    lista_atributo_geog=[]
    lista_atributo_proj=[]

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
    codigo=str(geof)        
    print(f"# --- # Listagem de dados do aerolevantamento:  ")
    print(f"Lista de atributos geofísicos = {lista_atributo_geof}")
    print(f"lista de atributos geograficos = {lista_atributo_geog}")
    print(f"lista de atributos projetados = {lista_atributo_proj}")
    return lista_atributo_geof, lista_atributo_geog, lista_atributo_proj
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# DESCRIÇÃO ESTATISTICA DOS DADOS AEROGEOFÍSICOS
def descricao(geof):
    lista_atributo_geof,lista_atributo_geog,lista_atributo_proj = lista_cols(geof)  # USANDO FUNCAO DEFINIDA ACIMA PARA CATEGORIZAR METADADO
        
    metadatadict = pd.DataFrame(geof.dtypes)
    metadatadict["Valores Faltantes"] = geof.isnull().sum()
    metadatadict["Valores Únicos"] = geof.nunique()
    metadatadict["Valores Negativos"] = sum(n < 0 for n in geof.values)
    metadatadict["Amostragem"] = geof.count()
    metadatadict = metadatadict.rename(columns = {0 : 'dType'})

    geof_df = geof.drop(axis=0,columns=lista_atributo_geog)
    geof_df.drop(axis=0,columns=lista_atributo_proj,inplace=True)

    #datadict['Valores Negativos'] = lista_negativo

    geof_descrito = geof_df.describe(percentiles=[0.001,0.1,0.25,0.5,0.75,0.995])
    
    return metadatadict,lista_atributo_geof,lista_atributo_geog,lista_atributo_proj,geof_descrito
#----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
def metadataframe(GeoDataFrame):
    '''
    Recebe: GeoDataFrame (Features and Geometry)

        Retorna: An object Pandas DataFrame containing a MetaData description of the GeoPandas Object GeoDataFrame
    '''
    meta_lito = pd.DataFrame(GeoDataFrame.dtypes)               # Describe the dtype of each column from the DataFrame or, better saying, GeoDataFrame;
    meta_lito['Valores null'] = GeoDataFrame.isnull().sum()     # Describe the sum of each null value from our object
    meta_lito['Valores unicos'] = GeoDataFrame.nunique()        # Describe the number of unique values from our object, that is a GeoDataFrame
    meta_lito = meta_lito.rename(columns = {0 : 'dType'})       # Rename the first column to 'dtype', the name of the function we used.
    return meta_lito
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
# com estas funçoes utilizadas asssimas, podemos definir uma funçao que descreve o nosso dado vetorial
def describe_geologico(gdf):
    lista_colunas = list(gdf.columns)
    lista_litotipos = list(gdf.LITOTIPOS.unique())
    lista_legenda = list(gdf.LEGENDA.unique())

    dic_litologico = {'lista_colunas': lista_colunas,
                      'lista_litotipos': lista_litotipos,
                      'lista_legenda': lista_legenda}
    return dic_litologico   
# ----------------------------------------------------------------------------------------------------------------------

# ----------------------------------------------------------------------------------------------------------------------
#### Filtro de LITOTIPOS
def filtro(gdf,mineral):
    '''
    Recebe uma camada vetorial e uma 'str', navega pela coluna LITOTIPOS selecionando geometrias que contem a 'str'

    Caso nenhuma geometria seja selecionada, retornara a lista de valores unicos presenta na coluna LITOTIPOS da camada vetorial


    '''
    filtrado = gdf[gdf['LITOTIPOS'].str.contains(mineral)]
    if filtrado.empty:
        print(f"{list(gdf['LITOTIPOS'].unique())}")
    else:
        return filtrado
# ----------------------------------------------------------------------------------------------------------------------


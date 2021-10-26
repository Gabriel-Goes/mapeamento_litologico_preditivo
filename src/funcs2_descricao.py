from tqdm import tqdm
import pandas as pd





# ----------------------------------------------------------------------------------------------------------------------
# METANÁLISE DOS DADOS LITOLÓGICOS
def metadataframe(GeoDataFrame):
    '''
    Recebe : 
        GeoDataFrame Object : Camadas vetoriais de unidades litoestratigráficas;
        
        Retorna :
            DataFrame Object: Planílha com metanálise das camadas vetoriais;
    '''
    print(f'# -- Gerando MetaDataFrame Litoestratigráfico')
    type_dataframe = pd.DataFrame(GeoDataFrame.dtypes)               # Describe the dtype of each column from the DataFrame or, better saying, GeoDataFrame;

    type_dataframe['Valores null']   = GeoDataFrame.isnull().sum()   # Describe the sum of each null value from our object
    type_dataframe['Valores unicos'] = GeoDataFrame.nunique()        # Describe the number of unique values from our object, that is a GeoDataFrame

    meta_dataframe_litologico = type_dataframe.rename(columns = {0 : 'dType'})       # Rename the first column to 'dtype', the name of the function we used.

    print('')
    
    return meta_dataframe_litologico
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



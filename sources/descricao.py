import tqdm
import pandas as pd

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

# DESCRIÇÃO ESTATISTICA DOS DADOS AEROGEOFÍSICOS
def descricao(geof):            
    lista_atributo_geof,lista_atributo_geog,lista_atributo_proj = lista_cols(geof)  # USANDO FUNCAO DEFINIDA ACIMA PARA CATEGORIZAR METADADO
    
    metadatadict = pd.DataFrame(geof.dtypes)
    metadatadict["Valores Faltantes"] = geof.isnull().sum()
    metadatadict["Valores Únicos"] = geof.nunique()
    metadatadict["Amostragem"] = geof.count()
    metadatadict = metadatadict.rename(columns = {0 : 'dType'})

    geof_df = geof.drop(axis=0, columns=lista_atributo_geog)
    geof_df.drop(axis=0, columns=lista_atributo_proj, inplace=True)

    geof_descrito = geof_df.describe(percentiles=[0.001,0.1,0.25,0.5,0.75,0.995])
    
    return metadatadict,lista_atributo_geof,lista_atributo_geog,lista_atributo_proj,geof_descrito

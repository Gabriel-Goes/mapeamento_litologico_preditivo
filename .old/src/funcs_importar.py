# ggrl;
# geologist_machine; 
# ic_2021
\
\
\

import pandas as pd
import geopandas as gpd
import fiona


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
    
    print(f"# -- Lista de camadas vetoriais disponiveis no Geopackage: {list(fiona.listlayers(gdb('geodatabase.gpkg')))}")

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
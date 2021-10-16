# ggrl;
# geologist_machine; 
# ic_2021
\
\
\

import pandas as pd
import geopandas as gpd
import fiona


# ~/Geodatabase/; 
def gdb(caminho='/home/ggrl/geodatabase/geodatabase.gpkg'):

    '''
    Definindo local de acesso aos dados na máquina local.
    '''

    gdb = caminho

    return gdb


def geof_gdb(geof):

    '''
    Recebe: 
        caminho_geof : /diretoŕo .XYZ;
          : .csv tratado;

    Retorna:
        str do caminho para o modulo importar.dado_bruto;
    '''

    path = '/home/ggrl/geodatabase/'

    geof_path= path + geof

    return geof_path
# ----------------------------------------------------------------------------------------------------------------------

# IMPORTADOR DE LITOLOGIAS POR ESCALA --------------------------------------------------------------------------#
def dado_bruto(camada, mapa,geof=None):
    '''
    Recebe:
        __camada : Camada vetorial presento no geopackage;
        __mapa   : Nome da folha cartografica presenta na coluna 'MAPA' da camada vetorial (SE NAO INSERIR MAPA RETORNA TODOS OS VETORES DA CAMADA SELECIONADA);
        __geof   : Dados dos aerolevantamentos. gama_tie, gama_line, 

    '''
    path_geof = geof_gdb(geof)
    print(f'Diretório de dados aerogeofisicos brutos: {path_geof}')
    
    geof_dataframe = pd.read_csv(path_geof)

    path_lito = gdb()
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


# SELECIONADOR DE REGIÃO  ---------------------------------------------------------------------------------------------#
def import_malha_cartog(escala,ids):

    malha_cartog = gpd.read_file(gdb(),
                                 driver='GPKG',
                                 layer='malha_cartog_'+escala+'_wgs84')

    malha_cartog_id_select = malha_cartog[malha_cartog['id_folha'].str.contains(ids)]# '.contains' não é ideal.
    
    return malha_cartog_id_select
# ----------------------------------------------------------------------------------------------------------------------
